# `reliable` counts overlapping windows as independent samples

Source: `kRa3PUxNBTM` [00:03:01] — sliding a window by one step makes
consecutive samples near-duplicates, so the sample size is a fiction and the
validation set is not a validation set. The video applies it to LSTM training
windows; the same defect is live in this repo's grading.

## Landing zone

`scorer` methodology fix — `RELIABLE_MIN_N` / `v_signal_efficacy` /
`v_signal_recommendation` in `sources/combiners/scorer/db.py`. View + constant
change. `v_replay_efficacy` in `backtest` carries the same shape and should be
fixed with it.

## The defect

`RELIABLE_MIN_N = 30` counts **rows**. Every signal currently flagged
`reliable = 1` rests on 3 or 8 distinct `composite_date`s:

| signal_id | horizon | n_rows | n_dates | reliable |
|---|---|---|---|---|
| si_spike | 10 | 1184 | 3 | 1 |
| stocks_rsi | 10 | 1057 | 3 | 1 |
| si_days_to_cover | 10 | 840 | 3 | 1 |
| si_spike | 5 | 2599 | 8 | 1 |
| reddit_trending | 5 | 49 | 8 | 1 |

At 10d the three dates are 2026-07-06/07/08 — forward windows overlapping by
8–9 of 10 days, i.e. **one** independent time block reported as n=1184. At 5d,
eight consecutive sessions give ~2 non-overlapping blocks.

The Wilson interval is computed on that row count, so it is far too narrow, and
`v_signal_recommendation` turns it into `keep` / `anti-signal`. `advisor`
consumes the flag (`fetch.py:167`, `WHERE reliable = 1`) as a size-cap
annotation.

## Not overstated

Rows are distinct tickers, not pure duplicates, so effective n is not 1 — but
same-date tickers share a market factor, and the measured per-date base rate
swings 0.311 → 0.552 across the eight 5d dates, which is that factor dominating.
Effective n is roughly (non-overlapping blocks) x (cross-sectional breadth well
below the ticker count), not the row count. The overstatement is large; the
exact factor is not the claim.

## Shape

Cluster the statistic by window rather than by row:

```sql
v_signal_efficacy_by_date  -- (signal_id, via_crosswalk, horizon,
                           --  composite_date, n_rows, date_hit_rate)
```

Then compute the interval across **non-overlapping date blocks** (dates spaced
>= horizon trading days apart), with `reliable` gating on the block count, not
the row count. Keep the row count as a separate reported column — it is honest
provenance, just not a sample size.

## Measurement plan

- **Null**: unchanged by this fix (see the date-matched-null proposal, which
  fixes the *value*; this fixes the *width*). The two are independent and both
  land on `v_signal_recommendation`.
- **Horizon**: 5, 10, 21. Block spacing must use the horizon, so the fix is
  per-horizon by construction.
- **Effective n**: at today's ledger, ~2 blocks at 5d, ~1 at 10d, 0 at 21d.
  Every current `reliable = 1` should flip to `insufficient evidence`. That is
  the correct answer, not a regression.
- **Threshold**: `RELIABLE_MIN_N` must be re-chosen for blocks, after data —
  not carried over as 30. Do not reuse the row-count constant.
- **Acceptance**: diff the `recommendation` column before/after. Expect every
  verdict to become `insufficient evidence`. If any signal retains `keep`,
  inspect it — with 8 sessions of history nothing should qualify.

## Why this is not itself a maturity objection

The fix is correct at n=8 and at n=800; it does not wait on data. What waits on
data is any *verdict* — and that is the point: the current view emits confident
verdicts the sample cannot support.
