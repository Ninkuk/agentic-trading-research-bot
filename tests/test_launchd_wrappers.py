"""Guards for the bash instrumentation in deploy/launchd/.

env.sh + run_job.sh (27 of 35 jobs) + 8 standalone wrappers have no other
test coverage. Nothing here runs a real wrapper or a real launchctl -- these
are small, fast guards against regressions that would silently remove
duration/hang-detection history, not a bash test suite.
"""

import re
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHD = REPO_ROOT / "deploy" / "launchd"

# Matches `exec` used as a command (start of a statement), not as a
# substring of another word and not merely mentioned in a comment (callers
# strip the comment portion of each line before applying this).
_EXEC_CMD = re.compile(r"(?<![\w-])exec(?=\s|$)")


def _code_only(line):
    """The portion of a shell line before any `#` comment."""
    return line.split("#", 1)[0]


# The two headless slots that drive a skill through `claude -p`, each paired
# with the skill it loads. `--permission-mode default` makes each wrapper's
# --allowedTools a real envelope, so a Robinhood getter the skill instructs
# but the wrapper omits is denied outright -- and headless there is nobody to
# approve it, so the job produces no snapshot and exits 1.
_MCP_SLOTS = {
    "portfolio_snapshot.sh": ".claude/skills/account-positions/SKILL.md",
    "journal_sync.sh": ".claude/skills/journal-sync/SKILL.md",
    "order_execution.sh": ".claude/skills/execute-queue/SKILL.md",
}

# Getters a skill names but deliberately does NOT call in this slot. Each
# entry is a decision, not an oversight -- keep the reason with it.
_NOT_GRANTED = {
    # Tax lots are read at decision time by `kill-thesis`; the snapshot
    # deliberately does not persist them (account-positions SKILL.md).
    "get_equity_tax_lots",
    # execute-queue names get_accounts precisely to say it is NOT granted:
    # its buying-power figure is unreliable per its own tool contract, and
    # get_portfolio is the granted source in that slot.
    "get_accounts",
}

# Widened beyond getters when the order-execution slot landed: its skill
# names `place_equity_order`/`review_equity_order`, which the wrapper must
# grant just as deterministically as any getter.
_TOOL = re.compile(r"`((?:get|place|review)_[a-z_]+)`")


def test_headless_slots_allowlist_every_getter_their_skill_calls():
    """A skill gaining a Robinhood getter without its wrapper gaining the
    matching --allowedTools entry is a silent, deterministic outage: the
    2026-07-23 option-capture work added get_option_positions/get_option_orders
    to the skills and the portfolio/journal slots failed every weekday after.
    Anything the skill names must be granted or explicitly not-granted."""
    for wrapper, skill in _MCP_SLOTS.items():
        allowlist = (LAUNCHD / wrapper).read_text()
        named = set(_TOOL.findall((REPO_ROOT / skill).read_text()))
        assert named, f"no getters found in {skill} -- extraction broke"
        ungranted = sorted(
            g for g in named - _NOT_GRANTED if f"Robinhood_MCP__{g}" not in allowlist
        )
        assert ungranted == [], (
            f"{wrapper} omits getter(s) {ungranted} that {skill} instructs; "
            f"add to --allowedTools or to _NOT_GRANTED with a reason"
        )


def test_order_execution_wrapper_never_grants_orders_wildcard():
    """`Bash(uv run python main.py orders *)` would include `orders queue`,
    letting the headless session author its own orders — the human-only
    invariant would be prose, not structure. Grants must stay enumerated per
    subcommand, and queue/resolve/reconcile must never appear."""
    text = (LAUNCHD / "order_execution.sh").read_text()
    assert "main.py orders *" not in text
    for sub in ("preflight", "plan", "record"):
        assert f"Bash(uv run python main.py orders {sub} *)" in text
    for sub in ("queue", "resolve", "reconcile"):
        assert f"orders {sub} *" not in text


def test_order_execution_wrapper_conventions():
    text = (LAUNCHD / "order_execution.sh").read_text()
    assert text.count("data/orders.db") >= 3  # preflight --db + two sqlite3 freshness reads
    assert "strftime('%Y-%m-%dT%H:%M:%S'" in text  # not datetime()
    assert "cancel_equity_order" not in text
    assert "get_accounts" not in text  # buying power must come from get_portfolio
    assert "status IN ('queued','planned')" in text  # STUCK covers the slow-session drift
    assert "--permission-mode default" in text


def test_order_execution_job_is_gated_behind_go_live(monkeypatch):
    """install.py must NOT schedule the order-execution job on a routine full
    install — go-live is an explicit human step after the first-run
    verification. (Even --dry-run writes plists launchd loads at login, so
    the gate has to be at JOBS-construction time.)"""
    import importlib

    from deploy.launchd import install

    monkeypatch.delenv("ORDERS_GO_LIVE", raising=False)
    importlib.reload(install)
    assert "order-execution" not in install.JOBS

    monkeypatch.setenv("ORDERS_GO_LIVE", "1")
    importlib.reload(install)
    assert "order-execution" in install.JOBS
    intervals = install.JOBS["order-execution"][1]
    assert {(i["Hour"], i["Minute"]) for i in intervals} == {(6, 32), (7, 32)}

    monkeypatch.delenv("ORDERS_GO_LIVE", raising=False)
    importlib.reload(install)


def test_run_job_sh_never_execs():
    """`exec` replaces the shell running run_job.sh, leaving no process to
    run env.sh's EXIT trap -- the run would log `start:` and never `end:`.
    A comment mentioning the word (as run_job.sh's own does, explaining why
    NOT to use it) is fine; only the command form is banned."""
    text = (LAUNCHD / "run_job.sh").read_text()
    offending = [line for line in text.splitlines() if _EXEC_CMD.search(_code_only(line))]
    assert offending == [], f"exec used as a command in run_job.sh: {offending!r}"


def test_every_wrapper_except_env_and_status_calls_job_start():
    """Every job-running wrapper must call job_start so daily_summary.py has
    a `start:`/`end:` pair to read. env.sh defines job_start (it doesn't
    call it) and status.sh is a read-only report, not a job -- both are
    correctly exempt."""
    skip = {"env.sh", "status.sh"}
    scripts = [p for p in sorted(LAUNCHD.glob("*.sh")) if p.name not in skip]
    assert scripts, "no launchd wrapper scripts found"
    missing = [p.name for p in scripts if "job_start" not in p.read_text()]
    assert missing == [], f"wrapper(s) never call job_start: {missing}"


def test_step_start_emits_step_not_start():
    """step_start's line shape must stay `step:`, distinct from job_start's
    `start:` -- daily_summary.py's scan_log counts only `start:` lines toward
    the "N runs in 24h" headline, and last_progress needs to tell "the run
    started" apart from "the run is still making progress". If step_start
    reverts to emitting `start:`, a multi-step wrapper (cftc_weekly.sh: 3
    families, preopen_batch.sh: 4 steps) silently inflates that headline by
    the step count, with nothing failing. Extracted just this function's body
    (not grepped across the whole file) because job_start legitimately
    contains `start:` too."""
    body = (LAUNCHD / "env.sh").read_text().split("step_start() {", 1)[1].split("}", 1)[0]
    assert "step:" in body
    assert "start:" not in body


def test_env_sh_exit_trap_emits_exactly_one_end_line_with_the_real_exit_code(tmp_path):
    """env.sh's EXIT trap must fire exactly once and log the ACTUAL exit
    code, even when `set -e` aborts the script on a failing command -- this
    is the mechanism run_job.sh's no-`exec` guard exists to protect. Sources
    the real env.sh from a throwaway script; never invokes a real wrapper."""
    script = tmp_path / "probe.sh"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            set -euo pipefail
            source "{LAUNCHD / "env.sh"}"
            job_start "probe"
            (exit 5)
            """
        )
    )
    script.chmod(0o755)

    result = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=30)

    end_lines = [line for line in result.stdout.splitlines() if "] end: " in line]
    assert len(end_lines) == 1, result.stdout
    assert "exit 5" in end_lines[0]
