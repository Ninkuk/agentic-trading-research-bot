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

# Hard wall-clock cap for ONE foreground command: run_with_timeout <secs> cmd...
# macOS ships neither timeout(1) nor gtimeout, so this is a plain bash
# watchdog -- run the command in the background and race a sleeper against it.
#
# Why a cap exists at all: on 2026-08-04 the journal slot sat wedged for 7h11m
# on 4s of CPU (stalled inside a `claude -p` MCP call), holding its launchd
# slot the whole time. launchd will not re-spawn a job while the instance is
# alive, and daily_summary.py's hang tier is DETECTION ONLY by design (see
# hung_jobs' docstring) -- so nothing in the system could reap it. The cap has
# to live in the job itself.
#
# Keep the cap BELOW daily_summary.py's _HUNG_SLOW_MIN (60min) for these jobs:
# a wedge should die and fail loudly on its own run rather than survive to
# collide with tomorrow's.
#
# Returns the command's status, or 124 (the conventional timeout status) when
# the cap fired. The FAILED: line is what daily_summary.py's _BAD markers
# match, so a killed run reports as a failure even if it died after writing
# its rows -- silence here would read as success.
#
# Polls with a FOREGROUND `sleep 1` rather than racing a background
# `( sleep "$limit"; kill ... ) &` sleeper. The sleeper version is the obvious
# shape and it is wrong: on the NORMAL path the command finishes first, and
# killing the sleeper subshell orphans the `sleep` still inside it (reparented
# to init, so it cannot be reaped by PID either). That orphan holds the job's
# inherited stdout/stderr for the remainder of the cap -- up to 20 minutes of a
# stray process in the job's group, which is the very "still running" symptom
# this function exists to remove. Caught by
# test_run_with_timeout_passes_through_a_fast_commands_own_status, which hung.
# Here the only other child is a 1s foreground sleep that always completes.
run_with_timeout() {
    local limit="$1"; shift
    local cmd="$1"

    "$@" &
    local cmd_pid=$!

    local waited=0
    while [ "$waited" -lt "$limit" ] && kill -0 "$cmd_pid" 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
    done

    # A plain variable, not an exit-status guess: a command may legitimately
    # return 124/143 on its own, so only this loop may claim the cap fired.
    local timed_out=0
    if kill -0 "$cmd_pid" 2>/dev/null; then
        timed_out=1
        # TERM first so claude can close its MCP children; KILL as backstop.
        kill -TERM "$cmd_pid" 2>/dev/null
        sleep 5
        kill -KILL "$cmd_pid" 2>/dev/null
    fi

    local status=0
    wait "$cmd_pid" || status=$?

    # On the killed path bash also prints its own job-control notice for the
    # reaped command ("... Terminated: 15  \"$@\""). Left alone deliberately:
    # it carries the PID and signal, and it contains none of daily_summary.py's
    # _BAD markers, so it cannot be misread as an additional failure.
    if [ "$timed_out" -eq 1 ]; then
        echo "[$(date '+%F %T')] FAILED: $cmd exceeded ${limit}s — killed" >&2
        status=124
    fi
    return "$status"
}
