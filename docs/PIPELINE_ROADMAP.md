# Signal → Candidate Pipeline Roadmap

Parent tracker for the layer **above** the screeners/monitors: turning per-source
signals into ranked leads, promoting leads to candidates through deterministic
gates, and passing candidates through a bounded LLM gate. The collection layer
underneath is complete — see [SOURCES_ROADMAP.md](SOURCES_ROADMAP.md).

Grounding research: [2026-07-03-signal-to-candidate-pipeline.md](research/2026-07-03-signal-to-candidate-pipeline.md)
(two-pass `/deep-research`; § references below point into it). That doc is a
research synthesis, **not** a spec — each stage here still gets its own design
spec in `docs/superpowers/specs/` before building.

**Source of truth for "Built"** is `registry.py`, same as the screener roadmap —
each pipeline stage ships as a dispatcher (e.g. `main.py leads`, `main.py gate`)
with its own SQLite DB, views, and offline tests. Specs/plans are transient
(`docs/superpowers/specs|plans/`); this file is the durable tracker.

## Status legend

| Status | Meaning |
|---|---|
| ✅ Built | Registered in `registry.py`, tested, in use |
| 📐 Planned | Spec **and** implementation plan written; not yet built |
| 📝 Spec'd | Design spec written; no plan yet |
| 💡 Idea | Researched in the pipeline doc; no spec |

**Evidence** (from the research doc's confidence tiers) — how well-sourced the
stage's design is: 🟢 `[verified]` survived adversarial verification ·
🟡 `[extracted]` sourced but backtest-it ·
🔵 `[prior]` reasoned recommendation, calibrate on own data.

## Architecture (target shape)

```
event-driven jobs (screeners/monitors — BUILT)
        ▼
signal funnel   — rank/composite/tag per-source signals → leads.db
        ▼
promotion gates — liquidity · confluence · correlation caps · regime dial · dedup → candidates
        ▼  (fixed daily window: pre-close, opt. pre-open)
bounded LLM gate — read-only state, reduce-only + τ, clamp in code, decision log
        ▼
execution (Robinhood MCP — out of scope; Claude command layer tracked in CLAUDE_ROADMAP.md)
```

Invariants carried down from the collection layer: stdlib-only, ELT (signals in
SQL views), injected `now_iso` (no wall-clock), no network in tests, secret
hygiene on errors.

---

## Groundwork already in place ✅

The research doc's §2 (per-source signal construction) is largely **already
built** as ELT views in the screener DBs:

| Signal | Where | Note |
|---|---|---|
| COT Index (0–100, 3y min-max) | `cftc_screener/db.py` — `v_cot_index` / `v_disagg_cot_index` / `v_tff_cot_index` + `_latest` + extreme views (≥90/≤10) | ⚠️ keyed on non-commercial / managed-money / leveraged-fund nets; research recommends **commercials** as the default premise group (§2) — resolve in the funnel spec |
| Macro regime flags | `fred_screener/db.py` — `v_regime_signals` | Late-cycle classifier inputs (CPI YoY, UNRATE) are FRED-native |
| Fundamentals cross-section | `sec_fundamentals/db.py` — `v_frame_cross_section`, `v_screener` | Raw ratios only — no z-scored quality composite yet (see Stage 1) |
| Sector/industry/mcap tags | `stock_analysis_screener` data points | Enables sector demeaning (= dummies-only OLS neutralization) in plain SQL |

---

## Stages

### Stage 1 — Signal funnel → ranked leads ✅ 🟢

**Built** as `pipeline/leads/` (registered: `main.py leads`). Spec retired (transient per CLAUDE.md); decisions D1–D6 live in the package's catalog/docstrings.

§1–§2. New package (e.g. `pipeline/leads/`) reading the per-source DBs
read-only, writing a unified `leads.db`. Pure Python + SQL, no network — fully
offline-testable.

Scope for v1 (three legs):
- **COT extremes → ETF leads** — needs the **COT → ETF instrument mapping
  catalog** (ES/NQ → index ETFs, commodity/metal contracts → sector ETFs,
  Treasury COT → duration ETFs). Don't force single-stock COT signals (§2).
  Tag: CS / mean-reversion / weeks-to-months.
- **Quality composite** — QMJ-style z-scored composite over `sec_fundamentals`
  (§2), demeaned per stockanalysis sector (dummies-only neutralization ≡ group
  demeaning — SQL window functions, no numpy). Cross-sectional
  `PERCENT_RANK()` with valid-names-that-day denominator (§1).
  Tag: CS / quality / position-horizon.
- **FRED regime dial** — not a lead: a global exposure **scalar** consumed by
  Stage 2 (§2). Deterministic late-cycle classifier.

Design decisions the spec must pin down: leads.db schema, the
`{type, implementation, horizon_band}` tag vocabulary (§1), the ETF mapping
catalog, commercial-vs-noncommercial COT premise, universe definition.
Deferred: log-market-cap leg of neutralization (add only if backtests show
size leakage).

### Stage 2 — Promotion gates → candidates ✅ 🔵

**Built** as `pipeline/promote/` (registered: `main.py promote`). Spec retired; thresholds live in the frozen GateConfig (config_hash on every snapshot) — calibrate via Stage 6 trials. Spread gate + |ρ| clustering deferred (FOLLOWUPS).

### Stage 3 — Bounded LLM gate ✅ 🟢

**Built** as `pipeline/gate/` (registered: `main.py gate`). Spec retired; τ/heat-cap live in catalog.py, guardrail_config_version pins every decision.

§4, §8 Q2 — best-evidenced stage. **Reduce-only veto gate + confidence
threshold τ** (DOSS pattern): agent may approve, cut size, or veto — never
increase. Fixed output grammar, read-only state store, mask
tickers/identifiers at the DATA layer (prompt-level guardrails provably fail),
clamp in code, `clamp_fired` is a risk alert. Symmetric ±15% band stays a
documented future experiment gated on logged deltas. τ calibration for slow
composite signals is an open empirical question.

### Stage 4 — Decision log & replay ✅ 🟢

**Built** with Stage 3 in `pipeline/gate/` (`gate.db`, trigger-enforced append-only, `--replay`). Spec retired.

§8 Q3. Immutable `gate_decision` row per candidate reaching the gate:
input-snapshot hash, deterministic recommendation, bounds, agent proposal, α,
post-clamp final, delta, `clamp_fired`, `decision_maker`
(deterministic/agent/human — the RTS 24 field that makes "the agent never
overrode the math" provable), hash-pinned model/prompt/guardrail-config.
Append-only event log + checkpoint per decision → deterministic replay.
Builds naturally **with** Stage 3 (same spec or adjacent).

### Stage 5 — Scheduler (two clocks) ✅ 🔵

**Built** as `pipeline/scheduler/` (registered: `main.py schedule`). Spec retired; the cron line lives in `run.py`'s docstring (Linux-only — macOS deployment via launchd is tracked in [DEPLOYMENT_ROADMAP.md](DEPLOYMENT_ROADMAP.md)). Prerequisite treasury `date('now')` fix shipped with this stage.

### Stage 6 — Backtest & validation harness ✅ 🟢

**Built** as `pipeline/trials/` (registered: `main.py trials`) + the fred `observation_vintages`/`v_asof` extension. Spec retired. v1 = trial registry + DSR + walk-forward over accumulated snapshots; retro price simulation still needs a price-history source (FOLLOWUPS).

§7. Trial registry (log every lookback/threshold/weighting tried) + **Deflated
Sharpe Ratio** reporting — non-optional once Stage 2 threshold tuning starts.
Tradability mask at data-load time; ALFRED vintages for revised FRED series
(the `incremental-since-misses-revisions` issue at backtest scale).
Needed **before** trusting any Stage 2 calibration.

---

## Recommended build order

Ranked by dependency × evidence strength (rationale in the 2026-07-04 session
that seeded this file):

1. ~~**Stage 1 — signal funnel.**~~ ✅ shipped. Inputs already exist; everything downstream
   consumes its output shape; forces the ETF-mapping and tag-vocabulary
   decisions that block all later stages.
2. ~~**Stage 5 — scheduler** (anytime, parallel).~~ ✅ shipped. Independent; monitors are built.
3. ~~**Stage 6 — backtest harness.**~~ ✅ shipped. Before Stage 2's thresholds get tuned, so
   every trial is logged from the first one.
4. ~~**Stage 2 — promotion gates.**~~ ✅ shipped. Thresholds calibrated via Stage 6.
5. ~~**Stages 3 + 4 — LLM gate + decision log** (together).~~ ✅ shipped. Consume candidates;
   best-evidenced design, least design risk.

**All six stages are built.** The roadmap is complete; remaining work is calibration (below) + FOLLOWUPS. Post-v1 hardening is tracked in [DEFENSES_ROADMAP.md](DEFENSES_ROADMAP.md).

## Open calibration questions (empirical, not literature gaps)

From §8 — answered by our own backtests, not more research:
1. Numeric liquidity screens ($ADV floor, spread bps, price floor, %-of-ADV cap).
2. τ calibration for a slow COT/FRED/fundamentals composite.
3. Symmetric-band magnitude in trading units (if ever enabled).
4. Cluster-level exposure-cap formula once |ρ|>0.70 pairs are grouped.

## Do-not-cite

Carried from the research doc: the March-2022 recession-probability figures,
any "optimal number of signals", "learned weights beat 1/N", the "SEC RATS
20%-of-ADV regulatory threshold", the "0.925 vs 0.375 Sharpe" tail-capping
figures — all refuted in verification. See the research doc's Do-not-cite
section before quoting numbers into specs.
