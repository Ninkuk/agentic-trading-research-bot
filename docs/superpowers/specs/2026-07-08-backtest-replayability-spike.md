# Spike: which composite signals can be backtested point-in-time

**Planned at**: commit `ef40b0c`, 2026-07-08. **Type**: investigation only — no
source code was modified. All findings below come from reading committed
`db.py` schemas/prune docstrings (present in this worktree); no fetcher or
network call was run. `data/` does not exist in this worktree (gitignored),
so no live-DB corroboration query was executed — every classification below
is derived entirely from static inspection, per the executor instructions'
guidance that a signal can be fully classified from its source `db.py` when
that settles the class (it did, for all 22).

## Drift check

```
git diff --stat ef40b0c..HEAD -- sources/combiners/backtest
```
Empty — no drift. The "Current state" premises in the plan hold as written.

## How the current FRED replay works

Read in full: `sources/combiners/backtest/catalog.py`, `db.py`, `fetch.py`,
`run.py`.

- **`fetch.py`** copies two things out of `fred.db` (ATTACHed read-only, no
  network): the full ALFRED `observation_vintages` history for the two
  replay series (`harvest_vintages`), and the unrevised `SP500` daily closes
  as the grading benchmark (`harvest_benchmark`).
- **`db.py`** stores those copies in `signal_vintages` (PK
  `series_id, date, realtime_start`) and `benchmark_closes` (PK `date`), then
  builds four views:
  - **`v_pit_signal`** — for every benchmark trading date `D` and series,
    picks the *latest observation whose `realtime_start` is `<= D`* (a
    correlated subquery ordered by `date DESC, realtime_start DESC LIMIT 1`).
    This is the as-of read: it reconstructs exactly what was publicly known
    on `D`, never a later revision.
  - **`v_replay_flags`** — reruns the *identical* score `CASE` expressions
    from `composite/catalog.py` (`FRED_CURVE_SCORE`, `FRED_HY_SPREAD_SCORE`,
    imported not re-typed) over `v_pit_signal.value`, so the replayed flag is
    provably the same flag composite would emit.
  - **`v_replay_returns`** — joins `v_spine` (row-numbered benchmark dates) to
    itself to get the forward return from the first close *strictly after*
    `asof_date` (no overnight look-ahead) to `horizon` trading days later.
  - **`v_replay_efficacy`** — hit-rate scoreboard (sign agreement between
    flag direction and forward return) with a Wilson CI (`scorer.db`'s
    `_wilson`/`RELIABLE_MIN_N`, imported not reimplemented), grouped by
    `signal_id, direction, horizon`.

**The template's shape, for anything that expands on it**: (1) copy an
as-of-queryable history table out of the source DB, (2) build an as-of view
equivalent to `v_pit_signal` — critically, **not** a literal reuse of
composite's own SQL, since every composite signal query is written as
"latest row" (`ORDER BY date DESC LIMIT 1` / `WHERE date = (SELECT MAX...)`),
which is exactly what must be replaced by an as-of predicate, (3) reuse the
composite score `CASE` verbatim, (4) join to a forward-return spine.

## Classification of the 22 voting signals

Excludes `portfolio_holding` (informational, never votes, per the plan).
Confirmed count: `grep -c '"signal_id":' sources/combiners/composite/catalog.py`
→ **23** signal definitions; this table has **22** rows (23 minus
`portfolio_holding`).

| signal_id | source DB | backing table/view | keying | prune model | class | justification |
|---|---|---|---|---|---|---|
| `fred_curve` | fred.db | `observation_vintages` | PK `(series_id, date, realtime_start)` | never pruned (historical store) | **PIT-replayable (revision-aware)** | ALFRED vintages; already implemented in `backtest/db.py` `v_pit_signal` today |
| `fred_hy_spread` | fred.db | `observation_vintages` | same | same | **PIT-replayable (revision-aware)** | same as above; already implemented |
| `cboe_vix` | cboe_stats.db | `vix_daily` | PK `date` | single-table snapshot-header delete only; `vix_daily` "NEVER cascade-pruned" (docstring) | **PIT-replayable-with-caveat** | daily exchange close, upsert-keyed per date, permanent; unrevised in practice; same-day publication (minimal lag) |
| `cboe_vix_backwardation` | cboe_stats.db | `vix_daily` | same | same | **PIT-replayable-with-caveat** | same table (`close` vs `vix3m`); same caveat |
| `cboe_equity_pcr` | cboe_stats.db | `pcr_daily` | PK `date` | same permanent-history model | **PIT-replayable-with-caveat** | percentile is computed over a trailing-252-row window; an as-of view must restrict that window to rows `<= asof_date` (doable — full series is retained); put/call volumes are unrevised |
| `fomc_blackout` | fomc.db | `events` (monitor_common) | PK `(event_type, event_date, subtype)`, **upsert-in-place** | events never deleted, but no revision trail — `upsert_events` firms up status/payload *in place*, only latest `fetched_at` kept | **Forward-only** | mutable calendar row, not vintaged: a past payload (e.g. `window_end`) that was later corrected is unrecoverable. Also always emits `score=0` (composite comment: "Gate, not direction") — non-directional even if replayed |
| `econ_imminent` | econ_calendar.db | `events` (monitor_common) | same monitor_common schema | same | **Forward-only** | identical structural reasoning to `fomc_blackout`; also always `score=0` (non-directional COUNT gate) |
| `mcal_days_to_opex` | market_calendar.db | `events`, sourced from `compute.py` | events table is mutable-in-place, BUT the underlying values are a **pure deterministic function** (`compute.opex_dates`/`third_friday`) of (year, static holiday set) | n/a — doesn't need stored history | **PIT-replayable (deterministic, not vintage-dependent)** | OPEX/quad-witching dates are recomputable for any historical date directly from the pure function in `sources/monitors/market_calendar/compute.py` (CLAUDE.md's named exception to the four-file rule) — a stronger guarantee than a vintage table, since the rule itself never changes |
| `nyfed_rrp` | nyfed.db | `repo_ops` (via `v_rrp_trend`) | PK `operation_id` | "Fact tables ... NEVER cascade-pruned" | **PIT-replayable-with-caveat** | NY Fed publishes op results same-day; permanent per-operation history; no documented revision behavior found |
| `tsy_tga` | treasury.db | `dts_cash` (via `v_tga_trend`) | PK `(record_date, account_type)` | "fact tables ... NEVER cascade-pruned" | **PIT-replayable-with-caveat** | Daily Treasury Statement, permanent per-date history; rarely revised, published next business day |
| `cftc_mm_extreme` | cftc.db | `cot_disagg` (via `v_disagg_cot_index_latest`) | PK `(code, report_date)` | "COT history is NOT snapshot-scoped ... single-table delete of snapshot headers only" | **PIT-replayable-with-caveat** | `_upsert_facts` docstring explicitly: **"Revised weeks overwrite in place"** — real, documented revision risk (occasional CFTC corrections); also a ~3-day publication lag (report_date = Tuesday close, published the following Friday) not separately tracked |
| `cftc_lev_extreme` | cftc.db | `cot_tff` (via `v_tff_cot_index_latest`) | same | same | **PIT-replayable-with-caveat** | identical to `cftc_mm_extreme` |
| `eia_crude_stocks` | eia.db | `eia_obs` (via `v_weekly_change`) | PK `(series_id, period)` | "NEVER cascade-pruned" | **PIT-replayable-with-caveat** | `write_observations` docstring: "revised values overwrite in place" — rare/small EIA revisions; weekly report has a few days' publication lag not separately tracked |
| `eia_natgas_storage` | eia.db | `eia_obs` (via `v_weekly_change`) | same | same | **PIT-replayable-with-caveat** | identical to `eia_crude_stocks` |
| `usda_stocks_to_use` | usda.db | `wasde_obs` (via `v_wasde_stocks_to_use`) | PK `(commodity, region, metric, market_year, unit)` — **no report_date/period in the key** | "NEVER cascade-pruned" (docstring), but see justification | **Forward-only** | Sharpest finding of this spike: `wasde_obs` looks like upsert-keyed history but isn't — WASDE reissues a balance-sheet line for the *same market_year* every month for ~12 months, and the PK has no time component to distinguish those monthly reports, so each new report overwrites the prior one in the same row. Only the latest-ever value for a market_year survives; a past month's WASDE estimate cannot be reconstructed. Structurally identical in effect to snapshot-scoped/latest-only, despite not routing through the shared cascade prune |
| `si_days_to_cover` | short_interest.db | `short_interest` (via `v_high_days_to_cover`) | PK `(symbol, settlement_date)` | `replace_settlement`: delete-then-insert per settlement_date; "NOT snapshot-scoped ... must NOT cascade" | **PIT-replayable-with-caveat** | per-settlement history is retained permanently (ticker-grain, large volume); risk: a FINRA repost of a corrected file for an old settlement replaces that date's rows with no audit trail of the original value (the docstring's explicit reason for using replace over upsert); ~1-2 week publication lag vs. settlement_date, but `settlements.fetched_at` gives a usable "known-by" timestamp proxy |
| `si_spike` | short_interest.db | `short_interest` (via `v_short_interest_spikes`) | same | same | **PIT-replayable-with-caveat** | identical to `si_days_to_cover` |
| `sv_ratio_spike` | short_volume.db | `short_volume` (via `v_ratio_spikes`) | PK `(symbol, date)` | `replace_day`: delete-then-insert per date; "NOT snapshot-scoped" | **PIT-replayable-with-caveat** | daily granularity, ~T+1 publication lag; same repost-risk caveat as short interest; `days.fetched_at` gives a known-by proxy |
| `ftd_persistent` | ftd.db | `fails` (via `v_persistent`) | PK `(cusip, settlement_date)` | `replace_period`: delete-then-insert per period; "NOT snapshot-scoped" | **PIT-replayable-with-caveat** | ~2-week publication lag typical of SEC FTD data; same repost-risk caveat; `periods.fetched_at` gives a known-by proxy |
| `reddit_trending` | reddit.db | `observations` (via `v_signals`) | `observations` FK's `snapshot_id`; `prune()` delegates to shared `screener_common.prune(..., child_table="observations")` — the generic cascade | **Forward-only** | Textbook snapshot-scoped cascade (CLAUDE.md's own example shape). Production retention is `--keep-days 90` (`docs/SCHEDULE.md`, `reddit-intraday` slot) — older snapshots and their observations are deleted outright |
| `stocks_rsi` | stocks.db (`stock_analysis_screener`) | `metrics` (via `v_latest`) | `metrics` FK's `snapshot_id`; `prune()` delegates to `screener_common.prune(..., child_table="metrics")` | same cascade | **Forward-only** | Same cascade shape; production retention `--keep-days 30` (`docs/SCHEDULE.md`, `preopen` slot: "stocks/etfs run `--keep-days 30`: their metrics rows are snapshot-scoped") |
| `edgar_insider` | edgar.db | `filings` (via `v_tickered`) | `filings` FK's `snapshot_id`; `prune()` delegates to `screener_common.prune(..., child_table="filings")` | same cascade | **Forward-only** | Same cascade shape; production retention `--keep-days 90` (`docs/SCHEDULE.md` edgar line: "filings are snapshot-scoped and this bound IS `v_activity_history`'s lookback depth") |

**Tally**: 3 PIT-replayable (2 vintage-based, already built; 1 deterministic)
+ 13 PIT-replayable-with-caveat + 6 Forward-only = **22**.

## Recommendation

**Coverage if built**: 16 of 22 voting signals (73%) are structurally
PIT-replayable, either cleanly (3) or with a documented caveat (13). The
other 6 (`fomc_blackout`, `econ_imminent`, `usda_stocks_to_use`,
`reddit_trending`, `stocks_rsi`, `edgar_insider`) are forward-only today.

**Grain matters more than the raw count for scoping a build.** Splitting the
16 replayable signals by grain:

- **Market grain (8 of 10 replayable)**: `fred_curve`, `fred_hy_spread`,
  `mcal_days_to_opex`, `cboe_vix`, `cboe_vix_backwardation`,
  `cboe_equity_pcr`, `nyfed_rrp`, `tsy_tga`. Each grades against ONE
  benchmark (SP500), i.e. reuses today's template almost verbatim — copy
  table, build an as-of view, reuse the score CASE, join the existing
  `v_replay_returns`/`v_replay_efficacy` shape. (Only `fomc_blackout`/
  `econ_imminent` are forward-only here, and both are non-directional gates
  anyway — excluding them costs nothing directional.)
- **Asset-class grain (4 of 5 replayable)**: `cftc_mm_extreme`,
  `cftc_lev_extreme`, `eia_crude_stocks`, `eia_natgas_storage`. Same
  single-benchmark shape, just graded against a sector-proxy return
  (composite's own `CROSSWALK` table already maps asset_class → tickers).
  Comparable effort to market grain. (`usda_stocks_to_use` is the one
  structural loss here, and it's a hard loss — the PK design destroys
  history, not just a formatting nit.)
- **Ticker grain (4 of 7 replayable)**: `si_days_to_cover`, `si_spike`,
  `sv_ratio_spike`, `ftd_persistent`. Structurally fine data, but grading
  needs a **new per-ticker forward-return spine** (thousands of symbols ×
  dates, not one benchmark) — a materially bigger build than the other two
  grains, closer to the plan's own estimate of "L and possibly blocked" for
  the full scorecard. (`reddit_trending`, `stocks_rsi`, `edgar_insider` are
  the forward-only losses here — half of ticker-grain voting signals.)

**Could any forward-only signal become replayable cheaply?** Optional future
work, not designed here, flagged per the plan:
- `reddit_trending` / `stocks_rsi` / `edgar_insider`: would need to stop
  cascade-pruning (or move to a parallel upsert-keyed history table) —
  ongoing storage growth is the real cost (stocks/etfs alone regenerate a
  full-universe row set daily; `docs/SCHEDULE.md` already notes unpruned
  growth as the reason `--keep-days 30` exists for that source).
- `fomc_blackout` / `econ_imminent`: would need `upsert_events` to write an
  append-only revision log instead of updating in place — a monitor-framework
  change (`sources/common/monitor_common.py`), not source-local; also low
  payoff since both are non-directional gates.
- `usda_stocks_to_use`: would need `wasde_obs`'s PK to include a report/period
  component (e.g. `report_date` or `wasde_report_month`) instead of
  collapsing to one row per `market_year` — a schema change with real
  storage cost (12x rows per market-year line) but would fix the sharpest
  structural gap found in this spike.

## Verdict

**GO, scoped** — build the market-grain + asset-class-grain expansion first
(12 signals, ships in roughly the shape of the existing FRED replay);
treat the ticker-grain expansion (4 signals, new forward-return spine) as a
separate, larger follow-up plan. **NO-GO** on the remaining 6 forward-only
signals without a structural retention change, which is optional future work
and out of scope here.

**Coverage: 16 of 22 (73%) structurally replayable** (3 clean + 13
with-caveat); **12 of 22 (55%) are a near-drop-in extension of today's
template**; the other 4 replayable signals require a materially bigger
per-ticker build; 6 of 22 (27%) stay forward-only pending a structural
retention change nobody should make just for this.
