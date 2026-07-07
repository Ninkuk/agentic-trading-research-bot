# Backtesting foundation — design

**Date:** 2026-07-07 · **Roadmap item:** 7 · **Size:** M (bar store is decision-only)

## Problem

Signals can only be evaluated forward from the day they shipped. Two blockers:

1. **Macro revision look-ahead.** `fred.db observations` is overwritten in place by
   revisions, so any historical read sees today's revised values, not what was
   knowable at the time. The ALFRED vintage machinery (`--vintages`,
   `observation_vintages`, `v_asof`, `set_asof`) exists and is tested but is
   neither backfilled nor scheduled.
2. **No ticker bar history.** `stocks.db`/`etfs.db metrics` are snapshot-scoped and
   pruned at 30 days; the scorer's close ledger (`scorer.db prices`) is append-only
   but close-only and only reaches back to the scorer's ship date.

## Done when (from ROADMAP)

- FRED `--vintages` backfilled (one-shot manual run) and scheduled (nightly).
- A bar-store decision made and **documented** (§ Bar-store ADR below) — no build
  this cycle.
- At least one signal replayed historically end-to-end as proof:
  `main.py backtest` produces a multi-year `v_replay_efficacy` readout for both
  FRED regime signals from real backfilled vintage data.

## Non-goals

- No ticker-grain replay (no historical inputs exist for ticker signals — that is
  exactly what the deferred bar store will provide).
- No changes to composite's or scorer's runtime behavior. The one composite edit
  (§ 2) is byte-identical SQL output.
- No scheduled slot for `backtest` — it is a manual analysis tool, not a collector.

## 1. FRED changes

- **Catalog:** add `Series("SP500", theme="benchmark")` — daily S&P 500 close,
  ~10 years of history (FRED licensing caps the lookback), same fetch machinery.
  This is the benchmark price spine for grading replays.
- **Schedule:** the nightly `fred` job in `deploy/launchd/install.py` becomes
  `job("fred", "--vintages")`; update `docs/SCHEDULE.md` in the same commit.
  Cost: ~31 extra API calls/run (one `/fred/series/observations` with
  `realtime_start=1776-07-04, realtime_end=9999-12-31` per series) and
  full-history payloads each night, idempotently upserted by
  `(series_id, date, realtime_start)`. Accepted for simplicity. Documented
  fallback if nightly runtime ever hurts: move `--vintages` to a separate weekly
  slot (the vintage fetch is a distinct call, so splitting is mechanical).
- **Backfill:** no new code. One manual
  `uv run python main.py fred --db data/fred.db --vintages` run pulls the entire
  ALFRED revision history for all series. Sanity check after: row counts in
  `observation_vintages` per series > 0, and spot-check one revised series
  (e.g. `PAYEMS`) shows multiple `realtime_start` values for a single `date`.

## 2. Composite refactor (behavior-preserving)

Composite's flag thresholds live inline in the signal SQL. Hoist the two FRED
CASE expressions into module constants in
`sources/combiners/composite/catalog.py`:

```python
FRED_CURVE_SCORE = "CASE WHEN value < 0 THEN -1 ELSE 0 END"
FRED_HY_SPREAD_SCORE = (
    "CASE WHEN value >= 5.0 THEN -2 WHEN value >= 4.0 THEN -1 "
    "WHEN value < 3.5 THEN 1 ELSE 0 END"
)
```

and interpolate them back into the existing `fred_curve` / `fred_hy_spread`
`SIGNALS` entries (f-string; the rendered SQL is semantically identical and
existing composite tests must pass unchanged). The backtest combiner imports
these constants, so replayed flags cannot drift from live flags.

## 3. The `backtest` combiner

Fourth combiner, standard four files, registered in `registry.py` as
`main.py backtest --db data/backtest.db`. Like composite, `fetch.py` has **no
network** — it reads `fred.db` ATTACHed read-only. No API keys touch this slice.

### catalog.py

- `REPLAY_SIGNALS`: `fred_curve` (series `T10Y2Y`, score CASE =
  `composite.catalog.FRED_CURVE_SCORE`) and `fred_hy_spread` (series
  `BAMLH0A0HYM2`, score CASE = `composite.catalog.FRED_HY_SPREAD_SCORE`).
- `BENCHMARK_SERIES = "SP500"`.
- Horizons imported from `sources.combiners.scorer.catalog.HORIZONS` (5/10/21
  trading days).

### fetch.py

`attach_ro`/`detach` (same `file:...?mode=ro` pattern as composite). Two pure
copy functions:

- `harvest_vintages(conn)` — `SELECT series_id, date, realtime_start, value FROM
  src.observation_vintages WHERE series_id IN (replay series)`.
- `harvest_benchmark(conn)` — `SELECT date, value FROM src.observations WHERE
  series_id = 'SP500'` (index closes are unrevised; plain observations suffice).

Skip-and-continue per series: on failure, `conn.rollback()` and print
`type(e).__name__` only (house rule, even though no URLs/keys are in play).

### db.py

Schema (idempotent `ensure_schema`): `snapshots` header (house convention),
`signal_vintages(series_id, date, realtime_start, value, PK(series_id, date,
realtime_start))`, `benchmark_closes(date PRIMARY KEY, close REAL NOT NULL)`.
Both data tables are upsert-keyed history (INSERT OR REPLACE), not
snapshot-scoped; `prune` deletes old snapshot headers only.

Views (the actual product):

- **`v_pit_signal`** — decision-date spine = `benchmark_closes.date` (SP500
  trading days), cross-joined to replay series. For each (series, D): the value
  **as known on D** — among observations having any vintage with
  `realtime_start <= D`, take the latest observation `date`, and within it the
  newest qualifying vintage's `value`. Pure SQL (window function), no per-date
  loop, no `calendar_now` dependency — the spine supplies every D at once.
- **`v_replay_flags`** — applies each signal's imported score CASE to its PIT
  value → the flag composite would have emitted on D, for every D in the spine.
- **`v_replay_returns`** — entry = first `benchmark_closes.date` **strictly
  after** D (same no-overnight-look-ahead rule as scorer's `entry_for`);
  `fwd_return = exit_close / entry_close - 1` where exit is the close
  `H` trading days after entry (row-offset over the spine, matching the
  scorer's "ledger price_date steps" horizon semantics), one row per horizon.
  Dates within the last `max(HORIZONS)` trading days yield NULL (not yet
  matured) via LEFT JOIN.
- **`v_replay_efficacy`** — per signal × flag × horizon: `hit` = sign
  agreement between flag and forward benchmark return (flag < 0 hits when
  return < 0; flag > 0 hits when return > 0; flag = 0 rows are the neutral
  base rate, reported in their own group but excluded from hit grading).
  Columns mirror scorer's `v_signal_efficacy`: `hit_rate`, `n_bench`,
  `hit_ci_lo`/`hit_ci_hi` (Wilson 95%, reusing scorer's `_wilson` SQL helper),
  `reliable` (`n_bench >= 30`), plus `avg_fwd_return`.

### run.py

Testable `run(db_path, now_iso, fred_db_path, *, attach=..., harvest_vintages=...,
harvest_benchmark=...)` seams + thin argparse `main(argv)` with `--db`
(default `backtest.db` — always pass `data/backtest.db`), `--fred-db`
(default `data/fred.db`), `--keep-days`. Flow: ensure_schema → snapshot header →
attach fred → copy → detach → print `v_replay_efficacy` summary → prune.

## 4. Bar-store ADR (decision only — recorded here)

**Decision: keep `scorer.db prices` untouched; ticker-grain bar history will be
a new dedicated screener slice (working name `bars`) with its own DB, built as
its own roadmap item when ticker replay is actually needed.**

Rationale:

1. The ledger's contract is *evidence* — closes actually harvested from
   production stocks/etfs snapshots. Backfilled OHLC from a different endpoint
   would change that provenance and flow into live grading
   (`entry_for`/`mature`) and `v_basis_breaks`.
2. OHLC needs its own fetch (candidate: stockanalysis historical endpoint —
   within the trusted exception; must be live-verified at build time per the
   repo invariant) with its own cadence and retention.
3. A separate slice is the house pattern: one source, one DB, four files.

Rejected alternative: widening `prices` with nullable OHLC columns — mixes
provenance in one table and conflicts with the ledger's `INSERT OR IGNORE`
self-heal semantics (a later OHLC backfill could not correct a close-only row
without changing ledger semantics).

At ship time, ROADMAP item 8 gains a "bar-store build (`bars` slice)" bullet
pointing at this ADR.

## 5. Error handling

- Copy failures: per-series skip-and-continue, rollback, `type(e).__name__`
  only.
- Missing vintage data (backfill not yet run): views LEFT JOIN and yield empty
  results rather than erroring — same partial-run convention as composite.
- `run.py` exits nonzero only on schema/IO failure, not on empty sources.

## 6. Testing

Offline, mirroring layers:

- `test_backtest_catalog.py` — roster shape; score CASEs are identical objects
  to composite's constants; horizons come from scorer.
- `test_backtest_fetch.py` — attach/copy against temp fred.db fixtures;
  skip-and-continue.
- `test_backtest_db_schema.py` / `test_backtest_db_views.py` — the load-bearing
  suite:
  - **No-look-ahead:** insert a revision vintage with `realtime_start > D`;
    `v_pit_signal` at D unchanged.
  - Revision visibility: same revision IS reflected for D' >= its
    `realtime_start`.
  - Publication lag: an observation whose earliest vintage is after D is
    invisible at D (even though its `date` <= D).
  - Entry is strictly after D; horizon exit is H spine rows after entry;
    unmatured dates yield NULL.
  - Efficacy math: hit/miss classification per flag sign, Wilson bounds,
    `reliable` gate, neutral-flag exclusion.
- `test_backtest_run.py` — end-to-end with injected seams; empty-fred case.
- `test_registry.py` — `backtest` entry.
- Composite: existing tests pass unchanged after the constant hoist (that IS
  the parity test, plus a direct assertion that the constants appear in the
  rendered `SIGNALS` SQL).
- FRED: catalog test updated for the 31st series.

## 7. Ops / ship checklist

1. Land code + tests (all four gates green).
2. One-shot vintage backfill; sanity-check counts (§ 1).
3. Re-run `deploy/launchd/install.py` so the nightly `fred` job carries
   `--vintages`; update `docs/SCHEDULE.md` (fred job note + a "manual tools"
   note that `backtest` is unscheduled by design).
4. Run `main.py backtest --db data/backtest.db`; read `v_replay_efficacy` —
   the multi-year readout is the roadmap proof. Record the headline numbers in
   the ROADMAP prune note.
5. Prune ROADMAP item 7; add the bar-store build bullet to item 8; update the
   `fred-vintages-deferred` memory (it is no longer deferred).
