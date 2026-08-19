# BMI — Badger Meter — 2026-07-27

Price $127.99 · market cap $3,710.0M · next earnings ~October 2026

Entry path: not recorded (pre-template run).

## 1. Verdict and thesis

**PASS at $127.99.** kill-thesis: **UNPROVEN** — conditions=6, refuted=0,
unknown=3.

A genuinely high-quality water-metering franchise (net cash, 22% ROIC, 33
consecutive years of dividend growth, positive operating leverage through the
FY21–25 boom), but the price still assumes the boom resumes: reverse DCF pays
**4.05%/yr at zero growth, ~7.1% on management's own recovery path, and ~9.1%
only if the full 2021–25 growth rate returns** — while revenue has now
declined two consecutive quarters, management guides FY26 "flattish" with the
growth back-loaded into Q4's easy comp, and the evidence that would
distinguish a project air-pocket from AMI-penetration peak does not exist in
any disclosure.

Price context: −33.7% over 1y; crashed −24% on the Apr 17 Q1 print and −13.2%
on the Jul 22 Q2 print (Robinhood bars). Short interest is 13.3% of float —
someone is funding the peak-penetration case seriously.

**Closest attack:** not recorded as such in original run.

Load-bearing conditions: six counted; not individually enumerated in the
original run (0 refuted, 3 unknown). Condition tiers not recorded in
original run.

## 2. Business

**Created:** water utilities get measurement they bill on (meters), plus AMI
networks (ORION endpoints, cellular NaaS) and software (BEACON, EyeOnWater)
that turn manual meter-reading into remote telemetry — labor savings, leak
detection, non-revenue-water recovery. Beyond-the-meter (SmartCover sewer
monitoring, UDlive) extends the same buyer relationship across the water
cycle.

**Captured:** hardware sale (meter + endpoint) at 41% gross margin, with a
structural mix lift as mechanical→static meters and cellular AMI carry
higher margin; then hardware-enabled recurring software/NaaS on top. Utility
water is the product line; flow instrumentation (~GDP growth, some
data-center exposure) is the rest.

**Protected:** incumbency in a 15–20 year replacement-cycle install base; an
AMI network is a decade-plus infrastructure commitment (rip-and-replace
switching cost); consultant/spec relationships gate the RFP funnel.
Mechanism is real but not absolute — Itron, Xylem/Sensus, Neptune fight for
the same conversions, and BMI itself touts "competitive conversions" in both
directions (Q2-26 call).

**Operating leverage (Phase 0): positive** through the boom: FY21→FY25
revenue +81% ($505M→$917M), op income +133% ($79M→$183M). What broke in 2026
is in §3.

## 3. Threads pulled

- **What broke:** after the FY21–25 boom (§2), Q1-26 revenue −9.0% YoY (op
  income −28.7%), Q2-26 −6.6% (−12.2%); TTM revenue $881M now sits below
  FY25's $917M and TTM op margin 18.6% vs 20.0% (stockanalysis financials;
  SEC facts confirm Q2 rev $222.3M, op inc $39.4M). Management: "project
  pacing dynamics" between completed AMI cohorts and nine awarded projects
  now ramping (PRASA begun); Q1 also had a $15–20M short-cycle shortfall.
- **Guide credibility:** FY26 base revenue "flattish," sequential
  improvement each quarter, YoY growth "heavily weighted to Q4" — the
  easiest comp (Q4-25 revenue was the year's low). Explicitly declined to
  give project-level detail this quarter. Not falsifiable until Q4 prints —
  that asymmetry is exactly what the market sold on Jul 22.
- **PRASA (Puerto Rico):** procurement challenged in a June letter from PR's
  Resident Commissioner (call Q&A; letter itself not read —
  low-confidence). Management: "fair and open process, we won it"; 10-Q
  Note 5 reports **no material legal proceedings**. Protests are routine in
  government contracting, but the project's size to the FY26 ramp is
  undisclosed → thread ends in UNKNOWN.
- **Electronics costs:** management's own words — AI/data-center build-out
  driving component cost and availability pressure "not easing";
  pass-through escalators in "most" but "not maybe 100%" of contracts.
  Margin already −110bp YoY (17.7% GAAP; 18.4% base). At-risk, not refuted:
  cost actions held Q2 gross margin at 40.8% (−30bp).
- **Capital allocation:** ~$63M of buybacks in H1-26 (treasury stock
  $51.6M→$114.4M, 10-Q), $90M authorization left, dividend 33rd year,
  UDlive bolt-on (May 2026), SmartCover $184M (Jan 2025). Net cash $72M.
  Nothing misaligned.
- **Options read (mandatory):** path 2 stopgap — BMI not in the CBOE
  catalog. See §4's table.
- **Dead ends:**
  - Insider filings: two Form 4s Jul 2, none since the print (EDGAR
    submissions).
  - Flow instrumentation's +6% quarter — management itself says model
    GDP-like, data-center products are small.
  - `sec_fundamentals.db` holds only the latest frame for BMI so annual
    history came from stockanalysis instead.
  - `/stocks/BMI/financials/` overview route returned no financialData
    (sub-routes worked).

## 4. Valuation

Levered TTM FCF **$150.3M** (ncfo $166.7M + capex −$16.4M, statistics route
`fcf`) against **market cap $3,710.0M** (hover-exact), net debt zero (net
cash $72M — conservatively not credited). P/FCF 24.7×. No Damodaran hurdle
was computed in the original run.

| path | growth | terminal | implied return |
|---|---|---|---|
| zero growth | 0×5 | 0% | **4.05%/yr** |
| management ("flattish" FY26, then AMI ramp) | 0, then 6%×4 | 2.5% | **7.07%/yr** |
| full boom resumption | 12%×5 | 3.0% | **9.10%/yr** |
| bear (FCF resets to 3y avg $137M) | 2%×5 | 2% | 5.77%/yr |

Asset-light check: capex is 1.9% of sales and D&A ($32.9M) exceeds it; 10-Q
shows no material purchase obligations, but the 10-K commitments footnote
was not read (UNKNOWN) — the electronics-supply warning is exactly where a
future take-or-pay could hide. Terminal risk: post-AMI-saturation growth
rests on the 15–20y replacement cycle plus an undisclosed software mix —
2.5–3% terminal survives replacement economics but the software split is
unverifiable.

**Options-implied move (path 2 stopgap — BMI not in the CBOE catalog;
Aug-21 expiry, 25 DTE, no earnings inside the window; next print ~Oct):**

| metric | value |
|---|---|
| spot | 127.99 |
| ATM strike | 130 |
| call mark | 4.95 |
| put mark | 5.90 |
| ATM IV | 40.36% |
| expected absolute move (MEAN, not a ceiling) | 8.48% |
| 1-sigma move | 10.56% |
| RV60 | 47.31% |
| RV20 | 64.58% |
| IV > RV60? | NO |
| IV > RV20? | NO |

Both windows are contaminated by the two earnings crashes, and their
disagreement is the finding. **Liquidity gate FAILED** (volume 0 both legs,
OI 43/40, spreads 44–75% of mark) → UNRELIABLE; moves no verdict. Thesis
makes no dated claim → timing refutation NOT APPLICABLE.

## 5. Falsifiers

For the pass (what flips it):

- Two consecutive quarters of **organic YoY growth** with base op margin
  held ≥18.5% — evidence the cohort ramp outruns completed-project rolloff —
  would move the credible path toward the ~9% row at today's price.
- A price where the arithmetic stops needing the boom: near **~$95–100**
  management's own path clears ~8.5–9% without any new evidence.
- Conversely (for the shorts): a PRASA cancellation or a Q4 miss against the
  year's easiest comp would confirm the saturation read.

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **Pacing vs peak** — no disclosure (order book beyond the anonymized
   cohort, industry AMI penetration) can distinguish an air-pocket from the
   top of the adoption S-curve. This is the pass itself; absence is decisive
   at this price.
2. **PRASA's size** to the FY26–27 ramp — management explicitly declines
   project-level detail. Would come from PRASA's own procurement record
   (low-confidence news tier).
3. **Software/recurring revenue split** — "higher software" is qualitative
   only; the terminal-growth input leans on it. Would come from a future
   segment disclosure.
4. (Minor) 10-K commitments footnote unread; Q1-25's 22.2% op-margin outlier
   unexplained.

## 7. Sources

- **Primary:** SEC EDGAR — Q2-26 10-Q (filed 2026-07-23; balance sheet,
  treasury stock, Note 5 contingencies, UDlive/SmartCover terms), 8-K
  2026-07-22, submissions index (Form 4 dates); XBRL facts via
  data/sec_fundamentals.db (Q2 frame).
- **stockanalysis.com (vetted exception):** statistics route (market cap,
  FCF, net cash, short interest, RSI, dates), income-statement route
  annual/quarterly series, transcripts route Q2-2026 call
  (primary-transcribed; all management quotes above).
- **Broker/market microstructure:** Robinhood MCP — equity quote/close,
  daily bars (crash magnitudes, closes array), option
  chain/instruments/quotes (straddle, IV, OI). Admissible: no integrated
  official source carries live quotes/chains for BMI.
- **Reference data:** none used.
- **Point-in-time repo DBs:** `data/sec_fundamentals.db` (Q2 XBRL frame;
  holds only the latest frame for BMI — see §3's dead ends).
- **Low-confidence:** the PRASA Resident-Commissioner letter (known only via
  call Q&A; not independently read).

## Kill-thesis record

**Kill-thesis verdict: UNPROVEN** — 6 load-bearing conditions, 0 refuted,
3 UNKNOWN.

Per-condition adjudication: not recorded in original run (the six conditions
were not individually enumerated).

Standing/statistical/options-timing checks: not recorded in original run,
beyond §4's note that the thesis makes no dated claim (timing refutation NOT
APPLICABLE) and the failed liquidity gate.

**Closest attack:** not recorded as such in original run.

**Flip evidence:** not recorded as a labelled pair in the original run; §5
carries the directional evidence.
