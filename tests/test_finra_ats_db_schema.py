from sources.screeners.finra_ats import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"venues", "ats_volume", "weeks", "snapshots"} <= tables
