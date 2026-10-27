"""Tolerant field coercion shared by the fetchers' pure parsers. Every source
hands back strings (CSV cells, JSON values) that are sometimes blank or
non-numeric; the parsers map those to None rather than raising, so one bad
cell drops a value, never a row."""

from collections.abc import Callable


def to_float(value) -> float | None:
    """int/float/numeric-string -> float; anything else (None, '', 'lots',
    bool) -> None."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def coerce[T](raw, cast: Callable[[str], T]) -> T | None:
    """Strip a string cell and apply ``cast``; blank/unparseable -> None."""
    raw = (raw or "").strip() if isinstance(raw, str) or raw is None else raw
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def to_int(raw) -> int | None:
    """Integer tolerant of a trailing '.0' (FINRA emits it for share counts).
    A header row's non-numeric cell fails float() -> None -> line dropped."""
    return coerce(raw, lambda v: int(float(v)))


def yyyymmdd_to_iso(raw) -> str | None:
    """'20260131' -> '2026-01-31'; anything else -> None."""
    s = (raw or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return None


def date_prefix(v) -> str | None:
    """First ten characters of a source date/datetime string, or None when blank."""
    return (v or "")[:10] or None
