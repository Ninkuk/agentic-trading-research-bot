import sqlite3
from datetime import datetime, timedelta


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def prune(conn, keep_days: int, now_iso: str, *, child_table: str,
          child_fk: str = "snapshot_id") -> int:
    """Delete snapshots older than keep_days before now_iso, cascading to
    child_table first. Returns the number of snapshots removed."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM {child_table} WHERE {child_fk} IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
