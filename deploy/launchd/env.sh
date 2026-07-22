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
    trap 'job_end "$?"' EXIT
}

job_end() {
    echo "[$(date '+%F %T')] end: $JOB_LABEL ($(( $(date +%s) - JOB_T0 ))s, exit $1)"
}

# Per-step marker for scripts that run several sub-steps in one job (e.g. a
# family/ticker loop, or a step() helper). Bash only has ONE EXIT trap per
# shell, so calling job_start per step would repeatedly clobber JOB_T0 /
# JOB_LABEL and leave the final end line reporting just the last step's
# duration under the last step's name. step_start only echoes the start
# line -- it never touches the whole-run timer or the trap.
step_start() {
    echo "[$(date '+%F %T')] start: $*"
}
