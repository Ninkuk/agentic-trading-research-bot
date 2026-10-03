# IBM — International Business Machines Corporation — 2026-09-01

Price $231.40 (official close, 2026-09-01) · market cap $218.01B ·
EV $275.15B · net debt $57.1B (stockanalysis; 10-Q gross debt $61.99B less
cash $8.18B = $53.8B) · next earnings 2026-10-21 AMC (Robinhood
`verified=true`; stockanalysis agrees)

User-directed entry. Not on the `candidates` screen; composite carries IBM
only as two informational annotations (`sa_fcf_yield` 6.26, `sa_fscore` 6,
score 0) — no flag.

## 1. Verdict and thesis

**PASS at $231.40.** kill-thesis: **FLAWED** — conditions=6 (1 probable,
3 plausible, 1 possible, 1 refuted), refuted=1, unknown=2.

IBM is a real business again: five years of positive operating leverage,
an 80%-recurring software base growing 8% (ARR $24.6B), a mainframe
franchise whose z17 cycle is running at ~130% of the prior program, and a
free-cash-flow engine that funds a $6.3B dividend with room to spare. But
at $231 the equity is priced at almost exactly its cost of equity once
stock compensation is charged (8.08% implied on the cash-flow-statement
FCF, 8.54% on IBM's own FCF definition, against an 8.50% hurdle), the
reported growth is substantially purchased with debt (Confluent $10.9B and
HashiCorp $6.4B in the last 18 months; net debt $57B), and the Q2 2026
miss — the worst single day in the company's history — exposed a live
question the next print has to answer: whether enterprise budgets moving to
AI hardware are *deferring* IBM's transaction-processing software deals or
*destroying* them. Fairly priced with an open structural question is a
pass, not a buy; the falsifier list below says what would flip it.

**Closest attack:** on the pass itself. IBM's own free-cash-flow
definition excludes the cash it lends to customers through IBM Financing,
and on that basis FY2025 FCF was $14.7B, not the $12.1B the cash-flow
statement shows, with FY2026 guided to ~$15.7B. Run the forward guide
through the same SBC-deducted 4%/2% construction and the implied return is
9.03%, +53 bp over the 8.50% hurdle — a number this repo has called BUY on
before. The attack fails only because it needs the guide to be met in a
year whose first half printed flat, and because the excluded outflow is
real cash funded by $13B of financing debt. It is close enough that the
flip price in §5 is quoted for both definitions.

Load-bearing conditions for an ownership case (tested, not endorsed):

1. *plausible* — The Q2 transaction-processing/ELA shortfall is a timing
   shift, not lost demand: ~1/3–40% of slipped deals closed by 2026-07-22
   (Q2 call); TP still guided down low-to-mid single digits for H2.
2. *plausible* — The recurring ~80% of software keeps growing 8–10%
   organically: ARR $24.6B +8%, Red Hat +11% accelerating, OpenShift ARR
   $2.2B (Q2 call, 10-Q). Downgraded from probable in the kill pass: ARR
   is "current quarter's recurring revenue × 4" with no acquisition
   carve-out (Annual Report), so the +8% includes Confluent's first full
   quarter; total organic software growth was flat.
3. *plausible* — z17 holds ≥120% program-to-program through 2026 and the
   installed-MIPS base (85% stable or growing) converts to TP monetisation
   in 2027 (Q2 call; management's own KPI).
4. *probable* — Free cash flow grows ~$1B in FY2026 off FY2025 (guide
   reiterated 2026-07-22; H1 FCF $4.76B flat YoY with a $600M inventory
   build management says reverses in H2).
5. *refuted* — The price offers a margin of safety over the cost of
   equity (≥ +50 bp on a trailing, SBC-deducted base — the standard this
   repo's BUY calls have used): every trailing base lands between −42 bp
   and +4 bp against the 8.50% operations-weighted hurdle (§4). Only the
   forward guide clears. Fair, not cheap.
6. *possible* — The >$10B five-year quantum programme and the $5B
   Lightwell commitment earn a return. Upside option value only; not load-
   bearing, and a cash drag on conditions 4 and 5 until proven otherwise.

**Dominant shared risk factor:** enterprise IT budget reallocation toward
AI infrastructure (AI capex pace crowding out software and mainframe
spend) — shared by 2 of 17 held names (INTU, MORN — both carry
"generative-AI substitution of paid software/services", a different
mechanism that fails in the same "AI reshapes enterprise software spend"
scenario) · 12 unlabelled (BR, CI, EEFT, G, HIG, LOPE, ORI, PAGS, PRI, SAP,
WRB, YOU have no factor line; CAH, KTB, ZTO carry non-matching factors).

## 2. Business

**Created:** IBM sells the plumbing that large enterprises will not turn
off. The mainframe (IBM Z) runs the core transaction systems of 45 of the
top 50 banks and "over 70% of the world's transaction volume in terms of
value" (Q2 call, primary-transcribed); the customer gets 2–15× lower total
cost of ownership than a migration and a platform with eight-nines
availability. Software (45% of revenue) is the hybrid-cloud and data layer
around that core — Red Hat (RHEL, OpenShift), HashiCorp, Confluent, the
Db2/CICS/IMS transaction-processing stack, automation (Apptio, Instana),
and watsonx. Consulting (31%) is the labour that makes the software and
the client's own transformation projects actually run. The customer
surplus is risk reduction: the systems keep working, and the vendor will
still exist in ten years.

**Captured:** four distinct mechanisms, not one. (a) Perpetual licences
and enterprise licence agreements (ELAs) on the mainframe software stack —
~20% of software revenue, capital-budgeted by the client, lumpy, and where
"every dollar of hardware revenue lands $3+ of software" (CFO, Q2 call).
(b) Subscription and consumption revenue — ~80% of software, ARR $24.6B —
priced per core/per node/per usage, growing 8% and moving toward 10%.
(c) Hardware sales and leases (Z, Power, Storage), cyclical on the
mainframe refresh; Distributed Infrastructure grew 37% in Q2 as clients
bought servers and storage ahead of price rises. (d) Consulting time-and-
materials and fixed-price signings ($5.3B/qtr, ~30% of backlog now GenAI).
Financing (~$0.8B revenue, $13B of segment debt, 80% investment-grade
receivables) is a captive lender that smooths (a) and (c).

**Protected:** the moat is switching cost on the mainframe stack, and it is
real and measurable — 140M installed MIPS, 85% of which are stable or
growing, and no evidence in the filings or the call of clients migrating
off. Outside the mainframe the protection is thinner: Red Hat competes
with hyperscaler-native Kubernetes and SUSE; watsonx competes with every
model vendor and with Microsoft/Google/AWS bundles; Consulting competes
with Accenture and the Indian IT majors on price. The Q2 shortfall showed
the mainframe moat has a *timing* weakness — clients can defer an ELA and
run on existing capacity for years ("they could run on an OpEx model
without doing a big purchase for three years") — even where it has no
*loss* weakness.

**Control:** one class of common stock, one vote per share (DEF 14A
2026-03-06, Q6). No controlling holder: Vanguard 10.03%, BlackRock 8.3%,
State Street 6.03% (proxy, as of 2025-12-31). Insiders hold 0.09%
(stockanalysis). Nothing forecloses an activist or a takeover except size.

**Operating leverage (Phase 0): positive.** Revenue up ~20% over four
years while operating income more than doubled (stockanalysis income-
statement route, which includes restructuring; FY2021 is post-Kyndryl
continuing operations):

| FY | revenue | operating income | margin |
|---|---|---|---|
| 2021 | $57.35B | $5.58B | 9.7% |
| 2022 | $60.53B | $7.52B | 12.4% |
| 2023 | $61.86B | $9.42B | 15.2% |
| 2024 | $62.75B | $9.79B | 15.6% |
| 2025 | $67.54B | $12.62B | 18.7% |
| TTM | $69.10B | $12.76B | 18.5% |

Not loss-making; leverage is heavy in absolute terms (gross debt $62B,
debt/FCF 4.7×, current ratio 0.79) but investment-grade with a $10B
undrawn revolver extended to 2029/2031 (8-K 2026-06-23), so it does not
trigger the Phase 0 kill. Not a domain-science business; nothing here is
unassessable.

## 3. Threads pulled

- **What happened between 2026-05-20 and 2026-07-23 (the stock went $225 →
  $329 → $206).** Three events, all primary-sourced. 2026-05-21: Commerce
  Department letter of intent for Anderon, a quantum wafer foundry with
  $1B of CHIPS incentives and $1B of IBM cash (10-Q, 8-K 2026-05-28).
  2026-05-28: management told investors it would invest ">$10B" in quantum
  over five years toward a fault-tolerant machine in 2029 (8-K Item 7.01).
  2026-07-14: a pre-announcement letter (8-K Ex. 99.1) — revenue $17.2B
  +1%, Software +5%, Consulting flat, Infrastructure −7%, operating EPS
  $2.93 vs $3.02 consensus, with the CEO's sentence "we did not adapt and
  move quickly enough, and numerous large deals failed to close on the
  timelines we expected." The stock fell 25.2% on 64M shares, its worst
  day on record (CNBC/Fortune, low-confidence colour for the record; the
  numbers are from the letter). The round trip is ~$100B of market cap on
  a quantum story and a one-quarter software miss; the business changed
  far less than the price did.

- **Deferral vs destruction — the thread that matters.** The 10-Q and call
  agree on the mechanism: in the last weeks of June clients redirected
  capex to "servers, storage and memory purchases to secure supply-
  constrained infrastructure ahead of expected price increases", so
  "tens" of large ELA deals slipped. TP revenue $2,030M vs $2,208M (−8%
  reported, −9% cc); mainframe −42% in the fifth quarter after z17 launch
  (vs +70% in the launch quarter). Management's evidence for deferral:
  ~1/3–40% of the slipped deals closed in the first three weeks of July
  against a normal ~75% close rate; Distributed Infrastructure +37% with a
  record $500M backlog shows the *same* clients spending with IBM on
  hardware. Evidence against: total organic software growth was flat;
  organic Data revenue was down mid-single digits (Morgan Stanley's
  question, not disputed); the FY software guide came down from 10%+
  ambition to 6–8%; and TP recovery was rescheduled to 2027. Finding: the
  question is open and the Q3 print (2026-10-21) is the first real test.

- **How much of the growth is bought.** Cash acquisitions: $3.3B (2021),
  $2.3B (2022), $5.1B (2023), $3.3B (2024), $8.3B (2025 — HashiCorp),
  $10.9B TTM (Confluent, closed 2026-03-17 for $2.5B current assets +
  $7.2B goodwill + ~$4B intangibles, integrated into Software; 10-Q note
  5). Software revenue +5% in Q2 with organic flat means essentially all
  of the quarter's software growth was Confluent. Goodwill is $74.6B
  against $34.5B of equity. `fcf = NCFO − capex` excludes every dollar of
  this; §4 charges it in one scenario.

- **Balance sheet after the shopping.** Total debt $61,987M at 2026-06-30
  ($48,940M non-financing, $13,047M financing); cash $8,178M; maturities
  $6.1B (2026), $11.5B (2027–28), $9.3B (2029–30), $34.2B after 2030;
  interest $24.2B over the life (Annual Report contractual obligations
  table). Purchase obligations $4.8B total, $2.0B in 2026 — small against
  $69B revenue, so the "asset-light" trailing capex ($1.1B) is not hiding
  a take-or-pay bomb. Pension: worldwide qualified plans 116% funded, US
  plan 137%, overall net underfunded position $2.3B (mostly non-qualified
  and retiree medical), mandated non-US contributions ~$0.8B over five
  years — not an equity haircut worth making. New since the call: a
  Canadian-dollar bond (4.10% 2030, 4.75% 2034; 8-K 2026-08-14) — more
  debt, first C$ issue since 2012.

- **Earnings pattern (Robinhood `get_earnings_results`, broker tier).**
  Seven straight beats by $0.10–0.21 (Q4'24 through Q1'26), then the Q2'26
  miss ($2.93 vs $3.02). That is the managed-guidance pattern breaking,
  which is exactly why the price reaction was so violent. The "actuals"
  are operating (non-GAAP) EPS; GAAP diluted for Q2 was $2.27 (10-Q).
  `sec_fundamentals.db` `v_screener.eps_diluted` is NULL for IBM, so the
  official cross-check ran against the 10-Q directly. Q3 consensus $2.91.

- **Insider filings since the call.** 2026-08-26: SVP Robert David Thomas
  sold 25,000 shares at a $230.32 weighted average (Form 4 filed
  2026-08-28; Form 144 same day), leaving 47,800 — a ~34% reduction six
  weeks after the crash, at the bottom of the range. 2026-08-27: CEO
  Krishna acquired 8,375.56 shares at $238.79 under code I (a plan-based
  discretionary transaction, not an open-market buy). The July 2 cluster
  of Form 4s is RSU vesting with tax withholding (codes M/F). One officer
  selling into a drawdown is a data point, not a thread; recorded.

- **Post-call reconciliation (events after 2026-07-22).** 2026-08-11:
  $240M Together AI deal — IBM deploying Nvidia systems, i.e. IBM selling
  the very hardware the ELA budgets went to (MT Newswires). 2026-08-13:
  OpenAI partnership for enterprise AI on legacy systems. 2026-08-26:
  HRL Laboratories purchase completed (the "transaction signed 2026-07-22
  … Infrastructure segment" in 10-Q note 5). 2026-08-31: Susquehanna PT
  $235 Neutral; Daiwa $217 Neutral (07-29); consensus $245.35, 25
  analysts, "Buy". Nothing since the call contradicts management's
  framing; nothing confirms it either. Silence on the slipped-deal count
  since July 22 is itself the reading.

- **Transcript corpus search (62 calls, 2021-04-19 → 2026-07-22; IBM's
  filing history is far longer, pre-corpus years unquantified because
  `stocks.db` has no `ipoDate` for IBM).** Issuer election: IBM;
  management 1,390 turns, outside 1,165. "Double-digit software" growth
  commitment appears in 14 of 62 documents, first 2021-10-20, peaking on
  the 2026-01-28 call (6 mentions) — so the Q2 reaffirmation is a
  five-year-old promise, not a new one. "Program to program" appears only
  since 2025-01-29 (8 docs) — the z17-era framing. "Deferred/deferral" is
  in 11 docs, heaviest on 2021-10-20 (6) — the last time IBM explained a
  miss as deferral was the Kyndryl-spin quarter. "Quantum" is in 46 of 62
  docs; the 2026-05-05 fireside chat carried 65 mentions. No management
  mention of "moving off" the mainframe before the Q2 2026 call (3 hits,
  all denials). Presence proven; absence never.

- **Options read (mandatory):** path 2 only (IBM is not in the 24-symbol
  CBOE catalog, so `data/options.db` has no history). Chain resolved;
  2026-11-20 expiry brackets the 2026-10-21 AMC print. Table and gate in
  §4.

- **Dead ends:** `/stocks/IBM/filings/` returned no page data (IR PDF
  index unavailable via stockanalysis; EDGAR used instead). Robinhood
  `get_sec_filing` returned "content not available" for every IBM filing
  tried (8-Ks, 10-K), so all filing text came from EDGAR directly.
  `revenue-by-geography`, `gross-profit-by-type` metrics routes are
  Pro-gated `{info}` for IBM; geography came from the 10-Q. The Q2 10-Q
  has no commitments footnote (annual-only); the Annual Report table was
  used. `earnings.db` has no IBM row in `v_upcoming_earnings` as of its
  2026-09-01 `calendar_now` — the date came from the statistics probe and
  Robinhood, which agree. None of these ruled anything out.

## 4. Valuation

**Inputs.** Market cap $218,009,897,846 (statistics probe `marketcap`
hover); TTM `fcf` $13,790,000,000 (= NCFO $14,888M + capex −$1,098M),
levered, paired with market cap; net debt 0 by the pairing rule. Two
haircuts: SBC run-rate $1,877M TTM (cash-flow route `sbcomp`) → SBC-
deducted base $11,913M; and a serial-acquirer charge in one scenario
($2.5B/yr, the 2021–2024 average cash acquisition spend, well below the
$8–11B of the last two years). No minority interest. The TTM base is
flattered: FY2025 `fcf` was $12,102M and IBM's own definition (which
strips financing-receivable swings) printed H1 2026 FCF at $4,760M, flat
YoY; H1 NCFO carried a $1.2B financing-receivable tailwind. Beta 0.709
(stockanalysis, 5Y) floored to the 0.8 band edge.

**Hurdle.** rf 4.75% + beta 0.8 × ERP 4.14% = **8.06%** (Damodaran
headline implied ERP and T-bond, as of 2026-09-01). Operations-weighted
alternative: FY2025 revenue 49.4% Americas / 32.9% EMEA / 17.8% Asia
Pacific (Annual Report); country total-ERPs from the January 2026
`ctryprem` vintage (US 4.46, Canada/Germany/Netherlands/Switzerland 4.23,
UK/France 5.01, Spain 5.78, Italy 6.69, Japan/China 5.14, India 7.08,
Australia 4.23) weight to ≈4.7% (run as 4.69%) → **8.50%**. Both shown;
the ops-weighted one is the honest denominator for a company with half its
revenue outside the US.

| scenario | base FCF | growth ×5y | terminal | implied return | vs 8.06% / vs 8.50% |
|---|---|---|---|---|---|
| A gross FCF, mid-case | $13.79B | 4% | 2.0% | 9.03% | +97 bp / +53 bp |
| **B SBC-deducted, mid-case (finding row)** | $11.91B | 4% | 2.0% | **8.08%** | **+2 bp / −42 bp** |
| C SBC-deducted, conservative | $11.91B | 2% | 1.5% | 7.17% | −89 bp / −133 bp |
| D gross FCF, guide-optimistic | $13.79B | 7,6,5,5,5% | 2.5% | 9.91% | +185 bp / +141 bp |
| E SBC- and acquisition-charged | $9.41B | 4% | 2.0% | 6.81% | −125 bp / −169 bp |
| F stress: no growth | $11.91B | 0% | 1.0% | 6.28% | −179 bp / −223 bp |

ATM IV is 39%, under the 50% line, so two decimals are permitted; the
honest read is still "8–9% on defensible assumptions, 6–7% if you charge
for how the growth is bought".

**The FCF definition matters here, so both are run.** IBM reports FCF as
operating cash flow *excluding IBM Financing receivables* less net capex:
FY2025 $14.7B (Annual Report) against the cash-flow statement's $12.1B, the
$2.6B gap being cash lent to customers through the captive financing arm
(financing receivables consumed $2.7B more cash in 2025 than in 2024 on the
z17 cycle; H1 2026 released $1.2B). That outflow is real cash, but it is
funded by $13B of financing-segment debt at 9:1 leverage and reverses over
a mainframe cycle, so IBM's number is the one most owners use. FY2026 is
guided to about $15.7B on that basis (+$1B). Same construction, same
hurdle:

| scenario | base FCF | growth ×5y | terminal | implied return | vs 8.50% |
|---|---|---|---|---|---|
| G1 IBM-defined FY2025, SBC-deducted | $12.82B | 4% | 2.0% | 8.54% | +4 bp |
| G2 IBM-defined FY2026 guide, SBC-deducted | $13.80B | 4% | 2.0% | 9.03% | +53 bp |
| G3 IBM-defined, conservative | $12.82B | 2% | 1.5% | 7.60% | −90 bp |
| G4 IBM-defined, acquisition-charged | $10.32B | 4% | 2.0% | 7.28% | −123 bp |

G1 and B bracket the trailing answer: −42 bp to +4 bp — the price *is* the
cost of equity. G2 is the only row that clears by a margin, and it is a
forecast, not a trailing base, in a year whose first half was flat.

**Integrity checks.**

- *Reinvestment warning, answered.* With GAAP net income $10,725M as the
  earnings base, FCF ≥ earnings and the tool prints its growth-without-
  reinvestment warning. IBM's earnings base is understated by acquired-
  intangible amortization ($664M in Q2 alone, ~$2.6B/yr; 10-Q segment
  reconciliation). Rerun with cash earnings ≈ $13.3B: scenario B's
  terminal reinvestment rate becomes 10.4% and implied terminal ROE 19.2%
  — above the 8.5% hurdle by ~11 points, i.e. "tough to do in perpetuity".
  Scenario A still trips the warning even on cash earnings. Either cut
  terminal growth toward 1.5% (scenario C, −133 bp) or accept that the 2%
  terminal is carrying an above-hurdle return forever. Scenario E, which
  charges acquisitions, prints a terminal ROE of 6.8% — *below* the hurdle,
  the "destroys value forever" reading — which is the honest description
  of an acquirer paying $7B of goodwill for $1B of revenue.
- *Market-share sentence.* 4% for five years puts revenue at ~$84B by
  2031; enterprise software plus IT services is a multi-trillion market,
  so no "bigger than the market" failure. The share question is inside
  TP: it needs the installed MIPS base to keep growing, which management
  says it is (85% stable or growing).
- *Terminal growth vs Item 1A.* The disclosed terminal risk is "Failure of
  Innovation Initiatives Could Impact the Long-Term Success of the
  Company" together with "Risks from Investing in Growth Opportunities" —
  in plain words, that the mainframe annuity fades faster than software
  and quantum replace it. A 2% terminal survives only if the recurring
  software base (80%, growing 8%) is the terminal business; it does not
  survive if TP is. Scenario C's 1.5% is the version that prices the risk.
- *Base-year cash tax.* Income taxes paid $1,948M in 2025 on $10.3B pretax
  (~19%) vs a mid-teens operating rate and a 21% statutory rate; the base
  is not flattered by an NOL that expires.
- *SBC.* Charged in the finding row ($1.88B, 2.7% of revenue). Share count
  +1.26% YoY (Confluent stock consideration, 3.0M awards) with buybacks
  suspended since Red Hat (10-K Item 5) — dilution, not shrinkage.
- *Cash pile.* $8.2B of cash against $62B of debt; no excess-cash
  adjustment.
- *Distribution clamp.* 8.08% sits inside the 5.26–9.88% band and above
  the 7.79% US median cost of capital — normal, not a strong pass on the
  clamp alone.
- *Leverage gate.* Net debt ≈ 21% of EV, book equity positive, no going-
  concern language → the DCF frame governs; the equity-as-option lens is
  omitted.

**Options-implied move (path 2, Robinhood stopgap).** Expiry 2026-11-20,
80 calendar days, ATM strike 230 (spot 231.40), bracketing the 2026-10-21
AMC print (reprices 2026-10-22). Call mark 18.025 (IV 37.96%), put mark
15.50 (IV 40.03%), IV = mean 39.00%.

| metric | value |
|---|---|
| spot | 231.40 |
| expected absolute move (MEAN, not a ceiling) | 14.49% |
| 1-σ move | 18.26% |
| ATM IV | 39.00% |
| RV60 | 69.43% |
| RV20 | 25.64% |
| IV > RV60? | NO |
| IV > RV20? | YES |

Liquidity gate: call spread $1.65 on an $18.03 mark (9.2%) and put spread
$1.20 on $15.50 (7.7%) both inside the 10%/2-tick gate; volume 148/113
(≥100); OI 471/1,323 → **PASSED** on the four uncalibrated constants (a
pass is unverified, not confirmation). The two realized-vol windows
disagree and the disagreement is the finding: RV60 still contains the
+50% May–June run and the −25% July 14 day, so "not elevated vs RV60" says
nothing; against the calm post-crash RV20 the market is pricing an event.
Timing check: this thesis states no required move for the Q3 catalyst, so
the 2-sigma refutation is **NOT APPLICABLE**; nothing here may confirm
anything.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** Price at or below ~$200 (statement FCF, scenario B) or
  ~$215 (IBM-defined FCF, scenario G1) with the FY2026 FCF guide intact:
  the trailing SBC-deducted run then clears the 8.50% hurdle by ~+50 bp.
  At $205 scenario B prints 8.46% — still at the hurdle, not over it.
- **Shift —** Q3 2026 print: Software constant-currency growth ≥8% with
  Transaction Processing flat or better YoY, or organic software growth
  back to mid-single digits — the deferral hypothesis becoming evidence.
- **Break (for the pass) —** Two consecutive quarters of TP growth with
  z17 ≥120% program-to-program and FY FCF ≥ guide; at that point the
  mainframe-timing risk is closed and the name is re-underwritten.

For an owner (sell):

- **Break —** FY2026 free-cash-flow guide cut, or software guide taken
  below 6%: the "productivity funds everything" claim fails.
- **Break —** A second quarter of TP down high-single digits with the
  slipped-deal count no longer disclosed: deferral has become destruction.
- **Shift —** z17 program-to-program falls below 120%, or installed MIPS
  "stable or growing" drops below ~80%.
- **Shift —** Another debt-funded acquisition above ~$5B before net debt
  falls, or a rating action on the senior unsecured.
- **Shift —** Quantum spend shows up as capex materially above the ~$1.1B
  trailing run-rate (the $10B/5yr programme leaving R&D and entering FCF).

**Reopen trigger:** 2026-10-23: ibm-q3-print-software-cc-growth-at-or-
above-8-with-tp-flat-or-better-or-fy26-fcf-guide-cut-or-price-at-or-
below-200

## 6. UNKNOWNs

1. **How many of the "low tens" of slipped ELA deals have closed since
   2026-07-22, and their dollar value.** Source: the Q3 call. Absence
   until then does not kill the pass; it is the reason for it.
2. **Organic (ex-Confluent) recurring software growth as a number.**
   Management said total organic software was "flat" in Q2 and that the
   recurring 80% grew 8%; the 10-Q does not split acquisition
   contribution by line, and ARR is defined with no acquisition carve-out.
   Confluent's standalone run-rate was roughly $1B+ of recurring revenue
   (low-confidence recollection, not verified here), which could be most
   of the $1.8B year-over-year ARR increase. Source: the Q3 10-Q, or an IR
   reconciliation. Its absence is what keeps condition 2 at *plausible*.
3. **The cash phasing of the >$10B quantum programme** (R&D vs capex vs
   M&A) and whether the FY2026 FCF guide already absorbs it. Source: the
   FY2026 10-K capex commentary. If most of it is capex in 2027–2029, the
   base FCF in §4 is too high by up to $1–2B/yr — enough to move every
   scenario one row down the table.
4. **Kyndryl-era share-count and cash-flow comparability** for the
   Phase 0 table's FY2021 row. Minor; direction is unaffected.

## 7. Sources

- **Primary:** 8-K 2026-07-14 with Ex. 99.1 investor letter
  (0000051143-26-000070); 8-K 2026-05-28 Item 7.01 (quantum $10B);
  8-K 2026-06-23 (credit facility extensions); 8-K 2026-08-14 (C$ notes);
  Form 10-Q for the quarter ended 2026-06-30 (0000051143-26-000078:
  segments, geography, debt, Confluent PPA, FCF, MIPS commentary); Form
  10-K FY2025 and its Annual Report exhibit (0000051143-26-000010: Item
  1A, contractual obligations, pension funded status, geography, cash
  taxes, buyback suspension); DEF 14A 2026-03-06 (vote structure, 5%
  holders); Forms 4 filed 2026-08-28 (Thomas sale, Krishna code-I
  acquisition) and Form 144 2026-08-26; Q2 2026 earnings call 2026-07-22
  (stockanalysis transcript — primary, transcribed) and the 62-call corpus
  search.
- **stockanalysis.com (vetted exception):** `/stocks/IBM/statistics/`
  (market cap, EV, FCF, capex, debt, beta, shares, short interest,
  analyst consensus), `/financials/income-statement/`, `/cash-flow-
  statement/`, `/balance-sheet/` (FY2021–TTM series), `/metrics/revenue-
  by-segment/`, `/transcripts/`.
- **Broker/market microstructure (Robinhood MCP):** `get_earnings_results`
  (estimate-vs-actual pattern — the estimate side is not covered by any
  integrated official source), `get_equity_quotes` (official close),
  `get_equity_historicals` (90 daily closes for RV), `get_option_chains` /
  `get_option_instruments` / `get_option_quotes` (path-2 implied move),
  `get_equity_news` (post-call event sweep), `get_sec_filing_index`
  (filing dates; content unavailable). `get_financials` not used.
- **Reference data:** Damodaran implied ERP 4.14% and T-bond 4.75% as of
  2026-09-01; country risk premiums, January 5, 2026 vintage; US cost-of-
  capital distribution (Data Update 5, 2026).
- **Point-in-time repo DBs (read-only):** `stocks.db` v_latest 2026-08-31
  ($233.87, fScore 6, zScore 3.4, RSI 48.7, no ipoDate); `sec_fundamentals
  .db` v_screener (Q2'26 revenue $17,162M, NI $2,165M, D/E 3.41; eps NULL);
  `composite.db` (annotations only, no flag); `portfolio.db`
  v_latest_positions (17 symbols for the factor overlap); `options.db`
  (no IBM history — path 1 unavailable); `earnings.db` (no IBM row).
- **Low-confidence:** CNBC, Fortune, Motley Fool and GuruFocus coverage of
  the 2026-05-21 and 2026-07-14 sessions (used only for the size of the
  moves and the "worst day on record" framing; every number was taken from
  the filings); MT Newswires/Benzinga headlines for the August event sweep.

## Kill-thesis record

**Ledger:** 2026-09-01 IBM FLAWED conditions=6 refuted=1 unknown=2 —
ownership call PASS at $231.40. The thesis attacked is the ownership case
in §1; the PASS is what survives.

**Per-condition adjudication.**

1. Deferral not destruction — **UNKNOWN.** Attack: the only evidence is
   management's own count (~1/3–40% of "low tens" of deals closed by
   2026-07-22 vs a ~75% normal close rate), undisclosed since. The
   disconfirming search found the *cause* persisting: enterprise memory
   and server prices up 50–200% in H1 2026 with shortages expected into
   mid-2027 (EE Times, IDC, Network World — low-confidence colour,
   consistent across sources). That is evidence the budget diversion
   continues, not evidence the deals are lost; management's own low-end
   guide ("recent spending dynamics persist through the second half") is
   the base case it implies. Cannot be credited; resolves at the Q3 print.
2. Recurring software grows 8–10% organically — **UNKNOWN** (downgraded
   from probable). Attack: ARR is "current quarter's recurring revenue × 4"
   with no acquisition carve-out (Annual Report), Confluent closed
   2026-03-17, so Q2's +8% ARR is Confluent's first full quarter; total
   organic software was flat. The Q1 figure (+7% recurring, with only
   two weeks of Confluent) is the best evidence for a mid-to-high-single-
   digit organic rate, and it is one quarter. Not refuted; not verifiable
   from any disclosure.
3. z17 ≥120% program-to-program and TP monetises in 2027 — **SURVIVED,
   weakly.** Attack: mainframe −42% in the fifth quarter and TP −9% were
   both below management's own expectations; the metric is management's
   and unaudited. Base rate: every prior IBM mainframe cycle has declined
   in year two, so the *shape* is normal; the claim is about the level,
   and 130% five quarters in is disclosed in the 10-Q. Survives as
   plausible, not probable.
4. FY2026 FCF +$1B — **SURVIVED.** Attack: H1 flat, so H2 must carry the
   full $1B; the bridge (inventory $600M reversing, front-loaded cash tax
   and capex) is plausible and IBM has hit or beaten its FCF guide in
   each of 2023–2025 ($14.7B in 2025 vs $13.5B+ guided). Incentive check
   cuts both ways: FCF is a PSU metric and operating cash flow an AIP
   metric (DEF 14A), so management is paid to hit it — and paid on a
   definition that excludes the financing-receivable outflow.
5. Margin of safety over the cost of equity — **REFUTED.** Evidence: §4
   scenarios B (−42 bp) and G1 (+4 bp) bracket the trailing SBC-deducted
   answer; only the forward guide (G2, +53 bp) clears. Charging
   acquisitions (E, G4) or cutting terminal growth to the Item 1A risk (C,
   G3) sends it −90 to −169 bp. Repairable by price (~$200–215) or by the
   Q3 print converting G2 from a forecast to a base.
6. Quantum/Lightwell earn a return — **UNKNOWN, not load-bearing.** No
   disclosure phases the >$10B; the CHIPS-funded Anderon is a letter of
   intent. Treated as option value and as a drag on 4 and 5.

**Standing checks.** *Base rate:* only ~29% of firms earn above their cost
of capital (Damodaran EVA), and scenario B's 2% terminal already assumes
IBM stays in that minority forever; large-cap serial acquirers paying
7× revenue in goodwill (Confluent: $7.2B goodwill on ~$1B revenue)
typically do not earn their cost of capital on the acquired dollars.
*Short case:* a levered serial acquirer with flat organic growth, a
mainframe cycle rolling over, TP structurally eroding as workloads run on
existing capacity, Consulting flat while AI deflates services pricing, a
$6.3B dividend absorbing half of FCF, goodwill at 2.2× book equity, and a
$10B quantum programme that is an announcement, not a business — priced at
20× earnings. It is a coherent short; what it lacks is a catalyst beyond
the Q3 print, and the 80%-recurring base is real cash. *Management
incentives:* AIP on revenue and operating cash flow, PSUs on revenue,
operating EPS and FCF over three years (DEF 14A). Revenue in both
programmes is not organic revenue, so a $19B acquisition spree lifts the
comp metric whether or not it earns its cost of capital — the thesis's
"growth is bought" concern is an incentive, not an accident. CEO 2025 AIP
paid at 150% of target. *Disconfirming search:* ran on memory-shortage
persistence (found, above) and on post-call evidence of TP deal recovery
(nothing beyond management's July 22 count — silence). *Moat as
mechanism:* the mainframe switching cost is a mechanism (140M MIPS, 2–15×
TCO, eight-nines availability) and it held — no evidence of migration off.
Its *timing* weakness (clients defer ELAs and run on existing capacity)
is now demonstrated, which is what §1 says.

**Statistical checks:** N/A — no backtest or repo signal underlies the
thesis; composite carries IBM as annotations only.

**Options-market timing check:** ran on path 2 only (IBM not in the CBOE
catalog; no `options.db` history). 2026-11-20 expiry, 80 DTE, brackets
the dated Q3 catalyst; liquidity gate passed on uncalibrated constants.
The thesis states no required move, so the 2-sigma refutation is NOT
APPLICABLE and nothing was refuted or confirmed. IV 39% vs RV20 25.6% /
RV60 69.4%: the windows disagree (the 60-day window still holds the
May–June +50% run and the −25% day), which is the finding.

**Closest attack:** the IBM-defined-FCF attack on the pass (G2: +53 bp on
the forward guide). It fails only because it needs a forecast as its base
in a year whose first half was flat.

**Flip evidence.** To SOUND for an owner: Q3 software constant-currency
growth ≥8% with TP flat or better and the FY FCF guide held — that
converts conditions 1 and 2 from UNKNOWN to SURVIVED and G2 from forecast
to base. To FLAWED-dead: a second quarter of TP down high-single digits
with the slipped-deal count no longer disclosed, or the FY FCF guide cut.
To flip the PASS to BUY on price alone: ~$200 (statement FCF) to ~$215
(IBM-defined FCF) with the guide intact.
