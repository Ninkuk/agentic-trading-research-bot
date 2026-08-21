---
name: journal-sync
description: Sync Robinhood equity and single-leg option fills into the decision journal (data/scorer.db) via the journal dispatcher, and record explicit passes on flagged tickers. Use when the user asks to sync/journal trades, log a pass, or backfill trade history. Also use to reconcile fills against broker realized P&L.
---

# journal-sync

Record what the human DID about composite opinions. Guiding invariant
(same as account-positions): Claude may fetch live state via MCP, but it
enters the system only through the `journal` dispatcher — never write SQL
against scorer.db directly.

## Procedure

1. Sync bound: a **fixed 72-hour lookback** — UTC now minus 72h, as full
   ISO. Never derive the bound from `--last-run`: EVERY ingest advances it,
   so a verdict-only or zero-fill ingest moves it past fills that were never
   fetched and the next sync silently skips them (this stranded the ZTO/ORI/
   PRI fills of 2026-08-19/20 until an interactive re-sync). The overlap is
   safe — `order_ref` idempotency counts re-seen fills as duplicates — and
   72h self-heals a weekend of wedged slots. If the journal has been down
   longer than 72h (STALE lines in `logs/journal.log`, or a gap in
   `journal_runs.ran_at`), widen the lookback to cover the whole gap.
2. Fetch via the Robinhood MCP (read-only tools):
   - `get_accounts` → pin the **"Agentic" account (number ending 1936)**;
     if no account matches, stop and report — never fall back.
   - `get_equity_orders` scoped to it: **filled** orders updated since the
     bound, PLUS `partially_filled` orders and `cancelled` orders with
     nonzero executions — a partially-filled GFD limit ends its life
     `cancelled` *with executions* (the most likely outcome of a capped
     morning limit on a gapping name), and skipping it silently drifts
     positions away from the journal. For those, quantity = the **sum of
     executions**, never the order's requested quantity. Never paste raw MCP
     payloads into the conversation (they can carry account identifiers).
   - `get_option_orders`, same scope and bound: filled option orders. See
     the option-fill bullet in step 3 for the field mapping.
   - **Label every fill**: pass the order's `placed_agent` through on each
     fill (`user`/`agentic`/`drip`/`recurring`). Automatic fills
     (drip/recurring) are journaled for the record but the dispatcher
     never matches them to an opinion and never attaches them as exits —
     they land in `v_freelance` labeled as such. (Policy revised
     2026-07-07: label, don't exclude.)
3. Build ONE JSON document in the scratchpad. To revise it, re-`Write` the
   whole document: the headless slot allowlists `Write` but not `Edit`, so an
   `Edit` call dies on a permission prompt no one is there to approve (this
   exact failure produced the 2026-07-23 stale-journal alert).

   ```json
   {"as_of": "<UTC now isoformat>",
    "fills": [{"symbol": "XLE", "side": "buy", "price": 94.30,
               "quantity": 2, "filled_at": "<order executed-at UTC ISO>",
               "order_ref": "<order id>", "placed_agent": "agentic"}],
    "passes": [{"symbol": "GLD", "note": "too crowded"}]}
   ```

   - The document may also carry a `verdicts` array
     (`{"symbol", "verdict": "buy"|"pass", "verdict_date": "YYYY-MM-DD"
     (bare Phoenix date), "doc", "note"}`) — research-ticker's own buy/pass
     calls, normally appended by that skill's final step, not dictated by
     the user. Idempotent on (symbol, verdict_date). Passes remain
     user-dictated; verdicts are the skill's record. Graded in
     `v_research_filter` (reading it is fine — reading is not writing).
   - `order_ref` = the order's id — the idempotency key; re-syncing an
     overlapping window is safe (duplicates are counted and skipped).
   - **Queue attribution**: if the fill's order id appears in
     `data/orders.db` `placements` (a morning queue execution), copy that
     queue row's `note` into the fill's `note` — the rationale is what
     scorer grades and must not die in orders.db. Read via the read-only
     URI ONLY, written EXACTLY as below — unquoted URI, so the command
     matches the wrapper's allowlist pattern
     `Bash(sqlite3 file:data/orders.db?mode=ro *)` (a quoted `"file:..."`
     would NOT match and dies headless on a permission prompt; a writable
     sqlite3 against orders.db is deliberately not grantable):
     `sqlite3 file:data/orders.db?mode=ro "SELECT q.note FROM placements p
     JOIN queue q ON q.id=p.queue_id WHERE p.order_id='<id>'"`.
     These are human decisions with machine hands: they keep `placed_agent`
     as the broker reports it and join the normal human buckets, no new
     actor.
   - `price` = the order's **average** fill price (a multi-execution order
     must not use the last execution's price); `filled_at` = the executed-at
     timestamp as full UTC ISO. Verify both field mappings on your first
     interactive run before trusting the scheduled slot.
   - **Option fills**: same `fills[]` array, with `symbol` = the
     **underlying**, `side` = the broker side, `price` = the **premium**,
     `quantity` = the number of **contracts** (required on option fills; the
     ledger books dollars as premium × contracts × 100), plus `contract_ref`
     (OCC symbol), `position_effect` (`"open"`/`"close"`), `strategy_ref`
     (the order id), and — required on opens — `right` (`"call"`/`"put"`)
     and `expiration` (`"YYYY-MM-DD"`). The dispatcher derives directional
     intent from (side, right) itself; never pre-map it. On a **multi-leg**
     order set `"multi_leg": true` on every leg — the parser refuses them by
     design (a spread is one bet; per-leg grading would double-count it). An
     **exercise or assignment** produces stock instead of a closing fill:
     dictate it as a close-shaped fill with `terminal: "exercise"` or
     `"assign"` (`price: 0` — the value is ignored and booked at premium 0) — it closes the
     contracts in the premium ledger; journal the resulting stock fill
     separately as its own equity entry (the two are not linked). A close spanning multiple open lots of the same contract is refused as an over-close: re-dictate it as per-lot closes, each with a **distinct** `order_ref` (e.g. `<broker-ref>:1`, `<broker-ref>:2`) — without distinct refs the second identical dictation dedupes as a duplicate and the remainder later expires as worthless. Contracts
     that expire un-closed are auto-booked by the sweep.
     Option decisions grade **selection** in `v_flag_response`
     (`acted_option`) and **P&L on premium terms** in `v_option_pnl` /
     `v_option_actor` (scorer.db); their equity-shaped P&L columns in
     `v_decision_outcomes` stay NULL — never read those for option
     economics.
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
     1936) — the same account pinned in step 2. This tool returns
     **aggregate, bucketed TOTALS only, never individual trades** (its own
     schema says so), so it can answer "do the totals agree" and nothing
     finer.
   - **Mind the three clocks.** The lookback bound from step 1 is a UTC
     ISO timestamp; `get_realized_pnl`'s `start_date`/`end_date` are
     `YYYY-MM-DD` interpreted at midnight **US/Eastern by default**; and this
     repo's calendar-date convention is **Phoenix** (a CLAUDE.md invariant —
     `composite` stamps `obs_date` on the Phoenix date and `journal` matches
     fills on it). Convert the UTC bound to a Phoenix calendar date with
     `phx_date` semantics, and pass `timezone="America/Phoenix"` so the
     broker's bucket boundaries agree with `obs_date`. Skip either step and
     window edges manufacture phantom divergences — the "cry wolf and be
     ignored" failure the tolerance model below exists to prevent.
   - For the **per-trade** comparison, use `get_pnl_trade_history` instead —
     it lists closed trades individually, but offers **preset spans only**
     (`week` / `month` / `3month` / `ytd` / `all`), so the sync window is not
     directly expressible. Choose the nearest **enclosing** preset span.
     **The tool is paginated** (`cursor` / `next_cursor`): follow
     `next_cursor` until that enclosing span is **fully retrieved**, then
     filter client-side down to the sync window — reading only page 1 and
     filtering against a truncated list fabricates unexplained divergences
     (journaled fills that look like they have no broker counterpart, purely
     because the counterpart was on a page you never fetched).
   - Compare the broker's figures against the fills just ingested: totals
     from `get_realized_pnl`, trade-by-trade from the filtered
     `get_pnl_trade_history`.
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
6. Order-queue reconciliation (only if `data/orders.db` exists): the
   morning execution slot records what it *says* it placed; cross-check
   that against the broker's own order list fetched in step 2. `Write` the
   fetched orders as `{"orders": [{"order_id", "ref_id", "symbol",
   "state"}]}` (include `ref_id` when the broker echoes a client order id;
   else null) and run:

   ```bash
   uv run python main.py orders reconcile --db data/orders.db --input <file>
   ```

   Report the JSON it prints: `orphan_placements` (we recorded a placement
   the broker has no order for — fabricated or lost, ALWAYS serious) and
   `orphan_orders`, split by the `likely_manual` flag: one carrying our
   `ref_id` is serious (session placed off-plan); one without is likely the
   human's own app trade — report as "likely manual — confirm", not as an
   alarm, so real alarms stay audible.
7. Report the printed counts (matched / freelance / exits / passes /
   duplicates / skipped / expired), plus the reconciliation results from
   steps 5 and 6.

## Manual path

The user dictates a trade ("bought 2 XLE at 94.30 Tuesday morning"): build
the same document without `order_ref` (rows record as `source: manual`).
`filled_at` must be a full timestamp — if the user only knows the day, use
`<date>T16:00:00+00:00` (9am Phoenix, regular session); a bare date is
rejected by the parser. Manual rows get a synthetic idempotency key over
their identifying fields (including `contract_ref`), so re-dictating the
same fill is a counted duplicate, not a double-book.

## Rules

- **Secret hygiene**: on any MCP or CLI error report the exception type
  name only — never message bodies, URLs, or payload fragments.
- **Write scope**: this command writes `data/scorer.db` via the journal
  dispatcher, plus confirmation timestamps in `data/orders.db` via
  `orders reconcile` (step 6 — an audit write, never an order write).
  Everything else it touches is read-only.
- Reading views (`v_decision_outcomes`, `v_flag_response`, `v_human_filter`,
  `v_freelance`, `v_option_pnl`, `v_option_actor`) to answer questions is
  fine — reading is not writing.
