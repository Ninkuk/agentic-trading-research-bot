from screener_common import connect, prune as _prune

__all__ = ["connect", "ensure_schema", "prune"]

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
