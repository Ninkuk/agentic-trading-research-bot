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

### 5. Decision journal

**Problem.** The scorer grades opinions; nothing records actions. Without
"composite said X on date D, human acted/passed, filled at P" there is no way
to measure the paper-vs-realized gap or whether the human filter adds value.
Robinhood MCP trade history can backfill fills via the same headless path the
portfolio slice uses.

**Done when.** A journal table keyed to composite opinions records
acted/passed and fill price; a view joins it to matured outcomes to show
realized-vs-paper per signal; entry is low-friction (a dispatcher fed by the
existing MCP skill pattern).

**Size.** M. **Depends on.** #2 (paper baseline must be honest first).

---

## Later — new layers

### 6. Sizing / risk advisor combiner

**Problem.** Nothing joins the scorecard against actual holdings.
`portfolio.db`'s docstring already promises the consumers ("real exposure,
whole-book heat") that don't exist. This is decision *support*, not order
generation — consistent with the human-execution design.

**Done when.** A combiner (or composite extension) reports: current book heat
(vol-scaled exposure per position and total), holdings today's composite
disagrees with, and a vol-scaled size cap for any newly flagged ticker.
CROSSWALK groups count as one bet for heat purposes.

**Size.** L. **Depends on.** #4 (shipped 2026-07-06 — advice should cite
`reliable` efficacy rows), plus a volatility input (ATR already in
`stocks.db` metrics).

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
