# YOU — Clear Secure, Inc. — 2026-09-08

Price $43.60 (official close, 2026-09-08) · market cap $5,898,560,375 ·
market cap net of excess cash $5,049,058,375 · next earnings 2026-11-04
(`earnings.db`, `edgar-estimate`) or 2026-11-05 BMO (Robinhood, unverified)

Supersedes `research/YOU-2026-08-08.md`. Unattended scheduled run. This is
**not** a reopen run — that thesis's trigger is dated 2026-11-05 (the Q3 print)
and has not come due — so there is no §0; the month's delta is pulled as the
first thread in §3 instead. YOU is a live holding (composite's
`portfolio_holding` signal carries a position in it as of 2026-09-08); the
prior run logged BUY at $51.35 and the name is ~15% lower since.

## 1. Verdict and thesis

**BUY at $43.60.** kill-thesis: **UNPROVEN** — conditions=5, refuted=0,
unknown=2.

**p(beat SPY, 63 td): 0.56** · kill-thesis: 0.47 — **Disputed expectation:**
the price implies roughly 11–13%/yr against a 9.01% hurdle on cash flows
haircut for SBC, the tax-receivable agreement and interest income, i.e. it is
already paying for a growth stall; what revises it is the Q3 print — Amex
renewal economics, the sequential Active CLEAR+ trajectory, and whether the
+20.5% revenue guide survives a quarter in which US checkpoint throughput ran
negative.

CLEAR is a prepaid-subscription toll booth on US air travel with a young B2B
identity attach, net cash $849.5M against a $5.90B market cap, a 25.1% GAAP
operating margin and strongly positive operating leverage. It has now fallen
37% from the intraday all-time high set on its own beat-and-raise earnings day
(2026-08-05, $69.07) to $43.60, and the EDGAR record over that month is empty
of anything adverse: **no 8-K since 2026-08-05**, no 10-Q amendment, and the
only filings are routine RSU-vest and 10b5-1 sales. Two things that did happen
were positive — JPMorgan initiated Overweight at a $55 target (~2026-08-24) and
CrowdStrike shipped a CLEAR1 integration into the Falcon platform
(2026-08-31). At this price a bear case in which growth all but stops (4%
fading to 2%, on cash flow already cut for SBC, TRA and interest, solved
against market cap net of the cash pile) still implies 11%/yr, +196bp over the
hurdle. That is the thesis: not that CLEAR compounds, but that it no longer
has to.

**Closest attack:** the hurdle is doing work it may not deserve. Every
scenario's implied return (11–16%) sits *above* the top of Damodaran's 80%
cost-of-capital band (5.3–9.9%), and the options market prices 56% ATM IV on a
name whose 5-year beta is 1.02. Both say the market demands more than 9.01%
for this risk. At a true 12% required return the conservative case's +318bp
goes to roughly zero and the bear case turns negative. Refutes nothing;
compresses the margin of safety from "cheap" to "fair on conservative
assumptions." Detail in the Kill-thesis record.

Load-bearing conditions (count: 5). CLEAR1's B2B compounding is deliberately
*not* among them — the CrowdStrike, AWS and Samsung integrations carry no
disclosed economics and the segment's revenue split has never been broken out,
so it is upside option value, not a leg the base case stands on.

1. **Retention holds near last-published levels** (~87% GDR) — *plausible
   only*: management discontinued the metric as of Q1'26 while it was
   declining (§3, retention thread). Unattackable, not disproved.
2. **Declining US air-travel volume is a trim to growth, not a break in the
   subscription base** — *plausible*: throughput ran −0.9% y/y in July and
   roughly −3.7% in August, but the first week of September came back to
   +0.2% (§3, TSA thread). One bad month, not an established trend.
3. **Bookings growth stays double digits** — *probable*: Q2'26 bookings
   +32.8% y/y, four consecutive quarters ≥17%, Q3 revenue guided +20.5%.
4. **Amex renewal preserves partner-funded economics** — *plausible*: the
   renewal exists and is in effect; terms undisclosed until "the appropriate
   time," with $315M of accrued partnership liability settling in Q3.
5. **TSA's free Touchless ID does not commoditize the paid queue-jump within
   the terminal horizon** — *plausible*: priced by setting terminal growth to
   the 10-year breakeven, i.e. zero real growth forever, not by assuming the
   risk away.

**Dominant shared risk factor:** US discretionary air-travel volume — shared
by 1 of 19 held names (EEFT, whose factor line reads "cross-border movement of
people"; a global contraction in people travelling fails both) · 6 unlabelled
(G, HIG, ORI, PAGS, PRI, WRB — theses exist from mid-August but predate the
factor line). Holdings enumerated from `composite.db`'s `portfolio_holding`
signal, since this slot has no `portfolio.db` grant.

## 2. Business

**Created:** sells *time and certainty on the day of travel*. A dedicated
biometric identity lane — increasingly eGates, sub-5-second verification, at
50 airports and >70% of the network — puts a member at the front of the
security queue at 62 US airports; the app adds wayfinding and concierge. At
$219/yr and last-published usage of ~7x/yr, a frequent flyer is buying queue
position for ~$31 per trip. CLEAR1 sells enterprises verified-human onboarding
and fraud reduction.

**Captured:** four distinct mechanisms, not one. (a) Prepaid annual consumer
subscriptions — $219 standard since 2026-07-01, $125 family, plus
airline- and Amex-subsidised tiers — collected upfront, which is why deferred
revenue sits at $573.0M and functions as a working-capital float. (b)
Partner-funded distribution: Amex and card-issuer statement credits and
airline tiers pay for members, accrued as a $315M partnership liability that
pays out each Q3. (c) TSA PreCheck enrollment fees — CLEAR is a
TSA-authorised enrollment provider at 280 retail locations. (d) CLEAR1 B2B
subscription contracts. Against all of it, CLEAR pays airports a revenue share
of roughly 14% of revenue.

**Protected:** a mechanism, not a label — (i) finite physical lane real estate
at 62 airports under multi-year revenue-share contracts that a competitor must
win airport by airport; (ii) a regulatory certification stack (TSA Registered
Traveler, SAFETY Act qualified anti-terrorism technology, FISMA High); (iii) a
43.5M-identity enrolled network reused across venues and CLEAR1 partners. The
hole is named and not papered over: the one competitor that needs neither an
airport contract nor a certification is the government itself.

**Control:** four classes of common stock are outstanding. The 10-Q balance
sheet at 2026-06-30 shows Class A 101,961,485, Class B 151,787, Class C
14,246,787, Class D 18,380,246 (134,740,305 total); the cover page reports
135,288,082 across all classes at 2026-07-31 — exactly the `sharesOut`
stockanalysis uses, which is the check that makes §4's pairing legitimate. The
per-class vote multiple and whether CLEAR is a "controlled company" under NYSE
rules could **not** be located in the 10-Q this run and are UNKNOWN (§6);
they would come from the charter or the DEF 14A. What is established is that a
four-class structure exists and that pre-IPO holders sit in the non-A classes
through Alclear — the governance backdrop against which management retired
three declining KPIs (§3).

**Operating leverage (Phase 0): strongly positive.** FY revenue / operating
income: 2021 $254.0M / −$114.9M → 2023 $613.6M / +$20.1M → 2025 $900.8M /
+$186.5M → TTM $1,000.7M / +$251.5M. TTM operating margin 25.13%, gross margin
66.66%. Revenue has roughly quadrupled since 2021 while operating income went
from a $115M loss to a $251M profit — the direction is unambiguous, and stock
compensation ($43.2M TTM, 4.3% of revenue) is charged inside those figures.

## 3. Threads pulled

- **The month since the prior thesis: another −15%, and the tape is again the
  only witness.** From the 2026-08-07 close of $51.29 the stock ground to
  $42.71 intraday on 8/20 and has chopped $42.85–45.77 since, closing $43.60
  on 9/8. SPY over the identical window went $773.26 → $765.96, −0.9%. So
  ~14 points of idiosyncratic drawdown. The EDGAR record for that month,
  confirmed against the `browse-edgar` atom feed rather than a summarised
  submissions blob: **the most recent 8-K is 2026-08-05** (the Q2 earnings
  8-K) and the most recent 10-Q is the same date. Nothing was filed. News over
  the window was net positive — JPMorgan (Bryan Smilek) initiated Overweight,
  $55 PT, ~2026-08-24; CrowdStrike announced the CLEAR1/Falcon integration on
  2026-08-31. Short interest *fell* over the decline (11.42M shares latest vs
  12.5M in the prior thesis; 12.46% of float, days-to-cover 7.65 vs 10.3), so
  this is shorts covering into a fall, not a fresh short campaign.
- **TSA checkpoint throughput — the thread that nearly changed the verdict,
  and then partly unwound.** DA Davidson's July note explicitly cited "TSA
  checkpoint data," so I pulled the primary source (tsa.gov passenger
  volumes). Monthly totals: July 2026 86,556,939 vs July 2025 87,358,365
  (**−0.92%**); August 2026 78,462,677 vs August 2025 81,459,227
  (**−3.68%**). That looked like a deteriorating end market and the best
  available explanation for a no-news decline. Then the disconfirming search
  turned up the September reversal, which I verified by summing the daily
  table myself: **Sept 1–7 2026 = 16,444,072 vs Sept 1–7 2025 = 16,408,202,
  +0.22%**. Two caveats on my own numbers, both cutting against overreading
  them: the *monthly* totals were summed by a fetch-summarising model, not by
  me, and an outside source computes August at −4.4% rather than −3.7% — call
  the August figure ±1pp; and calendar composition biases it, since August
  2026 (starting Saturday) carries an extra Monday where August 2025
  (starting Friday) carries an extra Friday, and Friday is the heavier travel
  day. Net finding: **the US air-travel pie stopped growing and had one clearly
  negative month, but "deteriorating" is not established** — the first week of
  September was flat-to-up. This becomes condition 2 and a falsifier, not a
  kill.
- **Retention disclosure discontinued mid-decline (still the biggest knock).**
  Published series through the Q1'25 letter: Annual CLEAR+ Net Member
  Retention 86.3% (Q4'23) → 81.4% (Q4'24); Gross Dollar Retention 89.8% peak
  (Q1'24) → 88.5% (Q4'24) → 87.3% (Q2'25); Annualized Usage 8.1x → 7.1x. On
  the Q4'25 call management said it would discontinue three metrics —
  cumulative platform uses, annual CLEAR+ gross dollar retention, and annual
  CLEAR+ member usage — beginning Q1'26. The Q2'26 KPI table now carries only
  Total Bookings, Total Members, Active CLEAR+ Members. Current retention is
  therefore **UNKNOWN by design**, and no triangulation exists because gross
  adds are not disclosed. Unchanged this month; nothing re-disclosed.
- **Insider selling: the cadence broke, and it broke upward.** The prior
  thesis's sharpest adverse observation was a biweekly Form 4 cadence from the
  founder/Alclear Investments running all year, culminating in ~324k shares
  sold at $60.52–68.45 into the 8/5–8/6 earnings spike. Reading the filer
  index since: that filer pair (CIKs 0001466453 / 0001869246) filed on
  2026-06-17, 6/25–6/26, 7/7, 7/15, 7/16, 7/17 and 2026-08-07 — and **has
  filed nothing in the month since**. The only Form 4s in the window are
  2026-09-03 and are routine: Michael Barkin (President) 11,444 shares at $45
  under a 10b5-1 plan adopted 2026-02-27; Kyle McLaughlin (EVP Aviation) an
  RSU vest, sell-to-cover and 4,499-share sale at $44.47 under a plan adopted
  2026-03-04; Dennis Liu (CAO) the same pattern, 2,104 shares at $44.47 under
  a plan adopted 2026-05-14. This resolves prior UNKNOWN #4 for these filers
  (all 10b5-1) and removes the "founder selling into strength" overhang for
  now. A stopped 10b5-1 allotment is an equally good explanation, so this is a
  removed negative, not a new positive.
- **The buyback, which is where the bear case is strongest.** Repurchases fell
  to $1.2M in H1'26 from $126.3M in H1'25, and FY2024's programme bought 13.8M
  shares at an average $19.78. Management then repurchased ~$22M quarter-to-
  date at an average $52.73 as of the Q2 call. The stock now trades 17% below
  that average. Two readings: disciplined (they bought at $20, stopped at $50)
  or informed (they stopped for a reason). The Q3 10-Q settles it — a large
  buyback in the low $40s confirms the first reading, a second idle quarter
  confirms neither and is itself a signal. Note the associated bear claim that
  "diluted shares climbed to 102.8M from 94.4M" is a **misread of the Up-C
  structure**: those are Class C/D units converting into Class A, and the
  all-class count went 136.9M (Feb 2025) → 134.7M (Jun 2026) → 135.3M (Jul
  2026), i.e. roughly flat to slightly down. That specific bear point is
  refuted; the buyback-collapse point is not.
- **Amex/partner economics.** Unchanged and still undisclosed: the new
  agreement is in effect, the $315M accrued liability settles in Q3 (making Q3
  FCF negative as in prior years), and the CFO said only that more would come
  "at the appropriate time." H1'26 OCF of $391.5M includes a +$152.0M
  accrued-liability build, so TTM FCF is timing-flattered by the partner
  float; the FY guide (≥$480M, post-payout) is the honest annual number.
- **CLEAR1 distribution is compounding, economics are not disclosed.**
  CrowdStrike/Falcon (2026-08-31) joins AWS Connect (~July) and Samsung
  (~June); the CrowdStrike release says the integration is available to
  existing customers of both companies "starting today" and discloses no
  pricing, revenue share or minimum. That is real distribution and zero
  quantifiable economics — hence its exclusion from the load-bearing set.
- **Options read (mandatory):** path 2 only — the Robinhood stopgap. YOU is
  not in the 24-symbol CBOE catalog so no path-1 `iv30` percentile exists.
  Table, liquidity verdict and DTE in §4.
- **Dead ends (work done, nothing found):** searched for an adverse corporate
  event behind the decline across the news feed, the 8-K atom feed and the
  full submissions index — nothing. Checked whether the Robinhood
  estimate-vs-actual pattern shows managed guidance: four small misses through
  2025 (Q1'25 −$0.04, Q2'25 −$0.02, Q3'25 −$0.01, Q4'25 −$0.07) then two beats
  in 2026 (+$0.02, +$0.03) — consistent with the eGates cost inflection, not
  with a beat-by-a-hair pattern. Composite now scores YOU 0 bullish / 0
  bearish with 0.0 coverage — the `si_days_to_cover` flag that first surfaced
  it has lapsed, so no machine opinion supports or opposes this run; the only
  ticker rows are the two informational annotations (`sa_fscore` 6,
  `sa_fcf_yield` 8.48). Commitments footnote (10-Q Note 16) re-checked as
  unchanged since the last filing: airport minimum annual fees $86.3M through
  2030+, stadium marketing $5.1M, no take-or-pay that threatens the
  asset-light base (TTM capex $34.3M = 3.4% of revenue).

## 4. Valuation

Inputs, 2026-09-08. Shares outstanding **135,288,082** across all four
classes (10-Q cover, 2026-07-31) × $43.60 = market cap **$5,898,560,375**.
Cash $959,268,000 less debt $109,766,000 = net cash **$849,502,000**; market
cap net of that excess cash is **$5,049,058,375**. TTM levered free cash flow
**$508,393,000** (= NCFO $542,645,000 + capex −$34,252,000). It is
post-interest under US GAAP, so it pairs with **market cap** and `--net-debt`
stays at zero throughout; enterprise value is the wrong denominator for this
flow and is never used below. TTM SBC $43,240,000 (4.32% of revenue) →
FCF−SBC $465,153,000. Consolidated TTM net income ≈$230.7M — Q3'25
$45,144,000, Q1'26 $56,384,000 and Q2'26 $72,310,000 verified against SEC
XBRL `us-gaap:ProfitLoss`, with Q4'25 (~$56.9M) inferred as the residual since
the fourth quarter is only derivable from the 10-K.

**The Up-C pairing, verified rather than inherited.** The usual holdco trap
is that consolidated FCF includes cash belonging to minority holders while
market cap prices only the parent. It does not bite here: the 10-Q cover's
all-class count (135,288,082) is *exactly* the share count behind the quoted
market cap, so the price is capitalising the whole LLC, not the Class A slice.
Consolidated FCF therefore pairs with it and **no NCI haircut applies**. The
haircuts that do apply are charged in the conservative and bear runs: the
tax-receivable agreement to pre-IPO holders (~$28.5M/yr run-rate) and
after-tax interest income on the cash pile (~$21.4M), giving a conservative
base of $415.25M, solved against market cap net of that cash.

Hurdle: **rf 4.78%** (DGS10, 2026-09-04, `data/fred.db`) **+ beta 1.02075 ×
ERP 4.14%** (Damodaran implied ERP, as of 2026-09-01) = **9.01%**. Beta sits
inside the 0.8–1.2 stable band, so no clamp. Terminal growth is set to the
**10-year breakeven `T10YIE` 2.37% (2026-09-08)** in every scenario — the
default ceiling, claiming no real terminal growth at all.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| Bear — travel stall (cash-adjusted) | $415.25M | 4→2% | 2.37% | **11%** | **+196bp** |
| Conservative (cash-adjusted) | $415.25M | 8→4% | 2.37% | **12%** | **+318bp** |
| Base | $465.15M | 12→7% | 2.37% | **13%** | **+412bp** |
| Optimistic | $508.39M | 18→10% | 2.37% | **16%** | **+720bp** |

Quoted to whole percents because ATM IV is 56.06% — above the 50% line, so a
figure like "12.19%" would be arithmetic, not knowledge. The first two rows
solve against market cap net of excess cash ($5.049B); the last two against
full market cap ($5.899B). **The finding is the bear row**: the price is
already paying for a near-total growth stall and still clears the hurdle. For
comparison, the 2026-08-08 run at $51.35 produced +171bp conservative and
+331bp base on *more generous* growth paths — the growth assumptions came down
this run and the spread went up anyway, entirely because of the 15% price
fall.

Integrity checks:

- **Reinvestment / terminal-growth warning fired on all four runs** ("base FCF
  >= base earnings leaves nothing reinvested"), because TTM FCF $508M exceeds
  consolidated net income $231M. The wedge is structural float — members
  prepay a year (deferred revenue $573.0M) and the partner accrual builds
  intra-year — plus D&A and SBC addbacks, not acquired-intangible
  amortisation. The honest response prescribed for this case was taken:
  terminal growth cut to exactly the 10-year breakeven, so no *real* terminal
  growth is claimed and nothing needs to be reinvested to fund it. The tool
  prints no `implied_terminal_roe` because the reinvestment rate is negative;
  that is the same fact stated from the other side, not a missing check.
- **Base-year cash tax vs marginal.** Effective tax rate 21.25% on $59.5M of
  income tax — at the marginal rate, not below it. No NOL flattery in the
  base year.
- **Serial-acquirer check: n/a.** Growth is organic; goodwill is static at
  $62.7M, so no acquisition spend is being excluded from `fcf` and smuggled
  back in as growth.
- **High-SBC check.** SBC $43.24M is 4.32% of revenue — moderate (INTU runs
  near 10%, BR near 1%) — and is deducted in three of the four rows.
- **Cash-heavy check.** Net cash is 14.4% of market cap, enough to bias the
  implied return low, so the two conservative rows solve against market cap
  net of it and charge the after-tax interest that cash earns.
- **Market-share sentence.** The base path compounds revenue from $1.0007B to
  roughly $1.6B by 2031 (FCF grows faster than revenue on operating leverage,
  so the FCF path above overstates the top line). At the $219 list price that
  is ~7.3M full-price-equivalent members against a TSA PreCheck enrolled pool
  north of 20M and ~800M annual US enplanements — high-single-digit
  penetration of the frequent-flyer base, not a bigger-than-the-market
  forecast. The honest caveat: with throughput flat to down, that growth has
  to come from price and penetration, because the market is not supplying it.
- **Terminal risk (Item 1A sweep).** The dominant structural risk is
  government first-party identity verification and credential authentication —
  TSA Touchless ID. Terminal growth of 2.37% assumes CLEAR's excess returns
  fade to zero, which is precisely the world in which that risk partially
  lands, so the terminal input survives its own disclosed endgame risk.
  Only ~29% of firms earn above their cost of capital in a given year, and
  this terminal assumption does not need CLEAR to be one of them.
- **Distribution clamp — and the closest attack.** The US median cost of
  capital is ~7.8% with 80% of firms inside 5.3–9.9%. All four implied returns
  (11–16%) sit *above* the top of that band. That is not a free lunch; it is
  evidence the beta-derived 9.01% hurdle understates what the market actually
  demands here, corroborated by 56% ATM IV on a beta-1.02 name. Read the
  spreads as compression, not as alpha.

**Options-implied move** (path 2 — Robinhood stopgap; YOU is absent from the
CBOE catalog so no path-1 IV percentile exists; broker/microstructure tier).
Expiry 2026-11-20, DTE 73, bracketing the early-November Q3 print — the event
that resolves both UNKNOWNs. ATM strike 44 against spot 43.60; call mark 4.20
(IV 0.544563), put mark 4.50 (IV 0.576600); ATM IV is the mean, 0.5605815.

| metric | value |
|---|---|
| spot | 43.60 |
| dte (calendar days) | 73 |
| ATM IV | 56.06% |
| expected absolute move (MEAN, not a ceiling) | 19.95% |
| 1-sigma move | 25.07% |
| RV60 | 44.32% |
| RV20 | 37.39% |
| IV > RV60? | YES |
| IV > RV20? | YES |

Both windows read YES, so IV is **elevated** — the market is pricing the
November print for considerably more than either trailing window realised, and
RV20 (37.4%) has fallen well below RV60 (44.3%), i.e. the stock has calmed
since the August waterfall while the option market has not. Per the one-way
valve, none of that is evidence *for* the thesis. **Liquidity gate FAILED** —
the call's $3.90/$4.50 market is a $0.60 spread on a $4.20 mark (14.3%) and
the put's $4.20/$4.80 is $0.60 on $4.50 (13.3%), both beyond
`max(10% of mark, 2 ticks)`; volume was 8 and 0 against a 100 floor, on open
interest of 57 and 60. The read is therefore **UNRELIABLE**, context only, and
it moved no verdict. **Timing check: NOT APPLICABLE** — the thesis makes no
dated move claim, so there is no `--required-move` to test against the 2-sigma
line.

Equity-as-option lens: **omitted**, correctly. Net debt is negative (net cash
$849.5M), book equity is positive at $243.2M, Altman Z is 3.11 and there is no
going-concern language — the Phase 4 leverage gate does not open.

## 5. Falsifiers

- **Break —** TSA or DHS gives non-members CLEAR-equivalent *lane position*
  free (not mere identity verification), or CLEAR loses a major airport
  cluster or one of its security authorizations.
- **Break —** the Q3'26 filing reveals Amex renewal terms materially worse:
  lower partner-funded bookings or worse per-member economics.
- **Break —** bookings growth falls below 10% y/y.
- **Shift —** Active CLEAR+ Members decline sequentially for two consecutive
  quarters (still disclosed quarterly, so observable).
- **Shift —** TSA monthly checkpoint throughput prints below −3% y/y for two
  further months (September's +0.2% first week is the current evidence against
  this). Free, monthly, and public at tsa.gov — the cheapest falsifier here.
- **Shift —** FY FCF guidance walked back below $465M.
- **Shift —** any re-disclosed or triangulated retention print materially
  below ~85% GDR.
- **Shift —** the Q3 10-Q shows a second idle buyback quarter with the stock
  in the low $40s, i.e. management declining to buy 17% below its own Q3-to-
  date average of $52.73.
- **Shift —** founder/Alclear Form 4 selling resumes at the pre-August cadence
  or in block size.

**Reopen trigger:** 2026-11-05: `you-q3-amex-terms-member-trajectory-and-
travel-volume` (inherits Break classification — the Amex-terms leg is a Break,
so the trigger is treated as one).

## 6. UNKNOWNs

1. **Current retention (GDR / NMR / usage).** Discontinued as of Q1'26; absent
   from the release, the 10-Q and the call. Would come from management
   re-disclosure, or from triangulation if gross adds were ever published —
   they are not. Its absence does not kill the thesis (bookings and active
   members are still disclosed) but it caps the verdict at UNPROVEN and holds
   condition 1 at *plausible*.
2. **Amex renewal economics.** Resolves at the Q3'26 10-Q and call. This is the
   one UNKNOWN whose adverse resolution is a Break, not a Shift.
3. **Per-class voting rights and controlled-company status.** Not locatable in
   the 10-Q this run; would come from the certificate of incorporation or the
   DEF 14A. Does not kill the thesis, but it leaves the governance backdrop to
   the KPI retirement unquantified.
4. **CLEAR1 revenue and margin split.** Never disclosed — only signings and
   NRR colour, and now three integration announcements with no economics. This
   is why CLEAR1 is option value rather than a load-bearing condition.
5. **True current ARPU by tier** (standard / airline / Amex mix). Only the
   posted price ladder and bookings-per-member arithmetic exist.
6. **Exact August TSA throughput decline.** My monthly totals (−3.68%) were
   summed by a fetch-summarising model over the TSA table and disagree with an
   outside computation (−4.4%) by ~0.7pp; the daily values I summed by hand
   (Sept 1–7) reconcile exactly with that outside source, so the daily data is
   trustworthy and the monthly aggregate is ±1pp. Does not change the sign or
   the conclusion.

## 7. Sources

- **Primary:** SEC EDGAR CIK 0001856314 — the `browse-edgar` atom feeds for
  8-K and 10-Q (establishing that the most recent 8-K is 2026-08-05); Form 4s
  filed 2026-09-03 for Barkin, McLaughlin and Liu, including the verbatim
  10b5-1 footnotes; the Q2'26 10-Q `you-20260630.htm` cover page (all-class
  share count 135,288,082 at 2026-07-31) and balance sheet (per-class counts
  at 2026-06-30); SEC XBRL `companyconcept` `us-gaap:ProfitLoss` for
  consolidated quarterly net income. Q2'26 earnings release and call, the
  Q4'25 call's KPI-discontinuation statement, and the Q4'24 shareholder
  letter's retention series carried forward from `research/YOU-2026-08-08.md`
  (call transcripts are primary for management statements).
  **TSA.gov passenger volumes** (2026 and 2025 pages) — daily and monthly
  checkpoint throughput.
- **stockanalysis.com (vetted exception):** `/stocks/YOU/statistics/` probe
  (block inventory) and the `/stocks/you/` overview for the news index,
  quoted price, PE and analyst target.
- **Broker/market microstructure:** Robinhood MCP, admissible here because no
  integrated official source covers these fields — official close $43.60 and
  the SPY comparison close; daily OHLCV bars for the price path and the RV20 /
  RV60 windows; the 2026-11-20 option chain, ATM marks, IV, open interest and
  volume for the implied-move table; estimate-vs-actual EPS for the eight-
  quarter surprise pattern (actuals cross-checked against filings; `Q2'26
  $0.49` agrees).
- **Reference data:** Damodaran (pages.stern.nyu.edu/~adamodar) — implied ERP
  4.14% with a stated T-bond rate of 4.75%, as of 2026-09-01; the
  cost-of-capital distribution (median ~7.8%, 80% band 5.3–9.9%) and the ~29%
  EVA base rate, January 2026 vintage.
- **Point-in-time repo DBs (read-only):** `stocks.db` `v_latest`
  (2026-09-04 snapshot — TTM flows, balance sheet, beta, short interest,
  margins, F-score, Z-score); `fred.db` (DGS10 4.78% at 2026-09-04, T10YIE
  2.37% at 2026-09-08); `earnings.db` (next event 2026-11-04, `edgar-estimate`;
  `calendar_now.today` = 2026-09-08); `composite.db` (zero votes, zero
  coverage; the `portfolio_holding` signal used to enumerate the book);
  `research/verdicts.log` (the 2026-08-08 UNPROVEN line).
- **Low-confidence:** web colour on the JPMorgan initiation and the DA
  Davidson target cut (TheFly headlines via the stockanalysis news index);
  the CrowdStrike release read through search summaries after the PRNewswire
  URL 404'd; the bear-case aggregation (hedge-fund count 33→27, short
  interest 15.62% of float, the H1 buyback comparison) — the buyback figures
  are directionally corroborated by the Q2 call but the exact numbers are not
  primary-verified this run, and the accompanying dilution claim is refuted
  above.

## Kill-thesis record

Ledger line: kill-thesis **UNPROVEN** — conditions=5, refuted=0, unknown=2;
ownership call BUY at $43.60. Nothing was refuted; two load-bearing conditions
cannot be attacked at all because the evidence does not exist in any
disclosure, and both become observable at the Q3 print.

Per-condition adjudication:

1. **Retention near ~87% GDR — UNKNOWN.** Attacked by looking for a
   triangulation route (gross adds, cohort disclosure, a re-disclosure in the
   Q2 release or 10-Q); none exists. Management retired the metric while it was
   falling. Unattackable, therefore uncredited.
2. **Travel-volume decline is a trim, not a break — SURVIVED, narrowly.** The
   attack was the strongest of the run and was built from primary TSA data:
   July −0.9%, August −3.7%. It failed to land only because the same source
   shows Sept 1–7 at +0.2% y/y, so a two-month deterioration is not
   established. Two more negative months refutes this condition.
3. **Bookings growth stays double digits — SURVIVED.** Q2 bookings +32.8%,
   four quarters ≥17%, Q3 guided +20.5%. The internal-consistency attack —
   that conditions 2 and 3 are strained, since a company cannot grow bookings
   30%+ into a shrinking end market forever — is real but survivable: Q2's
   +32.8% was delivered on roughly flat throughput, so the growth is
   price- and penetration-driven, not volume-driven. Condition 3 is doing most
   of the thesis's work and condition 2 is its dependency.
4. **Amex renewal preserves partner-funded economics — UNKNOWN.** Terms
   withheld until "the appropriate time." The $315M accrued liability is
   leverage held by Amex, not by CLEAR. No disclosure exists to attack.
5. **Touchless ID does not commoditize the paid lane — SURVIVED.** It verifies
   identity; it does not sell queue position. Retention survived its 2023–26
   rollout as far as the published series ran, and the risk is priced by
   setting terminal growth to zero real. Not refuted, and not confirmed either
   — it is handled by assumption, honestly labelled.

Standing checks. **Base rate:** only ~29% of firms earn above their cost of
capital, so "the excess return persists" is a 3-in-10 proposition — the
terminal assumption deliberately does not rely on it. **Short case (strongest
form):** a discretionary $219/yr subscription on a US air-travel base that just
contracted ~4% in a month; management retired its three deteriorating KPIs
exactly when they mattered; the largest partner's renewal terms are undisclosed
and the $315M accrual is Amex's leverage; the founder sold ~$20M into the
earnings spike; buybacks collapsed from $126.3M to $1.2M half-on-half; and the
free-cash-flow story is flattered by prepaid float that reverses the moment
growth stops — all at 29.7x trailing earnings. That is a coherent short, not a
strawman. **Management incentives:** founder performance RSUs are stock-price-
keyed, which aligns exactly with retiring a declining metric; the thesis does
not require management to act against incentive, but it does assume disclosure
integrity, and the KPI retirement is evidence against that assumption.
**Disconfirming search:** ran deliberately against my own new finding and
corrected it (the September throughput reversal), and surfaced the buyback
collapse and the hedge-fund exodus (33→27 funds); it also surfaced a dilution
claim that turned out to be an Up-C misread and is refuted in §3.
**Moat — mechanism or checkbox:** mechanism (airport-by-airport lane
contracts, a certification stack, an enrolled-identity network), with the hole
named rather than hidden.

Statistical checks: **N/A, stated.** The thesis rests on no backtest, screen or
repo signal — composite currently scores YOU 0/0 at 0.0 coverage, so there is
no hit rate, no overlapping-window problem and no effective-n question to
audit. Options timing check: **NOT APPLICABLE** — no dated move claim. Coverage
disclosure: path 2 (Robinhood stopgap) only, no path-1 history exists, and the
liquidity gate FAILED, so the options evidence is context and could not have
refuted anything even had a dated claim been made.

**Closest attack:** the hurdle-illusion. The 9.01% hurdle is built on a
five-year beta of 1.02, but every scenario's implied return (11–16%) sits above
the top of the 80% cost-of-capital band (5.3–9.9%) and the option market prices
56% ATM IV on the same name. Both are evidence that the market's true required
return here is well above 9%, and at 12% the conservative spread goes to
roughly zero and the bear case goes negative. It refutes no condition — it
converts "cheap" into "fair on conservative assumptions," which is why this is
a BUY at 0.56 rather than a conviction position.

**Flip evidence — toward SOUND:** the Q3 print re-discloses retention (or
publishes gross adds enabling triangulation) at or near ~87% GDR *and*
discloses Amex renewal terms no worse than the prior economics. **Toward
FLAWED:** Q3 bookings growth below ~10% y/y, or Amex renewal terms materially
worse, or two further months of TSA throughput at −3% or worse alongside a
sequential decline in Active CLEAR+ Members.

**p(beat SPY, 63 td): 0.47** — written before re-reading §1's 0.56. The
0.09 gap is the honest disagreement: §1 weights the valuation floor that the
bear case establishes, this pass weights the two unattackable conditions and
the hurdle illusion, and the horizon contains the print that settles both.
