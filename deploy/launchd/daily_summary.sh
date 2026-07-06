#!/bin/bash
# Nightly ntfy summary of the day's scheduled runs (see daily_summary.py).
set -uo pipefail
source "$(dirname "$0")/env.sh"
echo "[$(date '+%F %T')] start: daily summary"
uv run python deploy/launchd/daily_summary.py
