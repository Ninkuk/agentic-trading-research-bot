#!/bin/sh
# launchd tick for the two-clock scheduler (macOS deployment — see
# docs/DEPLOYMENT_ROADMAP.md). Single-runner is guaranteed by launchd
# itself: it never starts a second instance of a running job label, so the
# Linux cron wrapper's flock is unnecessary here (and macOS ships no flock).
# A StartInterval tick missed during sleep fires once on wake, which the
# scheduler's at-or-after triggers + idempotent trigger keys absorb.
set -eu
cd "$(dirname "$0")/.."

# launchd PATH is minimal: uv (homebrew) + claude (the gate's default
# claude-cli backend) live outside it.
PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH

# FRED/EIA/NASS keys + PIPELINE_EQUITY (and optional PIPELINE_FRACTIONAL)
# for promote; keys are query params, never logged.
set -a
. ./.env
set +a

exec /opt/homebrew/bin/uv run python main.py schedule \
    --db data/schedule.db --data-dir data --run
