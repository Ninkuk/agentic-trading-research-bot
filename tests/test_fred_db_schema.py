from sources.screeners.fred_screener import db


def _tables_and_views(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')").fetchall()
    return {r[0] for r in rows}


def test_ensure_schema_creates_tables_and_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    names = _tables_and_views(conn)
    assert {"snapshots", "series", "observations"} <= names
    assert {"v_latest", "v_yoy_change", "v_zscore", "v_regime_signals"} <= names


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise
    assert "observations" in _tables_and_views(conn)
