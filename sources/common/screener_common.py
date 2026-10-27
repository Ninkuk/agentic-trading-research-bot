import sqlite3
from collections.abc import Iterable
from datetime import datetime, timedelta


def connect(
    path: str, *, uri: bool = False, busy_timeout_ms: int | None = None
) -> sqlite3.Connection:
    """Open a DB in WAL mode. ``uri=True`` lets the connection ATTACH
    'file:...?mode=ro' sources (plain paths still open fine); ``busy_timeout_ms``
    waits on a locked DB instead of raising at once."""
    conn = sqlite3.connect(path, uri=uri)
    conn.execute("PRAGMA journal_mode=WAL")
    if busy_timeout_ms is not None:
        conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    return conn


def prune(
    conn,
    keep_days: int,
    now_iso: str,
    *,
    child_tables: Iterable[str] = (),
    child_table: str | None = None,
    child_fk: str = "snapshot_id",
) -> int:
    """Delete snapshots older than keep_days before now_iso, cascading to every
    table in ``child_tables`` first (``child_table`` is the one-table spelling).
    An empty cascade deletes headers only — the shape for packages whose domain
    rows are upsert-keyed history rather than snapshot-scoped. Returns the number
    of snapshots removed.

    The cutoff is compared to snapshots.captured_at as a plain string, so this
    is correct only because every writer stores captured_at and passes now_iso
    as a UTC isoformat() timestamp (identical, fixed-width format incl. the
    +00:00 offset). Feeding a naive/differently-formatted now_iso would make the
    lexicographic '<' misclassify boundary rows."""
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
    tables = [*child_tables, *([child_table] if child_table else [])]
    for table in tables:
        conn.execute(f"DELETE FROM {table} WHERE {child_fk} IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)


def add_missing_columns(conn, table: str, ddls: Iterable[str]) -> None:
    """Idempotent additive migration: ``ALTER TABLE table ADD COLUMN ddl`` for
    each ddl ("name TYPE ...") whose column is not already present."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for ddl in ddls:
        if ddl.split()[0] not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def split_csv(v: str | None) -> list[str] | None:
    """A comma-separated CLI value as a list; blank tokens dropped; None/empty
    -> None so the caller's "whole catalog" default applies."""
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated ids to fetch: ``only`` (or the full
    catalog) minus ``exclude``, then any ``add`` ids appended. Tokens are
    stripped; blanks and duplicates are dropped."""
    ids = list(only) if only else list(all_ids)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for i in [*ids, *(add or ())]:
        i = i.strip()
        if not i or i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out


def max_date(conn, table: str, date_col: str) -> str | None:
    """Newest stored date in ``table``, or None when it holds nothing yet."""
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    return row[0] if row and row[0] else None


def since_floor(last: str | None, start: str | None, full: bool, *, lookback_days: int):
    """Inclusive date floor for an incremental pull. Explicit ``start`` wins;
    ``full`` (or a first-ever pull with no stored data) pulls full history /
    from start; otherwise floor at ``last`` - lookback_days so late revisions
    inside the window are re-read."""
    if start is not None:
        return start
    if full or last is None:
        return start
    return (datetime.fromisoformat(last) - timedelta(days=lookback_days)).date().isoformat()
