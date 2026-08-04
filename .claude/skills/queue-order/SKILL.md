---
name: queue-order
description: Queue an equity buy for the next market open (human decision -> data/orders.db via the orders dispatcher). Use when the user says to queue/schedule a purchase, buy X at open, or wants to review or clear the pending order queue. The morning launchd slot executes whatever this queues.
---

# queue-order

Record the human's decision to buy at the next market open. Queue semantics:
**attempt at the NEXT open** — there is no "queue for Thursday" while
Wednesday's open is still ahead. A veto (gap, stale quote, caps) or a
stand-down morning (holiday, window miss) **retries at each later open until
`expires_on` (Phoenix date, inclusive); a veto on the last eligible day is
terminal**. The 6:32/7:32 launchd slot plans against a fresh quote, applies
the gap/cap/cash rails, and places a GFD limit order (share rows) or a
dollar-based GFD market order (notional rows).

## Queueing

1. Gather: symbol, size — whole-share `--qty` OR dollar `--notional`, never
   both — reference price, max gap %, optional expiry (default: next trading
   day), and the rationale. If the user has no reference price, offer to
   fetch `get_equity_quotes` and pin it to the live quote — with their
   confirmation, since ref_price × (1 + gap) is the hard price ceiling
   (share rows) / the pre-placement gap veto band (notional rows).

   Order-kind semantics — say this back to the user when queueing notional:
   - `--qty N` plans a GFD LIMIT order capped at ref × (1 + gap). The fill
     price can never exceed the ceiling.
   - `--notional D` plans a dollar-based MARKET order (the broker only
     accepts fractional as market type). The spend is exactly $D; the gap
     veto still refuses placement when the fresh ask is outside
     ref × (1 ± gap), but between that check and the fill the price floats —
     a gap-through-the-band risk of seconds, acceptable only because the
     notional itself caps the damage. Minimum $1, whole cents.
2. Run (env override needed because tool-driven shells have no TTY; this is
   the sanctioned human-in-the-loop path — the headless slot's allowlist
   never includes this subcommand):

   ```
   ORDERS_ALLOW_NONINTERACTIVE=1 uv run python main.py orders queue \
     --db data/orders.db --calendar-db data/market_calendar.db \
     --symbol TSLA --qty 20 --ref-price 310.00 --max-gap-pct 3 \
     --note "<the user's rationale — this reaches the decision journal>"
   ```

3. Read back `v_open_queue` (`sqlite3 file:data/orders.db?mode=ro "SELECT *
   FROM v_open_queue"` — always the read-only URI; writes go through the
   dispatcher only) and confirm to the user exactly what the next open will
   consider, including the implied price ceiling (share rows) or exact
   spend and veto band (notional rows) per order.

Constraints the dispatcher enforces (don't fight them): exactly one of
whole-share qty or ≥$1 whole-cent notional, no sub-$1 names, gap within
[0, 20]%, one open row per symbol, dollar caps and cash floor from `.env`
under committed hard ceilings.

## Reviewing / clearing

- Pending queue: `v_open_queue`. Morning outcomes: `v_run_results`.
  Anything needing eyes: `v_unreconciled`.
- A stuck `planned` row (session died between place and record) is cleared
  ONLY via `uv run python main.py orders resolve --db data/orders.db --id N
  --as placed|failed [--order-id ...]` — never ad-hoc SQL against orders.db.
- The human withdrawing a still-`queued` row (changed mind, repricing) uses
  `ORDERS_ALLOW_NONINTERACTIVE=1 uv run python main.py orders cancel --db
  data/orders.db --id N [--reason "..."]`. Human-only like `queue`; refuses
  once the morning claim has flipped the row to `planned` (then `resolve` is
  the only exit). Never granted to the headless slot.

## First-run verification (mandatory before go-live)

Before the launchd job is EVER armed (`ORDERS_GO_LIVE=1` at install time),
run /execute-queue manually once in an interactive session with a single
1-share order queued. Nothing in Python loads `.env` (only
deploy/launchd/env.sh does, for launchd jobs), so load it explicitly first:
`set -a; . ./.env; set +a; uv run python main.py orders plan ...`. Verify
the live `get_equity_quotes` / `get_portfolio` response fields (ask price,
quote timestamp, settled cash) against what
`sources/screeners/orders/fetch.py` expects — external feeds routinely
disagree with their docs (CLAUDE.md: live-verify source schemas). Adjust
`fetch.py` before go-live if the live shapes differ. Also verify in that
run: (a) `place_equity_order` echoes/accepts the `ref_id` as the client
idempotency key, and (b) the journal slot's read-only sqlite grant actually
matches the command form its skill instructs (run the attribution SELECT
once under the wrapper's allowlist semantics) — a pattern/command mismatch
there is a silent loss of every fill rationale.
