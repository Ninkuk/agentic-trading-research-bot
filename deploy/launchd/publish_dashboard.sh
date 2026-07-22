#!/bin/bash
# Publish reports/dashboard.html to the gh-pages branch behind GitHub Pages
# (see publish_dashboard.py). Runs at 9:20pm, AFTER the 9:15pm daily-summary
# ntfy, so a hung push can neither delay nor suppress that health alert.
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "publish dashboard"
uv run python deploy/launchd/publish_dashboard.py
