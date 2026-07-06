from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = [
    "connect",
    "ensure_schema",
    "upsert_underlying",
    "replace_day",
    "upsert_underlying_daily",
    "record_day",
    "write_snapshot",
    "stored_symbols",
    "prune",
]

_CONTRACT_COLS = [
    "snapshot_date",
    "occ_symbol",
    "source",
    "underlying",
    "expiration",
    "strike",
    "type",
    "bid",
    "ask",
    "mark",
    "last",
    "theo",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "open_interest",
    "volume",
    "underlying_price",
    "vol_oi_ratio",
    "fetched_at",
]

_DAILY_COLS = [
    "snapshot_date",
    "underlying",
    "underlying_price",
    "close",
    "iv30",
    "total_call_volume",
    "total_put_volume",
    "put_call_volume_ratio",
    "total_call_oi",
    "total_put_oi",
    "put_call_oi_ratio",
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
-- (1) unusual activity on each underlying's per-underlying latest snapshot:
-- contracts where today's volume dwarfs standing open interest. Works from
-- day one.
CREATE VIEW IF NOT EXISTS v_unusual_activity AS
SELECT underlying, occ_symbol, expiration, strike, type,
       volume, open_interest, vol_oi_ratio, iv, snapshot_date
FROM option_snapshots o
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM option_snapshots o2
                       WHERE o2.underlying = o.underlying AND o2.source = 'cboe')
  AND source = 'cboe'
  AND volume >= 100
  AND vol_oi_ratio >= 1.0
ORDER BY vol_oi_ratio DESC;

-- (2) IV Rank/percentile of each underlying's per-underlying latest iv30
-- within its full stored history (min-max rank + fraction-of-days-below
-- percentile). Returns meaningful values only once history accumulates
-- (needs many days).
CREATE VIEW IF NOT EXISTS v_iv_rank AS
WITH bounds AS (
  SELECT underlying, MIN(iv30) AS iv_min, MAX(iv30) AS iv_max, COUNT(*) AS n_days
  FROM underlying_daily WHERE iv30 IS NOT NULL GROUP BY underlying),
today AS (
  SELECT underlying, snapshot_date, iv30 FROM underlying_daily ud
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily u2
                         WHERE u2.underlying = ud.underlying)
    AND iv30 IS NOT NULL)
SELECT t.underlying, t.snapshot_date, t.iv30, b.iv_min, b.iv_max, b.n_days,
       CASE WHEN b.iv_max > b.iv_min
            THEN 100.0 * (t.iv30 - b.iv_min) / (b.iv_max - b.iv_min) END AS iv_rank,
       (SELECT 100.0 * COUNT(*) / b.n_days FROM underlying_daily h
         WHERE h.underlying = t.underlying AND h.iv30 < t.iv30) AS iv_percentile
FROM today t JOIN bounds b USING (underlying);

-- (3) per-underlying latest-day sentiment snapshot.
CREATE VIEW IF NOT EXISTS v_latest_sentiment AS
SELECT underlying, snapshot_date, underlying_price, iv30,
       put_call_volume_ratio, put_call_oi_ratio,
       total_call_volume, total_put_volume
FROM underlying_daily ud
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM underlying_daily u2
                       WHERE u2.underlying = ud.underlying);
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()


def upsert_underlying(conn, symbol: str, is_index: bool, date: str) -> None:
    """Upsert the underlying dimension: extend first_seen/last_seen to the
    min/max date ever seen, and keep is_index current."""
    conn.execute(
        """INSERT INTO underlyings (symbol, is_index, first_seen, last_seen)
           VALUES (:s, :i, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             is_index   = excluded.is_index,
             first_seen = MIN(underlyings.first_seen, excluded.first_seen),
             last_seen  = MAX(underlyings.last_seen,  excluded.last_seen)""",
        {"s": symbol, "i": 1 if is_index else 0, "d": date},
    )
    conn.commit()


def replace_day(
    conn, snapshot_date: str, underlying: str, rows: list, fetched_at: str, source: str = "cboe"
) -> int:
    """Delete this (snapshot_date, underlying, source)'s contract rows, then
    bulk-insert `rows`. Replace (not upsert) so a shrunk chain leaves no orphan.
    Dedupes the batch by occ_symbol. snapshot_date/source/fetched_at are stamped
    from params onto every row. Returns rows written."""
    by_key = {r["occ_symbol"]: r for r in rows}
    conn.execute(
        "DELETE FROM option_snapshots WHERE snapshot_date = ? AND underlying = ? AND source = ?",
        (snapshot_date, underlying, source),
    )
    placeholders = ", ".join(":" + c for c in _CONTRACT_COLS)
    stamp = {"snapshot_date": snapshot_date, "source": source, "fetched_at": fetched_at}
    params = [{**{c: r.get(c) for c in _CONTRACT_COLS}, **stamp} for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO option_snapshots ({', '.join(_CONTRACT_COLS)}) VALUES ({placeholders})",
        params,
    )
    conn.commit()
    return len(by_key)


def upsert_underlying_daily(conn, snapshot_date: str, daily: dict) -> None:
    """Upsert one (snapshot_date, underlying) rollup row."""
    row = {**{c: daily.get(c) for c in _DAILY_COLS}, "snapshot_date": snapshot_date}
    assignments = ", ".join(
        f"{c}=excluded.{c}" for c in _DAILY_COLS if c not in ("snapshot_date", "underlying")
    )
    placeholders = ", ".join(":" + c for c in _DAILY_COLS)
    conn.execute(
        f"INSERT INTO underlying_daily ({', '.join(_DAILY_COLS)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(snapshot_date, underlying) DO UPDATE SET {assignments}",
        row,
    )
    conn.commit()


def record_day(conn, snapshot_date: str, underlying: str, fetched_at: str, row_count: int) -> None:
    """Upsert one (snapshot_date, underlying) provenance row."""
    conn.execute(
        """INSERT INTO days (snapshot_date, underlying, fetched_at, row_count)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(snapshot_date, underlying) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (snapshot_date, underlying, fetched_at, row_count),
    )
    conn.commit()


def write_snapshot(conn, captured_at: str, symbol_count: int, row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, symbol_count, row_count) VALUES (?, ?, ?)",
        (captured_at, symbol_count, row_count),
    )
    conn.commit()
    return cur.lastrowid


def stored_symbols(conn) -> list:
    """Distinct underlyings that have at least one ingested day, sorted."""
    return [r[0] for r in conn.execute("SELECT DISTINCT underlying FROM days ORDER BY underlying")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Options history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — it must NOT cascade into option_snapshots."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)
        ).fetchall()
    ]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
