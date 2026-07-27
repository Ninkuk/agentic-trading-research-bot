# Universe-relative excess alongside SPY excess

Source: `1F0gYkk7YYw` [00:03:30] — "I've grabbed a bunch of random tickers that
exist today... really what we should do is look at the equal weighting of all
the stocks in my list."

`SALVAGED` from the concept as stated. As stated it *replaces* SPY, which throws
away the investment-relevant comparison `advisor` depends on (a real holding
competes with the index, not with the scanner's universe). The salvaged form
reports both.

## Landing zone

`scorer` methodology fix — `v_signal_efficacy` / `v_bucket_performance` /
`v_signal_recommendation` in `sources/combiners/scorer/db.py`.

## The defect

Ticker outcomes grade against `BENCHMARK = "SPY"` (`scorer/catalog.py:5`) while
composite's ticker layer is a microcap dislocation scanner. The two populations
are not comparable, so `hit = fwd_return > bench_fwd_return` mixes "this signal
picked well" with "microcaps moved differently from large caps this week."

Measured over the matured ledger, P(ticker beats SPY) is 0.4456 at 5d / 0.4027
at 10d, swinging 0.311 → 0.552 across the eight 5d dates.

Not the small-cap tilt: IWM vs SPY over 5,417 5d windows since 2005 gives
p=0.494. The effect is cross-sectional and date-specific.

## Correction: use the MEDIAN, not the mean

An earlier draft of this file claimed an equal-weighted universe benchmark is
"centred at 0.5 by construction." That is true of a **median** and measurably
false of a **mean**, which is what the video's "equal weighting of all the
stocks in my list" literally describes:

| comparator | P(ticker beats it), 5d | 10d | off 0.5 by |
|---|---|---|---|
| SPY | 0.4456 | 0.4027 | 0.054 |
| universe **mean** | 0.5968 | 0.5949 | **0.097** |
| universe **median** | 0.4998 | 0.4997 | 0.0003 |

The cross-section in this sample is left-skewed — a few catastrophic losers pull
the average below the typical stock — so the mean-based comparator is *worse*
centred than SPY, not better. The video's concept as literally stated does not
achieve its own goal. Specify the median.

This is a specification correction, not a second salvage: the salvage (report
both rather than replace SPY) is unchanged and its budget stays spent.

## Shape

```sql
v_universe_return   -- (composite_date, horizon, n_universe, median_fwd_return)
                    --   MEDIAN(fwd_return) over all scanned tickers that date
```

SQLite has no `median()`. Compute it with the row-number/count pattern already
used elsewhere in the repo — `ROW_NUMBER() OVER (PARTITION BY composite_date,
horizon ORDER BY fwd_return)` averaged over `rn IN ((n+1)/2, (n+2)/2)`, which
handles even and odd counts in one expression.

Then add, beside the existing SPY columns, `excess_vs_universe` and
`hit_vs_universe`. Keep both; never merge them. Same split discipline the view
already uses for `via_crosswalk`.

## Relationship to the other two scorer proposals

Three defects, one view, independent fixes — do not conflate:

| proposal | fixes |
|---|---|
| `random-draw-null-distribution` | the null **value** (0.5 is not the base rate) |
| `overlapping-windows-inflate-validation` | the interval **width** (rows are not samples) |
| this one | the **benchmark** (SPY is the wrong comparator for the universe) |

This one and the date-matched null are alternative remedies for the same
measured symptom. With the **median** comparator this is the cleaner of the two
— it lands at 0.4998, so the existing 0.5 null becomes correct rather than
needing a computed replacement. With the mean it is the worse of the two
(0.5968). That distinction is the whole reason the correction above matters.

Either way the date-matched null is still needed for the SPY-relative columns:
those columns stay, and they stay biased.

## Measurement plan

- **Null**: 0.5 for the universe-relative column — correct by construction for
  the median, and measured at 0.4998 (5d) / 0.4997 (10d). Keep this as a
  standing assertion: if pooled `hit_vs_universe` drifts off 0.5 by more than
  sampling error, the universe view is mis-specified (most likely someone
  changed the median back to a mean).
- **Horizon**: 5, 10, 21.
- **Effective n**: 8 distinct `composite_date` at 5d, 3 at 10d, 0 at 21d — and
  see the overlapping-windows proposal, because this column inherits the same
  too-narrow interval until that is fixed.
- **Threshold**: none. No parameter is introduced.
- **Acceptance**: for each signal, report SPY-excess and universe-excess side by
  side. A signal whose edge is entirely the microcap/large-cap spread will show
  positive SPY-excess and ~zero universe-excess. That separation is the
  deliverable.
