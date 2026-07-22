#!/bin/bash
# COT Friday run: all three report families, sequential (one Socrata host).
set -uo pipefail
source "$(dirname "$0")/env.sh"
job_start "cftc"

for family in legacy disaggregated tff; do
    step_start "cftc --family $family"
    # Capture $? into `rc` BEFORE it's used: word expansion runs $(date) first,
    # which resets $? to 0, so `echo "...FAILED($?)..."` on the `||` branch
    # always prints 0 -- verified: bash -c 'false || echo "$(date) FAILED($?)"'.
    uv run python main.py cftc --db data/cftc.db --family "$family" || {
        rc=$?
        echo "[$(date '+%F %T')] FAILED($rc): cftc --family $family" >&2
    }
done
