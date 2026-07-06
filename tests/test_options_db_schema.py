from sources.screeners.cboe_options import db


def test_ensure_schema_is_idempotent_and_creates_objects():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise
    names = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    }
    assert {"underlyings", "option_snapshots", "underlying_daily", "days", "snapshots"} <= names
    assert {"v_unusual_activity", "v_iv_rank", "v_latest_sentiment"} <= names


def test_option_snapshots_primary_key():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(option_snapshots)")]
    assert {
        "snapshot_date",
        "occ_symbol",
        "source",
        "iv",
        "delta",
        "open_interest",
        "volume",
        "vol_oi_ratio",
    } <= set(cols)
