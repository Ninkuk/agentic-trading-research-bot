"""portfolio.db: snapshot-scoped account state. One snapshot per
`account-positions` invocation; both children (account, positions) cascade
on prune. Downstream integrations (holdings dedup, G5 real exposure,
whole-book heat, marked-to-market equity) read v_latest_* read-only."""
from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,
    position_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS account (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    equity       REAL,
    cash         REAL,
    buying_power REAL,
    PRIMARY KEY (snapshot_id)
);

CREATE TABLE IF NOT EXISTS positions (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    quantity     REAL NOT NULL,
    avg_cost     REAL,
    market_value REAL,
    PRIMARY KEY (snapshot_id, symbol)
);

CREATE VIEW IF NOT EXISTS v_latest_account AS
SELECT a.* FROM account a
WHERE a.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);

CREATE VIEW IF NOT EXISTS v_latest_positions AS
SELECT p.* FROM positions p
WHERE p.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);
"""


def ensure_schema(conn) -> None:
    """Create tables + views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def write_snapshot(conn, captured_at: str, account: dict,
                   positions: list) -> int:
    """One snapshot header + its account row + position rows."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, position_count) VALUES (?, ?)",
        (captured_at, len(positions)))
    sid = cur.lastrowid
    conn.execute(
        "INSERT INTO account (snapshot_id, equity, cash, buying_power) "
        "VALUES (?, ?, ?, ?)",
        (sid, account.get("equity"), account.get("cash"),
         account.get("buying_power")))
    conn.executemany(
        "INSERT INTO positions (snapshot_id, symbol, quantity, avg_cost, "
        "market_value) VALUES (:sid, :symbol, :quantity, :avg_cost, "
        ":market_value)",
        [{**p, "sid": sid} for p in positions])
    conn.commit()
    return sid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Cascade account + positions then snapshot headers (fully
    snapshot-scoped, same pattern as candidates.db)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("account", "positions"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})",
                     ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
