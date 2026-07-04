# finra_short_interest/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities",
           "replace_settlement", "record_settlement", "write_snapshot",
           "stored_settlements", "prune"]

_SI_COLS = ["symbol", "settlement_date", "current_short_qty",
            "previous_short_qty", "avg_daily_volume", "days_to_cover",
            "change_pct", "revision_flag", "market_class"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    symbol     TEXT PRIMARY KEY,
    issue_name TEXT,                       -- newest issueName seen
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS short_interest (
    symbol             TEXT NOT NULL REFERENCES securities(symbol),
    settlement_date    TEXT NOT NULL,      -- YYYY-MM-DD
    current_short_qty  INTEGER NOT NULL,
    previous_short_qty INTEGER,
    avg_daily_volume   INTEGER,
    days_to_cover      REAL,               -- FINRA-computed daysToCoverQuantity
    change_pct         REAL,               -- FINRA-computed changePercent
    revision_flag      TEXT,
    market_class       TEXT,               -- marketClassCode (NNM/OTC/etc.)
    PRIMARY KEY (symbol, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_si_settlement ON short_interest(settlement_date);
CREATE INDEX IF NOT EXISTS ix_si_symbol     ON short_interest(symbol);
CREATE TABLE IF NOT EXISTS settlements (
    settlement_date TEXT PRIMARY KEY,
    fetched_at      TEXT NOT NULL,
    row_count       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    settlement_count INTEGER NOT NULL,
    row_count        INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables and indexes. Idempotent. (Views are added in Task 3.)"""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the symbol dimension: extend first_seen/last_seen to the min/max
    settlement date seen, and refresh issue_name to the newest (largest
    settlement_date) name observed."""
    params = [{"symbol": r["symbol"], "issue": r.get("issue_name"),
               "d": r["settlement_date"]} for r in rows]
    conn.executemany(
        """INSERT INTO securities (symbol, issue_name, first_seen, last_seen)
           VALUES (:symbol, :issue, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen),
             issue_name = CASE WHEN excluded.last_seen >= securities.last_seen
                               THEN excluded.issue_name
                               ELSE securities.issue_name END""",
        params,
    )
    conn.commit()


def replace_settlement(conn, settlement_date: str, rows: list[dict]) -> int:
    """Delete all short_interest rows for this settlement, then bulk-insert the
    given rows. Replace (not upsert) so a FINRA repost that drops a symbol
    leaves no orphan. Dedupes within the batch by (symbol, settlement_date).
    Returns rows written."""
    by_key = {(r["symbol"], r["settlement_date"]): r for r in rows}
    conn.execute("DELETE FROM short_interest WHERE settlement_date = ?",
                 (settlement_date,))
    placeholders = ", ".join(":" + c for c in _SI_COLS)
    params = [{c: r.get(c) for c in _SI_COLS} for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO short_interest ({', '.join(_SI_COLS)}) "
        f"VALUES ({placeholders})", params)
    conn.commit()
    return len(by_key)


def record_settlement(conn, settlement_date: str, fetched_at: str,
                      row_count: int) -> None:
    """Upsert one settlement's provenance row."""
    conn.execute(
        """INSERT INTO settlements (settlement_date, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(settlement_date) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (settlement_date, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, settlement_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, settlement_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, settlement_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_settlements(conn) -> list:
    """All ingested settlement dates, sorted ascending (ISO dates sort
    chronologically)."""
    return [r[0] for r in conn.execute(
        "SELECT settlement_date FROM settlements ORDER BY settlement_date")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Short-interest history is NOT snapshot-scoped, so this is a single-table
    delete of snapshot headers only — it must NOT cascade into short_interest."""
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
