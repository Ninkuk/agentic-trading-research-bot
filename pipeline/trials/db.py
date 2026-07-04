import hashlib
import json
from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "canonical_params", "register_trial",
           "trial_row", "write_result", "family_size",
           "family_latest_sharpes", "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
    trial_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    registered_at TEXT NOT NULL,
    stage         TEXT NOT NULL,          -- 'leads' | 'promote' | 'gate' | ...
    description   TEXT NOT NULL,
    params        TEXT NOT NULL,          -- canonical JSON of every knob
    params_hash   TEXT NOT NULL,          -- sha256 of params
    git_rev       TEXT,
    family        TEXT NOT NULL DEFAULT 'default',
    UNIQUE (stage, family, params_hash)   -- family-scoped: identical params in
                                          -- two families are DIFFERENT trials
);

CREATE TABLE IF NOT EXISTS trial_results (
    trial_id     INTEGER NOT NULL REFERENCES trials(trial_id),
    evaluated_at TEXT NOT NULL,
    window_start TEXT, window_end TEXT,
    n_obs INTEGER, sharpe REAL, skew REAL, kurtosis REAL,
    hit_rate REAL, avg_return REAL, max_drawdown REAL,
    dsr_at_eval REAL,        -- frozen at-the-time DSR; goes stale as N grows
    n_at_eval INTEGER,       -- the family N it was computed against
    detail TEXT,             -- JSON: max_gap_days, skipped, entry_lag, haircut
    PRIMARY KEY (trial_id, evaluated_at)
);

CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    trial_count  INTEGER,
    result_count INTEGER
);
"""

_VIEWS = """
CREATE VIEW IF NOT EXISTS v_latest_results AS
WITH ranked AS (
    SELECT r.*, ROW_NUMBER() OVER (PARTITION BY trial_id
                                   ORDER BY evaluated_at DESC) rn
    FROM trial_results r)
SELECT trial_id, evaluated_at, window_start, window_end, n_obs, sharpe, skew,
       kurtosis, hit_rate, avg_return, max_drawdown, dsr_at_eval, n_at_eval,
       detail
FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_trial_history AS
SELECT t.trial_id, t.stage, t.family, t.description, t.registered_at,
       r.evaluated_at, r.window_start, r.window_end, r.n_obs, r.sharpe,
       r.dsr_at_eval, r.n_at_eval
FROM trials t LEFT JOIN trial_results r ON r.trial_id = t.trial_id
ORDER BY t.trial_id, r.evaluated_at;

-- "How hard did we search": per family, N and the best latest result. Live
-- DSR (vs current N) needs inverse-Phi, which SQL lacks — the --leaderboard
-- command appends it in Python.
CREATE VIEW IF NOT EXISTS v_family_leaderboard AS
SELECT t.family,
       COUNT(DISTINCT t.trial_id)              AS n_trials,
       MAX(l.sharpe)                           AS best_sharpe,
       COUNT(l.trial_id)                       AS evaluated_trials
FROM trials t LEFT JOIN v_latest_results l ON l.trial_id = t.trial_id
GROUP BY t.family;

-- Snapshot-gap report: how much data each evaluation actually had.
CREATE VIEW IF NOT EXISTS v_evaluation_coverage AS
SELECT r.trial_id, r.evaluated_at, r.window_start, r.window_end, r.n_obs,
       json_extract(r.detail, '$.max_gap_days') AS max_gap_days,
       json_extract(r.detail, '$.skipped')      AS skipped
FROM trial_results r;
"""

_RESULT_COLS = ("evaluated_at", "window_start", "window_end", "n_obs",
                "sharpe", "skew", "kurtosis", "hit_rate", "avg_return",
                "max_drawdown", "dsr_at_eval", "n_at_eval", "detail")


def ensure_schema(conn) -> None:
    """Create tables + views. Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def canonical_params(params: dict) -> tuple:
    """(canonical JSON, sha256) — key order never changes the hash, so the
    DSR trial count N can never undercount from a re-registration."""
    canon = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return canon, hashlib.sha256(canon.encode()).hexdigest()


def register_trial(conn, stage: str, description: str, params: dict,
                   registered_at: str, family: str = "default",
                   git_rev: str = None) -> tuple:
    """Insert a trial; re-registering identical params in the same
    (stage, family) is a no-op returning the existing trial_id.
    Returns (trial_id, created)."""
    canon, digest = canonical_params(params)
    cur = conn.execute(
        """INSERT INTO trials (registered_at, stage, description, params,
                               params_hash, git_rev, family)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(stage, family, params_hash) DO NOTHING""",
        (registered_at, stage, description, canon, digest, git_rev, family))
    conn.commit()
    if cur.rowcount:
        return cur.lastrowid, True
    row = conn.execute(
        "SELECT trial_id FROM trials WHERE stage=? AND family=? AND "
        "params_hash=?", (stage, family, digest)).fetchone()
    return row[0], False


def trial_row(conn, trial_id: int):
    row = conn.execute(
        "SELECT trial_id, registered_at, stage, description, params, "
        "params_hash, git_rev, family FROM trials WHERE trial_id=?",
        (trial_id,)).fetchone()
    if row is None:
        return None
    keys = ("trial_id", "registered_at", "stage", "description", "params",
            "params_hash", "git_rev", "family")
    return dict(zip(keys, row))


def write_result(conn, trial_id: int, result: dict) -> None:
    cols = ", ".join(_RESULT_COLS)
    placeholders = ", ".join(":" + c for c in _RESULT_COLS)
    conn.execute(
        f"INSERT INTO trial_results (trial_id, {cols}) "
        f"VALUES (:trial_id, {placeholders})",
        {**result, "trial_id": trial_id})
    conn.commit()


def family_size(conn, family: str) -> int:
    """N for DSR: configurations REGISTERED in the family (searched), not
    just the evaluated ones."""
    return conn.execute("SELECT COUNT(*) FROM trials WHERE family=?",
                        (family,)).fetchone()[0]


def family_latest_sharpes(conn, family: str) -> list:
    """Latest evaluation's sharpe per trial in the family (non-NULL only) —
    the sd_SR input to SR0."""
    return [r[0] for r in conn.execute(
        """SELECT l.sharpe FROM v_latest_results l
           JOIN trials t ON t.trial_id = l.trial_id
           WHERE t.family=? AND l.sharpe IS NOT NULL""", (family,)).fetchall()]


def write_snapshot(conn, captured_at: str) -> int:
    tc = conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    rc = conn.execute("SELECT COUNT(*) FROM trial_results").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, trial_count, result_count) "
        "VALUES (?, ?, ?)", (captured_at, tc, rc))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete old snapshot headers ONLY. trials/trial_results are the
    multiple-testing ledger — they are NEVER pruned (an undercounted N makes
    every DSR a lie)."""
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
