from earnings_calendar import db


def test_ensure_schema_creates_tables_and_four_earnings_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "calendar_now"} <= tables
    assert {"v_upcoming_earnings", "v_imminent_earnings",
            "v_this_week_earnings", "v_earnings_confirmed"} <= views


def test_ensure_schema_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)   # must not raise
