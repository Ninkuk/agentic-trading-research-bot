from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_venues", "replace_week",
           "record_week", "write_snapshot", "stored_weeks", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS venues (
    mpid       TEXT PRIMARY KEY,
    ats_name   TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS ats_volume (
    week_start     TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    mpid           TEXT NOT NULL REFERENCES venues(mpid),
    trade_count    INTEGER,
    share_quantity INTEGER,
    tier           TEXT,
    PRIMARY KEY (week_start, symbol, mpid)
);
CREATE INDEX IF NOT EXISTS ix_ats_week   ON ats_volume(week_start);
CREATE INDEX IF NOT EXISTS ix_ats_symbol ON ats_volume(symbol);
CREATE TABLE IF NOT EXISTS weeks (
    week_start TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    week_count  INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables/indexes (+ views from Task 3). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_venues(conn, rows) -> None:
    """Upsert the mpid dimension: newest ats_name, widen first/last_seen."""
    agg = {}
    for r in rows:
        mp, w = r["mpid"], r["week_start"]
        cur = agg.get(mp)
        if cur is None:
            agg[mp] = {"mpid": mp, "ats_name": r.get("ats_name"),
                       "first": w, "last": w}
        else:
            if r.get("ats_name"):
                cur["ats_name"] = r["ats_name"]
            cur["first"] = min(cur["first"], w)
            cur["last"] = max(cur["last"], w)
    conn.executemany(
        """INSERT INTO venues (mpid, ats_name, first_seen, last_seen)
           VALUES (:mpid, :ats_name, :first, :last)
           ON CONFLICT(mpid) DO UPDATE SET
             ats_name=COALESCE(excluded.ats_name, venues.ats_name),
             first_seen=min(venues.first_seen, excluded.first_seen),
             last_seen=max(venues.last_seen, excluded.last_seen)""",
        list(agg.values()))
    conn.commit()


def replace_week(conn, week_start, rows) -> int:
    """Delete the week's rows then bulk-insert (dedupe by full key). A re-post
    that drops a venue leaves no orphan."""
    by_key = {(r["week_start"], r["symbol"], r["mpid"]): r for r in rows}
    conn.execute("DELETE FROM ats_volume WHERE week_start=?", (week_start,))
    conn.executemany(
        """INSERT INTO ats_volume
           (week_start, symbol, mpid, trade_count, share_quantity, tier)
           VALUES (:week_start, :symbol, :mpid, :trade_count, :share_quantity,
                   :tier)""", list(by_key.values()))
    conn.commit()
    return len(by_key)


def record_week(conn, week_start, fetched_at, row_count) -> None:
    conn.execute(
        """INSERT INTO weeks (week_start, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(week_start) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (week_start, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at, week_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, week_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, week_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_weeks(conn) -> list:
    return [r[0] for r in conn.execute(
        "SELECT week_start FROM weeks ORDER BY week_start")]


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots only. ats_volume is the store and is
    NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})",
                 ids)
    conn.commit()
    return len(ids)


_VIEWS = """
-- Off-exchange totals per symbol for the newest stored week.
CREATE VIEW IF NOT EXISTS v_latest_off_exchange AS
SELECT a.symbol,
       SUM(a.share_quantity) AS total_shares,
       SUM(a.trade_count)    AS total_trades,
       COUNT(DISTINCT a.mpid) AS venue_count
FROM ats_volume a
WHERE a.week_start = (SELECT MAX(week_start) FROM ats_volume)
GROUP BY a.symbol
ORDER BY total_shares DESC;

-- Biggest dark pools this (newest) week, with the ATS name.
CREATE VIEW IF NOT EXISTS v_top_dark_pools AS
SELECT a.mpid, v.ats_name,
       SUM(a.share_quantity) AS total_shares,
       SUM(a.trade_count)    AS total_trades
FROM ats_volume a
LEFT JOIN venues v ON v.mpid = a.mpid
WHERE a.week_start = (SELECT MAX(week_start) FROM ats_volume)
GROUP BY a.mpid, v.ats_name
ORDER BY total_shares DESC;

-- Per-(symbol, venue) weekly time series.
CREATE VIEW IF NOT EXISTS v_symbol_venue_history AS
SELECT a.symbol, a.mpid, v.ats_name, a.week_start, a.trade_count,
       a.share_quantity
FROM ats_volume a
LEFT JOIN venues v ON v.mpid = a.mpid
ORDER BY a.symbol, a.mpid, a.week_start;
"""
