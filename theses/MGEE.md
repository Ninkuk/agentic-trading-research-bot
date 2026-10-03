# MGEE — MGE Energy — 2026-09-24

Price $68.49 (official close, 2026-09-24) · market cap $2,587,826,982 ·
next earnings 2026-11-04 AMC (broker calendar, unverified; stocks.db agrees
on the date; earnings.db carries no MGEE event) · EV $3.51B, net debt $917.7M
(context only — §4 pairs a levered flow with market cap)
Entry path: user-directed (no candidates-screen row, no composite flag above
annotation weight; composite scores it +3 on `stocks_rsi` and
`si_days_to_cover`). No prior thesis. Unattended scheduled run.

## 1. Verdict and thesis

**PASS at $68.49 (official close 2026-09-24).** kill-thesis: **FLAWED** —
conditions=6 (4 probable, 2 plausible), refuted=1, unknown=0, pending=2,
not_obtained=0.

**p(beat SPY, 63 td): 0.44** · kill-thesis: 0.43
**Disputed expectation:** the price implies ~7.1–7.5% a year on the
company's own growth path (per-share dividends +5–7% through 2030, then
payout normalising at a 9.8% ROE), 93–134bp below an 8.42% cost of equity.
The market is still pricing MGEE as a bond proxy that deserves a ~0.5 beta.
What revises it is the price reaching ~$56, the 10-year falling back well
below 5%, or the 2028 rate case pricing a higher allowed ROE.

MGE Energy is a very good small utility. It has an AA- rating, a single
constructive regulator, forward test years, a fast-growing Madison
territory, 51 straight dividend raises, and a funded capital plan that grows
rate base 12% into 2027. None of that is in dispute. The price is. The stock
fell 18.7% from its 7/2 high while the 10-year rose 67bp (4.44% → 5.11%).
Even so, every realistic path this run modelled returns less than the cost
of equity. Growth here is paid for with equity: $250M was raised in May, and
2.31M forward shares are still to settle. So the per-share compounding the
bull case needs is ~6%, not the 12% the rate-base headline suggests. This is
a quality business at a price that has not yet caught up with 5% Treasuries.

**Closest attack:** the arithmetic. Hold every operating condition true —
rate base as filed, ROE at authorized, 6–7% per-share dividend growth,
affordability intact — and the implied return still sits 93–134bp under
the hurdle. At the raw 0.70 beta it is still 72bp under (8.01% hurdle). The
base path clears the hurdle only near a $2.12B market cap (~$56/share).
That makes this a price-and-rates call, not a business call.

Load-bearing conditions (the bull case — what owning at $68.49 needs):

1. *probable* — **Rate base grows as filed.** PSCW-approved test-year rate
   base $1,721.9M (2026: electric $1,346.3M + gas $375.6M) → $1,931.5M
   (2027: $1,537.9M + $393.6M), +12.2% (Q2 2026 financial update, slide 10).
   Most Certificate-of-Authority projects are approved; Fox, Superior,
   Akron, Dawn Break, Emerald Bluffs, the Dawn Break battery and the Elm
   Road gas conversion await Q4 2026 approval (~$305M MGE share, slides
   15–16).
2. *probable* — **Earned ROE stays near the 9.8% authorized** on a ~56%
   equity layer. TTM consolidated ROE 11.04% (stockanalysis); the deck
   claims "consistently earning an ROE near authorized levels".
3. *plausible* — **Per-share dividend/EPS growth of ~6% net of the forward
   settlement.** 2,310,232 forward shares at $72.9094 (~$168.4M) dilute
   ~6.1% at settlement. 2026 consensus EPS $3.97 (+6.6% on $3.72) sits
   *below* TTM $4.07 (stockanalysis forecast). Settled by the Q3 10-Q
   (2026-11-04: settlement status, run-rate EPS) and the FY2026 release.
4. *plausible* — **The next rate case lifts the allowed return toward the
   rate environment.** The 9.8% ROE was set in the 2026/27 settlement,
   while the 10-year sat near 4.1–4.4% (fred.db). The next case covers
   test year 2028. A PSCW order is expected by 2027-12, date not
   disclosed; the filing date is inferred from the prior cycle (filed
   April 2025).
5. *probable* — **Affordability headroom absorbs the capex wave.** The
   residential electric bill is 1.46% of Wisconsin median household income
   vs a 1.59% peer average (deck slide 17). Base-rate increases approved:
   2026 +0.15% electric / +2.77% gas, 2027 +3.63% / +2.04% (slide 10).
6. *probable-tier arithmetic, REFUTED* — **The price clears the hurdle on
   the stated path.** §4: 7.08–7.49% implied vs 8.42% hurdle across
   conservative→optimistic; the base clears only near $56.

**Dominant shared risk factor:** rising long-term Treasury yields repricing
long-duration, bond-proxy equity (regulated-utility de-rating) — shared by 0
of 23 held names · 1 unlabelled (PRI: `PRI-2026-08-20.md` carries no factor
line). Held list via composite `portfolio_holding` (snapshot 86); the
insurers (HIG, WRB, ORI) and Brazil-rate names (PAGS, TIMB) carry different
factors, and higher US yields help the insurers' float.

## 2. Business

**Created:** electricity to ~170,000 customers in and around Madison (72%
of regulated revenue; 87% residential) and natural gas to ~180,000
customers across seven counties (28%; 90% residential), delivered reliably.
Customers do not choose MGE. The service territory is a state-granted
franchise. What they get is regulated-cost power in Wisconsin's
fastest-growing county: Dane County is projected to grow ~43% in population
through 2050, with 2.6% unemployment (deck slide 7). Customer counts grow
1.6% a year.

**Captured:** three distinct mechanisms (deck slide 5, share of 2025 net
income):
- *Regulated utility (~75%)* — earns the authorized 9.8% ROE on a 56%
  equity share of rate base. Fuel and gas costs pass through (2% fuel
  bandwidth, gas cost recovery mechanism), so revenue swings with commodity
  prices and margin does not.
- *Nonregulated leased generation (~18%)* — the holding company owns
  generation (Certificate-of-Authority projects) and leases it to the
  utility under long-term leases with fixed returns. That is a regulated
  return in a different wrapper, with 50% current return on CWIP or 100%
  AFUDC during construction (slide 8).
- *ATC transmission stake (~7%)* — a FERC-regulated return on its
  American Transmission Co. investment.
- Plus small venture-capital fund gains, which contributed ~$3.9M pretax in
  Q2 2026 (Q2 release).

**Protected:** a mechanism, not a label. State law grants the exclusive
service territory, and the regulatory compact both guarantees and caps the
return: the moat stops competitors and stops excess returns. What keeps
the return intact is regulator goodwill. That rests on affordability (bills
below peers, improving 20% since 2014), the AA-/Aa2 credit quality the
agencies call "credit supportive", and preapproval of major projects. The
threats sit at the edges. Customer self-generation erodes load. Building
electrification is a long-run threat to the gas LDC (the 10-K does mention
"electrification"; the passage was not read, §6). And a change in PSCW
composition could remove the goodwill: all three commissioners are
Democratic appointees, one term ends March 2027, and the governorship is on
the Q4 2026 ballot (slide 9).

**Control:** one share, one vote, no controlling holder. Insiders 0.24%,
institutions 70.6%, float 37.66M of 37.78M shares (stocks.db v_latest). The
null answer: nothing in the charter was found that forecloses a takeover
or activist path (charter not read this run). Any change of control would
need PSCW approval, like any Wisconsin utility holding company acquisition.
That is general knowledge, not verified in a filing this run.

**Operating leverage (Phase 0): mildly positive.** Revenue → operating
income, $M (stockanalysis income statement):

| FY | revenue | op income | op margin |
|---|---|---|---|
| 2021 | 593.08 | 133.90 | 22.6% |
| 2022 | 699.82 | 157.15 | 22.5% |
| 2023 | 673.93 | 152.03 | 22.6% |
| 2024 | 659.94 | 156.05 | 23.6% |
| 2025 | 726.65 | 182.56 | 25.1% |
| TTM (Jun '26) | 752.13 | 183.10 | 24.3% |

Revenue +26.8% vs operating income +36.7% from 2021 to TTM. Revenue carries
fuel and gas pass-through, so the ratio is noisy, and the driver is rate
base, not scale. Net income $105.8M → $149.6M. Diluted EPS $2.92 → $4.07.
FCF is negative by design: TTM NCFO $278.1M against capex $442.4M
(−$164.3M). Every capital dollar is funded by debt and equity issued at the
authorized mix. Phase 0 did not kill: the business is persistently
profitable, and leverage (debt/EBITDA 3.24, D/E 0.65, net debt 26% of EV)
is modest for an AA- utility.

## 3. Threads pulled

- **Why the stock is down 18% while SPY is up 16%:** weekly and daily bars,
  2025-09-19 → 2026-09-24 (Robinhood). MGEE $83.98 → $68.49 (−18.4%), XLU
  −7.3% ($42.475 → $39.36), SPY +15.6%. The fall comes in two parts:
  (a) **the May equity offering** (below) — week of 5/4, −8.6% on 3.17M
  shares, right after a Q1 beat; (b) **rates** — DGS10 4.14% (2025-09-19)
  → 4.44% (6/30) → 4.94% (9/17) → 5.11% (9/23) (fred.db). Since 9/17
  MGEE is −8.7% ($75.00 → $68.49) vs XLU −5.6%; on 9/24 alone MGEE −3.3%
  vs XLU −1.0%. The 11-point lag vs XLU on the year is the offering plus a
  higher rate beta than large-cap peers. Nothing company-specific broke:
  the EDGAR filing list shows no 8-K since 8/21 (the dividend raise).
- **The equity raise (primary):** 424B5 prospectuses 2026-05-06/07; 8-K
  item 1.01 2026-05-08. 3,300,331 shares at $75.75 public price: 990,099
  sold directly, and 2,310,232 via forward sale agreements at an initial
  $72.9094 forward price (Business Wire release, 2026-05-06; stocktitan
  8-K summary). The forward has not settled — shares outstanding are
  37.78M. The Q2 deck says it "secured" 100% of equity needs through 2030
  under the current plan, with an optional $100M ATM "to address potential
  future increased capital needs" (slide 13). At the AGM (2026-05-19),
  CEO Jeff Keebler conceded EPS "faces dilution initially" but called the
  deal "accretive" with the capex it funds (stockanalysis AGM transcript).
  The ATM line is the overhang that remains if the plan grows (data
  centers, the Columbia gas conversion — neither in the $1.9B).
- **Capital plan and rate base (Q2 2026 financial update PDF, 2026-08-05):**
  capex $395M / $580M (incl. ~$203M for 168MW of RockGen, close late 2027
  subject to PSCW) / $300M / $310M / $315M = $1.9B through 2030. Coal exit:
  Elm Road off coal by end-2032; a Columbia gas conversion is being
  "explored" and is not in the plan. Renewables: ~400MW over five years.
- **Latest disclosure cadence (a finding):** MGEE holds no earnings calls.
  The stockanalysis transcript index has one item, the 2026 AGM. Quarterly
  disclosure is the 8-K release plus the financial-update deck. The Q2 8-K
  EX-99.2 deck is images only on EDGAR; the company-site PDF was read
  page by page. So there is no management Q&A on the rate move or the
  offering beyond one AGM shareholder question on dividend safety.
- **Q2 print (8-K EX-99.1, 2026-08-05):** GAAP EPS $0.89 vs $0.72; net
  income $33.4M vs $26.5M; H1 EPS $2.21 vs $1.86. Electric earnings +$3.0M
  on rate base growth; gas flat; ~$3.9M of VC fund gains. At a ~21% tax
  rate that is ~$0.08/share, so ~60% of the $0.13 beat vs the $0.76
  estimate was non-operating.
- **Earnings-estimate pattern (broker tier):** Q4'24 0.61 vs 0.84 (miss),
  Q1'25 1.14/0.98, Q2'25 0.72/0.73, Q3'25 1.22/1.19, Q4'25 0.64/0.64,
  Q1'26 1.32/1.13, Q2'26 0.89/0.76. Mostly in-line with two sizeable beats.
  No managed-beat pattern; weather and VC marks explain the variance. Q3'26
  estimate $1.25, report 2026-11-04 pm (unverified). Cross-check:
  sec_fundamentals.db `v_screener` still carries Q1 2026 (EPS $1.32, net
  income $48.48M), matching the broker actual. The DB has not captured Q2.
- **Dividend (8-K EX-99.1, 2026-08-21):** quarterly raised 7.0% to $0.5083
  ($2.0332 annualized), the 51st consecutive annual increase. Yield 2.97%
  at $68.49 vs DGS10 5.11%: a −214bp yield gap. That gap is the
  bond-proxy de-rating in one number.
- **Insider/ownership sweep (EDGAR Forms 4, through 2026-09-24):** director
  James G. Berbee bought 261.36 shares at $81.30 (8/19) and 274.74 at
  $77.35 (9/9). Code P, but ~$21K each and dividend-reinvestment sized,
  holding ~10,013 shares. Not a signal either way. No officer sales found.
  8-K 2026-06-23 (item 5.02) and 2026-04-21 (5.02): officer/director
  changes, content not read (§6).
- **Regulatory-composition thread:** all three PSCW commissioners are
  Democratic appointees; Hawkins' term ends March 2027; Wisconsin elects a
  governor in Q4 2026 (deck slide 9). The next governor appoints the
  commissioner who hears the 2028-test-year case. This could go either way
  on the authorized ROE (condition 4). No evidence of hostility found.
- **Data centers:** at the AGM, management said it gets interest from
  developers and requires that "incremental costs are paid for by the new
  customer". No signed load and none in the capex plan. Option value only
  (§6).
- **Options read (mandatory):** path 2 only. MGEE is not in the CBOE
  24-symbol catalog, so `data/options.db` has no history. A chain exists
  (expiries 10/16, 11/20, 2/19, 5/21), but the 11/20 ATM pair fails the
  liquidity gate badly. Table in §4.
- **Dead ends:** composite's +3 is `stocks_rsi` (RSI 15.8, +2) and
  `si_days_to_cover` (12.5 days, 24 days stale, +1). Microstructure only,
  uncalibrated for a utility, no weight. `sa_fscore` 4 and `sa_fcf_yield`
  −6.1 are score-0 annotations; the negative FCF yield is structural for a
  utility, not a flaw. earnings.db carries no MGEE event, a coverage gap
  in the earnings monitor. The transcript-corpus search was not run: the
  corpus is one AGM. `get_equity_news` was not used; the EDGAR filing
  list plus two web searches stood in. The 2026/27 rate settlement came
  out as reported: an all-party settlement, low-income funding $0.5M/yr
  (WPR / ibmadison, low-confidence colour).

## 4. Valuation

**Inputs.** Market cap $2,587,826,982 = 37,784,012 shares (stocks.db
`sharesOut`; statistics page 37.78M) × $68.49 official close. The probe CLI
prints schema only in this slot and ad-hoc Python is denied, so the
rendered statistics page via WebFetch supplied the ratios. The page's
rounded cap $2.59B agrees. **The FCF base is refused:** TTM fcf is
−$164.26M (NCFO $278.11M, capex $442.37M), and `reverse_dcf` returns
`refused: base_fcf must be positive, got -164264000.0` (exit 2). For a
utility that is funding its rate base, the owner's cash flow is the
dividend, not NCFO − capex. **Substituted base: dividends at the new
indicated rate, $2.0332 × 37,784,012 = $76,822,413.** Paired with market
cap, net debt 0.

Growth is **per-share**, so the 2.31M forward shares (~$168.4M of cash in
at settlement) enter as dilution of the growth path rather than as a
separate cash flow. Two-stage path: dividends grow at g for five years
while payout holds ~51% (76.8 / 149.6 TTM net income) to fund the capex
wave. Year 6 then steps the payout to the sustainable `1 − g/ROE`. At the
9.8% authorized ROE and 2.33% terminal growth that is 76.2% (step
+51.92%). Stress uses ROE = hurdle 8.42% and 2.0% terminal growth
(payout 1 − 0.02/0.0842 = 76.25%, step +51.49%). SBC: stocks.db `shareBasedComp` is NULL; the
dividend base is cash actually paid, so no SBC haircut applies. No
minority interests are reported; pension funded status is NOT OBTAINED
(§6). Leverage gate: net debt $917.7M = 26% of EV, below half, so no
equity-as-option lens.

**Hurdle:** rf 5.11% (DGS10, 2026-09-23) + beta 0.8 × ERP 4.14% (Damodaran
implied ERP, September 1, 2026, against his T-bond 4.75%) = **8.42%**. The
raw beta 0.70 (stocks.db 0.70028) is floored into the 0.8–1.2 band. This
is not a thin-float case (insiders 0.24%, float 99.7% of shares out), so
the floor is a stated conservative choice. At 0.70 the hurdle is 8.01%,
shown below. Mature-company companion rf + 4.5% = 9.61%.
**Terminal-growth ceiling:** 10-year breakeven 2.33% (T10YIE, 2026-09-24).
Revenue is US-only, so the headline US ERP stands.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| payout-frozen bookend (51% payout forever; terminal ROE 4.79%) | $76.8M div | 6.0% | 2.33% | 5.91% | −251bp |
| stress (normalise to ROE = hurdle) | $76.8M div | 3.0% | 2.0% | 6.42% | −201bp |
| conservative | $76.8M div | 5.0% | 2.33% | 7.08% | −134bp |
| base | $76.8M div | 6.0% | 2.33% | 7.29% | −114bp |
| optimistic | $76.8M div | 7.0% | 2.33% | 7.49% | −93bp |
| base at raw beta 0.70 (hurdle 8.01%) | $76.8M div | 6.0% | 2.33% | 7.29% | −72bp |
| base at market cap $2.15B (~$56.90) | $76.8M div | 6.0% | 2.33% | 8.21% | −21bp |

The payout-frozen family (3% / 5% / 6% / 7% at 51% payout forever) reads
5.17% / 5.76% / 5.91% / 6.07%. It is shown only to bound the answer: it
assumes retained earnings earn 4.1–4.8% forever, below the hurdle.

**Integrity checks.**
- *Reinvestment / terminal ROE:* the frozen runs print `implied_terminal_roe`
  0.0479 (0.0411 stress). That is value destruction in perpetuity, so
  those rows are not the thesis. The normalised rows set terminal ROE to
  9.8% by construction (1.38 points above the 8.42% hurdle, inside the
  ~5-point limit). Stress sets it equal to the hurdle, so zero excess
  return, per the default fade reading (~29% of firms sustain excess
  returns, Damodaran EVA). The regulator both grants and caps the 9.8%, so
  the terminal excess is small and administered, not competitive.
- *Growth vs reinvestment:* 6% per-share for five years is funded as
  stated. Retained earnings (~$73M/yr) plus the $250M offering cover the
  equity share of the $1.9B plan (deck slide 13); the dividend base sits
  below earnings, so no `growth without reinvestment` warning fires.
- *Market-share sentence (a franchise, so the bill stands in for share):*
  revenue at 6% for five years goes $752M → ~$1,006M (+34%) against
  customer growth of ~8% (1.6%/yr). Per-customer revenue rises ~24% (~4.4%
  a year), versus management's own "below 2%" average annual rate
  increases from 2018 to 2025 (AGM). Revenue includes fuel pass-through,
  so the gap is overstated. Still, it is the affordability pressure
  condition 5 must absorb.
- *Terminal growth vs Item 1A terminal risk:* Item 1A was NOT OBTAINED
  verbatim (the 10-K primary doc exceeds the fetch limit; §6). This run's
  own read of the structural endgame risk: gas-distribution load erosion
  from building electrification (28% of regulated revenue; the 10-K
  contains "electrification", per EDGAR full-text search) and
  self-generation eroding electric load. 2.33% nominal (zero real growth)
  survives both, because electrification moves gas-LDC load onto the
  electric rate base, which is the same franchise. Not verified against
  the filing's own wording.
- *Distribution clamp:* 7.1–7.5% sits just below the US median cost of
  capital (7.79%) and inside the 80% band (5.26–9.88%, Damodaran January
  2026). Not a strong-pass zone. It is a fair-to-rich price for a low-beta
  asset, and a negative spread even on the optimistic path.
- *Commitments:* the RockGen purchase ($203M) and the CA projects are
  inside the $1.9B plan. The 10-K purchase-obligation note was NOT
  OBTAINED (§6). A regulated utility recovers such commitments through
  rates, so they change financing, not the base.
- *Cash taxes:* TTM tax $21.6M on $171.3M pretax (12.6%), below the 21%
  marginal rate: renewable production tax credits. PSCW grants
  "deferral treatment for changes in legislation impacting tax credits"
  (slide 8), so a credit repeal reaches customers, not the dividend base.

**Options-implied move** — path 2 (Robinhood stopgap), expiry 2026-11-20,
57 DTE, strike 70 (nearest listed to spot $68.49; 2.2% above spot). It
brackets the 2026-11-04 AMC Q3 print (reprices 11/5). ATM IV = mean of
call 51.07% and put 19.75%; the legs disagree by 31 vol points, which is
itself the reliability finding.

| metric | value |
|---|---|
| spot | 68.49 |
| expected absolute move (MEAN, not a ceiling) | 11.32% |
| 1-σ move | 13.99% |
| ATM IV | 35.41% |
| RV60 | 18.21% |
| RV20 | 15.67% |
| IV > RV60? | YES |
| IV > RV20? | YES |

Liquidity gate: **FAILED → UNRELIABLE**. Call bid/ask $0.05/$10.00 (mark
$5.025, spread ~199% of mark), OI 0, volume 0. Put $0.05/$5.40 (mark
$2.725), OI 0, volume 1. The marks are midpoints of placeholder quotes,
and the "elevated" IV reading is an artifact of them. No verdict weight.
Timing check: the thesis states no required move on the print — N/A.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** price at or below ~$56 with conditions 1–3 intact. The base
  path then clears the 8.42% hurdle (−21bp at $56.90). Revalue.
- **Shift —** DGS10 back to ~4.4% with the price unchanged. The hurdle
  falls to ~7.7% and the base spread closes to ~−40bp. That alone does
  not flip; it combines with the price trigger.
- **Shift —** the 2028-test-year settlement/order sets an authorized ROE
  ≥ 10.3% on a ≥ 55% equity layer. That raises the normalised terminal
  payout and the per-share path.
- **Shift —** a signed large-load (data center) agreement with
  customer-paid incremental cost. It adds rate base without adding to
  affordability pressure.

For an owner (sell):

- **Break —** a PSCW order or settlement below 9.5% ROE, or a disallowance
  of a CA project. The regulatory compact is the moat.
- **Break —** an equity issuance beyond the May 2026 raise before 2028
  (the ATM activated or a new offering) without a matching capex
  addition. That breaks management's "100% of equity needs through 2030".
- **Shift —** 2027 EPS guidance or consensus below ~$4.10 after forward
  settlement. The per-share path is then under 5%, the conservative row.
- **Shift —** dividend growth below 5% in the August 2027 declaration.

**Reopen trigger:** 2026-11-04: mgee-q3-2026-print-forward-settlement-status-and-run-rate-eps-or-price-at-or-below-56

## 6. UNKNOWNs

1. **PENDING 2026-11-04 — forward-sale settlement timing and post-dilution
   EPS run-rate** (Q3 8-K/10-Q). Bears on condition 3. Does not kill.
2. **PENDING 2027-12 — the 2028-test-year authorized ROE** (PSCW order;
   filing expected ~spring 2027, date inferred from the prior cycle).
   Bears on condition 4. Does not kill.
3. **NOT OBTAINED — FY2025 10-K Item 1A risk factors** (primary doc
   mgee-20251231.htm exceeded WebFetch's 10MB limit; EDGAR full-text
   search confirms "electrification" appears, snippet not returned). Only
   the terminal-growth input depends on it. It does not kill, because the
   pass does not rest on the terminal rate.
4. **NOT OBTAINED — pension/OPEB funded status and the purchase-obligation
   total** (same 10-K, notes). The deck says pension/OPEB get escrow
   treatment (slide 8), so rates recover them. Does not kill.
5. **NOT OBTAINED — the 8-Ks of 2026-04-21 and 2026-06-23 (item 5.02
   officer/director changes)** and the 2026 DEF 14A (compensation design).
   Management incentives are unread. The observable behaviour (a funded
   plan, a regulated-return focus) is ordinary for a utility. Does not
   kill.
6. **UNKNOWN — the next governor's PSCW appointments** (election Q4 2026;
   Hawkins' seat opens March 2027). No filing will carry this before it
   happens.

Option value (not conditions): data-center load with customer-paid
incremental cost; the Columbia gas conversion adding rate base beyond the
$1.9B plan; a falling 10-year re-rating the whole sector.

## 7. Sources

- **Primary:** MGE Energy Q2 2026 earnings release (8-K EX-99.1,
  2026-08-05); Q2 2026 Financial Update deck (company-site PDF
  `20260805-financial-update.pdf`, slides 1–20 read; EDGAR EX-99.2 is
  images only); dividend 8-K EX-99.1 (2026-08-21); EDGAR filing index for
  CIK 1161728 through 2026-09-11; Form 4 ownership.xml for accessions
  0001193125-26-388717 and -359468 (Berbee); 424B5 (2026-05-07) and the
  offering pricing release (Business Wire, 2026-05-06); 2026 AGM
  transcript (via stockanalysis — primary-transcribed); EDGAR full-text
  search on the FY2025 10-K (hit only).
- **stockanalysis.com (vetted exception):** /stocks/mgee/statistics/,
  /financials/ (income statement, cash-flow statement), /forecast/ (2026
  EPS $3.97, targets $71/$77/$81, 4 analysts, Hold), /transcripts/ index.
- **Broker/market microstructure:** Robinhood MCP — official closes and
  quotes for MGEE/SPY/XLU (2026-09-24); weekly and daily bars for
  MGEE/XLU/SPY/WEC/AEE; the earnings estimate-vs-actual pattern (estimates
  are carried by no integrated official source; actuals cross-checked
  against the Q2 release and sec_fundamentals.db); option chain,
  instruments and quotes (11/20 strike 70).
- **Reference data:** Damodaran home page — implied ERP 4.14% on September
  1, 2026 (T-bond 4.75%); cost-of-capital distribution (median 7.79%, 80%
  band 5.26–9.88%) and the ~29% excess-return base rate (January 2026
  vintages, per the anchors reference).
- **Point-in-time repo DBs:** fred.db (DGS10 5.11% 2026-09-23, path from
  4.14% 2025-09-19; T10YIE 2.33% 2026-09-24); stocks.db v_latest (price
  $70.86 capture 2026-09-23, beta 0.70028, insiders 0.24%, institutions
  70.63%, float 37.66M, sharesOut 37.78M, SBC NULL, 4 analysts, next
  earnings 2026-11-04); composite.db snapshot 86 (`stocks_rsi` +2,
  `si_days_to_cover` +1, annotations; the held-name list via
  `portfolio_holding`); sec_fundamentals.db v_screener (Q1 2026 EPS $1.32,
  net income $48.48M — Q2 not yet captured); earnings.db (no MGEE event).
- **Low-confidence:** web-search colour on the 2026/27 rate settlement
  (WPR, ibmadison, RENEW Wisconsin, CUB); stocktitan's 8-K summary of the
  forward sale.

## Kill-thesis record

Ledger: **FLAWED** — conditions=6 (4 probable, 2 plausible), refuted=1,
unknown=0, pending=2, not_obtained=0. The §6 NOT OBTAINED items (Item 1A,
pension, 5.02 8-Ks, proxy) are attached to no load-bearing condition and
do not enter the ledger. The Item 1A miss is logged to `gaps.log`.

Step 1 found a hole in the draft. It listed five operating conditions and
treated the rate path as background. The bull case also needs the price to
clear the hurdle on the stated path. A rate is a scenario input, but that
condition can be tested today, so it was added as condition 6.

Per-condition adjudication:

1. Rate base grows as filed — **SURVIVED.** The attack was ~$305M of CA
   projects pending Q4 2026 approval and the RockGen purchase pending
   PSCW. It held: the 2026/27 test-year rate base is ordered, and the
   PSCW has preapproved every prior CA project listed as "Approved" on
   slides 15–16.
2. Earned ROE near 9.8% — **SURVIVED.** The attack was that TTM 11.04%
   is flattered by VC gains and the nonregulated leases. It held: even
   stripping ~$3.9M of Q2 gains, consolidated ROE sits above authorized,
   and forward test years limit regulatory lag.
3. Per-share growth ~6% net of dilution — **PENDING 2026-11-04.** The
   attack: 2026 consensus EPS $3.97 is below TTM $4.07, and the 2.31M
   forward shares take ~6.1% off per-share growth when they settle. The
   12.2% 2027 rate-base step less dilution nets to ~6%. That is the bull
   path, not a refutation, and the Q3 10-Q discloses the settlement
   status.
4. Next rate case lifts the allowed ROE — **PENDING 2027-12.** The attack:
   Wisconsin held 9.8%, and allowed ROEs move slowly against Treasury
   swings. A new governor appoints a commissioner before the order. No
   evidence today stands against an increase; none stands for one.
5. Affordability headroom — **SURVIVED, strained.** The attack: 6% revenue
   growth implies ~4.4%/yr per-customer bills vs a <2%/yr history (§4
   market-share sentence). It held: bills sit at 1.46% of median income vs
   1.59% for peers, the approved 2027 increases are ≤ 3.63%, and fuel
   pass-through overstates the gap.
6. The price clears the hurdle — **REFUTED.** §4 has 7.08% / 7.29% /
   7.49% vs 8.42% (−134 / −114 / −93bp); at the raw 0.70 beta, −72bp.
   The base clears only near $56. Repairable by price or rates, not by
   anything the business can do.

Internal consistency: the draft claims growth (12% rate base), low risk
(AA-, beta 0.70) and heavy reinvestment (negative FCF, equity issuance)
together. That is internally consistent: the growth is paid for, which is
exactly why per-share growth is ~6% and not 12%.

**Standing checks.**
- *Base rate:* ~29% of firms sustain excess returns (Damodaran EVA). A
  regulated utility's excess is administered and small (9.8% vs 8.42%).
  Utilities de-rated by a rate spike tend to track the 10-year, not their
  own fundamentals, until yields turn (general pattern, no measured rate
  cited).
- *Short case (strongest):* a small, illiquid bond proxy. Its 2.97% yield
  sits 214bp under the 10-year. A 6.1% forward-share overhang settles into
  a falling tape, with an optional $100M ATM behind it. Per-share growth
  was halved by its own funding. The 2026 EPS consensus sits below TTM
  because the Q2 beat was mostly VC marks. The regulator's composition can
  change after the November election, and the 28% gas business faces a
  long electrification tail. The short does not need the business to
  break, only yields to stay above 5%. It wins on condition 6 alone.
- *Management incentives:* proxy not read (§6 #5). Observable behaviour
  (pre-funding equity through 2030, a 7% dividend raise, a disciplined
  data-center stance) is owner-consistent. Issuing at $75.75 (forward at
  $72.91), 10% above today's price, was well timed for the company.
- *Disconfirming search:* the offering (found; it explains the May gap),
  the rate path (found; it explains September), 8-Ks since Q2 (only the
  dividend raise), insider selling (none found; only two small director
  buys).
- *Moat mechanism:* a state-granted exclusive franchise plus the
  regulatory compact. It is a mechanism, not a checkbox, and it caps
  returns as firmly as it protects them.

**Statistical checks:** composite's +3 (`stocks_rsi` RSI 15.8,
`si_days_to_cover` 12.5 days) is uncalibrated microstructure on a single
day. No weight. No backtest claim sits under the thesis.

**Options-timing check:** N/A — no dated required move. Path 2 only; the
11/20 chain failed the liquidity gate (UNRELIABLE, OI 0 both legs).

**Closest attack:** condition 6 — the base path clears the hurdle only near
$56, and even the optimistic path is −93bp.

**Flip evidence:** → SOUND on the bull case: price at or below ~$56 with
the Q3 print showing post-dilution run-rate EPS ≥ $4.10, or an authorized
ROE ≥ 10.3% for 2028. → worse: an ROE below 9.5%, a CA disallowance, or
equity issuance beyond the May raise.

**p(beat SPY, 63 td): 0.43** — written before re-reading §1's. A low-beta
utility in a rising 10-year tape, with a forward-share overhang and a print
inside the window, faces a headwind against SPY. RSI in the teens and an
18% drawdown give it some mean-reversion odds, not enough to reach a coin
flip.
