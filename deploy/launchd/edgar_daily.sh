#!/bin/bash
# Evening EDGAR run (after the 10pm ET filing cutoff, the same day's index is
# complete). edgar is the one screener with no skip-and-continue and no
# backfill — a failed day is a permanent hole — so retry once after 15 min.
set -uo pipefail
source "$(dirname "$0")/env.sh"

echo "[$(date '+%F %T')] start: edgar"
if ! uv run python main.py edgar --db data/edgar.db --keep-days 90; then
    echo "[$(date '+%F %T')] edgar failed; retrying in 15 min" >&2
    sleep 900
    uv run python main.py edgar --db data/edgar.db --keep-days 90 \
        || echo "[$(date '+%F %T')] edgar retry FAILED" >&2
fi
