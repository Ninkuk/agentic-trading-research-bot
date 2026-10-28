# Sourced by every launchd job script. launchd provides no shell profile,
# no repo cwd, and no .env — this supplies all three.
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
# macOS keys a command-line binary's Desktop/Documents/Downloads grant on the
# executable's PATH, and the native installer puts every version at a new one:
# each update re-prompts, nobody answers at 06:32, and the open() behind the
# dialog blocks until the watchdog kills claude. This copy is the shipped
# binary at one fixed path, Anthropic signature intact, so a single grant
# satisfies every version. Refreshed by rename, never in place: a running
# copy keeps its inode.
claude_stable() {
    local stable="$HOME/.local/share/claude/versions/stable" target ver
    target=$(readlink "$HOME/.local/bin/claude" 2>/dev/null) || return 0
    [ -f "$target" ] || return 0
    ver="${target##*/}"
    mkdir -p "$stable"
    if [ ! -x "$stable/claude" ] || [ "$(cat "$stable/version" 2>/dev/null)" != "$ver" ]; then
        cp "$target" "$stable/claude.new" && mv -f "$stable/claude.new" "$stable/claude" \
            && echo "$ver" >"$stable/version"
    fi
    export PATH="$stable:$PATH"
}
claude_stable
# The shipped binary's hardened runtime refuses lldb, so wedge_autopsy can only
# read the blocked path from this ad-hoc re-signed copy (get-task-allow). Its
# grant is keyed on the signature hash and dies with every re-sign, so it is
# opt-in: `launchctl setenv CLAUDE_DEBUGGABLE 1`. It lives UNDER versions/
# because the CLI runs its native-install startup path only from there.
# Refresh after a CLI update:
#   D=~/.local/share/claude/versions/debuggable
#   cp ~/.local/share/claude/versions/<ver> $D/claude
#   codesign -s - -f --entitlements $D/entitlements.plist $D/claude
if [ -n "${CLAUDE_DEBUGGABLE:-}" ] && [ -x "$HOME/.local/share/claude/versions/debuggable/claude" ]; then
    export PATH="$HOME/.local/share/claude/versions/debuggable:$PATH"
fi
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
        case "$cmd" in *claude*) wedge_autopsy "$cmd_pid" "${JOB_LABEL:-$cmd}" ;; esac
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

# Capture a wedged claude BEFORE it is killed: wedge_autopsy <pid> <label>.
# Every observed wedge is the main thread blocked in openat() with the event
# loop frozen, so the process itself can never log the path; the only record
# is from outside. lldb attaches only to the CLAUDE_DEBUGGABLE copy (see PATH
# above); on the shipped binary the sample/lsof files still land.
wedge_autopsy() {
    local pid="$1" label
    label=$(echo "$2" | tr ' /' '--')
    local dir="logs/claude-debug/autopsy-$label-$(date '+%F_%H%M%S')"
    mkdir -p "$dir"
    ps -o pid,ppid,stat,etime,%cpu,command -p "$pid" >"$dir/ps.txt" 2>&1
    for c in $(pgrep -P "$pid"); do ps -o pid,ppid,stat,etime,command -p "$c" | tail -1; done >>"$dir/ps.txt" 2>&1
    lsof -nP -p "$pid" >"$dir/lsof.txt" 2>&1
    sample "$pid" 2 -file "$dir/sample.txt" >/dev/null 2>&1
    # lldb_autopsy.py names the path and then forces the blocked open to
    # return -1, so claude's own debug log also records it before the kill.
    lldb -p "$pid" --batch -o "command script import deploy/launchd/lldb_autopsy.py" \
        >"$dir/lldb.txt" 2>&1 &
    local lpid=$! waited=0
    while [ "$waited" -lt 25 ] && kill -0 "$lpid" 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
    done
    kill "$lpid" 2>/dev/null
    wait "$lpid" 2>/dev/null
    sleep 3
    local leaf path
    leaf=$(grep -m1 -oE "[a-zA-Z_0-9\$]+  \(in libsystem_kernel" "$dir/sample.txt" 2>/dev/null | head -1 | sed 's/  (in libsystem_kernel//')
    path=$(grep -m1 "^AUTOPSY_PATH: " "$dir/lldb.txt" 2>/dev/null | cut -c15-220)
    echo "[$(date '+%F %T')] AUTOPSY: $dir leaf=${leaf:-?} path=${path:-unread}" >&2
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

# Debug log path for ONE headless claude invocation. The startup wedge leaves
# no transcript and no stderr line, so this file is the only evidence of what
# the process did before the watchdog killed it. logs/ is gitignored.
claude_debug_file() {
    mkdir -p logs/claude-debug
    # ~85KB per run, six runs a day: keep two weeks, enough to cover a wedge
    # that is only noticed from the weekly dashboard.
    find logs/claude-debug -name '*.log' -mtime +14 -delete 2>/dev/null
    echo "logs/claude-debug/$1-$(date '+%F_%H%M%S').log"
}

# Fail-fast startup probe, run BEFORE a real headless job: claude_probe <secs> <job>.
# `claude -p` sometimes wedges at startup (main thread blocked in openat, see
# wedge_autopsy) until the 1200s cap; the probe turns that into a ~90s FAILED:
# line (matches health.py's markers) and the caller skips the job. One haiku
# turn, no session file, no tools needed. Any nonzero status fails the same
# way -- the CLI sometimes exits with an auth error instead of wedging.
claude_probe() {
    local limit="$1"
    local job="$2"
    run_with_timeout "$limit" \
        claude -p "Reply with exactly: ok" --model haiku --max-turns 1 \
        --no-session-persistence --permission-mode default --output-format json \
        --debug-file "$(claude_debug_file "$job-probe")" >/dev/null
    local status=$?
    if [ "$status" -ne 0 ]; then
        echo "[$(date '+%F %T')] FAILED: claude startup probe status $status — headless claude wedged or errored; skipping $job. See logs/claude-debug/ (AUTOPSY line above on a wedge)" >&2
    fi
    return "$status"
}
