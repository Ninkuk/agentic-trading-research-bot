# Cboe implied correlation as a market-grain regime input (salvaged)

Source: Patrick Boyle, "Correlation For Traders and Investors" (lYmXOYbKHUI,
2020-06-25), [00:07:33]–[00:08:32]. Parent concept — implied minus realized
S&P 500 constituent correlation predicts future realized correlation — died at
gate 5: the realized leg needs a constituent close panel, and `scorer.prices`
holds ≥63 rows for only 18 spine symbols today (the ledger accrues daily, so
that leg is deferred under `realized-corr-stress-gauge`).

SALVAGED: implied−realized correlation spread → Cboe's published 3-month
implied correlation index (COR3M) as a level/percentile regime signal, same
shape as `cboe_vix`.

Why it is not a VIX duplicate (measured 2026-08-25 from the two Cboe CSVs,
5,178 shared sessions since 2006-01-03): level rho(COR3M, VIX) = 0.549,
20-day-change rho = 0.753, COR3M residual sd after regressing on VIX = 13.7 of
16.4. 160 sessions sit in the video's divergence cell (COR3M ≥ q75, VIX below
median).

## Landing zone

Composite catalog signal, market grain (`entity='*'`), replayed by `backtest`.
Feed: `https://cdn.cboe.com/api/global/us_indices/daily_prices/COR3M_History.csv`
— the same CDN route and `DATE,OPEN,HIGH,LOW,CLOSE` shape as the VIX feeds
`cboe_stats` already parses. Cboe is an admitted primary source. No new job:
one more `Feed(...)` in the existing 6:00pm `cboe-stats` slot.

## Shape

- `cboe_stats.vix_daily` gains a `cor3m REAL` column (ALTER migration — the
  live DB predates it) or a sibling `cor_daily(date, cor1m, cor3m)` table.
- Catalog signal `cboe_implied_corr`: raw_value = COR3M close (or trailing-252
  percentile, as `cboe_equity_pcr` does); score CASE thresholds are chosen
  AFTER the replay sweep, not now.
- `backtest` `MARKET_OBS_SIGNALS` entry, `publication_lag_days: 0` (exchange
  close, same session as VIX).

## Measurement plan

- Null: `v_benchmark_baseline` drift on the SP500 spine plus the seeded
  permutation `perm_p` — never `hit_rate` alone. Read `excess`,
  `beats_baseline`, `anti_signal`.
- Horizons: the replay's 5/10/21 days. ~5,100 sessions available, so effective
  n is the count of non-overlapping 21-day windows (~240), not the row count.
- Sweep: level thresholds over COR3M deciles AND the percentile form; also the
  VIX-conditioned split (COR3M high ∧ VIX below median) — this is the video's
  actual claim and stays a sub-cell of the sweep, never its own signal.
- Prior to beat: `cboe_vix` over the same replay shows no `beats_baseline` at
  any horizon and one `anti_signal` (bearish, 21d). A cousin with 0.55 level
  correlation must clear that bar or it is an annotation, not a vote.
- Promotion rule per CLAUDE.md: a signal enters `INFORMATIONAL_SIGNALS` first;
  voting weight only after a measured calibration pass over non-overlapping
  windows.
