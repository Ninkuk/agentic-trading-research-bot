from sources.screeners.treasury_screener import db


def test_ensure_schema_creates_all_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "snapshots",
        "dts_cash",
        "debt_penny",
        "avg_rates",
        "upcoming_auctions",
        "auction_results",
        "yield_curve",
    } <= tables
