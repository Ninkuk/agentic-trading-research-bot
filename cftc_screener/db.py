from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_markets", "write_cot",
           "write_family", "max_report_date", "write_snapshot", "prune"]

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

CREATE TABLE IF NOT EXISTS cot_disagg (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    prod_merc_long INTEGER, prod_merc_short INTEGER,
    swap_long INTEGER, swap_short INTEGER, swap_spread INTEGER,
    mm_long INTEGER, mm_short INTEGER, mm_spread INTEGER,
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    chg_oi INTEGER, chg_mm_long INTEGER, chg_mm_short INTEGER,
    chg_swap_long INTEGER, chg_swap_short INTEGER,
    pct_oi_mm_long REAL, pct_oi_mm_short REAL,
    pct_oi_swap_long REAL, pct_oi_swap_short REAL,
    traders_total INTEGER, traders_mm_long INTEGER, traders_mm_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_disagg_date ON cot_disagg(report_date);

CREATE TABLE IF NOT EXISTS cot_tff (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    dealer_long INTEGER, dealer_short INTEGER, dealer_spread INTEGER,
    asset_mgr_long INTEGER, asset_mgr_short INTEGER, asset_mgr_spread INTEGER,
    lev_long INTEGER, lev_short INTEGER, lev_spread INTEGER,
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    chg_oi INTEGER, chg_lev_long INTEGER, chg_lev_short INTEGER,
    chg_asset_mgr_long INTEGER, chg_asset_mgr_short INTEGER,
    pct_oi_lev_long REAL, pct_oi_lev_short REAL,
    pct_oi_asset_mgr_long REAL, pct_oi_asset_mgr_short REAL,
    traders_total INTEGER, traders_lev_long INTEGER, traders_lev_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_tff_date ON cot_tff(report_date);

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


_DISAGG_VIEWS = """
CREATE VIEW IF NOT EXISTS v_disagg_net AS
SELECT code, report_date, open_interest,
       mm_long - mm_short                 AS net_mm,        -- managed money (spec gauge)
       swap_long - swap_short             AS net_swap,
       prod_merc_long - prod_merc_short   AS net_prod_merc,
       other_rept_long - other_rept_short AS net_other
FROM cot_disagg;

CREATE VIEW IF NOT EXISTS v_disagg_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_disagg_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_mm, r.net_swap, r.net_prod_merc, r.net_other
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

CREATE VIEW IF NOT EXISTS v_disagg_cot_index AS
WITH w AS (
    SELECT code, report_date, net_mm,
           MIN(net_mm) OVER win AS lo,
           MAX(net_mm) OVER win AS hi
    FROM v_disagg_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_mm, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_mm - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_disagg_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_mm, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_disagg_cot_index)
SELECT code, report_date, net_mm, cot_index FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_disagg_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_mm, l.net_swap, l.net_prod_merc, l.net_other,
       ci.cot_index,
       c.pct_oi_mm_long, c.pct_oi_mm_short,
       c.chg_oi, c.chg_mm_long, c.chg_mm_short
FROM v_disagg_latest l
JOIN v_disagg_cot_index_latest ci
  ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot_disagg c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_managed_money_extremes AS
SELECT * FROM v_disagg_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""

_TFF_VIEWS = """
CREATE VIEW IF NOT EXISTS v_tff_net AS
SELECT code, report_date, open_interest,
       lev_long - lev_short               AS net_lev,       -- leveraged funds (spec gauge)
       asset_mgr_long - asset_mgr_short   AS net_asset_mgr,
       dealer_long - dealer_short         AS net_dealer,
       other_rept_long - other_rept_short AS net_other
FROM cot_tff;

CREATE VIEW IF NOT EXISTS v_tff_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_tff_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_lev, r.net_asset_mgr, r.net_dealer, r.net_other
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

CREATE VIEW IF NOT EXISTS v_tff_cot_index AS
WITH w AS (
    SELECT code, report_date, net_lev,
           MIN(net_lev) OVER win AS lo,
           MAX(net_lev) OVER win AS hi
    FROM v_tff_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_lev, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_lev - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_tff_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_lev, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_tff_cot_index)
SELECT code, report_date, net_lev, cot_index FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_leveraged_funds_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_lev, l.net_asset_mgr, l.net_dealer, l.net_other,
       ci.cot_index,
       c.pct_oi_lev_long, c.pct_oi_lev_short,
       c.chg_oi, c.chg_lev_long, c.chg_lev_short
FROM v_tff_latest l
JOIN v_tff_cot_index_latest ci
  ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot_tff c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_leveraged_funds_extremes AS
SELECT * FROM v_leveraged_funds_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and derived-signal views for every family.
    Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.executescript(_DISAGG_VIEWS)
    conn.executescript(_TFF_VIEWS)
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


def _upsert_facts(conn, table: str, cols: list, code: str, rows: list) -> int:
    """Upsert rows into ``table`` by (code, report_date) over ``cols``. Revised
    weeks overwrite in place; dates never duplicated. Dedupes within the batch
    (last wins). ``table`` is a trusted internal name (a family fact table)."""
    by_date = {r["report_date"]: r for r in rows}
    allcols = ["code", "report_date"] + cols
    placeholders = ", ".join(":" + c for c in allcols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    params = []
    for date, r in by_date.items():
        p = {"code": code, "report_date": date}
        for c in cols:
            p[c] = r.get(c)
        params.append(p)
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(allcols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(code, report_date) DO UPDATE SET {updates}",
        params,
    )
    conn.commit()
    return len(by_date)


def write_cot(conn, code: str, rows: list[dict]) -> int:
    """Upsert legacy COT rows into `cot`. Back-compat wrapper over _upsert_facts."""
    return _upsert_facts(conn, "cot", _COT_COLS, code, rows)


def write_family(conn, family, code: str, rows: list[dict]) -> int:
    """Upsert one market's rows into ``family.fact_table``, over the db columns
    derived from ``family.field_map``. Same (code, report_date) upsert semantics
    as write_cot."""
    cols = [c for c, _api, _cast in family.field_map]
    return _upsert_facts(conn, family.fact_table, cols, code, rows)


def max_report_date(conn, code: str, fact_table: str = "cot"):
    """Latest stored report_date for a market in ``fact_table``, or None. The
    optional ``fact_table`` keeps the legacy 2-arg call working."""
    row = conn.execute(
        f"SELECT MAX(report_date) FROM {fact_table} WHERE code=?",
        (code,)).fetchone()
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
