---
name: execute-queue
description: Headless market-open executor for the human-queued order list in data/orders.db. Invoked ONLY by deploy/launchd/order_execution.sh — never interactively except for the one-time first-run verification. Fetches quotes, pipes them into the deterministic planner, places exactly the planned limit orders, records results.
---

# execute-queue

Execute the human's queued buys at market open. You are a TRANSPORT, not a
decision-maker: Python decides what to buy, how much, and at what limit;
your job is to move data to it and copy its plan to the broker
param-for-param. You never adjust a price, substitute an order type,
reorder, split, skip, or add an order, and you never mint a `ref_id`.

## Steps

1. **Preflight.** Run:
   `uv run python main.py orders preflight --db data/orders.db --calendar-db data/market_calendar.db`
   Exit code 0 prints the symbols to fetch (one per line). Any other exit
   code: stop immediately and end the session — do not improvise.

2. **Fetch inputs.** Call `get_equity_quotes` for exactly those symbols, and
   `get_portfolio` for account cash. Buying power comes from `get_portfolio`
   only — `get_accounts` is deliberately NOT granted in this slot (its
   buying-power figure is unreliable per its own tool contract). `Write` one
   JSON document to the scratchpad directory:

   ```json
   {
     "as_of": "<UTC ISO timestamp from the quotes response>",
     "quotes": [{"symbol": "TSLA", "ask": 312.4, "quote_ts": "<UTC ISO>"}],
     "portfolio": {"settled_cash": 4200.5}
   }
   ```

   Copy numbers exactly as the MCP returned them. Never estimate, never fill
   a gap: a missing or unavailable ask stays `null` (the planner vetoes that
   row — that is correct behavior, not a problem to fix).

3. **Plan.** Run:
   `uv run python main.py orders plan --db data/orders.db --calendar-db data/market_calendar.db --input <that file>`
   The stdout JSON is the complete, final execution plan:
   `{"account_number": ..., "orders": [{"queue_id", "symbol", "qty", "limit_price", "ref_id"}]}`.
   If `orders` is empty, skip to step 5 with an empty results list.

4. **Place.** For each plan order, in the order given: call
   `review_equity_order`, then `place_equity_order`, with EXACTLY the plan's
   `symbol`, `qty`, `limit_price`, `ref_id`, and `account_number` — side
   buy, limit order, time-in-force GFD (day), regular market hours. Copy the
   qty and limit strings verbatim; do not reformat numbers.
   - Review alerts (halt, PDT, buying power) are informational for a
     limit-bounded order: include them in the result's `raw`, and proceed.
   - On an ambiguous failure (timeout, unclear response): retry ONCE with
     the SAME `ref_id` — the broker deduplicates on it, so this cannot
     double-place. Never retry with a new `ref_id`.
   - On a hard error: record `"state": "error"` with the error detail in
     `raw`, and continue to the next order.

5. **Record.** `Write` the results JSON:

   ```json
   {"results": [{"queue_id": 1, "ref_id": "...", "account_number": "...",
                 "order_id": "<broker id or null>", "state": "placed",
                 "raw": {}}]}
   ```

   Then run:
   `uv run python main.py orders record --db data/orders.db --input <that file>`

Never paste raw MCP payloads into the conversation output (they can embed
account identifiers) — they go only into the `raw` fields of the results
file. If any step fails in a way these instructions don't cover, stop and
end the session; the wrapper's freshness check will raise the alarm, which
is the designed loud-failure path.
