# Sourced by every launchd job script. launchd provides no shell profile,
# no repo cwd, and no .env — this supplies all three.
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

# Run-duration instrumentation. job_start records t0 and installs an EXIT trap
# so the end line is emitted on every exit path, including `set -e` aborts. The
# trap is set inside job_start so JOB_T0/JOB_LABEL exist before it can fire.
job_start() {
    JOB_T0=$(date +%s)
    JOB_LABEL="$*"
    echo "[$(date '+%F %T')] start: $*"
    # An EXIT trap sees $? == 0 for a signal-terminated process, so re-raise
    # the conventional 128+N via signal traps, installing the EXIT trap last
    # so it fires exactly once after these have set $?. Bash defers a trapped
    # signal until the foreground command returns; `launchctl kill` signals
    # the whole group and fires immediately.
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP
    trap 'job_end "$?"' EXIT
}

job_end() {
    echo "[$(date '+%F %T')] end: $JOB_LABEL ($(( $(date +%s) - JOB_T0 ))s, exit $1)"
}

# Per-step progress marker for multi-step jobs. Bash has ONE EXIT trap per
# shell, so calling job_start per step would clobber JOB_T0/JOB_LABEL;
# step_start only echoes. It emits `step:`, never `start:` --
# dashboard_lib/health.py counts `start:` lines for its run count and
# whole-run hang budget, so a per-step `start:` silently turns a run budget
# into a per-step one.
step_start() {
    echo "[$(date '+%F %T')] step: $*"
}

# Hard wall-clock cap for ONE foreground command: run_with_timeout <secs> cmd...
# macOS ships neither timeout(1) nor gtimeout. The cap lives in the job itself
# because nothing else can reap a wedge: launchd never re-spawns while the
# instance is alive, and dashboard_lib/health.py's hang tier is detection-only.
# Keep the cap BELOW health.py's HUNG_SLOW_MIN (60min) so a wedge dies loudly
# on its own run instead of colliding with tomorrow's.
# Returns the command's status, or 124 when the cap fired; the FAILED: line
# matches health.py's BAD_MARKERS so a killed run reports as a failure.
# Polls with a FOREGROUND `sleep 1`: a background `( sleep; kill ) &` sleeper,
# killed on the normal path, orphans its `sleep`, which holds the job's
# inherited stdout/stderr for the remainder of the cap.
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

    # Only this loop may claim the cap fired -- the command may legitimately
    # return 124/143 on its own.
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

    # Bash's job-control notice for the reaped command ("Terminated: 15 ...")
    # is left alone: it carries the PID and signal and matches no BAD_MARKERS.
    if [ "$timed_out" -eq 1 ]; then
        echo "[$(date '+%F %T')] FAILED: $cmd exceeded ${limit}s — killed" >&2
        status=124
    fi
    return "$status"
}

# run_with_timeout plus exactly ONE retry when the cap fired (124). The wedge
# class this targets is a transient stall inside the headless claude process
# while the machine around it stays healthy, so an immediate second attempt
# succeeds. Bounded at one: a second consecutive wedge is environmental and
# must fail loudly, not loop toward health.py's 60min hang tier. A non-124
# status is the command's own answer and is never retried -- that would double
# MCP fetches and claude spend on a deterministic failure. The first attempt's
# FAILED: line stays in the log so a rescued wedge still surfaces in the
# dashboard's problem scan; RETRY: is deliberately not in BAD_MARKERS.
run_with_timeout_retry() {
    local limit="$1"
    run_with_timeout "$@"
    local status=$?
    if [ "$status" -ne 124 ]; then
        return "$status"
    fi
    echo "[$(date '+%F %T')] RETRY: wedge killed at ${limit}s — one bounded retry" >&2
    run_with_timeout "$@"
}
