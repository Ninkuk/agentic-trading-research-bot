#!/bin/bash
# Nightly zero-dependency HTML dashboard into reports/dashboard.html (see
# dashboard.py). Runs after advisor (9:12pm) and before the daily-summary
# ntfy (9:15pm); a separate process, so a failure here cannot delay that alert.
set -uo pipefail
source "$(dirname "$0")/env.sh"
echo "[$(date '+%F %T')] start: dashboard"
uv run python deploy/launchd/dashboard.py
