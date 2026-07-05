from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "write_snapshot", "finalize_snapshot",
           "write_candidates", "write_rejections", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    candidate_count  INTEGER,
    rejection_count  INTEGER,
    equity           REAL NOT NULL,
    regime_scalar    REAL,
    leads_snapshot_id INTEGER,
    config_hash      TEXT NOT NULL,     -- sha256 of the frozen gate config
    fractional       INTEGER NOT NULL DEFAULT 0  -- sizing quantum: whole vs 1e-6
);

-- shares/size_lo/size_hi are REAL since fractional sizing; DBs created with
-- the earlier INTEGER DDL stay valid (SQLite INTEGER affinity stores a
-- non-integral REAL losslessly — pinned by test).
CREATE TABLE IF NOT EXISTS candidates (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    instrument TEXT NOT NULL, instrument_kind TEXT, direction TEXT NOT NULL,
    det_score REAL NOT NULL, horizon_band TEXT NOT NULL,
    signals TEXT NOT NULL,              -- JSON: contributing signal rows
    price REAL, atr REAL, sector TEXT,  -- sector = asset_class for ETFs
    next_earnings_date TEXT,            -- NULL for ETFs; feeds Stage 3 masking
    shares REAL NOT NULL, stop_price REAL NOT NULL,
    stop_distance REAL, risk_dollars REAL, realized_risk REAL,
    size_lo REAL NOT NULL, size_hi REAL NOT NULL,
    as_of_date TEXT NOT NULL, details TEXT,
    PRIMARY KEY (snapshot_id, instrument, direction)
);

CREATE TABLE IF NOT EXISTS rejections (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    instrument TEXT, direction TEXT, gate TEXT NOT NULL, reason TEXT,
    PRIMARY KEY (snapshot_id, instrument, direction, gate)
);
"""

# Views are derived: drop + recreate so definition changes reach old DBs.
_VIEWS = """
DROP VIEW IF EXISTS v_latest_candidates;
CREATE VIEW v_latest_candidates AS
SELECT c.* FROM candidates c
WHERE c.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);

-- The funnel's kill-report for the latest snapshot.
DROP VIEW IF EXISTS v_rejection_summary;
CREATE VIEW v_rejection_summary AS
SELECT gate, COUNT(*) AS n FROM rejections
WHERE snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1)
GROUP BY gate;

-- Exactly what Stage 3's gate consumes: latest candidates + run context.
DROP VIEW IF EXISTS v_gate_input;
CREATE VIEW v_gate_input AS
SELECT c.instrument, c.instrument_kind, c.direction, c.det_score,
       c.horizon_band, c.signals, c.price, c.atr, c.sector,
       c.next_earnings_date, c.shares, c.stop_price, c.stop_distance,
       c.risk_dollars, c.realized_risk, c.size_lo, c.size_hi, c.as_of_date,
       c.details, s.equity, s.regime_scalar, s.config_hash, s.fractional
FROM candidates c JOIN snapshots s ON s.id = c.snapshot_id
WHERE c.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);
"""

_CANDIDATE_COLS = ("instrument", "instrument_kind", "direction", "det_score",
                   "horizon_band", "signals", "price", "atr", "sector",
                   "next_earnings_date", "shares", "stop_price",
                   "stop_distance", "risk_dollars", "realized_risk",
                   "size_lo", "size_hi", "as_of_date", "details")


def _migrate(conn) -> None:
    """Pre-fractional DBs gain the snapshots.fractional column in place."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(snapshots)")}
    if cols and "fractional" not in cols:
        conn.execute("ALTER TABLE snapshots "
                     "ADD COLUMN fractional INTEGER NOT NULL DEFAULT 0")


def ensure_schema(conn) -> None:
    """Create tables, migrate old ones, then (re)create views. Idempotent."""
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.executescript(_VIEWS)
    conn.commit()


def write_snapshot(conn, captured_at, equity, regime_scalar,
                   leads_snapshot_id, config_hash, fractional=0) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, candidate_count, rejection_count,"
        " equity, regime_scalar, leads_snapshot_id, config_hash, fractional)"
        " VALUES (?, 0, 0, ?, ?, ?, ?, ?)",
        (captured_at, equity, regime_scalar, leads_snapshot_id, config_hash,
         int(fractional)))
    conn.commit()
    return cur.lastrowid


def finalize_snapshot(conn, snapshot_id: int) -> tuple:
    cc = conn.execute("SELECT COUNT(*) FROM candidates WHERE snapshot_id=?",
                      (snapshot_id,)).fetchone()[0]
    rc = conn.execute("SELECT COUNT(*) FROM rejections WHERE snapshot_id=?",
                      (snapshot_id,)).fetchone()[0]
    conn.execute("UPDATE snapshots SET candidate_count=?, rejection_count=? "
                 "WHERE id=?", (cc, rc, snapshot_id))
    conn.commit()
    return cc, rc


def write_candidates(conn, snapshot_id: int, rows: list) -> int:
    cols = ", ".join(_CANDIDATE_COLS)
    placeholders = ", ".join(":" + c for c in _CANDIDATE_COLS)
    conn.executemany(
        f"INSERT INTO candidates (snapshot_id, {cols}) "
        f"VALUES (:snapshot_id, {placeholders})",
        [{**r, "snapshot_id": snapshot_id} for r in rows])
    conn.commit()
    return len(rows)


def write_rejections(conn, snapshot_id: int, rows: list) -> int:
    conn.executemany(
        "INSERT OR REPLACE INTO rejections "
        "(snapshot_id, instrument, direction, gate, reason) "
        "VALUES (:snapshot_id, :instrument, :direction, :gate, :reason)",
        [{**r, "snapshot_id": snapshot_id} for r in rows])
    conn.commit()
    return len(rows)


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Cascade candidates + rejections then snapshot headers (fully
    snapshot-scoped, same pattern as leads.db)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("candidates", "rejections"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
