# HIG — The Hartford Insurance Group, Inc. — 2026-09-13

Price $136.36 (official close, 2026-09-11 — the 2026-09-13 Phoenix date is a
Saturday) · market cap $36,936,106,193 · next earnings 2026-10-26 AMC (broker
calendar, unverified by company; `data/earnings.db` carries an EDGAR-derived
estimate of 2026-10-22)

Entry path: unattended scheduled run. Supersedes `research/HIG-2026-08-13.md`
(BUY at $137.83, kill-thesis SOUND), whose reopen trigger 2026-11-02 has **not**
fired — this is a refresh, not a reopen, so there is no §0. HIG is a currently
held name (`composite.db` `ticker_scores.in_portfolio = 1`, snapshot
2026-09-14T04:05Z); composite carries no HIG signal flag (coverage 0.0).

## 1. Verdict and thesis

**BUY at $136.36.** kill-thesis: **SOUND** — conditions=5 (4 probable,
1 plausible), refuted=0, unknown=0, pending=1, not_obtained=0.

**p(beat SPY, 63 td): 0.53** · kill-thesis: 0.48 ·
**Disputed expectation:** at 1.705× book ex-AOCI the price implies The Hartford
earns roughly **12.4% on equity in perpetuity** against a trailing core ROE of
18.7% and a 2021–22 cyclical trough of 12.5–13% — the market is pricing a full
round-trip to the pre-hard-market floor and no credit for the structural
investment-income uplift that arrived since. What revises it upward is a Q3'26
print (2026-10-26) holding total prior-year development net favorable while core
ROE stays at or above 17%; what revises it downward is the same print showing
favorable development continuing to halve — 6M'26 $152M against 6M'25 $309M —
while Business Insurance renewal pricing keeps decelerating.

This is a good business at a price that still pays you to own it, and the margin
of safety is arithmetic rather than narrative. Solve the reverse DCF for the
core-earnings level at which the price merely earns its cost of equity and the
answer is a **mid-cycle core ROE of about 13.2%** — almost exactly what HIG
earned in 2021–22, when the 10-year Treasury was near 1.5%. Getting back there
now would require underwriting materially *worse* than 2021's, because net
investment income alone is running $800M a quarter against $658M a year ago
(+21.6%, Q2'26 supplement) — roughly two points of ROE gained in twelve months
on a $21.67B ex-AOCI equity base. Everything above 13.2% is spread, and the
trailing number is 18.7%.

**Closest attack:** the multiple, not the cash flow. The DCF says fair value
holds to a 13.2% ROE; the *market* has never paid 1.7× book ex-AOCI for a 13%
ROE insurer. HIG's own P/B ranged 1.32 (FY2021) to 2.02 (FY2025). If mid-cycle
ROE really settles near 14%, a de-rating toward 1.4× book ex-AOCI is ~$110/share
— **−19%** — and the reverse DCF's +47bp does not see it, because a DCF prices
perpetual ownership while a 63-trading-day horizon is priced by the multiple.
This attack does not refute a condition; it is why p(beat SPY) sits near a coin
flip on a name whose long-run value case is comfortable.

Load-bearing conditions of the bull case (5):

1. **Mid-cycle core earnings ROE holds above ~13.2%.** *Probable*: trailing
   core ROE 18.7% (Q2'26 supplement), FY2025 19.4%, and the 2021–22 trough of
   12.5–13% was earned with a 1.5% 10-year. NII of $800M/quarter vs $658M a
   year ago on $64.0B of investments is a structural uplift the trough
   comparison does not contain. This is the break-even from §4 and the crux.
2. **Total P&C prior-year development stays net favorable.** *Plausible*, and
   decaying: Q2'26 $(111)M favorable, 6M'26 $(152)M against 6M'25 $(309)M — a
   51% year-over-year halving. The decisive disclosure is the Q3'26 print,
   2026-10-26; the annual reserve review lands in Q4.
3. **Business Insurance underlying combined ratio stays below 90 through the
   soft cycle.** *Probable*: Q2'26 BI combined 90.4, underlying **88.6**. The
   softening is concentrated in large commercial property (broker indices put
   Q2'26 property down 8.1%, a fifth consecutive quarterly decline), a line
   where HIG's book is de minimis.
4. **Employee Benefits core margin does not fall below the stated 6–7% band
   after the Equitable integration.** *Probable*: Q2'26 EB core margin **8.9%**
   — two points above the top of management's own band — with a group
   disability loss ratio of 74.0%. A full reversion to 6.5% costs roughly
   $150M/yr of core earnings, ~0.7 points of ROE, and is already inside the §4
   stress runs.
5. **Capital return executes out of operating capital generation, not out of
   the Wellington proceeds.** *Plausible*: the $4.2B authorization through Dec
   2028 and the $475M/quarter 2026 pace are management's stated plan; core
   earnings of ~$3.85B/yr against ~$2.1B/yr returned fund it without help.
   The Wellington consideration is **$300M cash at close in Q1 2027** plus a
   seven-year earnout — not $1.9B of proceeds (8-K EX-99.1, 2026-06-03).

**Dominant shared risk factor:** US commercial casualty pricing cycle and
long-tail loss-cost inflation — shared by 2 of 19 other held names (WRB, ORI) ·
4 unlabelled (G, PAGS, PRI, and this name's own prior thesis). `portfolio.db`
is not readable in the headless slot; the held list was taken from
`composite.db` `ticker_scores.in_portfolio = 1` instead, which names the
symbols but not the weights. `research/WRB-2026-09-11.md` reaches the same
count from the other side and states the consequence plainly: three P&C
insurers on one cycle is the real book concentration, and it is an argument
against the next dollar going to any of them.

## 2. Business

Substantially unchanged from `research/HIG-2026-08-13.md` §2; restated in brief
with this run's deltas.

**Created:** Three franchises. (1) *Business Insurance* — P&C for small and
mid-size US businesses, where the customer gets fast automated quoting and
agents consolidate flow onto whoever is easiest to transact with. The CFO's
own metric at the 2026-09-10 KBW fireside chat: "75% of new business quotes
that come through in our small business business are quoted on the glass, no
human touch." (2) *Personal Insurance* — auto/home for the 50+ market under an
exclusive AARP license running through Dec 31, 2032 (10-K Item 1). **New this
run:** the rebuilt product is being extended beyond the AARP direct channel
into the independent-agency segment, live in **23 states** and still rolling
out (KBW, 2026-09-10). (3) *Employee Benefits* — group disability/life plus
absence-and-leave administration.

**Captured:** Underwriting profit plus float income. Q2'26: BI combined 90.4
(underlying 88.6), Personal Insurance combined 98.5 (underlying 87.5 — an
11-point catastrophe and development load), EB core margin 8.9%. Net investment
income $800M in the quarter on $64.0B of investments, against $658M a year
earlier. Asset-management fee income is being monetised and exits in Q1 2027.

**Protected:** Small commercial rests on a workflow and data advantage —
decades of small-business loss experience feeding risk selection, plus agent
integration deep enough that 75% of new-business quotes never touch a human.
Personal rests on a contract: AARP exclusivity to 2032. Benefits rests on
absence-management integration into employer HR systems. None of this stops
Travelers or Chubb; it stops a new entrant, and it explains why small-commercial
pricing held while large property fell. **New this run, and it cuts the other
way:** management is now buying the technology it wants rather than building it
— the stated attraction of the Equitable book is "the technology platform that
comes with this acquisition… from quote, to bind, to installing the cases"
(KBW). A moat you have to acquire is a moat you did not have.

**Control:** One class of common stock, one vote per share, no controlling
holder. Insiders hold **0.33%** of shares out and float is **99.5%** of shares
out (`stocks.db`, 2026-09-09) — the widest possible ownership. Nothing
forecloses an unsolicited approach or an activist campaign except scale and
insurance-regulatory change-of-control approval. This is the null answer, and
it matters in §4: the beta here is not a thin-float artifact.

**Operating leverage (Phase 0): positive.**

| FY | Revenue ($M) | Operating income ($M) | Net income ($M) | Diluted EPS |
|---|---|---|---|---|
| 2021 | 22,349 | 3,099 | 2,350 | 6.64 |
| 2022 | 22,356 | 2,482 | 1,798 | 5.46 |
| 2023 | 24,553 | 3,319 | 2,483 | 7.97 |
| 2024 | 26,560 | 4,075 | 3,090 | 10.35 |
| 2025 | 28,376 | 4,967 | 3,815 | 13.32 |
| TTM (Jun'26) | 29,315 | 5,288 | 4,344 | 15.48 |

FY2021→FY2025: revenue +27.0%, operating income +60.3%, diluted EPS +100.6%.
Operating income has grown more than twice as fast as revenue, and EPS faster
still because the share count fell. That is margin expansion compounded by
buybacks, not mix accounting.

## 3. Threads pulled

- **The Equitable Employee Benefits acquisition — the prior thesis missed it.**
  Announced **2026-08-04**, nine days before the prior write-up, which recorded
  the opposite as a dead end ("Not a serial acquirer… organic focus, nothing to
  announce"). That sentence is now wrong and is corrected here. Terms: ~$500M
  of premium, ~300 employees, expected close Q4 2026, **financial terms not
  disclosed** (company release, 2026-08-04). No 8-K was filed — the deal sits
  below the Item 1.01 materiality threshold, which is itself a size bound.
  Management concedes the acquired book's profitability must be "brought up
  over time" (KBW, 2026-09-10) and states the deal "does not change the
  company's previously announced capital management plans." Read against
  condition 4: ~$500M of premium on a ~$6B EB book is a 7–8% add at a lower
  margin than the 8.9% HIG currently earns, so it dilutes the segment margin
  toward the band rather than through it. Read against condition 1: even a
  $1.5B price would be 4% of market cap. Bounded on both counts — but it is a
  late-cycle capital-allocation tell on a name whose buyback is arguably the
  better use of the dollar.
- **The Wellington consideration is an earnout, not proceeds.** The prior
  thesis leaned condition 3 on "the $4.2B authorization + Wellington proceeds"
  against a stated NPV of $1.9B. The primary document says something narrower:
  "$300 million in cash at closing," plus additional payments over seven years
  based on after-tax cash generated by the combination, with a company-estimated
  NPV of $1.9B, closing **in the first quarter of 2027** (8-K EX-99.1,
  2026-06-03). Upfront cash is 16% of the headline. The condition survives
  because the buyback never needed the money — ~$3.85B of annual core earnings
  against ~$2.1B returned — but the funding story in the prior thesis was
  overstated by roughly six times and is corrected here.
- **Favorable development is halving, and that is the live thread.** Q2'26
  total net prior-accident-year development $(111)M favorable; 6M'26 $(152)M
  against 6M'25 $(309)M — down 51% year over year (Q2'26 investor financial
  supplement). The prior thesis flagged the workers'-compensation redundancy
  funding the casualty adds as "a wasting asset" and listed the size of that
  well as UNKNOWN; this is the first hard number showing it draining. **Bound
  it:** running favorable development from ~$300M/yr to zero costs ~$240M
  after-tax, ~6% of core earnings, ~1.1 points of ROE. A full swing to $300M
  *unfavorable* costs ~$475M after-tax, ~2.2 points of ROE — leaving ~16.5%,
  still 3.3 points above the §4 break-even. The thread is real and it does not
  reach the verdict.
- **Casualty pricing is moderating faster than HIG's own renewal rate.** HIG
  reported GL renewal +9.9% in Q2'26 (prior thesis, from the Q2 call); broker
  indices for the same quarter put general liability and commercial auto each
  around **+4.5%**, down from +6.1% and +5.7% in Q1'26, with umbrella at +5%
  against +8.2% (industry brokerage commentary — low-confidence tier). Two
  readings, and the write-up does not get to pick: either HIG is pricing well
  above market and will hold margin, or the market rate is falling toward a
  level HIG's +9.9% cannot survive another two quarters. Combined with the
  development decay above, this is the strongest version of the bear case —
  pricing above trend decelerating at the same moment the reserve cushion
  drains — and it is exactly what condition 2's PENDING date settles.
- **Nothing adverse has been filed since the prior thesis.** EDGAR sweep for
  CIK 874766, 2026-08-01 to date: two Form 3s (2026-09-09, initial ownership
  statements consistent with the two recently appointed directors), one Form 4
  (2026-08-11), one 8-K (2026-08-11, Items 5.02 and 7.01 — the board
  appointment and its press release). No Form 144, no insider sale, no 8-K
  carrying a reserve charge or a guidance change. Silence since the call, in a
  quarter with a hurricane season running below trend, is a mildly favourable
  reading.
- **Management incentives — the prior thesis's UNKNOWN #1, now closed.** DEF
  14A filed 2026-04-09: the annual incentive funds formulaically off
  *Compensation Core Earnings* (a dollar figure); the long-term plan is 75%
  performance shares / 25% options, and the performance shares pay 50% on
  **three-year-average core earnings ROE** and 50% on peer-relative TSR. The
  2023–25 cycle paid 176% — 168% on a 17.4% average ROE, 183% on TSR at the
  80th percentile. CEO target pay is ~93% variable (7% salary / 18% annual /
  75% LTI); CEO stock ownership guideline 6× salary. **The alignment is good
  where the thesis needs it** — half the LTI is the exact metric condition 1
  rests on, and a 13.2% ROE pays well below target. **The one misalignment is
  real and worth naming:** the *annual* plan pays on core earnings *dollars*,
  which an acquisition adds and a buyback does not. That is the incentive
  structure under which the Equitable deal was signed.
- **Options read (mandatory):** path 2 only (Robinhood stopgap — HIG is not in
  the 24-symbol CBOE catalog and `data/options.db` has no `v_iv_rank` row, so
  path 1 is structurally unavailable, not merely shallow). Metric table,
  liquidity-gate verdict and the timing-check applicability line are in §4.
- **Dead ends.** Short interest 0.02% of float — there is no short case being
  expressed in the tape. Composite carries no HIG flag and coverage is 0.0 in
  the latest snapshot, so the machine has no opinion to check this against.
  The stock's drift from $145.68 (2026-07-29) to $136.36 (2026-09-11), −6.4%,
  brackets the Equitable announcement but is not attributable to it — the
  decline began 2026-08-10, six days after, and no filing marks the date.
  `data/sec_fundamentals.db` carries only the Q2'26 GAAP quarter (revenue
  $7.263B, net income $1.298B, EPS diluted $4.68), which is a definitional
  mismatch against core earnings rather than a data gap; recorded and set
  aside.

## 4. Valuation

**Inputs.** Market cap **$36,936,106,193** (close $136.36 × 270,872,002 shares
out, `stocks.db` 2026-09-09). Total stockholders' equity $19,633M; **common
stockholders' equity excluding AOCI $21,670M** (Q2'26 supplement) → **P/B
ex-AOCI 1.705×**, against 1.92× on GAAP book and a five-year P/B range of 1.32
(FY2021) to 2.02 (FY2025). TTM GAAP net income $4.344B; TTM reported levered FCF
$5.789B (NCFO $5.880B − capex $0.091B).

**Base-flow choice: core earnings, recast basis — not reported FCF.** An
insurer's operating cash flow includes reserve-driven float growth, which is
cash that funds the investment portfolio, not cash an owner can strip while
premiums grow; reported FCF exceeds net income for exactly that reason. The
base used here is **$3.85B**, built two independent ways that agree: (a) 18.7%
trailing core ROE × ~$20.6B average ex-AOCI equity = $3.85B; (b) recast core EPS
of ~$13.82 × ~278M average diluted shares = $3.84B. Both are on HIG's **own
recast basis** — the Q2'26 supplement restates prior-period core EPS about
$0.17/quarter below the figures the broker feed carries (Q2'25: $3.24 in the
supplement vs $3.41 reported; the same $0.17 appears in Q1'25 and Q1'26), and
the recast basis is the one that already excludes what leaves in Q1 2027. The
prior thesis used $4.03B on the un-recast basis; this is a 4.5% reduction to the
base and it is deliberate. Net debt is **0 by the pairing rule** — the flow is
levered, so it pairs with market cap, never with the $41.2B enterprise value.

SBC is not separately reported on the statistics route for HIG, and needs no
haircut here: the base is core earnings, a GAAP-derived measure in which stock
compensation is already an expense. No material minority interests. No pension
or litigation haircut identified.

**Hurdle:** rf **4.95%** (`DGS10`, FRED, 2026-09-10) + beta **0.8** × ERP
**4.14%** (Damodaran, as-of 2026-09-01) = **8.26%**. The screened five-year beta
is **0.45** (`stocks.db`); it is floored into the 0.8–1.2 stable band. Note what
this run does *not* claim: the anchors' thin-float trigger does **not** fire
here — insiders are 0.33% and float is 99.5% of shares out — so 0.45 is a
genuine measurement of a genuinely low-beta business, and the floor is a
deliberate conservatism, not a required correction. At the raw beta the hurdle
is 6.81% and every spread below widens by +145bp. Unlike
`research/WRB-2026-09-11.md`, where flooring beta was the load-bearing choice
that flipped the verdict, here it makes the test harder and the verdict
survives it. The harsher absolute companion — a mature company's cost of
capital ≈ rf + 4.5% = **9.45%** — is also cleared by every run except the
stress cases.

**Terminal growth is 2.36% throughout**, the 10-year breakeven (`T10YIE`, FRED,
2026-09-11) and below the 4.95% risk-free cap. The prior thesis used 2.50%,
above the breakeven; corrected here.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A (recast TTM core, reinvestment uncharged — rejected as headline) | $3.85B | 4% | 2.36% | 13.75% | +549 bps |
| **B (headline: reinvestment charged)** | **$3.026B** | **4%** | **2.36%** | **11.33%** | **+307 bps** |
| C (no growth, 100% payout coherent) | $3.85B | 0% | 2.36% | 12.04% | +377 bps |
| D (mid-cycle core ROE 14%, charged) | $2.143B | 4% | 2.36% | 8.73% | +47 bps |
| E (break-even probe: core ROE 13.0%, charged) | $1.935B | 4% | 2.36% | 8.12% | −14 bps |
| F (reported levered FCF — rejected, float-inflated) | $5.789B | 4% | 2.36% | 19.40% | +1113 bps |

Runs B, D and E charge the reinvestment that growth costs. For an insurer that
reinvestment is statutory surplus: growing premium at *g* requires retaining
*g*/ROE of earnings. Run B retains 21.4% (4% growth at an 18.7% core ROE), Run D
28.6% (14% ROE), Run E 30.8% (13% ROE). Run A does not, and the solver's
`growth without reinvestment` warning fires on it — which is why A is shown and
not used. This is the same correction `research/WRB-2026-09-11.md` applied to
its own predecessor, made here before the number was quoted rather than after.

- **The reinvestment/terminal-ROE warning, answered.** Runs A and C trigger it;
  in both, terminal growth is set exactly at the 10-year breakeven, so all
  terminal growth is inflation repricing of existing assets and real growth is
  zero — repricing needs no reinvestment, so 100% payout is coherent there.
  Runs B/D/E answer it by charging the explicit-period reinvestment instead.
  Read `implied_terminal_roe` two-sided: **11.03%** in Run B is 2.8 points above
  the 8.26% hurdle — inside the "tough to do beyond ~5 points" band; **8.26%**
  in Run D is exactly the hurdle, i.e. excess returns fully faded; **7.67%** in
  Run E is *below* it, a terminal value that assumes value destruction forever.
  None of these require HIG to be one of the ~29% of firms that earn above
  their cost of capital in perpetuity (Damodaran EVA dataset, 2026 vintage).
- **The break-even, stated plainly.** The price earns exactly its cost of
  equity at a permanent mid-cycle core ROE of about **13.2%** — between Runs D
  and E. HIG's 2021–22 core ROE was 12.5–13%, earned with a 1.5% 10-year
  Treasury. Reverting there now requires underwriting worse than 2021's,
  because NII is $800M/quarter against $658M a year ago (+21.6% on $64.0B of
  investments) — about two points of ROE added in twelve months on a $21.67B
  equity base, and considerably more against 2021.
- **Gordon cross-check, independent of the DCF.** At 1.705× book ex-AOCI with
  k = 8.26% and g = 2.36%, the implied perpetual ROE is 1.705 × (0.0826 −
  0.0236) + 0.0236 = **12.4%** — the same answer the reverse DCF reaches by a
  different route, against a trailing core ROE of 18.7%.
- **Market-share sentence.** 4% for five years takes revenue from $29.3B to
  ~$35.7B. Against a US P&C direct-written-premium market in the high hundreds
  of billions growing mid-single digits (approximate reference figure), HIG's
  share is roughly flat. No bigger-than-the-market failure.
- **Base-year cash tax.** Cash tax 19.4% of pretax against a 21% marginal rate
  — no NOL or deferral flattering the base.
- **Serial-acquirer check.** `fcf = NCFO − capex` excludes acquisition spend,
  and HIG has now signed one (Equitable, price undisclosed). The base used here
  is core earnings rather than FCF, and the growth path is organic; the
  Equitable premium is ~1.7% of revenue and is not in the 4% path. If the
  purchase price proves large it is a one-time capital charge, not a growth
  subsidy — but the check is named rather than assumed away.
- **Asset-light / commitments.** Capex $91M on $29.3B of revenue. An insurer's
  capital intensity lives in reserves and statutory surplus, not in property —
  and Runs B/D/E now charge that surplus explicitly, which the prior thesis's
  headline run did not.
- **Terminal risk (Item 1A sweep).** The dominant structural risks are
  catastrophe/climate exposure and long-tail casualty reserve estimation. A
  2.36% terminal rate — pure expected inflation, zero real growth — survives
  both: P&C contracts reprice annually, so loss-cost inflation flows into
  premium, and cat and reserve shocks hit capital episodically rather than
  eliminating premium growth. Runs D and E additionally let excess returns fade
  to or below the cost of equity.
- **Distribution clamp.** The US median cost of capital is 7.79% and 80% of
  firms sit between 5.26% and 9.88% (Damodaran Data Update 5, 2026). Every run
  except E sits at or above the top of that band; E at 8.12% sits mid-band. No
  run lands below the 10th percentile, so the strong-pass clamp does not fire.

**Options-implied move (path 2 — Robinhood stopgap; HIG is not in the CBOE
catalog and `data/options.db` has no `v_iv_rank` row, so path 1 is structurally
unavailable).** 2026-12-18 $135 straddle — the nearest listed expiry that
brackets the 2026-10-26 AMC print and its 2026-10-27 repricing; the 2026-10-16
listing expires before the print and there is no November listing. Spot 136.36,
DTE 96, call mark 7.10 / put mark 5.05, ATM IV = mean(0.204518, 0.227615) =
**21.61%**:

| metric | value |
|---|---|
| spot | 136.36 |
| dte (calendar days) | 96 |
| expected absolute move (MEAN, not a ceiling) | 8.91% |
| 1-σ move | 11.08% |
| ATM IV | 21.61% |
| RV60 | 20.57% |
| IV > RV60? | YES |
| IV > RV20? | YES |
| RV20 | 18.02% |

Both windows read YES, which is the rule's definition of elevated — but the
stopgap caveat applies with full force here and the margin is one vol point:
the December expiry spans a scheduled earnings date that the 20-day realized
window does not contain at all. A 1.04-point premium to 60-day realized is the
market pricing a known calendar item, not a discovery. **Liquidity gate
FAILED** — call spread $6.40/$7.80 = $1.40 against a 10%-of-mark threshold of
$0.71; put spread $4.50/$5.60 = $1.10 against $0.51; same-day volume 0 (call)
and 4 (put), both far under 100. The read is therefore **UNRELIABLE** and moves
no verdict in either direction. **Timing check: not applicable** — this thesis
states no dated move requirement, so there is nothing for the 2-sigma test to
refute, and an implied move that happens to match what a thesis wants is not
evidence for the thesis.

No equity-as-option lens: net debt is $4.259B against a $41.2B enterprise value
(10.3%), book equity is positive at $19.6B, and there is no going-concern
language. The leverage gate does not fire.

## 5. Falsifiers

- **Break —** casualty reserves: a single-quarter GL plus commercial-auto
  strengthening above $200M; or strengthening that reaches accident years
  2024–25; or **total** P&C prior-year development turning net unfavorable for
  two consecutive quarters. Condition 2 has failed and the pricing-above-trend
  claim with it.
- **Break —** underwriting discipline: BI underlying combined ratio above 95
  for two consecutive quarters absent an identified one-off. Condition 3 has
  failed.
- **Break —** earnings power: trailing core earnings ROE below **14%** for two
  consecutive quarters. That is the last rung above the §4 break-even, and
  below it the price is no longer being paid for.
- **Shift —** pricing cycle: BI renewal written pricing ex-comp below ~4%
  while premium growth stays positive — growth bought with margin. Revalue on
  a lower base.
- **Shift —** Employee Benefits: core margin below 6% (out of the stated band)
  for a full year, or an Equitable purchase price disclosed above ~$1.5B.
  Revalue; neither breaks the story.
- **Shift —** capital allocation: a second acquisition announced before the
  Equitable integration is through, or the $475M/quarter buyback pace cut
  without a stated reason. The annual incentive pays on core earnings dollars;
  this is the observable that would show it driving the decision.
- **Shift —** the multiple: a de-rating below ~1.4× book ex-AOCI on unchanged
  fundamentals is the §1 closest attack playing out. That is a revaluation
  opportunity, not a sell — but it is the likeliest way this position loses
  money over the next two quarters.

**Reopen trigger:** 2026-10-26: hig-q3-total-pyd-net-favorable-with-core-roe-at-or-above-17-and-bi-underlying-cr-below-90

## 6. UNKNOWNs

1. **PENDING 2026-10-26** — Q3'26 total P&C prior-year development. Condition 2
   is a forecast whose decisive disclosure is dated; the Q3 release settles the
   direction and the Q4 annual reserve review settles the magnitude. Its
   absence does not kill the thesis: §3 bounds a full swing from today's
   favorable development to an equal-sized unfavorable one at ~2.2 points of
   ROE, leaving ~16.5% against a 13.2% break-even.
2. **PENDING (first 10-Q or 10-K after close, expected Q4 2026 / FY2026 10-K)**
   — the Equitable purchase price. Undisclosed in the announcement and no 8-K
   was filed, but the ASC 805 business-combination note will carry the
   purchase-price allocation and the pro-forma figures. Not load-bearing at
   plausible sizes: ~$500M of premium, and even a $1.5B price is 4% of market
   cap.
3. **UNKNOWN** — the reason for the ~$0.17/quarter recast of prior-period core
   EPS in the Q2'26 supplement. The gap is constant across Q1'25, Q2'25 and
   Q1'26, which is the signature of a definitional recast rather than a data
   error, and the most likely cause is the Hartford Funds business moving to
   held-for-sale after the 2026-06-03 agreement — but this run did not confirm
   it, and the supplement does not state it in the portion read. The inference
   is **not** relied on: §4's base is built on the recast numbers whatever the
   cause, which is the conservative side of the question either way.
4. **UNKNOWN** — true mid-cycle underwriting margin. Unknowable in advance and
   the honest gap in any insurer thesis written at a cycle top. Bounded rather
   than assumed away: Runs D and E price it at 14% and 13% core ROE
   respectively.
5. **UNKNOWN** — the remaining size of the workers'-compensation reserve
   redundancy that has funded the casualty additions. Not disclosed as a
   figure. Its exhaustion is a slow leak that the first Break falsifier catches
   as net-unfavorable total development. The 51% year-over-year decline in
   favorable development is the first visible evidence of the drain and is now
   in the falsifier list rather than in prose.

*Possible-tier, not a condition and not counted:* the agency-channel rollout of
the rebuilt Personal Insurance product (23 states as of 2026-09-10) could turn a
segment currently running a 98.5% combined ratio into a growth line. There is no
disclosure that says when or how much, so it is option value in §6, not a
numbered condition.

## 7. Sources

- **Primary:** Q2'26 investor financial supplement, 8-K EX-99.1 filed
  2026-07-23, acc. 0000874766-26-000059 (core earnings $945M / $3.42; 6M'26
  $1,757M / $6.32; core ROE TTM 18.7%; book value per diluted share ex-AOCI
  $78.91; common equity ex-AOCI $21,670M; BI combined 90.4 / underlying 88.6;
  PI combined 98.5 / underlying 87.5; EB core margin 8.9%, group disability
  loss ratio 74.0%; total PYD Q2'26 $(111)M, 6M'26 $(152)M, Q2'25 $(187)M,
  6M'25 $(309)M; cat losses Q2'26 $222M; NII $800M vs $658M; total investments
  $63,999M). 8-K EX-99.1 filed 2026-06-03, acc. 0000874766-26-000043
  (Wellington: $300M cash at closing, seven-year contingent payments, stated
  NPV $1.9B, Q1 2027 close). DEF 14A filed 2026-04-09, acc. 0000874766-26-000025
  (incentive metrics and weights, CEO pay mix, ownership guidelines). Company
  news release 2026-08-04 (Equitable Employee Benefits: ~$500M premium, ~300
  employees, Q4 2026 close, terms not disclosed). FY2025 10-K filed 2026-02-20
  (AARP licence through 2032, Item 1A risk factors). EDGAR filing index for CIK
  874766 (the 2026-08-01-to-date sweep). `data/sec_fundamentals.db` Q2'26 GAAP
  row (revenue $7.263B, net income $1.298B, EPS diluted $4.68).
- **stockanalysis.com (vetted exception):** `/stocks/HIG/statistics/` and the
  screener capture behind `data/stocks.db` (price, market cap, share count,
  beta, ownership, ratios, forward estimates); `/stocks/HIG/financials/`
  (FY2021–FY2025 income statement); `/stocks/HIG/financials/ratios/` (annual
  ROE and P/B history); `/stocks/HIG/transcripts/` route and the
  primary-transcribed KBW Insurance Conference fireside chat of 2026-09-10
  (detailSlug `745220-kbw-insurance-conference-2026`) — a company disclosure
  transcribed by a third party, quoted as primary for what management said.
- **Broker/market microstructure:** Robinhood MCP — live quote and official
  2026-09-11 close, daily bars for the realized-vol series, option chain,
  instruments and quotes for the implied-move table, and the estimate-vs-actual
  earnings series. Admissible because no already-integrated official source
  covers real-time quotes, option marks or consensus estimates for this ticker.
  The earnings *actuals* were cross-checked against HIG's own recast core EPS
  and the $0.17/quarter disagreement is reported in §4 and §6 rather than
  silently averaged away.
- **Reference data:** Damodaran home page — implied ERP 4.14%, as-of
  2026-09-01; cost-of-capital distribution (US median 7.79%, 10th–90th
  percentile 5.26%–9.88%) and the ~29% above-cost-of-capital base rate, 2026
  vintages; the 0.8–1.2 stable beta band and the rf+4.5% mature-company
  companion.
- **Point-in-time repo DBs:** `data/stocks.db` (2026-09-09 snapshot — price
  $136.56, beta 0.45012, insiders 0.33%, float 99.5%, short float 0.02%, next
  earnings 2026-10-26 amc, roe 22.06%/roe5y 16.62%, P/B 1.92); `data/fred.db`
  (DGS10 4.95% at 2026-09-10, T10YIE 2.36% at 2026-09-11); `data/earnings.db`
  (EDGAR-estimated 2026-10-22, no `event_time`); `data/composite.db` (no HIG
  flag, coverage 0.0; `in_portfolio = 1`; the held-symbol list used for the §1
  overlap count); `data/options.db` (no `v_iv_rank` row for HIG — path 1
  unavailable); `research/WRB-2026-09-11.md` and `research/HIG-2026-08-13.md`
  within this corpus.
- **Low-confidence:** industry brokerage commentary on 2026 commercial rate
  movement (property −8.1% in Q2'26, fifth consecutive decline; GL and
  commercial auto ~+4.5% in Q2'26 against +6.1% and +5.7% in Q1'26; umbrella
  +5% against +8.2%; median US nuclear verdict $21M in 2020 to $51M in 2024) —
  used in §3 to set a market baseline against HIG's disclosed +9.9% GL renewal
  rate, never as a substitute for a company disclosure. Seasonal catastrophe
  outlook for H2 2026 (below-average Atlantic activity on a strengthening El
  Niño; H1 2026 global insured cat losses ~$42–47B, below trend) — context
  only, not in any condition.

## Kill-thesis record

**SOUND** — conditions=5 (4 probable, 1 plausible), refuted=0, unknown=0,
**pending=1**, not_obtained=0.

Per-condition adjudication:

1. *Mid-cycle core ROE holds above ~13.2%* — **SURVIVED** at *probable*. Attack
   run: every driver of the last three years' ROE expansion is reversing at
   once — property pricing down five straight quarters, casualty rate increases
   moderating, favorable development halving, EB margin two points above its
   own band, Personal Insurance already at a 98.5% combined ratio. The attack
   is serious and it does not reach the break-even. The defence is one primary
   number: NII $800M/quarter against $658M a year ago on $64.0B of investments,
   about two points of ROE added in twelve months on $21.67B of ex-AOCI equity,
   with the 10-year at 4.95% against ~1.5% when HIG last earned 13%. A
   round-trip to 13% therefore needs underwriting *worse* than 2021's, and
   Q2'26 BI underlying combined is 88.6.
2. *Total P&C prior-year development stays net favorable* — **PENDING
   2026-10-26**. This is a dated forecast, not an unknowable, and what bears on
   it today cuts both ways: 6M'26 $(152)M is still favorable but is half of
   6M'25's $(309)M, and management describes the Q2 additions as "modest
   adjustments… in general liability and a little bit in commercial auto"
   (KBW, 2026-09-10) against a monitored social-inflation backdrop. Not
   credited as SURVIVED; the Q3 print settles it.
3. *BI underlying combined ratio stays below 90* — **SURVIVED** at *probable*.
   Attack run against the soft market: the softening is concentrated in large
   commercial property, which is de minimis in HIG's book, and the underlying
   ratio has been improving rather than deteriorating (88.6 in Q2'26).
4. *EB core margin does not fall below the 6–7% band after Equitable* —
   **SURVIVED** at *probable*. Attack run: the margin is 8.9%, two points above
   the band's top, so mean reversion is a certainty rather than a risk, and the
   acquired book's profitability is conceded to need improvement. The attack
   bounds at ~$150M/yr, ~0.7 points of ROE — inside Run D — and produces no
   evidence that the margin goes *below* 6%, which is what the condition says.
5. *Capital return executes out of operating capital generation* — **SURVIVED**
   at *plausible*. Attack run, and it landed on the prior thesis rather than
   this one: the Wellington consideration is $300M cash at a Q1 2027 close plus
   a seven-year earnout, not $1.9B of proceeds. The condition survives only
   because it was restated to remove that dependency — ~$3.85B of core earnings
   against ~$2.1B returned funds the pace unaided. The 2027+ pace is not
   committed, hence *plausible*.

Standing checks. **Base rate:** only ~29% of firms earn above their cost of
capital in perpetuity (Damodaran EVA dataset) — Runs D and E do not require HIG
to be one of them; Run D's terminal ROE is exactly the hurdle and Run E's is
below it. **Short case, strongest version:** a peak-cycle insurer at a
peak-cycle multiple (1.92× GAAP book against a 1.32× low four years ago), where
every ROE driver is reversing simultaneously, management is answering a
softening market by buying a sub-scale book at an undisclosed price whose
profitability it concedes must be fixed, 2027 loses the asset-management
earnings for $300M of cash, and the stock has gone nowhere for a year
(ch1y +4.5%) while the index made highs. That case is coherent and it is why
p(beat SPY) is near a coin flip — but it argues for a lower multiple, not for
a price below the DCF's fair value. **Management incentives:** well aligned
where it matters (50% of the LTI is three-year-average core earnings ROE, 50%
relative TSR, CEO pay 93% variable, 6× salary ownership guideline), with one
genuine misalignment named — the annual plan pays on core earnings *dollars*,
which an acquisition delivers and a buyback does not, and that is the plan under
which the Equitable deal was signed. **Disconfirming search:** run deliberately
against the company (broker rate indices, post-call filing sweep, the recast
discrepancy, the earnout terms), and it produced three corrections to the prior
thesis rather than confirmations. **Moat as mechanism:** small commercial passes
— 75% of new-business quotes bind with no human touch, on decades of proprietary
small-business loss data; Personal is a contract to 2032, which is a mechanism
with an expiry date, stated. Benefits is the weakest leg, and management is now
buying the technology rather than owning it.

Internal-consistency check passes: the thesis does not simultaneously claim high
growth, low reinvestment and low risk. The headline run charges 21.4% of
earnings to reinvestment for its 4% growth, terminal growth is capped at
expected inflation, and the stress runs let excess returns fade to or below the
cost of equity. **Statistical checks:** not applicable — no backtest, screen or
repo signal underwrites this thesis (composite has no HIG flag). **Options
timing check:** N/A — the thesis states no dated move requirement; separately,
the path-2 read is UNRELIABLE on a failed liquidity gate and path 1 is
structurally unavailable for this ticker.

**Closest attack:** multiple compression, not cash-flow deterioration. The
reverse DCF prices perpetual ownership and says the price holds down to a 13.2%
mid-cycle ROE; the market has never paid 1.7× book ex-AOCI for a 13–14% ROE
insurer, and HIG's own P/B was 1.32 as recently as FY2021. At 1.4× book ex-AOCI
the stock is ~$110, −19%, on fundamentals that never fell below Run D. Nothing
in the condition list catches this, because it is a repricing rather than a
refutation — which is exactly why it is the closest thing to a kill.

**Flip evidence — toward FLAWED:** a Q3'26 print showing total prior-year
development net unfavorable, or a second consecutive quarter of favorable
development halving, alongside BI renewal pricing ex-comp below 4%. That is
condition 2 refuted and condition 1 under direct threat in the same disclosure.
**Toward staying SOUND:** the same print with total development still net
favorable, core ROE at or above 17%, and BI underlying combined below 90.

**p(beat SPY, 63 td): 0.48** — written before re-reading §1's number. The value
case is comfortable and the horizon is too short to collect on it; a 0.45 beta
means the name lags a rising index, the Q3 print inside the window carries
genuine downside asymmetry given the development trend, and the de-rating risk
in the closest attack has no offsetting catalyst before year-end.
