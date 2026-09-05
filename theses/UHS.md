# UHS — Universal Health Services — 2026-07-30

Price $161.91 (−3.7% on the day, sector-wide move; live quote, 2026-07-30) ·
market cap $9.795B · next earnings 2026-10-26 AMC (tentative)

Entry path not recorded (pre-template run).

## 1. Verdict and thesis

**PASS at $161.91.** kill-thesis: **UNPROVEN** — conditions=6, refuted=0,
unknown=2.

UHS is a durably profitable, modestly levered hospital operator at 6.8×
trailing earnings and an 8.6% levered FCF yield — but more than half of its
EBITDA flows through Medicaid supplemental-payment programs whose statutory
rundown begins in 2028 and whose endpoint the company itself says it cannot
predict, and even a deep-stress reverse DCF implies only ~6.6%/yr at this
price. The price compensates fairly for the risk; it does not misprice it.

**Closest attack:** the six legs are really four — behavioral "pricing power"
is partly the same Medicaid supplemental spigot as the program-renewal leg,
and the 2026 earnings base carries ~$100–150M of out-of-period catch-ups
(detail in the Kill-thesis record).

Load-bearing conditions: count recorded as 6; the conditions were not
enumerated in the original run. Condition tiers not recorded in original run.

## 2. Business

**Created:** 375 inpatient facilities (27 acute-care hospitals; 346 behavioral
inpatient facilities — the largest US freestanding behavioral network) plus 168
outpatient sites across 40 states, DC, the UK, and Puerto Rico (FY2025 10-K).
Acute care is ~59% of revenue (~$10.2B FY2025), behavioral ~41% ($7.19B FY2025
same-facility). Patients get local hospital and psychiatric capacity that is
genuinely scarce — UHS's Laurel Ridge is roughly half the behavioral beds in
the San Antonio market (Q2'26 call).

**Captured:** Per-admission / per-diem reimbursement from Medicare, Medicaid,
and managed care — plus a second, less visible channel: state Medicaid
supplemental programs (directed payments funded by provider taxes and IGTs).
The 10-K quantifies it: net benefit **$1,016M (2024) → $1,339M (2025) →
$1,362M est-2026**, revised on the Q2'26 call to **~$1.5B** against guided
adjusted EBITDA-net-of-NCI of **$2.61–2.72B**. Over half of profitability is
a politically determined payment channel, not a market price.

**Protected:** Hospitals are local regulated oligopolies: licensure,
certificates of need in some states, physician networks, and replacement cost
protect *volume*. Nothing protects the *payment rate* — the actual risk here.
The moat is real and aimed at the wrong threat.

**Operating leverage (Phase 0):** not recorded in the original run.

## 3. Threads pulled

- **The OBBBA rundown (the core thread).** OBBBA (enacted 2025-07-04) caps state
  directed payments at Medicare-rate benchmarks and limits provider taxes;
  grandfathered programs ratchet down ~10pp/yr starting 2028; work requirements
  limit enrollment; ACA-era DSH cuts begin FFY2028 (10-K). Management: ">1/5 of
  the $1.5B is from state-based programs not subject to the OBBBA reductions"
  (Q2 call). The *pace* is bounded by statute; the *endpoint* is undisclosed
  and management says it cannot predict it. Near-term, the current
  administration's CMS has been approving *larger* pools (Florida's April 2026
  preprint approval increased the program; Texas CHIRP 2026 pool $9.2B vs
  $6.5B prior).
- **Earnings-base quality.** Q2'26 included a **$100M out-of-period Florida DPP
  benefit** (Oct 2024–Sep 2025 period); ex-items the quarter missed internal
  expectations by ~$63M (PLGL +$28M, San Antonio $20M, Cedar Hill $15M)
  (release + call). Attack partially blunted: retroactive catch-ups are
  chronic in both directions — Q2'25 contained $101M of its own — so TTM is
  flattered but not uniquely so.
- **Estimate pattern.** Four large beats through 2025 (e.g. Q3'25 $5.69 vs
  $4.82 est), then miss-by-a-hair Q4'25 and two thin beats in 2026 ($5.98 vs
  $5.91 in Q2). The easy upside ended when the policy regime turned (Robinhood
  `get_earnings_results`; broker tier — actuals not cross-checkable in
  `sec_fundamentals.db`, which has no UHS row).
- **Exchange subsidy expiry.** Enhanced subsidies expired 2025-12-31; exchange
  volumes −15% YoY in Q2 with an effectively **1:1 shift to self-pay**
  (management had assumed 10–20% found other coverage); full-year impact
  guided ~$85M, upper half of the original range (call).
- **OCF "collapse" — dead end, and a transcription catch.** The call
  transcript reads "$44.3 million" of Q2 operating cash flow; the actual
  statement shows **$443.3M** (H1: $845M vs $909M, the delta mostly
  AP-disbursement timing per the release). No cash-conversion problem. Do not
  source cash-flow numbers from call transcripts.
- **Laurel Ridge decertification.** Lost CMS reimbursement end of April 2026;
  recertification expected 2027; ~$25M FY2025 EBITDA facility, ~$50M 2026
  impact. UHS behavioral has prior regulatory history (2020 DOJ settlement),
  so the condition is "idiosyncratic, not systemic," not "never again."
- **Malpractice severity.** PLGL reserves +$50M for 2026 via semi-annual
  actuarial review; analyst framing on the call: a 2–3% annual EBITDA headwind
  for several years; management: industry-wide claim severity, cannot predict
  deceleration.
- **Refinancing.** $700M of 1.650% notes due 2026-09-01; new $700M 364-day
  delayed-draw TL amended into the credit agreement July 2026 (release). At
  current rates a rough +$25–30M/yr pre-tax interest headwind. Talkspace
  closes ~mid-August, funded by a separate $400M delayed-draw TL.
- **Capital returns.** Q2 buyback $320M at ~$169 avg (H1 $447.5M at ~$174);
  $977.6M authorization live; management "will meet if not exceed" $800–900M
  for the year. Diluted shares 83.7M (FY2021) → 62.1M (TTM), −26%
  (stockanalysis financials).
- **Options read (mandatory):** Path 2 only — UHS is not in the CBOE catalog,
  so no own-history IV percentile exists. Table in §4. Chain is thin: Sep-18
  ATM call spread is 16% of mark (>10% gate) and put OI is 16 — **fails the
  liquidity gate; reading is UNRELIABLE-labeled context**, and the thesis
  makes no dated claim, so no timing refutation applies.
- **Post-call sweep.** No UHS-specific 8-K or news after the call; today's
  −3.7% is sector-wide (HCA −2.7%, THC −1.9%; ACHC +3.6% on its own print).
  Dead end.
- **Dead ends:** the post-call sweep above, plus the pipeline checks —
  `composite.db` has no UHS row (never flagged); `sec_fundamentals.db`
  doesn't cover UHS; insider Forms 3/4 since the print were not retrieved
  (EDGAR query returned nothing parseable) — logged as an UNKNOWN.

## 4. Valuation

Reverse DCF, **levered `fcf` ($845.4M TTM = ncfo $1,800.3M + capex −$954.9M)
paired with market cap $9,794.8M**, net debt 0 by construction (minority
interest immaterial: $24M vs $1,526M net income).

Hurdle: not computed in the original run.

| scenario | base FCF | growth path | terminal | implied return |
|---|---|---|---|---|
| Base | $845.4M | +4%×3y | +2.0% | **11.3%/yr** |
| Normalized capex | $1.10B (ncfo − ~$700M maintenance capex) | +3%×3y | +1.5% | **13.4%/yr** |
| OBBBA stress | $845.4M | +2%×2y then −3%×3y | 0% | **8.4%/yr** |
| Deep stress | $845.4M | −6%×5y (cum. −27%) | 0% | **6.6%/yr** |

The terminal-growth inputs were tested against the disclosed terminal risk
(the OBBBA/supplemental rundown, 10-K): the base case's +2% assumes core
(non-supplemental) EBITDA growth of ~5–6% roughly offsets the post-2028
ratchet; the stress rows assume it does not. Guided 2026 capex $950M–1.1B vs
D&A $641M — trailing FCF carries heavy growth capex, which is why the
normalized row exists. ATM IV is ~35% (<50%), so the two-decimal figures
stand, but treat the spread between scenarios — 6.6% to 13.4% — as the real
answer.

Cross-checks (stockanalysis, 2026-07-30): trailing PE 6.84, forward PE 7.17,
EV/EBITDA 5.53, P/FCF 11.6, FCF yield 8.63%, shareholder yield 7.18%,
F-score 7.

**Options-implied move** (path 2 — Robinhood stopgap; Sep 18 2026 expiry, 50
DTE, $160 strike, spot $161.91; liquidity gate FAILED → UNRELIABLE):

| metric | value |
|---|---|
| spot | 161.91 |
| expected absolute move (MEAN, not ceiling) | 10.41% |
| 1-σ move | 13.02% |
| ATM IV | 35.19% |
| RV60 | 31.32% |
| RV20 | 41.09% |
| IV > RV60? | YES |
| IV > RV20? | NO |

The windows disagree — that disagreement is the finding: trailing 20-day
realized vol (inflated by the ±11% post-print swings) exceeds forward IV. Not
"elevated." Timing check: the thesis makes no dated claim, so no timing
refutation applies (see §3's options bullet).

## 5. Falsifiers

For an owner (sell):

1. CMS declines or materially shrinks a major program renewal (Florida
   2026-forward, Texas CHIRP annual preprint, Nevada SDP) — watch 8-Ks and
   the Q3 print (2026-10-26, after close, tentative).
2. The supplemental net-benefit trajectory turns down *before* 2028 (next
   10-K table below $1.3B run-rate ex-catch-ups).
3. Behavioral same-facility patient days <1% or rev/patient-day <4% for two
   consecutive quarters — the pricing leg is partly the supplemental spigot,
   so these fail together.
4. PLGL reserve additions ≥$50M repeating in 2027 (actuarial reviews are
   semi-annual).
5. Buyback pace drops materially while the price is depressed.
6. A second facility-level decertification within 12 months (pattern, not
   incident).

**Reopen trigger:** none stated as a dated/machine trigger; the Kill-thesis
record notes a price near **$130** (deep-stress implied ≈ 8%) reopens the
ownership call on its own.

## 6. UNKNOWNs

1. **Post-2028 supplemental endpoint** — what fraction of the ~$1.36B
   run-rate net benefit sits above the Medicare-rate caps and eventually goes
   away. Not in any disclosure; management explicitly cannot predict it.
   *Absence does not kill the thesis at the right price — it caps how good
   the verdict can get (hence UNPROVEN).*
2. **Malpractice severity trajectory** — actuarial, industry-wide,
   forward-unverifiable.
3. **Insider transactions since the print** — not retrieved; would come from
   EDGAR Forms 4. Absence not fatal.
4. **Talkspace terms/price** — funded via $400M delayed-draw TL per the
   release; full consideration not pulled here. Not load-bearing at this size.
5. **Behavioral Medicaid mix by state** — determines where OBBBA lands
   hardest; disclosed only in aggregate.

## 7. Sources

- **Primary:** Q2 2026 earnings release (2026-07-27, 8-K exhibit PDF via
  stockanalysis filings index); FY2025 10-K (filed 2026-02-25 —
  supplemental-program table, OBBBA risk language, segment tables, facility
  counts); Q2 2026 earnings call transcript (2026-07-28, via
  stockanalysis/Quartr — one number corrected against the release: OCF
  $443.3M, not "$44.3M").
- **stockanalysis.com (vetted exception):** statistics, income/cash-flow
  statements, transcripts and filings indexes (fetched live 2026-07-30).
- **Broker/market microstructure:** Robinhood MCP (admissible where no
  integrated official source covers the field): live quote, earnings
  estimate-vs-actual pattern, option chain/quotes, daily closes for RV. Not
  primary; labeled throughout.
- **Reference data:** none used.
- **Point-in-time repo DBs:** none listed in the original run's sources (§3
  records that `composite.db` has no UHS row and `sec_fundamentals.db` does
  not cover UHS).
- **Low-confidence:** none used. Web search used only to rule out post-call
  news ([Yahoo Finance UHS](https://finance.yahoo.com/quote/UHS/),
  [UHS IR news releases](https://ir.uhs.com/news-releases)).

## Kill-thesis record

Verdict **UNPROVEN**, conditions=6, refuted=0, unknown=2.

Per-condition adjudication: not recorded individually in the original run.
Standing/statistical/options-timing checks: options timing recorded in §3/§4
(no dated claim, so no timing refutation applies); other checks not recorded.

**Closest attack:** the six legs are really four — behavioral "pricing power"
(condition 3) is partly the same Medicaid supplemental spigot as condition 1,
and the 2026 earnings base carries ~$100–150M of out-of-period catch-ups, so
the cheap headline multiple overstates the margin of safety. Base-rate note
in the thesis's favor: this resembles HCA through the ACA-DSH-cut era (low
leverage, strong local share, grew through it), not the levered casualties;
against it: OBBBA is enacted law, not a repealable fear.

**Flip evidence:** a CMS approval of the Florida 2026-forward program at
similar scale *plus* any disclosure bounding the post-2028 endpoint (net
benefit floor ≥ ~$1B) flips toward SOUND/buy; a price near **$130**
(deep-stress implied ≈ 8%) reopens the ownership call on its own.
