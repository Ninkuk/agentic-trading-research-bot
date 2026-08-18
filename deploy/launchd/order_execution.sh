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
# The wedge cap + one retry: an unbounded claude wedge holds this label past
# the [open+2m, open+45m] window and blocks the label's other slot. The
# retry is placement-safe — plan claims only 'queued' rows, so a session
# killed after planning stands down and the STUCK check below alarms. Both
# attempts (2x1200s) finish inside the window with room to plan, and stay
# under health.py's 60min hang budget.
run_with_timeout_retry "${ORDERS_TIMEOUT_SECS:-1200}" \
    claude -p "/execute-queue" \
    --model sonnet \
    --allowedTools "Skill,TodoWrite,Write,mcp__claude_ai_Robinhood_MCP__get_equity_quotes,mcp__claude_ai_Robinhood_MCP__get_portfolio,mcp__claude_ai_Robinhood_MCP__review_equity_order,mcp__claude_ai_Robinhood_MCP__place_equity_order,Bash(uv run python main.py orders preflight *),Bash(uv run python main.py orders plan *),Bash(uv run python main.py orders record *)" \
    --permission-mode default \
    --output-format json

# strftime, NOT datetime(): captured_at is isoformat with 'T'; datetime()
# renders a space and 'T' > ' ' lexicographically (journal_sync.sh trap).
# preflight's own header must NOT satisfy the check that guards the session
# it precedes, hence phase IN ('plan','record').
# Inverted numeric tests (! [ ... ] 2>/dev/null): a non-numeric value makes
# `[` itself fail, and the alarm must fire on that, not silently skip.
FRESH=$(sqlite3 data/orders.db \
    "SELECT COUNT(*) FROM runs WHERE phase IN ('plan','record') AND captured_at >= strftime('%Y-%m-%dT%H:%M:%S','now','-15 minutes');" \
    2>/dev/null || echo 0)
if ! [ "${FRESH:-0}" -ge 1 ] 2>/dev/null; then
    echo "[$(date '+%F %T')] STALE: no plan/record run in 15m — read permission_denials in the JSON above before suspecting MCP auth" >&2
    exit 1
fi
# Unevaluated 'queued' rows too, not just 'planned': a slow session can
# drift past the window's upper bound, at which point plan writes a FRESH
# header but claims nothing — without this clause that morning reads as
# success and the rows silently expire tomorrow. Deliberate retry vetoes
# stay queued WITH a resolution_reason and are not stuck.
STUCK=$(sqlite3 data/orders.db \
    "SELECT COUNT(*) FROM queue WHERE status='planned' OR (status='queued' AND resolution_reason IS NULL);" \
    2>/dev/null || echo 0)
if ! [ "${STUCK:-0}" -eq 0 ] 2>/dev/null; then
    echo "[$(date '+%F %T')] STUCK: $STUCK row(s) still planned/unevaluated after the session — see v_unreconciled; clear with 'orders resolve'" >&2
    exit 1
fi
# Vetoes and retries are designed outcomes, not failures — but the log line
# is the alert, so say what happened to every row the run touched.
sqlite3 data/orders.db \
    "SELECT '[$(date '+%F %T')] veto ' || symbol || ' (' || status || '): ' || resolution_reason FROM queue WHERE resolution_reason IS NOT NULL AND status NOT IN ('planned','placed') AND (resolved_at >= strftime('%Y-%m-%dT%H:%M:%S','now','-15 minutes') OR (status='queued' AND resolution_reason LIKE 'retry:%'));" \
    2>/dev/null
echo "[$(date '+%F %T')] order execution complete"
