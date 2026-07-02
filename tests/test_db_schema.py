from screener.catalog import DataPoint
from screener.db import connect, ensure_schema, upsert_data_points


def cols(conn):
    return {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}


def test_ensure_schema_creates_tables_and_columns():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL", "sector": "TEXT"})
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"snapshots", "data_points", "metrics"} <= tables
    assert {"snapshot_id", "symbol", "price", "sector"} <= cols(conn)


def test_ensure_schema_is_idempotent_and_adds_new_columns():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL"})
    ensure_schema(conn, {"price": "REAL", "rsi": "REAL"})  # rerun + new column
    assert "rsi" in cols(conn)


def test_upsert_data_points_inserts_and_updates():
    conn = connect(":memory:")
    ensure_schema(conn, {})
    upsert_data_points(conn, [DataPoint("zScore", "Altman Z-Score", "Tech", True)])
    upsert_data_points(conn, [DataPoint("zScore", "Z-Score", "Technical", False)])
    row = conn.execute(
        "SELECT name, category, is_pro FROM data_points WHERE id='zScore'").fetchone()
    assert row == ("Z-Score", "Technical", 0)
