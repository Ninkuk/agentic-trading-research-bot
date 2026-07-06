from sources.screeners.cboe_stats import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "pcr_daily", "vix_daily"} <= tables
