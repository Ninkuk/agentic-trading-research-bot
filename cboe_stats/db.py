from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "write_pcr", "write_vix",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    feed_count  INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pcr_daily (
    date         TEXT PRIMARY KEY,
    total_pcr    REAL,
    equity_pcr   REAL,
    index_pcr    REAL,
    total_volume INTEGER
);
CREATE TABLE IF NOT EXISTS vix_daily (
    date  TEXT PRIMARY KEY,
    open  REAL, high REAL, low REAL, close REAL,
    vix3m REAL, vix9d REAL, vvix REAL
);
"""

# Which vix_daily columns each feed owns, and which parsed key fills them.
_VIX_MAP = {
    "VIX": {"open": "open", "high": "high", "low": "low", "close": "close"},
    "VIX3M": {"vix3m": "close"},
    "VIX9D": {"vix9d": "close"},
    "VVIX": {"vvix": "close"},
}


def ensure_schema(conn) -> None:
    """Create tables (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def write_pcr(conn, rows) -> int:
    by_date = {r["date"]: r for r in rows}
    conn.executemany(
        """INSERT INTO pcr_daily (date, total_pcr, equity_pcr, index_pcr,
                                  total_volume)
           VALUES (:date, :total_pcr, :equity_pcr, :index_pcr, :total_volume)
           ON CONFLICT(date) DO UPDATE SET
             total_pcr=excluded.total_pcr, equity_pcr=excluded.equity_pcr,
             index_pcr=excluded.index_pcr, total_volume=excluded.total_volume""",
        list(by_date.values()))
    conn.commit()
    return len(by_date)


def write_vix(conn, feed_id, rows) -> int:
    """Column-merge upsert: write only this feed's columns onto the date row, so a
    partial run never blanks a sibling column. Unknown feed (e.g. --add RVX with
    no column) is a no-op."""
    mapping = _VIX_MAP.get(feed_id)
    if not mapping:
        return 0
    cols = list(mapping)                          # vix_daily columns this feed owns
    by_date = {r["date"]: r for r in rows}
    params = [tuple([d] + [r.get(mapping[c]) for c in cols])
              for d, r in by_date.items()]
    collist = ", ".join(["date"] + cols)
    ph = ", ".join(["?"] * (1 + len(cols)))
    setc = ", ".join(f"{c}=excluded.{c}" for c in cols)
    conn.executemany(
        f"INSERT INTO vix_daily ({collist}) VALUES ({ph}) "
        f"ON CONFLICT(date) DO UPDATE SET {setc}", params)
    conn.commit()
    return len(by_date)


def write_snapshot(conn, captured_at, feed_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, feed_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, feed_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. pcr_daily/vix_daily are the
    accumulated history and are NEVER cascade-pruned (FRED prune shape)."""
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
-- Latest put/call vs its trailing percentile, with a contrarian flag.
CREATE VIEW IF NOT EXISTS v_pcr_extremes AS
WITH latest AS (SELECT * FROM pcr_daily ORDER BY date DESC LIMIT 1)
SELECT l.date, l.total_pcr, l.equity_pcr,
       (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
        WHERE equity_pcr IS NOT NULL) AS equity_pcr_pctile,
       CASE
         WHEN (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
               WHERE equity_pcr IS NOT NULL) >= 0.8 THEN 'fear'
         WHEN (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
               WHERE equity_pcr IS NOT NULL) <= 0.2 THEN 'complacency'
         ELSE 'neutral' END AS equity_flag
FROM latest l;

-- Latest VIX vs VIX3M term structure (backwardation = stress).
CREATE VIEW IF NOT EXISTS v_vix_term_structure AS
WITH latest AS (
    SELECT * FROM vix_daily WHERE close IS NOT NULL ORDER BY date DESC LIMIT 1
)
SELECT date, close, vix3m,
       CASE WHEN vix3m IS NOT NULL AND vix3m <> 0 THEN close / vix3m END
         AS vix_vix3m_ratio,
       CASE WHEN vix3m IS NULL THEN NULL WHEN close > vix3m THEN 1 ELSE 0 END
         AS backwardation
FROM latest;

-- One-row at-a-glance sentiment readout.
CREATE VIEW IF NOT EXISTS v_latest_sentiment AS
SELECT
  (SELECT date FROM vix_daily WHERE close IS NOT NULL
   ORDER BY date DESC LIMIT 1) AS vix_date,
  (SELECT close FROM vix_daily WHERE close IS NOT NULL
   ORDER BY date DESC LIMIT 1) AS vix_close,
  (SELECT date FROM pcr_daily ORDER BY date DESC LIMIT 1) AS pcr_date,
  (SELECT equity_pcr FROM pcr_daily ORDER BY date DESC LIMIT 1) AS equity_pcr,
  (SELECT total_pcr FROM pcr_daily ORDER BY date DESC LIMIT 1) AS total_pcr,
  (SELECT backwardation FROM v_vix_term_structure) AS backwardation;
"""
