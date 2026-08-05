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

import argparse
import datetime as dt
import json
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

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


def read_candidates(db_path: str) -> tuple[list[str], str | None]:
    """Screen symbols in screen order, or ([], error class name). Delegates
    to candidates.screen() rather than restating its SQL, so the sweep and
    `main.py candidates` can never disagree about what qualifies."""
    from sources.combiners.composite import candidates

    try:
        conn = candidates.connect_ro(db_path)
        try:
            return [row["symbol"] for row in candidates.screen(conn)], None
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 -- total by design
        return [], type(e).__name__


def read_verdicts(research_dir: Path) -> tuple[dict[str, tuple[str, str]], str | None]:
    """Newest verdict line per ticker, or ({}, error class name)."""
    try:
        text = (research_dir / "verdicts.log").read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001 -- total by design
        return {}, type(e).__name__
    return newest_verdict_lines(text.splitlines()), None


def build(
    db_path: str,
    research_dir: Path,
    today: str,
    kind: str,
    max_n: int | None,
) -> dict[str, Any]:
    """The two worklists plus whatever went wrong reading them. Reopens lead
    -- they answer a live question on a name that may be held."""
    errors: list[str] = []
    new: list[str] = []
    reopens: list[tuple[str, str, str, str]] = []

    if kind in ("new", "both"):
        symbols, err = read_candidates(db_path)
        if err:
            errors.append(f"candidates unreadable ({err})")
        new = unresearched(symbols, list_theses(research_dir))
    if kind in ("reopen", "both"):
        newest, err = read_verdicts(research_dir)
        if err:
            errors.append(f"verdicts.log unreadable ({err})")
        reopens = due_reopens(newest, today)

    # Reopens first, then new names. --max is opt-in and NEVER silent: what
    # it drops is carried in the document and printed.
    dropped: list[str] = []
    if max_n is not None:
        ordered = [r[0] for r in reopens] + new
        keep = set(ordered[:max_n])
        dropped = ordered[max_n:]
        reopens = [r for r in reopens if r[0] in keep]
        new = [s for s in new if s in keep]

    return {
        "today": today,
        "new": new,
        "reopens": reopens,
        "dropped": dropped,
        "errors": errors,
    }


# Above this many names the SKILL re-confirms before dispatching. It is a
# prompt threshold, never a truncation -- see the plan's Task 5.
SWEEP_LARGE = 20


def format_worklist(doc: Mapping[str, Any]) -> list[str]:
    """Human-readable rendering. Empty is a normal, common result and says so
    rather than implying work exists."""
    out = [f"=== Research Sweep worklist — {doc['today']} ==="]
    for err in doc["errors"]:
        out.append(f"  ! {err}")

    reopens = doc["reopens"]
    out.append("")
    out.append(f"B. due reopens (<= today): {len(reopens)}")
    for ticker, due, slug, thesis_date in reopens:
        out.append(f"    {ticker}  due {due}  {slug}  (thesis {thesis_date})")

    new = doc["new"]
    out.append("")
    out.append(f"A. un-researched candidates: {len(new)}")
    for symbol in new:
        out.append(f"    {symbol}")

    if doc["dropped"]:
        out.append("")
        out.append(f"DROPPED by --max ({len(doc['dropped'])}): {', '.join(doc['dropped'])}")

    total = len(new) + len(reopens)
    out.append("")
    if total == 0:
        out.append("nothing to research — both worklists are empty.")
    else:
        out.append(f"{total} name(s). NOT A RECOMMENDATION — input to research-ticker.")
    if total > SWEEP_LARGE:
        out.append(
            f"LARGE SWEEP: {total} names (> {SWEEP_LARGE}). The session "
            "web-search budget is shared and unreadable mid-run; a long "
            "sweep may degrade later runs' search quality."
        )
    return out


def main(argv: list[str] | None = None, now_iso: str | None = None) -> int:
    from sources.common.clock import phx_date

    p = argparse.ArgumentParser(
        prog="worklist",
        description=(
            "Names needing research: candidate-screen entries with no thesis, "
            "plus theses whose dated reopen trigger has come due. Reads "
            "read-only; writes nothing; recommends nothing."
        ),
    )
    p.add_argument("--db", default="data/stocks.db")
    p.add_argument("--research-dir", default="research")
    p.add_argument("--kind", choices=("new", "reopen", "both"), default="both")
    p.add_argument("--max", dest="max_n", type=int, default=None)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    now_iso = now_iso or dt.datetime.now(dt.UTC).isoformat()
    doc = build(args.db, Path(args.research_dir), phx_date(now_iso), args.kind, args.max_n)
    if args.json:
        print(json.dumps(doc, indent=2))
    else:
        print("\n".join(format_worklist(doc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
