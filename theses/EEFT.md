# EEFT — Euronet Worldwide, Inc. — 2026-09-07 (reopen of 2026-08-04, trigger: scheduled sweep supersession)

Price $73.81 (official close, 2026-09-04 — 2026-09-07 was a market holiday) ·
market cap $2,760.8M (37,403,595 shares × $73.81) · next earnings 2026-10-21
or 2026-10-22, tentative and sourced three different ways · EV $3,383.7M ·
adjusted net debt $1,457.3M (ATM cash excluded)

**Prior file:** `research/EEFT-2026-08-04.md` — kill-thesis UNPROVEN,
ownership call BUY at $76.07. A second run on 2026-09-06 logged
`UNPROVEN conditions=5 refuted=0 unknown=1 … (PASS)` to `verdicts.log` but
left no document in `research/` (see §3). The standing reopen trigger
(2026-11-05) is not yet due; this is a scheduled sweep supersession, not a
triggered reopen. Unattended scheduled run.

## 0. The reopen question, answered first

Neither standing reopen condition has fired, and the two that are measurable
today split.

| prior falsifier | actual | status |
|---|---|---|
| Second annual decline in US-outbound remittance market (FY2026) | Not measurable until FY2026 data; Q2 call cites "first annual decline in more than a decade" for the trailing period and "growth in remittance volume to Mexico over the last four months" | NOT TRIGGERED |
| Digital accelerator revenue growth below ~15% for two consecutive quarters | +31% in Q2, +35% year-to-date; four consecutive quarters of Ria digital transaction growth above 30% | NOT TRIGGERED |
| FY2026 adjusted EPS guidance cut below the 10–15% range | Reiterated at +10–15% on the 2026-07-30 call | NOT TRIGGERED |
| FY FCF (ex ATM-cash WC swings) below ~$280M | H1'26 pre-working-capital OCF ≈ $229.4M vs ≈ $207.8M in H1'25 (derived, §3); WC-neutral owner earnings $308.5M | NOT TRIGGERED |
| Net debt / adjusted EBITDA above ~1.5× | 2.22× on the honest measure (adjusted net debt $1,457.3M ÷ TTM EBITDA $657.5M); 0.95× on the headline measure that nets ATM cash | **FIRED** — on the honest measure |
| PI segment constant-currency revenue turning negative | Q2 PI revenue +11% (reported); constant-currency not separately disclosed | NOT TRIGGERED |
| 2026-09-06 trigger: gross debt below $2.4B | $2,653.0M at 2026-06-30 | NOT TRIGGERED (condition unmet) |
| 2026-09-06 trigger: price at or below $60 | $73.81 | NOT TRIGGERED |

The leverage falsifier fires only because the prior runs used the wrong
denominator, not because leverage rose: `stockanalysis`'s `netCash`
(−$622.9M) nets the ~$987.2M of cash that is physically sitting inside the
ATM estate and is not available to retire debt. The 8-K's own split —
unrestricted cash $1,196.7M, ATM cash $987.2M, total debt $2,654.0M — gives
adjusted net debt $1,457.3M. That is 2.22× TTM EBITDA, not 0.95×. This run
treats the prior 1.5× threshold as having been written against a mismeasured
number and restates it in §5 rather than selling on it; interest coverage is
7.05× and the €700M notes were repaid at maturity from the revolver without
strain.

The 2026-09-06 run's "gross debt below $2.4B" condition is also retired
here as the wrong test: gross debt at June 30 is seasonally peak precisely
because it funds the ATM cash the June travel season requires. A gross-debt
threshold on a business that borrows to stock its own machines measures the
season, not the balance sheet.

## 1. Verdict and thesis

**BUY at $73.81.** kill-thesis: **UNPROVEN** — conditions=5 (3 probable,
2 plausible), refuted=0, unknown=2.

**p(beat SPY, 63 td): 0.53** · kill-thesis: 0.47 —
**Disputed expectation:** the market is pricing roughly a 9%/yr return, which
requires the base cash flow to hold flat and no more; the thesis says the
same balance sheet produces $270–310M/yr through the cycle, which prices at
11.6–14.6%. The revision comes from the Q3 print (~2026-10-21) and the Q3
10-Q (~2026-11-10): whether the H1 payables outflow reverses, and whether
Cross-Border operating income stops falling by double digits.

Euronet is three fee-taking payment networks — an ATM and acquiring estate,
a prepaid-content distribution business, and a remittance/payout network —
bought at 8.9× FY2025 GAAP net income, 5.15× EV/EBITDA and a 9.7% FCF yield,
against a 9.01% cost of equity. Its annual net income rose $279.7M → $306.0M
→ $309.5M across 2023–2025 while operating income rose $432.6M → $503.2M →
$529.8M, so the cash-generating level the valuation depends on has a
five-year uptrend behind it, not a slope down. What the market is pricing is
that H1 2026 — net income −15.5% YoY, operating income −10.6% on revenue
+6.6% — is the new trend rather than a policy shock to one segment. It does
not need to be right about that for the price to work: a reverse DCF that
assumes the base never grows again, forever, still implies 9.74%/yr.

**Closest attack:** extrapolate H1 2026's decline as the base rather than as
a shock. At the reported TTM FCF of $268.9M shrinking 2%/yr with zero
terminal growth, the implied return is **8.94% — 7bp *below* the 9.01%
hurdle**; charge historical acquisition spend against the base on top of
that and it is 8.14%, −88bp. The attack fails to land only because the
three-year net-income series slopes *up*, so the decline is two quarters
old. Two more quarters like H1 and this attack is the correct reading.

Load-bearing conditions (5):

1. **The base level of cash generation is ~$270–310M/yr, not lower.**
   *probable* — GAAP net income $279.7M / $306.0M / $309.5M for FY2023–25
   (EDGAR XBRL); the WC-neutral owner-earnings identity net income $288.4M +
   D&A $152.4M − capex $132.3M = $308.5M does not touch working capital at
   all; the effective tax rate is 36.8%, so the base is not flattered by
   NOLs or deferrals.
2. **The H1 2026 operating-cash-flow collapse ($26.0M vs $184.6M) is
   working-capital timing, not earnings quality.** *plausible* — the four
   disclosed working-capital lines account for −$203.4M of swing, and H1 is
   structurally uninformative for this company (2024: H1 $212.2M → FY
   $732.8M; 2025: H1 $184.6M → FY $559.8M). But the cash-flow statement does
   not separate settlement float from trade payables, so a permanent float
   loss tied to falling remittance volume cannot be ruled out. **UNKNOWN in
   the kill pass.**
3. **Payments Infrastructure does not enter accelerating structural
   decline.** *plausible* — Q2 revenue +11% and operating income +2%, but
   the +11% includes CoreCard (acquired Nov 2025) and EEFT does not disclose
   its contribution, so organic PI operating income may already be negative.
   **UNKNOWN in the kill pass.**
4. **Leverage stays serviceable on the honest measure.** *probable* —
   adjusted net debt $1,457.3M = 2.22× TTM EBITDA, interest coverage 7.05×,
   the €700M 1.375% notes repaid at maturity in May 2026 from the revolver,
   H2 interest headwind ≈ $6M.
5. **Terminal growth of 0–2.35% survives the 10-K's disclosed cash-
   displacement risk.** *probable* — and non-binding: the ownership call
   does not depend on it, because a 0% terminal with a 0% growth path still
   clears the hurdle at 9.74%.

**Dominant shared risk factor:** cross-border movement of people (migration
flows plus international tourism) — holdings unavailable in this session.
Both of the two segments under pressure fail together under the same
condition: Cross-Border revenue follows migrant remittance corridors, and
Payments Infrastructure ATM withdrawals follow inbound European tourism.
epay is the only leg that does not.

## 2. Business

**Created:** three networks that each solve a physical-reach problem their
customers cannot solve alone. (a) *Payments Infrastructure* — an ATM estate
plus POS merchant acquiring plus the Ren/CoreCard processing stack: a
traveller gets cash and a currency conversion where their own bank has no
presence; a bank outsources a fleet it does not want to own; an issuer rents
a card-processing platform instead of building one. (b) *epay* — prepaid and
digital content distribution across a retail footprint: a game publisher or
a telco reaches a cash-paying consumer at a corner shop it could never
contract with directly. (c) *Cross-Border Payments* — Ria and xe remittance
plus the Dandelion wholesale payout network: a migrant sends money to a
payout point that exists in the recipient's town.

**Captured:** per-transaction fees, and they are not one business.
Withdrawal fees and dynamic-currency-conversion spread on the ATM estate;
merchant discount and interchange on acquiring; SaaS processing fees on
Ren/CoreCard; distribution commissions from content publishers on epay;
send fees plus FX spread on remittance; and wholesale payout fees from
third parties using Dandelion. Q2 2026 by segment: Payments Infrastructure
revenue $377.1M (+11%) / operating income $86.1M (+2%); epay $294.0M (+5%) /
$32.8M (+5%); Cross-Border $439.6M (−4%) / $43.3M (−34%); Corporate expense
$(25.1)M. [8-K ex-99.1, 2026-07-30]

**Protected:** density and licensing, not technology. The ATM estate and the
payout network are slow, capital-heavy and regulator-heavy to replicate —
a competitor cannot buy its way to a payout point in a Mexican town or a
Polish airport in a quarter. Roughly forty country money-transfer licences
are a per-jurisdiction cost a new entrant pays in years. This is a real
mechanism, and it is also a shallow one: remittance send-fee pricing is
openly competitive (Wise, Remitly, bank rails), and the ATM leg's protection
decays with every point of contactless adoption regardless of how dense the
estate is. The honest statement is that the moat protects the *position*
and does nothing to protect the *price*.

**Control:** one class of common stock, one share one vote, no controlling
holder. Insiders hold 7.71% and institutions the bulk of the rest. Nothing
in the structure forecloses an unsolicited approach or an activist campaign
— which, at 8.9× trailing earnings with a 12.4% short interest, is itself an
open question nobody has answered.

**Operating leverage (Phase 0): positive 2021→2025, sharply negative in
H1 2026.**

| period | revenue | operating income |
|---|---|---|
| FY2021 | $2,995.4M | $184.0M |
| FY2022 | $3,358.7M | $385.3M |
| FY2023 | $3,688.0M | $432.6M |
| FY2024 | $3,989.8M | $503.2M |
| FY2025 | $4,244.2M | $529.8M |
| H1 2025 | $1,989.8M | $233.8M (derived) |
| H1 2026 | $2,120.2M (+6.6%) | $209.1M (−10.6%) |
| TTM | $4,374.6M | $505.1M |

Revenue and operating income compounded together for four years (operating
margin 6.1% → 12.5%). In H1 2026 they separated: revenue +6.6%, operating
income −10.6%, net income $114.9M vs $136.0M (−15.5%). Two quarters is a
direction, not yet a trend — but it is the direction that decides this name.
[EDGAR XBRL `Revenues`, `OperatingIncomeLoss`, `NetIncomeLoss`; H1 2025
operating income derived from FY2025 $529.8M less Q3'25 $195.0M and the
8-K's Q2'25 segment sum $158.6M against the TTM $505.1M]

## 3. Threads pulled

- **The operating-cash-flow collapse, decomposed.** H1 2026 OCF was $26.0M
  against $184.6M in H1 2025, and Q1 2026 alone was **−$122.0M**. The four
  disclosed working-capital lines swing −$203.4M (AR +$162.3M, AP −$368.5M,
  prepaid +$119.3M, accrued −$116.5M) against −$23.2M a year earlier. Backing
  those out, pre-working-capital OCF is ≈ $229.4M in H1'26 versus ≈ $207.8M
  in H1'25 — i.e. it *rose* ~10%. This is the single most important number
  in the file and it is a derivation, not a disclosure: the statement does
  not label its own working-capital subtotal, and the four lines I could
  extract may not be all of them. The honest status is that the mechanism is
  plausible and the magnitude is approximate. What is not in doubt is the
  seasonality: 2024 went H1 $212.2M → 9M $652.5M → FY $732.8M, and 2025 went
  H1 $184.6M → 9M $381.9M → FY $559.8M. Q3 is the swing quarter for this
  company, every year. [EDGAR XBRL
  `NetCashProvidedByUsedInOperatingActivities`; 10-Q 2026-06-30]
- **Why the payables line is the thread and not the answer.** A −$368.5M
  move in trade accounts payable at a payments company is not ordinary
  supplier timing — it is settlement float. Float scales with transaction
  volume. Cross-Border transaction volume is *falling* on the US-outbound
  corridors. So some unknown share of that outflow is a permanent loss of
  float rather than a timing difference, and the cash-flow statement gives
  no way to separate the two. This is the attack that survives the whole
  file, and it resolves in the Q3 10-Q (~2026-11-10).
- **Payments Infrastructure: +11% revenue, +2% operating income.** CoreCard
  closed in November 2025, so Q2 2026's PI revenue contains an acquisition
  Q2 2025's did not, and Q1 carried roughly $10M of one-time plastic-card
  pass-through revenue at minimal profit. If CoreCard contributed anything
  to operating income, organic PI operating income declined. Management's own
  colour supports the soft read: ATM transactions "a bit softer than we
  expected earlier in the travel season," US-to-Europe airline bookings
  "about 5%–8% below the peak 2025 booking window." EEFT does not disclose
  CoreCard's contribution, and it does not lap until Q4 2026 — so this
  cannot be resolved from disclosure before the FY2026 10-K. Marked UNKNOWN.
- **The adjusted-EPS wedge, and what management is paid on.** Q2 GAAP net
  income $77.4M becomes adjusted earnings of $110.0M via intangible
  amortization $9.6M, **share-based compensation $15.7M**, an FX loss, tax
  effects and a non-cash investment gain — and is then divided by 39,060,425
  adjusted shares instead of the 46,177,113 GAAP diluted count. That is two
  independent flatteries stacked, and the full-year guidance (+10–15%) is
  stated in that metric. Every number in this thesis's valuation is GAAP:
  net income after SBC, after intangible amortization, and market cap on the
  actual 37,403,595 shares outstanding. The incentive concern is real but
  the exposure is indirect — the metric rewards buybacks funded from a
  revolver, which is the same lever as condition 4. The proxy was not read
  this run, so the exact bonus metric is UNKNOWN. [8-K ex-99.1]
- **The convertible overhang stays out of the money.** GAAP diluted shares
  include 8,047,923 from assumed conversion of the notes under ASU 2020-06 —
  which applies regardless of moneyness, so their presence in the diluted
  count is not a signal about the price. The $33.2M 0.75% 2049 notes remain
  outstanding at June 30. Conversion prices carried forward from the prior
  run's FY2025 10-K read: ~$127 (0.625% 2030) and ~$188 (2049), both far
  above $73.81. Market cap correctly uses shares outstanding, not the
  if-converted count. [10-Q 2026-06-30]
- **A director bought on the open market.** Thomas A. McDonnell, director,
  bought 781 shares at $70.60 on 2026-08-07 (Form 4, code P, acquired),
  taking direct holdings to 101,000 shares. It is ~$55k — small in dollars,
  and one director is not a pattern. It is nonetheless a change from the
  prior run, which recorded "no insider Form 4s after the drawdown." It is
  the only Form 4 since the print. [EDGAR Form 4, accession
  0001554855-26-001756]
- **The post-call sweep found almost nothing, which is itself the reading.**
  Since the 2026-07-30 print: a 10-Q and an S-8 (2026-08-04), the Form 4
  above, a 13G/A (2026-07-31) and a 13G (2026-08-12). **No 8-K.** So the
  +7.1% move on 2026-09-02 ($68.14 → $72.965 on 955k shares, roughly 1.5×
  normal volume) has no company disclosure behind it. One web search returned
  only a price-target reduction from $102 to $94 and an insider sale priced
  at ~$101 that cannot be recent — the search is mixed-vintage and is treated
  as low-confidence colour, not evidence. Unexplained.
- **Consensus expects Q3 to be flat.** Broker-tier estimate for Q3 2026 is
  $3.68 against a $3.62 actual a year earlier — +1.7%. Against a reiterated
  full-year guide of +10–15% adjusted EPS growth with H1 running roughly
  flat, that means H2 has to carry the entire year, or the guide gets cut.
  The trailing eight quarters show no chronic guide-down pattern: six beats
  (Q1'26 +12.9% the largest) and two small misses (Q2'25 −0.8%, Q2'26
  −3.1%). Report date is disputed across three sources — Robinhood
  2026-10-21 am (unverified), `stocks.db` 2026-10-22 amc, `earnings.db`
  2026-10-29 (edgar-estimate). Treated as ~Oct 21–22, tentative.
- **Options read (mandatory):** path 2 only. EEFT is not in the 24-symbol
  CBOE catalog and `data/options.db` has no `underlyings` row for it, so
  path 1 is unreachable — not a judgment call, a fact about the ticker. The
  liquidity gate **FAILS** and the read is UNRELIABLE, context only. Table
  and gate detail in §4.
- **Data-coverage findings.** EEFT is now in `data/sec_fundamentals.db`
  (added 2026-08-08), which the 2026-08-04 run recorded as absent — its
  `v_screener` row independently confirms the Q2 figures (revenue $1,108.4M,
  net income $77.4M, EPS diluted $1.71, assets $6,493.1M, equity $1,229.9M).
  EEFT is also now carried in `composite.db`'s universe but scores
  `bullish=0 bearish=0 total=0` on every snapshot through 2026-09-08 — it is
  tracked with zero signal coverage, so composite has no opinion. Separately:
  `verdicts.log` line 226 records a 2026-09-06 EEFT run, but no
  `research/EEFT-2026-09-06.md` exists on disk. Its conditions are therefore
  unauditable and this run could not sweep them; only its `reopen=` slug
  survives, and §0 answers it from the slug.
- **Dead ends:** the `/stocks/EEFT/metrics/` route returns the 404 error
  node, so there is no free segment-or-geography breakdown from
  `stockanalysis` for this ticker; the 10-Q carries no geographic revenue
  disaggregation table either, which is why §4's country-weighted ERP rests
  on stated assumptions rather than a disclosure. `stockanalysis`'s share-
  count fields for EEFT are unreliable and were discarded: `sharesYoY` reads
  **+1.937%** (net dilution) against a 10-Q cover-page count of 37,403,595
  at 2026-07-30, an H1 basic weighted average of 38,395,688, and 705,000
  shares repurchased for $50M in Q2 alone — the primary sources all say
  shrink. (`sharesInstitutions` on the same row reads 104.1%, which is
  impossible, so the whole share block is suspect.) `stockanalysis`'s `debt`
  of $2,806.8M also exceeds the 10-Q's $2,653.0M and the 8-K's $2,654.0M by
  ~$153M, consistent with the catalog's warning that this field is a
  carrying value; every debt figure in this file is the primary one. The
  latest transcript is still the 2026-07-30 Q2 call — no conference
  presentations since, so the corpus was not searched.

## 4. Valuation

**Inputs and pairing.** Levered TTM free cash flow paired with **market
cap**, net debt zero by the pairing rule (`fcf = NCFO + capex` is
post-interest under US GAAP; the debt is already served in the flow, so
enterprise value would double-count it). Market cap $2,760,759,347 =
37,403,595 shares (10-Q cover, 2026-07-30) × $73.81 (official close
2026-09-04). Reported TTM figures: OCF $401.2M, capex $132.3M, FCF $268.9M,
net income $288.4M, EBITDA $657.5M, SBC $60.6M.

Four bases are used and each is stated rather than blended:

- **$268.9M** — reported TTM FCF, which contains the H1 working-capital
  outflow and is therefore depressed.
- **$308.5M** — the WC-neutral owner-earnings identity: net income $288.4M
  + D&A $152.4M − capex $132.3M. This never touches working capital, which
  is the point. Capex slightly exceeds real D&A once ~$38M/yr of acquired-
  intangible amortization is set aside, so the identity is not crediting
  under-investment.
- **$245M** — the same base with roughly $60M/yr of historical acquisition
  spend charged against it, per the serial-acquirer check: `fcf` excludes
  M&A, and PI's Q2 revenue growth is partly bought (CoreCard, Nov 2025), so
  an uncharged base gets that growth for free.
- **$350M** — the optimistic case, roughly FY2025's cash generation.

No SBC haircut is applied on top, because every base is built from GAAP net
income, which already expenses the $60.6M. Applying it again — the $208.3M
"FCF − SBC" figure — double-counts, and is reported below only to show what
the double-count does. No minority-interest haircut: net income attributable
to noncontrolling interests was a $0.2M loss in Q2 and $0.0M for H1. No
excess-cash adjustment: the $2,183.9M of cash is $987.2M ATM cash plus
$1,196.7M unrestricted against $2,654.0M of debt — there is no cash pile to
net out, the balance is net *debt*.

**Hurdle:** rf 4.77% (`DGS10`, 2026-09-03, `data/fred.db`) + beta 0.829 ×
ERP 5.12% = **9.01%**. Beta is `stockanalysis`'s 5Y figure and sits inside
the 0.8–1.2 stable band, so no clamp. The ERP is **operations-weighted, not
the US headline**: Euronet's estate is majority non-US, and Damodaran's rule
is to weight the country table by operations. One vintage throughout
(country premium page, "Last updated January 5, 2026"): US 4.46%, developed
Europe blend 4.80% (Germany 4.23 / UK 5.01 / Spain 5.78), emerging blend
6.50% (Poland 5.33 / Hungary 6.69 / Greece 7.08 / Mexico 6.69 / India 7.08 /
Malaysia 5.78), weighted 30% / 45% / 25% → 5.12%. **The weights are an
assumption, not a disclosure** — neither the 10-Q nor the free
`stockanalysis` routes carry a geographic revenue split (§6). The US-headline
alternative (implied ERP 4.14%, 2026-09-01, T-bond 4.75%) would give a
hurdle of 8.20%; the higher figure governs because the operations are not
US. Damodaran's absolute companion for a mature company (rf + 4.5% = 9.27%)
sits 26bp above the computed hurdle, which is the right neighbourhood.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A — WC-neutral owner earnings | $308.5M | 4.0% | 2.35% | **14.55%** | **+554bp** |
| A2 — same, conservative terminal | $308.5M | 4.0% | 1.50% | 14.01% | +500bp |
| B — reported TTM, stressed | $268.9M | 2.0% | 1.50% | 11.59% | +258bp |
| C — optimistic | $350.0M | 7.0% | 2.35% | 17.78% | +877bp |
| E — floor: no growth, ever | $268.9M | 0.0% | 0.00% | 9.74% | +73bp |
| F — acquisition spend charged | $245.0M | 3.0% | 2.35% | 11.68% | +267bp |
| **K1 — kill: H1'26 is the trend** | $268.9M | **−2.0%** | 0.00% | **8.94%** | **−7bp** |
| K2 — kill: declining *and* charged | $245.0M | −2.0% | 0.00% | 8.14% | −88bp |
| X — double-counted SBC (not credited) | $208.3M | 2.0% | 1.50% | 9.32% | +31bp |

The shape is the finding: every scenario that does not assume permanent
decline clears the hurdle by 250–880bp, and the floor case — the base never
grows again, forever — still clears by 73bp. The only scenarios that fail
are the two that extrapolate H1 2026 forward as a trend, and they fail by
7bp and 88bp. That is a wide, one-sided margin, and it is why conditions 3
and 5 being UNKNOWN does not by itself force a pass.

**Integrity checks.**

- **Reinvestment / terminal-ROE warning, answered.** Scenario A with
  `--base-earnings` at GAAP net income $288.4M triggers `growth without
  reinvestment` — base FCF $308.5M exceeds earnings, leaving nothing
  retained to fund 2.35% real growth. The answer taken is the second of the
  two honest ones: the earnings base is understated by acquired-intangible
  amortization (~$9.6M/quarter, ~$38.4M/yr), so cash earnings are ~$326.8M.
  Rerun on that base the warning clears, but `implied_terminal_roe` reads
  **41.97%** at 2.35% terminal — far more than 5 points above the 9.01%
  hurdle and not defensible in perpetuity. Cutting terminal growth to 1.50%
  (scenario A2) brings it to 26.79%, still high; scenario F, which charges
  acquisitions, gives 15.62%, which *is* defensible against EEFT's own 17.2%
  ROIC and 20.3% five-year ROIC. The honest reading: scenario A's terminal
  value is doing too much work, F and E are the ones to lean on, and both
  still clear.
- **Base-year cash tax rate.** Effective rate 36.8% (income tax $170.2M on
  TTM pre-tax ~$458.6M). This is *above* any plausible marginal blended
  rate, not below it — the base is penalised by the foreign mix, not
  flattered by NOLs or deferrals. No haircut; if anything the base is
  conservative.
- **Serial-acquirer check.** Run explicitly as scenario F. CoreCard (Nov
  2025) is inside the revenue growth and outside the FCF definition. F
  charges ~$60M/yr against the base and grows it only 3% — still +267bp.
- **High-SBC check.** SBC $60.6M is 1.4% of revenue — modest, and already
  expensed in every base used. Scenario X shows what deducting it twice
  does; it is reported for transparency and not credited.
- **Market-share sentence.** Scenario A's path compounds FY2025 revenue of
  $4,244.2M at 4% for five years to **$5,164M** — a 21.7% increase over five
  years for a company already operating in ~40 countries. The addressable
  set (global remittance send-and-payout fees, European ATM and acquiring,
  prepaid content distribution) is each measured in tens of billions of
  dollars of annual fee revenue; a $0.9B revenue increase does not require
  share gains of a kind that would trip Damodaran's "bigger than the market"
  test. The exact TAM figures are UNKNOWN and were not fetched (§6), so this
  is a bound, not a computation.
- **Terminal growth vs the disclosed terminal risk.** The 10-K's Item 1A
  names contactless/NFC adoption reducing the need for cash, and hence ATM
  transactions, as the structural risk. Payments Infrastructure is ~34% of
  revenue ($377.1M of $1,110.7M in Q2). A 2.35% nominal terminal — the
  10-year breakeven, `T10YIE` 2.35% at 2026-09-04, which is the working
  ceiling here — implies zero real growth, i.e. the whole company merely
  keeps pace with inflation forever while a third of it shrinks. That
  requires the other two-thirds to grow in real terms, which the digital mix
  (26% of revenue, +31% in Q2, +35% YTD) is currently doing. It is a
  defensible but not a free assumption, which is why scenario E sets
  terminal growth to **0%** and the ownership call rests there rather than
  on 2.35%.
- **Distribution clamp.** US median cost of capital 7.79%, with 80% of firms
  between 5.26% and 9.88% (Damodaran Data Update 5, 2026). Every scenario
  including the two kill cases (8.94%, 8.14%) sits inside that band, and the
  non-declining cases sit at or above its upper edge. Nothing here is below
  the 10th percentile, so the "strong pass regardless of story" clamp does
  not fire.
- **Excess-return base rate.** Only ~29% of firms earn above their cost of
  capital, so the default terminal assumption is fade, not persistence. EEFT
  is in that 29% today (ROIC 17.2%, 5Y 20.3% against a 9.01% cost of
  equity). The valuation does not assume it stays there: scenario E fades
  the excess return to zero growth entirely and still clears.

**Leverage gate: not triggered.** Adjusted net debt $1,457.3M against an
adjusted enterprise value of $4,218.1M is 34.5% — below the ~50% threshold
that would make the equity a call option on the firm. Book equity is
positive ($1,245.3M) and there is no going-concern language. So no
`equity_option` run; the DCF frame governs §1's ownership call. Recorded
because the headline `netDebtEbitda` of 0.95× would have made this look
unambiguous when the honest figure is 2.22× — closer to the gate than the
screen suggests, still clear of it.

**Options-implied move.** Path 2 (Robinhood stopgap) only — EEFT is absent
from the CBOE catalog and from `data/options.db`, so path 1 is structurally
unreachable and no own-history IV percentile exists. Expiry 2026-11-20,
DTE 74 calendar days, which brackets the Q3 print on any of its three
disputed dates (Oct 21 / Oct 22 / Oct 29). ATM strike $75.00; IV is the
mean of the call's 40.30% and the put's 43.12%.

| metric | value |
|---|---|
| spot | 73.81 |
| dte (calendar days) | 74 |
| ATM IV | 41.71% |
| expected absolute move (MEAN, not a ceiling) | 15.04% |
| 1-sigma move | 18.78% |
| RV60 | 43.69% |
| IV > RV60? | NO |
| RV20 | 38.36% |
| IV > RV20? | YES |

**Liquidity gate FAILED → UNRELIABLE.** The call's bid/ask is $3.40/$6.70 —
a $3.30 spread on a $5.05 mark, 65% of mark; the put's is $4.50/$7.60, a
$3.10 spread on a $6.05 mark, 51%. Same-day volume was 1 contract and 0.
Both legs fail the spread test by a wide margin, so the IV reading is
context only and moves no verdict. The two realized-vol windows disagree
(IV below RV60, above RV20) — **that disagreement is the finding**, not
"elevated": RV60 still carries the −8.4% July 31 earnings gap and RV20 does
not. **Timing check NOT APPLICABLE:** the thesis makes no dated move claim —
it asserts a level of cash generation, not a price by a date — so there is
no required move to test against the 1.87σ that a 2-sigma refutation would
need. ATM IV is below 50%, so no whole-percent rounding rule applies to the
implied returns above.

## 5. Falsifiers

**For an owner (sell):**

- **Break —** Cross-Border operating income declines more than 20% YoY again
  in Q3 2026, or declines YoY in both Q3 and Q4. Two more quarters and the
  policy-shock reading is wrong and the structural reading is right.
- **Break —** Nine-month 2026 operating cash flow below ~$250M (2025's was
  $381.9M; 2024's $652.5M). Q3 is this company's swing quarter; if the H1
  payables outflow has not reversed by then, it was float loss, not timing.
- **Break —** Payments Infrastructure operating income declines YoY in any
  quarter while CoreCard is still in the base (through Q3 2026). With an
  acquisition inside the comparison, a decline means organic PI is falling
  materially.
- **Break —** Annual GAAP net income below ~$260M for FY2026 (versus
  $309.5M in FY2025 and $306.0M in FY2024) — that breaks condition 1, which
  is the one everything else rests on.
- **Shift —** Adjusted net debt (total debt less unrestricted cash, ATM cash
  *excluded* from the netting) above ~3.0× TTM EBITDA, i.e. above ~$1.97B at
  today's EBITDA. This restates the prior thesis's 1.5× net-debt-to-EBITDA
  falsifier onto the correct denominator; the old form was already tripped
  by a measurement error (§0).
- **Shift —** FY2026 adjusted EPS guidance cut below +10%, or the buyback
  suspended.
- **Shift —** Shares outstanding rise YoY on the basic count (not the
  if-converted diluted count) — buyback stopped or equity issued.

**Reopen trigger:** 2026-11-10:
`eeft-q3-10q-payables-reversal-with-9m-ocf-above-375m-and-cross-border-op-income-decline-under-10pct-and-pi-op-income-positive-yoy-or-price-at-or-below-58`
— the Q3 10-Q is the latest filing that settles the two UNKNOWNs, and
$58 is roughly where scenario K1's declining-base case would be fully
priced.

## 6. UNKNOWNs

1. **The split of the −$368.5M H1 payables outflow between settlement float
   and ordinary trade payables.** Would come from: a disaggregated
   working-capital note, or the Q3 10-Q showing the direction reverse. Its
   absence does **not** kill the thesis — every valuation base used is built
   from net income and never touches operating cash flow — but it is the
   reason condition 2 is UNKNOWN rather than probable, and it is the reason
   the leverage question cannot be closed.
2. **CoreCard's contribution to Payments Infrastructure revenue and
   operating income.** Would come from: segment re-reporting, or the FY2026
   10-K's acquisition note, or the Q4 2026 print when the acquisition laps.
   Its absence blocks separating organic from inorganic PI performance,
   which is condition 3. It does not kill the thesis because the valuation
   clears at zero growth, but it means the +11% headline cannot be read as
   health.
3. **Geographic revenue split.** Not in the 10-Q, and
   `/stocks/EEFT/metrics/` returns the 404 error node for this ticker, so
   the operations-weighted ERP in §4 rests on assumed 30/45/25 US /
   developed-Europe / emerging weights. Would come from: the FY2025 10-K's
   geographic note. The sensitivity is bounded — the US-headline ERP gives a
   hurdle of 8.20% instead of 9.01%, which only widens every spread — so a
   wrong weighting can only make the thesis look *better*, never worse.
4. **Management's bonus metric.** The DEF 14A was not read this run.
   Whether adjusted EPS is the compensation metric matters for how hard the
   $15.7M/quarter SBC add-back and the 39.06M-vs-46.18M share-count
   substitution get pushed. Would come from: the proxy's compensation
   discussion. Does not kill the thesis — the valuation uses GAAP throughout
   — but it bears on condition 4, since the metric rewards revolver-funded
   buybacks.
5. **Addressable-market sizes.** The market-share sentence in §4 is a
   qualitative bound, not a computed share. Would come from: World Bank
   remittance data and a European ATM/acquiring market study, neither
   fetched. Does not kill the thesis; the required growth (21.7% over five
   years) is modest enough that the bound is not close.
6. **What moved the stock +7.1% on 2026-09-02.** No 8-K, no Form 4, no
   filing of any kind between 2026-08-12 and today. Would come from: a press
   release outside EDGAR, an analyst action, or an index/flow event. Does
   not bear on the thesis either way; recorded because an unexplained 7%
   move on 1.5× volume is exactly the kind of thing that turns out to matter.
7. **The 2026-09-06 run's five conditions.** Its `verdicts.log` line exists;
   its document does not. Unauditable, so this run could not check whether
   it found something this one missed.

## 7. Sources

- **Primary:** 10-Q for the quarter ended 2026-06-30 (filed 2026-08-04;
  cash-flow statement and working-capital lines, debt split $826.2M current
  / $1,826.8M long-term, cover-page share count 37,403,595, basic and
  diluted weighted averages, noncontrolling interest, $33.2M 2049 notes);
  8-K ex-99.1 (filed 2026-07-30; segment revenue / operating income /
  adjusted EBITDA, adjusted-EPS reconciliation, balance-sheet cash /
  ATM cash / total debt split, FY2026 guidance reiteration); Form 4
  accession 0001554855-26-001756 (filed 2026-08-10; director open-market
  purchase); EDGAR submissions index (post-call filing sweep); SEC XBRL
  `companyconcept` API for `Revenues`, `OperatingIncomeLoss`,
  `NetIncomeLoss` and `NetCashProvidedByUsedInOperatingActivities` (all
  annual and quarterly series); FY2025 10-K Item 1A cash-displacement risk
  and convertible conversion prices, carried forward from the 2026-08-04
  run's read.
- **stockanalysis.com (vetted exception):** Q2 2026 earnings call
  transcript, 2026-07-30 (primary-transcribed — management quotations on
  guidance, Mexico corridor, ATM softness, the euro-note settlement,
  buybacks, digital accelerators, and the three analyst exchanges);
  transcripts index (confirming no event since 2026-07-30);
  `/stocks/EEFT/metrics/` (404 error node — recorded as a coverage gap).
- **Broker/market microstructure:** Robinhood MCP — no already-integrated
  official source covers these fields for EEFT. Official close $73.81
  (2026-09-04) and the SPY close for the same session; 91 daily bars
  2026-04-27 → 2026-09-04 for the realized-vol windows and the
  September 2 move; trailing eight quarters of estimate-vs-actual EPS and
  the Q3 2026 estimate of $3.68; the 2026-11-20 option chain, ATM
  instruments and quotes (marks, IV, bid/ask, open interest, volume) for
  §4's implied-move table.
- **Reference data:** Damodaran implied ERP 4.14% as of 2026-09-01 (T-bond
  4.75%) — reported but not used; country equity risk premiums, page "Last
  updated January 5, 2026," used for the operations-weighted 5.12%;
  cost-of-capital distribution (median 7.79%, 80% band 5.26–9.88%, Data
  Update 5, 2026); excess-return base rate ~29%.
- **Point-in-time repo DBs (read-only):** `data/fred.db` — `DGS10` 4.77%
  (2026-09-03), `T10YIE` 2.35% (2026-09-04). `data/stocks.db` `v_latest` —
  price $73.81 at `priceDate` 2026-09-04, market cap $2,760,759,347, EV
  $3,383.7M, TTM revenue / operating income / net income / OCF / capex /
  FCF / EBITDA / SBC, P/E 11.75, forward P/E 6.66, EV/EBITDA 5.15, FCF
  yield 9.74%, beta 0.829, ROIC 17.25% and 5Y 20.28%, ROE 22.37% and 5Y
  19.07%, interest coverage 7.05, short float 12.36%, insiders 7.71%,
  Altman Z 2.02, Piotroski F 6, price target $86.67 across 8 analysts.
  `data/sec_fundamentals.db` `v_screener` — independent Q2 cross-check.
  `data/earnings.db` `v_upcoming_earnings` — 2026-10-29, `edgar-estimate`.
  `data/composite.db` — EEFT in universe, zero signal coverage on every
  snapshot through 2026-09-08. `data/options.db` — no `underlyings` row
  (path 1 unreachable). `research/verdicts.log` — the prior two verdicts.
- **Low-confidence:** management's own framing on the call (Mexico
  stabilization resting on third-party market reports, the World Cup travel
  theory management itself declined to quantify, "we're sitting on an asset
  that we have not done enough with" on xe); one web search returning a
  price-target cut $102 → $94 and an insider sale at ~$101 that cannot be
  recent — mixed vintage, treated as colour and load-bearing on nothing.

## Kill-thesis record

**UNPROVEN — conditions=5, refuted=0, unknown=2.**

Per-condition adjudication:

1. *Base level of cash generation ~$270–310M/yr* — **SURVIVED**. Attacked
   three ways. (a) *The base is declining, not flat*: refuted by the annual
   series — GAAP net income $279.7M (2023) → $306.0M (2024) → $309.5M
   (2025), and operating income $432.6M → $503.2M → $529.8M. The slope is
   up; the decline is two quarters old. (b) *Acquisitions bought the
   growth*: charged in scenario F ($245M base, 3% growth) — still +267bp
   over the hurdle. (c) *Earnings flattered by low cash taxes*: refuted, the
   effective rate is 36.8%, above any plausible marginal rate.
2. *H1 OCF collapse is working-capital timing* — **UNKNOWN**. The −$368.5M
   trade-payables move at a payments company is settlement float, float
   scales with transaction volume, and Cross-Border volume is falling — so a
   permanent float loss cannot be separated from timing in any disclosure
   that exists. Mitigating: pre-working-capital OCF appears to have risen
   ~10% YoY (≈$229.4M vs ≈$207.8M, derived), and H1 is structurally
   uninformative for this company. Resolves in the Q3 10-Q, ~2026-11-10.
3. *Payments Infrastructure not in accelerating structural decline* —
   **UNKNOWN**. Q2 revenue +11% contains CoreCard (Nov 2025) and operating
   income grew only +2%; if the acquisition contributed any operating
   income, organic PI operating income declined. EEFT discloses no CoreCard
   split and it does not lap until Q4 2026. Cannot be attacked with existing
   disclosure.
4. *Leverage serviceable on the honest measure* — **SURVIVED**. Attacked by
   correcting the denominator: `netCash` nets $987.2M of cash physically
   inside the ATM estate, so the real figure is adjusted net debt $1,457.3M
   = 2.22× TTM EBITDA, not 0.95×. At 2.22× with 7.05× interest coverage and
   the €700M notes retired at maturity from the revolver, the condition
   holds. Altman Z of 2.02 (grey zone) was checked and discounted: Z is
   calibrated on manufacturers and systematically misreads a business that
   carries $1B of operating cash on balance sheet.
5. *Terminal growth 0–2.35% survives cash displacement* — **SURVIVED**, and
   demoted: the ownership call does not depend on it, because scenario E
   (0% growth, 0% terminal, forever) clears the hurdle at 9.74%.

Checks run:

- **Base rate.** Only ~29% of firms earn above their cost of capital
  (Damodaran EVA dataset), so persistence of EEFT's 17.2% ROIC is a
  3-in-10 proposition before evidence. Applied by not requiring it: the
  ownership case rests on scenarios E and F, which fade the excess return.
- **The short case, strongest form.** Euronet is a melting ice cube dressed
  as a compounder. Its two largest profit engines are structurally impaired
  — European ATM cash usage falls with every point of contactless adoption,
  and US-outbound remittance has now posted its first annual decline in over
  a decade with no policy reversal in sight. The impairment is masked by an
  adjusted EPS metric that adds back $63M/yr of stock compensation and
  divides by 39.06M shares instead of 46.18M, and by buybacks funded from a
  revolver at a 4.77% risk-free rate. Reported operating cash flow has gone
  $732.8M (FY2024) → $559.8M (FY2025) → $26.0M for H1 2026. The "digital
  accelerator" at 26% of revenue has no disclosed margin and may be replacing
  high-margin ATM revenue with low-margin digital revenue. 12.4% of the
  float is short, and that is the case being made.
- **Management incentives.** Guidance is stated in adjusted EPS growth
  (+10–15%), which excludes SBC and uses the lower share count — the metric
  rewards revolver-funded buybacks, which is the same lever as condition 4.
  The proxy was not read, so the exact bonus metric is UNKNOWN. The thesis
  does not assume management acts against this incentive; it just declines
  to use their metric.
- **Disconfirming search.** Ran against the *bear* facts, not the bull ones:
  the payables line, the CoreCard contamination of PI's +11%, the derived
  H1'25 operating income, the share-count field that disagreed with the
  10-Q, and the debt figure that disagreed with the 8-K. Three of the five
  turned up something (payables, CoreCard, the two bad `stockanalysis`
  fields).
- **Moat as mechanism, not checkbox.** Density and per-country licensing —
  a competitor cannot stand up a payout point in a Mexican town or an ATM in
  a Polish airport in a quarter. That is a mechanism. It is also explicitly
  scoped: it protects the *position* and not the *price*, and it does
  nothing at all against contactless adoption. Written as a shallow moat,
  not a wide one.
- **Statistical checks:** N/A — no claim in this thesis rests on a backtest,
  a hit rate, or a repo signal. `composite.db` carries EEFT with zero signal
  coverage, so there is no repo inference to null-test.
- **Options timing check: NOT APPLICABLE.** The thesis makes no dated move
  claim. Coverage disclosure: path 2 stopgap only (EEFT absent from the CBOE
  catalog and from `data/options.db`), and the liquidity gate FAILED — call
  spread 65% of mark, put spread 51%, same-day volume 1 and 0. Even had a
  dated claim existed, this chain could not have refuted it.

**Closest attack:** treat H1 2026 as the trend rather than the shock. At the
reported TTM FCF of $268.9M declining 2%/yr with zero terminal growth, the
implied return is 8.94% against a 9.01% hurdle — **7bp short**, the only
fair scenario in the file that fails. Charge acquisition spend as well and it
is 8.14%, −88bp. It does not land because the annual net-income series slopes
up, but it is 7bp from landing, and it needs only two more quarters like the
last two to become the correct reading.

**Flip evidence — to SOUND:** the Q3 10-Q (~2026-11-10) showing nine-month
operating cash flow above ~$375M (i.e. the payables outflow reversing) *and*
Cross-Border operating income declining less than 10% YoY. That closes
UNKNOWN 2 and most of UNKNOWN 3.

**Flip evidence — to FLAWED:** Cross-Border operating income down more than
20% YoY again in Q3, or Payments Infrastructure operating income negative
YoY with CoreCard still in the base, or nine-month operating cash flow below
~$250M. Any one of those makes the K1 column the base case rather than the
stress case, and K1 does not clear the hurdle.

**p(beat SPY, 63 td): 0.47.** Written before re-reading §1. The valuation is
genuinely cheap and the hurdle spread is wide on every non-declining base,
but two of five conditions are unverifiable until the print, and the
near-term setup is adverse: consensus expects Q3 adjusted EPS of $3.68
against $3.62 a year ago (+1.7%) while the reiterated full-year guide of
+10–15% requires H2 to carry the whole year. Over 63 trading days that is a
coin flip with a mild tilt against; the thesis's own horizon is two to three
years, and the 63-day number should not be read as the thesis's confidence.
