"""Selection rules for the research funnel: which candidate-screen names have
no thesis yet, and which theses have a dated reopen trigger that has come due.

Pure by design -- every function here takes already-read inputs (filenames,
ledger lines, symbols, a Phoenix date) and returns plain data. The impure
reads live in __main__.py's sibling CLI. This module is the CANONICAL home
for two rules that were previously duplicated across deploy/launchd/:

  * the thesis index (newest research/<TICKER>-<DATE>.md per ticker), and
  * the verdicts.log "only a ticker's newest line counts" rule.

deploy/launchd/research_nightly.py and deploy/launchd/dashboard_lib/data.py
both import from here rather than keeping private copies -- a re-researched
name must retire its old trigger identically everywhere, or the dashboard and
the sweep disagree about what is still open.

Not registered in registry.py: this is a helper, not a data pipeline.
"""

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

THESIS_RE = re.compile(r"^([A-Z0-9.\-]+)-(\d{4}-\d{2}-\d{2})\.md$")

# Two patterns, one rule. The sweep wants dated triggers only (an event:
# trigger has no due date and is grep-only by design); the dashboard renders
# both. Keeping them adjacent is what stops the pair from drifting.
REOPEN_DATED_RE = re.compile(r"\breopen=(\d{4}-\d{2}-\d{2}):(\S+)")
REOPEN_FIELD_RE = re.compile(r"\breopen=(\d{4}-\d{2}-\d{2}|event):(\S+)")


def index_theses(filenames: Iterable[str]) -> dict[str, str]:
    """{TICKER: newest thesis date} from research/<TICKER>-<YYYY-MM-DD>.md
    filenames. Non-matching names (README.md, verdicts.log) are ignored."""
    newest: dict[str, str] = {}
    for name in filenames:
        m = THESIS_RE.match(name)
        if not m:
            continue
        ticker, thesis_date = m.group(1), m.group(2)
        if thesis_date > newest.get(ticker, ""):
            newest[ticker] = thesis_date
    return newest


def list_theses(research_dir: Path) -> dict[str, str]:
    """index_theses over a directory. A missing directory is empty, not an
    error -- a fresh checkout has no research/."""
    if not research_dir.is_dir():
        return {}
    return index_theses(p.name for p in research_dir.iterdir())


def newest_verdict_lines(lines: Iterable[str]) -> dict[str, tuple[str, str]]:
    """verdicts.log lines -> {ticker: (thesis_date, line)}. Only each ticker's
    NEWEST line counts (ties: later line wins) -- re-researching a name
    retires the older thesis's fields. Comment and short lines are skipped."""
    newest: dict[str, tuple[str, str]] = {}
    for raw in lines:
        parts = raw.split()
        if len(parts) < 2 or raw.lstrip().startswith("#"):
            continue
        if parts[1] not in newest or parts[0] >= newest[parts[1]][0]:
            newest[parts[1]] = (parts[0], raw)
    return newest


def due_reopens(
    newest: Mapping[str, tuple[str, str]], today: str
) -> list[tuple[str, str, str, str]]:
    """Dated reopen triggers that have come due: reopen_date <= today
    (Phoenix). No floor -- a trigger is retired only by re-researching the
    name, so one still sitting past its date is genuinely unanswered, and an
    on-demand sweep must not drop it for being invoked on the wrong day.
    event: triggers never surface here. Sorted by (due, ticker).

    Returns (ticker, due, slug, thesis_date) tuples."""
    due: list[tuple[str, str, str, str]] = []
    for ticker, (thesis_date, line) in newest.items():
        m = REOPEN_DATED_RE.search(line)
        if m and m.group(1) <= today:
            due.append((ticker, m.group(1), m.group(2), thesis_date))
    due.sort(key=lambda row: (row[1], row[0]))
    return due


def unresearched(symbols: Iterable[str], theses: Mapping[str, str]) -> list[str]:
    """Screen symbols with no thesis of any date, in screen order. No
    staleness gate: staleness is what the reopen convention is for, and
    research_nightly.py already sweeps stale flagged/held names nightly."""
    return [s for s in symbols if s not in theses]
