#!/bin/bash
# Afternoon decision-journal sync via headless claude (subscription auth) ->
# Robinhood MCP order history -> main.py journal. Same silent failure mode
# as the portfolio slot (a claude session can "succeed" with stale MCP
# auth), and the same loud check: an empty-fill day still writes a
# journal_runs header, so a missing header means the sync itself failed.
set -uo pipefail
source "$(dirname "$0")/env.sh"

echo "[$(date '+%F %T')] start: journal sync"
claude -p "/journal-sync" \
    --model haiku \
    --allowedTools "mcp__claude_ai_Robinhood_MCP__get_accounts,mcp__claude_ai_Robinhood_MCP__get_equity_orders,Write,Bash(uv run python main.py journal *)" \
    --output-format json

# strftime, NOT datetime(): ran_at is isoformat with a 'T' separator, and
# datetime() renders with a space — 'T' > ' ' lexicographically, so a plain
# datetime() cutoff would count ANY same-UTC-date run as fresh.
FRESH=$(sqlite3 data/scorer.db \
    "SELECT COUNT(*) FROM journal_runs WHERE ran_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 hours');" \
    2>/dev/null || echo 0)
if [ "${FRESH:-0}" -lt 1 ]; then
    echo "[$(date '+%F %T')] STALE: no journal run in the last 2h — check Robinhood MCP auth" >&2
    exit 1
fi
echo "[$(date '+%F %T')] journal sync fresh"
