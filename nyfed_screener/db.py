from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "write_reference_rates",
           "write_repo_ops", "write_soma_holdings", "write_primary_dealer",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    domain_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reference_rates (
    rate_type      TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    percent_rate   REAL,
    volume_bn      REAL,
    pct_1 REAL, pct_25 REAL, pct_75 REAL, pct_99 REAL,
    PRIMARY KEY (rate_type, effective_date)
);
CREATE TABLE IF NOT EXISTS repo_ops (
    operation_id    TEXT PRIMARY KEY,
    operation_date  TEXT NOT NULL,
    operation_type  TEXT NOT NULL,
    total_submitted REAL,
    total_accepted  REAL,
    award_rate      REAL
);
CREATE INDEX IF NOT EXISTS ix_repo_ops_date ON repo_ops(operation_date);
CREATE TABLE IF NOT EXISTS soma_holdings (
    as_of_date    TEXT NOT NULL,
    security_type TEXT NOT NULL,
    par_value     REAL,
    PRIMARY KEY (as_of_date, security_type)
);
CREATE TABLE IF NOT EXISTS primary_dealer_stats (
    as_of_date TEXT NOT NULL,
    series_key TEXT NOT NULL,
    value      REAL,
    PRIMARY KEY (as_of_date, series_key)
);
-- IORB is a Fed administered rate NOT on the NY Fed API; this table lets
-- v_sofr_latest LEFT JOIN a spread (empty by default -> spread NULL). Populate
-- from FRED 'IORB' out-of-band.
CREATE TABLE IF NOT EXISTS iorb (
    effective_date TEXT PRIMARY KEY,
    percent_rate   REAL
);
"""


def ensure_schema(conn) -> None:
    """Create all NY Fed tables (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def _upsert(conn, table, cols, key_cols, rows) -> int:
    by_key = {tuple(r[k] for k in key_cols): r for r in rows}
    placeholders = ", ".join(f":{c}" for c in cols)
    non_key = [c for c in cols if c not in key_cols]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in non_key) or \
        f"{key_cols[0]}={key_cols[0]}"
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(key_cols)}) DO UPDATE SET {set_clause}",
        list(by_key.values()))
    conn.commit()
    return len(by_key)


def write_reference_rates(conn, rows) -> int:
    return _upsert(conn, "reference_rates",
                   ["rate_type", "effective_date", "percent_rate", "volume_bn",
                    "pct_1", "pct_25", "pct_75", "pct_99"],
                   ["rate_type", "effective_date"], rows)


def write_repo_ops(conn, rows) -> int:
    return _upsert(conn, "repo_ops",
                   ["operation_id", "operation_date", "operation_type",
                    "total_submitted", "total_accepted", "award_rate"],
                   ["operation_id"], rows)


def write_soma_holdings(conn, rows) -> int:
    return _upsert(conn, "soma_holdings",
                   ["as_of_date", "security_type", "par_value"],
                   ["as_of_date", "security_type"], rows)


def write_primary_dealer(conn, rows) -> int:
    return _upsert(conn, "primary_dealer_stats",
                   ["as_of_date", "series_key", "value"],
                   ["as_of_date", "series_key"], rows)


def write_snapshot(conn, captured_at, domain_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, domain_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, domain_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. Fact tables are the store and
    are NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})",
                 ids)
    conn.commit()
    return len(ids)


_VIEWS = ""   # filled in Task 4
