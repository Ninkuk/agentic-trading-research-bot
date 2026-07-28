#!/bin/bash
# Market-open order execution via headless claude -> Robinhood MCP.
# Scheduled at BOTH 6:32 and 7:32 Phoenix (9:32 ET across DST); preflight
# decides which slot is live — the other exits 0 before any session starts.
# There is deliberately NO flock: macOS ships no flock(1), and mutual
# exclusion lives in plan's BEGIN IMMEDIATE claim — a wake-coalesced
# duplicate session finds zero queued rows and no-ops. The ref_id passed to
# place_equity_order is the broker-side dedupe backstop.
set -uo pipefail
source "$(dirname "$0")/env.sh"

job_start "order execution"

uv run python main.py orders preflight --db data/orders.db --calendar-db data/market_calendar.db
rc=$?
if [ "$rc" -eq 3 ]; then
    echo "[$(date '+%F %T')] stand-down (empty queue / closed / outside window)"
    exit 0
fi
if [ "$rc" -ne 0 ]; then
    echo "[$(date '+%F %T')] PREFLIGHT ERROR rc=$rc (calendar-blind refuses to fly)" >&2
    exit 1
fi

# --permission-mode default is load-bearing (see portfolio_snapshot.sh):
# it makes --allowedTools a real envelope. Subcommands are ENUMERATED —
# `orders *` would grant `orders queue`, letting the session author its own
# orders and reducing the human-only invariant to prose. Buying power comes
# from the portfolio getter (the accounts getter's buying power is
# unreliable per its own tool contract). Deliberately absent: the cancel
# tool, all option tools, sells, Edit, general Bash.
claude -p "/execute-queue" \
    --model sonnet \
    --allowedTools "Skill,TodoWrite,Write,mcp__claude_ai_Robinhood_MCP__get_equity_quotes,mcp__claude_ai_Robinhood_MCP__get_portfolio,mcp__claude_ai_Robinhood_MCP__review_equity_order,mcp__claude_ai_Robinhood_MCP__place_equity_order,Bash(uv run python main.py orders preflight *),Bash(uv run python main.py orders plan *),Bash(uv run python main.py orders record *)" \
    --permission-mode default \
    --output-format json

# strftime, NOT datetime(): captured_at is isoformat with 'T'; datetime()
# renders a space and 'T' > ' ' lexicographically (journal_sync.sh trap).
# preflight's own header must NOT satisfy the check that guards the session
# it precedes, hence phase IN ('plan','record').
FRESH=$(sqlite3 data/orders.db \
    "SELECT COUNT(*) FROM runs WHERE phase IN ('plan','record') AND captured_at >= strftime('%Y-%m-%dT%H:%M:%S','now','-15 minutes');" \
    2>/dev/null || echo 0)
if [ "${FRESH:-0}" -lt 1 ]; then
    echo "[$(date '+%F %T')] STALE: no plan/record run in 15m — read permission_denials in the JSON above before suspecting MCP auth" >&2
    exit 1
fi
# 'queued' too, not just 'planned': a slow session can drift past the
# window's upper bound, at which point plan writes a FRESH header but claims
# nothing — without this clause that morning reads as success and the rows
# silently expire tomorrow.
STUCK=$(sqlite3 data/orders.db \
    "SELECT COUNT(*) FROM queue WHERE status IN ('queued','planned');" 2>/dev/null || echo 0)
if [ "${STUCK:-0}" -gt 0 ]; then
    echo "[$(date '+%F %T')] STUCK: $STUCK row(s) still queued/planned after the session — see v_unreconciled; clear with 'orders resolve'" >&2
    exit 1
fi
echo "[$(date '+%F %T')] order execution complete"
