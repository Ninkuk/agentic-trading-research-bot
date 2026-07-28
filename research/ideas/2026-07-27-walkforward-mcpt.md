# Permutation null for the replay's significance flags

Source: `NLBXgSmRBgU` [00:17:02]–[00:19:01] — permute the data after the first
training fold, re-run the walk-forward, and read the real statistic against the
permuted distribution. Applied here with flags held fixed and the outcome series
permuted: the repo's replay has no optimizer to re-fit, so the two nulls
coincide. That is an application to this architecture, not a weakening — the
test's content (real walk-forward statistic vs its distribution under permuted
data) is intact.

## Landing zone

`backtest` methodology fix — the significance machinery in
`sources/combiners/backtest/db.py` (`v_replay_efficacy`'s
`beats_baseline`/`anti_signal`) plus a resampling pass in `run.py`.

## The defect it fixes

Two, both already documented in `v_replay_efficacy`'s own docstring:

- The Wilson interval treats overlapping forward windows as independent, so it
  is too narrow (same defect the 2026-07-26 overlapping-windows proposal targets
  on the scorer side).
- The ~48 graded cells carry nominal, uncorrected 95% flags — ≈2 expected by
  chance; measured 2026-07-09, only ~7 of 11 flags survived Bonferroni.

A permutation null prices both in at once: each permuted series carries the same
overlap structure as the real one, and a family-wide max-statistic across cells
(Masters' multiplicity answer) gives one corrected p.

## Shape

```
replay_null   -- (signal_id, direction, horizon, n_perms, p_value)  per cell
              -- plus one family row: max-statistic p across all cells
```

Written by a permutation pass: shuffle each benchmark spine's daily log returns
(whole-series; preserves the return multiset, hence total drift — the current
`v_benchmark_baseline` null falls out automatically), rebuild permuted forward
returns, recompute each cell's hit_rate exactly as `v_replay_efficacy` does
(same one-row-per-observation dedupe). p = (1 + #{permutations with hit_rate ≥
real}) / (1 + n_perms) — the inclusive convention from the source
implementation (`mcpt/insample_donchian_mcpt.py` seeds `perm_better_count = 1`),
which counts the real sample as its own permutation and can never report p = 0.
Bearish cells flip the inequality. `v_replay_efficacy` LEFT JOINs it.

Stdlib-only (`random.Random(seed)` with the seed injected through `run(...)`,
never wall-clock — determinism invariant). Weekly Saturday job; 1,000 perms ×
~48 cells over a few-thousand-row spine is pure-Python minutes, acceptable at
that cadence.

## Measurement plan

- **Null**: the permutation distribution itself — per cell, plus the
  max-statistic family p. Nothing analytic to mis-assume.
- **Horizon**: the replay's existing horizons, unchanged.
- **Effective n**: per-cell `n_obs` as shipped (deduped observations; the replay
  spans years, e.g. fred_hy_spread n=53, so this is computable today — not
  maturity-gated).
- **Threshold**: report raw p; any accept/reject cutoff chosen after comparing
  against the current flags, never before.
- **Acceptance**: diff permutation-p verdicts against current
  `beats_baseline`/`anti_signal` per cell. Cells that flip measure the
  overlap-induced interval bias directly.

## Caveat that survives

Shuffling daily returns destroys the benchmark's autocorrelation and volatility
clustering ([00:09:31]), so cells whose flags key on vol regimes (`cboe_vix`,
`cboe_vix_backwardation`) get an optimistically biased null. The video's own
reading applies: a cell that fails even an optimistic null is dead; a cell that
passes one is a lead. A block-shuffle robustness variant is the follow-up if
those cells pass, block length chosen after data.
