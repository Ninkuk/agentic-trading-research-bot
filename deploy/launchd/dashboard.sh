#!/bin/bash
# Runs after advisor (9:12pm) as the last nightly reporter; renders
# data.json and pings the dead-man's switch.
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "dashboard"
uv run python deploy/launchd/dashboard.py
