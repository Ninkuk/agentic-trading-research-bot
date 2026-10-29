#!/bin/bash
# On-demand render + publish, kickstarted by .githooks/pre-push after a push
# to main (never scheduled; see install.py). The render skips the heartbeat
# because the dead-man's switch belongs to the 9:13pm nightly. The publish
# runs only if the render succeeded: publish_dashboard.py's freshness check
# reads data.json's mtime, so a failed render followed by a publish would
# ship the previous document under today's date.
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "publish now"
uv run python deploy/launchd/dashboard.py --no-heartbeat &&
    uv run python deploy/launchd/publish_dashboard.py
