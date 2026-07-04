from sources.monitors.fomc_calendar import db


def test_ensure_schema_creates_shared_tables_and_fomc_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "calendar_now"} <= tables
    assert {"v_next_fomc", "v_in_blackout", "v_upcoming_fomc_events"} <= views


def test_ensure_schema_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)   # must not raise
