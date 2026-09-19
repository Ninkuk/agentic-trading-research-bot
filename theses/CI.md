# CI — The Cigna Group — 2026-09-06

Price $282.52 (official close, 2026-09-04) · market cap $74.65B ·
next earnings 2026-10-29 BMO (contested — see §3) · EV $99.27B · net debt $24.62B

Entry path: unattended scheduled run. Supersedes `research/CI-2026-08-05.md`
(BUY at $270.49, kill-thesis UNPROVEN). That file's reopen trigger is dated
2026-10-29 and has **not** fired, so this is a scheduled re-run rather than a
trigger-fired reopen: §0 is omitted and the prior thesis's falsifiers are swept
in §3 instead. The position is currently **held** — `composite.db`
`ticker_scores.in_portfolio = 1` on every snapshot through 2026-09-07 — so §1 is
a hold-at-today's-price call, not a fresh entry.

## 1. Verdict and thesis

**BUY at $282.52.** kill-thesis: **UNPROVEN** — conditions=6 (2 probable,
4 plausible), refuted=0, unknown=2.

**p(beat SPY, 63 td): 0.56** · kill-thesis: 0.53 —
**Disputed expectation:** the market prices owner free cash flow of roughly
$6.6–7.5B/yr growing at 1–2% forever (implied return 10.3–13.0%/yr against an
8.1% hurdle), i.e. it treats Cigna as riskier than roughly 90% of US firms
because the Consolidated Appropriations Act 2026 deletes its rebate-retention
profit pool on a legislated 2028 timetable. What revises it is the pair of
prints inside this horizon: the September Investor Day's long-term algorithm,
and the Q3 disclosure of whether Pharmacy Benefit Services earnings troughed
and whether the minority-interest claim that doubled in H1'26 keeps doubling.

Cigna is two businesses bolted together: a scaled toll-road on US drug spend
(Express Scripts plus Accredo) and a deliberately commercial-only insurer that
is absent from every line — Medicare Advantage, Medicaid, ACA exchanges — that
broke its peers in 2024–2026. The discount is real and disclosed: Congress
legislated the rebate model away in February 2026. The thesis is that the
price already assumes that repricing goes badly. At $282.52 a run that cuts
free cash flow to the FY26 guidance level, strips stock compensation and the
minority holders' share, grows it 2% for five years and 1% thereafter still
implies 10.31%/yr — 225bp over the hurdle. A bear run in which owner cash flow
falls 3%/yr for five years and then never grows implies 7.75%, only 31bp short.
You do not have to believe management's Signature story to own this; you have
to believe cash flow does not collapse.

**Closest attack:** the base number, not the story. TTM free cash flow of
$9.113B sits on a three-year FCF trend of **−7.2%/yr** (`stocks.db`
`fcfGrowth3Y`) and on a working-capital position of **−$8.571B** — the
pharmacy-payables float — that unwinds as pharmacy lives shrink, and lives fell
4% YTD. Quoting the base row extrapolates the top of a declining, volatile
series. At the five-year-mean owner base ($7.456B) the implied return is
13.04%, not 15.45%. The attack moves the honest centre of the range down by
roughly 250bp; it does not reach the hurdle.

Load-bearing conditions (6):

1. *plausible* — **Owner free cash flow does not fall sustainably below
   ~$6.6B/yr.** TTM consolidated FCF $9.113B (OCF $10.277B + capex −$1.164B),
   but FY21–FY25 ran 6,037 / 7,361 / 10,240 / 8,957 / 8,389 ($M) — mean $8,197M,
   and the FY2021 print was itself below $6.6B. Downgraded from *probable* this
   run on the three-year trend and the float-unwind mechanism.
2. *probable* — **Cigna Healthcare's medical care ratio stays inside the FY26
   guide band of 83.7–84.7%**, with no repeat of the Q4'24 stop-loss miss. Q2'26
   MCR 84.5%, guide unchanged; the residual risk book is employer commercial plus
   stop-loss, repriced annually, with the ACA exchange exit effective 2027-01-01.
3. *probable* — **Specialty & Care Services keeps offsetting the PBS decline.**
   Q2'26 segment pre-tax adjusted earnings: S&CS $1,054M (+22% YoY), PBS $609M
   (−27% YoY), Cigna Healthcare $1,276M (+17%). Two quarters, not a trend, and
   management flagged part of the S&CS beat as early biosimilar timing.
4. *plausible* — **No federal action beyond CAA 2026** reaching Accredo or
   forcing PBM divestiture of pharmacies (an Arkansas-style mandate going
   federal). Unverifiable in any disclosure; see §6.
5. *plausible* — **The minority interests' claim on consolidated cash flow does
   not keep doubling.** NCI income H1'26 $422M vs H1'25 $186M (+127%); FY2025
   $331M, FY2024 $344M. NCI balance-sheet equity was only $290M at 2026-06-30
   against $161M at 2025-12-31, so roughly 70% of attributed income leaves as
   cash. New this run; the holders' identity is undisclosed (§6).
6. *plausible* — **Capital discipline holds**: no acquisition above ~$10B, the
   deleveraging to the ~40% debt/cap target completes, and the buyback resumes.
   TTM repurchases $1,281M against $3,621M in FY2025; shares QoQ −0.02%.

**Dominant shared risk factor:** US drug-pricing and PBM-compensation policy —
holdings unavailable in this session (the headless slot has no `portfolio.db`
grant, so the overlap count could not be run; `composite.db` confirms only that
CI itself is held).

## 2. Business

**Created:** Two distinct value creations. Evernorth (roughly 86% of revenue):
drug-purchasing scale — negotiating price against manufacturers and pharmacies
across 118.2M pharmacy lives — plus Accredo's clinically intensive specialty
dispensing, with limited-distribution access to 330+ medicines and nursing
support for therapies that cannot ship through a retail counter. The customer
(employer, health plan, government) gets a lower net drug cost than it could
negotiate alone. Cigna Healthcare (roughly 16% of revenue but 41% of segment
adjusted earnings): underwriting and administering employer health benefits
with integrated medical, pharmacy and behavioural data, plus the industry's
largest stop-loss book (>$8B premium) for self-funded employers.

**Captured:** Four distinct mechanisms, not "fees". (1) Spread and rebate
retention on pharmacy volume — the piece CAA 2026 rewrites. (2) Dispensing
economics in Accredo and Express Scripts Pharmacy, where biosimilar
substitution is margin-accretive rather than dilutive. (3) Fee-based services
to hospitals — Shields management services, Verity 340B, CarepathRx.
(4) Insurance underwriting margin in Cigna Healthcare, where premiums reprice
annually against cost trend.

**Protected:** Scale in drug purchasing is a genuine cost moat — three firms
control roughly 80% of US PBM volume, and a new entrant cannot replicate the
rebate and network position. Accredo's limited-distribution contracts are
bilateral manufacturer relationships that a competitor cannot copy quickly.
Switching costs are visible in retention above 97% for 2026 and mid-90s
indicated for 2027, and the three anchor clients (Centene, Prime Therapeutics,
DoD TRICARE) are renewed "through the end of the decade" per the FY2025 10-K.
What is *not* protected is the political legitimacy of rebate economics — that
protection failed in February 2026 when Congress legislated it away on a
timetable. The mechanism survives as scale plus clinical infrastructure; the
*capture* mechanism is being forcibly swapped. The moat protects the volume,
not the current toll.

**Control:** One class of common stock, one share one vote, no controlling
holder. Insiders hold 0.38%, institutions 92.5%. Nothing in the charter
forecloses an unsolicited approach or an activist campaign; the practical
barriers are size ($74.7B equity, $99.3B enterprise value) and insurance-
regulatory change-of-control approval in every state of domicile, not
structure. This is the null answer and it is written explicitly.

**Operating leverage (Phase 0): negative over five years, improving in the
last twelve months.**

| period | revenue | operating income | operating margin |
|---|---|---|---|
| FY2021 | $174,069M | $8,162M | 4.69% |
| FY2025 | $274,900M | $10,259M | 3.73% |
| TTM (Jun'26) | $282,382M | $11,021M | 3.90% |

Revenue +58% against operating income +26% is negative operating leverage on
its face, but it is mix rather than decay: pharmacy pass-through revenue grows
with drug list prices at near-zero incremental margin. The direction that
matters is the last leg — the TTM margin has recovered 17bp off the FY2025 low,
which the prior thesis's flat "negative" did not capture. Per-share economics
ran the other way throughout: diluted EPS $15.75 (FY21) → $22.18 (FY25) →
$24.18 (TTM) on a share count down roughly a fifth.

## 3. Threads pulled

- **Cash-flow quality — the thread that moved the answer.** TTM operating cash
  flow is $10,277M against net income to all holders of $6,983M and depreciation
  and amortization of $1,737M; the residual ~$1.56B comes from working capital,
  deferred taxes and the $291M stock-compensation addback. Working capital is
  **−$8,571M** and net working capital **−$13,036M** (current ratio 0.85) — this
  is the pharmacy-payables float, cash collected before pharmacies are paid. It
  is a genuine, durable source of cash *while volume grows*, and it runs backwards
  when volume shrinks. Total pharmacy customers fell 4% YTD to 118.2M. Meanwhile
  `stocks.db` reports TTM OCF growth of **+94.2% YoY** against a three-year OCF
  growth rate of **−7.3%/yr** and three-year FCF growth of **−7.2%/yr**: the TTM
  figure is a high print in a volatile, declining series. Consequence: §4 quotes
  the five-year-mean and guidance-based rows as the centre, not the TTM row.
- **The minority interests — a new and partly unresolved claim (SEC XBRL).**
  `NetIncomeLossAttributableToNoncontrollingInterest`: FY2024 $344M, FY2025
  $331M, then Q1'26 $207M and Q2'26 $215M — H1'26 $422M against H1'25 $186M,
  **+127% YoY**. TTM works out to roughly $567M, which independently reproduces
  the prior thesis's ~$0.57B estimate. The cash test the skill demands: NCI
  balance-sheet equity (`MinorityInterest`) was $161M at 2025-12-31 and $290M at
  2026-06-30, so of $422M attributed in H1 only $129M stayed in the balance —
  roughly **70% left as cash**. The claim is real cash, not an accounting
  artefact, and at the Q2 run-rate it is ~$860M/yr against a ~$8–9B consolidated
  base. §4 haircuts for it. `PaymentsOfDividendsMinorityInterest` is not tagged
  (HTTP 404), so the distribution is inferred from the balance roll-forward, not
  read directly. Who the holders are remains undisclosed (§6).
- **Prior-thesis falsifier sweep (2026-08-05 → 2026-09-06).** No new print, so
  every falsifier is measured against the same Q2'26 data: pharmacy lives
  (−4% YTD) NOT RETRIGGERED — no new datapoint; PBS trough NOT TRIGGERED — no new
  datapoint; MCR band NOT TRIGGERED (84.5%, guide unchanged); anchor-client loss
  NOT TRIGGERED; large acquisition NOT TRIGGERED; regulatory expansion beyond CAA
  2026 NOT TRIGGERED; Investor Day GRAZED — it is confirmed but has not happened
  and has no announced date. Nothing fired.
- **The September Investor Day — the near catalyst, and it has no public date.**
  Both executives committed to it on the Q2'26 call. CFO Ann Dennison: *"We look
  forward to our upcoming Investor Day in September, where we'll go deeper on our
  long-term strategy, growth opportunities, and the outlook for Evernorth and
  Cigna Healthcare."* CEO Brian Evanko: *"We look forward to hosting our Investor
  Day this fall."* On 2026-09-06 no date has been published — not on the IR
  events page, not in a press release, not in an 8-K. Going in, Evanko has
  already reaffirmed the framing: *"our view for 2027 continues to be consistent
  with our prior commentary to deliver against our 10% to 14% EPS algorithm."*
  The event is therefore asymmetric in structure: the reaffirmation is priced,
  the cut is not.
- **Insider filings — investigated, and the alarming reading dissolved.** Seven
  ownership filings in a month looked like distribution: Form 4 on 08-06, 08-20
  (×2), 09-02 and 09-03; Form 144 on 08-04, 08-18 and 09-03. Pulled the two most
  recent. The 09-03 Form 4 is **Brian C. Evanko, President and CEO**, and the
  transaction code is **A (award)** — 3,113 restricted shares and 6,716 options
  struck at $281.1325, dated 2026-09-01, leaving him 41,030 shares direct plus
  25,614 in a GRAT. Not a sale. The 09-03 Form 144 is officer Neville Everett
  proposing **617 shares, $175,258.85**, from a 2026-03-01 restricted-stock
  vesting, with nothing sold in the prior three months. The 09-02 Form 4 is
  director George Kurian. This is routine grant-and-vest mechanics, not insider
  distribution. Prior UNKNOWN #4 (the 08-04 Form 144 seller) remains unnamed but
  is now clearly the same category.
- **Management incentives — an adverse finding.** The DEF 14A (filed 2026-03-12)
  shows the long-term Strategic Performance Share program moving from the
  2023–2025 design of 50% relative TSR / 50% cumulative adjusted income from
  operations per share to a 2026 design of **70% cumulative adjusted income from
  operations per share, 30% relative TSR**. Weight shifted *toward* a metric
  management defines and away from the market's own verdict. Two consequences.
  First, the six-quarter beat streak the prior thesis cited as "managed guidance
  restored" is measured in the same adjusted EPS that now pays 70% of the LTI —
  and Signature transition costs are exactly the sort of item that gets
  classified out. Second, a 70%-weighted per-share metric rewards buybacks over
  deleveraging, which is the opposite of what management is currently doing —
  mildly reassuring on discipline, and it makes the buyback leg of condition 6
  more likely rather than less.
- **eviCore strategic review — still open, unquantified.** Announced with the Q1
  2026 results (April 2026) alongside the ACA exchange exit. Evanko has said no
  transaction is under way and the company is weighing a partnership or a
  combination with complementary industry participants. eviCore is prior
  authorization and utilization management — small, and politically exposed given
  the industry-wide push to standardise and automate prior auth. Not in the Q2'26
  call transcript at all. Optionality, not a condition; no disclosed financials.
- **DOJ antitrust probe expanded (mid-July 2026, low-confidence).** Reported
  expansion of an investigation into Claritev involving multiple insurers. No
  company-specific quantification and no mention in Cigna's own disclosures that
  this run could reach. Recorded, not load-bearing.
- **Q3 print date — the sources disagree.** `stocks.db` and stockanalysis both
  carry 2026-10-29 BMO; Robinhood's `get_earnings_results` carries **2026-11-05**
  with `verified: false`. `data/earnings.db` has no `v_upcoming_earnings` row for
  CI at all (its `calendar_now.today` is 2026-09-04, so CI sits outside the
  forward window). Cigna has not published the date. The reopen trigger below
  uses 2026-11-05 so it backstops the later of the two.
- **Options read (mandatory):** path 2 only (Robinhood stopgap). CI is not in
  the 24-symbol CBOE catalog and `data/options.db` has no history for it, so
  path 1 does not apply and no own-history IV percentile exists. See §4 for the
  table — the liquidity gate **fails**, so the numbers are directional only.
- **Dead ends:** the insider-filing cluster (above) — checked precisely because
  it looked bad, and it is routine. The Item 1A terminal-risk sweep was not
  re-run: no 10-K has been filed since 2026-02-26, and the prior thesis's read of
  the same document (CAA 2026 dates and provisions, $6.3B purchase obligations
  against ~$9B/yr FCF and $1.2B capex) is unchanged; re-reading an unchanged
  filing is not a check. The transcript corpus was not swept — no thread here
  turns on multi-year management phrasing, and the corpus can only prove presence.
  The leverage gate was computed and **not** triggered: net debt $24.62B is 24.8%
  of the $99.27B enterprise value, well below the ~50% threshold, book equity is
  positive at $42.91B, and there is no going-concern language — so §4 carries no
  equity-as-option table. `get_equity_tax_lots` could not be called (no grant in
  this slot), so the per-lot cost basis for the held position is unread.

## 4. Valuation

**Inputs.** Market cap $74,653,222,000 (264,240,486 shares × $282.52,
2026-09-04 close; stockanalysis reports $74.65B). TTM levered free cash flow
$9,113M = operating cash flow $10,277M + capex −$1,164M. Paired with **market
cap**, `--net-debt 0` by the pairing rule: the flow is post-interest, so
enterprise value ($99.27B) is the wrong denominator and would understate the
implied return by hundreds of basis points on $24.62B of net debt. Two haircuts
are applied before solving. Stock compensation: **$291M** (FY2025, SEC XBRL
`AllocatedShareBasedCompensationExpense`; FY2024 $308M, FY2023 $286M) — added
back inside operating cash flow but not cash the owner keeps. Minority
interests: **~$860M/yr** at the Q2'26 run-rate, subtracted as a dollar rather
than a percentage; the percentage version (12% of the pre-haircut base) is
harsher and is shown as its own row. Base earnings for the reinvestment check
are **cash earnings ~$7,676M** = net income to common $6,416M plus after-tax
acquired-intangible amortization (~$1,556M/yr pre-tax at the Q2'26 $389M
run-rate, taxed at the 19.17% effective rate) — not the GAAP $6,416M, because
Express Scripts amortization understates the earnings base exactly as the
skill's BR case describes.

Precision note: ATM IV is 30.42%, below the 50% line, so decimals are quoted.

**Hurdle.** rf 4.75% + beta 0.8 × ERP 4.14% = **8.06%** (Damodaran, as of
2026-09-01). The regression beta is **0.32** (5Y; 1Y beta 0.08) — far outside
the 0.8–1.2 stable band, so it is floored into the band and that is stated:
using the raw 0.32 would have handed the hurdle read a free pass at 6.08%.
Cigna is a US-only operating business after the 2022 sale of the international
life and health book to Chubb, so the headline US ERP applies and no
operations-weighted country ERP is needed. The absolute companion —
rf + 4.5% = **9.25%** for a mature company — sits 119bp above the computed
hurdle, so the spreads below are also read against 9.25% where it changes the
sign.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| base — TTM as reported | $9.113B | 4% | 2.0% | 15.45% | +739bp |
| SBC-adjusted | $8.822B | 4% | 2.0% | 15.03% | +697bp |
| **owner FCF** (SBC + $860M NCI) | $7.962B | 4% | 2.0% | **13.78%** | +571bp |
| owner FCF, 12% NCI haircut instead | $7.763B | 4% | 2.0% | 13.49% | +542bp |
| owner FCF, tax normalized 19.2%→23% | $7.632B | 4% | 2.0% | 13.30% | +523bp |
| **5-year-mean base** (FY21–25 mean, haircut) | $7.456B | 4% | 2.0% | **13.04%** | +498bp |
| conservative — FY26 guide, haircut | $6.600B | 2% | 1.0% | 10.31% | +225bp |
| bear — owner FCF declines | $6.600B | −3% | 0.0% | 7.75% | −31bp |
| trend bear — extrapolate `fcfGrowth3Y` | $7.962B | −7.2% | 0.0% | 7.75% | −31bp |
| harsh bear — rebate pool goes to zero | $5.000B | 0% | 0.0% | 6.70% | −136bp |

The conservative row against the stricter 9.25% anchor is +106bp rather than
+225bp; the bear rows are −150bp and −255bp. The centre of the honest range is
the owner-FCF and five-year-mean rows, **13.0–13.8%**, with the conservative row
at 10.31% as the floor of the plausible zone and the bear rows as the tail.

**Integrity checks.**

- *Reinvestment and the growth-without-reinvestment warning.* Every 2.0%-terminal
  row prints it: base FCF exceeds base earnings, so nothing is reinvested, yet
  terminal growth is positive. Answered, not ignored: 2.0% is set at price-level
  repricing of existing assets, which needs no reinvestment — real growth beyond
  inflation is not modelled anywhere in this section. The owner-FCF row is nearly
  self-consistent on its own terms (terminal reinvestment rate −3.7%, i.e. FCF ≈
  cash earnings). The conservative row is the strict one: reinvestment 14.0% and
  **implied terminal ROE 7.13%**.
- *Terminal ROE read two-sided.* 7.13% sits **below** the 8.06% hurdle — that row
  therefore assumes the company mildly destroys value in perpetuity. That is
  intentional and it is the conservatism doing its job; it is not an error. No
  row assumes a terminal ROE more than five points above the hurdle, so the
  "tough to do forever" test is not engaged. The default reading — excess returns
  fade rather than persist, since only ~29% of firms earn above their cost of
  capital — is what the 1.0–2.0% terminal rates already encode.
- *Base-year cash tax rate.* Effective rate 19.17% against a US marginal of
  roughly 23% including state. Normalizing costs ~$330M of base FCF and 48bp of
  implied return (the row is shown). The base is mildly flattered; it is not
  NOL-driven and there is no disclosed cliff.
- *Serial-acquirer check.* `fcf = OCF − capex` excludes acquisition spend, and
  Cigna spent $597M on cash acquisitions in FY2025 ($131M FY2024, $447M FY2023).
  The growth paths above are organic and the acquisition spend is immaterial at
  this scale — 6.5% of one year's FCF — so no separate charge is made.
- *Asset-light claim.* Tested against the FY2025 10-K commitments footnote in the
  prior run: purchase obligations total $6.3B ($3.2B investment commitments,
  $3.1B IT and service contracts; $2.1B due in 2026) against ~$9B/yr FCF and
  $1.2B capex. No hidden capex wave; the low-capex base survives.
- *Terminal growth against the disclosed terminal risk.* The dominant Item 1A
  structural risk is the CAA 2026 rewrite of PBM compensation — 100% rebate
  remittance to ERISA plan sponsors from August 2028, Part D delinking from
  January 2028, any-willing-pharmacy from January 2029. A 2.0% terminal rate
  survives that only if Signature's fee model replaces rebate economics at
  comparable margin, which is management's claim and not yet a fact. That is why
  the conservative row cuts terminal growth to 1.0% and the bear rows to zero —
  and why the ownership call is made from those rows rather than the base one.
- *Market share.* The 4%/yr path compounds TTM revenue of $282.4B to **$343.6B**
  by 2031. CMS projects national health expenditure from $5.3T (2024) to $8.6T
  (2033), roughly 5.5%/yr, which puts 2031 NHE near $7.7T. Cigna's implied share
  therefore **falls** from ~5.3% to ~4.5%. This is the opposite of a
  bigger-than-the-market forecast: the base path assumes Cigna grows slower than
  the pool it sells into.
- *Distribution clamp.* The US median cost of capital is 7.79% and 80% of US
  firms sit between 5.26% and 9.88% (Damodaran, 2026 update). Every non-bear row
  here implies a return **above the 90th percentile** — the market is pricing CI
  as riskier than roughly nine in ten US firms. The 2028 rebate cliff is a real
  reason that could be correct; it is also the entire disagreement.
- *Leverage gate.* Net debt $24.62B is 24.8% of enterprise value, book equity is
  positive at $42.91B, debt/EBITDA 2.50×, interest coverage 7.78×, and there is
  no going-concern language. Below the ~50% threshold, so the equity-as-option
  lens does not apply and is omitted; the DCF frame governs §1's call.

**Options-implied move (path 2 — Robinhood stopgap; path 1 unavailable, CI is
not in the CBOE 24 and `data/options.db` has no history).** Expiry **2026-12-18,
103 DTE** from 2026-09-06. The chain lists weeklies only through 2026-10-23 and
then jumps to December, so no expiry falls near the unannounced September
Investor Day and none brackets the Q3 print more tightly; the December contract
is the only one spanning both catalysts. Strike **280** against spot 282.52
(0.9% below spot; call delta 0.582, put delta −0.425, so the call is slightly
in the money — footnoted, not corrected). Call mark 20.10 (IV 29.05%), put mark
16.25 (IV 31.79%), mean ATM IV 30.42%.

| metric | value |
|---|---|
| spot | 282.52 |
| expected absolute move (MEAN, not a ceiling) | 12.87% |
| 1-σ move | 16.16% |
| ATM IV | 30.42% |
| RV60 | 27.92% |
| RV20 | 21.03% |
| IV > RV60? | YES |
| IV > RV20? | YES |

Both windows read YES, so the rule permits the word **elevated** — but only by
250bp against RV60, and the December expiry spans the Q3 print while the RV20
window (opening around 2026-08-06) contains no print at all, which is precisely
the stopgap's structural weakness. Read it as a modest, calendar-explicable
premium, not a discovery.

**Liquidity gate: FAILED → UNRELIABLE.** Call spread $18.80/$21.40 = 12.9% of
mark and put spread $14.80/$17.70 = 17.8%, both above the 10% limit; call volume
0 and put volume 10, both under the 100 floor; call OI 116 and put OI 130, with
the median-OI leg not computed. The four gate constants are themselves
uncalibrated, so a failure is informative and a pass would not have been.
**Timing check: NOT APPLICABLE** — the thesis makes no dated claim requiring a
specific move size, so no `--required-move` was passed and nothing here refutes
or supports anything.

## 5. Falsifiers

For an owner (sell):

- **Break —** Owner free cash flow tracks to an annualized run-rate below
  **$6.0B**. That is beneath the conservative row's base and inside the bear
  zone; at that level the implied return no longer clears the hurdle on any
  terminal assumption. Read it off the Q3 cash flow statement, not the adjusted
  EPS headline.
- **Break —** Pharmacy lives keep leaking. Total pharmacy customers fell 4% YTD
  to 118.2M. If the "strongest selling season in three years" has not stabilised
  lives by the Q2'27 print, the volume franchise is eroding under the model
  transition — and the working-capital float erodes with it.
- **Break —** Federal action beyond CAA 2026 that reaches Accredo or forces PBM
  divestiture of owned pharmacies. That hits the crown jewel, not just the
  rebate pool, and no valuation row here survives it.
- **Break —** A large acquisition (>$10B). The model needs the shareholder yield
  and the deleveraging, not another integration.
- **Shift —** Medical care ratio above the 84.7% top of the FY26 guide band, or
  stop-loss high-cost-claimant frequency turning up — the exact Q4'24 failure
  mode recurring.
- **Shift —** A second consecutive year of double-digit PBS earnings decline in
  2027. That falsifies the ~4%-margin Signature conversion claim, which the
  conservative row does not price but the base rows do.
- **Shift —** NCI income holds at $215M+/quarter through Q3 with no disclosed
  one-off explanation. At ~$860M/yr that is more than a tenth of the owner base,
  permanently.
- **Shift —** The September Investor Day cuts the 10–14% adjusted-EPS algorithm
  or the Evernorth long-term growth framing.
- **Shift —** Anchor client loss or mid-contract repricing: Centene, Prime
  Therapeutics, or DoD TRICARE.

**Reopen trigger:** 2026-11-05: ci-q3-owner-fcf-run-rate-nci-doubling-and-pbs-trough

## 6. UNKNOWNs

1. **Who the minority holders are, and why their claim doubled.** H1'26 NCI
   income $422M against $186M a year earlier is the largest single new fact in
   this run, and the FY2025 10-K equity/noncontrolling-interest note is where the
   identity and the contractual basis would be. This session could not extract it
   — `PaymentsOfDividendsMinorityInterest` is untagged (HTTP 404) and a targeted
   search returned only that Ascent Health Services sits inside Evernorth's
   benefits-management operations, which is not the same as confirming it is the
   NCI counterparty. Does not kill the thesis: the size is bounded and §4
   subtracts it. It does cap conviction, and it is one of the two reasons the
   kill verdict is UNPROVEN.
2. **Signature margins at scale.** The ~4% claim has no external verification
   before the 2027 insured-book conversion prints, with the first self-funded
   scale evidence in 2028. Does not kill the thesis — the conservative and bear
   rows assume no recovery — but it is what forces the 10.3–13.8% range instead
   of a point estimate.
3. **Federal legislative intent beyond CAA 2026.** Unverifiable in any
   disclosure by construction. Condition 4 rests on it. Its absence does not kill
   the thesis but it cannot be attacked, which is the second reason for UNPROVEN.
4. **The Investor Day date and agenda.** Confirmed by two executives on the Q2
   call, unannounced as of 2026-09-06 on the IR events page, in the newsroom, and
   in EDGAR. It falls inside the 63-day horizon this thesis is graded on, and its
   content is unknown. Resolution: an 8-K or IR press release, any day now.
5. **How much of Q2's S&CS beat was borrow-forward.** Management said part of
   the +22% was early biosimilar-adoption timing that will not repeat at the same
   magnitude in H2; the degree is unquantified. Carried from the prior run,
   unresolved.
6. **eviCore's standalone economics.** No segment disclosure, no announced
   transaction, no mention on the Q2 call. Cannot be valued; treated as
   unpriced optionality, not as a condition.
7. **The held position's cost basis.** `get_equity_tax_lots` requires a grant
   this headless slot does not have, and `portfolio.db` is not readable here, so
   the per-lot underwater check that would normally run before a hold call could
   not. Does not change the analysis — the ownership call is made at today's
   price regardless of basis — but it is a stated coverage gap, not an omission.

## 7. Sources

- **Primary:** SEC XBRL company-concept API (`data.sec.gov`) for
  `NetIncomeLossAttributableToNoncontrollingInterest` (FY2024 $344M, FY2025 $331M,
  Q1'26 $207M, Q2'26 $215M, H1'26 $422M), `MinorityInterest` (balance-sheet NCI
  $161M at 2025-12-31, $232M at 2026-03-31, $290M at 2026-06-30),
  `AllocatedShareBasedCompensationExpense` (FY2023 $286M, FY2024 $308M, FY2025
  $291M) and `AmortizationOfIntangibleAssets` (FY2025 $1,743M, Q2'26 $389M);
  Q2'26 earnings release 8-K Ex-99.1 filed 2026-07-30; DEF 14A filed 2026-03-12
  (SPS metric weightings, CEO ownership guideline); Form 4 filed 2026-09-03
  (Evanko, code A award) and Form 144 filed 2026-09-03 (Everett, 617 shares,
  $175,258.85); EDGAR filing index for the full ownership sweep since 2026-07-25;
  FY2025 10-K (CAA 2026 provisions, purchase obligations, anchor-client renewals)
  as read in the prior run and unchanged. Primary, transcribed (Quartr via
  stockanalysis): Q2'26 earnings call 2026-07-30 — the Investor Day, 2027
  algorithm and Signature-margin quotes.
- **stockanalysis.com (vetted exception):** `/stocks/ci/statistics/` (market cap,
  enterprise value, FCF, OCF, capex, debt, working capital, ratios, beta, short
  interest, F-score, WACC), `/stocks/ci/financials/` (FY revenue, operating
  income, net income, EPS history), `/stocks/ci/financials/cash-flow-statement/`
  (FY OCF, capex, FCF, acquisitions, repurchases, dividends),
  `/stocks/ci/transcripts/` (index and Q2'26 detail), `/stocks/ci/` (news feed and
  analyst actions). Route resolution and payload conventions per
  `docs/stockanalysis_data_json_catalog.md`.
- **Broker/market microstructure:** Robinhood MCP, admissible because no
  already-integrated official source covers these fields — `get_equity_quotes`
  (spot $282.52, 2026-09-04 close; peer closes UNH/CVS/ELV), `get_equity_
  historicals` (92 daily bars for the realized-vol windows and the SPY
  comparison), `get_option_chains` / `get_option_instruments` / `get_option_quotes`
  (expiry ladder, ATM marks, IV, open interest, volume), `get_earnings_results`
  (estimate-vs-actual pattern; the "actual" is adjusted EPS, not GAAP, and the
  2026-11-05 Q3 date is `verified: false`). Not primary; labelled.
- **Reference data:** Damodaran NYU Stern — implied ERP 4.14% and T-bond rate
  4.75% as of **2026-09-01**; US median cost of capital 7.79% with an 80% band of
  5.26–9.88% (2026 data update); excess-return base rate ~29% (EVA dataset); the
  0.8–1.2 beta band and the rf+4.5% mature-company anchor. CMS national health
  expenditure projections ($5.3T in 2024 → $8.6T in 2033) for the market-share
  sentence.
- **Point-in-time repo DBs (read-only):** `stocks.db` snapshot 2026-09-04 (price
  $286.26 for priceDate 2026-09-03, TTM FCF, `fcfGrowth3Y` −7.2%, `ocfGrowth`
  +94.2%, working capital, D&A $1,737M, beta, RSI, next earnings 2026-10-29);
  `sec_fundamentals.db` `v_screener` (Q2'26 GAAP: revenue $71.668B, net income
  $1.660B, EPS diluted $6.29, equity $42.62B); `composite.db` (no signal coverage
  — score 0, coverage 0.0 — and `in_portfolio = 1`, which is how this run knows
  the position is held); `earnings.db` (`calendar_now.today` 2026-09-04, no CI row
  in `v_upcoming_earnings`). `portfolio.db` and `scorer.db` are not readable from
  this slot.
- **Low-confidence:** web colour on the eviCore strategic review status and the
  mid-July DOJ/Claritev probe expansion; the reported existence of a September
  Investor Day beyond the two verbatim call quotes. Labelled, and none of it is
  load-bearing.

## Kill-thesis record

**UNPROVEN** — conditions=6, refuted=0, unknown=2.

Per-condition adjudication:

1. **SURVIVED, strained — tier downgraded *probable* → *plausible*.** Attacked
   with the FY FCF history (6,037 / 7,361 / 10,240 / 8,957 / 8,389 $M, FY21–25),
   the −7.2%/yr three-year FCF trend, the +94% TTM OCF swing, and the −$8,571M
   working-capital float that unwinds as pharmacy lives fall. FY2021 FCF was
   itself below the $6.6B line. The condition holds only because the five-year
   mean owner base ($7.456B) still implies 13.04%, +498bp over hurdle — but the
   TTM row is not quotable as the centre.
2. **SURVIVED, supporting evidence refuted.** The "six consecutive beats"
   argument is statistically empty: roughly 75% of S&P constituents beat
   consensus EPS in a given quarter, so six in a row is a ~17.8% outcome, not a
   signal. Worse, the beats are on *adjusted* EPS, which the 2026 proxy makes
   70% of the long-term incentive payout — management defines and is paid on the
   number the streak is measured in. The MCR band (84.5% actual, 83.7–84.7%
   guide unchanged) is a separate and harder disclosure and it is what carries
   the condition.
3. **SURVIVED, thin.** Two quarters of S&CS growth offsetting PBS is not a
   trend, and management itself flagged part of the +22% as early biosimilar
   timing that will not repeat at that magnitude. Credited on the *level* of
   segment earnings, not the growth rate.
4. **UNKNOWN.** Legislative intent beyond CAA 2026 is not disclosed anywhere.
   Could not be attacked; not credited.
5. **UNKNOWN.** The size and cash reality of the minority claim were pinned this
   run (H1'26 $422M vs H1'25 $186M; NCI equity $161M → $290M, so ~70%
   distributed), but the holders' identity and the reason for the doubling are
   undisclosed, so whether it mean-reverts cannot be attacked. Bounded by the
   §4 haircut; not credited.
6. **SURVIVED, with an adverse incentive on the record.** The 2026 SPS shifted
   to 70% cumulative adjusted income per share from 50%, cutting relative TSR to
   30% — heavier weight on a metric buybacks mechanically improve. Observed
   behaviour is the opposite (TTM repurchases $1,281M vs $3,621M in FY2025,
   shares QoQ −0.02%), so discipline is currently being demonstrated against the
   incentive rather than with it.

Checks that ran. **Base rate:** ~29% of firms earn above their cost of capital
(Damodaran EVA), so no row here assumes persistent excess returns — the 1–2%
terminal rates are price-level repricing. No measured base rate exists for
"regulated intermediary loses its statutory profit pool and replaces it," and
none was invented. **Short case:** a levered 2.3%-net-margin intermediary whose
largest profit pool has a legislated 2028 expiry, whose volume base is already
shrinking (pharmacy lives −4% YTD), whose growth segment depends on the same
manufacturer relationships under political attack, and whose reported cash flow
is inflated by a negative-working-capital float that unwinds with volume — on
that reading 8.9× forward is not cheap, it is a correctly-priced melting ice
cube. **Management incentives:** run, adverse, above. **Disconfirming search:**
run on the seven-filing insider cluster, which dissolved — the CEO's 09-03 Form 4
is an award, the 09-03 Form 144 is 617 shares from an RSU vest. **Moat as
mechanism:** passes — three firms hold ~80% of PBM volume, Accredo's
limited-distribution contracts are bilateral, anchor clients renewed through the
decade; but the mechanism protects volume while the *capture* is legislated away.
**Statistical checks:** the beat streak fails against a 75% base rate; CI's
+4.4pp over SPY in 22 sessions since the prior thesis is one overlapping episode
with effective n of 1 and is not evidence; no repo signal underlies the thesis
(composite coverage 0.0). **Options timing check: N/A** — no dated move-size
claim; path 2 only, liquidity gate failed, disclosed in §4. **Already-held
bias:** real and acknowledged — held position, prior BUY, price up 4.4%. The
mitigation actually applied was re-deriving the base FCF from the FY history
instead of carrying the prior run's TTM figure, which cut the headline implied
return by ~250bp. The per-lot cost-basis check could not run (no grant).

**Closest attack:** the cash-flow-quality attack on condition 1 — TTM FCF is the
top of a declining, volatile series resting on a float that shrinks with volume.
It moved the numbers materially and did not reach the hurdle.

**Flip evidence — toward FLAWED:** Q3 owner FCF tracking below a ~$6.0B
annualized run-rate; or MCR above 84.7%; or NCI income holding at $215M+/quarter
with no one-off explanation; or the September Investor Day cutting the 10–14%
algorithm. **Toward SOUND:** the Q3 10-Q or the FY2025 10-K NCI note identifying
the minority holders and showing the H1'26 doubling is discrete and
non-recurring, *together with* a Q3 print showing PBS pre-tax earnings
stabilising year over year — that closes both unknowns at once.

**p(beat SPY, 63 td): 0.53.** The horizon contains two binary events — an
Investor Day whose reaffirmation is already priced and whose cut is not, and a
Q3 print on a business whose disclosed direction of travel (pharmacy lives −4%,
PBS −27%) is negative. The valuation cushion is large and genuine; a cheap
stock without a catalyst also stays cheap. Slight edge, not conviction.
