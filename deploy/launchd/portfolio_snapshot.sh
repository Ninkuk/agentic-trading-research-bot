#!/bin/bash
# Post-close portfolio snapshot via headless claude (subscription auth) ->
# Robinhood MCP -> main.py portfolio. This is the schedule's one silent
# failure mode (a claude session can "succeed" while the MCP connector's
# auth is stale), so verify a fresh snapshot actually landed and fail loudly
# if not — the log line is the alert.
set -uo pipefail
source "$(dirname "$0")/env.sh"

job_start "portfolio snapshot"
# NOT haiku: it improvises tools outside --allowedTools (reaching for Edit or a
# Bash heredoc where the allowlist grants Write) and then reports the MCP
# connector as unauthenticated rather than retrying. Verified 2026-07-08 --
# haiku failed this slot 3/3 while sonnet ran it clean. The allowlist is the
# write-scope guarantee: never widen `Write`/`Bash`/`Edit` to work around a
# model improvising — fix the model. Read-only Robinhood getters are a
# different axis and DO get added as the skill grows to call them; a skill
# calling a getter the wrapper omits is a silent weekday outage, which is why
# test_launchd_wrappers.py asserts the two sets agree.
# get_equity_quotes is granted for that reason, but note the trigger: the
# UPSTREAM tool changed, not the skill. get_equity_positions stopped
# returning market_value and its guide now redirects to get_equity_quotes,
# so market value is derived (price x quantity) and the slot failed
# 2026-08-03/04 on the denial. No offline test can catch a vendor contract
# change -- the allowlist test only fires once the skill names the getter.
# --permission-mode default is load-bearing: a global defaultMode=auto in
# ~/.claude/settings.json AUTO-APPROVES tools outside --allowedTools in
# headless runs (proven 2026-07-22 by a research-nightly session committing
# an unreviewed file). Pinning the mode makes this allowlist a real envelope;
# Skill (loads /account-positions) and TodoWrite become explicit for that reason.
# 20min cap vs. a ~30-80s normal run: ~15x headroom, and safely under
# dashboard_lib/health.py's 60min hang tier so a wedge dies on its own run.
run_with_timeout "${PORTFOLIO_TIMEOUT_SECS:-1200}" \
claude -p "/account-positions" \
    --model sonnet \
    --allowedTools "Skill,TodoWrite,mcp__claude_ai_Robinhood_MCP__get_accounts,mcp__claude_ai_Robinhood_MCP__get_portfolio,mcp__claude_ai_Robinhood_MCP__get_equity_positions,mcp__claude_ai_Robinhood_MCP__get_equity_quotes,mcp__claude_ai_Robinhood_MCP__get_option_positions,Write,Bash(uv run python main.py portfolio *)" \
    --permission-mode default \
    --output-format json

FRESH=$(sqlite3 data/portfolio.db \
    "SELECT COUNT(*) FROM snapshots WHERE captured_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 hours');" \
    2>/dev/null || echo 0)
if [ "${FRESH:-0}" -lt 1 ]; then
    echo "[$(date '+%F %T')] STALE: no portfolio snapshot in the last 2h — read permission_denials in the JSON above before suspecting MCP auth" >&2
    exit 1
fi
echo "[$(date '+%F %T')] portfolio snapshot fresh"
