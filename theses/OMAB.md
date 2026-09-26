# OMAB — Grupo Aeroportuario del Centro Norte (OMA) — 2026-08-20

Price $101.80 (live quote, in-session 2026-08-20; official close $102.02,
2026-08-19) · market cap $4,914,924,966 · EV $5,614,872,051 (not used in the
pairing) · next earnings 2026-10-23 BMO (tentative, broker calendar)

User-directed run, described as a new candidates-screen name; as of this run
`scorer.db` `candidate_appearances` holds no OMAB row and `composite.db`
`ticker_scores` has never flagged it (both are US-universe artifacts; OMAB is
a Mexican FPI trading as an ADR — 1 ADS = 8 Series B shares).

## 1. Verdict and thesis

**PASS at $101.80.** kill-thesis: **SOUND** — conditions=6 (5 probable,
1 plausible), refuted=0, unknown=1.

OMA is close to the platonic good business: thirteen 50-year federal airport
concessions in central-north Mexico with legal exclusivity in each catchment,
anchored on Monterrey, earning 55% operating margins and ~29% ROIC under a
tariff regime indexed to inflation, with an unregulated commercial layer
growing faster than traffic. The price is the problem. On a levered owner-FCF
base rebuilt from the 20-F cash-flow statement (stockanalysis's `fcf` field
overstates it ~2x by missing IFRIC-12 concession capex and interest paid),
today's price implies 4.9–7.8% annual returns against a 10.1% Mexico-risk
cost of equity — and the government demonstrated in 2023 that it can and
will rewrite the concession economics by decree. Wonderful company, wrong
price, and a regulator holding a ratchet.

**Closest attack:** the owner-FCF reconstruction itself — if interest paid
sat inside operating cash flow, the base would be ~$70M too low and the
whole valuation section shifts. Verified against the 20-F consolidated cash
flow statement: interest paid (Ps.1,208,107k FY25) is a financing-activities
line, concession investments (Ps.2,539,273k) are investing — the
reconstruction is exact. The attack failed on the primary filing.

Load-bearing conditions:

1. *probable* — **Legal-monopoly quality.** Exclusive concessions to 2048,
   Monterrey (Mexico's third metro) 54.3% of 2025 traffic, Adjusted EBITDA
   margin 75.2% (2Q26). Source: 20-F, 2Q26 release.
2. *probable* — **Owner FCF is ~$150–220M, not the $412M the aggregator
   prints.** FY25 from the 20-F: NCFO Ps.7,446M − investing Ps.2,417M −
   interest paid Ps.1,208M = Ps.3,821M ≈ $219M; TTM analog ≈ Ps.3,299M ≈
   $189M. stockanalysis `fcf` (NCFO + PP&E capex only) misses concession
   additions and interest.
3. *probable* — **Concession capex steps up.** Approved 2026–2030 MDP:
   Ps.16,634M committed (Dec-2025 pesos, INPPIC-indexed) ≈ Ps.3.3B/yr vs
   Ps.2,517M committed in 2025, plus Ps.1,271M of postponed 2021–2025 works
   moved into 2026–27. 20-F + 6-K of 2025-12-22.
4. *probable* — **Growth ceiling is mid-single-digit in USD.** Traffic:
   2Q26 +0.4%, Jul +3.9%, FY25 +8.5% (post-hoc rebound year); tariffs track
   Mexican inflation minus a 0.8%/yr real efficiency factor; long-run peso
   drag cuts the USD conversion. No path to the ~15–20%/yr FCF growth the
   price needs (see §4).
5. *probable* — **The hurdle is ~10.1% and the pass survives any defensible
   variant.** rf 4.74% + beta 0.8 (floored from a thin-float 0.33) × Mexico
   total ERP 6.69%. Even a US-only hurdle (8.16%) exceeds the base implied
   6.29%.
6. *plausible* — **Perpetuity terminal is generous.** Concessions terminate
   2048; renewal (up to +50y) requires accepting whatever changes the
   Ministry imposes. Without renewal, today's price implies 1.31%/yr. The
   renewal itself is the condition's unknown — but either way the perpetuity
   read is an upper bound, which strengthens the pass.

## 2. Business

**Created:** a passenger or airline touching central-north Mexico has no
alternative — each concession is the only commercial airport in its
catchment. Value created is basic mobility infrastructure: Monterrey
(business/industrial, 54.3% of 2025 pax), tourist coasts (Acapulco,
Mazatlán, Zihuatanejo), and border/regional cities. Occupancy of commercial
space at 96.4% (2Q26) says tenants want in.

**Captured:** four distinct mechanisms, not one. (1) Regulated aeronautical
revenue — a maximum tariff per workload unit (passenger or 100kg cargo),
set per airport per five-year MDP, indexed to Mexican producer inflation
minus 0.8%/yr real, dual-till (domestic TUA +7.7% in 2Q26). (2) Unregulated
commercial revenue — parking, restaurants, VIP lounges, retail; Ps.66.4 per
pax in 2Q26, +6.3% YoY, growing faster than traffic. (3) Diversification —
OMA Carga logistics (+29.1% 2Q26), two hotels, an industrial park at
Monterrey. (4) Construction revenue is an IFRIC-12 accounting artifact —
zero margin, ignore it in mix math.

**Protected:** by statute, not by brand — the Mexican Airport Law requires a
federal concession to operate a public-service airport, and OMA holds the
only ones in its territories until 2048. The moat's true owner is therefore
the government, which has already exercised its power: the Nov 13, 2023
decree doubled the concession tax from 5% to 9% of gross revenues effective
2024, and the 20-F states it "may be revised at any time." The protection
mechanism and the chief risk are the same fact.

**Operating leverage (Phase 0): positive.** FY21→FY25 (MXN, income
statement): revenue 8,720M → 15,964M (+83%); operating income 4,110M →
8,941M (+118%); operating margin 47.1% → 56.0%. TTM: 16,325M / 9,004M
(55.2%). (Total revenue includes zero-margin construction revenue, so the
margin trend understates the operating businesses' leverage.)

## 3. Threads pulled

- **The 2026–2030 MDP (the quarter's structural event).** Approved
  2025-12-18: Ps.16,005M committed investment in Dec-2024 pesos (Ps.16,634M
  in Dec-2025 pesos), max tariffs per WLU set per airport with the real
  efficiency factor moving 0.7% → 0.8%/yr against OMA. Capex steps up ~30%
  vs 2025's committed level, and 2026–27 also absorb Ps.1,271M of postponed
  prior-cycle works. Finding: the FCF trough runs through this five-year
  window; the price does not discount it.
- **The 2023 intervention (the regulatory ratchet).** Concession tax 5%→9%
  by decree effective 2024; 20-F says revisable at any time; OMA may
  *request* a compensating tariff amendment, "such a request may not be
  honored." Finding: the regulated moat's economics sit at the government's
  discretion, demonstrated within the last three years. This is the terminal
  risk named in §4.
- **Owner-FCF reconstruction (the aggregator trap).** stockanalysis `fcf` =
  NCFO + PP&E capex = Ps.6,980M TTM — but OMA's real investment flows
  through "investments in concession" (intangibles, Ps.2,735M TTM) and its
  interest (Ps.1,270M TTM) sits in financing under its IFRS presentation.
  Verified line-by-line against the 20-F cash flow statement. Owner FCF ≈
  Ps.3,299M TTM ($189M) / Ps.3,821M FY25 ($219M).
- **Dividends exceed owner FCF.** FY25 dividends Ps.4,469M vs owner FCF
  Ps.3,821M; total debt rose Ps.11.8B → 14.0B over 2024–TTM. ND/Adj-EBITDA
  is still only 1.03x (FY25), and the July 2026 Ps.3.0B refi (7yr fixed at
  9.17% MXN, AAA-mex, 3.2x demand) shows easy market access — but the
  distribution is partly borrowed, which matters for anyone valuing this on
  its 4.66% dividend yield.
- **Monterrey concentration and the traffic stall.** 54.3% of 2025 pax,
  46.0% of aero+non-aero revenue from one airport; Monterrey traffic fell
  1.6% in 2Q26. Monthly prints: Nov'25 +2.9%, Dec'25 +6.9%, 2Q26 +0.4%,
  Jul'26 +3.9%. Finding: 2025's +8.5% is not the run-rate; the current one
  is low single digits.
- **FX runs through everything.** Peso appreciated 18.85 → 17.51 YoY
  (Jun'26): international TUA (USD-denominated) fell 8.7% in MXN terms
  while the USD-quoted ADR benefited. The USD investor holds MXN cash
  flows; long-run peso depreciation is a drag the recent strength hides.
- **VINCI control.** VINCI Entities beneficially own 29.99%; SETA's Series
  BB (12.9%) carries rights to appoint directors and officers plus a
  technical-assistance fee tied to EBITDA (Ps.69M in 2Q26). The 2026-03-16
  Form 3 cluster (Havard, de Longevialle, Mathieu, Notebaert et al.) is the
  VINCI-slate board refresh. No Form 4 insider sales on file since. Colour:
  a world-class operator with control economics junior holders don't get.
- **Earnings-estimate pattern (broker tier).** Trailing 8 quarters: misses
  Q4'24 (−13%), Q4'25 (−15%), Q1'26 (−5%); beats Q3'25 (+8%), Q2'26 (+2%).
  No managed-guidance smoothness — estimate error is mostly FX and traffic.
  Q2'26 actual $1.74/ADS cross-checks exactly against the 6-K print (no
  `sec_fundamentals.db` row exists to check against; FPI).
- **Post-call sweep.** Since the Jul 28 print: only sell-side moves (JPM to
  Neutral Jul 22, Citi Buy May 7, Santander Outperform May 27, MS PT $125
  Aug 5) and the Aug 5 traffic report. No 8-K/6-K events contradicting
  management's framing. Silence read as: no new facts, the disagreement here
  is valuation method, not information.
- **Options read (mandatory):** path 2 only (Robinhood stopgap) — OMAB is
  not in the CBOE `options.db` catalog, so no own-history IV percentile
  exists. Chain is listed but near-dead (OI 0–5, volume 0 at the ATM
  strikes; spreads ~100% of mark). Liquidity gate FAILED → UNRELIABLE.
  Table and applicability in §4.
- **Dead ends:** no stockanalysis transcript corpus exists for OMAB (0
  calls indexed — corpus coverage, not company history; the Q2 call was
  held 2026-07-28), so the latest-call read was substituted with the full
  earnings release, the 20-F, and eleven months of 6-Ks; `/stocks/OMAB/filings/`
  returns 0 events; `sec_fundamentals.db`, `composite.db`, `scorer.db`
  carry no OMAB rows (US-universe artifacts); no 13D/G amendments in the
  filing window; nothing ruled anything out.

## 4. Valuation

**Inputs.** Market cap $4,914,924,966 (`marketcap` hover, statistics
route, converted at the route's own 17.47 MXN/USD). Levered owner FCF
paired against market cap; net debt 0 by the pairing rule. Base flows are
reconstructed, not the aggregator's field: TTM Ps.3,299M ≈ **$188.8M**
(base); FY25 Ps.3,821M ≈ **$218.7M** (optimistic); forward-MDP-loaded ≈
Ps.2,650M ≈ **$151.7M** (conservative — adds the ~Ps.650M/yr step-up to
the new MDP run-rate incl. postponed works). Haircuts considered: NCI in
net income is Ps.23.6M FY25 (0.4% — negligible, no haircut); SBC nil
disclosed; no pension/litigation claims surfaced (§6.5).

**Hurdle:** rf 4.74% + beta 0.8 × ERP 6.69% = **10.09%** (Damodaran home
page Aug 1, 2026 for rf; ctryprem.html Jan 5, 2026 vintage for Mexico total
ERP — operations-weighted, 100% Mexico). Beta clamp stated: the printed 5Y
beta is 0.333 — a thin-float (avg ~59k ADS/day), 30%-controlled ADR — 
floored into the 0.8–1.2 band. Robustness: even with zero country premium
(US headline ERP 4.28%) the hurdle is 8.16%, above every scenario below.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| conservative (fwd MDP capex) | $151.7M | 3% | 1.5% | 4.86% | −524 bp |
| base (TTM owner FCF) | $188.8M | 4% | 2.0% | 6.29% | −381 bp |
| optimistic (FY25 owner FCF) | $218.7M | 6% | 2.5% | 7.81% | −228 bp |

**Integrity checks.**

- *Terminal ROE / reinvestment:* no "growth without reinvestment" warning —
  FCF < earnings in every scenario. Base implied terminal ROE is 5.11%,
  *below* the 10.1% hurdle: the terminal already assumes reinvestment
  destroys value, and the price still only implies 6.29%. Intentional
  conservatism, stated.
- *Market-share sentence:* 4–6%/yr growth tracks Mexican air-traffic growth
  inside catchments where OMA is the sole operator by law — the forecast
  needs no share gain at all.
- *Terminal risk vs terminal growth:* the dominant disclosed structural risk
  (20-F risk factors) is unilateral revision of the tariff bases/concession
  tax — demonstrated 2023 — plus concession expiry 2048. Terminal growth is
  held at/below inflation (1.5–2.5%, all under rf 4.74%) and the finite-life
  check below prices the endgame explicitly.
- *Finite-concession check (aux arithmetic, not the solver):* flows to 2048
  only, no renewal, no terminal value → today's price implies **1.31%/yr**.
  Most of the price is the un-guaranteed post-2048 renewal.
- *What would clear the hurdle:* ~20%/yr FCF growth ×5y on the base, or
  ~15%/yr on the FY25 base — against +0.4% Q2 traffic. Not in evidence.
- *Base-year cash tax:* cash taxes Ps.2,675M TTM exceed book tax Ps.2,318M —
  the base is not flattered by deferrals.
- *Distribution clamp:* base and conservative implied returns sit below the
  US median cost of capital (7.79%, Data Update 2026); a strong pass
  regardless of story.
- *Own-debt juxtaposition:* OMA's July 2026 7-year peso notes price at 9.17%
  nominal MXN. The equity's implied USD return of ~6.3% sits below the
  company's own peso cost of debt (different currencies — MXN carries
  expected depreciation — but the gap is not close).

**Options-implied move** — path 2 (Robinhood stopgap; no CBOE history).
Primary print: 2026-09-18 expiry, 29 DTE, brackets no scheduled catalyst.
Secondary: 2027-01-15, 148 DTE, the only expiry bracketing the 2026-10-23
BMO earnings (no monthly falls between 10-16 and 01-15).

| metric | Sep-18 (29 DTE) | Jan-15 (148 DTE) |
|---|---|---|
| spot | 101.80 | 101.80 |
| expected absolute move (MEAN, not ceiling) | 6.78% | 14.64% |
| 1-σ move | 8.30% | 18.28% |
| ATM IV | 29.43% | 28.70% |
| RV60 | 32.75% | 32.75% |
| RV20 | 29.83% | 29.83% |
| IV > RV60? | NO | NO |
| IV > RV20? | NO | NO |

Liquidity gate: **FAILED → UNRELIABLE** (ATM OI 0–5 contracts, volume 0,
spreads ≈100% of mark vs the 10%/2-tick gate). Timing check: **N/A** — the
thesis makes no dated claim, so no refutation was attempted; IV below both
RV windows is consistent with no event premium priced, which is not
evidence for anything.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** price: the base scenario clears the 10.09% hurdle only near
  ~$54/ADR; anywhere under ~$65 this becomes a live re-underwrite rather
  than a pass. (Price level — grep-only.)
- **Shift —** owner FCF re-rates: FY26 reported NCFO minus concession
  investments minus interest lands above ~Ps.4.5B (≈$260M) with traffic
  growth restored ≥4% — the base was too pessimistic; revalue.
- **Shift —** the terminal de-risks: a concession extension beyond 2048 is
  granted on published terms, or the 2031–2035 MDP process starts with
  tariff/tax terms visibly favorable; revalue.

For an owner (sell):

- **Break —** a second unilateral revision of the concession tax or tariff
  bases (the 2023 mechanism firing again): the regulated return is not
  property but sufferance; story over at any price.
- **Break —** Monterrey traffic declines for four consecutive quarters
  outside a macro recession: the anchor catchment is impaired.
- **Shift —** peso moves >20% against the USD in either direction: the
  USD flow base is re-set; rerun the valuation.

**Reopen trigger:** 2027-03-01: fy26-print-owner-fcf-traffic

## 6. UNKNOWNs

1. **Post-2048 renewal probability and terms.** Unknowable today — renewal
   requires accepting Ministry-imposed changes. Would come from SICT/AFAC
   policy toward the first expiring concessions (2040s). Does not kill the
   pass; the perpetuity read already gives the thesis this point for free.
2. **Per-airport approved maximum-tariff schedule 2026–2030.** The tables
   in the 2025-12-22 6-K and 20-F stripped out with HTML tables; the totals
   and the 0.8% X-factor are known. Would come from the 6-K exhibit /
   BMV filing. Not load-bearing at this verdict margin.
3. **Per-year 2026–2030 MDP capex schedule.** Only the 5-year total was
   extracted (20-F Note 10 has the split). The average plus postponed
   amounts bound it well enough. Not load-bearing.
4. **Q2'26 call content.** No transcript corpus exists on the vetted route;
   the call was 2026-07-28 (webcast on IR). Mitigated by the full earnings
   release; residual risk is management's verbal framing of the Monterrey
   slowdown. Does not kill the pass.
5. **Litigation/pension-type equity claims.** Not exhaustively swept beyond
   the Ps.2,912M maintenance provision (already in flows). AAA-mex local
   ratings suggest nothing material. If a material claim exists, it makes
   the pass stronger, not weaker.

## 7. Sources

- **Primary:** SEC EDGAR CIK 1378239 — 20-F FY2025 (filed 2026-04-30:
  concession terms/2048, concession tax 5%→9%, X-factor 0.7→0.8, VINCI/SETA
  structure, Monterrey concentration, MDP commitment tables, consolidated
  cash-flow statement); 6-Ks of 2026-07-28 (2Q26 results), 2026-07-17
  (Ps.3.0B notes), 2025-12-22 (MDP approval), 2026-02-24 (4Q25/FY25),
  monthly traffic 6-Ks (Dec'25–Aug'26); Form 3 cluster 2026-03-16/17.
- **stockanalysis.com (vetted exception):** statistics route (market cap,
  EV, USD-converted TTM lines, beta, short interest, analyst counts),
  income-statement and cash-flow-statement routes (MXN history — the `fcf`
  field's IFRIC-12 blind spot corrected against the 20-F), symbol lookup,
  news feed.
- **Broker/market microstructure:** Robinhood MCP — live quote, option
  chain/instruments/quotes (no integrated official source covers this ADR's
  live quotes or chain), daily bars for the RV windows, trailing
  estimate-vs-actual EPS (estimates are not covered by any integrated
  source; actuals cross-checked to the 6-K).
- **Reference data:** Damodaran — rf 4.74% and US implied ERP 4.28% (home
  page, Aug 1, 2026); Mexico total ERP 6.69% (ctryprem, Jan 5, 2026
  vintage); US cost-of-capital distribution (2026 Data Update 5); ~29%
  excess-return base rate (EVA dataset).
- **Point-in-time repo DBs (read-only):** `stocks.db` v_latest snapshot 37
  (2026-08-19 close $102.02, next earnings 2026-10-23, CIK, float);
  `composite.db` / `scorer.db` / `sec_fundamentals.db` / `options.db` — no
  OMAB coverage (itself recorded as a finding).
- **Low-confidence:** TheFly analyst-action headlines via the stockanalysis
  news feed (upgrades/PTs), labelled colour only.

## Kill-thesis record

Ledger line: `2026-08-20 OMAB SOUND conditions=6 refuted=0 unknown=1
reopen=2027-03-01:fy26-print-owner-fcf-traffic` (thesis direction: PASS).

Per-condition adjudication:

1. Legal-monopoly quality — **SURVIVED.** Attack: is the exclusivity real?
   No competing commercial airport can operate without a federal concession
   (Airport Law); no second-airport project exists in OMA's catchments
   (unlike Mexico City's AIFA, which sits in ASUR/GACM territory).
2. Owner-FCF reconstruction — **SURVIVED** (closest attack). Interest-paid
   placement verified in the 20-F cash-flow statement (financing); FY25
   arithmetic ties to the peso (7,446 − 2,417 − 1,208 = 3,821).
3. Capex step-up — **SURVIVED.** Attack: is the MDP figure inflated or
   deferred? It is committed, INPPIC-indexed, and 1H26 actuals (Ps.949M in
   2Q26 alone) already run at the higher rate.
4. Growth ceiling — **SURVIVED.** Attack (bull side): MDP capex is
   remunerated through the tariff base, so aero revenue can outgrow
   inflation. Granted in the optimistic scenario (6%/yr) — still −228 bp
   versus the hurdle; clearing it needs ~15%/yr on that base with +0.4%
   current traffic. The internal-consistency check also flags the bull
   variant: high growth + rising payout + government-capped returns cannot
   all hold (g = reinvestment × return, and the return is regulated).
5. Hurdle — **SURVIVED.** Attack: country risk double-counted with the
   beta floor? Every defensible variant (US-only ERP 8.16%; mature+CRP
   ~10.6–11.5%; floor-free 6.97% rejected as thin-float artifact) exceeds
   the base implied 6.29% except the indefensible raw-beta one.
6. Perpetuity-terminal generosity — **SURVIVED** with the run's one
   UNKNOWN (renewal). Both branches favor the pass: renewal granted →
   perpetuity read stands and still fails the hurdle; renewal denied/
   repriced → 1.31% finite-life read governs.

Standing checks: base rate — only ~29% of firms sustain excess returns;
OMA's regulated monopoly is a legitimate candidate for the persistent
minority, which is why the verdict attacks price, not quality. Short case —
traffic stall + Monterrey nearshoring fade + peso reversal + debt-funded
dividends through a five-year capex trough: constructed, and it is
materially the pass case. Management incentives — VINCI's EBITDA-linked TA
fee and control stake reward EBITDA growth and distributions over per-share
FCF discipline; consistent with debt-funded dividends, does not contradict
the pass. Disconfirming search — sought the bull case: 8 analysts, mean PT
$123.90 (+22%), upgrades through 2026; their EV/EBITDA-multiple framing does
not engage the owner-FCF or finite-concession math. Moat mechanism — named
(statutory exclusivity), not a checkbox.

Statistical checks: no backtest/screen claims in the thesis; only the base
rate above was used. Options timing check: N/A by rule — no dated claim;
coverage disclosed (path 2 stopgap, illiquid chain, liquidity gate FAILED).

**Closest attack:** condition 2 (the FCF reconstruction), refuted by the
20-F cash-flow statement itself.

**Flip evidence:** toward FLAWED/buy — FY26 owner FCF ≥ ~Ps.4.5B with
traffic ≥4%, a price near ~$54–65, or a published-terms concession
extension (any one reopens; all three would flip). Toward harder-pass —
a second unilateral concession-tax/tariff revision, or Monterrey declining
four straight quarters.
