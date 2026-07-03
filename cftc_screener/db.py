from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_markets", "write_cot",
           "max_report_date", "write_snapshot", "prune"]

# The 26 curated data columns of `cot` (order matters for INSERT/UPDATE reuse).
_COT_COLS = [
    "open_interest",
    "noncomm_long", "noncomm_short", "noncomm_spread",
    "comm_long", "comm_short",
    "nonrept_long", "nonrept_short",
    "chg_oi", "chg_noncomm_long", "chg_noncomm_short",
    "chg_comm_long", "chg_comm_short",
    "pct_oi_noncomm_long", "pct_oi_noncomm_short",
    "pct_oi_comm_long", "pct_oi_comm_short",
    "traders_total", "traders_noncomm_long", "traders_noncomm_short",
    "traders_comm_long", "traders_comm_short",
    "conc_net_4_long", "conc_net_8_long", "conc_net_4_short", "conc_net_8_short",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    code        TEXT PRIMARY KEY,
    name        TEXT,
    asset_class TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS cot (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    noncomm_long  INTEGER, noncomm_short INTEGER, noncomm_spread INTEGER,
    comm_long     INTEGER, comm_short    INTEGER,
    nonrept_long  INTEGER, nonrept_short INTEGER,
    chg_oi        INTEGER,
    chg_noncomm_long INTEGER, chg_noncomm_short INTEGER,
    chg_comm_long INTEGER, chg_comm_short INTEGER,
    pct_oi_noncomm_long REAL, pct_oi_noncomm_short REAL,
    pct_oi_comm_long REAL, pct_oi_comm_short REAL,
    traders_total INTEGER,
    traders_noncomm_long INTEGER, traders_noncomm_short INTEGER,
    traders_comm_long INTEGER, traders_comm_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_date ON cot(report_date);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    market_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""


_VIEWS = """
CREATE VIEW IF NOT EXISTS v_net AS
SELECT code, report_date, open_interest,
       noncomm_long - noncomm_short AS net_noncomm,
       comm_long    - comm_short    AS net_comm,
       nonrept_long - nonrept_short AS net_nonrept
FROM cot;

CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_noncomm, r.net_comm, r.net_nonrept
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

-- COT Index: net non-commercial position as a 0-100 percentile within its own
-- trailing 156-week (3-year) range. 90+/10- = crowded long/short.
CREATE VIEW IF NOT EXISTS v_cot_index AS
WITH w AS (
    SELECT code, report_date, net_noncomm,
           MIN(net_noncomm) OVER win AS lo,
           MAX(net_noncomm) OVER win AS hi
    FROM v_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_noncomm, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_noncomm - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_noncomm, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_cot_index)
SELECT code, report_date, net_noncomm, cot_index FROM ranked WHERE rn = 1;

-- Positioning board: latest net positions, COT index, %OI, and WoW changes.
CREATE VIEW IF NOT EXISTS v_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_noncomm, l.net_comm, l.net_nonrept,
       ci.cot_index,
       c.pct_oi_noncomm_long, c.pct_oi_noncomm_short,
       c.chg_oi, c.chg_noncomm_long, c.chg_noncomm_short
FROM v_latest l
JOIN v_cot_index_latest ci ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_extremes AS
SELECT * FROM v_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and derived-signal views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()


def upsert_markets(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the market dimension: refresh name/asset_class/last_seen, preserve
    first_seen."""
    params = [{"code": r["code"], "name": r.get("name"),
               "asset_class": r.get("asset_class"), "seen": captured_at}
              for r in rows]
    conn.executemany(
        """INSERT INTO markets (code, name, asset_class, first_seen, last_seen)
           VALUES (:code, :name, :asset_class, :seen, :seen)
           ON CONFLICT(code) DO UPDATE SET
             name=excluded.name, asset_class=excluded.asset_class,
             last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_cot(conn, code: str, rows: list[dict]) -> int:
    """Upsert COT rows by (code, report_date). Revised weeks overwrite in place;
    dates never duplicated. Dedupes within the batch (last wins)."""
    by_date = {r["report_date"]: r for r in rows}
    cols = ["code", "report_date"] + _COT_COLS
    placeholders = ", ".join(":" + c for c in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _COT_COLS)
    params = []
    for date, r in by_date.items():
        p = {"code": code, "report_date": date}
        for c in _COT_COLS:
            p[c] = r.get(c)
        params.append(p)
    conn.executemany(
        f"INSERT INTO cot ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(code, report_date) DO UPDATE SET {updates}",
        params,
    )
    conn.commit()
    return len(by_date)


def max_report_date(conn, code: str):
    """Latest stored report_date for a market, or None if it has no rows."""
    row = conn.execute(
        "SELECT MAX(report_date) FROM cot WHERE code=?", (code,)).fetchone()
    return row[0] if row and row[0] else None


def write_snapshot(conn, captured_at: str, market_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, market_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, market_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    COT history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — do NOT cascade into cot."""
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
