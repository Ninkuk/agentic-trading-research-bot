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


def test_ensure_schema_adds_skew_term_columns_to_a_pre_existing_daily_table():
    """A live options.db predates the rollup columns; ensure_schema must
    ALTER them in (additive, nullable) rather than fail the nightly run."""
    conn = db.connect(":memory:")
    conn.executescript(
        """CREATE TABLE underlying_daily (
               snapshot_date TEXT NOT NULL, underlying TEXT NOT NULL,
               underlying_price REAL, close REAL, iv30 REAL,
               total_call_volume INTEGER, total_put_volume INTEGER,
               put_call_volume_ratio REAL, total_call_oi INTEGER,
               total_put_oi INTEGER, put_call_oi_ratio REAL,
               PRIMARY KEY (snapshot_date, underlying));"""
    )
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(underlying_daily)")}
    assert {
        "front_expiration",
        "back_expiration",
        "atm_iv_front",
        "atm_iv_back",
        "term_spread",
        "put25_iv",
        "call25_iv",
        "skew25",
    } <= cols
    db.ensure_schema(conn)  # idempotent on the migrated table
