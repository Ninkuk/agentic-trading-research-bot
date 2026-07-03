from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_underlying", "replace_day",
           "upsert_underlying_daily", "record_day", "write_snapshot",
           "stored_symbols", "prune"]

_CONTRACT_COLS = [
    "snapshot_date", "occ_symbol", "source", "underlying", "expiration",
    "strike", "type", "bid", "ask", "mark", "last", "theo", "iv", "delta",
    "gamma", "theta", "vega", "rho", "open_interest", "volume",
    "underlying_price", "vol_oi_ratio", "fetched_at",
]

_DAILY_COLS = [
    "snapshot_date", "underlying", "underlying_price", "close", "iv30",
    "total_call_volume", "total_put_volume", "put_call_volume_ratio",
    "total_call_oi", "total_put_oi", "put_call_oi_ratio",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS underlyings (
    symbol     TEXT PRIMARY KEY,
    is_index   INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS option_snapshots (
    snapshot_date    TEXT NOT NULL,
    occ_symbol       TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'cboe',
    underlying       TEXT NOT NULL REFERENCES underlyings(symbol),
    expiration       TEXT,
    strike           REAL,
    type             TEXT,
    bid              REAL,
    ask              REAL,
    mark             REAL,
    last             REAL,
    theo             REAL,
    iv               REAL,
    delta            REAL,
    gamma            REAL,
    theta            REAL,
    vega             REAL,
    rho              REAL,
    open_interest    INTEGER,
    volume           INTEGER,
    underlying_price REAL,
    vol_oi_ratio     REAL,
    fetched_at       TEXT,
    PRIMARY KEY (snapshot_date, occ_symbol, source)
);
CREATE INDEX IF NOT EXISTS ix_os_underlying_date
    ON option_snapshots(underlying, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_os_date ON option_snapshots(snapshot_date);
CREATE TABLE IF NOT EXISTS underlying_daily (
    snapshot_date         TEXT NOT NULL,
    underlying            TEXT NOT NULL REFERENCES underlyings(symbol),
    underlying_price      REAL,
    close                 REAL,
    iv30                  REAL,
    total_call_volume     INTEGER,
    total_put_volume      INTEGER,
    put_call_volume_ratio REAL,
    total_call_oi         INTEGER,
    total_put_oi          INTEGER,
    put_call_oi_ratio     REAL,
    PRIMARY KEY (snapshot_date, underlying)
);
CREATE TABLE IF NOT EXISTS days (
    snapshot_date TEXT NOT NULL,
    underlying    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    PRIMARY KEY (snapshot_date, underlying)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    symbol_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""

_VIEWS = """
-- (1) unusual activity on the latest snapshot: contracts where today's volume
-- dwarfs standing open interest. Works from day one.
CREATE VIEW IF NOT EXISTS v_unusual_activity AS
SELECT underlying, occ_symbol, expiration, strike, type,
       volume, open_interest, vol_oi_ratio, iv, snapshot_date
FROM option_snapshots
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM option_snapshots)
  AND source = 'cboe'
  AND volume >= 100
  AND vol_oi_ratio >= 1.0
ORDER BY vol_oi_ratio DESC;

-- (2) IV Rank/percentile of each underlying's latest iv30 within its full
-- stored history (min-max rank + fraction-of-days-below percentile). Returns
-- meaningful values only once history accumulates (needs many days).
CREATE VIEW IF NOT EXISTS v_iv_rank AS
WITH bounds AS (
  SELECT underlying, MIN(iv30) AS iv_min, MAX(iv30) AS iv_max, COUNT(*) AS n_days
  FROM underlying_daily WHERE iv30 IS NOT NULL GROUP BY underlying),
today AS (
  SELECT underlying, snapshot_date, iv30 FROM underlying_daily
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily)
    AND iv30 IS NOT NULL)
SELECT t.underlying, t.snapshot_date, t.iv30, b.iv_min, b.iv_max, b.n_days,
       CASE WHEN b.iv_max > b.iv_min
            THEN 100.0 * (t.iv30 - b.iv_min) / (b.iv_max - b.iv_min) END AS iv_rank,
       (SELECT 100.0 * COUNT(*) / b.n_days FROM underlying_daily h
         WHERE h.underlying = t.underlying AND h.iv30 < t.iv30) AS iv_percentile
FROM today t JOIN bounds b USING (underlying);

-- (3) latest-day sentiment snapshot per underlying.
CREATE VIEW IF NOT EXISTS v_latest_sentiment AS
SELECT underlying, snapshot_date, underlying_price, iv30,
       put_call_volume_ratio, put_call_oi_ratio,
       total_call_volume, total_put_volume
FROM underlying_daily
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily);
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()
