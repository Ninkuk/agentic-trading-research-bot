# Sourced by every launchd job script. launchd provides no shell profile,
# no repo cwd, and no .env — this supplies all three.
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi
