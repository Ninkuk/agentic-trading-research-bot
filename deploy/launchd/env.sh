# Sourced by every launchd job script. launchd provides no shell profile,
# no repo cwd, and no .env — this supplies all three.
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

# Run-duration instrumentation. job_start records t0 and installs an EXIT trap,
# so the matching end line is emitted on EVERY exit path -- including one taken
# by `set -e` on a failing command, where a trailing call would never run.
# Setting the trap inside job_start (not at file scope) guarantees JOB_T0 and
# JOB_LABEL are already set before the trap can fire, which matters under `set -u`.
job_start() {
    JOB_T0=$(date +%s)
    JOB_LABEL="$*"
    echo "[$(date '+%F %T')] start: $*"
    # A signal-terminated process sees $? == 0 in its EXIT trap (only `set -e`
    # aborts and explicit `exit N` preserve the real status there), so a job
    # terminated by a signal -- e.g. a human `kill` after noticing a hang --
    # would otherwise log a false "exit 0" at exactly the moment that matters
    # most. (daily_summary.py's hang detection is detection-only: it reports
    # a job running past its budget, it never kills or restarts one.)
    # Re-raise the conventional 128+N status via a signal trap so it reaches
    # job_end intact; install the EXIT trap last so it still fires exactly
    # once, after these have set $? for it to read.
    #
    # Bash defers a trapped signal until the current foreground command
    # finishes, so a manual `kill <bashpid>` sent while a long-running
    # foreground command (e.g. `uv run python ...`) is executing can appear
    # to do nothing -- the trap only runs once that command returns control
    # to this shell. `launchctl kill`, which signals the whole process
    # group, reaches the foreground command directly and fires the trap
    # immediately.
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    trap 'job_end "$?"' EXIT
}

job_end() {
    echo "[$(date '+%F %T')] end: $JOB_LABEL ($(( $(date +%s) - JOB_T0 ))s, exit $1)"
}

# Per-step marker for scripts that run several sub-steps in one job (e.g. a
# family/ticker loop, or a step() helper). Bash only has ONE EXIT trap per
# shell, so calling job_start per step would repeatedly clobber JOB_T0 /
# JOB_LABEL and leave the final end line reporting just the last step's
# duration under the last step's name. step_start only echoes a progress
# line -- it never touches the whole-run timer or the trap.
#
# Emits `step:`, NOT `start:` -- deliberately distinct from job_start's line
# shape. A `start:` line means "a run began"; daily_summary.py's scan_log
# counts only those for its "N runs in 24h" headline, and its hang-detector
# (last_progress) needs to tell "the run started" apart from "the run is
# still making progress" while still treating both as evidence the job is
# alive. Before this, step_start emitted `start:` too, so a multi-step
# wrapper's last_start picked up the CURRENT STEP's timestamp under a "run
# start" label, silently turning a whole-run budget into a per-step one
# (cftc_weekly.sh: 3x; preopen_batch.sh: 4x) and inflating the run count by
# the same factor.
step_start() {
    echo "[$(date '+%F %T')] step: $*"
}
