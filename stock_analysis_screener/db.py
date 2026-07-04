import json
import sys
from collections.abc import Iterable

from stock_analysis_screener.catalog import DataPoint
from sources.common.screener_common import connect, prune as _prune

__all__ = ["connect", "ensure_schema", "prune", "write_snapshot",
           "upsert_data_points"]

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


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _to_cell(v):
    """Coerce a parsed data-point value into something SQLite can bind. Some
    stockanalysis.com data-points are arrays (e.g. inIndex=["SP500","NASDAQ100"],
    tags=["clean-energy"]); JSON-encode any list/dict to TEXT so the value is
    preserved (and queryable via json_each) instead of raising ProgrammingError.
    Scalars (str/int/float/None) pass through untouched."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, separators=(",", ":"))
    return v


def _metrics_column_types(conn) -> dict[str, str]:
    return {r[1]: r[2] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}


def ensure_schema(conn, columns: dict[str, str]) -> None:
    """Create base tables and add any missing metrics columns. Idempotent.

    A column's SQLite affinity is fixed when it is first created and cannot be
    changed by a later ALTER. If a subsequent run infers a different affinity
    for an existing column, we keep the original and warn, since the mismatch
    would otherwise silently mis-store values (e.g. text in a REAL column)."""
    conn.executescript(_BASE_SCHEMA)
    existing = _metrics_column_types(conn)
    for col, affinity in columns.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE metrics ADD COLUMN {_quote_ident(col)} {affinity}")
        elif existing[col] and existing[col] != affinity:
            print(f"warning: data-point '{col}' inferred as {affinity} but its "
                  f"metrics column is {existing[col]}; keeping {existing[col]} "
                  f"(values may be stored with mismatched affinity)",
                  file=sys.stderr)
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
        [snapshot_id, symbol] + [_to_cell(fields.get(cid)) for cid in column_ids]
        for symbol, fields in data.items()
    ]
    conn.executemany(sql, rows)
    conn.commit()
    return snapshot_id


def prune(conn, keep_days, now_iso):
    """Prune stock snapshots + metrics. Delegates to the shared helper."""
    return _prune(conn, keep_days, now_iso, child_table="metrics")
