#!/bin/bash
# COT Friday run: all three report families, sequential (one Socrata host).
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "cftc"

for family in legacy disaggregated tff; do
    step_start "cftc --family $family"
    uv run python main.py cftc --db data/cftc.db --family "$family" \
        || echo "[$(date '+%F %T')] FAILED($?): cftc --family $family" >&2
done
