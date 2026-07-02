import sqlite3
from collections.abc import Iterable

from screener.catalog import DataPoint

_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,
    universe_count INTEGER NOT NULL,
    source         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS data_points (
    id       TEXT PRIMARY KEY,
    name     TEXT,
    category TEXT,
    is_pro   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS metrics (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    symbol      TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, symbol)
);
CREATE INDEX IF NOT EXISTS ix_metrics_symbol ON metrics(symbol);
CREATE VIEW IF NOT EXISTS v_latest AS
SELECT m.* FROM metrics m
WHERE m.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _metrics_columns(conn) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}


def ensure_schema(conn, columns: dict[str, str]) -> None:
    """Create base tables and add any missing metrics columns. Idempotent."""
    conn.executescript(_BASE_SCHEMA)
    existing = _metrics_columns(conn)
    for col, affinity in columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE metrics ADD COLUMN {_quote_ident(col)} {affinity}")
    conn.commit()


def upsert_data_points(conn, data_points: Iterable[DataPoint]) -> None:
    conn.executemany(
        """INSERT INTO data_points (id, name, category, is_pro)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, category=excluded.category, is_pro=excluded.is_pro""",
        [(d.id, d.name, d.category, int(d.is_pro)) for d in data_points],
    )
    conn.commit()


def write_snapshot(conn, captured_at: str, source: str,
                   data: dict[str, dict], column_ids: list[str]) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, ?)",
        (captured_at, len(data), source),
    )
    snapshot_id = cur.lastrowid
    cols = ["snapshot_id", "symbol"] + column_ids
    quoted = ", ".join(_quote_ident(c) for c in cols)
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO metrics ({quoted}) VALUES ({placeholders})"
    rows = [
        [snapshot_id, symbol] + [fields.get(cid) for cid in column_ids]
        for symbol, fields in data.items()
    ]
    conn.executemany(sql, rows)
    conn.commit()
    return snapshot_id


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete snapshots + metrics older than keep_days before now_iso. Returns count."""
    from datetime import datetime, timedelta
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM metrics WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
