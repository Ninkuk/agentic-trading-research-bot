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
counts. Shipped 2026-07-07; 9:12pm daily slot between scorer and
daily-summary.)*

### 7. Backtesting foundation

**Problem.** Signals can only be evaluated forward from now. Remaining
blockers (the close-ledger prune was #3, shipped): no OHLC bar history
anywhere (stocks/etfs metrics are latest-snapshot-only), and FRED vintages
are deferred so macro signals can't be replayed without revision look-ahead.

**Done when.** FRED `--vintages` backfilled and scheduled (see
`fred-vintages` deferral note); a decision made and documented on a bar store
(extend the close ledger vs a new OHLC slice); at least one signal replayed
historically end-to-end as proof.

**Size.** L. **Depends on.** — (#1/#3 prerequisites shipped).

### 8. Signal-research backlog (open-ended)

Ideas that need the machinery above before they're worth building:

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
