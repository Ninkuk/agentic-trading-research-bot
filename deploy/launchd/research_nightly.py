"""Nightly autonomous research loop: select flagged/stale tickers, run
/research-ticker headlessly once per ticker, verify a thesis landed.

Phase 1 of the agentic roadmap (spec: docs/superpowers/specs/
2026-07-22-nightly-research-loop-design.md). Decision support only: the
tool allowlist is read-only — order tools are never listed.

Run from the repo root (the launchd wrapper guarantees it). Prints to
stdout; launchd routes it to logs/research-nightly.log. Exit 0 on an empty
selection or >=1 success; exit 1 iff every selected ticker failed.
"""

import datetime as dt
import re
import sqlite3
from pathlib import Path

THESIS_RE = re.compile(r"^([A-Z0-9.\-]+)-(\d{4}-\d{2}-\d{2})\.md$")


def list_theses(research_dir: Path) -> dict[str, str]:
    """{TICKER: newest thesis date} from research/<TICKER>-<YYYY-MM-DD>.md."""
    newest: dict[str, str] = {}
    if not research_dir.is_dir():
        return newest
    for p in research_dir.iterdir():
        m = THESIS_RE.match(p.name)
        if not m:
            continue
        ticker, date = m.group(1), m.group(2)
        if date > newest.get(ticker, ""):
            newest[ticker] = date
    return newest


def _read_symbols(db_path: str, query: str) -> list[str]:
    """One-column symbol query against a read-only DB; total — a missing
    file, table, or view yields [] (a partial pipeline is not an error)."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return [row[0] for row in conn.execute(query)]
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return []


def read_flagged(db_path: str) -> list[str]:
    return _read_symbols(db_path, "SELECT symbol FROM v_flagged")


def read_held(db_path: str) -> list[str]:
    return _read_symbols(db_path, "SELECT symbol FROM v_latest_positions")


def select_candidates(
    flagged: list[str],
    held: list[str],
    theses: dict[str, str],
    today: str,
    max_n: int,
    stale_days: int,
) -> list[str]:
    """Priority: never-researched flags, stale flags, stale held. Sorted
    within each bucket for deterministic nights; capped at max_n."""
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=stale_days)).isoformat()

    def stale(t: str) -> bool:
        return theses.get(t, "") < cutoff  # absent ("") is infinitely stale

    new_flags = sorted(t for t in flagged if t not in theses)
    stale_flags = sorted(t for t in flagged if t in theses and stale(t))
    stale_held = sorted(t for t in held if t not in flagged and stale(t))

    out: list[str] = []
    for t in new_flags + stale_flags + stale_held:
        if t not in out:
            out.append(t)
    return out[:max_n]
