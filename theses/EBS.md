# EBS — Emergent BioSolutions, Inc. — 2026-08-10

Price $4.47 (Robinhood quote) · market cap $229.19M · next earnings
2026-10-28

Identity: Emergent BioSolutions, Inc., NYSE:EBS, CIK 0001367644, Gaithersburg MD
— the biodefense / medical-countermeasures manufacturer and owner of NARCAN
nasal spray. US listing, `/stocks/` route. Not entered from the candidates
screen; this is a directed run on a name that fell 40.7% in three sessions.

**Session constraint (judgment call, affects sourcing):** the sandbox in this
run denied `sqlite3`, `curl`, and arbitrary Python, so the point-in-time DB
cross-checks (`sec_fundamentals.db`, `stocks.db`, `composite.db`,
`earnings.db`) and direct SEC EDGAR fetches could not be executed. Live figures
come from the stockanalysis `__data.json` probe where it ran, and from WebFetch
against the same site where the probe's CLI could only print schema. Every
number below is labelled by tier in §7. Two UNKNOWNs in §6 exist solely because
of this and are recoverable on a normal run.

## 1. Verdict and thesis

**PASS at $4.47.** kill-thesis: **FLAWED** — conditions=5, refuted=1,
unknown=2. What is flawed is the *ownership* case — condition 4 was attacked
and the evidence stands against it — which is why the call is a pass.

EBS is a leveraged stub: a genuinely good US
government biodefense franchise bolted to a consumer naloxone franchise that is
now in priced-driven decline, sitting on $450M of 3.875% notes due 2028-08-15
that must be refinanced at roughly triple the coupon. The apparent bargain
signals — 37.5% TTM FCF yield, 0.67x book — both dissolve on inspection: the
TTM cash flow includes quarters management has explicitly guided away from, and
0.67x book is 2.9x *tangible* book once the just-impaired intangibles come out.

**Closest attack:** the MCM-strength / short-squeeze case, which did *not*
land — detail in the Kill-thesis record.

Load-bearing conditions (count: 5):

1. **The $450M 2028 note maturity is refinanced without wiping out the
   equity** — *plausible only*, and materially damaged (§3, the 2028-wall
   thread). Refinancing 3.875% paper at a market rate costs ~$28M/yr of
   incremental interest against an estimated $36M of owner FCF.
2. **MCM government revenue holds ~$500M+/yr through the refi window** —
   *probable*. Q2'26 MCM revenue $168M, highest Q2 since 2020; 10+ contract
   awards YTD; international ~20% of H1 MCM. This is the real asset.
3. **NARCAN cash flow does not decay faster than the $191.3M impairment
   already assumes** — *UNKNOWN*: the cash-flow model behind the impairment is
   not disclosed.
4. **The H2'26 EBITDA collapse is contract timing, not the new run-rate** —
   **REFUTED** (§3, the H2'26 guide thread).
5. **No further guidance cut before the refi window** — *possible only*, and
   now hard-wired to a covenant: consolidated total leverage ≤5.25:1.00,
   first tested for the quarter ending **2026-09-30**.

## 2. Business

**Created:** Two unrelated customers. For the US government, EBS makes
stockpile products nobody else reliably makes: anthrax vaccines (BioThrax,
CYFENDUS), ACAM2000 smallpox vaccine, botulism antitoxin (BAT), TEMBEXA
(smallpox antiviral), Ebanga (Ebola). The value is *option insurance* — the
government buys the capability to respond, not doses it expects to use. For
consumers and public-health buyers, NARCAN reverses an opioid overdose in
minutes without training; the value is a life saved by a bystander.

**Captured:** Not one mechanism, three. (i) Multi-year BARDA/ASPR
procurement contracts and modifications against the Strategic National
Stockpile — Q2'26 alone booked a $52.7M ACAM2000 modification and a $64.5M BAT
modification. (ii) Growing international MCM sales, ~20% of H1'26 MCM revenue,
following ACAM2000 approvals in Saudi Arabia and Singapore for mpox. (iii)
Branded OTC and public-health sales of NARCAN at a price premium to generic
naloxone. TTM revenue $770.2M; H1'26 was $390.4M.

**Protected:** For MCM the mechanism is real and unusually durable: the
moat is *regulatory and physical*, not commercial. A competitor needs an FDA
licence for a product that cannot be efficacy-tested in humans (approval runs
through the Animal Rule), a validated fill-finish plant, and a customer whose
entire procurement logic favours a proven incumbent over a cheaper newcomer.
That is a decade-long barrier and it is holding.

For NARCAN the mechanism has **just failed**, and this is the whole story. The
protection was a first-mover OTC switch and brand recognition — never a patent
thicket on a 1970s molecule. A 4mg OTC competitor was approved 2026-06-16 and a
10mg prescription product launches this month. Management's own words on the
Aug 5 call: *"we do expect to see additional price erosion."* Their strategic
response — *"new carrying cases, multi-packs, wall kits, and brand emphasis"* —
is packaging. When the defence of a >50%-share franchise is carrying cases, the
silence about the actual mechanism is the answer.

**Operating leverage (Phase 0):** not recorded in original run.

## 3. Threads pulled

- **The H2'26 guide — timing or a break? (REFUTES condition 4)** The bull
  reading is that MCM revenue is lumpy government timing and H2 will catch
  up. Two pieces of evidence stand against it, and both are the company's:

  - **Management attributed the cut to the commercial segment, not MCM.** CFO
    Rich Lindahl: the revision *"primarily reflects lower expected commercial
    revenue in the second half of the year, driven by increased competitive
    pressure in NARCAN."* Contract timing is not the stated cause.
  - **Gross margin was cut alongside revenue.** Adjusted gross margin
    guidance went 45–47% → 42–44%. Timing moves revenue between quarters; it
    cannot compress gross margin 300bp. A 300bp margin cut is price erosion.

  The arithmetic of the guide is worse than the headline. H1'26 revenue was
  $390.4M; the FY26 midpoint of $660M implies **H2'26 ≈ $270M** — 0.69x H1
  and −29% against H2'25's $379.8M. On EBITDA it is starker: H1'26 adjusted
  EBITDA was ~$137M against a full-year guide of $130–150M, so **H2'26
  adjusted EBITDA is guided to roughly $0–26M.** And 2025 offers no seasonal
  excuse — H2/H1 ran 1.05x that year.

  **Verdict: refuted.** Condition 4 fails on management's own attribution.
- **The 2028 wall, and why it is an equity risk (damages condition 1).**
  The April 2026 refinancing was reported as a win — *"reduced interest
  rates, and enhanced operating and financial flexibility."* The 8-K terms
  say otherwise. The $150M initial term loan (plus $75M delayed draw) is from
  **OrbiMed Royalty & Credit Opportunities V** with Jefferies Finance, priced
  at **Term SOFR (3.00% floor) + 6.25%** — a ≥9.25% all-in, first-lien,
  healthcare-specialty-lender rate. Companies with cheap options do not
  borrow from OrbiMed.

  The 2031 maturity is contingent. It **springs to 91 days before the 2028
  notes** (≈2028-05-16) unless, at that date, note principal outstanding is
  ≤$75M **and** the company holds $75M of liquidity plus funds to repay the
  notes in full. From $450M outstanding, the $75M note-repurchase
  authorization cannot reach that test. The wall is real and dated.

  The equity-level point the credit framing misses: the 3.875% coupon is a
  legacy 2020 rate. Refinancing $450M at a market rate near what the
  incumbent secured lender already charges (~10%) raises interest from ~$17M
  to ~$45M — roughly **$28M/yr of incremental interest against an estimated
  $36M of owner FCF**. Refinancing does not merely need to succeed;
  succeeding consumes most of the equity's cash flow. See §4.

  **Not refuted — damaged.** Whether the market will fund it is knowable
  from the 2028 notes' trading price, which I could not obtain (§6).
- **The covenant clock (re-frames condition 5).** The term loan carries a
  **consolidated total leverage ratio ≤5.25:1.00, tested every fiscal
  quarter commencing with the quarter ending 2026-09-30** (delayed draw
  additionally requires secured leverage ≤1.75:1.00). The ABL revolver was
  *halved*, $100M → $50M.

  The first test lands 51 days from now and should pass: TTM adjusted EBITDA
  at Q3'26 still contains the strong Q1'26 and Q2'26 quarters (~$167M by my
  build), putting gross leverage near 3.5x. The danger is the roll. As those
  two quarters age out during 2027, a TTM built on the guided H2'26 run-rate
  (~$50M annualised) would put leverage near 11x — far through the covenant.
  **Condition 4 is therefore not just a valuation input; it is a solvency
  input.** That is the single most important structural finding in this run.
- **Management's leverage number is backward-looking.** On the same call
  that cut EBITDA guidance 15%, management said net leverage *"remained
  stable at 1.9x trailing 12-month adjusted EBITDA."* That is arithmetically
  true (≈$448.5M / ≈$237M TTM adjusted EBITDA) and decision-irrelevant. On
  their own new FY26 guide it is **$448.5M / $140M = 3.2x**; on TTM GAAP
  EBITDA of $36.9M it is 12.2x. Not a misstatement — but the metric chosen
  was the one that stopped describing the company on the day it was quoted.
- **Capital allocation while walled in.** Two authorizations run
  concurrently: $75M to repurchase the 2028 notes, and **$50M to repurchase
  shares** through March 2027. Buying the notes below par is correct — it
  deleverages at a discount and chips at the springing test. Buying the
  *stock* is not obviously so: TTM "net common stock issued/(repurchased)"
  was **−$35.4M**, spent while the stock traded roughly $7–$12. It is $4.47
  now. That is cash converted into losses and no longer available for the
  covenant or the refinancing.
- **The statistics route is lying about this company (methodology).** Worth
  recording because it would have flipped the triage. `/stocks/EBS/
  statistics/` reports TTM operating income **+$140.5M** and ROIC
  **+16.18%**. `/financials/income-statement/` reports **−$66.0M** and the
  ratios route reports ROIC **−9.29%**. The catalog documents exactly this:
  `/statistics/` excludes impairment- and restructuring-type charges and
  nothing labels the difference. The tell was internal: EV $677.69M at
  EV/EBITDA 18.37 implies EBITDA of ~$36.9M, which is impossible beside a
  $140.5M operating income. −66.0 + 102.9 D&A = 36.9 ✓. The quarterly
  columns reconcile to the annual (76.5 − 27.9 + 10.5 − 125.1 = −66.0 ✓).
- **Options read (mandatory):** path 2 only (EBS is not in the 24-symbol
  CBOE catalog, so no `iv30` percentile exists; path 1 does not apply this
  run) — see §4's metric table.
- **Dead ends:**

  - **Robinhood `get_earnings_results` vs GAAP.** Trailing-8-quarter actuals
    sum to roughly +$1.44 TTM EPS against GAAP −$3.55 — a $4.99/share gap.
    Confirms the standing note that these actuals are not GAAP; it added
    nothing here. The estimate side did show a pattern worth one line: five
    of the last seven quarters beat, often hugely (Q3'25 +1.06 vs −0.03
    est), which is consistent with lumpy MCM revenue nobody models well, not
    with managed guidance.
  - **Cash-tax flattery check — passes, in the wrong direction.** TTM cash
    taxes were $30.8M *paid despite GAAP losses* (valuation allowance /
    foreign tax). So the base FCF is not flattered by an NOL shield; there
    is no tax tailwind to look forward to either.
  - **Insider selling.** A search surfaced a report of director share sales
    but the source 403'd and EDGAR was unreachable this session. Not used.
    Recorded as UNKNOWN (§6) rather than as colour.
  - **Levi & Korsinsky investigation** into whether EBS misled on the FY26
    outlook and its characterization of NARCAN demand and pricing.
    Plaintiff-firm investigation notices follow essentially every >25%
    single-day drop; the base rate of these becoming material is low. Noted,
    not weighted.

## 4. Valuation

Reverse DCF, levered FCF paired with **market cap** (never EV — `fcf` here is
`ncfo + capex`, post-interest). Market cap $229.19M. Hurdle = rf + beta × ERP =
4.74% + 2.36 × 4.28% = **14.84%**, with rf and implied ERP as of **2026-08-01**.

**ATM IV is 84.53%, so every implied return below is quoted to the nearest
whole percent and the range is wide.** A two-decimal figure on this name would
be arithmetic, not knowledge.

**Base FCF build (the load-bearing assumption).** FY26 guided adjusted EBITDA
midpoint $140M − ~$40M cash interest (forward run-rate; quarterly interest has
fallen 15.2 → 14.7 → 11.0 → 10.0 post-refi) − ~$15M capex − ~$30M cash tax
(TTM actual $30.8M) − $18.9M SBC (a real cost adjusted EBITDA adds back) =
**~$36M owner FCF**.

| scenario | base FCF | growth path | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| TTM, naive | $67M (TTM FCF − SBC) | flat, tg 2% | 2% | **30%** | +1513bp |
| **Base** | $36M | flat, tg 2% | 2% | **17%** | +200bp |
| Declining 10%/yr | $36M | −10%/yr, tg 0% | 0% | **10%** | −458bp |
| Stress | $20M | flat, tg 2% | 2% | **10%** | −467bp |
| **Base + 2028 refi** | $36M → $8M from yr 3 | tg 0% | 0% | **4%** | **−1036bp** |

Read honestly, three of five cases fail the hurdle and the last one fails it by
a mile. The two that pass are the two that cannot be defended:

- The **$67M** case uses TTM cash flow containing Q3'25 (EBITDA $102.4M) — a
  quarter the company has now guided away from. It is the number the screen
  sees and it is stale by construction.
- The **$36M flat** case (+200bp) holds interest at $40M **forever**, which is
  false by 2028-08-15 at the latest. Stepping FCF down by the ~$28M/yr that
  refinancing $450M from 3.875% to ~10% costs takes the same case to **4%/yr —
  below the risk-free rate of 4.74%**. That is the honest base case, and it is
  the row that decides this write-up.

**Terminal integrity.** `implied_terminal_roe` is **3.85%**, far below the
14.84% hurdle — the terminal value assumes this company destroys value in
perpetuity. For once that is not a red flag to defend away but the correct
description of a business whose larger-margin franchise is in price decline; I
am not claiming otherwise. Terminal growth was capped at 2% (below rf 4.74%) in
the passing cases and 0% in the stress cases. The dominant structural terminal
risk is single-customer concentration in US government biodefense procurement
(appropriations risk) layered on a naloxone franchise with no molecule
protection; 2% does not survive that on the commercial half, which is why the
deciding row uses 0%.

**Beta sensitivity.** Flooring beta into the anchors' 0.8–1.2 stable band gives
a 9.88% hurdle and turns the base case to +697bp. I do not use it. That band
rule exists to stop a thin-float name printing an artificially *low* beta and
buying itself a free pass; EBS's 2.36 is a real beta on a real distressed,
levered microcap, and flooring it here would launder risk out of the answer.

**Market-share sentence:** not applicable in the usual direction — no case
here assumes growth. The base case assumes a >50% naloxone share *erodes*, and
even so does not clear the hurdle once the refi is priced.

**Book value is not the floor it appears to be.** Shareholders' equity $341.4M
looks like 0.67x P/B. But $261.8M of that is other intangible assets — the same
asset class just written down $191.3M — and goodwill is already zero. Tangible
equity is ~$79.6M, i.e. **~$1.55/share against a $4.47 price, or 2.9x tangible
book.** The "trading below book" comfort does not survive the subtraction.

**Options-implied move** (path 2 only — EBS is not in the 24-symbol CBOE
catalog, so no `iv30` percentile exists; path 1 does not apply this run).
Expiry 2026-12-18, **DTE 130**, $5 strike chosen as ATM on delta (+0.535 /
−0.486) over the nominally-nearer $4 strike, spot $4.49:

| metric | value |
|---|---|
| spot | 4.49 |
| expected absolute move (MEAN, not a ceiling) | 42.32% |
| 1-σ move | 50.45% |
| ATM IV | 84.53% |
| RV60 | 89.09% |
| RV20 | 131.95% |
| IV > RV60? | NO |
| IV > RV20? | NO |

IV sits **below both** realized windows, so this is not an elevated-IV setup —
the options market is pricing less movement than the stock has actually
delivered over 20 and 60 days. **This is not evidence for the thesis** in
either direction; it only means no timing refutation is available here, and the
pass call does not require a move.

**The chain fails the liquidity gate badly and the table above is marked
UNRELIABLE**: the $5 call is bid 0.45 / ask 1.10 against a 0.775 mark (an ~84%
spread, versus a 10%-of-mark gate), and both $4 legs show open interest 0. The
gate's four constants are themselves uncalibrated, but a failure this wide is
informative regardless.

## 5. Falsifiers

What would make me buy (this is a pass, so these run in reverse):

1. **Shift —** Q3'26 print, 2026-10-28 — H2 revenue and adjusted gross
   margin. If revenue lands at or above the top of the implied H2 range and
   adjusted gross margin holds ≥44%, condition 4's refutation is wrong and
   this re-opens as a genuine double.
2. **Break — either way.** The 2028 notes. Any refinancing, exchange, or
   tender that pushes the maturity past 2030 at a coupon under ~8% removes
   the deciding row in §4. Equally: the notes trading below ~70 would confirm
   the credit market disagrees with the equity and would harden the pass.
3. **Break —** The covenant at 5.25x. A reported consolidated total leverage
   ratio above ~4.5x at any quarterly test, or any amendment/waiver request,
   ends it.
4. **Break —** NARCAN price realization. A second impairment of the NARCAN
   asset group, or disclosed share below 40%, confirms the decay is running
   ahead of the model.
5. **Shift —** Capital allocation. Continued *share* repurchase into the
   2028 wall (rather than note repurchase) would tell me management is not
   managing the maturity.

**Reopen trigger:** none stated (no machine-readable trigger recorded;
falsifier 1 names the 2026-10-28 Q3 print).

## 6. UNKNOWNs

1. **The 2028 notes' trading price and yield.** The single most
   decision-relevant number in this analysis and I could not get it — cbonds
   403'd, and no other free source carried a live quote. Would come from
   FINRA TRACE or a broker fixed-income screen. **Does its absence kill the
   thesis?** No — it would only strengthen or soften an already-negative
   call. But it caps condition 1 at UNKNOWN and it is why the verdict is not
   stronger than it is.
2. **The cash-flow model behind the $191.3M NARCAN impairment** (condition
   3). Not disclosed beyond "updated cash flow expectations." Would come from
   the 10-Q's fair-value footnote. Absence prevents judging whether the
   write-down is conservative or catching up.
3. **Insider Form 3/4 activity.** EDGAR was unreachable this session
   (WebFetch 403, curl denied). A secondary source reported director sales
   but did not survive verification. Recoverable on any normal run; would
   sharpen §3's capital-allocation thread but does not change the call.
4. **Maintenance capex and the commitments footnote.** TTM capex is $11.8M
   against D&A of $102.9M — a 8.7x gap at a company that runs fill-finish
   plants. Either the asset base is being harvested, or capex is about to
   rise. The 10-K commitments-and-contingencies footnote would settle it. My
   $15M capex assumption in §4 is therefore likely **too low**, which makes
   the base case optimistic, not conservative.
5. **Q3/Q4'26 revenue split between MCM timing and NARCAN erosion.**
   Management declined to quantify (Jessica Fye, JPMorgan, asked directly on
   long-term NARCAN price and volume and got *"relatively flat, somewhere
   around that area"* with no share-loss or price-decline figures).

## 7. Sources

- **Primary:** Q2 2026 earnings call, 2026-08-05 (guidance revision, $191.3M
  NARCAN impairment, restructuring, MCM contract modifications, management
  quotes). April 2026 refinancing 8-K (term loan size, OrbiMed/Jefferies,
  Term SOFR+6.25% with 3.00% floor, April 16 2031 maturity,
  springing-maturity test, 5.25:1.00 leverage covenant first tested
  2026-09-30, 1.75:1.00 secured test, ABL cut $100M→$50M) — read via
  stocktitan's filing summary, **not** the filing itself, because EDGAR was
  unreachable; treat the covenant figures as one remove from primary until
  re-verified. August 2020 offering release ($450M, 3.875%, due 2028).
- **stockanalysis.com (vetted exception):** `/statistics/` via the `probe`
  decoder; `/financials/`, `/financials/income-statement/` (annual and
  `?p=quarterly`), `/financials/cash-flow-statement/`,
  `/financials/balance-sheet/`, `/financials/ratios/`, `/transcripts/` index
  and the Q2 2026 detail — the last six via WebFetch against the rendered
  page rather than the `__data.json` route, because the sandbox denied the
  decoding script. Route-level discrepancies recorded in §3 (the
  statistics-route thread).
- **Broker/market microstructure:** Robinhood MCP — real-time market state,
  not researched disclosure; admissible here only where no integrated
  official source covers the field. Equity quote and official close; option
  chain, ATM instruments and quotes (marks, IV, delta, OI, spreads); daily
  bars for the realized-vol series. `get_earnings_results` for the
  estimate-vs-actual pattern in §3 (dead ends). `get_financials` not used —
  banned by the skill's provenance rule.
- **Reference data:** Damodaran NYU Stern home page, implied ERP 4.28% and
  T-bond rate 4.74%, both **as of 2026-08-01**.
- **Point-in-time repo DBs:** none used — the sandbox denied `sqlite3` this
  session (see the session-constraint note under the title).
- **Low-confidence:** colour, not load-bearing. Levi & Korsinsky
  investigation notice (plaintiff-firm press release). A secondary report of
  director share sales, which 403'd on fetch and is recorded as UNKNOWN
  rather than used. An Investing.com summary of the Q2 slide deck used only
  to cross-check the $234.3M revenue and $180.2M net loss figures, both of
  which reconcile to the quarterly statement.

## Kill-thesis record

Ledger line: kill-thesis **FLAWED** — conditions=5, refuted=1, unknown=2;
ownership call PASS at $4.47. What is flawed is the *ownership* case —
condition 4 was attacked and the evidence stands against it — which is why
the call is a pass.

**Closest attack:** the closest attack that did *not* land — MCM is genuinely
strong and genuinely contracted, and a 21.4%-of-float short interest at 10.15
days to cover is real squeeze fuel. If H2'26 proves to be timing after all,
this is a double. I could not refute that possibility — I could only show
management does not claim it.

Per-condition adjudication as the original run recorded it: condition 4
**REFUTED** on management's own attribution (§3, the H2'26 guide thread);
condition 1 *plausible only* and materially damaged, capped at UNKNOWN by the
missing 2028-note price (§6); condition 3 *UNKNOWN* (the cash-flow model
behind the impairment is not disclosed); no separate SURVIVED/REFUTED sweep
beyond this was recorded. Options-timing check: ran path 2; IV sits below
both realized windows, so no timing refutation is available and the pass call
does not require a move (§4). Standing/statistical checks: not recorded in
original run.

**Flip evidence:** not recorded as a separate block in the original run; §5
is explicitly framed as "what would make me buy" and runs in reverse.
