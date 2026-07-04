from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_companies", "write_facts",
           "write_snapshot", "prune"]

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

_FACT_COLS = ("tag", "uom", "period_end", "fiscal_year", "fiscal_period",
              "value", "form", "filed", "accession")


def ensure_schema(conn) -> None:
    """Create companies/facts/snapshots + indexes (+ views from _VIEWS). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_companies(conn, rows: list, captured_at: str) -> None:
    """Upsert the company dimension: refresh ticker/name/sic/last_seen, preserve
    first_seen (FRED upsert_series shape)."""
    params = [{"cik": r["cik"], "ticker": r.get("ticker"), "name": r.get("name"),
               "sic": r.get("sic"), "seen": captured_at} for r in rows]
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
    params = [(cik, r["tag"], r.get("uom"), r["period_end"], r.get("fiscal_year"),
               r.get("fiscal_period"), r.get("value"), r["form"], r.get("filed"),
               r.get("accession")) for r in by_key.values()]
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


def write_snapshot(conn, captured_at: str, company_count: int,
                   fact_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, company_count, fact_count) "
        "VALUES (?, ?, ?)", (captured_at, company_count, fact_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Single-table delete only — facts are the historical store and are NEVER
    cascade-pruned (FRED prune shape, NOT the screener_common cascade)."""
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


# Views are defined in Task 4; start with an empty string so ensure_schema works
# now and gains the views when Task 4 fills this in.
_VIEWS = ""
