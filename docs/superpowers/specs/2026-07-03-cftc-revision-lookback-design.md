# CFTC Revision Lookback + Cross-Screener Write Robustness — Design

**Date:** 2026-07-03
**Status:** Approved, ready for implementation planning
**Origin:** Deferred follow-ups from the `cftc_screener` whole-branch review
(2026-07-03). Two independent fixes, both in run-orchestration code.

## Goal

1. **CFTC revision capture (fixes review finding I1).** The CFTC screener's
   incremental fetch passes `since = max_stored_date` and filters strictly
   `report_date > since`, so on a steady-state re-run **no already-stored week
   is ever re-fetched** — and the `(code, report_date)` upsert's whole reason
   for existing (CFTC revises prior weeks) never fires. Make re-runs re-fetch a
   recent lookback window so revisions are re-absorbed, with a `--full` escape
   hatch for rare deep corrections.
2. **Cross-screener write robustness.** In both `cftc_screener/run.py` and
   `fred_screener/run.py`, the DB writes sit *outside* the per-item
   `try/except`, so a write failure for one market/series aborts the entire run
   instead of skip-and-continue. Move the writes inside the guarded block.

## Scope note (corrected during design)

I1 is **CFTC-only**. FRED's `run` does not use a `since = max_stored`
optimization — it re-fetches from `--start` (or full history) every run and
upserts, so it already captures revisions. The write-robustness fix (#2) applies
to **both** CFTC and FRED.

## Why a lookback (not strict incremental, not always-full)

CFTC corrections are **not routine** — they occur as-needed when data-quality
errors or trader-classification changes surface, and can reach back several
weeks (e.g. the 2009 VIX correction spanned three as-of dates). There is no
fixed window guaranteed to contain every revision. A modest recent-weeks
lookback re-absorbs the common case cheaply; a `--full` re-pull covers the rare
deep case. Chosen over "always re-pull like FRED" to preserve the incremental
efficiency the original plan chose, and over "lookback only" so deep
corrections have a built-in remedy.

## Design

Changes are confined to the two run modules, their tests, and docs. **No change
to** `fetch.py`, `db.py`, `catalog.py`, `http_client.py`, or any view.

### 1. CFTC lookback (`cftc_screener/run.py`)

- Add `_LOOKBACK_WEEKS = 10` (module constant).
- Add `full: bool = False` to `run(...)` and a `--full` flag to `main`.
- Per selected market, compute the inclusive fetch floor:
  - `full` **or** `max_report_date(conn, code) is None` → floor = the CLI
    `start` (may be `None` → full history).
  - otherwise → floor = `max_stored_date − _LOOKBACK_WEEKS`
    (`(datetime.fromisoformat(max_stored) - timedelta(weeks=_LOOKBACK_WEEKS)).date().isoformat()`).
- Fetch with that floor as the **inclusive** bound:
  `fetch_rows(code, app_token=app_token, start=floor)` (no `since=`). `_build_url`
  already emits `report_date_as_yyyy_mm_dd >= 'floorT00:00:00'` for `start`, so
  the last ~10 weeks are re-fetched and the upsert overwrites any revised week
  in place; no duplicate dates.
- `fetch.py` is untouched. The strict `since` primitive remains (still
  unit-tested); the run path simply stops using it.

### 2. Write robustness (`cftc_screener/run.py` + `fred_screener/run.py`)

Move the per-item DB writes inside the existing `try`, and roll back on failure:

- CFTC: `upsert_markets` + `write_cot` move inside the per-market `try`. On any
  exception: `conn.rollback()`, print `warning: skipping {code}:
  {type(e).__name__}` to stderr, `continue`. `successes` increments only after
  a clean write.
- FRED: `upsert_series` + `write_observations` move inside the per-series `try`,
  same `conn.rollback()` + skip-and-continue. (FRED's existing message form
  `warning: skipping {series_id}: {type(e).__name__}` is preserved — still logs
  only the exception class, never the key/URL.)

Partial-write nuance: each writer commits internally, so if `upsert_markets`
commits and then `write_cot` raises, the dimension row persists with no facts —
harmless (a later successful run fills it), and `rollback()` clears only the
failed writer's uncommitted statements.

### 3. Tests

- `tests/test_cftc_run.py`:
  - **Update** `test_run_passes_since_from_max_stored_date` → assert the
    incremental run passes `start = max_stored − 10 weeks` (the boundary the
    fake fetch receives), replacing the old strict-`since` assertion.
  - **Add** `test_run_full_ignores_stored_max`: with `full=True`, `start` passed
    to fetch is the CLI start (or `None`), not the lookback floor.
  - **Add** `test_run_skips_failing_write_and_continues`: a market whose
    `write_cot` raises (injected) is skipped, the good market persists, and a
    snapshot is still written.
- `tests/test_fred_run.py`:
  - **Add** `test_run_skips_failing_write_and_continues`: a series whose
    `write_observations` raises is skipped-and-continued; the good series
    persists.

### 4. Docs / memory

- Update the CFTC design spec
  (`docs/superpowers/specs/2026-07-03-cftc-screener-design.md`) incremental
  section to describe the lookback + `--full`.
- Correct the `incremental-since-misses-revisions` memory: I1 is CFTC-only
  (FRED already re-pulls); mark the lookback + `--full` as the resolution.

## Non-goals

- No change to FRED's fetch cadence (it already re-pulls).
- No deferred/batched-commit rework of the writers (they commit per item today;
  keep that — the rollback handles the failed tail).
- No configurable lookback via CLI — `_LOOKBACK_WEEKS` is a constant; `--full`
  is the escape hatch. (YAGNI.)

## Success criteria

- A second CFTC run re-fetches the last 10 weeks and overwrites a revised week
  in place (verified by test asserting the `start` floor).
- `--full` forces a complete re-pull.
- A single market/series failing its DB write no longer aborts the run (both
  screeners).
- Full suite green (was 169; +3 new CFTC/FRED tests, 1 updated).
