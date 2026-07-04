from nyfed_screener import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "reference_rates", "repo_ops", "soma_holdings",
            "primary_dealer_stats", "iorb"} <= tables
