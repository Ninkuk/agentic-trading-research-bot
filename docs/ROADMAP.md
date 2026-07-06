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

## Now — evidence integrity

The scorer's outcome tables are permanent and drive future re-weighting
decisions. Every day these issues stand, contaminated rows accumulate.

*(Item 1, the scorer basis-break guard, shipped 2026-07-06: maturation now
refuses windows containing a split-shaped consecutive-day move on either
leg; `v_basis_breaks` is the audit view. Residuals live in item 8.)*

*(Item 2, next-day entry, shipped 2026-07-06: entries are the first close
strictly after `composite_date`; registration defers until that close
exists, so steady-state registers with a one-night lag. Pre-fix pending
rows are wiped by a one-time migration — nothing had matured.)*

### 3. Permanent close-ledger retention

**Problem.** `PRICE_KEEP_DAYS = 90` prunes the only growing price series in
the system. Daily closes for a few thousand symbols cost megabytes per year;
every pruned day is backtest evidence permanently lost. Cheapest possible
backtesting prerequisite.

**Done when.** Ledger prune removed (or retention made effectively unbounded),
prune docstring updated, disk-growth expectation noted in `SCHEDULE.md`.

**Size.** S. **Depends on.** — (do before or with #1's re-harvest window)

---

## Next — evaluation hardening

### 4. Statistical guardrails on efficacy views

**Problem.** `v_signal_efficacy` / `v_bucket_performance` render a 68 % hit
rate on n = 12 identically to one on n = 200, while ~144 simultaneous
experiments (24 signals × 3 horizons × crosswalk split) guarantee some rows
look brilliant by chance. Separately, crosswalked commodity proxies are graded
as excess *vs SPY* — a mismatched benchmark that flatters commodity signals
whenever equities fall.

**Done when.** Views expose min-n gating (a `reliable` flag or filtered
variant) and a crude binomial confidence interval; crosswalked outcomes are
benchmarked against a matched proxy (e.g. the crosswalk ETF's own asset class)
or explicitly labeled unbenchmarked.

**Size.** M. **Depends on.** #1, #2 (no point hardening views over
contaminated rows).

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

**Size.** L. **Depends on.** #4 (advice should cite reliable efficacy), plus a
volatility input (ATR already in `stocks.db` metrics).

### 7. Backtesting foundation

**Problem.** Signals can only be evaluated forward from now. Three blockers:
close ledger was pruned (#3 fixes), no OHLC bar history anywhere
(stocks/etfs metrics are latest-snapshot-only), and FRED vintages are deferred
so macro signals can't be replayed without revision look-ahead.

**Done when.** FRED `--vintages` backfilled and scheduled (see
`fred-vintages` deferral note); a decision made and documented on a bar store
(extend the close ledger vs a new OHLC slice); at least one signal replayed
historically end-to-end as proof.

**Size.** L. **Depends on.** #3; #1 (adjusted-price semantics must be settled
before history accumulates on top).

### 8. Signal-research backlog (open-ended)

Ideas that need the machinery above before they're worth building:

- **Ticker-grain options signal** — chains are already collected intraday +
  close; nothing derives per-ticker unusual IV / flow. The obvious unused
  input.
- **Regime-conditional efficacy** — `v_signal_efficacy` × `market_regime`:
  does a signal only work risk-on? Needs sample sizes only time (and #3) buys.
- **Weighting the composite** — still a human decision; revisit only when #4's
  guardrails say the efficacy evidence is reliable.
- **Basis-guard enrichment** (residuals from shipped item 1) — cross-check
  quarantined windows against the provider's split-adjusted `ch1w`/`ch1m`
  columns to clear false positives (real crashes beyond −45 %/day) and catch
  sub-threshold splits (3:2, ratio 0.667, passes the guard). Dividend drift
  also remains unhandled (close-only returns understate total return).
