from screener_common import connect, prune as _prune

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    filter       TEXT NOT NULL,
    ticker_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    snapshot_id      INTEGER NOT NULL REFERENCES snapshots(id),
    ticker           TEXT NOT NULL,
    name             TEXT,
    rank             INTEGER,
    mentions         INTEGER,
    upvotes          INTEGER,
    rank_24h_ago     INTEGER,
    mentions_24h_ago INTEGER,
    PRIMARY KEY (snapshot_id, ticker)
);
CREATE INDEX IF NOT EXISTS ix_observations_ticker ON observations(ticker);
CREATE TABLE IF NOT EXISTS tickers (
    ticker     TEXT PRIMARY KEY,
    name       TEXT,
    asset_type TEXT,
    first_seen TEXT,
    last_seen  TEXT
);

-- Most recent snapshot per filter, joined to its observations.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT id, filter, captured_at,
           ROW_NUMBER() OVER (PARTITION BY filter
                              ORDER BY captured_at DESC, id DESC) AS rn
    FROM snapshots
)
SELECT r.filter, r.captured_at, o.ticker, o.name, o.rank, o.mentions,
       o.upvotes, o.rank_24h_ago, o.mentions_24h_ago
FROM ranked r
JOIN observations o ON o.snapshot_id = r.id
WHERE r.rn = 1;

-- Latest rows enriched with derived signals (NULL-guarded denominators).
CREATE VIEW IF NOT EXISTS v_signals AS
SELECT *,
    mentions - mentions_24h_ago AS mention_delta,
    CASE WHEN mentions_24h_ago IS NULL OR mentions_24h_ago = 0 THEN NULL
         ELSE (mentions - mentions_24h_ago) * 1.0 / mentions_24h_ago END
        AS mention_pct_change,
    rank_24h_ago - rank AS rank_delta,
    CASE WHEN mentions IS NULL OR mentions = 0 THEN NULL
         ELSE upvotes * 1.0 / mentions END AS upvote_ratio
FROM v_latest;

-- Biggest mention movers first.
CREATE VIEW IF NOT EXISTS v_trending AS
SELECT * FROM v_signals
WHERE mention_pct_change IS NOT NULL
ORDER BY mention_pct_change DESC;

-- Per-ticker time-series with deltas between consecutive stored snapshots.
CREATE VIEW IF NOT EXISTS v_history AS
SELECT o.ticker, s.filter, s.captured_at, o.rank, o.mentions, o.upvotes,
    o.mentions - LAG(o.mentions) OVER w AS mention_delta_since_last,
    LAG(o.rank) OVER w - o.rank AS rank_delta_since_last
FROM observations o
JOIN snapshots s ON s.id = o.snapshot_id
WINDOW w AS (PARTITION BY o.ticker, s.filter
             ORDER BY s.captured_at, o.snapshot_id);
"""


def ensure_schema(conn) -> None:
    """Create tables and derived-signal views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def write_snapshot(conn, captured_at: str, filter_: str,
                   rows: list[dict]) -> tuple[int, int]:
    """Insert one snapshot header + its observation rows. Returns (id, count)."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, filter, ticker_count) VALUES (?, ?, ?)",
        (captured_at, filter_, len(rows)),
    )
    snapshot_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO observations
           (snapshot_id, ticker, name, rank, mentions, upvotes,
            rank_24h_ago, mentions_24h_ago)
           VALUES (:sid, :ticker, :name, :rank, :mentions, :upvotes,
                   :rank_24h_ago, :mentions_24h_ago)""",
        [{**r, "sid": snapshot_id} for r in rows],
    )
    conn.commit()
    return snapshot_id, len(rows)


def _asset_type(ticker: str) -> str:
    return "crypto" if ticker.endswith(".X") else "stock"


def upsert_tickers(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the ticker dimension: refresh name/last_seen, preserve first_seen."""
    conn.executemany(
        """INSERT INTO tickers (ticker, name, asset_type, first_seen, last_seen)
           VALUES (:ticker, :name, :asset_type, :seen, :seen)
           ON CONFLICT(ticker) DO UPDATE SET
             name=excluded.name,
             asset_type=excluded.asset_type,
             last_seen=excluded.last_seen""",
        [{"ticker": r["ticker"], "name": r["name"],
          "asset_type": _asset_type(r["ticker"]), "seen": captured_at}
         for r in rows],
    )
    conn.commit()


def prune(conn, keep_days, now_iso):
    """Prune reddit snapshots + observations. Delegates to the shared helper."""
    return _prune(conn, keep_days, now_iso, child_table="observations")
