from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "write_run", "finalize_run",
           "write_decision", "write_events", "run_row", "decisions_for_run",
           "max_event_seq"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS gate_runs (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at               TEXT NOT NULL,
    candidates_snapshot_id    INTEGER,
    decision_count            INTEGER,
    window                    TEXT NOT NULL,
    equity                    REAL NOT NULL,
    heat_cap                  REAL NOT NULL,
    tau                       REAL NOT NULL,
    model_version             TEXT,
    guardrail_config_version  TEXT NOT NULL,
    fractional                INTEGER NOT NULL DEFAULT 0  -- sizing quantum; replay reads THIS
);

-- Share columns are REAL since fractional sizing; DBs created with the
-- earlier INTEGER DDL stay valid (INTEGER affinity keeps REALs lossless).
CREATE TABLE IF NOT EXISTS gate_decisions (
    decision_id               TEXT PRIMARY KEY,
    run_id                    INTEGER NOT NULL REFERENCES gate_runs(id),
    decided_at                TEXT NOT NULL,
    instrument                TEXT NOT NULL,
    direction                 TEXT NOT NULL,
    input_snapshot_hash       TEXT NOT NULL,
    checkpoint                TEXT NOT NULL,
    det_shares                REAL NOT NULL,
    det_stop                  REAL,
    det_score                 REAL,
    stop_distance             REAL,
    size_lo                   REAL NOT NULL,
    size_hi                   REAL NOT NULL,
    agent_action              TEXT,
    agent_size_mult           REAL,
    agent_confidence          REAL,
    agent_rationale           TEXT,
    agent_error               TEXT,
    tau                       REAL NOT NULL,
    final_shares              REAL NOT NULL,
    delta                     REAL NOT NULL,
    clamp_fired               INTEGER NOT NULL DEFAULT 0,
    policy_decision           TEXT NOT NULL,
    decision_maker            TEXT NOT NULL,
    model_version             TEXT,
    prompt_hash               TEXT,
    guardrail_config_version  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_decision_events (
    decision_id               TEXT NOT NULL REFERENCES gate_decisions(decision_id),
    seq                       INTEGER NOT NULL,
    event                     TEXT NOT NULL,
    at                        TEXT NOT NULL,
    detail                    TEXT,
    PRIMARY KEY (decision_id, seq)
);

CREATE TRIGGER IF NOT EXISTS gate_decisions_no_update BEFORE UPDATE ON gate_decisions
BEGIN SELECT RAISE(ABORT, 'gate_decisions is append-only'); END;

CREATE TRIGGER IF NOT EXISTS gate_decisions_no_delete BEFORE DELETE ON gate_decisions
BEGIN SELECT RAISE(ABORT, 'gate_decisions is append-only'); END;

CREATE TRIGGER IF NOT EXISTS gate_decision_events_no_update BEFORE UPDATE ON gate_decision_events
BEGIN SELECT RAISE(ABORT, 'gate_decision_events is append-only'); END;

CREATE TRIGGER IF NOT EXISTS gate_decision_events_no_delete BEFORE DELETE ON gate_decision_events
BEGIN SELECT RAISE(ABORT, 'gate_decision_events is append-only'); END;
"""

_VIEWS = """
CREATE VIEW IF NOT EXISTS v_approved_book AS
SELECT d.* FROM gate_decisions d
WHERE d.run_id = (SELECT id FROM gate_runs
                  ORDER BY captured_at DESC, id DESC LIMIT 1)
  AND d.policy_decision = 'Permit' AND d.final_shares > 0;

CREATE VIEW IF NOT EXISTS v_gate_alerts AS
SELECT d.* FROM gate_decisions d
WHERE d.run_id = (SELECT id FROM gate_runs
                  ORDER BY captured_at DESC, id DESC LIMIT 1)
  AND (d.clamp_fired = 1 OR d.agent_error IS NOT NULL
       OR d.policy_decision = 'Deny'
       OR (d.agent_action = 'veto' AND d.final_shares > 0));

CREATE VIEW IF NOT EXISTS v_delta_history AS
SELECT run_id, COUNT(*) AS n_decisions,
       SUM(agent_action = 'veto')                          AS n_vetoes,
       SUM(agent_action = 'veto' AND final_shares > 0)     AS discarded_vetoes,
       SUM(clamp_fired)                                    AS clamps,
       AVG(ABS(delta))                                     AS mean_abs_delta
FROM gate_decisions GROUP BY run_id;

CREATE VIEW IF NOT EXISTS v_decision_makers AS
SELECT run_id, decision_maker, COUNT(*) AS n
FROM gate_decisions GROUP BY run_id, decision_maker;
"""

_DECISION_COLS = ("decision_id", "run_id", "decided_at", "instrument", "direction",
                  "input_snapshot_hash", "checkpoint", "det_shares", "det_stop",
                  "det_score", "stop_distance", "size_lo", "size_hi", "agent_action",
                  "agent_size_mult", "agent_confidence", "agent_rationale",
                  "agent_error", "tau", "final_shares", "delta", "clamp_fired",
                  "policy_decision", "decision_maker", "model_version", "prompt_hash",
                  "guardrail_config_version")


def _migrate(conn) -> None:
    """Pre-fractional DBs gain gate_runs.fractional in place (gate_runs is
    not trigger-protected — finalize_run already updates it)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gate_runs)")}
    if cols and "fractional" not in cols:
        conn.execute("ALTER TABLE gate_runs "
                     "ADD COLUMN fractional INTEGER NOT NULL DEFAULT 0")


def ensure_schema(conn) -> None:
    """Create tables + views + triggers; migrate old DBs. Idempotent."""
    conn.executescript(_SCHEMA)
    _migrate(conn)
    conn.executescript(_VIEWS)
    conn.commit()


def write_run(conn, captured_at, candidates_snapshot_id, window, equity, heat_cap,
              tau, guardrail_config_version, fractional=0) -> int:
    """Insert a gate run (decision_count and model_version NULL at insert)."""
    cur = conn.execute(
        "INSERT INTO gate_runs (captured_at, candidates_snapshot_id, window, "
        "equity, heat_cap, tau, guardrail_config_version, fractional) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (captured_at, candidates_snapshot_id, window, equity, heat_cap, tau,
         guardrail_config_version, int(fractional)))
    conn.commit()
    return cur.lastrowid


def finalize_run(conn, run_id: int, decision_count: int, model_version: str) -> None:
    """Update gate run with final decision_count and model_version."""
    conn.execute(
        "UPDATE gate_runs SET decision_count=?, model_version=? WHERE id=?",
        (decision_count, model_version, run_id))
    conn.commit()


def write_decision(conn, row: dict) -> None:
    """Insert a decision row from a dict covering all _DECISION_COLS."""
    cols = ", ".join(_DECISION_COLS)
    placeholders = ", ".join(":" + c for c in _DECISION_COLS)
    conn.execute(
        f"INSERT INTO gate_decisions ({cols}) VALUES ({placeholders})",
        row)
    conn.commit()


def write_events(conn, decision_id: str,
                 events: list) -> None:
    """Write events (tuples of (event, at, detail)) with seq continuing from max."""
    start_seq = max_event_seq(conn, decision_id)
    rows = []
    for i, (event, at, detail) in enumerate(events, start=start_seq + 1):
        rows.append((decision_id, i, event, at, detail))
    conn.executemany(
        "INSERT INTO gate_decision_events (decision_id, seq, event, at, detail) "
        "VALUES (?, ?, ?, ?, ?)",
        rows)
    conn.commit()


def run_row(conn, run_id: int) -> dict | None:
    """Fetch gate run by id as dict, or None if not found."""
    cur = conn.execute("SELECT * FROM gate_runs WHERE id=?", (run_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))


def decisions_for_run(conn, run_id: int) -> list:
    """Fetch all decisions for a run as list of dicts."""
    cur = conn.execute("SELECT * FROM gate_decisions WHERE run_id=?", (run_id,))
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def max_event_seq(conn, decision_id: str) -> int:
    """Get the max seq for a decision_id, or 0 if none."""
    result = conn.execute(
        "SELECT MAX(seq) FROM gate_decision_events WHERE decision_id=?",
        (decision_id,)).fetchone()
    return result[0] if result[0] is not None else 0
