from pipeline.scheduler import db

NOW = "2026-07-04T12:00:00+00:00"


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_schema_tables_and_views():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    assert {"job_runs", "snapshots", "v_recent_runs", "v_failures"} <= names
    db.ensure_schema(conn)  # idempotent


def test_attempts_increment_and_finish():
    conn = _fresh()
    a1 = db.start_attempt(conn, "cftc", "2026-07-03", NOW)
    assert a1 == 1
    db.finish_attempt(conn, "cftc", "2026-07-03", a1, NOW, "error", "HTTPError")
    a2 = db.start_attempt(conn, "cftc", "2026-07-03", NOW)
    assert a2 == 2
    db.finish_attempt(conn, "cftc", "2026-07-03", a2, NOW, "ok")
    assert db.ok_exists(conn, "cftc", "2026-07-03")
    assert db.attempt_count(conn, "cftc", "2026-07-03") == 2
    assert not db.ok_exists(conn, "cftc", "other-key")


def test_error_row_records_type_name_only():
    conn = _fresh()
    a = db.start_attempt(conn, "fred", "cpi:2026-07-04", NOW)
    db.finish_attempt(conn, "fred", "cpi:2026-07-04", a, NOW, "error", "KeyError")
    err = conn.execute("SELECT error FROM job_runs WHERE job='fred'").fetchone()[0]
    assert err == "KeyError"


def test_live_running_blocks_until_stale():
    conn = _fresh()
    db.start_attempt(conn, "stocks", "weekly:2026-06-28", "2026-07-04T11:30:00+00:00")
    assert db.live_running(conn, "stocks", "weekly:2026-06-28", NOW, stale_hours=2)
    # same row viewed 3 hours later: stale -> crashed, no longer blocks
    assert not db.live_running(conn, "stocks", "weekly:2026-06-28",
                               "2026-07-04T14:31:00+00:00", stale_hours=2)


def test_running_with_successor_attempt_is_not_live():
    conn = _fresh()
    a1 = db.start_attempt(conn, "j", "k", "2026-07-04T09:00:00+00:00")
    db.finish_attempt(conn, "j", "k", a1, NOW, "error", "RuntimeError")
    a2 = db.start_attempt(conn, "j", "k", NOW)
    db.finish_attempt(conn, "j", "k", a2, NOW, "ok")
    assert not db.live_running(conn, "j", "k", NOW, stale_hours=2)


def test_chain_recency_helpers():
    conn = _fresh()
    assert db.newest_ok_among(conn, ("cftc", "fred")) is None
    a = db.start_attempt(conn, "cftc", "2026-07-03", "2026-07-03T20:00:00+00:00")
    db.finish_attempt(conn, "cftc", "2026-07-03", a, "2026-07-03T20:05:00+00:00", "ok")
    a = db.start_attempt(conn, "fred", "cpi:2026-07-04", NOW)
    db.finish_attempt(conn, "fred", "cpi:2026-07-04", a, NOW, "ok")
    job, key, fin = db.newest_ok_among(conn, ("cftc", "fred"))
    assert (job, key, fin) == ("fred", "cpi:2026-07-04", NOW)
    assert db.last_ok_finished_at(conn, "leads") is None
    assert db.last_ok_finished_at(conn, "cftc") == "2026-07-03T20:05:00+00:00"


def test_views_and_prune():
    conn = _fresh()
    a = db.start_attempt(conn, "j", "k", "2026-01-01T00:00:00+00:00")
    db.finish_attempt(conn, "j", "k", a, "2026-01-01T00:01:00+00:00", "error", "OSError")
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, NOW, 0, 0)
    assert conn.execute("SELECT COUNT(*) FROM v_failures").fetchone()[0] == 1
    assert db.prune(conn, keep_days=30, now_iso=NOW) >= 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0] == 0
