# MU — Micron Technology, Inc. (Nasdaq: MU) — 2026-09-28

Price $1,050.37 (live quote 2026-09-28 14:15 UTC, Robinhood; official close
2026-09-25 $1,082.28) · market cap $1,186.3B (live price × 1,129,393,151
shares, 10-Q cover) · next earnings 2026-09-30 AMC (FQ4 FY26; Robinhood
verified, stockanalysis agrees; earnings.db still carries the 06-24 event).

Entry path: user-directed (`/research-ticker MU`). Not a `candidates` row.
composite.db shows one bullish vote only (`reddit_trending` 2026-09-21);
`sa_fscore` 8 and `sa_fcf_yield` 2.1% are annotations. The print is in two
days; this run is written knowing that and does not pretend otherwise.

## 1. Verdict and thesis

**PASS at $1,050.37 (live, 2026-09-28).** kill-thesis: **FLAWED** —
conditions=4 (1 probable, 3 plausible), refuted=1, unknown=0, pending=2,
not_obtained=0.

**p(beat SPY, 63 td): 0.48** · kill-thesis: 0.42

**Disputed expectation:** at $1,050 the price implies roughly $120B of FY27
free cash flow held flat for five years and forever after (11.7%/yr implied,
−264bp against the measured-beta hurdle of 14.4%, +158bp against the
beta-clamped 10.2%). Every path in which FY27 is the peak prices at 5–8%.
The market is pricing a supercycle with no cycle. Revision up: the FY2026
10-K (due ~mid-Oct 2026) shows floor-priced SCA minimums near the current
run-rate, or FY27 capex is guided flat. Revision down: TrendForce's 1Q27
contract-price outlook turns flat-to-down, or a rival pulls a greenfield fab
forward.

Micron is, today, the best business it has ever been: FQ3 FY26 revenue
$41.5B at an 84.6% GAAP gross margin and an 80.4% operating margin, FQ4
guided to $50B at ~86%, 16 take-or-pay Strategic Customer Agreements (SCAs)
with $18B of cash deposits arriving. None of that is in dispute. What is in
dispute is whether cash flow at this level is a plateau or a peak, and the
price only works as a plateau. The SCA floors — the one new mechanism that
could make this cycle different — bound out at roughly $22B/yr of
floor-priced revenue against a $200B+ run-rate; the SCA ceilings cap ~40% of
revenue at CQ2-2026 prices; and all three merchant producers plus CXMT are
adding greenfield capacity for 2027–28, funded in SK hynix's case by a
$26.2B US listing in July. This is a good business at a price that requires
the memory cycle to have ended. I do not own that claim.

**Closest attack:** the one that landed — condition 3. The bull case needs
FY27 free cash flow (~$120B) to persist for five years; the reverse DCF
shows no decay path clears even the beta-clamped hurdle until ~$800. Against
persistence stand the SCA price ceilings (the upside half of the pricing
distribution is contractually removed for ~40% of revenue), the floor
arithmetic ($100B of RPO over ≤4.5 years), the disclosed 2027–28 capacity
pipeline at all three producers, Micron's own "supply improves gradually in
2028", and the base rate of every prior memory cycle (FY22 operating income
$9.7B became a $3.6B loss in FY23). The second-closest is not an attack on
the thesis but on the calendar: a 93.6% ATM IV into Wednesday's print prices
a 9.8% one-sigma move, and July showed a beat-and-raise pop fully retraced
within five weeks.

Load-bearing conditions of the bull case (4):

1. **The FQ4 FY26 print and the FQ1 FY27 guide land at or above
   consensus** ($51.2B / $31.59 non-GAAP EPS for FQ4; $57.3B / $35.45 for
   FQ1) — *plausible*; settled 2026-09-30 AMC. Evidence today: guidance is
   $50.0B ± $1.0B and $31.00 ± $1.00 (press release), so consensus sits
   2.5% above the midpoint; six consecutive beats of 10–42% (Robinhood);
   TrendForce's 4Q26 outlook (2026-09-24) has AI-server DRAM and NAND
   contract prices still rising.
2. **FY27 free cash flow reaches ~$120B** — *plausible*; first settled by
   the FQ1 FY27 print (2026-12-16) and the FY27 capex frame it carries.
   Derivation: consensus FY27 EPS $159.49 × 1.145B diluted ≈ $182B net
   income; D&A ~$12B; capex ≥ $42B (management: FY27 quarterly capex "above
   fiscal Q4 levels", FQ4 net capex ≈ $10.4B); receivables build ~$25B.
   $120B is the midpoint of a $100–135B range, not a point estimate.
3. **FCF holds at the FY27 level for at least five years — no cyclical
   decay** — *plausible* on the bull's own framing (the nearest dated
   disclosures are the FY2026 10-K's SCA RPO next-twelve-months table,
   ~mid-Oct 2026, and the rivals' CY2027 capex guides in Oct/Jan); the
   kill pass REFUTES it on today's evidence — see the record.
4. **Micron holds ~20–25% DRAM share and an HBM share near its DRAM share
   through the HBM4/HBM4E transition** — *probable*. HBM4 shipments passed
   $1B in FQ3 and are in high-volume production for the lead customer's
   platform (press release, call); management targets HBM share ≈ DRAM
   share by design (call); SK hynix reports 56.4% HBM revenue share in Q1
   2026 (its 424B4). Third-party colour that Micron's HBM4 pin speeds lag
   is low-confidence and unverifiable.

**Dominant shared risk factor:** AI-infrastructure capex pace (hyperscaler
memory demand and DRAM/NAND pricing) — shared by 0 of 24 held names · 0
unlabelled. Three holdings (INTU, MORN, G) carry the inverse exposure —
generative-AI substitution — so an AI-capex bust that hurts MU would tend to
relieve them, not compound.

## 2. Business

**Created:** Micron makes the DRAM, HBM, NAND and NOR that every computer
stores its working state in. The customer buys bits at a bandwidth, a power
envelope and a form factor; in 2026 the scarce thing is not the bit but the
delivered capacity at all, and the AI-system builder gets a second thing:
system performance, which management says (and the customers' own
architectures confirm) is bounded by memory bandwidth and capacity before it
is bounded by compute. Micron's specific edge is being first with
low-power DRAM in the data center (LPDRAM/SOCAMM2, sole-sourced for a
period at NVIDIA, per the CBO on 2026-08-27) and with HBM4 on the 1-beta
node; it also designs customer-specific parts embedded in multi-year
roadmaps rather than JEDEC commodity.

**Captured:** three mechanisms, and they are not the same business. (1)
Spot and short-contract commodity DRAM/NAND, priced quarterly — FQ3 DRAM
prices rose in the low-60s% QoQ, NAND mid-80s%, on bit growth of only low-
to mid-single digits: revenue growth in FY26 is almost entirely price. (2)
HBM and other premium data-center parts, priced per stack at a large per-bit
premium, allocated a year ahead, and consuming ~3× the wafers per bit
(the "trade ratio") — this is where volume share is set strategically, not
sold to the highest bidder. (3) Since FQ3, the SCAs: five-year (auto:
three-year) take-or-pay contracts with binding annual volumes, most with a
price band (ceiling ≈ CQ2-2026 market price, floor undisclosed but set for
a gross margin "well above" the prior ~62% peak), several fixed-price or
floating; $18B of unrestricted cash deposits and ~$4B of letters of credit
back them, returnable in the back half of the term. Revenue by unit in FQ3:
Cloud Memory $13.8B (33%), Core Data Center $11.5B, Mobile & Client $11.5B,
Automotive & Embedded $4.6B; data-center revenue >$25B (>$100B annualised),
data-center SSD >$5B.

**Protected:** a mechanism, but a bounded one. Three merchant producers make
leading-edge DRAM (Samsung, SK hynix, Micron); a new entrant needs a decade
of node development and tens of billions per fab, and CXMT is the only one
trying. Within the three, Micron's protection is node timing (1-gamma in
HVM, next node H2 CY27), HBM packaging yield, and now contract structure.
What it has never had is pricing power through a capacity wave: the
oligopoly has cut price to fill fabs in every cycle since 1995, and Micron's
own 10-K names CXMT and YMTC as state-backed oversupply risks. The SCAs are
the first attempt to contract that behaviour away, and their teeth are real
(binding volumes, deposits, "no contractual way to get out" per the CBO) but
the floor-priced commitment is small next to the run-rate (§3).

**Control:** one class, one vote per share (DEF 14A 2025-11-25); no
controlling holder. Largest: Vanguard 8.4%, BlackRock 7.6%, Capital World
6.3%. Insiders 0.2% (stocks.db). Board nine, eight independent; the CEO is
also Chairman. Stockholders approved a Delaware §102(b)(7) officer
exculpation amendment on 2026-01-15 (8-K 2026-01-21). Nothing forecloses an
unsolicited bid or an activist; the null answer applies.

**Operating leverage (Phase 0): positive, and extreme in both directions.**

| period | revenue | operating income | op margin |
|---|---|---|---|
| FY2021 | $27.7B | $6.8B | 24.5% |
| FY2022 | $30.8B | $9.7B | 31.6% |
| FY2023 | $15.5B | −$3.6B | −23.0% |
| FY2024 | $25.1B | $1.3B | 5.2% |
| FY2025 | $37.4B | $9.8B | 26.2% |
| TTM to May-26 | $90.3B | $59.3B | 65.7% |
| FQ3 FY26 alone | $41.5B | $33.3B | 80.4% |

FQ2→FQ3 incremental operating margin was 98% ($17.2B of operating income on
$17.6B of added revenue). FY22→FY23 the same lever ran the other way: revenue
halved and operating income swung by $13.3B. That symmetry is the whole
valuation question. (Sources: stockanalysis income statement, S&P Global;
press release for FQ3.)

## 3. Threads pulled

- **The floor arithmetic (the thread that decided the verdict).** The call
  disclosed that 14 of 16 SCAs carry ~$100B of remaining performance
  obligations at minimum volume × minimum price, over terms ending CY2030,
  and that agreements with fixed prices or ceilings will eventually cover
  ~40% of revenue. $100B over ≤4.5 remaining years is ~$22B/yr of
  floor-priced revenue. Forty percent of a $200B run-rate is ~$80B/yr. So
  either the floors sit at roughly a quarter to a third of CQ2 prices, or
  minimum volumes sit far below expected volumes, or both — management
  stressed RPO is "inherently conservative" and revenue will "well exceed"
  it. UBS asked exactly this on the call and did not get a number. The
  bound is enough: the floors protect against a bust, not against a
  normalisation, and the next-twelve-months RPO in the 10-Q ($1.8B on the
  $5B booked by May 28) confirms the feathering is slow. The 10-K will print
  the next-twelve-months figure for the $100B — that is the reopen input.
- **The ceiling arithmetic.** The largest SCAs cap existing products at the
  CQ2-2026 market price for the term (call; 10-Q). FQ3 and FQ4 already
  reflect CQ2 pricing. For the ~40% of revenue under bands, the price line
  cannot rise from here; volume can. New SCAs will carry ceilings at the
  market price when signed (CBO, 2026-08-10), so the cap ratchets only
  through new signings.
- **Rival capacity.** SK hynix priced a US ADS offering on 2026-07-09:
  17.79M ADS at $149, $26.2B net, "general corporate purposes, including
  capital expenditures", 2026 capex "considerably" above 2025's W27.5T;
  M15X (Cheongju) took wafers in Q1 2026, Yongin phase-1 cleanroom Q1
  2027, Indiana packaging H2 2028; HBM revenue share 56.4% in Q1 2026; its
  own risk factors say memory ASPs "are expected to continually decline"
  (424B4, primary). Samsung P5 Pyeongtaek targeted 2028 and a reported 50%
  HBM capacity increase in 2026 (TrendForce, low-confidence). Micron: ID1
  first wafers mid-CY2027, Hsinchu meaningful shipments mid-CY2027, second
  Idaho fab and first New York fab end-2028 (call; 2026-08-10 forum). CXMT
  and YMTC are named in Micron's Item 1A. Management's own framing:
  tightness "beyond calendar 2027", supply "improves gradually in 2028",
  "no line of sight" to supply meeting demand.
- **Demand-side cracks since the call.** 2026-09-28 pre-market: memory
  names down 2–6% on OpenAI pausing some training and tool-use inference
  work, and on the 30-year Treasury above 5.5% (TipRanks, Barron's,
  Benzinga — low-confidence colour, dated). Samsung and SK hynix fell 4–5%
  in Seoul the same session on foreign selling after the Chuseok break
  (Invezz). TrendForce's 4Q26 forecast, dated four days earlier, still has
  contract prices rising for AI-server DRAM/NAND with consumer segments
  narrowing. No primary evidence yet that demand has turned; the first
  wobble in sentiment is recorded as such.
- **Insider transactions since the call (Forms 4, primary).** CEO Mehrotra
  sold ~55,000 shares across 2026-07-24 and 08-21 at $943–990 under a
  10b5-1 plan adopted 2026-01-30; holdings 312,168 → 264,503 (−15%). CPO
  Arnzen sold ~40,000 on 2026-07-01 at $1,077–1,096 (121,458 → 85,737,
  −29%, 10b5-1 of 2025-12-19). CBO Sadana 15,000 on 08-18 at $934. CAO
  Allen 879 at $1,000. New director Björlin 25 shares. No open-market buys
  by any insider in the window. Plan-based, but no one added.
- **Deposits are not cash the owner keeps.** $18B of SCA deposits arrive
  mostly in FQ4 as financing inflows, are held unrestricted, and are
  returned in the back half of the agreements (CFO). They inflate gross cash
  and net cash without being equity. Net cash of $23.75B at May 28 is
  pre-deposit; anything the FQ4 balance sheet shows above that is a
  liability first.
- **Consensus above the guide.** FQ4 consensus $51.2B / $31.59 sits above
  the $50.0B / $31.00 midpoints (stockanalysis forecast; Robinhood $31.50).
  The pattern of the last six prints is a beat of 10–42% on non-GAAP EPS,
  widening as the cycle accelerated; Robinhood's "actual" is non-GAAP
  ($25.11 for FQ3) where sec_fundamentals carries GAAP $24.67, and they
  reconcile via SBC and a $325M debt-tender loss.
- **Compensation.** PRSUs (65% of CEO LTI) pay 50% on 3-year rTSR vs the
  SOX index (55th percentile for target, capped at target if absolute TSR
  is negative) and 25% each on HBM3E+ and data-center SSD market share or
  bit shipments; the annual plan reads on non-GAAP net income and operating
  margin (DEF 14A). Share-and-bit metrics reward volume — the behaviour
  that has ended every prior cycle. No conflict with the thesis; a
  consistency with the short case.
- **Capital return.** $10B authorisation, $7.19B used through FY25, $650M
  bought in the first nine months of FY26, repurchases "subject to
  restrictions applicable under our CHIPS Act direct funding agreements"
  (10-K Item 5; grants up to $6.4B). Dividend $0.15/qtr. Debt cut from
  $15.4B to $5.7B via tenders (loss $500M YTD). Cash is going to capex and
  debt, not to owners, and the SCA deposits will fund the FY27 capex step.
- **Options read (mandatory):** path 2 only (MU is outside the 24-symbol
  CBOE catalog; options.db has no MU row). Expiry 2026-10-02, 4 DTE,
  brackets the 09-30 AMC print. Table and liquidity gate in §4.
- **Dead ends:** no minority interest line (no NCI haircut); no going-
  concern or covenant language; `debt` on the statistics page ($6.38B)
  matches the 10-Q ($5.72B long-term + current) within rounding; purchase
  obligations for PP&E $2.93B at May 28 (up from $1.77B) plus $5.5B of
  multi-year take-or-pay at FY25 year-end — material only as confirmation
  that capex is rising, no hidden off-balance-sheet capacity commitment
  found; a stocks.db/probe cross-check of price and share count agreed;
  the earnings.db calendar is stale (last event 06-24) but the statistics
  page and Robinhood agree on 09-30; sec_fundamentals holds the FQ3 10-Q
  facts (revenue $41.456B, op income $33.318B, EPS $24.67) and they match
  the press release exactly.

## 4. Valuation

**Inputs.** Levered flows against market cap; net debt 0 by the pairing
rule (net cash $23.75B at May 28 is 2% of cap and is not netted, which
biases the implied returns slightly low; the incoming $18B of deposits is a
liability and is never netted).
- Market cap $1,186.3B = $1,050.37 live × 1,129,393,151 shares (10-Q
  cover). The statistics page's `marketcap` hover $1,181,627,584,234 was
  captured pre-market and implies ~$1,046; stocks.db's 2026-09-28 capture
  is $1,222.3B at Friday's $1,082.28.
- TTM levered `fcf` $26,172,000,000 (ncfo $51,432M + capex −$25,260M);
  SBC TTM $1,204M (1.3% of revenue) deducted → $24.97B. TTM net income
  $50,469M for `--base-earnings`.
- Consensus FY26 FCF $50.45B (stockanalysis forecast, 42 analysts) less
  SBC ~$1.3B → $49.15B; FY26 net income consensus $83.0B.
- FY27 derived FCF $120B (condition 2's derivation), net income $182B.
- Capex: FY26 net ~$27B (10-Q); FY27 quarterly "above FQ4 levels".
- No minority interest, no pension, no material litigation reserve found.

**Hurdle:** rf 5.18% (DGS10, 2026-09-24) + beta 2.22 × ERP 4.14% =
**14.37%** (Damodaran implied ERP as of 2026-09-01, solved against his
4.75% T-bond). Beta 2.22 sits far above the 0.8–1.2 band; it is not a
thin-float artefact (insiders 0.2%, float 99.7% of shares out) but the
measured price of memory cyclicality, so it is kept as the primary hurdle.
The clamped row (beta 1.2 → **10.15%**) is the sensitivity and the more
generous reading. Terminal growth 2.34% = the 10-year breakeven (T10YIE,
2026-09-25), under the 5.18% cap.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A: TTM levered, flat | $24.97B | 0% | 2.34% | **4%** | −1010bp (−588bp clamped) |
| B: consensus FY26, flat | $49.15B | 0% | 2.34% | **6%** | −822bp (−400bp clamped) |
| C: FY27 peak, cycle decay to $48.6B | $120B | −25/−25/−20/−10/0 | 2.34% | **6%** | −806bp (−384bp clamped) |
| D: FY27 peak, mild decay to $82.5B | $120B | −15/−15/−10/−5/0 | 2.34% | **8%** | −606bp (−184bp clamped) |
| E: FY27 held flat (supercycle, no cycle) | $120B | 0% | 2.34% | **12%** | −264bp (+158bp clamped) |
| F: FY27 then bust to $30B | $120B | −40/−40/−20/0/+5 | 2.34% | **5%** | −913bp (−491bp clamped) |

Precision follows the IV rule: ATM IV 93.6% > 50%, so whole percents;
the two-decimal CLI output (A 4.27%, B 6.15%, C 6.31%, D 8.31%, E 11.73%,
F 5.24%) is arithmetic, not knowledge.

Price sweep on the same paths: D clears the clamped hurdle at ~$800
(+13bp) and E clears the measured hurdle at ~$800 (+36bp); at $750 they
read +69bp and +120bp. C never clears either hurdle above $700.

- **Reinvestment / terminal ROE:** every run has FCF below earnings
  (reinvestment 34–51%), so no `growth without reinvestment` warning fired.
  Implied terminal ROE is 4.6–6.9% — *below* both hurdles in every
  scenario. That is intentional and is the honest read of a terminal memory
  business: excess returns fade, and a 2.34% terminal rate on a heavily
  reinvesting fab operator claims only repricing. A bull who needs excess
  returns to persist must defend it against the Item 1A risk below.
- **Market share:** no growth is compounded in E, so no "bigger than the
  market" test applies to it. Consensus FY27 revenue $248B against WSTS's
  memory forecast (>$800B in 2026, +32% in 2027 → ~$1.06T) and
  TrendForce's $1.28T is a ~20–23% share, consistent with Micron's
  historical DRAM share. The forecast is not bigger than the market; it is
  the market forecast that is 5–6× 2024's.
- **Terminal risk (10-K Item 1A):** the dominant structural risk is
  "increasing competition and DRAM and NAND oversupply due to significant
  investment ... including by the Chinese government and ... CXMT and
  YMTC", beside fixed-cost underutilisation when supply overshoots. A
  2.34% terminal rate survives it only because it claims no real growth;
  every scenario except E already assumes the risk partly materialises.
- **Cash tax:** TTM effective 14.6% vs 21% US statutory, from long-standing
  Singapore/Taiwan/Japan incentives (10-K). No NOL flattery; base not
  haircut.
- **Serial acquirer:** no (Hsinchu fab purchase is capex, in the numbers).
- **SBC:** $1.2B TTM, 1.3% of revenue, deducted. Diluted count 1,145M vs
  basic 1,128M: a 1.5% overhang, immaterial.
- **Distribution clamp:** scenarios A–D and F sit inside or below the
  5.3–9.9% band that holds 80% of US firms; only E reaches the top decile.
  On any assumption short of "no cycle", this is the pass side of the
  distribution.
- **Leverage gate:** not triggered (net cash; equity $100.7B; Altman Z
  9.4). No equity-as-option run.

**Options-implied move** (path 2 — Robinhood stopgap; expiry 2026-10-02, 4
DTE, bracketing the FQ4 print on 2026-09-30 AMC; $1,050 strike both legs,
nearest to spot $1,050.37). Marks: call 43.575, put 40.975. ATM IV =
mean(0.939742, 0.932738). Closes: 89 daily bars, 2026-05-20..09-25.

| metric | value |
|---|---|
| spot | 1,050.37 |
| expected absolute move (MEAN, not a ceiling) | 8.05% |
| 1-σ move | 9.80% |
| ATM IV | 93.62% |
| RV60 | 76.78% |
| RV20 | 50.18% |
| IV > RV60? | YES |
| IV > RV20? | YES |

- **Liquidity gate: PASSED** (call spread $0.25 on a $43.58 mark = 0.6%,
  OI 4,378, volume 960; put spread $0.25, OI 1,488, volume 1,028) — on the
  four uncalibrated constants, so a pass is unverified rather than
  confirmation.
- "Elevated" reads YES on both windows, but the expiry spans a scheduled
  print and the trailing windows contain the June print and July's −40%
  drawdown, so this is the market pricing a known event, not a finding.
- **Timing check applicability:** the bull case's dated claim (condition 1)
  needs a beat, not a move of a stated size, so no `--required-move` was
  passed and nothing is refuted or supported by this table. The July
  precedent — +15.7% on 06-25, fully retraced by 07-02 and −39% by 07-29 —
  is recorded as the reason p(beat SPY) over 63 td is not raised by an
  expected beat.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** price at or below ~$800 with the FY27 FCF frame intact: the
  mild-decay path D then clears the clamped hurdle and the flat path E
  clears the measured one. At ~$750 both carry a real margin.
- **Shift —** the FY2026 10-K's SCA disclosure (~mid-Oct 2026) shows
  next-twelve-months floor-priced RPO of $50B+ (floors near current
  pricing, or minimum volumes near expected), which would turn condition 3
  from refuted to pending.
- **Shift —** SK hynix or Samsung guide CY2027 capex flat or down, or delay
  Yongin/P5, in their October or January reports.
- **Break —** the FQ1 FY27 guide (2026-12-16) shows FCF conversion or capex
  materially better than the $120B frame (e.g., capex held near $40B with
  revenue ≥ $60B/qtr) — the frame, not the price, was wrong.

For an owner (sell):

- **Break —** TrendForce's 1Q27 contract-price outlook (expected ~Dec 2026)
  shows server DRAM flat-to-down QoQ, or FQ1 FY27 guided revenue below FQ4
  actual.
- **Break —** any SCA customer disclosed as renegotiating, deferring or
  litigating volumes; or a 10-Q that drops the "contractually enforceable"
  language.
- **Shift —** HBM4E qualification slips past CY2027 or a lead customer's
  HBM4 allocation to Micron is disclosed below ~15%.
- **Shift —** insider open-market buying, or a repurchase step-up after the
  CHIPS restriction period, would change the capital-return read without
  changing the cycle read.

**Reopen trigger:** 2026-12-16:
mu-fq1-fy27-print-fy27-capex-guide-and-10k-sca-floor-rpo-or-price-at-or-below-800

## 6. UNKNOWNs

1. **UNKNOWN** — the SCA floor prices and minimum volumes per customer.
   Private contract terms; no filing will print them. Bounded by the RPO
   arithmetic in §3 (~$22B/yr at the floors) — the bound is what refutes
   condition 3, so the absence sharpens rather than kills the analysis.
2. **PENDING 2026-10 (FY2026 10-K)** — next-twelve-months revenue on the
   ~$100B RPO, and the FQ4 deposit balance. Named by the CFO as coming in
   the 10-K. This is the reopen input.
3. **PENDING 2026-09-30 / 2026-12-16** — FY27 capex in dollars. Only a
   directional guide exists ("above FQ4 levels" per quarter). A $60B+
   figure takes FY27 FCF to the bottom of the $100–135B range.
4. **UNKNOWN** — Micron's HBM4 allocation at NVIDIA for Rubin. Management
   states >$1B shipped and share targeted ≈ DRAM share; third-party
   estimates (SK hynix 60–70%, Samsung 25–30%, Micron remainder) are
   low-confidence. Not load-bearing for the pass; load-bearing for the bull
   only if HBM margins diverge sharply from DDR5, which management
   declined to quantify.
5. **UNKNOWN** — identities of the four large SCA customers. Concentration
   is disclosed only in aggregate in the 10-K (customer >10% of revenue);
   the FY26 10-K will name the count, not the names.
6. Option value, unnumbered in §1: agentic and physical-AI demand outrunning
   every 2027–28 capacity add (*possible*); a fourth wave of SCAs with
   higher ceilings; HBM4E pricing. None is a condition.

## 7. Sources

**Primary:** Micron 8-K 2026-06-24 Ex. 99.1 (FQ3 FY26 press release,
guidance, business-unit table, balance sheet); 10-Q for the quarter ended
2026-05-28 (SCA/RPO note, deposits, purchase obligations, FY26 capex ~$27B,
debt tenders, share count); 10-K FY2025 filed 2025-10-03 (Item 1A oversupply
/ CXMT / YMTC, Item 5 CHIPS repurchase restriction, Note 13 commitments,
Note 20 incentives); DEF 14A 2025-11-25 (one vote per share, 5% holders,
PRSU design); 8-Ks 2026-01-21 (annual meeting, exculpation), 2026-03-25
(tender offers), 2026-06-09 and 2026-08-26 (board and officer changes);
Forms 4 filed 2026-07-01, 07-23, 07-28, 08-20, 08-25, 08-28; FQ3 FY26
earnings call 2026-06-24, Technology Leadership Forum 2026-08-10 and Six
Five Summit 2026-08-27 (transcripts via stockanalysis, primary-transcribed;
numbers corroborated against the press release and 10-Q). SK hynix Form
424B4 dated 2026-07-09 (rival capacity, HBM share, risk language).

**stockanalysis.com (vetted exception):** `/stocks/MU/statistics/`
(hover values), `/financials/income-statement/`,
`/financials/cash-flow-statement/`, `/financials/balance-sheet/` (annual
and quarterly), `/forecast/` (consensus FY26/FY27, price targets),
`/transcripts/` index, overview news feed (headlines only).

**Broker/market microstructure:** Robinhood MCP `get_equity_quotes` (live
price and official close), `get_earnings_results` (estimate-vs-actual
pattern and the 09-30 date — the estimate side is not covered by any
integrated official source), `get_option_chains` / `get_option_instruments`
/ `get_option_quotes` (path-2 chain), `get_equity_historicals` (89 closes).

**Reference data:** Damodaran implied ERP 4.14% (2026-09-01); 0.8–1.2 beta
band and the 5.26–9.88% cost-of-capital band (Data Update 5, 2026); ~29%
excess-return base rate; WSTS 2026 forecast (memory >$800B, 2027 +32%);
TrendForce 4Q26 price outlook (2026-09-24) and 2027 memory market $1.28T
(2026-05-29).

**Point-in-time repo DBs (read-only):** stocks.db (2026-09-28 capture:
$1,082.28, beta 2.22, insiders 0.215%, institutions 79.2%, SBC $1.204B,
sbcByRevenue 1.33%); sec_fundamentals.db (FQ3 facts match the release);
fred.db (DGS10 5.18% 2026-09-24; T10YIE 2.34% 2026-09-25); composite.db
(one `reddit_trending` vote, annotations only); earnings.db (stale 06-24
event; noted); portfolio.db (24 held symbols for the factor overlap);
options.db (no MU row → path 1 unavailable).

**Low-confidence:** TipRanks / Barron's / Benzinga / Invezz headlines on the
2026-09-28 sell-off and the OpenAI pause; TrendForce and ETNews-sourced
HBM4 share and capacity estimates; substack/blog claims about Micron's
Rubin allocation and pin speeds; the analyst's on-call reference to a
December 14 CHIPS restriction date (the 10-K confirms a restriction, not a
date).

## Kill-thesis record

Ledger: `2026-09-28 MU FLAWED conditions=4 refuted=1 unknown=0 pending=2
not_obtained=0 reopen=2026-12-16:mu-fq1-fy27-print-fy27-capex-guide-and-10k-sca-floor-rpo-or-price-at-or-below-800`

Per-condition adjudication (the bull case's list in §1):

1. **PENDING 2026-09-30** — FQ4 print / FQ1 guide at or above consensus.
   Attacked with the bar (consensus 2.5% above the guide midpoint), the
   09-28 demand headlines, and the SCA ceilings; against that, TrendForce's
   four-day-old 4Q26 price outlook and a six-print beat streak. Nothing
   today stands against it; nothing today proves it.
2. **PENDING 2026-12-16** — FY27 FCF ≈ $120B. Attacked on capex (SK hynix
   "considerably higher"; Micron pulling in cleanroom) and working capital:
   a $60B capex year and a $30B receivables build still leave ~$100B. The
   frame survives as a range; the point does not exist yet.
3. **REFUTED** — FCF holds at the FY27 level for five years. Evidence
   against, all primary or reference-tier: (a) ~40% of revenue is or will be
   capped at CQ2-2026 prices, removing the upside half of the price
   distribution for that slice while the downside is floored far lower;
   (b) $100B of RPO across 14 SCAs over ≤4.5 years ≈ $22B/yr at the floors,
   a quarter to a third of what 40% of the run-rate would be; (c) the
   disclosed 2027–28 capacity pipeline at all three producers plus CXMT,
   funded in SK hynix's case by $26.2B raised in July; (d) Micron's own
   "supply improves gradually in 2028" and SK hynix's own "ASPs expected to
   continually decline"; (e) base rate: FY22 $9.7B operating income to a
   $3.6B loss in FY23, FY18→FY19 before that, and Damodaran's ~29% of
   firms sustaining excess returns. Evidence for: management's "no line of
   sight" to supply meeting demand and WSTS/TrendForce forecasts — which
   end in 2027 and say nothing about 2028–31. The condition needs 2028–31.
   Refuted at the *probable* and *plausible* tiers; it survives only as
   *possible*, which is option value, not a condition.
4. **SURVIVED at probable** — share through HBM4/HBM4E. HBM4 >$1B shipped
   and in high-volume production for the lead platform (press release);
   NVIDIA's CEO confirmed all three suppliers qualified for Rubin (web,
   low-confidence but consistent with Micron's primary statement). The
   "distant third / pin-speed lag" colour is unverifiable and does not
   overturn a primary disclosure.

Standing checks:
- **Base rate:** peak-cycle memory margins have reversed within roughly two
  years in every cycle in Micron's own filings; ~29% of firms earn above
  their cost of capital in perpetuity. The story starts as a 3-in-10
  proposition and the sector's history makes it worse.
- **Short case:** 6.6× forward earnings is what a memory stock looks like
  at the top, not the bottom; the SCAs cap price on 40% of revenue and
  floor it at a level management will not disclose; every producer is
  building; insiders sold through July–August and nobody bought; the
  stock has gone nowhere since 06-24 ($1,048.51 → $1,050.37) while FY27
  EPS estimates roughly doubled — the multiple is already compressing;
  $18B of "cash" is customer money; the first demand headline (OpenAI)
  arrived two days before the print.
- **Management incentives:** PRSUs 50% rTSR vs SOX (3-yr), 25% HBM3E+
  share/bits, 25% data-center SSD share/bits; annual plan on non-GAAP net
  income and operating margin. Share-and-bit metrics reward capacity and
  volume; consistent with the cycle's usual ending, not against it.
- **Disconfirming search:** rival prospectus, rival capex, Korean market
  selling, the OpenAI pause, Forms 4, TrendForce's consumer-segment margin
  squeeze. Run and recorded.
- **Moat:** a mechanism (node timing, HBM packaging, three-player
  oligopoly, now contract structure) — but the oligopoly has never held
  price through a capacity wave and the contract structure's floor is
  small. Real, bounded, and not what the price needs.
- **Statistical checks:** N/A — no backtest or screen result is claimed.
  The composite flag is one `reddit_trending` vote and is not evidence.
- **Options timing check:** ran (path 2, 2026-10-02 expiry, 4 DTE, liquid
  on the uncalibrated gate). The bull's dated claim needs a beat, not a
  sized move, so no refutation was attempted; the 9.8% one-sigma move is
  recorded as context. Path 1 unavailable (no options.db history for MU).

**Closest attack:** condition 3's floor-and-ceiling arithmetic — it landed.
Next closest: the July precedent that a beat-and-raise pop fully retraces,
which bears on the 63-day probability, not the thesis.

**Flip evidence:** to SOUND — the FY2026 10-K's SCA table shows floor-priced
next-twelve-months revenue of $50B+ (floors near current prices), *and* the
price sits at or below ~$800, so that a mild-decay path clears the hurdle;
condition 3 then reads PENDING and the ownership call flips. Further toward
FLAWED-and-dead — a 1Q27 contract-price decline or an SCA renegotiation
disclosure, either of which converts the decay paths from scenario D toward
C or F.

**p(beat SPY, 63 td): 0.42** — written before re-reading §1's line. Two
prints fall inside the window and both will probably beat; the reason the
number sits below 0.5 is that the stock has already stopped rewarding
beats, and a 2.2-beta name into a rate-and-AI-sentiment wobble has more
ways to lag SPY over 63 days than to lead it.
