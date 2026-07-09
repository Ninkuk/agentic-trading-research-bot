#!/bin/bash
# Post-close portfolio snapshot via headless claude (subscription auth) ->
# Robinhood MCP -> main.py portfolio. This is the schedule's one silent
# failure mode (a claude session can "succeed" while the MCP connector's
# auth is stale), so verify a fresh snapshot actually landed and fail loudly
# if not — the log line is the alert.
set -uo pipefail
source "$(dirname "$0")/env.sh"

echo "[$(date '+%F %T')] start: portfolio snapshot"
# NOT haiku: it improvises tools outside --allowedTools (reaching for Edit or a
# Bash heredoc where the allowlist grants Write) and then reports the MCP
# connector as unauthenticated rather than retrying. Verified 2026-07-08 --
# haiku failed this slot 3/3 while sonnet ran it clean. The allowlist is the
# write-scope guarantee, so fix the model, never widen the list.
claude -p "/account-positions" \
    --model sonnet \
    --allowedTools "mcp__claude_ai_Robinhood_MCP__get_accounts,mcp__claude_ai_Robinhood_MCP__get_portfolio,mcp__claude_ai_Robinhood_MCP__get_equity_positions,Write,Bash(uv run python main.py portfolio *)" \
    --output-format json

FRESH=$(sqlite3 data/portfolio.db \
    "SELECT COUNT(*) FROM snapshots WHERE captured_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 hours');" \
    2>/dev/null || echo 0)
if [ "${FRESH:-0}" -lt 1 ]; then
    echo "[$(date '+%F %T')] STALE: no portfolio snapshot in the last 2h — check Robinhood MCP auth" >&2
    exit 1
fi
echo "[$(date '+%F %T')] portfolio snapshot fresh"
