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
    position_count INTEGER NOT NULL,
    option_count   INTEGER NOT NULL DEFAULT 0
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

-- Option legs, keyed by CONTRACT: two contracts on one underlying are two
-- rows (the (snapshot_id, symbol) PK above could never hold them — the
-- structural blocker the 2026-07-08 options spec named). Column names
-- follow cboe_options. quantity is SIGNED (short = negative). Capture-only
-- today: advisor's heat math does not read this table yet, so a held
-- option is stored but still invisible to v_book_heat until the signed
-- delta-dollar increment ships.
CREATE TABLE IF NOT EXISTS option_positions (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    occ_symbol   TEXT NOT NULL,
    underlying   TEXT NOT NULL,
    type         TEXT,
    strike       REAL,
    expiration   TEXT,
    quantity     REAL NOT NULL,
    avg_cost     REAL,
    market_value REAL,
    multiplier   REAL,
    PRIMARY KEY (snapshot_id, occ_symbol)
);

CREATE VIEW IF NOT EXISTS v_latest_account AS
SELECT a.* FROM account a
WHERE a.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);

CREATE VIEW IF NOT EXISTS v_latest_positions AS
SELECT p.* FROM positions p
WHERE p.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);

CREATE VIEW IF NOT EXISTS v_latest_option_positions AS
SELECT o.* FROM option_positions o
WHERE o.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1);
"""


def ensure_schema(conn) -> None:
    """Create tables + views, then the idempotent column migration (a db
    created before option capture lacks snapshots.option_count)."""
    conn.executescript(_SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(snapshots)")}
    if "option_count" not in cols:
        conn.execute("ALTER TABLE snapshots ADD COLUMN option_count INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def write_snapshot(
    conn, captured_at: str, account: dict, positions: list, option_positions: list | tuple = ()
) -> int:
    """One snapshot header + its account row + position/option-leg rows."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, position_count, option_count) VALUES (?, ?, ?)",
        (captured_at, len(positions), len(option_positions)),
    )
    sid = cur.lastrowid
    conn.execute(
        "INSERT INTO account (snapshot_id, equity, cash, buying_power) VALUES (?, ?, ?, ?)",
        (sid, account.get("equity"), account.get("cash"), account.get("buying_power")),
    )
    conn.executemany(
        "INSERT INTO positions (snapshot_id, symbol, quantity, avg_cost, "
        "market_value) VALUES (:sid, :symbol, :quantity, :avg_cost, "
        ":market_value)",
        [{**p, "sid": sid} for p in positions],
    )
    conn.executemany(
        "INSERT INTO option_positions (snapshot_id, occ_symbol, underlying, type,"
        " strike, expiration, quantity, avg_cost, market_value, multiplier)"
        " VALUES (:sid, :occ_symbol, :underlying, :type, :strike, :expiration,"
        " :quantity, :avg_cost, :market_value, :multiplier)",
        [{**o, "sid": sid} for o in option_positions],
    )
    conn.commit()
    return sid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Cascade account + positions then snapshot headers (fully
    snapshot-scoped, same pattern as candidates.db)."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)
        ).fetchall()
    ]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("account", "positions", "option_positions"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
