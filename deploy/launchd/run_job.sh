#!/bin/bash
# Generic launchd entrypoint: run_job.sh <screener> [args...]
# Every plist that needs a single main.py invocation routes through here.
#
# NOT `exec`: exec replaces this shell, leaving no process to run env.sh's EXIT
# trap, so the run would log `start:` and never `end:`. The extra shell process
# is the price of a duration line.
set -euo pipefail
source "$(dirname "$0")/env.sh"
job_start "$@"
uv run python main.py "$@"
