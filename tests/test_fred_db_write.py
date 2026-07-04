from sources.screeners.fred_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _meta(series_id, theme="rates", title="T", **extra):
    base = {"id": series_id, "theme": theme, "title": title}
    base.update(extra)
    return base


def test_write_observations_upserts_by_series_and_date():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")

    n1 = db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 1.0},
        {"date": "2026-02-01", "value": 2.0},
    ])
    assert n1 == 2

    # Re-run with a REVISED value for an existing date + one new date.
    n2 = db.write_observations(conn, "X", [
        {"date": "2026-02-01", "value": 2.5},   # revision
        {"date": "2026-03-01", "value": 3.0},   # new
    ])
    assert n2 == 2

    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id='X' ORDER BY date"
    ).fetchall()
    assert rows == [("2026-01-01", 1.0), ("2026-02-01", 2.5), ("2026-03-01", 3.0)]


def test_write_observations_stores_none_as_null():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [{"date": "2026-01-01", "value": None}])
    got = conn.execute(
        "SELECT value FROM observations WHERE series_id='X'").fetchone()
    assert got[0] is None


def test_upsert_series_preserves_first_seen():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X", title="Old")], "2026-01-01T00:00:00+00:00")
    db.upsert_series(conn, [_meta("X", title="New")], "2026-07-02T00:00:00+00:00")
    first_seen, last_seen, title = conn.execute(
        "SELECT first_seen, last_seen, title FROM series WHERE series_id='X'"
    ).fetchone()
    assert first_seen == "2026-01-01T00:00:00+00:00"
    assert last_seen == "2026-07-02T00:00:00+00:00"
    assert title == "New"


def test_v_latest_picks_latest_non_null():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 1.0},
        {"date": "2026-02-01", "value": 2.0},
        {"date": "2026-03-01", "value": None},   # trailing gap must be skipped
    ])
    row = conn.execute(
        "SELECT date, value FROM v_latest WHERE series_id='X'").fetchone()
    assert row == ("2026-02-01", 2.0)


def test_v_zscore_sign_on_known_distribution():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    # values 0,0,0,0,10 -> latest 10 is well above the mean -> positive z
    db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 0.0},
        {"date": "2026-02-01", "value": 0.0},
        {"date": "2026-03-01", "value": 0.0},
        {"date": "2026-04-01", "value": 0.0},
        {"date": "2026-05-01", "value": 10.0},
    ])
    z = conn.execute(
        "SELECT zscore FROM v_zscore WHERE series_id='X'").fetchone()[0]
    assert z > 0


def test_v_yoy_change_computes_delta():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [
        {"date": "2025-06-01", "value": 100.0},
        {"date": "2026-06-01", "value": 110.0},
    ])
    row = conn.execute(
        "SELECT latest, year_ago, change_abs, change_pct "
        "FROM v_yoy_change WHERE series_id='X'").fetchone()
    assert row[0] == 110.0
    assert row[1] == 100.0
    assert row[2] == 10.0
    assert abs(row[3] - 10.0) < 1e-9


def test_prune_deletes_old_snapshots_but_not_observations():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [{"date": "2020-01-01", "value": 1.0}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, "2026-07-01T00:00:00+00:00", 1, 1)  # recent

    removed = db.prune(conn, keep_days=30, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    snaps = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    assert snaps == 1      # old snapshot gone
    assert obs == 1        # observation preserved
