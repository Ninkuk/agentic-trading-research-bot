# Deflate the efficacy intervals for overlapping forward windows

**Origin:** `kRa3PUxNBTM` [00:03:01], salvaged. The video's point was about LSTM
*training* windows stepped one day at a time; this repo trains no model but computes
Wilson intervals over daily-stepped 5/10/21-day *forward* windows, which has the
identical defect. Ledger: `non-overlapping-training-windows SALVAGED gate=5:architecture`
→ `-salvaged SURVIVED`.

## The finding is the gap, not the video

`kill-thesis` step 4 already states this rule as a check it runs on a human's thesis:

> **Overlapping windows.** Forward returns sampled daily over 20-day windows are
> ~20x less independent than they look.
> — `.claude/skills/kill-thesis/SKILL.md:90-91`

`backtest`'s `v_replay_efficacy` and `scorer`'s `v_signal_efficacy` both compute
`_wilson()` on the **nominal** row count (`n_bench = COUNT(hit)`;
`backtest/db.py:301-303`, `scorer/db.py:287-289, 316-318`). The repo enforces the
rule on theses and violates it on its own backtest output. That asymmetry is the
finding; the video only supplied the mechanism.

## Landing zone

`scorer` / `backtest` methodology fix. No new screener, no catalog signal, no new
launchd slot — `backtest` already runs Sat 7:30am and `scorer` nightly 9:10pm.

## Shape

Change the interval, never the null. `v_benchmark_baseline`'s measured `p_up`/`p_down`
drift is already correct and is not touched.

- `v_replay_efficacy` (`sources/combiners/backtest/db.py:271-326`) gains `n_eff`
  alongside the existing `n_obs` / `n_days` / `n_bench`. **`n_bench` stays** — a fix
  must not delete the number it corrects.
- `hit_ci_lo` / `hit_ci_hi` recompute from `_wilson()` on `n_eff`.
- `beats_baseline` (`db.py:286-289`) and `reliable` (`db.py:281`) re-decide on the
  deflated interval. `RELIABLE_MIN_N = 30` (`scorer/db.py:35`) then means thirty
  *independent* windows, which is what its name always implied.
- Mirror in `scorer` `v_signal_efficacy` / `v_bucket_performance`
  (`scorer/db.py:267-322`). Ship both together: same defect, and fixing only the side
  currently biting is the fix-the-instance failure.
- The caveat prose at `backtest/db.py:257-270` and `docs/SCHEDULE.md:43` warns about
  drift and about uncorrected multiple comparisons and is silent on overlap. Extend it.

## What it costs today

**Deflate the denominator the interval is actually computed on.** `_wilson()` runs
on `n_bench = COUNT(hit)`, not on `n_obs`, so the correction is
`n_eff = n_bench / max(1, horizon / spacing)` with `spacing = n_days / n_obs`. The
two differ only where some observations have a NULL forward return — one row in six
below (`eia` bearish 21: `n_bench` 327 vs `n_obs` 330) — but deflating `n_obs` would
be correcting a number the shipped view never used.

So corrected, deflation takes `beats_baseline` from **6 to 0** — every
currently-flagged row loses the flag, because the baseline sits outside the shipped
interval and inside the deflated one.

| signal | dir | h | n_obs | n_bench | spacing | n_eff | shipped CI | deflated CI | baseline |
|---|---|---|---|---|---|---|---|---|---|
| fred_hy_spread | bearish | 21 | 53 | 53 | 1.00 | 2.5 | [0.079,0.271] | [0.013,0.710] | 0.314 |
| fred_hy_spread | bearish | 10 | 53 | 53 | 1.00 | 5.3 | [0.120,0.335] | [0.040,0.621] | 0.346 |
| cboe_vix | bearish | 21 | 365 | 365 | 1.00 | 17.4 | [0.185,0.270] | [0.090,0.459] | 0.314 |
| eia_natgas_storage | bullish | 21 | 235 | 235 | 4.75 | 53.1 | [0.562,0.685] | [0.491,0.743] | 0.559 |
| eia_natgas_storage | bullish | 10 | 235 | 235 | 4.75 | 111.5 | [0.558,0.681] | [0.529,0.706] | 0.541 |
| eia_natgas_storage | bearish | 21 | 330 | 327 | 4.87 | 75.8 | [0.457,0.564] | [0.400,0.620] | 0.438 |

Read the first row: `RELIABLE_MIN_N = 30` currently stamps a flag on what is,
independently, about **2.5** windows.

## Measurement plan

**Candidate estimators.** Three, and all three were tried on the live store:

1. *Crude n/horizon deflation* — divide the nominal count by the overlap factor and
   recompute Wilson on the same point estimate. No free parameters at all.
2. *Non-overlapping block subsample* — **the block is `horizon` calendar days, not
   `horizon` observations.** Keep one observation per `horizon`-day block in
   `first_asof` order and recompute the hit rate on that subsample alone. In
   observation units the stride is `k = round(horizon / spacing)`, the same overlap
   factor (1) divides by — striding by `horizon` observations instead would deflate a
   second time on top of the spacing already inside it. On `eia_natgas_storage`,
   spacing 4.87 days, every 21st observation spans ~102 calendar days and k should be
   4, so the as-written form put this estimator ~4.7x away from (1) *by construction*
   and made the cross-check below unpassable. Its point estimate moves too, so it is a
   genuinely different estimator, not the same query re-run. Its one free choice is
   phase, removed by averaging over all `k` offsets.
3. *Block bootstrap* — resample contiguous length-`k` blocks with replacement
   and take the empirical 2.5/97.5 percentiles. Makes no Bernoulli-independence
   assumption at all, and is the only one of the three that survives serial
   correlation *within* a block.

**Adopt (2), the non-overlapping block subsample, and report (1) beside it.** (2) is
expressible as `ROW_NUMBER() OVER (ORDER BY first_asof) % k` with
`k = CAST(ROUND(horizon * n_obs / n_days) AS INTEGER)` — pure SQL over one attached
DB, which is the architecture constraint. (1) is one arithmetic expression and costs
nothing, so it ships as the cross-check: agreement between two estimators is the
verification, not re-running either twice. (3) is rejected here on architecture, not
on merit — resampling with replacement is not a SQL window function, and the repo has
zero runtime dependencies. Revisit it if the two SQL estimators ever disagree.

**Measured 2026-07-26, `data/backtest.db` read-only.** With the corrected stride, (2)
averaged over its `k` phases and (1) agree on all six rows: none is distinguishable
from baseline, and their effective n's now differ by at most 11% (`eia` bullish 21,
58.8 vs 53.1 — the residual is `k`'s rounding to an integer) instead of by 4.7x.

| signal | dir | h | k | (2) p / n_eff / CI | (1) p / n_eff / CI |
|---|---|---|---|---|---|
| fred_hy_spread | bearish | 21 | 21 | 0.135 / 2.5 / [0.010,0.700] | 0.151 / 2.5 / [0.013,0.710] |
| fred_hy_spread | bearish | 10 | 10 | 0.210 / 5.3 / [0.041,0.623] | 0.208 / 5.3 / [0.040,0.621] |
| cboe_vix | bearish | 21 | 21 | 0.226 / 17.4 / [0.091,0.460] | 0.225 / 17.4 / [0.090,0.459] |
| eia_natgas_storage | bullish | 21 | 4 | 0.626 / 58.8 / [0.498,0.738] | 0.626 / 53.1 / [0.491,0.743] |
| eia_natgas_storage | bullish | 10 | 2 | 0.621 / 117.5 / [0.531,0.704] | 0.621 / 111.5 / [0.529,0.706] |
| eia_natgas_storage | bearish | 21 | 4 | 0.511 / 81.8 / [0.404,0.616] | 0.511 / 75.8 / [0.400,0.620] |

**Phase dependence is real, and averaging is what hides it.** Scored per phase rather
than averaged, the flag survives in a minority of phases rather than in none.
Estimator (2) *as originally written* (stride = `horizon` observations) retains the
flag in 2/21, 2/21, 2/10, 0/21, 0/10 and 0/21 phases across the six rows — so "all six
lose the flag" holds on a majority reading, never on every phase. With the corrected
stride: 2/21 (`cboe_vix` 21), 1/4 (`eia` bearish 21), 1/2 (`eia` bullish 10), 0/4, 0/10,
0/21 — and `eia` bullish 10 at `k = 2` is an exact split. Averaging makes the estimator
single-valued; the per-phase spread is the honest error bar around it and belongs in
the implementation's tests, not swept.

- **Null:** unchanged. `v_benchmark_baseline`'s measured `p_up`/`p_down`, never 0.5.
  This proposal touches the interval around the estimate, not the thing it is
  compared to.
- **Horizon:** existing — `HORIZONS = (5, 10, 21)` for `scorer`, `_horizons_union()`
  for `backtest`. Nothing new.
- **Effective n:** the `n_eff` column above, computed per `(signal_id, direction,
  horizon)`, measured against the store's own latest observation and never
  `date('now')`.
- **Threshold sweep:** none, deliberately. The block *is* the horizon in calendar
  days, and the observation stride `k` is that horizon divided by the measured
  spacing — both read off the data, neither tunable — so nothing here is chosen
  before data.
- **Columns that change:** `v_replay_efficacy.{hit_ci_lo, hit_ci_hi, reliable,
  beats_baseline}` plus a new `n_eff`; the same four in `scorer`'s
  `v_signal_efficacy` and `v_bucket_performance`, which feed
  `v_signal_recommendation`'s `keep`/`watch`/`anti-signal` verdict.

## The expected answer is "nothing is distinguishable yet"

**On today's store the corrected view reports zero signals beating baseline. That is
the result, not a failure, and it is not grounds for rejecting the correction.** An
implementation that leaves some flag standing has been built wrong. The whole point
is to stop reporting flags that overlap manufactured — and `backtest/db.py:258-259`
says `reliable` "match[es] the scorer's meaning that the advisor depends on", with
`docs/SCHEDULE.md:64` having the advisor compute 1%-risk-budget size caps off it. An
overstated interval currently feeds sizing.

**Honest caveat on the magnitude.** True effective n lies somewhere between `n/k` and
`n` — observations are not perfectly dependent inside a window, so `n/k` is a floor
and `n` is a ceiling. The precise count therefore depends on the estimator. What is
measured above is that (1) and the corrected (2) agree on direction and on all six
rows losing the flag; neither pins the exact number. A moving-block bootstrap of (3)
run alongside them (5,000 reps, blocks of `k`) does **not** agree — it keeps the flag
on `eia` bullish 10 and on `fred_hy_spread` bearish 21 — which is exactly the
disagreement the adopt-paragraph says would make (3) worth revisiting. Any earlier
claim that all three estimators agree is retracted; two do.

Nothing here is an implementation mandate. The human decides.
