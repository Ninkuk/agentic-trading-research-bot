"""orders.db: the buy-order queue, execution-run headers, and the append-only
broker placement record. NOT snapshot-scoped and never pruned — queue rows
are human decisions (same never-prune rule as scorer.db decisions) and the
whole DB is tiny. The queued→planned flip happens only inside plan's single
BEGIN IMMEDIATE transaction (see run.py) — that atomic claim, plus the
per-order ref_id the broker deduplicates on, is the double-buy guard."""

import sqlite3

__all__ = ["connect", "ensure_schema"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queue (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol            TEXT NOT NULL,
    qty               INTEGER NOT NULL CHECK (qty > 0),
    ref_price         REAL NOT NULL CHECK (ref_price >= 1.0),
    max_gap_pct       REAL NOT NULL CHECK (max_gap_pct >= 0),
    expires_on        TEXT NOT NULL,          -- Phoenix date
    note              TEXT,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
        ('queued','planned','placed','vetoed','expired','failed')),
    ref_id            TEXT UNIQUE,            -- minted at claim time
    planned_limit     TEXT,                   -- decimal string, set at claim time
    queued_at         TEXT NOT NULL,          -- UTC isoformat
    resolved_at       TEXT,
    resolution_reason TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    phase       TEXT NOT NULL CHECK (phase IN ('preflight','plan','record','reconcile')),
    detail      TEXT
);

CREATE TABLE IF NOT EXISTS placements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id       INTEGER NOT NULL REFERENCES queue(id),
    run_id         INTEGER NOT NULL REFERENCES runs(id),
    ref_id         TEXT NOT NULL,
    account_number TEXT NOT NULL,
    limit_price    TEXT NOT NULL,             -- decimal string, as sent
    order_id       TEXT,
    outcome        TEXT NOT NULL CHECK (outcome IN ('placed','error')),
    confirmed_at   TEXT,                      -- set by reconcile (or resolve)
    raw            TEXT,
    recorded_at    TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_open_queue AS
SELECT id, symbol, qty, ref_price, max_gap_pct, expires_on, note, queued_at
FROM queue WHERE status = 'queued' ORDER BY id;

-- Outcome of the most recent plan run: everything it touched, joined to any
-- placement. LEFT JOIN so vetoed/expired rows appear with NULL order ids.
CREATE VIEW IF NOT EXISTS v_run_results AS
SELECT q.id, q.symbol, q.qty, q.status, q.resolution_reason,
       p.limit_price, p.order_id, p.outcome
FROM queue q
LEFT JOIN placements p ON p.queue_id = q.id
WHERE q.resolved_at >= (SELECT COALESCE(MAX(captured_at), '') FROM runs WHERE phase = 'plan')
ORDER BY q.id;

-- Anything needing human eyes: a claim that never became a broker order,
-- or a placed row with NO confirmed placement. NOT EXISTS (not row-wise
-- LEFT JOIN) so an early outcome='error' placement can't flag a row that a
-- later placement or a human resolve has already confirmed.
CREATE VIEW IF NOT EXISTS v_unreconciled AS
SELECT q.id, q.symbol, q.status, q.resolution_reason
FROM queue q
WHERE q.status = 'planned'
   OR (q.status = 'placed' AND NOT EXISTS (
        SELECT 1 FROM placements p
        WHERE p.queue_id = q.id
          AND p.order_id IS NOT NULL AND p.confirmed_at IS NOT NULL));
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
