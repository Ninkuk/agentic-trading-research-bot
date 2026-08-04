"""orders.db: the buy-order queue, execution-run headers, and the append-only
broker placement record. NOT snapshot-scoped and never pruned — queue rows
are human decisions (same never-prune rule as scorer.db decisions) and the
whole DB is tiny. The queued→planned flip happens only inside plan's single
BEGIN IMMEDIATE transaction (see run.py) — that atomic claim, plus the
per-order ref_id the broker deduplicates on, is the double-buy guard.

A queue row is exactly one of two order kinds, enforced by CHECK:
whole-share (qty set, plans a GFD limit order) or notional (notional set,
plans a dollar-based market order — the broker only accepts fractional as
market type, so the spend is capped by the notional itself and the gap veto
against ref_price is the price protection)."""

import sqlite3

__all__ = ["connect", "ensure_schema"]

# Shared between the CREATE TABLE IF NOT EXISTS path (fresh DB) and the
# rebuild migration (live pre-notional DB) so the two shapes cannot drift.
_QUEUE_DDL = """
CREATE TABLE {clause} {name} (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol            TEXT NOT NULL,
    qty               INTEGER CHECK (qty IS NULL OR qty > 0),
    notional          REAL CHECK (notional IS NULL OR notional >= 1.0),
    ref_price         REAL NOT NULL CHECK (ref_price >= 1.0),
    max_gap_pct       REAL NOT NULL CHECK (max_gap_pct >= 0),
    expires_on        TEXT NOT NULL,          -- Phoenix date
    note              TEXT,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
        ('queued','planned','placed','vetoed','expired','failed','cancelled')),
    ref_id            TEXT UNIQUE,            -- minted at claim time
    planned_limit     TEXT,                   -- decimal string, set at claim time:
                                              -- limit price (share rows) or exact
                                              -- dollar amount (notional rows)
    queued_at         TEXT NOT NULL,          -- UTC isoformat
    resolved_at       TEXT,
    resolution_reason TEXT,
    CHECK ((qty IS NOT NULL) + (notional IS NOT NULL) = 1)
)
"""

_SCHEMA_TABLES = (
    _QUEUE_DDL.format(clause="IF NOT EXISTS", name="queue")
    + """;

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
    limit_price    TEXT NOT NULL,             -- decimal string, as sent: limit price
                                              -- (share rows) or dollar amount
                                              -- (notional rows), from queue.planned_limit
    order_id       TEXT,
    outcome        TEXT NOT NULL CHECK (outcome IN ('placed','error')),
    confirmed_at   TEXT,                      -- set by reconcile (or resolve)
    raw            TEXT,
    recorded_at    TEXT NOT NULL
);
"""
)

# Views are DROP+CREATE (not IF NOT EXISTS) so definition changes propagate
# to live DBs on the next ensure_schema.
_SCHEMA_VIEWS = """
DROP VIEW IF EXISTS v_open_queue;
CREATE VIEW v_open_queue AS
SELECT id, symbol, qty, notional, ref_price, max_gap_pct, expires_on, note, queued_at
FROM queue WHERE status = 'queued' ORDER BY id;

-- Outcome of the most recent plan run: everything it touched, joined to any
-- placement. LEFT JOIN so vetoed/expired rows appear with NULL order ids.
DROP VIEW IF EXISTS v_run_results;
CREATE VIEW v_run_results AS
SELECT q.id, q.symbol, q.qty, q.notional, q.status, q.resolution_reason,
       p.limit_price, p.order_id, p.outcome
FROM queue q
LEFT JOIN placements p ON p.queue_id = q.id
WHERE q.resolved_at >= (SELECT COALESCE(MAX(captured_at), '') FROM runs WHERE phase = 'plan')
ORDER BY q.id;

-- Anything needing human eyes: a claim that never became a broker order,
-- or a placed row with NO confirmed placement. NOT EXISTS (not row-wise
-- LEFT JOIN) so an early outcome='error' placement can't flag a row that a
-- later placement or a human resolve has already confirmed.
DROP VIEW IF EXISTS v_unreconciled;
CREATE VIEW v_unreconciled AS
SELECT q.id, q.symbol, q.status, q.resolution_reason
FROM queue q
WHERE q.status = 'planned'
   OR (q.status = 'placed' AND NOT EXISTS (
        SELECT 1 FROM placements p
        WHERE p.queue_id = q.id
          AND p.order_id IS NOT NULL AND p.confirmed_at IS NOT NULL));
"""

_QUEUE_COPY_COLS = (
    "id, symbol, qty, ref_price, max_gap_pct, expires_on, note, status,"
    " ref_id, planned_limit, queued_at, resolved_at, resolution_reason"
)

# Full current column list, for rebuilds whose source already has notional.
_QUEUE_COPY_COLS_ALL = _QUEUE_COPY_COLS.replace("id, symbol, qty,", "id, symbol, qty, notional,")


def _migrate_queue_notional(conn: sqlite3.Connection) -> None:
    """Rebuild a pre-notional queue table in place (SQLite cannot relax the
    old qty NOT NULL via ALTER). The NEW table is renamed into position —
    renaming the OLD one aside would make ALTER rewrite placements' foreign
    key to follow it. Existing rows keep their ids (and the AUTOINCREMENT
    sequence) with notional NULL."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(queue)").fetchall()}
    if not cols or "notional" in cols:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Old views reference the table being dropped and would fail the
        # RENAME's schema re-parse; ensure_schema recreates them right after.
        for view in ("v_open_queue", "v_run_results", "v_unreconciled"):
            conn.execute(f"DROP VIEW IF EXISTS {view}")
        conn.execute(_QUEUE_DDL.format(clause="", name="queue_migrate"))
        conn.execute(
            f"INSERT INTO queue_migrate ({_QUEUE_COPY_COLS}) SELECT {_QUEUE_COPY_COLS} FROM queue"
        )
        conn.execute("DROP TABLE queue")
        conn.execute("ALTER TABLE queue_migrate RENAME TO queue")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _migrate_queue_status_cancelled(conn: sqlite3.Connection) -> None:
    """Rebuild a queue table whose status CHECK predates 'cancelled' — SQLite
    cannot ALTER a CHECK constraint. Same rename-into-position dance as the
    notional migration, for the same placements-FK reason. A pre-notional DB
    never reaches here in the old shape: its rebuild already used the current
    DDL, so this detects nothing and no-ops."""
    (ddl,) = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='queue'"
    ).fetchone()
    if "'cancelled'" in ddl:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        for view in ("v_open_queue", "v_run_results", "v_unreconciled"):
            conn.execute(f"DROP VIEW IF EXISTS {view}")
        conn.execute(_QUEUE_DDL.format(clause="", name="queue_migrate"))
        conn.execute(
            f"INSERT INTO queue_migrate ({_QUEUE_COPY_COLS_ALL})"
            f" SELECT {_QUEUE_COPY_COLS_ALL} FROM queue"
        )
        conn.execute("DROP TABLE queue")
        conn.execute("ALTER TABLE queue_migrate RENAME TO queue")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_TABLES)
    _migrate_queue_notional(conn)
    _migrate_queue_status_cancelled(conn)
    conn.executescript(_SCHEMA_VIEWS)
    conn.commit()
