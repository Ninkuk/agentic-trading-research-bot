from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_companies", "write_facts", "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,
    company_count INTEGER NOT NULL,
    fact_count    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS companies (
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,
    name       TEXT,
    sic        TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS facts (
    cik           INTEGER NOT NULL REFERENCES companies(cik),
    tag           TEXT    NOT NULL,
    uom           TEXT,
    period_end    TEXT    NOT NULL,
    fiscal_year   INTEGER,
    fiscal_period TEXT,
    value         REAL,
    form          TEXT    NOT NULL,
    filed         TEXT,
    accession     TEXT,
    PRIMARY KEY (cik, tag, period_end, form)
);
CREATE INDEX IF NOT EXISTS ix_facts_tag_period ON facts(tag, period_end);
CREATE INDEX IF NOT EXISTS ix_facts_cik        ON facts(cik);
"""

_FACT_COLS = (
    "tag",
    "uom",
    "period_end",
    "fiscal_year",
    "fiscal_period",
    "value",
    "form",
    "filed",
    "accession",
)


def ensure_schema(conn) -> None:
    """Create companies/facts/snapshots + indexes (+ views from _VIEWS). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_companies(conn, rows: list, captured_at: str) -> None:
    """Upsert the company dimension: refresh ticker/name/sic/last_seen, preserve
    first_seen (FRED upsert_series shape)."""
    params = [
        {
            "cik": r["cik"],
            "ticker": r.get("ticker"),
            "name": r.get("name"),
            "sic": r.get("sic"),
            "seen": captured_at,
        }
        for r in rows
    ]
    conn.executemany(
        """INSERT INTO companies (cik, ticker, name, sic, first_seen, last_seen)
           VALUES (:cik, :ticker, :name, :sic, :seen, :seen)
           ON CONFLICT(cik) DO UPDATE SET
             ticker=excluded.ticker, name=excluded.name, sic=excluded.sic,
             last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_facts(conn, cik: int, rows: list) -> int:
    """Upsert facts by (cik, tag, period_end, form): a revised value overwrites
    in place; a different form for the same period is a new row (v_revisions).
    Dedupes within the batch (last wins). Returns distinct rows written."""
    by_key = {(r["tag"], r["period_end"], r["form"]): r for r in rows}
    params = [
        (
            cik,
            r["tag"],
            r.get("uom"),
            r["period_end"],
            r.get("fiscal_year"),
            r.get("fiscal_period"),
            r.get("value"),
            r["form"],
            r.get("filed"),
            r.get("accession"),
        )
        for r in by_key.values()
    ]
    conn.executemany(
        f"""INSERT INTO facts (cik, {", ".join(_FACT_COLS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cik, tag, period_end, form) DO UPDATE SET
              uom=excluded.uom, fiscal_year=excluded.fiscal_year,
              fiscal_period=excluded.fiscal_period, value=excluded.value,
              filed=excluded.filed, accession=excluded.accession""",
        params,
    )
    conn.commit()
    return len(params)


def write_snapshot(conn, captured_at: str, company_count: int, fact_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, company_count, fact_count) VALUES (?, ?, ?)",
        (captured_at, company_count, fact_count),
    )
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Single-table delete only — facts are the historical store and are NEVER
    cascade-pruned (FRED prune shape, NOT the screener_common cascade)."""
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


_VIEWS = """
-- Newest reported value per (cik, tag), joined to the company label.
CREATE VIEW IF NOT EXISTS v_latest_fundamentals AS
WITH ranked AS (
    SELECT f.*, ROW_NUMBER() OVER (
               PARTITION BY f.cik, f.tag
               ORDER BY f.period_end DESC, f.filed DESC) AS rn
    FROM facts f
)
SELECT r.cik, c.ticker, c.name, r.tag, r.uom, r.period_end,
       r.fiscal_year, r.fiscal_period, r.value, r.form, r.filed
FROM ranked r JOIN companies c ON c.cik = r.cik
WHERE r.rn = 1;

-- All filers' values for one tag+period (caller filters tag/period_end).
CREATE VIEW IF NOT EXISTS v_frame_cross_section AS
SELECT f.tag, f.period_end, f.cik, c.ticker, c.name, f.uom, f.value,
       f.fiscal_year, f.fiscal_period, f.form, f.filed
FROM facts f JOIN companies c ON c.cik = f.cik
ORDER BY f.tag, f.period_end, f.value DESC;

-- Pivoted headline metrics per company + ratios derived live from raw facts.
CREATE VIEW IF NOT EXISTS v_screener AS
WITH pivoted AS (
    SELECT l.cik, MAX(l.ticker) AS ticker, MAX(l.name) AS name,
      MAX(CASE WHEN l.tag IN ('Revenues',
             'RevenueFromContractWithCustomerExcludingAssessedTax')
          THEN l.value END) AS revenues,
      MAX(CASE WHEN l.tag='NetIncomeLoss' THEN l.value END) AS net_income,
      MAX(CASE WHEN l.tag='Assets' THEN l.value END) AS assets,
      MAX(CASE WHEN l.tag='Liabilities' THEN l.value END) AS liabilities,
      MAX(CASE WHEN l.tag='StockholdersEquity' THEN l.value END) AS equity,
      MAX(CASE WHEN l.tag='CommonStockSharesOutstanding' THEN l.value END) AS shares,
      MAX(CASE WHEN l.tag='EarningsPerShareDiluted' THEN l.value END) AS eps_diluted
    FROM v_latest_fundamentals l GROUP BY l.cik
)
SELECT p.cik, p.ticker, p.name, p.revenues, p.net_income, p.assets,
       p.liabilities, p.equity, p.shares, p.eps_diluted,
       CASE WHEN p.revenues IS NOT NULL AND p.revenues <> 0
            THEN p.net_income / p.revenues END AS net_margin,
       CASE WHEN p.equity IS NOT NULL AND p.equity <> 0
            THEN p.net_income / p.equity END AS roe,
       CASE WHEN p.equity IS NOT NULL AND p.equity <> 0
            THEN p.liabilities / p.equity END AS debt_to_equity
FROM pivoted p;

-- Restatements: a (cik, tag, period_end) reported under >1 form, with the delta.
CREATE VIEW IF NOT EXISTS v_revisions AS
WITH multi AS (
    SELECT cik, tag, period_end FROM facts
    GROUP BY cik, tag, period_end HAVING COUNT(*) > 1
),
seq AS (
    SELECT f.cik, f.tag, f.period_end, f.form, f.filed, f.value,
           f.value - LAG(f.value) OVER (
               PARTITION BY f.cik, f.tag, f.period_end
               ORDER BY f.filed) AS value_delta
    FROM facts f JOIN multi m
      ON m.cik=f.cik AND m.tag=f.tag AND m.period_end=f.period_end
)
SELECT s.cik, c.ticker, s.tag, s.period_end, s.form, s.filed, s.value,
       s.value_delta
FROM seq s JOIN companies c ON c.cik = s.cik
ORDER BY s.cik, s.tag, s.period_end, s.filed;
"""
