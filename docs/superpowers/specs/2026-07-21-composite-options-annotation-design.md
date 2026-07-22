# Composite reads options.db — Phase 1: annotation only

2026-07-21. Decision delegated to Claude by the user ("make the decision for me").

## Problem

`cboe_options` (registered as `options`, writing `data/options.db`) has run hourly since
2026-07-02 and no combiner consumes any of it. The open question from the last batch's
handoff: does per-ticker options data belong in composite's market regime, the per-ticker
scorecard, or advisor sizing?

## Measured facts the decision rests on

- Composite already consumes market-wide options sentiment (`cboe_equity_pcr`,
  cboe_stats.db, 252-day percentile). At market grain, options.db adds nothing new.
  The new capability is **per-underlying** data.
- Coverage is 24 symbols: 19 mega-caps, SPY/QQQ/IWM, plus SPX and VIX (index products).
- PCR levels are structurally incomparable across the universe (index products 1.3–2.0
  from hedging flow; single names 0.3–0.7). Absolute thresholds would flag the indices.
- `v_iv_rank` has `n_days = 13` (2026-07-21); any percentile-vs-own-history signal is
  meaningless until `n_days >= 60`, ~mid-September 2026 — the same gate
  `.claude/skills/shared/options-read.md` already uses.
- `v_unusual_activity`'s floor (volume >= 100, vol/OI >= 1) currently passes 3,778
  contracts across all 24 names — the `si_spike` fires-on-everything failure mode.
- The book is empty (latest portfolio snapshot has zero positions): an advisor-side
  read would act on nothing today.
- The calibration lesson (memory): thresholds set before real data existed have
  misfired three times in this repo.

## Decision

**Phase 1 (this batch): scorecard annotation, never votes.** Two new ticker-grain
catalog entries in `sources/combiners/composite/catalog.py`, both `score 0`, both added
to `db.INFORMATIONAL_SIGNALS`:

| signal_id     | raw_value               | source view              | budget |
|---------------|-------------------------|--------------------------|--------|
| `options_iv30`| `iv30`                  | `src.v_latest_sentiment` | 4 days |
| `options_pcr` | `put_call_volume_ratio` | `src.v_latest_sentiment` | 4 days |

Both exclude `SPX` and `VIX` (not tradeable tickers; structurally different PCR).
`v_latest_sentiment` is MAX(snapshot_date)-per-underlying — no `calendar_now`
dependency, so the one-clock rule holds. One row per underlying is guaranteed by the
view's construction over PK `(snapshot_date, underlying)`.

Safety is structural, not calibrated: `INFORMATIONAL_SIGNALS` keeps the rows out of
`bullish/bearish/total/coverage` (the `earnings_imminent` precedent — a score-0 row
would otherwise still widen `v_flagged`'s `total >= 2` evidence gate), and scorer and
advisor both filter `score != 0` (verified: `scorer/fetch.py:98`, `advisor/fetch.py:48`).

## Deferred, with reasons

- **Scored signals** (contrarian per-ticker PCR percentile, IV-rank tiers): blocked on
  `n_days >= 60` (~mid-Sept 2026). Percentile-vs-own-history sidesteps the cross-name
  comparability problem; requires the one measured calibration pass the lesson demands.
- **Market-regime addition**: redundant with `cboe_equity_pcr`.
- **`v_unusual_activity`**: needs its own threshold design + calibration; not a signal
  as shipped.
- **Advisor iv30 sizing** (forward vol alongside ATR): revisit when the book holds
  covered names or options trading begins.

## Testing

Mirror the `earnings_imminent` test patterns: catalog-shape assertions, one-clock rule,
`INFORMATIONAL_SIGNALS` membership plus a behavioral no-new-flag test, and a
fixture-DB extraction test (via `sources.screeners.cboe_options.db.ensure_schema`)
asserting one score-0 row per underlying and SPX/VIX exclusion. Smoke-run against real
`data/` into a scratch DB; `v_flagged` must be identical with and without the new
signals.
