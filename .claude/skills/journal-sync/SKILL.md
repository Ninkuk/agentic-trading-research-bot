---
name: journal-sync
description: Sync Robinhood equity fills into the decision journal (data/scorer.db) via the journal dispatcher, and record explicit passes on flagged tickers. Use when the user asks to sync/journal trades, log a pass, or backfill trade history. Also use to reconcile fills against broker realized P&L.
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
   - **Label every fill**: pass the order's `placed_agent` through on each
     fill (`user`/`agentic`/`drip`/`recurring`). Automatic fills
     (drip/recurring) are journaled for the record but the dispatcher
     never matches them to an opinion and never attaches them as exits —
     they land in `v_freelance` labeled as such. (Policy revised
     2026-07-07: label, don't exclude.)
3. Build ONE JSON document in the scratchpad:

   ```json
   {"as_of": "<UTC now isoformat>",
    "fills": [{"symbol": "XLE", "side": "buy", "price": 94.30,
               "quantity": 2, "filled_at": "<order executed-at UTC ISO>",
               "order_ref": "<order id>", "placed_agent": "agentic"}],
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
   - `note` (on a fill, or on a `passes[]` entry) may carry a short
     gradeability tag recording that an options check fired at decision
     time, e.g. `iv_elevated_at_entry`. Without it, that check can never be
     graded against `v_decision_outcomes` — grading past opinions is the
     entire reason `scorer` exists. No schema change needed: `decisions.note`
     already exists and this is its intended use.
4. Ingest:

   ```bash
   uv run python main.py journal --db data/scorer.db --input <scratchpad>/journal.json
   ```

5. Reconcile against broker realized P&L — **read-only: report the
   comparison, never auto-write.** The dispatcher write in step 4 is the
   only write path this skill has; this step does not touch it.

   - Call `get_realized_pnl` (Robinhood MCP, read-only) for the same window
     as the sync, scoped to the pinned "Agentic" account (number ending
     1936) — the same account pinned in step 2.
   - Compare the broker's figures against the fills just ingested.
   - **Expected divergence** — note it, don't flag it as a sync bug:
     - T+1 trade-vs-settlement drift at window edges.
     - drip/recurring fills, which land in `v_freelance` by design (step 2)
       and are never matched to an opinion.
     - `scorer.realized_return` is a single-lot ratio
       (`exit_fill_price / fill_price - 1`, computed from journaled fills
       only) while the broker computes realized P&L per actual closed tax
       lot, possibly under a different lot-selection method — these two
       numbers are structurally not apples-to-apples even when the dates
       agree.
   - **Unexplained divergence** — anything outside the above — investigate
     and report; do not paper over it.
   - Never paste raw MCP payloads into the conversation; on any error report
     the exception type name only, same as elsewhere in this skill.
6. Report the printed counts (matched / freelance / exits / passes /
   duplicates / skipped), plus the reconciliation result from step 5.

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
