# Score the policy rate's direction of travel, not its level

Source: `t2f0vyfABdM` [00:06:31] — "the level of the interest rates matters way
less than what they're actually doing." The video proposes three views: 1-day
change, 20-day change, and a binary hiking flag.

`SALVAGED` from the concept as stated. The 1-day change is dropped: DFF's mean
absolute 1-day move is 0.0112 at month-turns vs 0.0036 mid-month (n=750/3471,
2015+), i.e. 3.1x larger — repo-market window-dressing, not policy. Two views
survive: the 20-day change and the hiking/cutting regime binary.

## Landing zone

New composite catalog signal(s) + the matching `backtest` replay entries.
No new fetcher, no new source, no new schedule slot.

## The gap

`DFF` (effective fed funds) is fetched and stored — **26,321 daily observations
back to 1954-07-01**, the deepest series in the store — and appears **zero
times** in `sources/combiners/composite/catalog.py` and
`sources/combiners/backtest/catalog.py`. Composite scores exactly two FRED
series, both as levels:

| signal | series | shape |
|---|---|---|
| `fred_curve` | T10Y2Y | level (`value < 0`) |
| `fred_hy_spread` | BAMLH0A0HYM2 | level bands |

(`WCESTUS1` in the catalog is an EIA crude-stocks series, not a Fed one.)

The repo already has the change idiom elsewhere — `nyfed_rrp` scores
`change_vs_prior`, `tsy_tga` scores `wow_change` — so this is an inconsistency
in coverage, not a new pattern.

## Shape

Two hoisted score constants beside the existing `FRED_CURVE_SCORE` /
`FRED_HY_SPREAD_SCORE`, so the backtest replays the identical expression and the
flags cannot drift between composite and the replay (the invariant those
constants exist to protect):

```python
FRED_DFF_20D_CHANGE_SCORE = "CASE WHEN ... END"   # direction of travel
FRED_DFF_REGIME_SCORE     = "CASE WHEN ... END"   # hiking / cutting / neutral
```

Both are market-grain (`entity = '*'`), SQL over `fred.db observations` with a
self-join for the 20-day lag. DFF has ALFRED vintages, so it enters the replay
through the existing vintage path with `publication_lag_days = 1` (H.15 posts
next business day).

## Measurement plan

- **Null**: `v_benchmark_baseline` in `backtest` — benchmark drift, already
  built. Read `excess` / `beats_baseline`, never `hit_rate`.
- **Horizon**: the replay's existing horizon set.
- **Effective n**: **count rate cycles, not days.** The replay window is
  SPY-era (1993+), which holds roughly 8 independent hiking/cutting episodes.
  A 20-day change on consecutive sessions is ~95% overlapping, so the row count
  will badly overstate the sample — this signal is a worked example of the
  defect in the `overlapping-windows-inflate-validation` proposal, and should
  not be promoted until that fix lands.
- **Threshold**: sweep after data. Do not pick basis-point cutoffs up front —
  CLAUDE.md records three misfires from pre-data thresholds.
- **Multiplicity cost**: `v_replay_efficacy` already emits ~48 graded rows with
  ~2 expected to flag by chance. Two more signals push that toward ~58. State
  the corrected test, not just the nominal flag.
- **Promotion rule**: ship at score 0 (`INFORMATIONAL_SIGNALS`) first, exactly
  as `sa_fscore` / `sa_fcf_yield` were, and promote to voting only after a
  measured calibration pass over non-overlapping windows.

## Honest caveat

The video's own experiment found that adding rates made its model *worse*
(CAGR 29% -> 24%). That is evidence about its model, which by its own account
learns nothing from any input — not evidence about the signal. This proposal
rests on the repo's coverage gap and DFF's 72-year history, not on the video's
result.
