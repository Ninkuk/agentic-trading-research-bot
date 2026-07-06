# Scorer next-day entry — implementation plan

Spec: `docs/superpowers/specs/2026-07-06-scorer-nextday-entry-design.md`.
Source changes in `sources/combiners/scorer/db.py` + `catalog.py` comment;
test updates across the scorer test files; one-time live-DB migration.

## Task 1 — red: new-contract tests

- `test_entry_for_respects_guard` → rewritten: first close strictly after
  the date; forward-staleness refusal; unknown symbol refusal.
- New `test_same_night_registration_defers`: ledger ends at composite_date
  → `register_snapshot` returns (0, 0) and writes NO marker; after
  inserting the next close, the same call registers normally.
- `test_duplicate_entry_window_registers_marker_only` → Fri/Sat composite
  dates both anchor to the Monday close.
- `test_bench_gap_does_not_discard_gradeable_night` → reworked per spec.
- Shift entry expectations one day in the roundtrip/bench/basis-guard
  tests; `test_split_after_exit_does_not_block` uses horizons (4, 5) so
  one window still ends before the break.
- `test_scorer_db_views` / `test_scorer_run`: adjust seeds so registration
  has a post-composite_date close available; expectations shift a day.

## Task 2 — green: db.py + catalog.py

1. `entry_for`: `price_date > ? AND price_date <= date(?, '+N days')`
   ORDER BY price_date ASC LIMIT 1; docstring for forward guard.
2. `register_snapshot`: anchor = `MIN(price_date) WHERE price_date > ?`;
   early-return (0, 0) with a `defer composite snapshot …` print when the
   anchor is NULL, before the marker INSERT; docstrings updated (dedupe
   comment, catch-up note in module header).
3. `catalog.py`: ENTRY_MAX_AGE_DAYS comment now describes the forward
   bound.

## Task 3 — migration + docs + ship

- One-time live migration (nothing matured, lossless): delete all rows
  from the three outcome tables and `registered_snapshots` in
  `data/scorer.db`; verify re-registration defers cleanly on the next run.
- `docs/SCHEDULE.md` scorer line: note the one-night registration lag.
- `docs/ROADMAP.md`: prune item 2.
- Full gates, commit.
