# Score the already-ingested Graham cheapness field as composite's first valuation signal

**Origin:** `oJQqiogr6S0` [00:05:00], salvaged. The concept as stated — buying below
Graham intrinsic value beats the market — died at gate 2 because the field already
ships. The weakened claim is not that cheapness works (the video's own backtest says
it does not, on a harness that fails its own identity check at [00:09:00]) but that
composite scores **no valuation input at all** and already holds the data to measure
one. Ledger: `graham-value-discount-signal SALVAGED gate=2:duplication` →
`-salvaged SURVIVED`.

## The two facts this rests on

Both re-verified against the live store before writing, read-only:

1. **The data is already here.** `data/stocks.db` `metrics.grahamUpside` holds
   **48,746 rows across 2,724 symbols**, ingested by the existing `preopen` 4:00am
   job. Zero new network calls, zero new feed, zero new launchd slot.
2. **There is no valuation signal to duplicate.** `composite/catalog.py` ships
   **26** signals — 10 market-grain, 5 asset-class, 11 ticker-grain — and every one
   is macro, regime, flow, or positioning:
   `fred_curve`, `fred_hy_spread`, `cboe_vix`, `cboe_vix_backwardation`,
   `cboe_equity_pcr`, `fomc_blackout`, `econ_imminent`, `mcal_days_to_opex`,
   `nyfed_rrp`, `tsy_tga`, `cftc_mm_extreme`, `cftc_lev_extreme`,
   `eia_crude_stocks`, `eia_natgas_storage`, `usda_stocks_to_use`,
   `si_days_to_cover`, `si_spike`, `sv_ratio_spike`, `ftd_persistent`,
   `reddit_trending`, `stocks_rsi`, `edgar_insider`, `earnings_imminent`,
   `options_iv30`, `options_pcr`, `portfolio_holding`.
   `grep -rinE "graham|lynchFairValue|intrinsic|valuation|earningsYield|pegRatio"` over
   `sources/ registry.py main.py deploy/`, excluding the screener that ingests it,
   returns one hit — a headless-allowlist entry for `tools.valuation.reverse_dcf`,
   not a scored signal.

   *Correction to the run brief:* it recorded "17 signals" and listed `equity_index`,
   `rates`, `energy`, `metals`, `grain`, `softs`, `ags` among them. Those are
   `CROSSWALK` asset-class keys (`catalog.py:522-530`), not signal ids. The count is
   26; the "no valuation signal" conclusion is unaffected and independently verified.

This would be the first valuation signal in the catalog.

## Landing zone

Composite catalog signal. One `SIGNALS` entry, structurally identical to the shipped
`stocks_rsi`: `"db": "stocks.db"`, `"grain": "ticker"`, returning the
`(entity, raw_value, score, obs_date)` row contract from `composite/catalog.py`'s
module docstring as `(symbol, grahamUpside, <score CASE>, priceDate)` over
`src.v_latest`.

## Shape — and the distribution hazard

`grahamUpside` is a percentage upside with no upper bound: it ranges to **176,586**
in the current store (min −99.8). **An absolute cut is therefore inadmissible** — the
top of the distribution is a penny-stock artifact, not a value opportunity, and it is
exactly the pathology the video flagged at [00:07:01] without diagnosing.

The score must be a **percentile rank of `grahamUpside` within the day's eligible
cross-section**, not a threshold on the raw number. Two guards on top:

- the same `dollarVolume >= 10000000` liquidity filter `stocks_rsi` already uses,
  which on its own leaves **2,496** of the latest cross-section's 5,597 names;
- `grahamUpside IS NOT NULL` — the field is populated for **2,705** of those
  5,597, so a `LEFT JOIN` yielding NULL is the normal case for the rest.

The two together leave **1,783** eligible names. Each count is that filter alone
against `stocks.db` `v_latest`; the 1,783 belongs to the conjunction and to
neither bullet.

`raw_value` stays the raw `grahamUpside` so the un-ranked number remains readable in
`signal_scores`.

## Measurement plan

- **Null:** scorer's existing benchmark-relative one. `hit = fwd_return >
  bench_fwd_return` (`scorer/db.py:306-308`), so 0.5 is the correct null and no
  base-rate correction applies. The named benchmark-relative trap is checked, not
  assumed.
- **Horizon:** 5d and 10d from `HORIZONS = (5, 10, 21)`. Read
  `avg_directional_excess`, never `hit_rate` alone, and require the result to hold on
  both horizons before reading anything into either.
- **Effective n:** far below nominal. Forward windows overlap and a cross-section of
  cheap names is sector-clustered, so nominal `n_bench` overstates independence — see
  the sibling proposal `2026-07-26-overlapping-window-effective-n.md`, which is the
  general form of this same objection. Gate on `reliable`
  (`n_bench >= RELIABLE_MIN_N`, 30) as a floor only, never as a verdict.
- **Thresholds: a measured recalibration pass before any threshold is chosen.**
  Ship the signal emitting `raw_value` with a provisional flat score, accumulate at
  least one quarter of matured `signal_outcomes`, sweep the percentile cut against
  that, and only then write the score `CASE`. `CLAUDE.md` records that every new
  catalog signal needs one measured recalibration pass and that pre-data thresholds
  have misfired three times. This proposal chooses no cut.
- **Known limitation:** `backtest` cannot replay this. There are no point-in-time
  vintages for stockanalysis.com fundamentals, and `stocks.db` metrics are
  snapshot-scoped at `--keep-days 30` (`docs/SCHEDULE.md:26`), so no history exists to
  replay against. It is **scorer-gradable, forward-only**, and the first readable
  result is months out. Retaining a longer daily valuation cross-section would be a
  separate decision, not part of this proposal.

Nothing here is an implementation mandate. The human decides.
