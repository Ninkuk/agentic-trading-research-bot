# Research: Screeners → Leads → Trading Candidates

**Type:** Research synthesis (not a spec). Design decisions belong in `docs/superpowers/specs/`.
**Date:** 2026-07-03
**Method:** `/deep-research` workflow, two passes.
Pass 1 (architecture) — 106 agents, 24 sources, 116 claims, top 25 verified: **24 confirmed, 1 refuted**.
Pass 2 (focused follow-up on the open questions, see §8) — 108 agents, 25 sources, 103 claims,
top 25 verified: **20 confirmed, 5 refuted**.
**Scope fixed at intake:** horizon-agnostic (signal type dictates holding period), **equities/ETFs
only**, LLM as a bounded final gate. Pass 2's evidence upgraded the gate design from "approve + tune"
to a **reduce-only veto gate** (see §8, Q2). Execution via Robinhood MCP is out of scope.

> **Confidence tiers used below:** `[verified]` survived adversarial verification ·
> `[extracted]` pulled from a source but not in the verified top-25 (standard, but treat as
> "backtest it" not "cited law") · `[prior]` reasoned recommendation where the corpus had no
> verified evidence — labeled honestly rather than fabricated.

---

## Headline verdict

The intended architecture is the one the evidence endorses. The strongest, best-corroborated
finding is *negative*: under leakage-controlled evaluation, LLM trading agents produce
**little-to-no genuine stock-selection alpha** — their apparent skill is memorized tickers and
passive factor exposure, not reasoning. That is the affirmative case for keeping the math in
deterministic Python and confining the LLM to a clamped, auditable gate. `[verified]`

One model recommended a real ticker but refused to trade in **25/25** cells when shown the
identical numbers with the ticker anonymized — pattern-matching memory, not data analysis.
`[verified]`

---

## 1. The signal funnel — raw monitor data → ranked lead list

Canonical quant funnel is **neutralize → rank → composite**, done cross-sectionally per date. `[verified]`

1. **Neutralize** each raw factor via per-date OLS residualization against industry dummies and
   (optionally) log market-cap: `F̃ₜ = (I − Xₜ(XₜᵀXₜ)⁻¹Xₜᵀ)Fₜ`. Regress raw factor on
   industry/size, keep the residual → strips "fired only because it's a small-cap energy name."
2. **Cross-sectional percentile rank**, denominator = count of *valid (non-missing)* names that
   day, so ranks are comparable across days as the universe drifts.
3. **Z-scored composite** for multi-dimension signals (see §2 quality composite).

**Route by signal TYPE, not habit:** `[verified]`

| Signal type | Implementation | Why |
|---|---|---|
| Value / mean-reversion / positioning extremes | **Cross-sectional** | Value works CS; ranking nets out the market factor |
| Momentum / trend | **Time-series** | Momentum works best TS |
| Carry | Either | Works in both |

Algebra behind "CS hedges the market": **cross-sectional weight = time-series weight − cross-sectional
mean.** Subtracting the mean → dollar-neutral, market-hedged for free.

**Horizon tagging:** signal *type* implies both implementation *and* natural horizon. Tag each
signal `{type, implementation, horizon_band}` at construction; that tag routes the candidate.
COT positioning extreme → CS/mean-reversion → weeks-to-months. Fundamentals-quality rank → CS →
position horizon.

---

## 2. Source-specific signal construction (the actual data sources)

### CFTC COT → COT Index `[verified]`
```
COT_Index = (Current_Net − Min_Net_3y) / (Max_Net_3y − Min_Net_3y) × 100
```
- 0–100 min-max oscillator, **3-year (156-week)** lookback. 100 = most bullish in 3y, 0 = most bearish.
- **Commercials are the default underlying** group (rallies/declines typically caused by commercial
  buy/sell — the "smart money" convention). Disaggregated/TFF gives cleaner producer/merchant vs.
  managed-money splits than legacy — use producer/commercial as premise, managed-money as confirm/divergence.
- **The index is a normalizer/extreme-detector, NOT a trigger** (source's own caveat). One input
  into the composite, gated by confirmation (§3).
- For equities/ETFs: maps most directly onto **ETFs with a futures analog** (index ETFs via ES/NQ,
  commodity/sector ETFs via underlying, rate-sensitive ETFs via Treasury COT). Don't force a
  single-stock COT signal that doesn't exist.

### FRED → regime / risk-on-risk-off classifier `[verified]`
- **Elevated inflation + low unemployment has historically preceded U.S. recessions** — late-cycle
  imbalance. CPI and UNRATE are FRED-native → deterministic classifier:
  `regime = late_cycle if (CPI_yoy > thr AND UNRATE < thr)`.
- Macro variables are **stronger recession predictors than financial variables beyond four quarters**
  — fits position-horizon signals, less so swing timing.
- Use FRED regime as a **risk-appetite dial that scales exposure**, not a precise probability model.
- **⚠️ DO NOT CITE** the specific "March 2022 ~5% vs ~50% recession probability" figures — **refuted
  0–3**. Only the qualitative directional relationship survived.

### Fundamentals/earnings → z-scored quality composite `[verified]`
```
Quality = Z( Profitability + Growth + Payout + Safety )
```
QMJ-style: z-score each proxy cross-sectionally within dimension, sum into dimension scores,
z-score the composite. This is the pattern to replicate for stockanalysis.com fundamentals.

---

## 3. Lead → candidate promotion gates

**⚠️ Weakest-sourced section — structure well-supported, thresholds are `[prior]`/`[extracted]` defaults to backtest, not cited law.**

- **Liquidity** — min ADV / dollar-volume, max spread, price floor (drop sub-$5 / illiquid). A signal
  you can't fill at size is not a candidate.
- **Confirmation / confluence** — require ≥N independent signals agree, or require an extreme (COT at
  0/100) be confirmed by a second leg (price/trend or fundamental rank) before promotion.
- **Correlation / exposure caps** — check candidate correlation to existing book; cap sector/factor
  exposure so five "independent" signals aren't secretly one bet (§5).
- **Regime filter** — gate/scale candidates by the FRED regime dial.
- **Cross-signal dedup** — same name from COT + quality + momentum → **one** sized candidate.

Output: small candidate list, each carrying
`{deterministic_score, horizon_band, computed_size, stop, guardrail_bounds}`.

---

## 4. The bounded LLM gate (best-cited section)

**Endorsed I/O contract:** `[verified]`
1. **Deterministic State Store is READ-ONLY to the LLM.** Environment updates it; agent only reads.
2. **Output is a typed tuple:** `(candidate_action, confidence α∈[0,1], validity_check)` where the
   check is a hard predicate like `holds < max_leverage`.
3. **Admit only above a deterministic threshold:** `if ConfidenceScore(α) > X: include`.
4. **Constrain to a fixed grammar** — agent emits
   `{approve|reject, size_mult∈[lo,hi], limit_offset∈[lo,hi], rationale}`; nothing else parses.

**Clamp/validate/log pattern (the "tune within guardrails"):**
```
1. Python emits: recommended_size, recommended_limit, bounds=(size_lo,size_hi,limit_lo,limit_hi)
2. LLM proposes: tuned_size, tuned_limit, approve/reject, rationale
3. Python CLAMPS:  final_size = clamp(tuned_size, size_lo, size_hi)     # agent CANNOT escape
4. Python LOGS:    delta = final_size − recommended_size, rationale, clamp_fired flag
5. "clamp fired" is itself a risk flag worth alerting on
```

**Clamp must be code, not prompt:** `[verified]` prompt-level "do not exceed X" / "don't use
memorized knowledge" **provably fail** — the model treats them as suggestions. Every guardrail must
be deterministic code the LLM cannot override, and **leakage control belongs at the DATA layer**
(mask identifiers/dates fed to the agent) — telling it "pretend you don't know" doesn't work.

**Stricter default than symmetric ±X% — consider reduce-only for v1:** `[prior]` since the LLM's
discretionary alpha is near-zero-to-negative `[verified]`, let it *cut* size or veto but not
*increase* beyond the deterministic recommendation. Express caution (qualitative news read can dodge
a landmine) without expressing conviction (evidence says it has none). Widen later only if logged
deltas show up-tunes added value.

**Optional hardening — selective consensus (TrustTrade):** `[verified, medium]` run the gate through
N independent agent calls, weight by agreement, log disagreement as a risk flag. Post-v1.

**Sobering context:** `[verified]` audit of 19 LLM-trading studies — only 2/19 report time-consistent
splits, 1/19 models costs, 1/19 documents survivorship, 0/19 reach top reproducibility tier. The
deterministic discipline here is the thing almost nobody does.

---

## 5. Position sizing & risk math

**⚠️ Formulas below are `[extracted]` — standard, mutually consistent across six sources, trivially
checkable, but NOT in the verified top-25. Backtest them; don't treat as adversarially confirmed.**

Core identity (size is a function of stop distance):
```
shares       = risk_dollars / stop_distance
risk_dollars = account_equity × risk_fraction        # commonly 0.5–2% per trade
```
ATR/volatility sizing (bigger stop → fewer shares):
```
stop_distance = ATR × multiplier
shares        = (equity × risk_fraction) / (ATR × multiplier)
```
**Kelly — heavy haircut.** `f = p − (1−p)/b`. Full Kelly is dangerous: slight edge overestimate →
severe drawdown, and p/b on slow signals are noisy. Use fractional Kelly (¼–½) or skip for fixed-fractional.

**Portfolio-level (where multi-signal books live or die):**
- **Portfolio heat** — cap *total* open risk (Σ per-position risk_dollars) at a fixed % of equity.
- **Correlation-aware caps** — failure mode is five signals that are secretly one bet; cap combined
  exposure per correlation cluster / sector / factor.
- **Max positions** — hard integer cap keeps the book auditable.

**LLM interaction:** Python computes `shares` and sets `bounds`; agent tunes within bounds (or
reduce-only). Agent never computes size and never sees a path around portfolio heat — that check runs
in Python *after* the clamp and can veto regardless of agent approval.

---

## 6. Review cadence — event-driven, not fixed windows

**⚠️ Biggest evidence gap: no verified claim adjudicates cadence. Recommendation is `[prior]`,
reasoned from verified data properties.**

The data is slow; fixed 3×-daily windows are calibrated for intraday data that this pipeline doesn't have.
- **COT** releases **Friday ~3:30pm ET** (reflecting prior Tuesday) — changes **once a week**.
- **FRED** updates on a **published release calendar** (CPI, unemployment, etc.).
- **Earnings** land on **scheduled dates** per name.

**Recommendation — two clocks:**
1. **Signal/candidate generation → event-driven**, tied to release schedules (COT screener Friday
   post-release; FRED regime on release-calendar dates; fundamentals on earnings dates). Bonus: this
   *eliminates a class of look-ahead bugs* — a job that only fires on publication can't act on data
   before it exists.
2. **Execution/gate → a fixed daily window (or two).** For swing/position horizon, a single
   **pre-close** review to act on the current candidate list suffices, plus an optional **pre-open**
   gap/overnight-news veto. Mid-day adds cost, not edge, at this horizon.

Net: the five-touchpoint instinct collapses to **event-driven signal jobs + one-or-two daily gate
windows** for slow official-source data. Keep richer intraday cadence in reserve for future fast-data monitors.

> Aligning jobs to release calendars is a *correctness* feature (structural look-ahead defense), not
> just efficiency. Same root problem as the `incremental-since-misses-revisions` note viewed from
> another angle.

---

## 7. Backtesting & validation pitfalls

**Multiple testing manufactures false winners (Deflated Sharpe Ratio):** `[verified]`
- The **single most important number** is **how many signal variations you tried.** A backtest not
  controlling for search extent is *"worthless regardless of reported performance"* — after enough
  trials a false positive is **guaranteed**.
- **Log every trial** (every COT lookback, FRED threshold, composite weighting) and report the
  **Deflated Sharpe Ratio** (penalizes selection bias across N trials + short, non-Normal samples).
  With COT + FRED + fundamentals you'll test dozens of combos — DSR is non-optional.

**Point-in-time / look-ahead:** `[verified]`
- Apply a **tradability mask at data-load time** so no rolling primitive (MA, correlation, rank) reads
  a non-executable price. Quantified: dropping the mask **inflated IC by 18% while cutting realized
  Sharpe by 0.44** — IC alone is misleading.
- Caveat: that paper's t+1 mechanism is China A-share daily-limit-motivated; for US equities/ETFs the
  executability concern is **halts, delistings, revised data**, not symmetric daily limits.

**Revised macro data — ALFRED discipline:** `[extracted]` FRED series are **revised**. Backtesting on
today's revised CPI/GDP is look-ahead. Use **ALFRED vintages (point-in-time)** so each backtest date
sees only data-as-first-published. This is the `incremental-since-misses-revisions` issue; the
surveyed literature almost never handles it.

---

## Recommended architecture

```
┌─ EVENT-DRIVEN JOBS (fire on release calendars) ────────────────┐
│  COT screener (Fri) │ FRED regime (release dates) │ Fundamentals (earnings) │
└───────────────────────────────┬────────────────────────────────┘
                                 ▼
┌─ DETERMINISTIC PYTHON — signal funnel ─────────────────────────┐
│ 1. neutralize (OLS residual vs industry/size)                  │
│ 2. cross-sectional rank / COT-index / z-score composite        │
│ 3. tag {type, implementation, horizon_band}   → RANKED LEADS   │
└───────────────────────────────┬────────────────────────────────┘
                                 ▼
┌─ DETERMINISTIC PYTHON — promotion gates ───────────────────────┐
│ liquidity · confluence · correlation caps · regime dial · dedup│
│ → CANDIDATES {det_score, size, stop, guardrail_bounds}         │
└───────────────────────────────┬────────────────────────────────┘
                                 ▼  (fixed daily window: pre-close, opt. pre-open)
┌─ BOUNDED LLM GATE — read-only state, typed output ─────────────┐
│ input:  masked data (no tickers/dates leaked)                  │
│ output: (approve|reject, size_mult∈bounds, rationale, α)       │
│ Python: CLAMP to bounds · reject if α<X · portfolio-heat check │
│         LOG delta(det vs tuned) + clamp-fired flag             │
└───────────────────────────────┬────────────────────────────────┘
                                 ▼
                        Robinhood MCP (execution — out of scope)
```

---

## 8. Follow-up findings (Pass 2 — resolving the open questions)

Pass 1 flagged three under-evidenced gaps. Pass 2 researched them directly. Results below;
sources in the Pass 2 block at the end.

### Q2 → RESOLVED (strong): reduce-only veto gate, not symmetric ± bands

**This upgrades §4's `[prior]` reduce-only suggestion to an evidence-backed default.** `[verified, high]`
DOSS (arXiv 2606.03704, ICLR 2026 Financial-AI workshop) restricts the LLM to *accept the
deterministic proposal or override it to a predefined conservative default* — the override can
**only revert to the safe default, never introduce a new or larger action.** Implement as a fixed
confidence threshold τ (identical to the canonical abstention rule, TACL 2025 "Know Your Limits"):
```
final = deterministic_default   if confidence < τ
final = agent_proposal          otherwise      # agent_proposal must be ≤ deterministic size
```
- **Don't naively scale size by confidence.** `[verified, high]` "When Alpha Breaks" (arXiv 2603.13252):
  for cross-sectional rankers, epistemic uncertainty is *positively coupled* with signal strength
  (ρ≈0.616 over 1,865 dates), so inverse-uncertainty sizing perversely de-levers the strongest
  signals. **Scope caveat (author-stated):** specific to ranking geometry; may not apply to a slow
  COT/FRED/fundamentals composite. ⚠️ The "0.925 vs 0.375 Sharpe" figure was **refuted 1–2 — do not cite**.
- **If a symmetric band is used anyway:** `[verified, medium]` residual-RL / trust-region practice
  bounds the correction to a small "tube" — **~10–20% of the action range** — since unbounded steps
  cause "catastrophic drops in performance" (TRPO rationale). Robotics/RL analogy, **not** a
  trading-specific magnitude — a starting point to backtest, not a sourced number.
- **Confidence gating is quantifiably viable** `[verified, medium]` (crypto domain, conceptual not
  structural analogy): separating direction-prediction from execution gave 82.68% accuracy at 11.99%
  coverage, ~151 bps/trade. Lower coverage buys materially higher per-trade edge.

**Build decision:** ship reduce-only + τ for v1; keep symmetric ±15% as a documented future
experiment, gated on logged deltas proving up-tunes would have added value.

### Q3 → RESOLVED (strong): decision-log schema

One immutable `gate_decision` row per candidate reaching the gate: `[verified]` unless noted.

| Field | Basis |
|---|---|
| `decision_id`, `trace_id` | LoginRadius / OpenTelemetry (`trace_id` links across services) |
| `timestamp` | Decision Event Schema (DES, arXiv 2604.09296) |
| `input_snapshot_hash` | SHA-256 of exact candidate+market state fed to the gate |
| `deterministic_recommendation` | your pipeline (size, limit, score) |
| `guardrail_bounds` | the (lo, hi) the agent must stay within |
| `agent_proposal` | size, limit, approve/reject |
| `confidence` (α) | drives the τ gate (DOSS) |
| `final_value` | post-clamp |
| `delta` = final − deterministic | the audit crux |
| `clamp_fired` (bool) | flag when the agent tried to exceed bounds |
| `policy_decision` (Permit/Deny) | LoginRadius guardrail-check result |
| `decision_maker` (`deterministic`/`agent`/`human`) | **MiFID II / RTS 24** `[verified, high]` — regulation *mandates* recording which actor decided, via distinct "execution within firm" + "investment decision within firm" fields |
| `agent_rationale` (Thought/Plan) | LoginRadius — **label as *stated* reasoning, not verified truth** (CoT-faithfulness: >30% can be post-hoc) |
| `model_version`, `prompt_hash`, `guardrail_config_version` | **hash-pin all three per decision** for reproducibility |

**Replayability** `[verified, high]`: persist a serialized **checkpoint** at each decision point;
record accept/reject as **first-class workflow state** (`pending`/`approved`/`rejected`); keep an
**append-only ordered event log** (event-sourcing). Input-snapshot hash + pinned config/prompt/model
→ any past decision replays deterministically and diffs cleanly. *(Redis HITL; Microsoft Agent
Framework; LangGraph time-travel.)*
**Alerting** `[prior]`: clamp-fired rate, veto-rate drift, large deltas, confidence drift.

> The load-bearing borrowed field is RTS 24's `decision_maker` attribution — it makes "the agent
> never overrode the math" *provable* from the log rather than merely asserted.

### Q1 → PARTIALLY RESOLVED

- **Market impact** `[verified, high]`: size against the **square-root law** (impact ∝ √Q; depends on
  total volume, barely on schedule) and keep participation **well below the ~20%-of-ADV breakdown**
  where the law fails. *(Bouchaud; arXiv 2205.07385; arXiv 2606.24019.)* ⚠️ The "SEC RATS 20%-of-ADV
  regulatory threshold" was **refuted 0–3** — ~20% is where the *empirical law* degrades, not a rule.
- **Correlation cap** `[verified, medium]`: flag pairs at **|ρ| > 0.70** as the same bet; treat
  **0.70–0.80 as a regime-dependent band**; separate normal- vs crisis-regime correlations.
- **Confluence/dedup** `[verified, medium]`: compute a **cross-correlation matrix of signal
  constituents** before combining (>|0.8| flags concern; pair with VIF); evaluate multiple weighting
  schemes rather than one. ⚠️ **Refuted 0–3, do not cite:** any *optimal number* of signals, **and**
  "learned weights beat 1/N" — equal-weight is a legitimate default.
- **Not resolved** `[prior]`: no citable source for the specific numeric screens (min $ADV floor,
  max spread bps, price floor, exact %-of-ADV cap). A ~1–5% participation cap is a conservative
  reading of the √-law, but the number is yours to backtest.

### Still genuinely open (empirical/calibration, not literature gaps)

1. Numeric liquidity screens ($ADV floor, spread bps, price floor, %-of-ADV) — backtest on own data.
2. Correct τ and its calibration for a *slow* COT/FRED/fundamentals composite (published evidence is
   crypto / cross-sectional-ranker domains with different cadence).
3. Symmetric-band magnitude in *trading* units (±% of size vs ATR/spread/bps denominated).
4. Cluster-level exposure-cap formula once |ρ|>0.70 pairs are grouped (sources give the pairwise flag,
   not the cluster cap).

---

## Do-not-cite
- "Macro models implied ~50% vs financial ~5% recession probability in March 2022" — **refuted 0–3** (Pass 1).
  Only the qualitative "inflation + low unemployment precedes recessions" relationship is supported.
- Any *optimal number* of signals to combine, and "learned weights beat 1/N" — **refuted 0–3** (Pass 2).
- "SEC RATS 20%-of-ADV regulatory threshold" — **refuted 0–3** (Pass 2); the ~20% is an empirical-law
  breakdown point, not a regulation.
- The "0.925 vs 0.375 Sharpe" tail-capping figures — **refuted 1–2** (Pass 2).
- Claim that abstain/veto boundaries *must* be explicit human-defined functions — **refuted 0–3** (Pass 2).

---

## Sources

**Primary (verified):**
- arXiv 2507.07107 — factor neutralization, cross-sectional rank, tradability mask — https://arxiv.org/html/2507.07107
- arXiv 2605.19337 — bounded-gate contract, read-only state, 19-study validation audit — https://arxiv.org/html/2605.19337v1
- arXiv 2409.06289 — LLM bounded to operator grammar + confidence threshold — https://arxiv.org/html/2409.06289v2
- arXiv 2605.28359 — memory-controlled benchmark: no genuine alpha — https://arxiv.org/pdf/2605.28359
- arXiv 2603.22567 — TrustTrade, selective consensus / uniform-trust hallucination — https://arxiv.org/pdf/2603.22567
- arXiv 2605.03762 — OracleProto: prompt "don't use memory" provably fails — https://arxiv.org/pdf/2605.03762
- Federal Reserve FEDS Note — inflation+low-unemployment regime / recession risk — https://www.federalreserve.gov/econres/notes/feds-notes/financial-and-macroeconomic-indicators-of-recession-risk-20220621.html
- SSRN 2460551 — Bailey & López de Prado, Deflated Sharpe Ratio — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551

**Secondary (verified):**
- Quantpedia — time-series vs cross-sectional (value CS / momentum TS / carry both) — https://quantpedia.com/time-series-vs-cross-sectional-implementation-of-momentum-value-and-carry-strat/
- Alpha Architect — z-scored quality composite (QMJ-style) — https://alphaarchitect.com/cross-section-of-returns/
- Barchart — COT Index formula, 3-year lookback, commercials-default — https://www.barchart.com/education/technical-indicators/cot-index
- ml4trading.io Ch.4 — ALFRED point-in-time / two-timestamp discipline — https://ml4trading.io/third-edition/chapters/04_fundamental_alternative_data/

**Practitioner (extracted, position sizing — lower confidence):**
- Risk Before Returns: fixed-fractional / ATR / Kelly-lite — https://medium.com/@ildiveliu/risk-before-returns-position-sizing-frameworks-fixed-fractional-atr-based-kelly-lite-4513f770a82a
- Swing-trading risk management / position sizing — https://www.tradealgo.com/trading-guides/stocks/swing-trading-risk-management-position-sizing-stop-losses-and-portfolio-rules
- Applying the Kelly Criterion to trading — https://quantstrategy.io/blog/applying-the-kelly-criterion-to-trading-maximizing-growth/

### Pass 2 sources (follow-up — §8)

**Primary (verified):**
- DOSS — reduce-only/override-to-default gate + confidence threshold τ (arXiv 2606.03704, ICLR 2026 workshop) — https://arxiv.org/pdf/2606.03704
- TACL 2025 "Know Your Limits" — abstention survey, confidence-threshold rule — https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00754/131566/Know-Your-Limits-A-Survey-of-Abstention-in-Large
- "When Alpha Breaks" — uncertainty↔signal-strength coupling, inverse-uncertainty sizing hazard (arXiv 2603.13252) — https://arxiv.org/pdf/2603.13252
- Decision Event Schema — 10 required root fields, tiered evidence (arXiv 2604.09296) — https://arxiv.org/abs/2604.09296
- Residual Policy Learning — base policy + bounded residual (arXiv 1812.06298) — https://arxiv.org/abs/1812.06298
- Bouchaud review of market-impact laws (arXiv 2205.07385) — https://arxiv.org/abs/2205.07385
- √-law empirical test on AAPL (arXiv 2606.24019) — https://arxiv.org/abs/2606.24019
- MDPI Applied Sciences 15(20):11145 — confidence-threshold direction/execution split — https://www.mdpi.com/2076-3417/15/20/11145

**Regulatory / practitioner (verified):**
- Deutsche Börse RTS 24 Reporting Handbook v4.6 — decision-maker attribution fields — https://www.cashmarket.deutsche-boerse.com/resource/blob/4227544/bfff0d13263440b3438f139eed187d0e/data/20251103_ReportingHandbook_RTS24_v4.6.pdf
- LoginRadius — AI-agent audit field matrix (agent_id, tool_params_hash, policy_decision, trace_id) — https://www.loginradius.com/blog/engineering/auditing-and-logging-ai-agent-activity
- Redis — HITL checkpoint / event-log replay pattern — https://redis.io/blog/ai-human-in-the-loop/
- Bouchaud — the square-root law of market impact — https://bouchaud.substack.com/p/the-square-root-law-of-market-impact
- Emergent Mind — residual RL (clip-to-tube) — https://www.emergentmind.com/topics/residual-reinforcement-learning-rl
- TransferLab — TRPO/PPO trust-region rationale — https://transferlab.ai/blog/trpo-and-ppo/
- FactSet — practical signal-weighting methods — https://insight.factset.com/a-practical-approach-to-weighting-signals
- Macrosynergy — cross-correlation matrix for signal dedup — https://macrosynergy.com/academy/notebooks/regression-based-fx-signals/
- breakingalpha — |ρ|>0.70 correlation-risk heuristic — https://breakingalpha.io/insights/correlation-risk-management-multiple-algorithms
