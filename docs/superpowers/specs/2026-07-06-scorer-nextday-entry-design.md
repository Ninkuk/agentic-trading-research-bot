# Scorer next-day entry — design

**Date:** 2026-07-06
**Status:** approved (roadmap item 2)

## Problem

`entry_for` selects the newest ledger close **≤** `composite_date`, but the
composite forms its opinion at 9:05 pm *using data through that same close*.
The earliest a human can act is the next session — so every graded outcome
silently pockets the overnight gap, which is exactly where retail-attention
signals (reddit, SI spikes, insider clusters) concentrate their apparent
edge. Zero rows have matured, so the fix lands before any contaminated
grade exists.

## Design: defer registration until the entry close exists

Entry becomes the **first ledger close strictly after** `composite_date`
(the honest choice for a close-only ledger — one extra day of drift,
zero look-ahead). That close doesn't exist on the night the composite
snapshot is created, so:

- **`entry_for` flips direction:** first `price_date > composite_date`
  and `<= composite_date + ENTRY_MAX_AGE_DAYS` (the staleness guard now
  bounds how far *forward* a thin symbol's next print may be; 7 days still
  covers any holiday weekend).
- **Registration defers instead of consuming:** `register_snapshot`
  computes the window anchor as `MIN(price_date) > composite_date` (global
  across symbols, same reasoning as today's global anchor). If none exists
  yet, it returns **without writing the marker row** — the snapshot stays
  unregistered and the nightly loop (`registered_ids` diff) naturally
  retries it the next night. No run.py changes.
- **Dedupe unchanged in shape:** Fri/Sat/Sun composite snapshots all
  anchor to Monday's close and collapse to one grading via the existing
  `registered_snapshots.entry_date` marker-only path; the earliest
  snapshot (lowest id) wins, as now.
- **Maturation unchanged:** horizons still count distinct ledger dates
  after `entry_date`; gap guard and basis guard apply as-is.

### Steady-state cadence shift

Each night registers the *previous* night's composite snapshot (one-night
lag); the newest snapshot defers with a printed
`defer composite snapshot N: ledger not past <date>` line. Still one
registration per trading day — just lagged. `docs/SCHEDULE.md`'s scorer
line gets a note.

### Catch-up semantics improve

Today a late-registering snapshot enters at "whatever ledger window is
current" (drift). Under next-day entry the entry is *historically exact*
(first close after composite_date) whenever the ledger retains it — the
db.py header docstring is updated accordingly.

## Live-DB migration (one-time, lossless)

All currently registered rows carry look-ahead entries; none have matured.
Delete every row from `ticker_outcomes`, `signal_outcomes`,
`regime_outcomes`, and `registered_snapshots`; the next scorer runs
re-register all retained composite snapshots under the new semantics as
their entry closes arrive (Jul 2–5 snapshots anchor to the Jul 6 close,
harvested from Tuesday's pre-open batch). No vintage flag needed — the
permanent record starts clean, entirely post-fix.

## Tests

Existing registration/maturation tests shift one day (entry `DAYS[i+1]`
instead of `DAYS[i]`) — updated in place, keeping each test's original
intent. New/reworked coverage:

- `entry_for` returns the first close strictly after the date; refuses
  when the next print is beyond the forward guard; still refuses unknown
  symbols.
- Same-night registration defers: no marker row, snapshot re-registers on
  a later call once the ledger advances.
- Weekend dedupe still collapses Fri/Sat/Sun to the Monday anchor.
- `test_bench_gap_does_not_discard_gradeable_night` reworked to the new
  semantics: a snapshot whose ledger hasn't advanced past composite_date
  defers rather than registering a partial window.

## Out of scope

Open prices (ledger is close-only by design); regrading horizons from the
open; any change to harvest, maturation SQL, prune, or the CLI.
