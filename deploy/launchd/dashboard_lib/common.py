"""Shared helpers for the dashboard's section exporters.

Every exporter module (data.py, grades.py, book.py, sources_views.py) builds
the same section shape — `columns` + `rows`, optional `tiles`, `verdict`,
`empty`, `total` — from a read-only SQLite view. These helpers keep that
shape identical across modules so the React GenericSection renders any of
them with no per-section frontend work.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

Section = tuple[str, str, str, Any, str, str, list[tuple[str, str]]]


def col(
    key: str,
    label: str,
    *,
    numeric: bool = True,
    direction: str | None = None,
    term: str | None = None,
) -> dict[str, Any]:
    return {"key": key, "label": label, "numeric": numeric, "direction": direction, "term": term}


def spark_col(key: str = "history", label: str = "Trend") -> dict[str, Any]:
    """A column whose values are bare number arrays — sectionCells renders
    them as an inline sparkline."""
    return col(key, label, numeric=False)


def ro(data_dir: str, db_name: str) -> sqlite3.Connection:
    """Read-only connection; the exporters never hold write access."""
    conn = sqlite3.connect(f"file:{Path(data_dir) / db_name}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fetch(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]


def scalar(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> Any:
    row = conn.execute(sql, tuple(params)).fetchone()
    return None if row is None else row[0]


def histories(
    conn: sqlite3.Connection,
    sql: str,
    params: Iterable[Any] = (),
    *,
    limit: int,
) -> dict[Any, list[float]]:
    """Group a `(key, value)` result ordered oldest-first into per-key
    number lists, keeping the newest `limit` points. NULL values are
    dropped — a sparkline gap reads as a broken line, which is worse than a
    slightly shorter one."""
    out: dict[Any, list[float]] = {}
    for key, value in conn.execute(sql, tuple(params)):
        if value is None:
            continue
        out.setdefault(key, []).append(float(value))
    return {k: v[-limit:] for k, v in out.items()}


def attach_history(
    rows: list[dict[str, Any]], hist: Mapping[Any, list[float]], key: str, field: str = "history"
) -> None:
    for r in rows:
        series = hist.get(r.get(key))
        # A one-point sparkline is a dot with no story — drop it (Design
        # Memory: "no tiny 2-point sparklines").
        r[field] = series if series and len(series) >= 3 else None


def tile(
    label: str,
    value: Any,
    band: str | None = None,
    tone: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    t: dict[str, Any] = {"label": label, "value": value, "band": band, "tone": tone}
    if history:
        t["history"] = history
    return t


def verdict(text: str, tone: str) -> dict[str, str]:
    return {"text": text, "tone": tone}


def round_or_none(v: Any, nd: int = 4) -> float | None:
    return None if v is None else round(float(v), nd)
