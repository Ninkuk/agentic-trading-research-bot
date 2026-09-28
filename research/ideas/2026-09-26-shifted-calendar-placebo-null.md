# Circular-shift null for the replay's significance flags

> **Implemented 2026-09-27** (`mcpt.rotation_null`, `replay_rotation_null`,
> `v_replay_efficacy.rot_p`/`rot_n`, run beside the shuffle pass under the
> same `--perms` gate). Sibling table rather than a `method` column: the
> live table predates the change and a new PK would need a migration.
> Per-cell p is exhaustive over that spine's own shifts; the family row
> shares one k across every cell over the shortest graded spine's range.

Source: LosingLoonies, "Using Astrology to Predict Stock Prices" (iKJdaNq9AVQ,
2026-09-26), [00:04:30] — shift the lunar calendar by 1..28 days, run the
identical strategy on every shifted calendar, and read the real calendar
against that distribution; the real one sat mid-pack.

Applied here: hold each benchmark spine FIXED and rotate every cell's
observation rows by k (mod N) for every k, recomputing excess exactly as
`mcpt.py` does. Same method, shift range generalized from the lunar period to
the spine length — not a weakening.

## Landing zone

`backtest` methodology fix — a sibling pass to `mcpt.py`'s shuffle null,
surfaced as a second p column in `v_replay_efficacy`. No new source, no new
job: the existing Sat 7:30am `backtest` slot.

## The defect it fixes

`mcpt.py`'s docstring records both. The whole-series shuffle destroys the
spine's autocorrelation and volatility clustering (an optimistic null for
vol-regime cells), and it treats a flag's clustered observations as that many
draws over near-iid returns: `fred_hy_spread` bearish is 53 obs that are
essentially one 2020 episode, graded as n=53. Rotation preserves both series'
dependence — the 53-day cluster moves whole across the real return history, so
the null asks how often a random 53-day stretch of the real spine beats the
drift. The recorded follow-up was a block shuffle with "block length chosen
after data"; rotation has no block-length parameter to choose.

Live stakes, measured 2026-09-26 from `data/backtest.db`: four cells sit at
`perm_p` < 0.05 (`eia_natgas_storage` bullish 10d 0.027, `fred_dff_chg20`
bullish 21d 0.027, `eia_natgas_storage` bearish 21d 0.043, `nyfed_rrp` bearish
5d 0.048); the family p is 0.335. The `cboe_vix` / `cboe_vix_backwardation`
cells read 0.22–0.90, already dead under the lenient null — the vol-cell motive
has no stakes today, the one-episode motive does.

## Shape

```
replay_null.method   -- 'shuffle' | 'rotate', added to the primary key
                     -- (or a sibling table replay_rotation_null with the
                     --  same (signal_id, direction, horizon, n, p_value) shape)
v_replay_efficacy.rot_p   -- LEFT JOIN, NULL until the pass has run
```

One k per draw applied to EVERY cell at once (as one shuffle serves every cell
today), so cross-cell dependence survives into the family max-statistic. The
drift baseline is identical for every k — returns are untouched — so excess is
hit_rate minus a constant and the "excess, not raw" precaution is automatic.
Rotation is per (signal, benchmark) spine: EIA cells rotate within XLE's rows,
FRED cells within SP500's.

## Measurement plan

- **Null**: exhaustive — every k in 1..N−1, no RNG, no seed;
  p = (1 + #{k : excess_k ≥ real}) / N, the same inclusive convention.
- **Horizon**: the replay's 5/10/21, unchanged.
- **Effective n**: shifts near 0 and near N are near-duplicates of the real
  alignment for persistent flags, which makes p conservative. Report it as is;
  an exclusion radius would be a hand-picked parameter.
- **Threshold**: none. `rot_p` is reported beside `perm_p`; any cutoff is
  chosen after comparing the two, never before.
- **Acceptance**: diff the four `perm_p` < 0.05 cells under `rot_p`. A cell
  that passes both is a lead under two nulls; one that fails `rot_p` is a
  one-episode artifact. Report the rotation family p beside the shuffle's.
- **Cost**: N ≈ 2,569 shifts × ~66 cells over precomputed prefix sums is
  cheaper than the 1,000-shuffle pass it sits beside.

## Caveat that survives

Rotation assumes the joint series is circularly stationary; a secular regime
(2016–21 zero rates against 2022–23 hikes) makes some alignments structurally
implausible, and the wrap-around adds one artificial junction per k. Neither
null is the truth. Disagreement between them is the reading.
