#!/bin/bash
# Pre-open batch, serialized in one process so ordering never depends on
# launchd and the SEC rate limiter is shared: earnings -> stocks -> etfs
# -> reddit baseline. Skip-and-continue per job.
set -uo pipefail
source "$(dirname "$0")/env.sh"

step() {
    job_start "$@"
    uv run python main.py "$@" || echo "[$(date '+%F %T')] FAILED($?): $*" >&2
}

# Earnings watchlist = current portfolio holdings + the cboe_options catalog
# (equities only — indices and broad ETFs don't report earnings). Without
# --only the earnings monitor skips EDGAR 8-K confirmation entirely.
WATCH=$(uv run python - <<'PY'
import pathlib
import sqlite3

from sources.screeners.cboe_options.catalog import CATALOG

syms = {u.symbol for u in CATALOG if not u.is_index} - {"SPY", "QQQ", "IWM"}
db = pathlib.Path("data/portfolio.db")
if db.exists():
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()
    if row and row[0]:
        syms |= {s for (s,) in conn.execute(
            "SELECT symbol FROM positions WHERE snapshot_id = ?", (row[0],))}
print(" ".join(sorted(syms)))
PY
)

if [ -n "${WATCH:-}" ]; then
    # shellcheck disable=SC2086  # --only takes space-separated tickers
    step earnings --db data/earnings.db --only $WATCH
else
    echo "[$(date '+%F %T')] FAILED: empty earnings watchlist" >&2
fi
step stocks --db data/stocks.db --type s --keep-days 30
step stocks --db data/etfs.db --type e --keep-days 30
step reddit --db data/reddit.db --keep-days 90
echo "[$(date '+%F %T')] preopen batch done"
