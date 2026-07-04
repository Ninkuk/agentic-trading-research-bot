from sources.screeners.usda_screener import db


def test_ensure_schema_creates_table_and_views_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"snapshots", "usda_obs"} <= tables
    assert {"v_latest_balance", "v_stocks_to_use", "v_series_history"} <= views
