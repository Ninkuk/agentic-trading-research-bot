# Scorer basis-break guard — implementation plan

Spec: `docs/superpowers/specs/2026-07-06-scorer-basis-guard-design.md`.
One file of source changes (`sources/combiners/scorer/db.py`), two test
files. TDD: tests first, red → green.

## Task 1 — red: guard contract tests

`tests/test_scorer_db_write.py` (reuse the file's existing seed/register
helpers):

- `test_split_in_window_stays_pending` — flat $100 stock, 2:1 split day 4,
  register h=5 → after `mature`, row has `matured_at IS NULL`.
- `test_gradual_crash_still_matures` — −30 % over 5 days, every day-over-day
  ratio within [0.55, 1.8] → matures with the true negative return.
- `test_split_after_exit_does_not_block` — split lands after the h=5 exit
  date → the h=5 row matures; the h=10 row (window spans the split) stays
  pending.
- `test_benchmark_break_blocks_symbol_rows` — SPY ledger contains a break
  inside the window → symbol row stays pending; regime row stays pending.

`tests/test_scorer_db_views.py`:

- `test_v_basis_breaks_flags_split_only` — ledger with one split pair and
  normal noise elsewhere → view returns exactly the split pair with its
  ratio.

Run: `uv run pytest tests/test_scorer_db_write.py tests/test_scorer_db_views.py`
— new tests fail, existing pass.

## Task 2 — green: db.py

1. Constants `BASIS_BREAK_LO = 0.55`, `BASIS_BREAK_HI = 1.8` beside
   `PRICE_KEEP_DAYS`.
2. `_SCHEMA` becomes an f-string; add `v_basis_breaks` view (consecutive-date
   pairs via correlated `MAX(price_date) < price_date`, break condition by
   multiplication, baked thresholds).
3. `_MATURE_SYMBOL`: add `NOT EXISTS` break-scan clauses for the graded leg
   and `:bench`, window `(entry_date, x.xdate]`, beside the julianday bound.
   `_MATURE_REGIME`: same clause for `:bench` only.
4. `mature()` passes `lo`/`hi` params; extend the comment block above
   `_MATURE_SYMBOL` documenting the guard (quarantine-is-permanent
   semantics, spec reference).

## Task 3 — gates + ship

- `uv run pytest` (full), `uv run ruff check`, `uv run ruff format`,
  `uv run mypy`.
- Update `docs/ROADMAP.md`: prune item 1; move the option-(a) enrichment +
  3:2 residual into the item 8 backlog.
- Commit (docs + code), pre-commit hook runs the four gates.
