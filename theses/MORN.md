# MORN — Morningstar, Inc. — 2026-10-03 (reopen of 2026-09-01, trigger: scheduled-sweep)

Price $183.61 (last regular-session trade, 2026-10-02; ex-dividend $0.50 that
day) · market cap $6.888B · next earnings 2026-10-28 AMC (confirmed —
Robinhood `verified=true`, stockanalysis "next confirmed earnings date")

**Reopen block.** Prior file: `research/MORN-2026-09-01.md` — verdict FLAWED,
ownership call **PASS at $209.86**. Its first flip-toward-buy falsifier was
"price at or below ~$185 with the TTM base unchanged", where its finding row
moved to +84 bp. Price is now $183.61 and the TTM base is literally
unchanged (no print since Q2). The reopen question: does the fired price
trigger flip the call?

Unattended scheduled run.

## 0. The reopen question, answered first

**Not yet — the trigger fired on price, but the hurdle moved under it.** The
prior trigger's +84 bp assumed the 8.81% cost of equity held. It did not:
the 10-year Treasury went from 4.75% (Damodaran's 2026-09-01 rate, the one
the prior hurdle used) to **5.24%** (`DGS10`, 2026-10-01), and the 5-year
beta printed 1.02 against 0.98. The hurdle rose **65 bp to 9.46%**. Re-run
the prior's own finding row (SBC deducted, 6.5% flat, 2.0% terminal) at
today's price and hurdle and the spread is **+24 bp**, not +84 bp. Using
the skill's default terminal ceiling (the 2.36% breakeven, where the prior
used 2.0%) it is **+51 bp**. Both sit inside the ±70 bp band of hurdle
estimation error the prior run named as the bar for a determinable sign.
At today's hurdle the price that clears the bar is about **$179**.

The September decline itself carries no company news. Morningstar fell
12.5% between the 9/1 and 10/2 closes; FactSet fell 12.9%, S&P Global
12.3%, Moody's 10.8%, MSCI 4.8%, and SPY *rose* 1.0% (Robinhood daily bars).
The whole financial-data and ratings group de-rated together while the
10-year rose 45 bp. This was a factor move, not a MORN fact.

| prior falsifier | actual | status |
|---|---|---|
| Shift — price ≤ ~$185 with TTM base unchanged | $183.61, base unchanged — but hurdle +65 bp, so the spread is +24 bp (prior construction) / +51 bp (breakeven terminal), not +84 bp | **FIRED** (nominally; premise did not hold) |
| Shift — Q3 Direct/PitchBook AOI margins expand YoY | Q3 prints 2026-10-28 | **NOT TRIGGERED** (pending) |
| Shift — renewal and licence tables kept, Direct licences growing | Q3 supplemental, 2026-10-28 | **NOT TRIGGERED** (pending) |
| Shift — disclosed MCP/LLM licensing revenue | September Q&A (8-K 2026-09-25) silent on it | **NOT TRIGGERED** |
| Break — Direct/PitchBook renewal < 100% | Next reading FY2026 10-K, ~Feb 2027 | **NOT TRIGGERED** |
| Break — renewal table withdrawn without substitute | No filing since | **NOT TRIGGERED** |
| Shift — Direct licences −2%+ YoY two quarters | Q3 supplemental, 2026-10-28 | **NOT TRIGGERED** (pending) |
| Shift — Credit revenue −20%+ | No print | **NOT TRIGGERED** |
| Break — levered acquisition > ~$1B outside core | None. Sept Q&A answers an M&A question with "selective acquisitions" in a "balanced capital allocation approach" — standard language, no deal | **NOT TRIGGERED** |
| Shift — Vanguard index-provider review | Nothing found in the news or EDGAR sweep | **NOT TRIGGERED** |

## 1. Verdict and thesis

**PASS at $183.61.** kill-thesis: **FLAWED** — conditions=5 (1 probable,
4 plausible), refuted=1, unknown=0, pending=2, not_obtained=0.

**p(beat SPY, 63 td): 0.47** · kill-thesis: 0.45

**Disputed expectation:** after stock compensation, the price implies 9.97%
a year on 6.5% growth and a 2.36% terminal. That is +51 bp over a 9.46% cost
of equity, inside the hurdle's own error band. The Q3 print (2026-10-28)
settles whether Direct and PitchBook segment margins stop compressing.
Damodaran's 2026-10-01 ERP settles whether the rate spike raised the
hurdle or only moved the premium around inside it.

It is still a good business, and it is materially closer to a buy than a
month ago. Six of eight valuation rows now clear the hurdle, against three
of seven last time. But the 12.5% price drop bought back less margin of
safety than it looks: half of it went to a 49 bp rise in the risk-free rate.
The honest central reading is about +50 bp of expected excess return. The
prior run said that is not enough to be confident of the sign. The
refuted condition (segment margin compression) gets its next test in 25
days. One condition refuted, two pending, and a thin spread add up to a
narrow pass, not a buy.

**Closest attack:** the hurdle-vintage attack, which argues the PASS is
mis-measured in the opposite direction. Damodaran's 4.14% ERP was solved
against a 4.75% T-bond on 2026-09-01. The S&P 500 then ended September
higher while the 10-year rose 49 bp. An implied ERP solves for the index's
expected return and subtracts the T-bond, so a flat index and a higher
T-bond mechanically shrink the premium. A vintage-consistent hurdle is about
8.97–9.06%, and the finding row's spread becomes **+91 to +100 bp**, clear
of the bar. The PASS survives because that figure is an inference about a
number not yet published. The skill's recipe pairs today's `DGS10` with the
latest published ERP, and the mature-company companion (rf + 4.5% = 9.74%)
cuts the other way (+23 bp). The October 1 ERP is a dated PENDING item, and
§5 carries it as a flip.

**Load-bearing conditions of the bull case (5).** MCP/LLM distribution
monetising is *possible* tier, so it is option value in §6, not a condition.

1. *plausible* — **Renewal rates hold ≥100% at Direct and PitchBook through
   the AI transition.** FY2025 10-K table: Data 101%, Direct ~104%,
   PitchBook ~103% (PitchBook down from 108%). Settles in the FY2026 10-K,
   ~Feb 2027. The Aug-25 Q&A #6 says the metric "may become less meaningful
   as pricing models change."
2. *probable* — **Consolidated operating leverage stays positive.** TTM
   revenue +9.3% YoY against operating income +27.2%. FY2020→TTM revenue is
   +84.7% and operating income +171%.
3. *plausible, refuted for the trailing period* — **Direct and PitchBook
   segment AOI margins stop compressing.** Q2 26: Direct 45.2% vs 46.0%,
   PitchBook 30.3% vs 31.7% (Aug-25 Q&A #6). PitchBook's AI savings are
   "redeployed… rather than flowing straight through to margin" (#22). Next
   reading: Q3 print, 2026-10-28.
4. *plausible* — **SBC-deducted levered FCF ($430.5M) is a fair owner's
   flow.** $497.5M TTM FCF less the $67.0M SBC run-rate. It still excludes
   acquisition spend: charging a $150M/yr deal run-rate prints −74 bp.
   Settles with the FY2026 cash-flow statement (~Feb 2027), but the Q3 10-Q
   updates the TTM.
5. *plausible* — **Credit's private-market ratings growth persists.** ~25%
   of 2025 credit-ratings revenue references private markets (Aug-25 Q&A
   #11), and Credit is the largest growth contributor. Next reading: Q3
   print, 2026-10-28.

**Dominant shared risk factor:** generative-AI substitution of paid
information and knowledge-work subscriptions sold to enterprises — shared by
3 of 23 other held names (INTU "generative-AI substitution of paid
software/services workflows"; SAP "enterprise application software seat-and-
suite spend displaced by AI agents"; G "AI-driven deflation in
labour-arbitrage knowledge services") · 0 unlabelled. Holdings come from
`composite.db`'s `portfolio_holding` signal on its latest snapshot (24
symbols, MORN included). `portfolio.db` is not readable in this unattended
slot, so the list covers composite's view of the book, not a live broker
read.

## 2. Business

Unchanged from `research/MORN-2026-07-30.md` §2 and the deltas in
`research/MORN-2026-09-01.md` §2. Value is created through curated
investment data across funds, private markets, credit and indexes. It is
captured through per-seat and enterprise licences (moving to value- and
consumption-based pricing), issuance-linked ratings fees, AUM basis points,
and index licensing. It is protected by DBRS's NRSRO licensure, the
analyst-built private-markets dataset, and index switching costs. Deltas
this run:

**Created / Captured:** no new disclosure. The September investor Q&A (8-K
2026-09-25, questions through 2026-09-04) covered only M&A policy and board
tenure.

**Protected:** no new evidence either way. The peer-group de-rating (§0) is
the market re-pricing the whole category's protection. It is not
information about Morningstar's specific mechanisms.

**Control:** unchanged in substance. Founder Joseph D. Mansueto ~37%;
insiders 47.75% (stockanalysis) / 48.52% (`stocks.db`); float 19.3–19.6M
on 37.51M shares out. One share class. The structure forecloses an
unsolicited takeover and any activist path. One intra-family movement: Daniel
Mansueto, a 10% owner, reported a Form 4 (filed 2026-10-02). It records a
scheduled GRAT annuity distribution of 657,779 shares to the grantor on
2026-09-30, code J, $0, leaving 3,196,048 held through GRATs. That is a
transfer inside the control group, not a sale.

**Operating leverage (Phase 0): positive at the consolidated line, negative
at the two largest segments.** No new print, so the figures are the prior
run's:

| | revenue | operating income | op margin |
|---|---|---|---|
| FY2020 | $1,389.5M | $215.2M | 15.5% |
| TTM to Q2 2025 | $2,347.4M | $458.9M | 19.6% |
| TTM to Q2 2026 | $2,566.5M | $583.5M | 22.7% |

Revenue +9.3% YoY against operating income +27.2%. That is consolidated
expansion from mix (Credit growth, retired loss-making products), while
Direct and PitchBook AOI margins compress (condition 3). The live
statistics page confirms the TTM is unchanged: revenue $2.57B, operating
income $583.50M, FCF $497.50M.

## 3. Threads pulled

- **The rate leg (load-bearing this run).** `DGS10` climbed almost every
  week of September: 4.79% (9/1) → 5.00% (9/15) → 5.18% (9/24) → 5.29%
  (9/30) → 5.24% (10/1). The 10-year breakeven (`T10YIE`) held at
  2.31–2.40% throughout, so the move is real yield, not inflation. For a
  long-duration equity flow, that changes the hurdle without changing the
  business. It is why §0's trigger fired without flipping the call.
- **The price leg: a group move, not a MORN move.** 9/1→10/2 closes: MORN
  −12.5%, FDS −12.9%, SPGI −12.3%, MCO −10.8%, MSCI −4.8%, SPY +1.0%. The
  worst stretch, 9/8–9/11, hit FDS hardest (−14% in four sessions) and MORN
  with it (−8.8%). MORN's beta to the group is high, and its idiosyncratic
  component over the month is roughly zero. The factor line in §1 names the
  scenario the group is pricing.
- **10/2 specifically.** MORN −3.7% on the day against an adjusted prior
  close of $190.71, so the $0.50 ex-dividend is 0.26pp of it. The same day:
  FDS −4.2%, MSCI −1.7%, MCO −1.3%, SPGI −0.5%, SPY +0.7%. The only filings
  that day were the Daniel Mansueto Form 3/Form 4 (GRAT distribution,
  above). No news found.
- **EDGAR post-call sweep (complete this run, unlike the prior's 403).**
  Filings since 2026-08-20: 8-Ks on 8/25 (Aug investor Q&A, read last run),
  9/18 (Item 8.01, quarterly dividend $0.50, unchanged), and 9/25 (Item 7.01,
  Sept investor Q&A). Form 4s through August are the 0001324069 filer
  cadence (Mansueto 10b5-1 per the 2026-07-30 run) and director/officer
  filings on 8/26 and 9/2. No 8-K Item 1.01/2.01 (no deal) and no Item 5.02
  (no officer change).
- **Earnings pattern.** Six straight adjusted-EPS beats: Q1 25 +8.3%,
  Q2 25 +9.6%, Q3 25 +5.4%, Q4 25 +14.8%, Q1 26 +19.5%, Q2 26 +9.9%
  (Robinhood). These are not hair-thin, managed beats. The consensus
  undershoots persistently. Q3 26 estimate: $2.97. As the prior run
  recorded, these actuals are adjusted, not GAAP (Q2 26 GAAP diluted EPS
  $2.83 in `sec_fundamentals.db` vs $3.10 adjusted). No new quarter to
  cross-check.
- **Buyback continues.** Shares −3.05% QoQ and −6.52% YoY (statistics
  page; buyback yield 6.52%). As the prior run said, this redistributes the
  equity return rather than adding to it.
- **Options read (mandatory):** path 2 (Robinhood stopgap) only. MORN is
  not in the CBOE catalog, so path 1 is structurally unavailable. Liquidity
  gate **FAILED → UNRELIABLE**. Table in §4.
- **Dead ends:** (a) no sector news explains the September group de-rating.
  A web search for a FactSet/S&P Global/Moody's sell-off in September 2026
  returned only February 2026's SPGI guidance-miss episode, so the cause
  stays unattributed beyond the rate move. (b) No new transcript and no
  earnings call, by design. The investor Q&A cadence held: September
  questions through 9/4, response 9/25. (c) The September Q&A carries no
  operating data. (d) Damodaran's home page still shows the 2026-09-01 ERP;
  the October 1 update is not yet posted. (e) `composite.db` still has MORN
  at zero signals, 0.0 coverage, `in_portfolio=1`. Expected for a
  microcap-dislocation scanner.

## 4. Valuation

**Inputs.** Levered TTM FCF **$497.5M** (operating cash flow $646.9M − capex
$149.4M; live statistics page, unchanged since Q2) against **market cap
$6,887,866,771** (37,513,571 shares × $183.61). Net debt is 0 by the pairing
rule: the flow is post-interest, so EV ($8.27B) would double-count the
debt. No minority interests. Cash $523.8M is 7.6% of market cap, so no
excess-cash adjustment. The SBC run-rate is $67.0M (`stocks.db`, 2.61% of
revenue), and the finding row deducts it, giving $430.5M. Cash earnings
for the reinvestment check are $524.3M (net income $421.6M + $102.7M
acquired-intangible amortisation, carried from the prior run's cash-flow
statement).

**Hurdle:** rf 5.24% (`DGS10`, 2026-10-01) + beta 1.02 × ERP 4.14%
(Damodaran implied ERP as of 2026-09-01, against his 4.75% T-bond) =
**9.46%**. Beta is inside the 0.8–1.2 band; no clamp. Insiders at 48% trip
the thin-float warning, but that floors a *sub-band* beta, and 1.02 is not
sub-band. **The vintage mix is not small this month.** The reference
treats the month-old ERP as noise next to its own drift (4.28→4.14 was
14 bp). This month the rate moved 49 bp between the ERP's solve date and
today, so §1's closest attack carries the vintage-consistent alternative
(≈8.97–9.06%). The mature-company companion is rf + 4.5% = 9.74%. US ERP
used: about a quarter of revenue is non-US, all in developed markets, where
the country-weighted ERP differs by tens of basis points at most.

**Terminal-growth ceiling:** 10-year breakeven `T10YIE` **2.36%**
(2026-10-02).

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| base (demonstrated growth) | $497.5M | 8/8/7/7/6% | 2.36% | 11.40% | **+194 bp** |
| conservative | $497.5M | 6.5% flat | 2.36% | 11.13% | **+167 bp** |
| SBC deducted, demonstrated growth | $430.5M | 8/8/7/7/6% | 2.36% | 10.21% | **+75 bp** |
| **SBC deducted, conservative growth** | **$430.5M** | **6.5% flat** | **2.36%** | **9.97%** | **+51 bp** |
| same, prior run's 2.0% terminal | $430.5M | 6.5% flat | 2.00% | 9.70% | **+24 bp** |
| terminal real-growth stress | $497.5M | 5% flat | 1.0% | 9.62% | **+16 bp** |
| acquisition charged, acquisitive growth | $347.5M | 8/8/7/7/6% | 2.36% | 8.73% | **−74 bp** |
| AI-decay stress | $497.5M | 4/3/2/1/0% | 0.0% | 7.92% | **−155 bp** |

**The bolded row is the finding.** It is the only construction whose
terminal value passes the reinvestment check (below). The gross-FCF rows
look rich for exactly the reason they fail it. Across hurdles, the finding
row's spread is +100 bp at a vintage-consistent 8.97%, +51 bp at the
recipe's 9.46%, and +23 bp at the 9.74% mature-company companion. **Flip
price at today's hurdle: ~$179** (market cap $6.716B gives 10.16%, +70 bp).
On the prior's 2.0% terminal it is ~$172.

ATM IV is 42.2%, under the 50% precision trigger, so two decimals are
admissible. The spread is the finding.

**Integrity checks.**

- *Reinvestment / terminal ROE: answered.* On gross FCF ($497.5M against
  $524.3M cash earnings) the reinvestment rate is 5.1%, and 2.36% terminal
  growth implies a 46.2% perpetual return on retained capital. That is
  indefensible, and it is why the gross rows are not the finding. On the
  SBC-deducted base the reinvestment rate is 17.9%, and the implied terminal
  ROE is **13.19%**: 3.7 points above the 9.46% hurdle (inside Damodaran's
  ~5-point band) and below MORN's actual 18.24% ROIC. The finding row is
  internally consistent. On net income alone (no amortisation add-back),
  the tool's growth-without-reinvestment warning would fire. The
  acquired-intangible base is why it does not: goodwill $1,745.6M and
  intangibles $569.2M (prior run).
- *Market-share sentence.* 6.5% for five years puts 2031 revenue at about
  $3.52B, an increment of ~$0.95B. Against a competitive set (Bloomberg,
  LSEG, FactSet at $2.44B TTM, S&P Capital IQ, plus the ratings majors)
  many times Morningstar's size, that needs no implausible share. The base
  path ($3.63B) is the same answer.
- *Terminal growth vs Item 1A.* The dominant structural risk is AI
  scraping and free substitution of paid information. That is FY2025 10-K
  Item 1A, as quoted in the 2026-07-30 run; not re-read this session
  because no new 10-K has been filed. A 2.36% terminal is nominal
  inflation with zero real growth. It survives that risk only if the
  non-scrapeable legs (NRSRO licensure, analyst-built private data, index
  licensing) carry the terminal cash flow. The AI-decay row is the run
  where they do not (−155 bp). The base rate (only ~29% of firms earn above
  their cost of capital) argues for fade, which the 0%-terminal row
  expresses.
- *Base-year cash tax.* TTM effective rate ~25% against a mid-20s
  marginal. No NOL flattery and no haircut.
- *Distribution clamp.* Rows span 7.92%–11.40%. The finding row (9.97%)
  sits at the top of the ~5–10% band holding 80% of US firms. The two
  gross rows above 10% fail the reinvestment check. Nothing here is a
  strong pass on distribution grounds, and nothing is a screaming buy
  either.
- *Explicit-period growth vs reinvestment (raised by Phase 5).* 6.5%
  growth on a 17.9% accounting reinvestment rate implies a ~36% return on
  new capital during the forecast years, about twice the 18.24% ROIC. The
  defence is partial: a data business expenses most of its reinvestment
  (analyst headcount, product build) through opex, so the
  capex-and-acquisition reinvestment rate understates it. The strain is
  real, and it is one more reason the +51 bp is not a margin of safety.
- *No leverage gate.* Net debt $1.38B against EV $8.27B is 16.7%, well
  under half, so the equity-as-option lens is not run.

**Options-implied move.** Path 2 (Robinhood stopgap) only; path 1 is
structurally unavailable (not in the CBOE catalog). Expiry **2026-11-20, 49
DTE**, ATM $185 strike. It is the nearest listed expiry that brackets the
2026-10-28 AMC print (10-16 expires before it). IV is the mean of the
call's 44.20% and the put's 40.29%. Marks: call $11.50, put $10.90.

| metric | value |
|---|---|
| spot | 183.61 |
| dte (calendar days) | 49 |
| ATM IV | 42.24% |
| expected absolute move (MEAN, not a ceiling) | 12.20% |
| 1-sigma move | 15.48% |
| RV60 | 39.13% |
| IV > RV60? | YES |
| RV20 | 38.02% |
| IV > RV20? | YES |

**Liquidity gate FAILED → UNRELIABLE.** Open interest is 0 (put) and 1
(call), volume 0 and 1, and bid/ask spreads are $3.80 and $4.00, about 35%
of mark. Read as shape only: IV sits a few points above both realised
windows, a modest premium consistent with an earnings print inside the
window. IV rose from 37.5% a month ago as realised vol stayed high.
**Timing check: NOT APPLICABLE.** The thesis states no dated move
requirement.

## 5. Falsifiers

**For the pass (flip toward buy):**

- **Shift —** price at or below ~$179 with the TTM base and today's 9.46%
  hurdle unchanged. The finding row clears +70 bp there. (Restated from the
  prior run's $185, which assumed an 8.81% hurdle.)
- **Shift —** Damodaran's 2026-10-01 implied ERP at or below ~3.75% with
  `DGS10` near 5.2%. That puts the hurdle near 9.05% or lower and the
  finding row at ≥ +90 bp at today's price.
- **Shift —** the Q3 26 print (2026-10-28) shows Direct and PitchBook AOI
  margins expanding YoY, reversing condition 3's refutation.
- **Shift —** the Q3 supplemental keeps the licence and renewal tables and
  Direct licences return to growth.
- **Shift —** a disclosed, quantified MCP/LLM licensing revenue line.

**For an owner (sell):**

- **Break —** Direct or PitchBook revenue renewal rate below 100% in the
  FY2026 10-K (~Feb 2027).
- **Break —** the renewal table withdrawn without a comparable substitute.
- **Shift —** Direct licensed users down more than 2% YoY for two
  consecutive quarters (Q2 26: −0.6%).
- **Shift —** a second consecutive quarter of Direct and PitchBook AOI
  margin compression at the Q3 print, *without* offsetting consolidated
  leverage. Condition 3 moves from "refuted for one period" to a trend.
- **Shift —** Morningstar Credit revenue down 20%+ without offsetting
  subscription acceleration.
- **Break —** a levered acquisition above ~$1B outside data, ratings, or
  indexes.
- **Shift —** `DGS10` sustained above ~5.6%. The hurdle passes the finding
  row's implied return at today's price.

**Reopen trigger:** 2026-10-29: morn-q3-print-direct-and-pitchbook-aoi-margins-expand-yoy-or-price-at-or-below-179-at-9.46-hurdle-or-oct-erp-at-or-below-3.75

## 6. UNKNOWNs

1. **PENDING 2026-10-28** — Q3 26 Direct and PitchBook AOI margins, Direct
   licence count, Credit growth. They come from the Q3 8-K/supplemental and
   settle conditions 3 and 5. Their absence does not kill the thesis; the
   date is fixed.
2. **PENDING ~early October 2026** — Damodaran's 2026-10-01 implied ERP, the
   number that settles whether the 9.46% hurdle overstates the cost of
   equity (§1 closest attack). It will come from his home page. It does not
   kill the thesis; it moves the spread by up to ~50 bp.
3. **PENDING ~Feb 2027** — FY2026 renewal-rate table, and whether it
   survives as a disclosure at all (Aug-25 Q&A #6). It settles condition 1.
   It is not fatal by itself. Withdrawal without a substitute is a §5 Break.
4. **UNKNOWN** — Indexes/CRSP economics. Below ASC 280 segment thresholds
   (Aug-25 Q&A #24), so no filing carries them. Bounded: ~6% of revenue.
   Not fatal.
5. **UNKNOWN (option value, *possible* tier)** — MCP/LLM licensing revenue.
   Three mechanisms confirmed, no dollars disclosed, and the largest one
   (premium connectors) is free today (Aug-25 Q&A #23). Not a base-case
   input.
6. **UNKNOWN** — the cause of the September sector de-rating beyond the
   rate move. No news source attributes it. If it reflects a specific AI
   product launch aimed at financial data, it bears on the factor line; no
   evidence was found either way.

## 7. Sources

**Primary:** SEC EDGAR, all read via WebFetch this session.
`cgi-bin/browse-edgar` filing list for CIK 1289419 (filings since
2026-08-20). 8-K 0001289419-26-000048 (filed 2026-09-25, Item 7.01, Sept
investor Q&A, questions through 2026-09-04; Exhibit 99.1
`morningstarresponsestoin.htm`). 8-K 0001289419-26-000046 (filed 2026-09-18,
Item 8.01, $0.50 dividend). Form 4 0002047675-26-000008 (Daniel Mansueto,
GRAT distribution, 2026-09-30). The August 25 investor Q&A (accession
0001289419-26-000035; Q&A numbers #1–#24 cited above) and the FY2025 10-K
Item 1A and renewal table are carried forward from
`research/MORN-2026-09-01.md` and `research/MORN-2026-07-30.md` as
point-in-time citations.

**stockanalysis.com (vetted exception):** `/stocks/MORN/statistics/`, read
as the rendered page via WebFetch: the headless slot's probe CLI prints a
schema summary only, so the `__data.json` `hover` route could not yield
values. Used for market cap, EV, shares (37.51M), float, insider/institution
%, TTM revenue/op income/net income/EBITDA/OCF/capex/FCF, cash, debt, beta
1.02, ROIC 18.24%, WACC 8.21%, short float 7.33%, buyback yield 6.52%, next
earnings date, analyst target $236.67. Probe schema-run on the same route
confirmed the page structure.

**Broker/market microstructure:** Robinhood MCP. The MORN/SPY quote (last
regular trade 2026-10-02, adjusted prior close for the ex-dividend), daily
bars for MORN/SPY/FDS/MSCI/SPGI/MCO (2026-06-24 → 2026-10-02) for the peer
comparison and RV windows, trailing-8-quarter estimate-vs-actual EPS, and
the option chain, instruments and quotes for the 2026-11-20 $185 straddle.
Admissible: no integrated official source covers real-time quotes, option
marks or consensus estimates for this ticker.

**Reference data:** Damodaran NYU Stern home page, fetched 2026-10-03:
implied ERP 4.14% and T-bond 4.75%, both as of 2026-09-01 (the October
update not yet posted). Terminal-ROE band and mature-company companion via
`references/damodaran-anchors.md`.

**Point-in-time repo DBs:** `data/fred.db` (DGS10 5.24% on 2026-10-01 and
its September path; T10YIE 2.36% on 2026-10-02). `data/stocks.db` (beta
1.02192, insiders 48.52%, institutions 65.66%, float 19,293,311, shares out
37,513,571, SBC $67.0M, SBC/revenue 2.61%, 3 analysts). `data/composite.db`
(MORN zero signals, `in_portfolio=1`; the 24-symbol `portfolio_holding`
list used for the factor overlap). `data/options.db` (path 1 unavailable,
not in catalog). `data/earnings.db` was queried but its view has no
`symbol` column under that name, so the confirmed date comes from
Robinhood and stockanalysis instead.

**Low-confidence:** web search results (dividend ex-date colour; the
February 2026 SPGI-guidance sector episode, used only to rule out a
September analogue).

## Kill-thesis record

**Verdict: FLAWED** — conditions=5 (1 probable, 4 plausible), refuted=1,
unknown=0, pending=2, not_obtained=0. The refutation is unchanged from the
prior run: condition 3. Management's own Q2 26 segment figures (Aug-25 Q&A
#6) show Direct AOI margin 45.2% vs 46.0% and PitchBook 30.3% vs 31.7%. No
disclosure since has contradicted them. The thesis is repairable, not dead.
A single Q3 print showing YoY expansion would clear the refutation, and
the date is fixed (2026-10-28). The rate move is not counted as a
condition. It is a §4 scenario input. The condition it hides ("the finding
row clears the hurdle by more than its error") is what §1's PASS rests on.

**Per-condition adjudication.**

1. Renewal ≥100% at Direct and PitchBook — **PENDING 2027-02-15** (FY2026
   10-K). Attacked with today's evidence: the trend is adverse (PitchBook
   108%→103%), Direct licences are −0.6% YoY, and management has flagged
   the metric as possibly "less meaningful" (Aug-25 Q&A #6). That is
   direction, not a level below 100%, so it is not refuted. If the table is
   withdrawn without a substitute, this becomes UNKNOWN, and §5 carries
   that as a Break.
2. Consolidated operating leverage positive — **SURVIVED** (probable).
   Revenue +9.3%, operating income +27.2%. Working capital nets only
   +$21.9M against $646.9M OCF (prior run's check, base unchanged). The
   attack that it is mix-driven lands on condition 3, not on this one.
3. Segment margins stop compressing — **REFUTED** for the trailing period
   (cited above). Next test 2026-10-28.
4. SBC-deducted FCF is a fair owner's flow — **SURVIVED** at plausible.
   Attacked on acquisitions: TTM revenue growth includes CRSP, but the
   finding row's 6.5% path is below the ~8.2% organic ex-sunset rate. It is
   an organic-only path, so excluding acquisition spend is the consistent
   half of Phase 4's exclusive-or. Attacked on internal consistency: 6.5%
   growth on 17.9% reinvestment implies ~36% returns on new capital in the
   explicit years (§4 bullet). That partly lands, mitigated by expensed
   reinvestment, and does not refute the flow figure itself.
5. Credit private-market growth persists — **PENDING 2026-10-28**. No
   evidence today stands against it. No ratings-revenue disclosure has come
   since Q2, and the September Q&A is silent. The ~25% private-market share
   (Aug-25 Q&A #11) is cyclical exposure, not a refutation.

**Standing checks.**

- *Base rate.* ~29% of firms earn above their cost of capital (Damodaran
  EVA dataset). MORN is in that group today (ROIC 18.24% vs WACC 8.21%),
  but every gross-FCF row assumes persistence. The finding row's 13.19%
  terminal ROE is a fade toward the hurdle, which is the base-rate-consistent
  construction.
- *The short case, strongest version.* The whole financial-data group is
  being de-rated together (MORN −12.5%, FDS −12.9%, SPGI −12.3% in a month
  with SPY +1.0%). The market is re-pricing seat-licensed information
  businesses as AI collapses the cost of structuring data. MORN's two core
  segments already show margin compression and a shrinking Direct seat
  count, and real yields are rising against long-duration cash flows. RSI
  is 35.9 and the price is below the 50-day ($201.46) but above the 200-day
  ($186.23 — about to be breached). Short interest is 7.33% of float. A
  short sees momentum, factor and rates all aligned, with the one
  company-specific catalyst (Q3) testing a condition that last printed
  against the bull.
- *Management incentives.* Founder ~37%, insiders ~48%. The strongest
  alignment against value destruction, and the September Form 4 is an
  intra-family GRAT distribution, not selling. The counter-cut stands from
  the prior run: a controlling owner running written-only Q&A faces less
  pressure to keep inconvenient disclosures.
- *Disconfirming search.* Run: one web search for downgrades, target cuts
  or PitchBook competition dated September 2026 returned only 2024–25
  items (a Redburn downgrade on licence-growth deceleration, a UBS target
  cut). That is old bear evidence, already absorbed in the prior theses'
  conditions. There is nothing new against, and nothing new for. A search
  for the September sector trigger (§3 dead end a) also came back empty.
- *Moat as mechanism.* Unchanged. It passes on DBRS NRSRO licensure and
  PitchBook's platform-exclusive IP. It fails on Direct desktop, where
  seats are shrinking against Bloomberg/LSEG/FactSet/Capital IQ.

**Statistical checks: N/A.** No backtest, screen or repo signal is
load-bearing (composite: zero signals, 0.0 coverage).

**Options timing check: DID NOT FIRE.** The thesis states no dated move
requirement. Coverage: path 2 only (not in the CBOE catalog), liquidity gate
FAILED (OI 0/1, ~35% spreads). These marks could not have moved a verdict.

**Falsifier check: passes.** §5 names Break/Shift falsifiers both ways, a
restated price level ($179) that accounts for the hurdle move, and a dated
reopen.

**Closest attack:** the hurdle-vintage attack (§1), which cuts *against the
PASS*. A September in which SPY rose and the 10-year rose 49 bp
mechanically lowers the October implied ERP, and a vintage-consistent
8.97–9.06% hurdle puts the finding row at +91 to +100 bp, past the 70 bp
bar. It does not land today because the October ERP is unpublished, and
the mature-company companion (9.74%, +23 bp) bounds the other side. It is
the attack most likely to flip the ownership call within the month.

**Flip evidence.** → **SOUND:** the Q3 print (2026-10-28) shows Direct and
PitchBook AOI margins expanding YoY, which repairs condition 3, with
condition 5's Credit growth intact. → **worse / still FLAWED:** a second
quarter of segment compression, or the renewal table withdrawn in the
FY2026 10-K. → **BUY** (orthogonal to the label): price ≤ ~$179 at a 9.46%
hurdle, or the October ERP ≤ ~3.75%.

**p(beat SPY, 63 td): 0.45**. Written before re-reading §1's line. The
63-day window contains the Q3 print, which tests the refuted condition, and
the group's momentum is negative. The valuation edge (~+50 bp a year)
is far too small to show up in one quarter against a 42% IV.
