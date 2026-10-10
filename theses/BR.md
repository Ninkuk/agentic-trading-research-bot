# BR — Broadridge Financial Solutions — 2026-10-08

Price $165.21 (official close, 2026-10-08) · market cap $18,652,214,287
(112,900,032 shares × $165.21) · next earnings 2026-11-03 BMO (unverified)

Unattended scheduled run, user-directed on the ticker. Supersedes
`research/BR-2026-09-06.md` (PASS at $172.88, UNPROVEN). That thesis's own
reopen trigger (2026-11-03: q1-fy27-print-proxy-and-price) is **not** yet
due, so this is a fresh run at a new price, not a reopen — no §0. Since the
last run: the DEF 14A it was waiting on has been filed, and the 10-year
Treasury is up 50bp.

## 1. Verdict and thesis

**PASS at $165.21.** kill-thesis: **UNPROVEN** — conditions=6 (2 probable,
4 plausible), refuted=0, unknown=1, pending=2, not_obtained=0.

**p(beat SPY, 63 td): 0.47** · kill-thesis: 0.46 — **Disputed expectation:**
at $165.21 the market prices an implied 8.1–10.9%/yr against a 9.19% hurdle.
The spread is +15 to +45bp when growth is organic only and SBC is charged,
and −48 to −110bp when the M&A that buys the guided growth is charged. What
revises it: the 2026-11-03 Q1 print (organic recurring growth against a
record event-driven comp) and the final Reg E-Delivery release's treatment
of processing fees.

The business has not changed and remains good: a fee-scheduled toll between
~1,000 brokers and every US issuer, with operating income up every year
since FY20 and margin expanding every year since FY22 (13.31% → 17.40%). The stock is 4.4% lower than at the last run (SPY +0.5%
over the same window), but the 10-year moved from 4.78% to 5.28% and pushed
the hurdle up 63bp. Net, the spread barely moved. The repricing was a rate
repricing, not a discount opening up. The best honest construction (organic
growth, SBC charged) clears the hurdle by 15–45bp and fails Damodaran's
mature-company companion of 9.78%. That is a fair price, not a margin of
safety, so this is still a pass for a new position.

**Closest attack:** management's own disclosed e-delivery effect, a "modest
decrease in recurring revenue growth over a two- to three-year period" after
FY27, lands squarely inside the five-year forecast window. It pulls the
honest organic path from 6% toward 5%, and the bull spread from +45bp to
+15bp, which is inside estimation noise.

Load-bearing conditions (6) — the bull case: owning BR at $165.21 beats SPY.
The rate itself is a §4 input, not a condition.

1. *probable* — **FY26 company-defined FCF of $1,233.0M is the right base.**
   NCFO $1,345.6M − capex $67.2M − capitalized software $45.4M, which
   reconciles to the 10-K MD&A. The $997.0M of purchase obligations (Kyndryl
   IT services through FY2032, plus cloud) is operating spend already inside
   NCFO, not hidden capex.
2. *plausible* — **Organic recurring growth holds at 5–7%.** FY27 guide:
   6–8% recurring constant-currency, of which ~1pt is M&A [Q4 FY26 call, per
   `BR-2026-09-06.md`]. First read: the Q1 FY27 print, 2026-11-03. The
   FY28–FY30 e-delivery drag is disclosed and works against the top half of
   that range.
3. *plausible* — **The organic construction is the right one.** Its premise
   is that BR's continuing M&A earns at least its cost, so an organic-only
   path neither gains nor loses from it. Bounded by blended ROIC of 17.0%
   [`stocks.db`], which carries $3,787.8M of goodwill [FY26 10-K] and still
   sits ~8 points above the hurdle. Per-deal returns are undisclosed (FY26:
   four deals, $300.2M aggregate). Decisive read: the FY27 10-K, ~2027-08.
4. *plausible* — **The final Reg E-Delivery rule leaves the NYSE
   processing-fee schedule untouched.** The proposal's scope is the delivery
   default only. The adopting release is undated, so this is carried as the
   one load-bearing UNKNOWN.
5. *probable* — **Management is paid to grow organically, not to buy
   growth.** DEF 14A (2026-09-29): long-term incentives are 50% PRSUs on
   comp-adjusted EPS plus **organic** recurring revenue growth, and 50% stock
   options. The annual bonus is 30% comp-adjusted EBT, 20% closed sales, 10%
   fee revenue, 10% onboarding, 5% client satisfaction, 25% strategic. FY26
   bonuses paid 102–110% of target. Say-on-pay got ~92% support in 2025.
6. *plausible* — **The 2026-11-03 Q1 print reaffirms the FY27 guide** while
   lapping a record $114M event-driven quarter. The consensus Q1 estimate of
   $1.37 is already 9% below last year's $1.51 actual [Robinhood], so the
   comparison is expected. Pending 2026-11-03.

**Dominant shared risk factor:** US retail equity-account and position growth
— holdings unavailable in this session.

## 2. Business

Unchanged from `BR-2026-09-06.md` §2; restated briefly.

**Created:** solves the many-to-many problem between ~1,000 broker-dealers and
effectively every US public issuer and fund. Proxy distribution, voting and
regulatory disclosure reach 200M+ beneficial-owner accounts at a mutualized
cost no single broker could match. GTO adds back- and middle-office
processing that lets banks retire legacy stacks.

**Captured:** four distinct mechanisms:
- (i) per-position regulatory processing fees under the NYSE Rule 451/465
  schedule (the issuer pays, the broker picks the vendor, the SEC reviews the
  schedule);
- (ii) recurring per-account and per-communication subscription fees;
- (iii) GTO SaaS and license revenue;
- (iv) event-driven work, guided at $250–300M for FY27.

Distribution pass-through carries low or no margin, and it is the leg the SEC
is modernizing.

**Protected:** SEC and NYSE rules *compel* broker distribution at a scheduled
fee, so a competitor cannot undercut a regulated price. Taking share means
rebuilding ~1,000 broker integrations for a customer (the broker) who does
not pay the bill. The SEC's own comment file (SR-NYSE-2020-96) describes BR
as handling "almost all" US beneficial-owner proxy processing. Revenue
retention is 98%. The weakness has the same source: the rulebook that grants
the toll can amend it.

**Control:** one class of common stock, one vote per share, no controlling
holder. Insiders hold 0.39% and institutions 98.07% [`stocks.db`]. Nothing
structural blocks a takeover or an activist. The annual meeting is
2026-11-10 [DEF 14A].

**Operating leverage (Phase 0): positive.** FY figures from SEC XBRL, as
tabulated in `BR-2026-09-06.md` (no 10-K since):

| FY | revenue $M | operating income $M | margin |
|---|---|---|---|
| 2019 | 4,362.2 | 652.7 | 14.96% |
| 2020 | 4,529.0 | 624.9 | 13.80% |
| 2021 | 4,993.7 | 678.7 | 13.59% |
| 2022 | 5,709.1 | 759.9 | 13.31% |
| 2023 | 6,060.9 | 936.4 | 15.45% |
| 2024 | 6,506.8 | 1,017.1 | 15.63% |
| 2025 | 6,889.1 | 1,188.6 | 17.25% |
| 2026 | 7,476.8 | 1,300.6 | 17.40% |

Revenue +71.4% and operating income +99.3% from FY19 to FY26. Leverage has
run positive every year since the FY20–FY22 trough from the Itiviti
integration. `stocks.db` agrees: TTM revenue $7,476.8M, operating income
$1,300.6M.

## 3. Threads pulled

- **The DEF 14A closes a three-run gap, and it reads favorably.** Filed
  2026-09-29 alongside the ARS and a DEFA14A. Long-term incentives are tied
  to *organic* recurring revenue growth and comp-adjusted EPS over three
  years. Acquired revenue therefore does not pay the long-term grant, which
  is the strongest available answer to "is management incentivized to buy
  growth?" The annual bonus's 20% closed-sales weight rewards bookings, not
  margin. The EBT metric (30%) keeps that honest. A CEO total-compensation
  figure of $4,741,817 came back from the proxy extraction. It is
  implausibly low for a Summary Compensation Table total and is **not**
  relied on anywhere here.
- **Why the stock fell: rates, not news.** BR went from $172.88 (2026-09-04)
  to $156.93 (2026-10-02), then recovered to $165.21. Over the same period
  DGS10 rose from 4.78% to 5.28% [`fred.db`] and SPY rose 0.5%. EDGAR shows
  no 8-K since 2026-08-04, only the proxy, the ARS and Forms 4. A 2.7%-yield,
  mid-single-digit-growth compounder is a long-duration asset, and its
  spread over the hurdle was nearly unchanged through the move (§4). Today's
  +3.17% (SPY −0.42%) has no filed or reported cause. A dated web search
  found nothing.
- **Post-call events, all non-cash today:**
  - The Korea Securities Depository proxy-voting MOU (2026-09-28).
  - Distributed Ledger Repo volume: $7.5T in September, averaging $359B a
    day [Broadridge press release].
  - Boaz Lahovitsky named President of Wealth Management (2026-09-23, per a
    low-confidence aggregator; no 8-K, so it is below the Item 5.02 officer
    threshold).

  These are tokenization and international optionality, consistent with
  `BR-2026-09-06.md`'s Payward thread. None is a revenue datum.
- **Insider filings: routine, a dead end.** The 2026-09-28 and 2026-10-06
  Forms 4 sampled are director deferred-stock-unit grants and dividend
  equivalents (code A, $0.00; e.g. Nazareth, Murray). 2026-10-05: Corporate
  VP Carey sold 2,501 shares at $159.76, footnoted as "sold to cover tax
  liabilities upon the vesting of 5,275 performance based Restricted Stock
  Units" on 2026-10-01. No discretionary open-market selling or buying.
- **The e-delivery headwind is quantified in shape, not size.** Management
  guides no FY27 effect, then a "modest decrease in recurring revenue growth
  over a two- to three-year period" with distribution revenue falling and
  margins rising [summarized in law-firm coverage of the proposal;
  low-confidence tier for the wording]. That headwind sits inside the §4
  forecast window, which is why scenario B (5%) gets equal weight with O
  (6%). Comments closed 2026-09-21. No adopting release yet.
- **Commitments footnote: asset-light holds.** Contractual obligations
  [FY26 10-K]:
  - debt principal $3,274.7M;
  - interest and fees $687.6M;
  - operating leases $316.9M;
  - purchase obligations $997.0M (Kyndryl IT services through FY2032, plus
    cloud).

  The purchase obligations are services opex already flowing through NCFO,
  not deferred capex, so no base-FCF haircut. Litigation: "no material
  pending legal proceedings."
- **FY26 acquisition spend confirmed.** Four businesses (CQG, Acolin, iJoin,
  Signal) for an aggregate $300.2M in cash [FY26 10-K MD&A]. The cash-flow
  line net of cash acquired is $282.7M, which is the D/E charge.
- **The earnings pattern is managed and adjusted.** Six reported quarters
  [Robinhood, broker tier]: +0.01, +0.05, +0.29, +0.24, +0.11, +0.07 vs
  estimate, Q4 FY26 $3.82 vs $3.75. `data/sec_fundamentals.db` now has a BR
  row (new since the last run). Its `v_screener` latest period shows
  revenues $1,953.6M, net income $276.3M and GAAP diluted EPS $2.36. Which
  fiscal quarter that row is was not confirmed, so the adjusted-vs-GAAP
  cross-check is **inconclusive**. Either way, the Robinhood actuals are
  adjusted figures, as the repo's standing note says.
- **Machine view: none.** `composite.db` snapshot 100 (2026-10-09T04:05Z, i.e.
  2026-10-08 Phoenix) scores BR at 0/0/0 with coverage 0.0 and
  `in_portfolio`=1. Only informational rows exist: `sa_fcf_yield` 7.07%,
  `sa_fscore` 7.0, `portfolio_holding` 0.125% of book (obs 2026-10-07).
- **Options read (mandatory):** path 2 only (Robinhood stopgap). Path 1 is
  N/A because BR is not in the CBOE catalog. The 2026-11-20 $165 pair is the
  nearest expiry that brackets the 2026-11-03 print, and it **FAILS the
  liquidity gate**. Table in §4.
- **Dead ends:**
  - `data/portfolio.db` was refused (no grant), so there is no factor-overlap
    count.
  - Exact `hover` strings on `/stocks/BR/statistics/` are unreachable: the
    probe CLI prints schema only, and ad-hoc Python is not permitted.
    Market cap uses `stocks.db` `sharesOut` 112,900,032 (the statistics
    page's "112.90 million") × the official close. The 10-K cover count
    (114,021,798 at 2026-07-31) would give $18.84B, +1.0%, consistent with
    continued buybacks.
  - The next-earnings date disagrees: `earnings.db` `v_upcoming_earnings`
    has 2026-11-02 (source `edgar-estimate`), while `stocks.db` and
    Robinhood have 2026-11-03 BMO (Robinhood marks it unverified).
  - The 10-K's Note 6 per-deal purchase-price allocation was not reached in
    the fetch (non-load-bearing; the aggregate is in hand).
  - Searches for causes of the 2026-10-02 (−2.62%) and 2026-10-08 (+3.17%)
    moves returned only aggregator colour.

## 4. Valuation

**Inputs and pairing.** Levered FCF against **market cap $18,652,214,287**.
Net debt is 0 by the pairing rule. For reference only, net debt is $3,116.7M
(debt $3,520.5M − cash $403.8M), ~14% of EV, far below the leverage gate, so
the equity-option lens does not apply.

- **Base flow:** company FY26 FCF $1,233.0M (unchanged; Q1 FY27 is
  unreported).
- **Haircuts where a row says so:** SBC $93.9M (1.26% of revenue) and FY26
  acquisition spend $282.7M. No minority interests. No material litigation.
- **Pension:** not checked. BR's footnote has never shown a material
  underfunding in prior runs, but it was not read this run.
- **Base earnings for the reinvestment test:** cash earnings $1,174.7M = net
  income $1,124.3M − after-tax Canton gain + after-tax acquired-intangible
  amortization ($291.8M), at the 22.24% FY26 rate (derivation in
  `BR-2026-09-06.md` §4).

**Hurdle:** rf 5.28% + beta 0.932 × ERP 4.20% = **9.19%**. The ERP is
Damodaran's implied figure as of 2026-10-01; his T-bond rate then was 5.29%.
rf is DGS10 on 2026-10-07. Beta 0.93204 [`stocks.db`] is inside the 0.8–1.2
band, so no clamp. His mature-company companion, rf + 4.5% = **9.78%**, is
also quoted. **Terminal growth 2.35%** = the 10-year breakeven `T10YIE` on
2026-10-08 (the working ceiling; zero real growth in perpetuity).

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A — company FCF, total-guide-mid growth unpaid | $1,233.0M | 6% | 2.35% | 10.23% | **+104bp** |
| C — company FCF, guide-high, M&A growth unpaid | $1,233.0M | 8% | 2.35% | 10.89% | **+169bp** |
| O — less SBC, organic-mid | $1,139.1M | 6% | 2.35% | 9.64% | **+45bp** |
| B — less SBC, organic-low | $1,139.1M | 5% | 2.35% | 9.35% | **+15bp** |
| D′ — M&A at 6yr mean $143.8M, 7% | $1,089.2M | 7% | 2.35% | 9.62% | **+43bp** |
| D″ — M&A at 6yr mean, matched 6.6% | $1,089.2M | 6.6% | 2.35% | 9.50% | **+31bp** |
| D — less FY26 M&A, total-guide 7% | $950.3M | 7% | 2.35% | 8.71% | **−48bp** |
| E — less SBC and FY26 M&A, 7% | $856.4M | 7% | 2.35% | 8.10% | **−110bp** |

Against the 9.78% companion: A +45, C +111, O −14, B −43, D′ −16, D″ −28,
D −107, E −168bp. Row D clears the 9.19% hurdle at ~$152 (market cap $17.16B
→ 9.25%). Compared with the 2026-09-06 table, every comparable spread
narrowed 30–45bp (A +137 → +104, D −6 → −48, D′ +80 → +43). A 4.4% lower
price did not keep pace with a 63bp higher hurdle.

**Integrity checks.**

- **Reinvestment / terminal ROE.** Rows A and C print the tool's `growth
  without reinvestment` warning (base FCF > cash earnings). That warning is
  why they are listed as "growth unpaid" and not leaned on.
  - O and B show a 77.5% implied terminal ROE: indefensible as a perpetual
    return on incremental capital. Organic growth this cheap requires the
    toll to keep repricing.
  - D at 12.3% is ~3 points above the hurdle and defensible.
  - E at 8.67% is *below* the hurdle, a value-destroying terminal, and is
    the fade-consistent case.
  - D′ at 32.3% is "tough to do" in perpetuity.

  The honest centre is therefore the B–O band, with D as the bear-side
  check.
- **Base-year cash tax.** The FY26 effective rate is 22.24% against a ~24–25%
  marginal rate. No NOL story, no haircut.
- **Market share.** 6% for five years puts FY2031 revenue at ~$10.0B, and 5%
  at ~$9.5B (1.27–1.34× FY26). The proxy leg is already "almost all" of US
  beneficial-owner processing [SR-NYSE-2020-96], so that growth must come
  from position-count growth, the fee schedule, GTO, wealth and
  international. Those are less protected markets than the one the moat
  argument describes.
- **Terminal growth vs the Item 1A terminal risk.** The FY26 10-K names
  physical-delivery decline (possible "restructuring of our physical
  distribution operations") and tokenization disintermediation. A 2.35%
  terminal rate equals breakeven inflation, so it claims no real growth. It
  survives the delivery decline because distribution is low-margin, but it
  needs BR to keep taxing tokenized rails. The Payward, Galaxy, Ondo and
  Alpaca relationships plus DLR volume are the evidence for that today.
- **Distribution clamp.** Implied returns span 8.10–10.89%, around the US
  median cost of capital of 7.79% (80% band 5.26–9.88%, Damodaran Data
  Update 2026). That distribution was measured at a lower risk-free rate
  than today's 5.28%, so the band understates current hurdles. Nothing here
  is a strong pass regardless of story, and nothing is a bargain.
  Excess-return base rate: ~29% of firms.

**Options-implied move.** Path 2 (Robinhood stopgap); path 1 is N/A because
BR is not in the CBOE catalog. Listed expiries: 2026-10-16, 2026-11-20,
2026-12-18, 2027-03-19 and 2027-12-17. **2026-11-20, DTE 43**, is the nearest
expiry that brackets the 2026-11-03 BMO print. The ATM pair is the $165
strike against $165.21 spot; ATM IV is the mean of the call's 35.81% and the
put's 40.61%. Computed by `tools.options.implied_move` over 74 closes
(2026-06-25 → 2026-10-08).

| metric | value |
|---|---|
| spot | 165.21 |
| dte (calendar days) | 43 |
| ATM IV | 38.21% |
| expected absolute move (MEAN, not a ceiling) | 10.41% |
| 1-sigma move | 13.11% |
| RV60 | 32.96% |
| IV > RV60? | YES |
| RV20 | 26.14% |
| IV > RV20? | YES |

**Liquidity gate: FAILED → UNRELIABLE.**

| leg | bid/ask | spread | spread / mark | OI | volume today |
|---|---|---|---|---|---|
| call | $7.50/$9.60 | $2.10 | 24.6% of $8.55 | 3 | 14 |
| put | $7.50/$9.80 | $2.30 | 26.6% of $8.65 | 2 | 0 |

Both legs are well over the 10%-of-mark gate. The call/put IV gap of 4.8
points is itself a sign of a stale, wide book. IV above both RV windows is
the stopgap's known artifact: the window spans a print and RV20 contains
none. **Timing check: NOT APPLICABLE** — the thesis needs no dated move.
ATM IV is under 50%, so implied returns stay at two decimals.

## 5. Falsifiers

**For the pass (flip toward buy):**

1. **Shift —** price at or below ~$152, where even the FY26-M&A-charged row D
   clears the 9.19% hurdle. Equivalently, a fall in DGS10 back toward 4.8%
   at today's price, which drops the hurdle ~45bp and puts the B–O band
   ~60–90bp clear.
2. **Shift —** the Q1–Q2 FY27 prints showing organic recurring growth at or
   above 6% **with** a quantified e-delivery offset, moving the honest
   centre from B to O-or-better.
3. **Shift —** the final Reg E-Delivery adopting release leaving the
   processing-fee schedule untouched, with the stock not already re-rated.

**For an owner (sell):**

4. **Break —** the final rule touches processing fees or intermediary
   compensation rather than only the delivery default.
5. **Break —** a Schwab- or Fidelity-scale broker moving to issuer-direct
   communications or self-custody equity wallets that bypass ProxyVote.
6. **Shift —** FY27 guidance cut below 5% recurring constant-currency, or
   below 8% adjusted EPS.
7. **Shift —** equity position growth below 5% for two straight quarters,
   or revenue retention below 97%.
8. **Shift —** an e-delivery transition showing *recurring* (not just
   distribution) revenue declining with no quantified offset.
9. **Shift —** M&A spend stepping well above $300M a year while organic
   growth slips, i.e. growth being bought, not earned. That would undo
   condition 3 and move the centre to row D/E.

**Reopen trigger:** 2026-11-03: q1-fy27-print-organic-growth-and-price — read
organic recurring growth and the guide at the Q1 FY27 print (and the
acquisition line in the 10-Q), then re-run the B/O/D rows at that day's price
and DGS10.

## 6. UNKNOWNs

1. **UNKNOWN — the final Reg E-Delivery rule's treatment of processing
   fees.** The proposal's scope is the delivery default only. Comments
   closed 2026-09-21, and the SEC has no dated adoption. Would come from the
   SEC adopting release. This is the one load-bearing UNKNOWN; it caps the
   verdict at UNPROVEN and does not kill the thesis.
2. **UNKNOWN — the size of the FY28–FY30 e-delivery drag on recurring
   growth.** Management says "modest" and has disclosed no fee mix by
   communication type. Would come from a segment or fee-type disclosure BR
   has never made. Not load-bearing on its own; it is why B carries equal
   weight with O.
3. **PENDING 2026-11-03 — Q1 FY27 organic growth, guide reaffirmation, and
   event-driven revenue against the $114M comp.**
4. **NOT OBTAINED (non-load-bearing) — FY26 10-K Note 6 per-deal
   purchase-price allocation, and the proxy's FY24–FY26 PRSU payout
   percentage.** The aggregate deal price ($300.2M) and the PRSU metric
   design are in hand; the detail would only refine condition 3.
5. **UNKNOWN — the cause of the 2026-10-02 (−2.62%) and 2026-10-08 (+3.17%)
   moves.** No filing or credible news found. Does not bear on the thesis.
6. **Option value (*possible* tier, not a condition):** tokenized-equity
   governance (Payward, Galaxy, Ondo, Alpaca), DLR repo scale ($7.5T in
   September), and the Korea depository MOU. Each could matter; none has a
   revenue line.

## 7. Sources

- **Primary:** FY26 10-K (filed 2026-08-04; CIK 1383312) — MD&A acquisitions
  (four businesses, $300.2M aggregate cash), goodwill $3,787.8M, the
  contractual-obligations table, the legal-proceedings statement, Item 1A as
  read in prior runs. DEF 14A, accession 0001140361-26-037937 (filed
  2026-09-29): annual meeting 2026-11-10, incentive metrics and weights,
  FY26 bonus payout 102–110%, 2025 say-on-pay ~92%. EDGAR filing index for
  CIK 1383312 (filings since 2026-09-01: DEF 14A, DEFA14A and ARS on 09-29;
  Forms 4 on 09-28, 10-05 and 10-06). Forms 4 0001225208-26-007964
  (Nazareth), -008290 (Murray) and -008251 (Carey, sell-to-cover). SEC
  comment file SR-NYSE-2020-96. Federal Register 2026-14679 (Reg
  E-Delivery). Broadridge press releases: Korea Securities Depository MOU
  (2026-09-28) and DLR September volume. FY19–FY26 operating table from SEC
  XBRL as tabulated in `BR-2026-09-06.md`.
- **stockanalysis.com (vetted exception):** `/stocks/BR/statistics/` probe:
  112.90M shares, trailing P/E 17.21, EV/EBITDA 12.03, ROE 40.92%, next
  earnings text. Prior-run income and cash-flow statement figures (no
  filing since), carried via `stocks.db`.
- **Broker/market microstructure:** Robinhood MCP, admissible because no
  integrated official source covers quotes, option chains or estimates for
  BR. Used: official close $165.21 (2026-10-08) and SPY $773.93; daily bars
  2026-06-25 → 2026-10-07; the option chain and the 2026-11-20 $165
  call/put quotes; eight quarters of EPS estimate vs actual, plus the Q1
  FY27 estimate of $1.37 and the 2026-11-03 date (unverified).
- **Reference data:** Damodaran implied ERP 4.20% and T-bond rate 5.29%, as
  of 2026-10-01 (NYU Stern home page). Mature-company companion rf + 4.5%.
  US median cost of capital 7.79%, 80% band 5.26–9.88% (Data Update 2026).
  Excess-return base rate ~29%.
- **Point-in-time repo DBs:**
  - `fred.db`: DGS10 5.28% (2026-10-07), path 4.78 → 5.28 since 2026-09-04;
    T10YIE 2.35% (2026-10-08).
  - `stocks.db` `v_latest`, snapshot 71 (price date 2026-10-07): price
    $160.13, sharesOut 112,900,032, beta 0.93204, SBC $93.9M (1.256% of
    revenue), insiders 0.39%, institutions 98.07%, debt $3,520.5M, cash
    $403.8M, ROE 40.92%, ROIC 17.03%, fScore 7, fcf $1,278.4M, next
    earnings 2026-11-03 bmo, 9 analysts at a $213.38 target.
  - `composite.db` snapshot 100: coverage 0.0, informational rows only.
  - `sec_fundamentals.db`: a new BR row (period unconfirmed).
  - `earnings.db`: 2026-11-02 edgar-estimate.
  - `portfolio.db`: not readable in this session.
- **Low-confidence:** law-firm memos on the Reg E-Delivery proposal and BR's
  "modest decrease" framing (Akin, Cooley, Gibson Dunn, Sidley); ad-hoc-news
  aggregator items on the 2026-10-02 move; a mitchellake.com item on the
  wealth-president hire.

## Kill-thesis record

**UNPROVEN** — conditions=6 (2 probable, 4 plausible), refuted=0, unknown=1,
pending=2, not_obtained=0.

Step 1 moved one item out. The draft's "9.19% is the right hurdle" rests on
an exogenous rate, so it is a §4 input, not a condition. What it hid is
whether the price clears the hurdle on the stated path, and conditions 2 and
3 carry that. Six remain.

Per-condition adjudication:

1. **FCF base $1,233.0M — SURVIVED (probable).** Attack: the 10-K's $997.0M
   of purchase obligations is disguised capex. It fails, because these are
   Kyndryl IT services and cloud contracts, i.e. operating spend already
   expensed through NCFO. The SBC deduction is applied in the honest rows.
2. **Organic 5–7% holds — PENDING 2026-11-03.** Attack: the disclosed
   post-FY27 e-delivery drag. That drag is real and lands inside the five-year
   window, so it argues for 5% over 6%. It does not refute 5–7%, because
   management guides FY27 untouched and the drag "modest." The decisive
   checkpoint is dated.
3. **Organic construction right — SURVIVED (plausible).** Attack: per-deal
   M&A returns are undisclosed, and if bolt-ons earn below cost, the organic
   row overstates value. It fails on the aggregate: blended ROIC is 17.0%
   *with* $3.79B of goodwill in the capital base, ~8 points above the
   hurdle. The internal-consistency check also passes, because O grows only
   organically and charges no M&A, so it does not get growth free. It stays
   plausible because the blend may mask weaker recent deals.
4. **Fee schedule untouched — UNKNOWN.** The proposal's scope is favorable,
   but no dated document settles it, and a search for any current NYSE
   451/465 fee proceeding found none. This routes the verdict to UNPROVEN.
5. **Incentives aligned — SURVIVED (probable).** Attack: closed sales (20%)
   and "comp-adjusted" definitions reward volume and flatter EPS. Partly
   landed: the bonus does reward bookings. But the long-term grant is on
   *organic* recurring growth, which removes the M&A temptation, and EBT
   (30%) disciplines bookings. The thesis does not assume management acts
   against its pay.
6. **Q1 reaffirmation — PENDING 2026-11-03.** Attack: the record $114M
   event-driven comp. Weak, because consensus already models Q1 EPS 9% below
   last year ($1.37 vs $1.51).

Standing checks.
- **Base rate:** ~29% of firms earn above their cost of capital. BR is in
  that group (ROIC 17%), but the fade-consistent rows (E at an 8.67%
  terminal ROE) sit below the hurdle.
- **Short case:** a 2.7%-yield, ~5–6%-organic-growth stock competing with a
  5.28% Treasury. The protected leg is fully penetrated, so all growth comes
  from less-moated GTO, wealth and international. E-delivery cuts recurring
  growth for 2–3 years after FY27. The regulator can amend the toll. The
  last month showed the stock trading as a duration asset. Not refuted; it
  is why this is a PASS.
- **Management incentives:** run for the first time in four runs (DEF 14A
  read); aligned.
- **Disconfirming search:** run on the price moves (nothing), on fee-schedule
  proceedings (nothing current), and on insider selling (sell-to-cover only).
- **Moat:** a mechanism (compelled distribution at a scheduled fee, the
  payer/chooser split, ~1,000 integrations), not a checkbox.

Statistical checks: N/A. No backtest, screen or repo signal underlies the
thesis; composite coverage is 0.0.

Options timing check: NOT APPLICABLE (no dated move claimed). Coverage: path 2
only, 2026-11-20 at DTE 43, liquidity gate FAILED (spreads 24.6% and 26.6% of
mark, OI 3/2). UNRELIABLE.

**Closest attack:** the disclosed e-delivery drag on recurring growth after
FY27 sits inside the five-year window and moves the honest organic row from O
(+45bp) to B (+15bp). That is noise-level against 9.19% and negative against
the 9.78% companion.

**Flip evidence:**
- **To SOUND:** a dated adopting release leaving processing fees untouched,
  which clears the only UNKNOWN.
- **To FLAWED:** the rule touching fees, or Q1–Q2 organic recurring growth
  below 5%.

**p(beat SPY, 63 td): 0.46.**
