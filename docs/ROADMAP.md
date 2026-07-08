# Roadmap

Prioritized work queue derived from a gap analysis of the pipeline against the
standard algorithmic-trading stack (data → signals → combination → sizing →
risk → execution → evaluation). This file is the durable backlog: when an item
is picked up it graduates into the normal spec → plan → build workflow
(`docs/superpowers/specs/`, `docs/superpowers/plans/`), and its entry here is
pruned once it ships. Tiers are priority, not a schedule.

Context for the tiering: the repo deliberately has no automated execution and
no automated re-weighting — the human is the execution and weighting layer.
Those are design choices, not gaps. What the tiers below protect, in order, is
(1) the integrity of the evidence the human reads, (2) the quality of the
views that present it, (3) new decision-support layers on top.

Each item: **problem → done when → size (S/M/L) → dependencies**.

---

## Now — evidence integrity (ALL SHIPPED 2026-07-06)

*(Item 1, basis-break guard: maturation refuses windows containing a
split-shaped consecutive-day move on either leg; `v_basis_breaks` is the
audit view. Residuals live in item 8.)*

*(Item 2, next-day entry: entries are the first close strictly after
`composite_date`; registration defers until that close exists, so
steady-state registers with a one-night lag. Pre-fix pending rows were
wiped by a one-time migration — nothing had matured.)*

*(Item 3, permanent close ledger: the prices prune and `PRICE_KEEP_DAYS`
removed; the ledger is append-only forever — the future backtest store.)*

---

## Next — evaluation hardening

*(Item 4, statistical guardrails: `v_signal_efficacy` / `v_bucket_performance`
expose `n_bench`, a Wilson 95% CI on hit_rate, and a `reliable` flag
(n_bench >= 30); crosswalked outcomes grade against matched class benchmarks
(CROSSWALK_BENCHMARK), class proxies explicitly unbenchmarked. Shipped
2026-07-06. Residual: ticker-grain buckets stay SPY-benchmarked — see
item 8.)*

*(Item 5, decision journal: `decisions` in scorer.db keyed to composite
opinions — fills auto-matched from Robinhood order history (headless
2:40pm `/journal-sync` slot), passes inferred in `v_flag_response` with
explicit override; `v_decision_outcomes` (slippage, realized-vs-paper),
`v_human_filter` (acted vs passed). Shipped 2026-07-06; slot installed and
first interactive sync run 2026-07-07 — field mappings verified against
live orders (`average_price`, not `price`; execution timestamp). Policy
set that run: `placed_agent` drip/recurring fills are journaled but
labeled — never matched to an opinion, never exit-attached (nobody's
decision; visible in `v_freelance` via the `placed_agent` column).
Day-one caveat: fills predating the composite's first opinion correctly
record as freelance, so the earliest rows carry no paper baseline.)*

---

## Later — new layers

*(Item 6, sizing/risk advisor: `advisor` combiner joins the composite
scorecard against real holdings — `v_book_heat`/`v_group_heat` (ATR heat,
crosswalk groups count as one bet), `v_disagreements`, and 1%-risk-budget
size caps in `v_latest_caps`, annotated with scorer `reliable` signal
counts. Caps are fractional (`cap_shares REAL` — whole-share flooring
zeroes every cap at small equity) and scale with equity each night;
bearish flags carry NULL caps (long-only book — the row is the advice).
Shipped 2026-07-07; 9:12pm daily slot installed same day, first live run
verified against the real book (2 positions, heat 0.21 % of equity,
coverage 1.0, XOM weak disagreement, zero caps — nothing flagged).
Residuals live in item 8.)*

*(Item 7, backtesting foundation: the `backtest` combiner replays composite's
two FRED regime signals point-in-time over ~10y and grades them against
forward SP500 returns — `v_pit_signal` (value-as-known-on-D via ALFRED
vintages), `v_replay_flags` (composite's exact hoisted score CASEs),
`v_replay_returns` (entry strictly after D, 5/10/21d), `v_replay_efficacy`
(Wilson-CI hit rates mirroring scorer). FRED `--vintages` backfilled +
scheduled weekly (`fred-vintages` Sat 7am); backfilling exposed and fixed
three live FRED caps the offline-tested fetcher never hit — the >2000
vintage-dates 400 (windowed realtime tiling), the 100k-row truncation (offset
pagination), and ALFRED-absent series (benchmark skip). Proof (2026-07-07,
real data): both signals grade — `fred_hy_spread` bullish 0.61/0.63/0.70 hit
@5/10/21d (n~580, reliable, CI clears 0.5 — the real edge); `fred_curve`
bearish 0.39/0.36/0.33 (n=546, reliable — an inverted 2s10s was not a
short-term SP500 short over 2016–2026). Bar store: decided **NOT** built —
ticker bar history becomes a dedicated `bars` slice (see item 8); the close
ledger stays evidence-only. Shipped 2026-07-07. Residuals in item 8.)*

### 8. Signal-research backlog (open-ended)

Ideas that need the machinery above before they're worth building:

- **Bar-store build (`bars` slice)** (deferred from shipped item 7) — the
  backtest replays only market-grain FRED signals because ticker-grain signals
  have no historical inputs: stocks/etfs metrics are 30-day snapshot-scoped and
  the close ledger is close-only. A dedicated OHLCV screener (its own DB, four
  files, live-verified fetch) unlocks ticker-grain replay when needed; the close
  ledger stays evidence-only (provenance). Decision + rejected-alternative
  rationale: `docs/superpowers/specs/2026-07-07-backtesting-foundation-design.md`
  § 4.
- **Ticker-grain options signal** — chains are already collected intraday +
  close; nothing derives per-ticker unusual IV / flow. The obvious unused
  input.
- **Regime-conditional efficacy** — `v_signal_efficacy` × `market_regime`:
  does a signal only work risk-on? Needs sample sizes only time (and #3) buys.
- **Weighting the composite** — still a human decision; revisit only when the
  efficacy guardrails (shipped 2026-07-06) say the evidence is
  reliable (`reliable` = 1 and the Wilson CI clears 0.5).
- **Basis-guard enrichment** (residuals from shipped item 1) — cross-check
  quarantined windows against the provider's split-adjusted `ch1w`/`ch1m`
  columns to clear false positives (real crashes beyond −45 %/day) and catch
  sub-threshold splits (3:2, ratio 0.667, passes the guard). Dividend drift
  also remains unhandled (close-only returns understate total return).
- **Matched benchmarks at ticker grain** (residual from shipped item 4) —
  `ticker_outcomes` buckets grade vs SPY even for tickers whose score is
  dominated by crosswalked commodity votes; per-ticker benchmark needs
  crosswalk provenance on ticker_scores first.
- **Advisor enrichment** (residuals from shipped item 6) — deliberate
  scope cuts to revisit once the views prove useful. *(Digest fold SHIPPED
  2026-07-07: advisor book heat / disagreements / size caps now render as a
  plain-text `— advisor —` block in the 9:15pm daily-summary ntfy push —
  `advisor_digest()` in `deploy/launchd/daily_summary.py`, mirroring
  `signals_digest`; staleness note uses local Phoenix dates; NULL
  `cap_shares` on bearish-flag nights guarded so the digest can't crash.)*
  Still open: correlation beyond crosswalk groups (QQQ + NVDA count as
  separate bets today — only CROSSWALK siblings collapse); same-night
  sibling caps each see the full remaining group budget (alternatives, not a
  shopping list — a shared-budget view would close that); options positions
  are invisible to book heat (portfolio.db is equities-only).
- **VIXEQ dispersion/correlation signal** — `cboe_stats` already carries
  VIX/VIX3M/VIX9D/VVIX and derives `v_vix_term_structure`; adding CBOE's
  VIXEQ (market-cap-weighted single-name implied vol) would let a new view
  compute the VIX/VIXEQ spread as an implied-correlation proxy — a regime
  axis term structure can't see (single-name-driven vol vs systemic vol).
  Cheap to fetch (same source, same catalog pattern). Hold until #7 ships:
  backtest the spread's forward-return efficacy via `v_replay_efficacy`
  before wiring it into `composite` — same lesson as composite's first
  calibration pass, don't add scorer weight on vibes.
- **Mine TradingView for signal ideas** — two corpora:
  scripts (<https://www.tradingview.com/scripts/>, published Pine Script
  indicators/strategies) and ideas (<https://www.tradingview.com/ideas/>,
  discretionary trade write-ups / analysis). Research-only: harvest the
  *idea* (what input, what transform, what threshold) and reimplement over
  our own official-source data + SQL views, never depend on TradingView as a
  feed (it fails the official-primary-source policy). Filter hard for signals
  we can actually source (macro/positioning/flow from FRED/CFTC/FINRA/CBOE,
  not chart-pattern TA on price we don't store); anything kept still passes
  through #7 backtesting before earning composite weight.
