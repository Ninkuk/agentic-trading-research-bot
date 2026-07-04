from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "start_attempt", "finish_attempt",
           "ok_exists", "attempt_count", "live_running", "last_ok_finished_at",
           "newest_ok_among", "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS job_runs (
    job         TEXT NOT NULL,
    trigger_key TEXT NOT NULL,
    attempt     INTEGER NOT NULL,      -- 1, 2, 3... one ROW per attempt
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,         -- 'running' | 'ok' | 'error'
    error       TEXT,                  -- exception type name only (secret hygiene)
    PRIMARY KEY (job, trigger_key, attempt)
);
CREATE INDEX IF NOT EXISTS ix_job_runs_status ON job_runs(job, status);

CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    due_count   INTEGER,
    ran_count   INTEGER
);

CREATE VIEW IF NOT EXISTS v_recent_runs AS
SELECT job, trigger_key, attempt, started_at, finished_at, status, error
FROM job_runs ORDER BY started_at DESC, job LIMIT 50;

-- (job, trigger_key) whose latest attempt errored and never got an ok.
CREATE VIEW IF NOT EXISTS v_failures AS
WITH latest AS (
    SELECT job, trigger_key, MAX(attempt) AS attempt
    FROM job_runs GROUP BY job, trigger_key)
SELECT r.job, r.trigger_key, r.attempt, r.started_at, r.error
FROM job_runs r JOIN latest l
  ON l.job = r.job AND l.trigger_key = r.trigger_key AND l.attempt = r.attempt
WHERE r.status = 'error'
  AND NOT EXISTS (SELECT 1 FROM job_runs o
                  WHERE o.job = r.job AND o.trigger_key = r.trigger_key
                    AND o.status = 'ok');
"""


def ensure_schema(conn) -> None:
    """Create job_runs/snapshots + views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def start_attempt(conn, job: str, trigger_key: str, started_at: str) -> int:
    """Insert the next 'running' attempt row. Returns its attempt number."""
    n = attempt_count(conn, job, trigger_key) + 1
    conn.execute(
        "INSERT INTO job_runs (job, trigger_key, attempt, started_at, status) "
        "VALUES (?, ?, ?, ?, 'running')", (job, trigger_key, n, started_at))
    conn.commit()
    return n


def finish_attempt(conn, job: str, trigger_key: str, attempt: int,
                   finished_at: str, status: str, error: str = None) -> None:
    conn.execute(
        "UPDATE job_runs SET finished_at=?, status=?, error=? "
        "WHERE job=? AND trigger_key=? AND attempt=?",
        (finished_at, status, error, job, trigger_key, attempt))
    conn.commit()


def ok_exists(conn, job: str, trigger_key: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM job_runs WHERE job=? AND trigger_key=? AND status='ok' "
        "LIMIT 1", (job, trigger_key)).fetchone() is not None


def attempt_count(conn, job: str, trigger_key: str) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(attempt), 0) FROM job_runs "
        "WHERE job=? AND trigger_key=?", (job, trigger_key)).fetchone()[0]


def live_running(conn, job: str, trigger_key: str, now_iso: str,
                 stale_hours: int) -> bool:
    """True iff the LATEST attempt is 'running' and fresh. A running row older
    than stale_hours is a crashed attempt: it stops blocking (the row itself is
    never rewritten — the next attempt is a new row)."""
    row = conn.execute(
        "SELECT status, started_at FROM job_runs WHERE job=? AND trigger_key=? "
        "ORDER BY attempt DESC LIMIT 1", (job, trigger_key)).fetchone()
    if row is None or row[0] != "running":
        return False
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(hours=stale_hours)).isoformat()
    return row[1] >= cutoff


def last_ok_finished_at(conn, job: str):
    row = conn.execute(
        "SELECT MAX(finished_at) FROM job_runs WHERE job=? AND status='ok'",
        (job,)).fetchone()
    return row[0]


def newest_ok_among(conn, jobs: tuple):
    """(job, trigger_key, finished_at) of the newest ok run among jobs, or None."""
    qmarks = ",".join("?" * len(jobs))
    row = conn.execute(
        f"SELECT job, trigger_key, finished_at FROM job_runs "
        f"WHERE job IN ({qmarks}) AND status='ok' "
        f"ORDER BY finished_at DESC LIMIT 1", jobs).fetchone()
    return tuple(row) if row else None


def write_snapshot(conn, captured_at: str, due_count: int, ran_count: int) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, due_count, ran_count) "
        "VALUES (?, ?, ?)", (captured_at, due_count, ran_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete snapshots and finished job_runs older than the cutoff. Never
    deletes 'running' rows (crash evidence). String comparison — fixed-width
    UTC isoformat required."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if ids:
        qmarks = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    cur = conn.execute(
        "DELETE FROM job_runs WHERE started_at < ? AND status != 'running'",
        (cutoff,))
    conn.commit()
    return len(ids) + cur.rowcount
