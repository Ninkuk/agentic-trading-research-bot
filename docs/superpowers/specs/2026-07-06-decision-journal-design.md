# Decision journal — design

**Date:** 2026-07-06 · **Roadmap item:** 5 (evaluation hardening) · **Size:** M

## Problem

The scorer grades composite opinions against forward returns; nothing records
what the human did about them. Without "composite said X on date D, human
acted/passed, filled at P" there is no way to measure the paper-vs-realized
gap (entry slippage, hold timing) or whether the human filter adds value
(do the flags acted on outperform the flags passed?).

## Decisions made during brainstorming

1. **Pass capture: inferred, with explicit override.** A flagged opinion with
   no journal row counts as *passed* — computed in the view, never stored.
   Only actions (and the occasional explicit pass with a note) are journaled.
   Accepted blind spot: "never saw it" is indistinguishable from "saw it and
   declined" unless explicitly annotated; the portfolio consequence is
   identical either way, so the performance math is unaffected.
2. **Entries + optional exits.** An acted row records the entry fill; an exit
   fill can attach to the same row later. Entry slippage and paper-horizon
   grades are always available; realized round-trip appears when the exit
   exists. No chore if an exit is never logged.
3. **Entry flow: MCP backfill, deterministic matching, scheduled headless.**
   A skill fetches filled orders via the Robinhood MCP (same headless
   `claude -p` path as the portfolio slice, scheduled daily right after it)
   and pipes one JSON doc to a dispatcher. Because a headless run cannot stop
   to confirm, all trade→opinion matching is deterministic Python — testable,
   never Claude judgment. Manual dictation uses the same JSON shape.

## Architecture

New module **`sources/combiners/scorer/journal.py`** inside the scorer
package, registered in `registry.py` as its own dispatcher:

```bash
uv run python main.py journal --db data/scorer.db --input <file|->
uv run python main.py journal --db data/scorer.db --last-run   # prints MAX(ran_at) for the skill's since-bound
```

Journal tables live **in `data/scorer.db`**, schema owned by `scorer/db.py`.
Rationale: SQLite refuses persistent views that reference an ATTACHed
database, and the deliverable is a *live view* joining decisions to matured
outcomes — so decisions must share a file with `ticker_outcomes`. scorer.db
is already the permanent-evidence store ("outcomes ARE the experiment");
decisions are the other half of that experiment and are likewise never
pruned. Two dispatchers now write scorer.db (nightly `scorer`, afternoon
`journal`); they touch disjoint tables and WAL handles the concurrency.

Matching at ingest reads **composite.db ATTACHed read-only** (`--composite-db`,
default alongside the scorer db) — the same pattern as the scorer's harvest.
This is deliberate: scorer registration defers one night (next-day-close
entries), so matching against `ticker_outcomes` would misclassify a
morning-after fill as freelance. The opinion exists in composite.db the
night it forms. composite.db prunes on a long cascade while the matching
window is days, so pruning never affects matching; once matched, the
decision's `(composite_snapshot_id, symbol)` key joins to the scorer's own
permanent outcome rows and never needs composite.db again.

## Schema

```sql
CREATE TABLE IF NOT EXISTS decisions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                TEXT NOT NULL,
    action                TEXT NOT NULL CHECK (action IN ('acted', 'passed')),
    side                  TEXT CHECK (side IN ('buy', 'sell')),  -- NULL for passes
    composite_snapshot_id INTEGER,          -- matched opinion; NULL = freelance
    composite_date        TEXT,
    opinion_score_sum     INTEGER,          -- matched opinion's score at ingest
    opinion_total         INTEGER,          -- (composite.db prunes; capture now)
    fill_date             TEXT,             -- NULL for passes
    fill_price            REAL,
    quantity              REAL,
    exit_fill_date        TEXT,
    exit_fill_price       REAL,
    order_ref             TEXT UNIQUE,      -- broker order id: idempotency key
    exit_order_ref        TEXT UNIQUE,      -- idempotency for the exit leg
    note                  TEXT,
    source                TEXT NOT NULL DEFAULT 'mcp'
                          CHECK (source IN ('mcp', 'manual')),
    recorded_at           TEXT NOT NULL
);
-- one explicit pass per matched flag (NULL snapshot ids are not deduped by
-- SQLite, but ingest never writes a pass without a match)
CREATE UNIQUE INDEX IF NOT EXISTS idx_decisions_pass
    ON decisions (composite_snapshot_id, symbol) WHERE action = 'passed';

-- Backstop for the views' window re-keying: at most one outcome-owning
-- snapshot per entry window. register_snapshot's dedupe already guarantees
-- this sequentially; the index makes the assumption durable.
CREATE UNIQUE INDEX IF NOT EXISTS idx_owner_window
    ON registered_snapshots (entry_date) WHERE ticker_rows > 0;

CREATE TABLE IF NOT EXISTS journal_runs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at             TEXT NOT NULL,
    fills_seen         INTEGER NOT NULL DEFAULT 0,
    matched            INTEGER NOT NULL DEFAULT 0,
    freelance          INTEGER NOT NULL DEFAULT 0,
    exits_attached     INTEGER NOT NULL DEFAULT 0,
    passes_recorded    INTEGER NOT NULL DEFAULT 0,
    duplicates_skipped INTEGER NOT NULL DEFAULT 0,
    skipped            INTEGER NOT NULL DEFAULT 0
);
```

Notes:

- `order_ref` is the Robinhood order UUID — a random identifier, not an
  account identifier, stored only in the local db for idempotency. UNIQUE
  with NULLs allowed (manual entries have none; manual dedupe is the
  user's responsibility, documented in the skill).
- Decisions and journal_runs are **never pruned** — same policy and rationale
  as the outcome tables. The scorer's `prune` is unchanged.
- Schema goes through `ensure_schema` in `scorer/db.py` like everything else
  (`CREATE ... IF NOT EXISTS`, views DROP+CREATEd each run).

## Input document

One JSON doc (scratchpad file or stdin), built by the skill or dictated:

```json
{"fills": [{"symbol": "XLE", "side": "buy", "price": 94.30, "quantity": 2,
            "filled_at": "2026-07-07T14:31:00+00:00",
            "order_ref": "a1b2c3..."}],
 "passes": [{"symbol": "GLD", "note": "too crowded"}]}
```

`fill_date` is the **Phoenix-local date** of `filled_at` (shift −7h before
truncating, exactly like `composite_date` in `fetch.read_snapshots`). Both
sides of the match must be on one clock: with a raw UTC date, an
extended-hours fill at 5:30pm Phoenix lands on the next UTC date and would
match that evening's 9:05pm opinion — formed hours *after* the fill
executed (look-ahead in the permanent record). Validation is strict:
`filled_at` must parse with `datetime.fromisoformat`, price/quantity must
be real numbers (bools rejected); bad rows are skipped and counted,
portfolio-parser style.

## Matching algorithm (deterministic, in `journal.py`)

Constants live at module top like the scorer's guard bounds:
`MATCH_WINDOW_DAYS = 5` (calendar days an opinion stays matchable).

Per **buy** fill:

1. Find the most recent `ticker_scores` row (via ATTACHed composite.db) for
   that symbol with `composite_date < fill_date` and
   `fill_date <= composite_date + MATCH_WINDOW_DAYS`, where `composite_date`
   is `date(snapshots.captured_at)`. Most recent snapshot wins.
2. Match → decision row with that `(composite_snapshot_id, composite_date)`
   **plus the matched opinion's own `score_sum`/`total` copied onto the
   row** (`opinion_score_sum`, `opinion_total`). This matters for weekend
   reruns: the graded outcome rows belong to the window *owner* snapshot,
   whose score may differ from the sibling actually matched — alignment
   must be judged against the opinion the human actually saw, and
   composite.db prunes, so the score must be captured at ingest.
   No match → freelance row (`composite_snapshot_id` NULL). Matching is
   direction-agnostic (a buy can match a bearish opinion); the views then
   classify by alignment (see `v_flag_response`).

Per **sell** fill:

1. If an open acted-buy decision for the symbol exists
   (`exit_fill_date IS NULL AND fill_date <= sell fill_date`), attach the
   sell as its exit — oldest open row first (FIFO). Partial sells attach
   whole: the journal measures price/timing skill, not P&L attribution.
2. Otherwise it becomes its own decision row, matched to an opinion by the
   same window rule as buys (freelance when none matches).

Per **pass**: match the most recent *flagged* opinion for the symbol within
the window before the run's `now_iso` (Phoenix-shifted to a date, same
clock as everything else — evening dictation answers that evening's flag);
no flagged opinion in window → skipped and counted (a pass must answer a
real flag). Flagged mirrors composite's `v_flagged` thresholds
(`ABS(score_sum) >= 4 AND total >= 3`) via `FLAG_MIN_ABS_SCORE` /
`FLAG_MIN_TOTAL` constants **defined in `scorer/db.py` and interpolated
into the view SQL** — one definition serves both the matcher and
`v_flag_response`, and a test pins the constants to composite's view text
so the two systems drift together, never apart.

Duplicate `order_ref`s (already in `decisions`, either leg) are skipped and
counted. The whole ingest is one transaction with the `journal_runs` header.

## Views (in scorer.db, live SQL)

**Window re-keying (applies to every decision-joining view).** The scorer
grades one snapshot per ledger window: weekend and same-day-rerun snapshots
sharing an entry window register marker-only, and only the window's first
registrant owns outcome rows. A Monday fill naively matches Sunday's
snapshot (most recent in window) — which owns nothing. So the views resolve
each decision's snapshot to its window owner before joining outcomes:

```sql
FROM decisions d
LEFT JOIN registered_snapshots r
       ON r.composite_snapshot_id = d.composite_snapshot_id
LEFT JOIN registered_snapshots owner
       ON owner.entry_date = r.entry_date AND owner.ticker_rows > 0
LEFT JOIN ticker_outcomes t
       ON t.composite_snapshot_id = owner.composite_snapshot_id
      AND t.symbol = d.symbol
```

(Marker-only rows keep `ticker_rows = 0`, so `ticker_rows > 0` selects the
owner; a decision matched to a not-yet-registered snapshot has no `r` row
and simply shows NULL paper legs until the nightly scorer catches up — the
view is live, so it heals itself.)

- **`v_decision_outcomes`** — acted decisions joined to their paper baseline
  via the window re-keying above, one row per horizon (LEFT JOIN —
  freelance rows and not-yet-registered opinions appear with NULL paper
  legs). `aligned` is computed from the decision's own stored
  `opinion_score_sum` (the opinion the human saw), not the owner's score.
  `fill_lag_days` (`julianday(fill_date) - julianday(entry_date)`) is
  exposed so readers can tell true slippage from drift on late fills.
  **One row per horizon**: filter or group by `horizon` before aggregating,
  or every decision counts three times — stated in the view comment. Columns: decision fields;
  `aligned` (side agrees with score_sum sign); `entry_slippage` =
  `(fill_price / entry_close - 1)` signed so positive is always
  cost (negated for sells); paper `fwd_return` / `bench_fwd_return`;
  `realized_return` = round-trip from fills when the exit exists
  (`exit_fill_price / fill_price - 1`, sign-flipped for sells).
- **`v_flag_response`** — every matured flagged opinion (thresholds
  interpolated from the shared constants) LEFT JOIN decisions, with the
  decision side of the join re-keyed through the window owner (so a pass
  recorded against Sunday's marker-only snapshot answers Friday's graded
  flag): `response` = `acted` / `passed` (explicit row) / `passed_inferred`
  (no row). **A decision counts as `acted` only when its direction aligns
  with the flag** (buy on a bull flag, sell on a bear flag): without this
  filter, an exit-shaped sell — the first sell of a pre-journal holding, or
  the second lot of a scale-out, both of which legitimately fall through
  exit-attachment — would flip a bull flag from `passed_inferred` to
  `acted` and contaminate the acted-vs-passed comparison this feature
  exists to make. Non-aligned trades remain fully visible in
  `v_decision_outcomes` (`aligned = 0`); they just don't count as answering
  the flag. Carries paper `fwd_return`, benchmark excess, horizon.
- **`v_human_filter`** — the headline aggregate over `v_flag_response`:
  per horizon and response class, `n`, average paper excess in the flag's
  direction. If acted flags outperform passed flags, the filter adds value.
  Day one reports plain averages and `n`; the Wilson helpers can be reused
  later once samples justify it.
- **`v_freelance`** — acted decisions with `composite_snapshot_id` NULL:
  the trades nothing recommended, with realized return when exited.

## Entry skill and schedule

New skill **`.claude/skills/journal-sync/SKILL.md`**, mirroring
account-positions:

1. `main.py journal --db data/scorer.db --last-run` → since-bound.
2. Robinhood MCP `get_equity_orders`, **Agentic account (ending 1936)** pin,
   filled orders only, since the bound. Never paste raw payloads into the
   conversation; build the JSON doc in the scratchpad.
3. `uv run python main.py journal --db data/scorer.db --input <file>`.
4. Report counts per category (matched / freelance / exits / duplicates /
   skipped). Errors: exception type names only.

Manual path (documented in the same skill): user dictates fills or passes;
Claude builds the same JSON with `source: "manual"` and no `order_ref`.

Schedule: launchd slot at **2:40pm weekdays** (matching portfolio's
MON–FRI cadence), right after the portfolio slot (2:30pm), headless
`claude -p "/journal-sync"`. Update `deploy/launchd/install.py` and
`docs/SCHEDULE.md` together, per policy. No-fill runs write a zero-count
`journal_runs` header — that is the "ran and found nothing" signal the
freshness check reads.

The freshness check must compare like-formatted strings:
`ran_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', '-2 hours')` — plain
`datetime('now', ...)` renders with a space separator, and `'T' > ' '`
lexicographically, so any same-UTC-date run would pass a "2-hour" check.
`portfolio_snapshot.sh` has the identical latent bug against `captured_at`;
fix it in the same commit since we're copying the pattern.

Robinhood field assumptions (unverifiable offline, so the skill states
them): the order's **average** fill price feeds `price` (a multi-execution
order must not use the last execution's price), and the executed-at
timestamp must be UTC ISO. Verify both on the first interactive run before
trusting the scheduled slot.

## Error handling

- Per-row *validation* is skip-and-continue with counts (at parse — a
  malformed row never aborts the doc). Ingest itself is all-or-nothing:
  one transaction; a hard SQL failure rolls back everything including the
  run header. (These are different layers, not a contradiction: bad *data*
  skips, bad *execution* aborts.)
- `run()` with fills/passes but no composite.db path raises
  `FileNotFoundError` explicitly (never a `TypeError` from a None path).
- Secret hygiene as everywhere: `type(e).__name__` only.
- composite.db missing/unreadable at ingest → all fills that need matching
  become an error, not silent freelance rows: exit non-zero so the launchd
  log shows it (misclassifying every fill as freelance would silently
  corrupt the filter-value evidence).

## Testing

Mirrors the module layout, offline, injected `now_iso`:

- `tests/test_journal_parse.py` — doc parsing, field validation, skip counts.
- `tests/test_journal_matching.py` — window edges (composite_date == fill_date
  excluded; day 5 included, day 6 not), most-recent-snapshot tie-break, FIFO
  exit attachment, partial-sell attach, freelance buy and sell, direction-
  agnostic matching, duplicate order_ref idempotency (re-run same doc → zero
  new rows), pass requires a flagged opinion.
- `tests/test_journal_db_views.py` — slippage sign for buys and sells,
  realized round-trip, inferred vs explicit pass in `v_flag_response`,
  `v_human_filter` aggregates, freelance rows NULL paper legs, window
  re-keying (decision matched to a marker-only weekend snapshot grades
  against the owning snapshot's outcome rows).
- `tests/test_journal_run.py` — dispatcher: stdin/file input, `--last-run`,
  transaction rollback on hard failure, missing composite.db exits non-zero.
- `test_registry.py` — `journal` entry.
- Flag-threshold pin test: journal's flagged predicate equals composite
  `v_flagged`'s.

## Accepted residuals (adversarial review 2026-07-06)

- **Multi-lot exits:** the first sell closes the whole decision (single
  exit columns); a second scale-out lot becomes its own sell decision
  (usually freelance). Its price is excluded from the original decision's
  `realized_return`, and the exit leg drops the sell's quantity/note.
  Alignment filtering keeps it out of `v_human_filter`; revisit if
  scale-outs become routine.
- **Same-timestamp round trips:** FIFO processes chronologically with buys
  first on exact `filled_at` ties, so a tie produces a zero-duration
  round trip. Negligible.
- **`passed_inferred` before go-live:** flags matured before the journal
  existed count as inferred passes. The scorer and journal both shipped
  2026-07-06, so the pre-journal population is ~empty; documented rather
  than coded around.
- **Late-fill slippage mixes drift:** `entry_slippage` on a fill 3 days
  after the paper entry is mostly market drift; `fill_lag_days` is exposed
  so readers can filter, but no decomposition is attempted.

## Out of scope

- Options trades (equity fills only day one; `get_option_orders` later).
- P&L attribution / quantity-weighted returns (journal measures decision
  quality at the price level).
- Any feedback into composite weights — reading `v_human_filter` stays a
  human decision, same as the efficacy views.
