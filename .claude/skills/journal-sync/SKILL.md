---
name: journal-sync
description: Sync Robinhood equity fills into the decision journal (data/scorer.db) via the journal dispatcher, and record explicit passes on flagged tickers. Use when the user asks to sync/journal trades, log a pass, or backfill trade history.
---

# journal-sync

Record what the human DID about composite opinions. Guiding invariant
(same as account-positions): Claude may fetch live state via MCP, but it
enters the system only through the `journal` dispatcher — never write SQL
against scorer.db directly.

## Procedure

1. Since-bound:

   ```bash
   uv run python main.py journal --db data/scorer.db --last-run
   ```

   Prints an ISO timestamp or `never` (→ use 7 days ago).
2. Fetch via the Robinhood MCP (read-only tools):
   - `get_accounts` → pin the **"Agentic" account (number ending 1936)**;
     if no account matches, stop and report — never fall back.
   - `get_equity_orders` scoped to it: **filled** orders updated since the
     bound. Never paste raw MCP payloads into the conversation (they can
     carry account identifiers).
   - **Exclude automatic fills**: drop orders whose `placed_agent` is
     `drip` or `recurring` — dividend reinvestments and auto-invests are
     nobody's decision, and the journal measures decision quality (policy
     set on the first interactive run, 2026-07-07). Keep `user` and
     `agentic` fills.
3. Build ONE JSON document in the scratchpad:

   ```json
   {"as_of": "<UTC now isoformat>",
    "fills": [{"symbol": "XLE", "side": "buy", "price": 94.30,
               "quantity": 2, "filled_at": "<order executed-at UTC ISO>",
               "order_ref": "<order id>"}],
    "passes": [{"symbol": "GLD", "note": "too crowded"}]}
   ```

   - `order_ref` = the order's id — the idempotency key; re-syncing an
     overlapping window is safe (duplicates are counted and skipped).
   - `price` = the order's **average** fill price (a multi-execution order
     must not use the last execution's price); `filled_at` = the executed-at
     timestamp as full UTC ISO. Verify both field mappings on your first
     interactive run before trusting the scheduled slot.
   - `passes` only when the user dictates them; a pass must answer a
     currently-flagged ticker or it is skipped with a message.
   - Zero fills is normal: ingest the empty doc anyway — the run header is
     the "ran and found nothing" signal the schedule's freshness check reads.
4. Ingest:

   ```bash
   uv run python main.py journal --db data/scorer.db --input <scratchpad>/journal.json
   ```

5. Report the printed counts (matched / freelance / exits / passes /
   duplicates / skipped).

## Manual path

The user dictates a trade ("bought 2 XLE at 94.30 Tuesday morning"): build
the same document without `order_ref` (rows record as `source: manual`).
`filled_at` must be a full timestamp — if the user only knows the day, use
`<date>T16:00:00+00:00` (9am Phoenix, regular session); a bare date is
rejected by the parser. Manual rows have no idempotency key — check
`v_decision_outcomes` for an existing row before re-dictating.

## Rules

- **Secret hygiene**: on any MCP or CLI error report the exception type
  name only — never message bodies, URLs, or payload fragments.
- **Write scope**: this command writes ONLY `data/scorer.db`, only via the
  dispatcher. Everything else it touches is read-only.
- Reading views (`v_decision_outcomes`, `v_flag_response`, `v_human_filter`,
  `v_freelance`) to answer questions is fine — reading is not writing.
