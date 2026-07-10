# Backlog — deferred work

Durable follow-ups that are scoped but intentionally not built yet. Unlike the
transient specs under `docs/superpowers/`, this file persists. Each item is
self-contained enough to pick up cold.

## Backtest: CFTC asset-class replay (`cftc_mm_extreme`, `cftc_lev_extreme`)

**Status**: deferred (2026-07-08). The rest of the GO-scoped backtest
expansion from
`docs/superpowers/specs/2026-07-08-backtest-replayability-spike.md` shipped —
market grain (`cboe_vix`, `cboe_vix_backwardation`, `nyfed_rrp`, `tsy_tga`,
`cboe_equity_pcr`) plus the multi-benchmark spine and the energy `eia_*`
signals. Only the two CFTC signals remain.

**Why deferred, not just unbuilt.** Two independent reasons:

1. ~~**Data availability.**~~ **RESOLVED 2026-07-09 (plan 005).** Asset-class
   signals grade against a sector proxy (energy→XLE, metals→GLD, …), never
   SP500 — grading a sector bet against equities flatters it whenever equities
   fall. Those proxies used to have only a few days of closes in `scorer.db`'s
   permanent `prices` ledger, so any asset-class replay graded ~zero rows.

   `main.py pricehistory --db data/scorer.db` (one-shot, never scheduled)
   backfilled all 18 crosswalk proxies from stockanalysis's history API:
   **118,644 rows**, XLE to 1998-12-23, GLD to 2004-11-19, DBA to 2007-01-08,
   TLT to 2002-07-29. `CLASS_BENCHMARKS` now carries XLE/GLD/DBA/TLT, so
   **step 1 of the build recipe below is done.** The `eia_*` signals went from
   `n_bench = 0` to 339–1,595 graded rows per direction/horizon.

   Note `v_pit_market` anchors each signal's as-of value onto the *benchmark's*
   trading-day spine, so `n_days` is bounded by the benchmark's close count —
   that, not signal depth, was always the bottleneck. A `neutral` row still
   shows `n_bench = 0` by design (`hit` is NULL when `score = 0`).
2. **Unvalidatable-now complexity.** CFTC is the one *hard* signal in the
   batch. Its composite input is `AVG(cot_index)` per asset class, where
   `cot_index` is a **3-year rolling percentile** of net positioning computed
   in `cftc.db`'s `v_disagg_cot_index_latest` / `v_tff_cot_index_latest`.
   Replaying it point-in-time means reconstructing that rolling percentile
   as-of each historical date from the raw COT net-position history — a
   sliding-window recompute (like `cboe_equity_pcr`, but 3-year and
   percentile-of-net-position, not trailing-252-of-a-raw-value). Building that
   with **no live matured rows to check against** (0, per reason 1) risks a
   silent point-in-time bug surfacing months later unwatched — exactly what
   the repo's *live-verify / no-silent-row-drops* invariant (CLAUDE.md) warns
   against.

**Build recipe (when the ledger has matured).**

1. **Benchmarks**: add the remaining class proxies to
   `backtest/catalog.py:CLASS_BENCHMARKS` (metals→GLD, ags→DBA, rates→TLT),
   harvested from `scorer.db` `prices` exactly like XLE. The multi-benchmark
   spine (`benchmark_closes` keyed by `(benchmark, date)`, per-benchmark
   `v_spine`/`v_replay_returns`, efficacy join on `(benchmark, asof_date)`)
   already supports this — no view changes needed.
2. **As-of `cot_index`**: the hard part. `cot_index(code, report_date)` is a
   rolling percentile of net positioning over a ~3-year window ending at
   `report_date`. Copy the raw per-`(code, report_date)` net-position series
   out of `cftc.db` (`cot_disagg` / `cot_tff`) into a backtest store, then
   build a dedicated as-of view (new `flag_mode`, cf. `pctile`'s `v_pit_pcr`)
   that recomputes the rolling percentile using only report rows `<=` the
   as-of date. Watch the documented CFTC hazards: `_upsert_facts` overwrites
   revised weeks in place (no revision trail — accept the with-caveat class),
   and there's a ~3-day publication lag (report_date = Tuesday close,
   published the following Friday) not separately tracked.
3. **Asset-class aggregation**: composite does `AVG(cot_index) GROUP BY
   asset_class` over the markets in each class (`markets.asset_class`). The
   replay must reproduce that grouping as-of, then reuse composite's score
   CASE verbatim (hoist it to a `CFTC_COT_INDEX_SCORE` constant in
   `composite/catalog.py`, mirroring the other hoisted CASEs). Grade each
   asset class against its proxy benchmark from step 1.
4. **Tests**: synthetic `cot_index` history proving the rolling percentile is
   recomputed as-of (no look-ahead), and asset-class grading against the
   correct proxy — the pattern used for `cboe_equity_pcr` + `eia_*`.

**Also structurally out of scope** (from the spike's NO-GO set, unchanged):
the 6 forward-only signals (`fomc_blackout`, `econ_imminent`,
`usda_stocks_to_use`, `reddit_trending`, `stocks_rsi`, `edgar_insider`) and
the ticker-grain signals (`si_*`, `sv_ratio_spike`, `ftd_persistent`), which
need a per-ticker forward-return spine — a separate, larger plan.
