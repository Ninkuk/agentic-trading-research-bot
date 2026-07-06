#!/bin/bash
# Generic launchd entrypoint: run_job.sh <screener> [args...]
# Every plist that needs a single main.py invocation routes through here.
set -euo pipefail
source "$(dirname "$0")/env.sh"
echo "[$(date '+%F %T')] start: $*"
exec uv run python main.py "$@"
