# Date-matched empirical null for scorer verdicts

Source: `aiFpAl3mgGk` [00:07:01] — judge a picker against the distribution of
random single-stock draws, not against a benchmark line.

## Landing zone

`scorer` methodology fix — `v_signal_recommendation` in
`sources/combiners/scorer/db.py`. View change only; no new source, no new
launchd job, no new data.

## The defect

`v_signal_recommendation` splits on a hardcoded `0.5`: CI wholly above → `keep`,
wholly below → `anti-signal`. The comment calls 0.5 "a coin flip". Measured over
the matured ledger, the coin is not fair and its bias moves by date:

| horizon | n_rows | n_dates | P(ticker beats SPY) |
|---|---|---|---|
| 5 | 7203 | 8 | 0.4456 |
| 10 | 3402 | 3 | 0.4027 |

Per composite_date at 5d the rate spans 0.311 (2026-07-06) → 0.552 (2026-07-15).
A signal firing only on early-July dates is graded against a null that was ~0.31
in reality; at 0.5 it is labelled `anti-signal` for matching its own base rate.

Not the small-cap tilt: IWM vs SPY over 5,417 5d windows since 2005 gives
p=0.494 (10d: 0.5042). The index-level tilt is a coin flip. The effect is
cross-sectional and date-clustered, which is what makes a date-matched null the
right instrument rather than a corrected constant.

## Shape

A view over `ticker_outcomes` giving the per-(composite_date, horizon)
cross-sectional base rate, and a second aggregating it to the exact date set on
which each signal fired:

```sql
v_date_base_rate     -- (composite_date, horizon, n_universe, p_beat)
v_signal_null        -- (signal_id, via_crosswalk, horizon, expected_p)
                     --   n-weighted mean of p_beat over the dates that signal fired
```

`v_signal_recommendation` then compares the Wilson interval to `expected_p`
instead of `0.5`. Same four states, same ordering.

Universe: 694–1490 tickers per date already in `ticker_outcomes`, both
directions — a wide enough cross-section, and it is the correct conditioning set
(the population picks are drawn from). `bench_fwd_return IS NOT NULL` only.

## Measurement plan

- **Null**: `expected_p`, the date-matched cross-sectional P(beat SPY), not 0.5.
- **Horizon**: 5, 10, 21 (`scorer.catalog.HORIZONS`) — unchanged.
- **Effective n**: 8 distinct `composite_date` at 5d, 3 at 10d, 0 at 21d. Quote
  dates, never rows; 7203 rows is one overlapping fortnight.
- **Threshold**: none to sweep — the null is computed, not chosen. That is the
  point: a date-matched null is correct at n=8 and at n=800, so this does not
  wait on maturity.
- **Acceptance**: re-run `v_signal_recommendation` under both nulls and diff the
  verdict column. Report how many signals change state and in which direction.
  If nothing changes, the fix is correct and inert — ship it anyway, because the
  bias grows with any date set whose base rate is not 0.5.
- **Backtest parity**: `v_replay_efficacy` already compares against an empirical
  `v_benchmark_baseline` rather than 0.5. This closes the gap between the two
  combiners; check the two baselines are not silently different nulls
  (benchmark drift vs cross-sectional beat rate — they are not the same thing,
  and both may be warranted).

## Caveat that survives

The 0.4456 figure itself rests on 8 clustered dates and is not a stable estimate
of anything. It motivates the fix; it is not evidence for a corrected constant.
Do not hardcode 0.4456.
