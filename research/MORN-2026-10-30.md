# MORN — Morningstar, Inc. — 2026-10-30 (reopen of 2026-10-03, trigger: morn-q3-print-direct-and-pitchbook-aoi-margins-expand-yoy-or-price-at-or-below-179-at-9.46-hurdle-or-oct-erp-at-or-below-3.75)

> [!IMPORTANT]
> **In one sentence:** Morningstar's Q3 print was strong where it counted — Direct margins repaired, Credit up 18% — but the stock rose 23% in the month and now prices about 0.75 points less than its cost of equity after stock compensation, so pass at this price.

Price $226.07 (last regular-session trade, 2026-10-30; prior close $222.54) ·
market cap $8,388.2M · next earnings 2027-02-11 AMC (Robinhood, not yet
verified; `earnings.db` edgar-estimate 2027-01-27)

**Reopen block.** Prior file: `research/MORN-2026-10-03.md` — verdict FLAWED,
ownership call **PASS at $183.61**. Three-way trigger: (a) the Q3 26 print
shows Direct *and* PitchBook AOI margins expanding YoY, or (b) price at or
below ~$179 at a 9.46% hurdle, or (c) Damodaran's 2026-10-01 ERP at or below
3.75%. The reopen question: did any leg fire, and does the print flip the
call? MORN is a held position (journaled buy 2026-07-31; 0.0515 sh in
`portfolio.db`, snapshot 2026-10-29).

## 0. The reopen question, answered first

**HALF-TRIGGERED, and the call does not flip — it moves further from a buy.**
Leg (a) fired on Direct and failed on PitchBook. Direct Platform AOI margin
was 46.8% against 44.4% (+2.4 pp); PitchBook was 29.8% against 31.3% (−1.5
pp), its second consecutive compression quarter (nine months −1.7 pp). Leg
(b) went the wrong way: the stock closed $183.55 on 10/2 and trades $226.07
today, +23.2%. Leg (c) did not fire: the October 1 implied ERP printed
**4.20%**, up from 4.14%, not down to 3.75%. The prior run's closest attack —
that a flat September index and a higher T-bond would mechanically shrink
the ERP — did not land; Damodaran solved October against a 5.29% T-bond and
the premium rose 6 bp.

The hurdle did fall, but not by enough to matter: `DGS10` 5.24% → 5.05%
(2026-10-28), beta 1.022, ERP 4.20%, so 9.46% → **9.34%**. The price rose
23%. On the prior run's own finding row (SBC deducted, 6.5% flat, breakeven
terminal) the spread went from **+51 bp to −75 bp**. The print was good; the
market priced it and then some. At today's hurdle the finding row clears
zero at about **$202** and clears the +70 bp bar at about **$183** — which is
where the stock was when the prior run passed on it.

The move is again a group move. 10/2 → 10/30 closes: MORN +23.2%, FDS
+24.0%, SPGI +20.8%, MSCI +16.4%, MCO +11.9%, SPY −1.8% (Robinhood daily
bars). The September de-rating of the financial-data group reversed in
October, before and after the print. On the print day itself (10/28 AMC →
10/29 session) MORN rose 3.6% against SPY −0.4%, FDS +2.4%, SPGI +2.5%, MCO
+2.4%, MSCI +2.3%. MORN's idiosyncratic reaction to its own quarter was
about a point.

| prior falsifier | actual | status |
|---|---|---|
| Shift — price ≤ ~$179 at 9.46% hurdle | $226.07; hurdle 9.34%; finding row −75 bp | **NOT TRIGGERED** (moved away) |
| Shift — Oct-1 ERP ≤ ~3.75% with DGS10 ~5.2% | ERP 4.20% (T-bond 5.29%); DGS10 5.05% | **NOT TRIGGERED** |
| Shift — Q3 Direct and PitchBook AOI margins expand YoY | Direct 46.8% vs 44.4% (+2.4 pp); PitchBook 29.8% vs 31.3% (−1.5 pp) | **HALF-TRIGGERED** |
| Shift — licence and renewal tables kept, Direct licences growing | Licence table kept; Direct 18,814 vs 18,771 (+0.2%, "relatively flat"); PitchBook user count redefined to include connector-only users, "not directly comparable" | **GRAZED** |
| Shift — disclosed, quantified MCP/LLM licensing revenue | None. 13M cumulative connector tool calls, 28% of Direct and PitchBook clients on MCP, no dollars | **NOT TRIGGERED** |
| Break — Direct/PitchBook renewal < 100% (FY2026 10-K) | ~Feb 2027 | **NOT TRIGGERED** (pending) |
| Break — renewal table withdrawn without substitute | No 10-K yet. Cousin event: PitchBook licensed-user metric redefined at the quarter churn rose | **NOT TRIGGERED** (watch) |
| Shift — Direct licences −2%+ YoY two quarters | +0.2% | **NOT TRIGGERED** |
| Shift — second quarter of Direct *and* PitchBook compression without consolidated leverage | PitchBook second quarter, yes; Direct repaired; consolidated OI +31.0% on revenue +8.9% | **HALF-TRIGGERED** (PitchBook only) |
| Shift — Credit revenue −20%+ | Credit +18.3%, AOI +44.5% | **NOT TRIGGERED** |
| Break — levered acquisition > ~$1B outside core | None; no 8-K Item 1.01/2.01 since 10/3 | **NOT TRIGGERED** |
| Shift — DGS10 sustained above ~5.6% | 5.05% | **NOT TRIGGERED** |

## 1. Verdict and thesis

**PASS at $226.07.** kill-thesis: **FLAWED** — conditions=6 (2 probable,
4 plausible), refuted=2, unknown=0, pending=1, not_obtained=0.

> [!IMPORTANT]
> **p(beat SPY, 63 td): 0.45** · kill-thesis: 0.42
>
> **Disputed expectation:** after stock compensation, the price implies 8.59%
> a year on 6.5% growth and a 2.35% terminal — 75 bp *under* a 9.34% cost of
> equity, and under it on every SBC-deducted path up to 9% growth. The market
> is paying for the Q3 operating leverage (OI +31% on revenue +9%) to repeat
> and for PitchBook to stop shrinking its margin. The Q4 print (2027-02-11,
> tentative) and the FY2026 10-K renewal table are what revise it.

The business is better than it was a month ago, and the stock is worse. The
quarter repaired the one condition the prior two runs had refuted — Direct
margins — and showed Credit still compounding at 18% with a 37.7% margin.
But PitchBook compressed again on corporate and VC churn, its licensed-user
metric was redefined in the same quarter, and the price moved 23% on a
4-percent-ish idiosyncratic read plus a group re-rating. For an owner, no
sell falsifier fired: the held sliver stays on the §5 owner list. For a
buyer at $226, the price already assumes the demonstrated growth path and
leaves nothing over the hurdle.

> [!WARNING]
> **Closest attack:** the gross-FCF attack, which argues the pass is
> mis-measured. On reported FCF ($492.8M, SBC not deducted) the demonstrated
> path prints 9.74%, +40 bp over the hurdle, and 6.5% flat prints +17 bp.
> Both are inside the hurdle's own error band, and both fail the terminal
> reinvestment check (FCF above cash earnings, so the terminal growth is
> paid for by nothing). The attack lands only if SBC is not a cost; at 2.5%
> of revenue it is small, and that is exactly why the two readings sit only
> 1.1 points apart. The pass survives because the honest base is the
> SBC-deducted one and it is 75 bp short.

**Load-bearing conditions of the bull case (6).** MCP/LLM distribution
monetising stays *possible* tier — option value in §6, not a condition.

1. *plausible* — **Renewal rates hold ≥100% at Direct and PitchBook through
   the AI transition.** FY2025 10-K: Data 101%, Direct ~104%, PitchBook ~103%
   (from 108%). Settles in the FY2026 10-K, ~Feb 2027. Direct licences +0.2%
   this quarter with revenue per licence up; PitchBook churn "higher" in
   corporate and VC (10-Q).
2. *probable* — **Consolidated operating leverage stays positive.** Q3: revenue
   +8.9%, operating income +31.0%; TTM to Q3 26 vs TTM to Q3 25: revenue
   +9.4%, operating income +31.2%. Headcount 10,610, −4.9% YoY, with the
   quarter's opex +3.0%.
3. *plausible, refuted on the PitchBook half* — **Direct and PitchBook
   segment AOI margins stop compressing.** Direct repaired (+2.4 pp). PitchBook
   29.8% vs 31.3%, second straight quarter, nine months −1.7 pp. Next reading:
   Q4 print, 2027-02-11 (tentative); the Nov 25 investor Q&A may explain it.
4. *plausible* — **SBC-deducted levered FCF ($427.8M) is a fair owner's
   flow.** TTM FCF $492.8M less $65.0M SBC run-rate. Q3 FCF −2.9% YoY on
   working capital; TTM conversion 70.6% of adjusted OI. Still excludes
   acquisition spend (CRSP $359.6M cash in Q1). Settles with the FY2026
   cash-flow statement.
5. *probable* — **Credit's private-market ratings growth persists.** Q3 Credit
   revenue +18.3%, AOI +44.5%, new-issuance transaction revenue +28.5%,
   unpublished (private) ratings ~30% of ratings revenue (CEO letter). The
   evidence is current; the risk is the cycle, and the CEO's own reading list
   this quarter is headed "Growing signs of stress in private credit."
6. *refuted* — **The price clears the cost of equity on the stated path.** The
   finding row is −75 bp at $226.07; the demonstrated-growth row −56 bp; 9%
   flat −8 bp. Clears zero at ~$202. This is the condition the pass rests on.

> [!WARNING]
> **Dominant shared risk factor:** generative-AI substitution of paid
> information and knowledge-work subscriptions sold to enterprises — shared by
> 3 of 25 other held names (INTU "generative-AI substitution of paid
> software/services workflows"; SAP "enterprise application seat-and-workflow
> spend displaced by AI agents"; G "AI-driven deflation in labour-arbitrage
> knowledge services") · 0 unlabelled. `portfolio.db` was readable this
> session: 26 symbols in `v_latest_positions` (snapshot 2026-10-29), MORN
> included, every other holding with a thesis carrying a factor line.

## 2. Business

Unchanged from `research/MORN-2026-07-30.md` §2 and the deltas in the
2026-09-01 and 2026-10-03 runs. Value is created through curated investment
data across funds, private markets, credit and indexes; captured through
per-seat and enterprise licences (moving to value- and consumption-based
pricing), issuance-linked ratings fees, AUM basis points and index licensing;
protected by DBRS's NRSRO licensure, the analyst-built private-markets
dataset, and index switching costs. Deltas this run:

**Created:** Direct AI launched 2026-10-07 — ~3,500 users logged in, 86% ran
a query or agent, 42,000+ prompts (CEO letter). PitchBook's Data Premium
Connector passed 13M cumulative tool calls in October from 1M in July; 28% of
PitchBook clients and 28% of Direct clients with a licence have used an MCP
offering. The AGM (May) framed the design: "Our objective is to ensure that AI
models reason through Morningstar's frameworks." The Sustainalytics test in
the letter — an LLM on public sources found emissions data for 12–15% of
sampled companies and product involvement for under 1% — is management's
argument that the data is not scrapeable.

**Captured:** Direct revenue +5.4% (6.2% organic) on flat licences, so the
capture mechanism this quarter was price per licence, not seats; "roughly
half of Direct Platform's 2025 revenue was driven by Morningstar Data"
(AGM). PitchBook +3.9% (4.0% organic) with "particular softness in the
corporate and venture capital client segments, which continued to
experience higher churn" (10-Q); at the AGM, 10% of customers were
firm-wide (non-seat) and those represent ~40% of users, and an "MCP-only
product… priced separately" was in development. Credit revenue is 94%
transaction-based ($101.4M of $107.8M): new-issuance +28.5%, recurring
surveillance +0.5%. Remaining performance obligations ~$1.7B (25% rest of
2026, 49% in 2027, 17% in 2028).

**Protected:** no new evidence either way on the mechanisms. One disclosure
change cuts the wrong way: the PitchBook licensed-user count now includes
standalone connector users after "a large renewal," and the company says
the count "is not directly comparable to prior periods" — in the quarter
platform growth slowed. The CEO calls it "a small change." It is the
metric the prior theses watched for seat erosion.

**Control:** unchanged. Founder Joseph D. Mansueto ~37%; insiders 48.28%;
float 19.58M of 37.10M shares out; one share class. The structure forecloses
an unsolicited takeover and any activist path. BlackRock's 13G/A (filed
2026-10-27, event 2026-09-30) reports 1,821,367 shares, 4.9%. No Form 4 has
been filed since the 2026-10-02 Daniel Mansueto GRAT distribution; the
August 10b5-1 cadence from the 0001324069 filer stopped on 8/24 — consistent
with a pre-print blackout, and worth re-reading in November.

**Operating leverage (Phase 0): positive at the consolidated line; positive
at Direct this quarter; negative at PitchBook for a second quarter.**

| | revenue | operating income | op margin |
|---|---|---|---|
| FY2021 | $1,699.3M | $257.0M | 15.1% |
| FY2023 | $2,038.6M | $230.6M | 11.3% |
| FY2025 | $2,445.5M | $506.2M | 20.7% |
| TTM to Q3 2025 | $2,395.4M | $469.9M | 19.6% |
| TTM to Q3 2026 | $2,621.2M | $616.7M | 23.5% |

TTM revenue +9.4% against operating income +31.2%. Q3 alone: revenue
+8.9%, operating income +31.0%, operating margin 24.9% from 20.7%. The
leverage is mix (Credit, Retirement, retired loss-making products) plus
flat headcount; it is not coming from the two largest segments equally.

## 3. Threads pulled

- **The print against the trigger (load-bearing).** Revenue $672.1M, +8.9%
  reported, 6.8% organic, 7.8% ex-sunset (Morningstar Office and
  second-party opinions). Adjusted OI $189.9M, +26.1%, margin 28.3% (+3.9
  pp). Adjusted EPS $3.48 vs $3.04 consensus, +14.5%; GAAP diluted $3.06,
  +41.0%. Segment AOI margins: Direct 46.8% (44.4%), PitchBook 29.8%
  (31.3%), Credit 37.7% (30.8%), Wealth 12.5% (5.0%), Retirement 57.1%
  (49.4%). Direct's repair is real: AOI +11.2% on revenue +5.4%. PitchBook's
  compression is also real: AOI −1.1% on revenue +3.9%, and the 10-Q gives
  no cause beyond the churn sentence. Severance +$6.9M YoY, technology
  costs up for cloud and AI, bonus expense down.
- **The price leg: group again, not MORN.** Table in §0. MORN's beta to the
  financial-data group carried the month; the print-day residual was about
  +1 point. RSI 66.1, price above the 50-day ($205.90) and 200-day
  ($185.71). Short interest 1.24M, 6.35% of float, down from 1.42M.
- **PitchBook, pulled further.** AGM (May 2026): "organic growth has
  slowed"; churn concentrated in "single-use cases"; corporate softness in
  non-M&A use cases, venture book soft; non-backed company coverage to
  double to 20M by year-end; firm-wide licences and an MCP-only SKU as the
  pricing answer. Q3: revenue +3.9%, users +4.6% *including* connector-only
  users from one large renewal, so organic seat growth is below 4.6% and
  unquantified. The margin fell for the second quarter while AI engineering
  spend rose ("code committed at a 4x greater pace"). This is a segment
  re-pricing its product under churn; the margin is the cost of that.
- **Credit, pulled further.** 59.6% structured finance, 34.4% fundamental,
  6.0% data licensing. New issuance +28.5% against surveillance +0.5%: the
  growth is almost entirely issuance-linked, i.e. cyclical. The CEO letter
  cites surging private-credit issuance for energy infrastructure and
  "hybrid public-private financings" by non-data-center corporates, and
  lists "Growing signs of stress in private credit" among his reading
  without comment. Condition 5 is probable on the quarter and exposed on the
  cycle.
- **Cash flow and the balance sheet.** Q3 FCF $155.4M, −2.9% on working
  capital (unearned revenue −$25.6M, receivables −$43.1M); YTD FCF $331.5M,
  +17.8%. TTM FCF $492.8M vs $497.5M last run. Total debt $1,678.7M
  (revolver $590.0M drawn, $160.0M available; A-1 $365.6M; A-2 $375.0M,
  three-year from Oct 2025; 2.32% notes $349.2M due 2030); covenant
  leverage 1.8x; cash and investments $524.6M. Q3 buyback $100.0M for
  486,573 shares, an average **$205.5** — up from $177.7 in Q2 and $175.8 in
  Q1. The CEO: "buying back stock at a price we believe is discounted."
  Shares −8.6% YoY. The buyback is funded with revolver draws at ~SOFR +
  1.05–1.425%; at 1.8x that is fine, and it is still return redistribution,
  not return creation.
- **Earnings pattern.** Seven straight adjusted-EPS beats: Q1 25 +8.3%, Q2 25
  +9.6%, Q3 25 +5.4%, Q4 25 +14.8%, Q1 26 +19.5%, Q2 26 +9.9%, Q3 26 +14.5%
  (Robinhood). Not hair-thin; consensus (3 analysts) undershoots. Actuals
  are adjusted, not GAAP: Q3 GAAP diluted $3.06 (10-Q) vs $3.48. The Q4 26
  estimate is $3.07, below Q3's $3.48 — an easy bar or a Q4 seasonal, not
  checked. `sec_fundamentals.db` still carries Q2's $2.83; the Q3 10-Q
  (2026-10-28) had not been ingested at run time.
- **The rate and ERP leg.** `DGS10` 5.24% (10/1) → 5.05% (10/28); `T10YIE`
  2.36% → 2.35% (10/29). Damodaran Oct-1 ERP 4.20% against a 5.29% T-bond
  (September's 4.14% against 4.75%). The recipe hurdle fell 12 bp to 9.34%;
  a vintage-consistent hurdle (5.29% + 1.022 × 4.20%) is 9.58%, *higher*
  than the recipe's. The prior run's vintage attack is dead this month.
- **EDGAR post-call sweep.** Filings since 2026-10-03: Form 3/4 (10/2,
  Daniel Mansueto GRAT), 13G/A (10/27, BlackRock 4.9%), 10-Q and 8-K (10/28:
  press release, CEO letter, supplemental). No Item 1.01/2.01/5.02. 10-Q
  Item 1A: "no material changes" other than as provided; legal: normal
  course, no accrual named. Next dated disclosures: investor questions close
  2026-11-05, 8-K response targeted 2026-11-25.
- **Options read (mandatory):** path 2 (Robinhood stopgap) only; MORN is not
  in the CBOE catalog. Liquidity gate **FAILED → UNRELIABLE** on both
  expiries. Table in §4.
- **Dead ends:** (a) no sell-side or press coverage of the 10/29 move was
  found (one web search returned only the filings and a wire summary).
  (b) The 10-Q does not explain the PitchBook margin; the Nov 25 Q&A is the
  next chance. (c) The remaining repurchase authorization is not stated in
  the 10-Q text; the AGM cited a $1B programme from fall 2025 with $500M
  used YTD. (d) Transcript corpus: 7 rows, all AGMs (2021–2026), no
  quarterly calls — by design; the 2026 AGM was read to ~100k of 177k
  characters, the StepStone/PitchBook Q&A tail not. (e) `composite.db`:
  zero signals, 0.0 coverage, `in_portfolio=1` — expected.

## 4. Valuation

**Inputs.** Levered TTM FCF **$492.8M** (operating cash flow $641.9M − capex
$149.1M; live statistics page, updated for Q3) against **market cap
$8,388.2M** (37,104,311 shares, 10-Q cover 2026-10-23, × $226.07). Net debt
is 0 by the pairing rule: the flow is post-interest ($24.2M cash interest in
Q3), so EV ($9.73B) would double-count the $1.68B of debt. No minority
interests. Cash $524.6M is 6.3% of market cap; no excess-cash adjustment.
SBC run-rate **$65.0M** (four quarters: 16.6 + 27.3 + 10.8 + 10.3; 2.48% of
revenue), deducted in the finding row to **$427.8M**. Cash earnings for the
reinvestment check: net income $445.5M + ~$75M acquired-intangible
amortisation (9M26 $59.1M per the 10-Q, Q4 25 ~$15M) ≈ **$520M**.

**Hurdle:** rf 5.05% (`DGS10`, 2026-10-28) + beta 1.022 × ERP 4.20%
(Damodaran implied ERP as of 2026-10-01, solved against a 5.29% T-bond) =
**9.34%**. Beta inside the 0.8–1.2 band; insiders at 48% trip the thin-float
warning but that floors a sub-band beta only. Mature-company companion rf +
4.5% = 9.55%. Vintage-consistent alternative 9.58%. US ERP: about a quarter
of revenue is non-US, developed markets, tens of bp at most.

**Terminal-growth ceiling:** 10-year breakeven `T10YIE` **2.35%**
(2026-10-29).

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| gross FCF, demonstrated growth | $492.8M | 8/8/7/7/6% | 2.35% | 9.74% | **+40 bp** |
| gross FCF, conservative | $492.8M | 6.5% flat | 2.35% | 9.52% | **+17 bp** |
| SBC deducted, demonstrated growth | $427.8M | 8/8/7/7/6% | 2.35% | 8.79% | **−56 bp** |
| **SBC deducted, conservative (finding row)** | **$427.8M** | **6.5% flat** | **2.35%** | **8.59%** | **−75 bp** |
| SBC deducted, 9% flat (bull) | $427.8M | 9% flat | 2.35% | 9.26% | **−8 bp** |
| same as finding, prior run's 2.0% terminal | $427.8M | 6.5% flat | 2.00% | 8.31% | **−103 bp** |
| terminal real-growth stress | $492.8M | 5% flat | 1.0% | 8.04% | **−130 bp** |
| acquisition charged ($150M/yr) | $342.8M | 8/8/7/7/6% | 2.35% | 7.53% | **−182 bp** |
| AI-decay stress | $492.8M | 4/3/2/1/0% | 0.0% | 6.45% | **−290 bp** |

**The bolded row is the finding.** Against the mature-company companion
(9.55%) it is −96 bp; against the vintage-consistent 9.58%, −99 bp. Only the
two gross-FCF rows clear the hurdle and both trip the tool's
`growth without reinvestment` warning (FCF ≥ earnings). **Flip price at
today's hurdle: ~$202** (market cap $7.50B, −3 bp); the +70 bp bar the prior
runs used sits at **~$183** ($6.80B). Last run the stock was at $183.61 and
the same row read +51 bp; the 23% move cost 126 bp of spread against a 12 bp
hurdle cut.

ATM IV is 39.9–40.6%, under the 50% precision trigger; two decimals are
admissible. The spread is the finding.

**Integrity checks.**

- *Reinvestment / terminal ROE: answered.* On the SBC-deducted base
  ($427.8M against ~$520M cash earnings) the reinvestment rate is 17.8% and
  the implied terminal ROE is **13.24%** — 3.9 points above the 9.34%
  hurdle, inside Damodaran's ~5-point band and below the 19.44% ROIC the
  statistics page prints. The gross rows fail the check (reinvestment rate
  −10.6%): their terminal growth is unfunded, which is why they are not the
  finding despite clearing the hurdle.
- *Market-share sentence.* 6.5% for five years puts 2031 revenue at about
  $3.59B, an increment of ~$0.97B against a competitive set (Bloomberg,
  LSEG, FactSet at ~$2.4B, S&P Capital IQ, the ratings majors) many times
  Morningstar's size. No implausible share is needed; the pass is not about
  growth feasibility.
- *Terminal growth vs Item 1A.* 10-Q Item 1A: no material changes from the
  FY2025 10-K, whose dominant structural risk (per the 2026-07-30 run) is AI
  scraping and free substitution of paid information. A 2.35% terminal is
  nominal inflation with zero real growth; it survives only if the
  non-scrapeable legs (NRSRO, analyst-built private data, indexes) carry the
  terminal flow. The AI-decay row is the run where they do not.
- *Base-year cash tax.* Nine-month cash taxes paid $126.2M against $111.3M
  expense; effective rate 25.0% (Q3) against a mid-20s marginal. No NOL
  flattery; no haircut.
- *Serial acquirer.* CRSP ($363.0M, Feb 2026) sits inside the TTM; organic
  growth 6.8% is what the finding row's 6.5% tracks, so excluding acquisition
  spend is the consistent half. The charged row shows the cost of assuming
  deals continue.
- *Distribution clamp.* Rows span 6.45%–9.74%. The finding row (8.59%) sits
  inside the 5.26–9.88% band holding 80% of US firms and above the 7.79%
  median. Not a strong pass on distribution grounds; a plain one on the
  spread.
- *No leverage gate.* Net debt $1.33B against EV $9.73B is 13.7%, covenant
  leverage 1.8x; the equity-as-option lens is not run.

**Options-implied move.** Path 2 only. Two expiries read: **2027-03-19, 140
DTE**, $230 strike (nearest listed to spot; no $225), which brackets the
tentative Q4 print (2027-02-11) and the FY2026 10-K; and **2026-12-18, 49
DTE**, $230, which brackets the 2026-11-25 investor Q&A. March IV is the
mean of the call's 40.14% and the put's 39.58%; marks $22.25 / $22.40.
December IV is the mean of 40.90% and 40.30%; marks $12.30 / $14.80.

| metric | 2027-03-19 (140 DTE) | 2026-12-18 (49 DTE) |
|---|---|---|
| spot | 226.07 | 226.07 |
| ATM IV | 39.86% | 40.60% |
| expected absolute move (MEAN, not a ceiling) | 19.75% | 11.99% |
| 1-sigma move | 24.69% | 14.88% |
| RV60 | 35.95% | 35.95% |
| IV > RV60? | YES | YES |
| RV20 | 36.79% | 36.79% |
| IV > RV20? | YES | YES |

**Liquidity gate FAILED → UNRELIABLE** on both: open interest 5/1 (March)
and 14/0 (December), volume 0 and 1/0, bid/ask spreads $4.50–$4.80 on
$12–22 marks (20–36%). Read as shape only: IV sits 3–5 points above both
realised windows, which themselves contain the print day. The flip price
($202) is −11.3% in log terms, under half a sigma on the March tenor — a
distance, not evidence. **Timing check: NOT APPLICABLE.** The thesis states
no dated move requirement.

## 5. Falsifiers

**For the pass (flip toward buy):**

- **Shift —** price at or below ~$202 with the TTM base and today's 9.34%
  hurdle unchanged (finding row at zero); ~$183 for the +70 bp bar.
- **Shift —** the Q4 26 print (2027-02-11, tentative) shows PitchBook AOI
  margin expanding YoY with Direct still expanding — condition 3 repaired on
  both halves.
- **Shift —** the FY2026 10-K keeps the renewal table with Direct and
  PitchBook at or above 100%, and discloses an organic PitchBook user count
  (ex-connector) that is growing.
- **Shift —** a disclosed, quantified MCP/LLM licensing revenue line (the
  AGM's "priced separately" MCP-only SKU showing up as dollars).
- **Shift —** `DGS10` at or below ~4.6% with the ERP unchanged (hurdle ≤
  ~8.9%; the finding row clears at today's price).

**For an owner (sell):**

- **Break —** Direct or PitchBook revenue renewal rate below 100% in the
  FY2026 10-K (~Feb 2027).
- **Break —** the renewal table withdrawn without a comparable substitute.
  The PitchBook user redefinition is the warning shot; a second
  redefinition or the table's removal is the Break.
- **Shift —** Direct licences down more than 2% YoY for two consecutive
  quarters (Q3 26: +0.2%).
- **Shift —** a third consecutive quarter of PitchBook AOI margin compression
  at the Q4 print *with* PitchBook revenue growth below 3%.
- **Shift —** Credit new-issuance transaction revenue down 20%+ YoY in a
  quarter without surveillance offsetting — the private-credit cycle turning.
- **Break —** a levered acquisition above ~$1B outside data, ratings or
  indexes (revolver has $160M headroom; a deal that size is new debt).
- **Shift —** `DGS10` sustained above ~5.6%.

> [!NOTE]
> **Reopen trigger:** 2027-02-26: morn-fy26-10k-direct-and-pitchbook-renewal-at-or-above-100-and-q4-pitchbook-aoi-margin-expands-yoy-or-price-at-or-below-202-at-9.34-hurdle

## 6. UNKNOWNs

1. **PENDING 2026-11-25** — management's explanation of the PitchBook margin
   decline and of the user-metric redefinition (investor Q&A 8-K; questions
   close 2026-11-05). The 10-Q gives only the churn sentence. Not fatal; it
   decides whether condition 3's PitchBook half is a pricing transition or a
   structural loss.
2. **PENDING 2027-02-11 (tentative)** — Q4 26 PitchBook and Direct AOI
   margins, Credit issuance. Settles condition 3's trend.
3. **PENDING ~2027-02-26** — FY2026 renewal-rate table and whether it
   survives (Aug-25 Q&A #6 flagged it as possibly "less meaningful").
   Settles condition 1. Withdrawal without substitute is a §5 Break.
4. **UNKNOWN** — organic PitchBook licensed-user growth ex-connector users.
   The redefinition means the +4.6% cannot be decomposed from any filing.
   Bounded: below 4.6%; the sign is not disclosed.
5. **UNKNOWN** — Indexes/CRSP economics. Below ASC 280 thresholds; Indexes
   revenue $39.0M in Q3 (+78.9% reported, +11.8% organic). Bounded ~6% of
   revenue. Not fatal.
6. **UNKNOWN (option value, *possible* tier)** — MCP/LLM licensing revenue.
   Usage metrics are now disclosed (13M tool calls, 28% client adoption); no
   dollars. Not a base-case input.
7. **NOT OBTAINED** — the final ~77k characters of the 2026 AGM transcript
   (StepStone/PitchBook Q&A) and the remaining repurchase authorization
   figure. Neither bears on the call.

## 7. Sources

**Primary:** SEC EDGAR, read this session. `cgi-bin/browse-edgar` atom
filing list for CIK 1289419. 8-K 0001289419-26-000056 (filed 2026-10-28):
Exhibit 99.1 press release (`exhibit991-pressrelease_09.htm`), CEO
shareholder letter (`morningstarq32026ceolett.htm`), supplemental deck
(`morningstarq32026supplem.htm`) — segment table, licence counts, Credit
mix, FCF reconciliation, debt and leverage. 10-Q 0001289419-26-000054
(`morn-20260930.htm`, downloaded raw and grepped): cover share count, Note 3
debt, CRSP purchase accounting, Note 6 RPO, Item 1A, legal, churn and
licence sentences, nine-month SBC/amortisation/cash taxes. 13G/A
0002012383-26-003928 (BlackRock, 2026-09-30). The FY2025 10-K renewal table
and Item 1A, and the Aug-25 investor Q&A (#6, #11, #22–24), are carried from
the 2026-07-30 / 09-01 / 10-03 runs as point-in-time citations.

**stockanalysis.com (vetted exception):** `/stocks/MORN/statistics/` via
the `__data.json` probe (`hover` values): market cap, EV, shares, float,
insider/institution %, TTM income/cash-flow/balance-sheet lines, beta 1.022,
ROIC, SMA50/200, RSI, short interest, analyst count. `/financials/
cash-flow-statement/?p=quarterly` (quarterly SBC, FCF, buybacks, cash
taxes) and `/financials/income-statement/` (annual and quarterly revenue
and operating income for the Phase 0 table). `/transcripts/` index (7 AGM
rows) and the 2026 AGM transcript (primary-transcribed; read to ~100k
characters).

**Broker/market microstructure:** Robinhood MCP. Quotes for MORN, SPY, FDS,
SPGI, MCO, MSCI (2026-10-30 session close); daily bars 2026-06-22 →
2026-10-29 for the peer table and the RV windows (92 MORN closes);
trailing-8-quarter estimate-vs-actual EPS; option chain, instruments and
quotes for the 2027-03-19 and 2026-12-18 $230 straddles. Admissible: no
integrated official source covers real-time quotes, option marks or
consensus estimates for this ticker.

**Reference data:** Damodaran NYU Stern home page, fetched 2026-10-30:
implied ERP 4.20% as of 2026-10-01 against a 5.29% T-bond; September's
4.14% / 4.75% for the vintage comparison. Terminal-ROE band, mature-company
companion and distribution clamps via `references/damodaran-anchors.md`.

**Point-in-time repo DBs:** `data/fred.db` (DGS10 5.05% on 2026-10-28;
T10YIE 2.35% on 2026-10-29). `data/stocks.db` (snapshot 2026-10-30: beta
1.02229, insiders 48.281%, institutions 65.79%, float 19,581,090, shares
37,104,311, SBC $65.0M, SBC/revenue 2.48%, 3 analysts, price $222.54).
`data/earnings.db` (Q3 event 2026-10-28 after close, eps_est 3.04; next
edgar-estimate 2027-01-27). `data/composite.db` (MORN zero signals,
`in_portfolio=1`, snapshot 121). `data/portfolio.db` (`v_latest_positions`,
26 symbols, snapshot 2026-10-29; MORN 0.051546 sh). `data/sec_fundamentals.db`
(`v_screener`: Q2 26 eps_diluted 2.83 — the Q3 10-Q not yet ingested).
`data/options.db` (path 1 unavailable, not in catalog).

**Low-confidence:** one web search (Q3 results coverage) — returned the
filings and a wire summary only; no price-move attribution.

## Kill-thesis record

**Verdict: FLAWED** — conditions=6 (2 probable, 4 plausible), refuted=2,
unknown=0, pending=1, not_obtained=0. Two refutations: condition 3 on its
PitchBook half (second consecutive compression quarter, management's own
segment table), and condition 6, the price-clears-hurdle condition, which
fails on every SBC-deducted path. The thesis is repairable: a Q4 PitchBook
margin expansion repairs 3, and a ~10% lower price repairs 6. Neither is
available today.

**Per-condition adjudication.**

1. Renewal ≥100% at Direct and PitchBook — **PENDING 2027-02-26** (FY2026
   10-K). Attacked with today's evidence: Direct licences +0.2% with revenue
   per licence up is consistent with ≥100% at Direct; PitchBook "higher
   churn" in corporate and VC plus a metric redefinition is adverse
   direction, not a level below 100%. Not refuted.
2. Consolidated operating leverage positive — **SURVIVED** (probable).
   Q3 OI +31.0% on revenue +8.9%; TTM +31.2% on +9.4%; headcount −4.9%.
   Attacked as one-off: severance +$6.9M and lower bonus accrual flatter the
   quarter; the nine-month figure (+31.9%) does not depend on them.
3. Segment margins stop compressing — **REFUTED on the PitchBook half**
   (29.8% vs 31.3%; nine months −1.7 pp). Direct half repaired (+2.4 pp).
   Next test 2027-02-11.
4. SBC-deducted FCF is a fair owner's flow — **SURVIVED** at plausible. Q3
   FCF −2.9% is working capital (unearned revenue and receivables), not
   earnings; TTM conversion 70.6% of adjusted OI vs 71.5% a year ago. The
   acquisition attack is answered by the charged row (−182 bp) rather than
   by the base.
5. Credit private-market growth persists — **SURVIVED** (probable on the
   period). Attacked on cyclicality: 94% transaction-based, new issuance
   +28.5% vs surveillance +0.5%, and the CEO's own reading list flags
   private-credit stress. The attack describes the risk, not a current
   refutation.
6. Price clears the hurdle on the stated path — **REFUTED**. −75 bp on the
   finding row, −56 bp demonstrated, −8 bp at 9% flat; +40/+17 bp only on
   gross FCF, which fails the reinvestment check.

**Standing checks.**

- *Base rate.* ~29% of firms earn above their cost of capital. MORN is in
  the group (ROIC 19.44% vs 8.57% WACC on the statistics page); the finding
  row's 13.24% terminal ROE is a fade toward the hurdle, the
  base-rate-consistent construction.
- *The short case, strongest version.* A seat-licensed information business
  whose second-largest segment is losing corporate and VC seats to churn and
  has just redefined the metric that would show it; whose growth engine
  (Credit) is 94% issuance-linked at a moment the CEO is reading about
  private-credit stress; trading at 19.8× trailing GAAP after a 23% month
  on a group re-rating, buying back stock with revolver draws at $205. RSI
  66. A short sees mean reversion in the factor plus one segment metric
  moving the wrong way; the bull sees Direct repaired and consolidated
  margins at a record.
- *Management incentives.* Founder ~37%, insiders ~48%: the strongest
  alignment against value destruction. The counter-cut stands: a controlling
  owner running written-only Q&A faces less pressure to keep inconvenient
  disclosures, and this quarter one metric was redefined.
- *Disconfirming search.* One web search for post-print coverage returned
  nothing beyond the filings. The 10-Q risk-factor section says no material
  changes. No bear evidence newer than the churn sentence was found; no
  bull evidence newer than the print.
- *Moat as mechanism.* Unchanged. Passes on DBRS NRSRO licensure and
  PitchBook's platform-exclusive private-markets IP; fails on Direct
  desktop seats, which are flat and monetised by price.

**Statistical checks: N/A.** No backtest, screen or repo signal is
load-bearing (composite: zero signals, 0.0 coverage).

**Options timing check: DID NOT FIRE.** No dated move requirement. Coverage:
path 2 only, liquidity gate FAILED on both expiries (OI 5/1 and 14/0,
spreads 20–36% of mark). These marks could not have moved a verdict.

**Falsifier check: passes.** §5 names Break/Shift falsifiers both ways, a
restated flip price ($202 at 9.34%), and a dated reopen (2027-02-26, the
FY2026 10-K).

> [!WARNING]
> **Closest attack:** the gross-FCF attack (§1), which puts the demonstrated
> path at +40 bp and the conservative path at +17 bp if stock compensation
> is treated as non-cash. It does not land: both rows fail the terminal
> reinvestment check, both sit inside the hurdle's error band, and at 2.5%
> of revenue the SBC deduction is small enough that the two readings differ
> by only 1.1 points — the pass holds on either base once the error band is
> respected.

> [!NOTE]
> **Flip evidence.** → **SOUND:** the Q4 26 print shows PitchBook AOI margin
> expanding YoY alongside Direct (repairs 3) *and* the price is at or below
> ~$202 at a 9.34% hurdle (repairs 6). → **worse / still FLAWED:** a third
> quarter of PitchBook compression, or the FY2026 renewal table withdrawn or
> below 100%. → **BUY** (orthogonal to the label): price ≤ ~$202 with the
> TTM base unchanged, or `DGS10` ≤ ~4.6%.

> [!IMPORTANT]
> **p(beat SPY, 63 td): 0.42**. Written before re-reading §1's line. The
> window (to ~2027-01-29) contains the Nov 25 Q&A but not the Q4 print. The
> stock enters it 23% up in a month on a group re-rating with RSI 66 and a
> −75 bp valuation spread; the print's good news is in the price. Momentum
> and the seven-beat pattern argue up, the factor reversal and the spread
> argue down, and the spread is the larger number.
