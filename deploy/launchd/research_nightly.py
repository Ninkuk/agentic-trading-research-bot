"""Nightly autonomous research loop: select flagged/stale tickers, run
/research-ticker headlessly once per ticker, verify a thesis landed.

Phase 1 of the agentic roadmap: headless judgment tasks, human reads output.
Decision support only: the tool allowlist is read-only — order tools are
never listed.

Run from the repo root (the launchd wrapper guarantees it). Prints to
stdout; launchd routes it to logs/research-nightly.log. Exit 0 on an empty
selection or >=1 success; exit 1 iff every selected ticker failed.
"""

import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.common.clock import phx_date  # noqa: E402

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


# Read-only envelope for the headless run. NEVER add order tools here
# (place_*, cancel_*, review_*) — expanding this list is a deliberate,
# reviewed act (see the phase ladder in the spec). Bash is enumerated per
# entrypoint, never a catch-all (`uv run python *` would allow `python -c`,
# i.e. arbitrary code — the allowlist is the write-scope guarantee): the
# four entries below are the only Bash entrypoints the research-ticker skill
# uses. The journal entrypoint is the loop's ONE intended DB write — the
# skill's mandatory verdict-logging step appends decision rows to
# data/scorer.db.
ALLOWED_TOOLS = ",".join(
    [
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "Bash(uv run python -m sources.screeners.stock_analysis_screener.probe *)",
        "Bash(uv run python -m tools.valuation.reverse_dcf *)",
        "Bash(uv run python -m tools.options.implied_move *)",
        "Bash(uv run python main.py journal *)",
        "mcp__claude_ai_Robinhood_MCP__get_equity_quotes",
        "mcp__claude_ai_Robinhood_MCP__get_equity_historicals",
        "mcp__claude_ai_Robinhood_MCP__get_equity_fundamentals",
        "mcp__claude_ai_Robinhood_MCP__get_earnings_results",
        "mcp__claude_ai_Robinhood_MCP__get_earnings_calendar",
        "mcp__claude_ai_Robinhood_MCP__get_option_chains",
        "mcp__claude_ai_Robinhood_MCP__get_option_quotes",
        "mcp__claude_ai_Robinhood_MCP__get_option_instruments",
        "mcp__claude_ai_Robinhood_MCP__search",
    ]
)


def build_command(ticker: str, model: str) -> list[str]:
    return [
        "claude",
        "-p",
        f"/research-ticker {ticker}",
        "--model",
        model,
        "--allowedTools",
        ALLOWED_TOOLS,
        "--output-format",
        "json",
    ]


def parse_denials(stdout: str) -> list[str]:
    """Tool names claude was denied. Total: garbage in, [] out. Denials are
    the real diagnostic — a headless model can improvise a tool outside the
    allowlist and then misreport the denial as an MCP auth failure."""
    try:
        doc = json.loads(stdout)
        return [str(d.get("tool_name", d)) for d in doc.get("permission_denials", [])]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def verify_thesis(research_dir: Path, ticker: str, today: str, min_bytes: int = 2048) -> bool:
    """A fresh thesis is tonight's Phoenix-dated file above a floor that
    catches empty/aborted writes (a real thesis runs far larger)."""
    p = research_dir / f"{ticker}-{today}.md"
    try:
        return p.stat().st_size >= min_bytes
    except OSError:
        return False


def _default_invoke(cmd: list[str], timeout_s: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
        return proc.returncode, proc.stdout
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  invoke failed ({type(e).__name__})")
        return 124, ""


def run_night(
    candidates: list[str],
    invoke,
    research_dir: Path,
    today: str,
    model: str,
    timeout_s: int = 1200,
) -> tuple[list[str], list[str]]:
    """One claude process per ticker, sequentially; a failure never stops
    the night. Success == a fresh verified thesis, not claude's exit code."""
    ok: list[str] = []
    failed: list[str] = []
    for ticker in candidates:
        rc, out = invoke(build_command(ticker, model), timeout_s)
        denials = parse_denials(out)
        if denials:
            print(f"  {ticker}: permission_denials: {', '.join(denials)}")
        if rc == 0 and verify_thesis(research_dir, ticker, today):
            print(f"  {ticker}: thesis landed")
            ok.append(ticker)
        else:
            print(f"  {ticker}: FAILED (rc={rc}, fresh thesis absent or too small)")
            failed.append(ticker)
    return ok, failed


def main(argv=None, invoke=None, now_iso=None) -> int:
    max_n = int(os.environ.get("RESEARCH_NIGHTLY_MAX", "3"))
    stale_days = int(os.environ.get("RESEARCH_STALE_DAYS", "30"))
    model = os.environ.get("RESEARCH_NIGHTLY_MODEL", "opus")
    composite_db = os.environ.get("RESEARCH_COMPOSITE_DB", "data/composite.db")
    portfolio_db = os.environ.get("RESEARCH_PORTFOLIO_DB", "data/portfolio.db")
    research_dir = Path(os.environ.get("RESEARCH_DIR", "research"))

    if max_n <= 0:
        print("research-nightly disabled (RESEARCH_NIGHTLY_MAX=0)")
        return 0

    now_iso = now_iso or dt.datetime.now(dt.UTC).isoformat()
    today = phx_date(now_iso)
    invoke = invoke or _default_invoke

    candidates = select_candidates(
        read_flagged(composite_db),
        read_held(portfolio_db),
        list_theses(research_dir),
        today,
        max_n,
        stale_days,
    )
    if not candidates:
        print("nothing to research (no new flags, nothing stale)")
        return 0

    print(
        f"selected: {', '.join(candidates)} (max={max_n}, stale_days={stale_days}, model={model})"
    )
    ok, failed = run_night(candidates, invoke, research_dir, today, model)
    print(f"done: {len(ok)} ok, {len(failed)} failed of {len(candidates)} selected")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
