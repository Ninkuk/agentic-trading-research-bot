# finra_short_volume/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities", "replace_day",
           "record_day", "write_snapshot", "stored_days", "prune"]

_SV_COLS = ["symbol", "date", "short_volume", "short_exempt_volume",
            "total_volume", "short_ratio", "market"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    symbol     TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS short_volume (
    symbol              TEXT NOT NULL REFERENCES securities(symbol),
    date                TEXT NOT NULL,
    short_volume        INTEGER NOT NULL,
    short_exempt_volume INTEGER,
    total_volume        INTEGER NOT NULL,
    short_ratio         REAL,
    market              TEXT,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS ix_sv_date   ON short_volume(date);
CREATE INDEX IF NOT EXISTS ix_sv_symbol ON short_volume(symbol);
CREATE TABLE IF NOT EXISTS days (
    date       TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    day_count   INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
"""

_VIEWS = """
-- per-symbol time series (drill-down)
CREATE VIEW IF NOT EXISTS v_symbol_history AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume;

-- (1) latest-day leaderboard, liquid names only (order by short_ratio or volume)
CREATE VIEW IF NOT EXISTS v_latest AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume
WHERE date = (SELECT MAX(date) FROM short_volume)
  AND total_volume >= 100000;

-- (2) heavy short participation on the latest day
CREATE VIEW IF NOT EXISTS v_high_short_ratio AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume
WHERE date = (SELECT MAX(date) FROM short_volume)
  AND total_volume >= 100000
  AND short_ratio >= 0.50;

-- (3) latest short_ratio vs the symbol's trailing 20-day average (excl. today)
CREATE VIEW IF NOT EXISTS v_ratio_spikes AS
WITH w AS (
  SELECT symbol, date, short_ratio, total_volume,
         AVG(short_ratio) OVER (PARTITION BY symbol ORDER BY date
                                ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS base
  FROM short_volume)
SELECT w.symbol, w.date, w.short_ratio, w.total_volume, w.base,
       CASE WHEN w.base > 0 THEN w.short_ratio / w.base END AS spike_ratio
FROM w
WHERE w.date = (SELECT MAX(date) FROM short_volume)
  AND w.total_volume >= 100000
  AND w.base > 0;

-- global dense rank of distinct trading days (trading days are not contiguous
-- calendar days; this ordinal defines "consecutive")
CREATE VIEW IF NOT EXISTS v_date_rank AS
SELECT date, DENSE_RANK() OVER (ORDER BY date) AS drank
FROM (SELECT DISTINCT date FROM short_volume);

-- (4) gaps-and-islands: one row per (symbol, unbroken run of elevated days)
CREATE VIEW IF NOT EXISTS v_short_streaks AS
WITH q AS (
  SELECT sv.symbol, sv.date, sv.short_ratio, dr.drank,
         dr.drank - ROW_NUMBER() OVER (PARTITION BY sv.symbol
                                       ORDER BY sv.date) AS grp
  FROM short_volume sv JOIN v_date_rank dr USING (date)
  WHERE sv.total_volume >= 100000 AND sv.short_ratio >= 0.50)
SELECT symbol, COUNT(*) AS streak_days,
       MIN(date) AS streak_start, MAX(date) AS streak_end,
       MAX(short_ratio) AS peak_ratio,
       (MAX(date) = (SELECT MAX(date) FROM short_volume)) AS active
FROM q GROUP BY symbol, grp;
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the symbol dimension: extend first_seen/last_seen to the min/max
    date ever seen for each symbol."""
    params = [{"symbol": r["symbol"], "d": r["date"]} for r in rows]
    conn.executemany(
        """INSERT INTO securities (symbol, first_seen, last_seen)
           VALUES (:symbol, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen)""",
        params,
    )
    conn.commit()


def replace_day(conn, date: str, rows: list[dict]) -> int:
    """Delete all short_volume rows for this date, then bulk-insert the given
    rows. Replace (not upsert) so a FINRA file repost that drops a row leaves no
    orphan. Dedupes within the batch by (symbol, date). Returns rows written."""
    by_key = {(r["symbol"], r["date"]): r for r in rows}
    conn.execute("DELETE FROM short_volume WHERE date = ?", (date,))
    placeholders = ", ".join(":" + c for c in _SV_COLS)
    params = [{c: r.get(c) for c in _SV_COLS} for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO short_volume ({', '.join(_SV_COLS)}) VALUES ({placeholders})",
        params,
    )
    conn.commit()
    return len(by_key)


def record_day(conn, date: str, fetched_at: str, row_count: int) -> None:
    """Upsert one day's provenance row."""
    conn.execute(
        """INSERT INTO days (date, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (date, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, day_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, day_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, day_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_days(conn) -> list:
    """All ingested dates, sorted ascending (ISO dates sort chronologically)."""
    return [r[0] for r in conn.execute("SELECT date FROM days ORDER BY date")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Short-volume history is NOT snapshot-scoped, so this is a single-table delete
    of snapshot headers only — it must NOT cascade into short_volume."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
