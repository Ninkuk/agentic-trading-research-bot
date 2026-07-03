from screener_common import connect, prune as _prune

__all__ = ["connect", "ensure_schema", "prune", "write_snapshot", "upsert_issuers"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    index_date   TEXT NOT NULL,
    filing_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS filings (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    accession   TEXT NOT NULL,
    cik         INTEGER NOT NULL,
    company     TEXT,
    ticker      TEXT,
    form        TEXT NOT NULL,
    bucket      TEXT NOT NULL,
    filed_date  TEXT NOT NULL,
    path        TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, accession, cik)
);
CREATE INDEX IF NOT EXISTS ix_filings_ticker ON filings(ticker);
CREATE INDEX IF NOT EXISTS ix_filings_bucket ON filings(bucket);
CREATE TABLE IF NOT EXISTS issuers (
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,
    company    TEXT,
    first_seen TEXT,
    last_seen  TEXT
);

-- Every filing from the most recent snapshot.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH latest AS (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1
)
SELECT f.* FROM filings f JOIN latest l ON f.snapshot_id = l.id;

-- Latest filings from tickered (tradeable) issuers only.
CREATE VIEW IF NOT EXISTS v_tickered AS
SELECT * FROM v_latest WHERE ticker IS NOT NULL;

-- Insider (Form 4) filing count per ticker -> cluster detection.
CREATE VIEW IF NOT EXISTS v_insider_activity AS
SELECT ticker, company, COUNT(*) AS insider_filings
FROM v_tickered WHERE bucket = 'insider'
GROUP BY ticker, company
ORDER BY insider_filings DESC;

-- Latest material-event (8-K) filings per ticker.
CREATE VIEW IF NOT EXISTS v_events AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'event';

-- Latest activist/large-stake (13D/13G) filings.
CREATE VIEW IF NOT EXISTS v_stakes AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'stake';

-- Latest IPO / offering (S-1, 424B) filings.
CREATE VIEW IF NOT EXISTS v_offerings AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'offering';

-- Filings-per-ticker across index dates, with delta vs the prior stored day.
CREATE VIEW IF NOT EXISTS v_activity_history AS
WITH per_day AS (
    SELECT f.ticker AS ticker, s.index_date AS index_date,
           COUNT(*) AS filings_count
    FROM filings f JOIN snapshots s ON s.id = f.snapshot_id
    WHERE f.ticker IS NOT NULL
    GROUP BY f.ticker, s.index_date
)
SELECT ticker, index_date, filings_count,
       filings_count - LAG(filings_count) OVER (
           PARTITION BY ticker ORDER BY index_date) AS filings_delta_since_last
FROM per_day;
"""


def ensure_schema(conn) -> None:
    """Create tables + ELT views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def prune(conn, keep_days, now_iso):
    """Prune edgar snapshots + filings. Delegates to the shared helper."""
    return _prune(conn, keep_days, now_iso, child_table="filings")


def write_snapshot(conn, captured_at: str, index_date: str,
                   rows: list[dict]) -> tuple[int, int]:
    """Insert one snapshot header + its filing rows. Returns (id, count).

    The SEC master.idx daily index sometimes repeats the exact same filing
    line more than once. A filing is uniquely identified by
    (accession, cik), so duplicate lines are collapsed to a single stored
    row (first occurrence wins) before insert and counting.
    """
    seen = set()
    deduped = []
    for r in rows:
        key = (r["accession"], r["cik"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, index_date, filing_count) "
        "VALUES (?, ?, ?)",
        (captured_at, index_date, len(deduped)),
    )
    snapshot_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO filings
           (snapshot_id, accession, cik, company, ticker, form, bucket,
            filed_date, path)
           VALUES (:sid, :accession, :cik, :company, :ticker, :form, :bucket,
                   :filed_date, :path)""",
        [{**r, "sid": snapshot_id} for r in deduped],
    )
    conn.commit()
    return snapshot_id, len(deduped)


def upsert_issuers(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the issuer dimension: refresh ticker/company/last_seen, keep
    first_seen. Dedupes by CIK within the batch."""
    seen = {}
    for r in rows:
        seen[r["cik"]] = (r.get("ticker"), r["company"])
    conn.executemany(
        """INSERT INTO issuers (cik, ticker, company, first_seen, last_seen)
           VALUES (:cik, :ticker, :company, :seen, :seen)
           ON CONFLICT(cik) DO UPDATE SET
             ticker=excluded.ticker,
             company=excluded.company,
             last_seen=excluded.last_seen""",
        [{"cik": c, "ticker": t, "company": n, "seen": captured_at}
         for c, (t, n) in seen.items()],
    )
    conn.commit()
