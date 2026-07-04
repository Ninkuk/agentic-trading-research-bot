from datetime import datetime, timedelta

from sources.common.screener_common import connect
from pipeline.leads import catalog

__all__ = ["connect", "ensure_schema", "write_snapshot", "finalize_snapshot",
           "write_source_state", "write_leads", "write_regime", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    lead_count  INTEGER,
    source      TEXT
);

-- provenance: which source DBs, at what state, fed this run
CREATE TABLE IF NOT EXISTS source_state (
    snapshot_id        INTEGER NOT NULL REFERENCES snapshots(id),
    source             TEXT NOT NULL,
    db_path            TEXT,
    source_captured_at TEXT,
    max_data_date      TEXT,
    PRIMARY KEY (snapshot_id, source)
);

CREATE TABLE IF NOT EXISTS leads (
    snapshot_id     INTEGER NOT NULL REFERENCES snapshots(id),
    instrument      TEXT NOT NULL,      -- ETF or stock ticker, normalized
    instrument_kind TEXT NOT NULL,      -- 'etf' | 'stock'
    signal          TEXT NOT NULL,      -- 'cot_commercial_extreme' | 'quality_composite'
    direction       TEXT NOT NULL,      -- 'long' | 'short'
    signal_type     TEXT NOT NULL,
    implementation  TEXT NOT NULL,
    horizon_band    TEXT NOT NULL,
    score           REAL NOT NULL,      -- signal-native: COT index 0-100, quality z
    rank_pct        REAL,               -- cross-sectional percentile where applicable
    as_of_date      TEXT NOT NULL,
    details         TEXT,               -- JSON: confirm-leg values, member z's, code/asset_class
    PRIMARY KEY (snapshot_id, instrument, signal)
);

CREATE TABLE IF NOT EXISTS regime (
    snapshot_id          INTEGER PRIMARY KEY REFERENCES snapshots(id),
    as_of_date           TEXT,
    cpi_yoy              REAL,
    unrate               REAL,
    yield_curve_inverted INTEGER,
    hy_spread            REAL,
    late_cycle           INTEGER,
    exposure_scalar      REAL NOT NULL,
    regime_incomplete    INTEGER NOT NULL DEFAULT 0
);
"""

_VIEWS = """
-- Latest snapshot's leads with the run's regime scalar joined on (LEFT JOIN:
-- a skipped regime leg yields NULL scalar instead of hiding the leads).
CREATE VIEW IF NOT EXISTS v_latest_leads AS
SELECT l.snapshot_id, l.instrument, l.instrument_kind, l.signal, l.direction,
       l.signal_type, l.implementation, l.horizon_band, l.score, l.rank_pct,
       l.as_of_date, l.details, r.exposure_scalar, r.regime_incomplete
FROM leads l
LEFT JOIN regime r ON r.snapshot_id = l.snapshot_id
WHERE l.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);

-- Grouped per instrument, for Stage 2 confluence / dedup.
CREATE VIEW IF NOT EXISTS v_leads_by_instrument AS
SELECT instrument, instrument_kind,
       COUNT(*)                  AS signal_count,
       SUM(direction = 'long')   AS long_count,
       SUM(direction = 'short')  AS short_count,
       GROUP_CONCAT(signal, ',') AS signals
FROM v_latest_leads
GROUP BY instrument, instrument_kind;
"""

_LEAD_COLS = ("instrument", "instrument_kind", "signal", "direction",
              "signal_type", "implementation", "horizon_band", "score",
              "rank_pct", "as_of_date", "details")

_REGIME_COLS = ("as_of_date", "cpi_yoy", "unrate", "yield_curve_inverted",
                "hy_spread", "late_cycle", "exposure_scalar",
                "regime_incomplete")


def ensure_schema(conn) -> None:
    """Create tables + ELT views. Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def write_snapshot(conn, captured_at: str) -> int:
    """Insert one run header (lead_count starts at 0; finalize_snapshot sets
    the real count once every leg has written). Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, lead_count, source) "
        "VALUES (?, 0, 'pipeline/leads')", (captured_at,))
    conn.commit()
    return cur.lastrowid


def finalize_snapshot(conn, snapshot_id: int) -> int:
    """Set the header's lead_count from the rows actually written. Returns it."""
    n = conn.execute("SELECT COUNT(*) FROM leads WHERE snapshot_id=?",
                     (snapshot_id,)).fetchone()[0]
    conn.execute("UPDATE snapshots SET lead_count=? WHERE id=?",
                 (n, snapshot_id))
    conn.commit()
    return n


def write_source_state(conn, snapshot_id: int, states: list[dict]) -> None:
    """Insert source provenance records (which source DBs fed this run)."""
    conn.executemany(
        """INSERT INTO source_state
           (snapshot_id, source, db_path, source_captured_at, max_data_date)
           VALUES (:snapshot_id, :source, :db_path, :source_captured_at,
                   :max_data_date)""",
        [{**s, "snapshot_id": snapshot_id} for s in states])
    conn.commit()


def write_leads(conn, snapshot_id: int, leads: list[dict]) -> int:
    """Insert leads, validating the pinned tag vocabulary writer-side
    (spec: a VOCAB violation is a code bug -> ValueError, not a migration)."""
    for lead in leads:
        for field, allowed in catalog.VOCAB.items():
            if lead[field] not in allowed:
                raise ValueError(f"invalid {field}: {lead[field]!r}")
        if lead["direction"] not in ("long", "short"):
            raise ValueError(f"invalid direction: {lead['direction']!r}")
        if lead["instrument_kind"] not in ("etf", "stock"):
            raise ValueError(
                f"invalid instrument_kind: {lead['instrument_kind']!r}")
    cols = ", ".join(_LEAD_COLS)
    placeholders = ", ".join(":" + c for c in _LEAD_COLS)
    conn.executemany(
        f"INSERT INTO leads (snapshot_id, {cols}) "
        f"VALUES (:snapshot_id, {placeholders})",
        [{**lead, "snapshot_id": snapshot_id} for lead in leads])
    conn.commit()
    return len(leads)


def write_regime(conn, snapshot_id: int, regime: dict) -> None:
    """Insert the regime state for this snapshot."""
    cols = ", ".join(_REGIME_COLS)
    placeholders = ", ".join(":" + c for c in _REGIME_COLS)
    conn.execute(
        f"INSERT INTO regime (snapshot_id, {cols}) "
        f"VALUES (:snapshot_id, {placeholders})",
        {**regime, "snapshot_id": snapshot_id})
    conn.commit()


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete snapshots older than keep_days before now_iso, cascading the
    three snapshot-scoped children first (leads.db is fully snapshot-scoped —
    unlike the FRED/fundamentals historical stores). String-compares
    captured_at to the cutoff, so both must be fixed-width UTC isoformat."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("leads", "regime", "source_state"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
