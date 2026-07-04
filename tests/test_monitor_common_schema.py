from sources.common.monitor_common import connect, ensure_schema, set_today


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def test_ensure_schema_creates_tables():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "snapshots", "calendar_now"} <= names


def test_ensure_schema_idempotent_keeps_singleton():
    conn = _fresh()
    ensure_schema(conn)  # second call must not raise
    n = conn.execute("SELECT COUNT(*) FROM calendar_now").fetchone()[0]
    assert n == 1


def test_set_today_writes_date_and_horizon():
    conn = _fresh()
    today = set_today(conn, "2026-07-03T12:00:00+00:00", horizon_days=5)
    assert today == "2026-07-03"
    row = conn.execute(
        "SELECT today, horizon_days FROM calendar_now WHERE id=0").fetchone()
    assert row == ("2026-07-03", 5)


def test_subtype_defaults_to_empty_string_not_null():
    conn = _fresh()
    conn.execute("INSERT INTO events (event_type, event_date, source, fetched_at) "
                 "VALUES ('x', '2026-07-03', 'fred', 't')")
    conn.commit()
    assert conn.execute("SELECT subtype FROM events").fetchone()[0] == ""
