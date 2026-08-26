from sources.screeners.cboe_stats import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "pcr_daily", "vix_daily"} <= tables


def test_ensure_schema_migrates_cor3m_onto_pre_existing_vix_daily():
    """A live DB written before COR3M shipped lacks the column; CREATE IF NOT
    EXISTS never widens it, so ensure_schema must ALTER."""
    conn = db.connect(":memory:")
    conn.execute(
        "CREATE TABLE vix_daily (date TEXT PRIMARY KEY, open REAL, high REAL,"
        " low REAL, close REAL, vix3m REAL, vix9d REAL, vvix REAL)"
    )
    conn.execute("INSERT INTO vix_daily (date, close) VALUES ('2026-06-01', 14.6)")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(vix_daily)")}
    assert "cor3m" in cols
    assert conn.execute("SELECT close, cor3m FROM vix_daily").fetchone() == (14.6, None)
