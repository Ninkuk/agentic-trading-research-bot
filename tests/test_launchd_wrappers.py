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
