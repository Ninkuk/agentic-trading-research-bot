#!/bin/bash
# Publish the built dashboard/dist + reports/data.json to the gh-pages
# branch behind GitHub Pages (see publish_dashboard.py). Runs at 9:20pm, a
# separate process from the 9:13pm dashboard render, so a hung push can
# never block it.
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "publish dashboard"
uv run python deploy/launchd/publish_dashboard.py
