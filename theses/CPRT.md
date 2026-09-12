# CPRT — Copart, Inc. — 2026-09-06 (reopen of 2026-07-26, trigger: q4-print-insurance-volumes)

Price $33.72 (regular-session last trade, 2026-09-04) · market cap
$31,218,363,173 · next earnings 2026-09-10 AMC

**Reopen run.** Prior file: `research/CPRT-2026-07-26.md`. Prior verdict:
FLAWED (conditions=6, refuted=2, unknown=4), ownership call PASS at ~$27.94.
Reopen question: did the Q4 FY2026 print (expected 2026-09-03 AMC) show US
insurance-unit volumes stabilizing with hard numbers, and does that change
the pass?

## 0. The reopen question, answered first

**The trigger did not fire because the event has not happened.** Copart
moved its Q4 FY2026 release to Thursday 2026-09-10 after 4:00 p.m. ET, with
the call at 5:30 p.m. ET (Copart release, 2026-09-01, via BusinessWire;
`data/earnings.db` still carried only the 2025-09-04 and 2026-05-21 events,
and Robinhood `get_earnings_results` shows Q4 FY26 as 2026-09-10 pm,
verified, `actual: null`). The reopen was dated off last year's slot; the
print slipped a week. The latest hard number is therefore still Q3 FY2026
(Feb–Apr 2026): US insurance units −4.2% (≈−3% ex-CAT), improving from −9.5%
(−7.3% ex-CAT) in Q1 and −10.7% (−4.8% ex-CAT) in Q2 — a narrowing decline,
not a stabilization, and not the number the trigger asked for.

What *did* change in six weeks is the price and the competitor's evidence.
The stock is up 20.7% ($27.94 → $33.72) on a President appointment (Jane
Pocock, 2026-08-01), a Bloomberg report that Copart is bidding for CCC
Intelligent Solutions (2026-08-18, unconfirmed by any 8-K), and a JPMorgan
upgrade to $40 (2026-09-03). Meanwhile RB Global's Q2 2026 8-K (primary,
2026-08-06) reports automotive units +11% YoY with "net market share gains"
— the first common-basis datapoint the prior run said it lacked. Both moves
push the same way: the pass gets **stronger**, not weaker. Every reverse-DCF
scenario now lands 1–4 points below the cost of equity, versus the prior
run's 2–3 points, and the share-loss question the prior run marked UNKNOWN
now has a primary-source answer from the other side of the table.

| prior falsifier | actual | status |
|---|---|---|
| Price falls so Scenario A clears ~10% (low-$20s) | Price rose 20.7% to $33.72; Scenario A now implies ~7% | NOT TRIGGERED |
| Q4 FY26 print (2026-09-03 AMC) shows insurance units stabilizing with hard numbers | Print moved to 2026-09-10 AMC; not reported. Latest: Q3 US insurance units −4.2% (≈−3% ex-CAT) | NOT TRIGGERED (event pending) |
| Another quarter of YoY revenue decline | No new quarter reported since Q3 (+2.1% YoY) | NOT TRIGGERED |
| Capex reaccelerating toward 12–13% of revenue without matching growth | No new capex print (Q3 capex $80.9M = 6.5% of revenue); but a reported ~$5.7B-EV bid for CCC is "total investment rising" by another route | GRAZED |
| Further named account losses to RB Global/IAA | No named account; RB Global's own 8-K: automotive units +11%, "net market share gains" | HALF-TRIGGERED |

## 1. Verdict and thesis

**PASS at $33.72 (regular-session last trade, 2026-09-04).** kill-thesis:
**SOUND (on this pass)** — conditions=5 (4 probable, 1 plausible),
refuted=0, unknown=0.

Copart is a very good business — ~30% ROIC, $4.1B net cash, an entrenched
two-player salvage-auction structure — whose US insurance volumes have now
shrunk for four consecutive quarters while its only real competitor reports
double-digit unit growth and claims share gains. At $33.72 the market
capitalization of $31.2B implies an annual equity return of roughly 5–8%
under every free-cash-flow assumption tested, from a bear case with capex
normalized to a bull case with 6% growth and 2.5% terminal growth — all
below the 9.0% cost of equity, and all below the US median cost of capital.
The price needs ~14% FCF growth for five years to clear the hurdle; the
company's insurance units are negative, consensus three-year revenue growth
is 3.8%, and the reported CCC bid would spend the cash pile on a business
whose $308M FCF cannot close the gap. The 9/10 print cannot fix the
arithmetic — a stabilization would confirm the bull scenario, which fails
on its own.

**Closest attack:** the growth ceiling. Copart compounded revenue at 14.6%/yr
over FY2021–FY2025; if it returned to that rate for five years the price
would clear the hurdle. That period was inflation-driven ASP growth plus
CAT volume on a rising total-loss-frequency tailwind, and units are now
negative — but a 14% path is inside the company's own recent history, not
outside it.

Load-bearing conditions for the pass:

1. *probable* — **The base FCF is not materially understated.** TTM FCF
   $1,339M already uses the lowest capex in six years ($346M, 7.5% of
   revenue vs a 12–13% five-year norm); SBC is only $38M; interest income
   on the cash pile ($192M) is inside NCFO and is handled by scenario E.
   Every plausible correction lowers the base, none raises it.
2. *probable* — **Five-year FCF growth stays well below ~14%.** At 12% for
   five years the price still implies 8.7% vs a 9.0% hurdle. US insurance
   units −4.2% (Q3), global units −2.4%, consensus 3-year revenue growth
   3.76% (stockanalysis `analystForecasts`), ASP growth ~4% — the run-rate
   is single-digit.
3. *probable* — **The ~9% hurdle is the right bar.** rf 4.75% + beta 1.03
   (inside the 0.8–1.2 band) × ERP 4.14% = 9.01%; the company's own WACC
   estimate is 9.88%. Even the US median cost of capital (7.79%) is above
   the bull scenario.
4. *probable* — **The US insurance volume decline is at least partly share
   loss, so any recovery is partial.** Copart's CEO conceded an account was
   lost (2026-07-06 call); RB Global's Q2 2026 8-K reports automotive units
   +11% "supported by net market share gains." Copart's own ex-CAT trend is
   narrowing (−7.3% → −4.8% → −3%), which is consistent with cyclical
   coverage retrenchment *plus* a lost account, not either alone.
5. *plausible* — **A CCC acquisition, if it happens, cannot bridge the
   gap.** CCC's TTM FCF is $308M on a $5.69B EV; pro forma (Copart FCF +
   CCC FCF − after-tax interest on ~$2.5B new debt − forgone interest on
   the cash) is ~$1.38B against the same $31.2B cap → ~7%. To clear 9% the
   combined FCF would need ~$2.0B. Terms are undisclosed; any price paid
   only makes this worse, so the unknown price is not load-bearing.

**Dominant shared risk factor:** US auto-insurance claims volume — carrier
coverage retrenchment (liability-only / high-deductible shift) and falling
accident frequency (ADAS) — shared by 0 of 19 held names (labelled: CAH,
GMED, INTU, KTB, MORN, PYPL, ZTO — none match) · 12 unlabelled (BR CI EEFT
G HIG LOPE ORI PAGS PRI SAP WRB YOU). HIG, WRB and ORI are P&C underwriters
with no factor line; on this variable they sit on the opposite sign (fewer
claims helps an underwriter), so a labelled version would not fail
together with Copart.

## 2. Business

Unchanged from `research/CPRT-2026-07-26.md` §2 — the FY2025 10-K is still
the current annual filing (FY2026 10-K expected late September). Deltas:

**Created / Captured:** unchanged. One new datapoint on the buyer-side
flywheel from the Q3 call: international buyers take more than one-third
of US-sold volume, and of 30,000+ buyers who entered via non-insurance
vehicles over three years, "a strong majority" bid on an insurance vehicle
within 90 days (Liaw, 2026-05-21 call).

**Protected:** unchanged — industry-level barriers (land/zoning, seller
integration), not Copart-specific. The new evidence cuts *against* Copart's
relative position: RB Global's Q2 2026 8-K claims "net market share gains"
while Copart's US insurance units fell 4.2% in the overlapping period. The
prior run's load-bearing gap ("why Copart beats IAA") now has a primary
source on the other side.

**Control:** one class of common stock, one vote per share (10-K cover:
"Common Stock, par value $0.0001 per share"); no controlling holder.
Insiders hold 8.60% (stockanalysis `shares` block). Founder-family
influence runs through the seats — Willis Johnson (Chairman, founder) and
Jay Adair (CEO since 2026-07-31, son-in-law) — not through a share class.
Nothing forecloses an activist or an unsolicited bid by structure. Two
governance changes since the prior run: Jane Pocock appointed President
(2026-08-01; 8-K/A 2026-08-19: $804K salary, $643K target bonus, $800K RSUs,
500,000 options of which 279,000 carry a 125%-of-strike price hurdle), and
David J. Berger — a Wilson Sonsini M&A / governance / activism-defense
partner, whose firm is Copart's outside counsel — added to the board
(2026-08-13; 8-K 2026-08-18). A CEO whose new President is paid on a +25%
stock hurdle, a board that just added an M&A lawyer, and a reported bid
for a $5.7B-EV software company are three consistent signals.

**Operating leverage (Phase 0): negative.** FY2021→FY2025: revenue
$2,693M → $4,647M (+72.6%); operating income $1,136M → $1,753M (+54.2%).
Operating margin 42.2% → 37.7%; TTM (to 2026-04-30) revenue $4,639M,
operating income $1,752M — flat against FY2025 on both lines. Quarterly:
Q3 FY26 revenue $1,237M (+2.1% YoY), operating income $464M (+2.8% YoY).
Source: stockanalysis `/financials/income-statement/` annual and quarterly.

## 3. Threads pulled

- **Did the print happen? (the reopen question.)** No. Copart's own
  2026-09-01 release sets Q4 FY2026 for 2026-09-10 after the close; the
  prior run's 2026-09-03 date was inferred from last year's slot
  (2025-09-04). Consensus into the print: EPS $0.38 (Robinhood estimate;
  the stockanalysis-sourced Yahoo piece also carries $0.38 and $1.14B
  revenue, i.e. +1.3% YoY on Q4 FY25's $1,125M). Not a dead end — it is
  the new reopen.
- **Is the share-loss question still UNKNOWN? (prior UNKNOWN #1.)** No
  longer. RB Global's Q2 2026 8-K (Ex. 99.1, filed 2026-08-06): automotive
  GTV $2,448.7M (+13%), unit volume 658.8K lots vs 595.9K (+11%),
  "supported by net market share gains and higher average price per
  vehicle sold." Copart's US insurance units for the overlapping quarter:
  −4.2%. The windows are offset by a month and RBA's automotive line
  includes non-insurance lots, so this is not a clean unit-for-unit
  comparison — but a primary filing from the competitor asserting share
  gains, next to Copart's CEO conceding a lost account, is enough to move
  the condition from UNKNOWN to *probable*. The Copart-side series
  (transcripts): Q4 FY25 −2.1%, Q1 FY26 −9.5% (−7.3% ex-CAT), Q2 −10.7%
  (−4.8% ex-CAT), Q3 −4.2% (≈−3% ex-CAT).
- **The CCC bid.** Bloomberg (2026-08-18, via MT Newswires "Market Chatter"
  — rumor tier) reports Copart in talks to acquire CCC Intelligent
  Solutions against GTCR and Veritas. No 8-K from either company; CCC's
  Robinhood news feed carries nothing but the same report. Sized from
  stockanalysis `/stocks/CCC/statistics/`: market cap $4.42B, EV $5.69B,
  debt $1.38B, TTM revenue $1,112M, EBITDA $318M, FCF $308M. Copart's
  $4.2B cash would not cover it; a deal means debt for the first time
  since FY2021. Strategically coherent — CCC is the estimating platform
  that sits upstream of the total-loss decision Copart says it "helps
  drive" — but scenario G (§4) shows it does not change the ownership
  call. Live, unresolved; folded into the reopen trigger.
- **Insider and governance filings since the prior run.** Liaw (outgoing
  CEO) sold 27,745 shares on 2026-07-28 at ~$30.49 (Form 4, 2026-07-30;
  99,641 shares remain) — small, post-departure, not a signal. Forms 3 for
  Pocock (President, 2026-08-01) and Berger (director, 2026-08-13); Forms 4
  on 2026-08-18 record the Pocock grant and a Stearns (CFO) grant, both
  code A (awards, not purchases). No open-market insider buying into the
  20% rally.
- **Sell-side dispersion.** Barclays cut to $25 (Sell, 2026-08-26) while
  JPMorgan upgraded to Overweight $40 (2026-09-03); the two most recent
  actions bracket the price by ±25%. Low-confidence colour; not relied on.
- **Options read (mandatory):** path 2 only (CPRT is outside the 24-symbol
  CBOE catalog, so `v_iv_rank` does not apply). Expiry 2026-09-18, 12 DTE,
  brackets the 2026-09-10 AMC print. Table in §4. Liquidity gate FAILED
  (spread 34% of mark) → UNRELIABLE; no thesis-required move exists to
  test.
- **Dead ends:** `data/sec_fundamentals.db` now carries a CPRT row (added
  2026-08-21) but only the latest quarter — net income $402.4M and diluted
  EPS $0.43 match stockanalysis Q3 FY26 and the Robinhood actual exactly;
  revenue is NULL, so the annual cross-check still runs on stockanalysis.
  `data/composite.db` has no CPRT row (no flag, no signal history).
  `data/earnings.db` had not picked up the 2026-09-10 date. EDGAR 8-K
  index pages returned site navigation to a plain `curl`; the `index.json`
  route worked. Nothing in the 8-K/8-K/A texts beyond the appointments
  and compensation above — no CCC mention.

## 4. Valuation

Inputs, live 2026-09-06 from `/stocks/CPRT/statistics/` (`hover`): market
cap $31,218,363,173; enterprise value $27,111,767,173; total cash
$4,199,712,000; debt $93,116,000 (net cash $4,106,596,000); TTM NCFO
$1,685,427,000; capex −$346,194,000; TTM `fcf` $1,339,233,000; TTM net
income $1,553,201,000; SBC $38,112,000; interest income $192,144,000; cash
tax rate 18.85%; beta 1.029. Pairing: levered TTM FCF $1.339B against
market cap $31.22B; net debt 0 by the pairing rule. No minority interest;
no pension or litigation haircut identified (the DOJ AML inquiry is not
quantifiable — §6).

Hurdle: rf 4.75% + beta 1.03 × ERP 4.14% = **9.01%** (Damodaran implied ERP
as of 2026-09-01, trailing-12-month with adjusted payout; 10Y T-bond 4.75%).
Beta inside the 0.8–1.2 band, no clamp. Company's own WACC estimate 9.88%
(stockanalysis) sits above it.

Precision: path-2 ATM IV is 51.4%, above the 50% line, so implied returns
are quoted to the nearest whole percent and the range is wide.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A — reported TTM as-is | $1.339B | 3% | 2.0% | ~7% | ≈ −2.4 pts |
| B — capex normalized to 5y avg $479M | $1.206B | 3% | 2.0% | ~6% | ≈ −2.9 pts |
| C — B minus SBC, flat growth | $1.168B | 1% | 1.5% | ~5% | ≈ −3.8 pts |
| D — bull: insurance reaccelerates | $1.339B | 6% | 2.5% | ~8% | ≈ −1.4 pts |
| E — cap net of cash ($27.11B) vs FCF ex after-tax interest | $1.183B | 3% | 2.0% | ~7% | ≈ −2.4 pts |
| G — CCC pro forma (cap unchanged, FCF +CCC −interest) | $1.381B | 3% | 2.0% | ~7% | ≈ −2.3 pts |
| A at 12% growth | $1.339B | 12% | 2.0% | ~9% | ≈ −0.4 pts |
| A at $20.5B cap ($22.14/sh) | $1.339B | 3% | 2.0% | ~9% | ≈ 0 |

Exact solver outputs: A 6.58%, B 6.12%, C 5.21%, D 7.63%, E 6.65%, G 6.72%,
A@12% 8.66%, A@$20.5B 8.96%. Scenario A clears the hurdle only at roughly
$22/share at unchanged fundamentals — the prior run's "low-$20s" flip
level, restated against a proper hurdle. Every scenario except the 12%
path sits below the US median cost of capital (7.79%); B and C sit at or
below the 10th-percentile bound (5.26%), a strong pass by the distribution
clamp regardless of story.

- **Reinvestment / terminal ROE:** with `--base-earnings` $1,553M the
  terminal reinvestment rate is 13.8% (scenario A) and implied terminal
  ROE 14.5% — within ~5 points of the hurdle, defensible; no
  growth-without-reinvestment warning fired. Scenario C's 6.1% terminal ROE
  is below the hurdle, i.e. the bear case assumes value destruction at the
  margin — intentional, as the bear case.
- **Market-share sentence:** the 12% path puts FY2031 revenue at ~$7.8B
  against a US salvage + adjacent whole-car pool management sizes at "15
  million+" auction-mediated non-insurance units plus ~4M insurance units;
  at ~$1,100 revenue per unit that is ~7M units, roughly a third of the
  combined pool from ~4M today — not bigger than the market, but it needs
  the whole-car push to work at scale while the core shrinks.
- **Terminal growth vs Item 1A:** the disclosed terminal risk is unchanged
  from the prior run — accident-frequency decline from ADAS/autonomy and
  total-loss-frequency reversal (FY2025 10-K Risk Factors). 2.0% terminal
  in A/B/E/G is at inflation, not real growth; scenario C's 1.5% is the
  honest floor. Scenario D's 2.5% is the bull case and still fails.
- **Cash tax vs marginal:** 18.85% cash rate vs ~21% federal + state —
  not NOL-flattered; no haircut.
- **Serial-acquirer check:** FY2021–25 FCF excludes Purple Wave and land
  M&A; the CCC pro forma (G) charges the deal explicitly. Growth in A–E is
  organic-only.
- **Asset-light check:** unchanged — 10-K Note 15 discloses no multi-year
  land or capacity commitment; TTM capex is the lowest in six years and
  scenario B reverts it.

**Options-implied move** (path 2, Robinhood; expiry 2026-09-18, 12 DTE,
brackets the 2026-09-10 AMC print which reprices at the 9/11 open). ATM
strike 32.5 (nearest to spot 33.72; the 35 strike is 6 cents further, so
the 35 straddle is footnoted). Call mark $0.725, put mark $0.725, IV mean
of 50.25% and 52.55%:

| metric | value |
|---|---|
| spot | 33.72 |
| expected absolute move | 4.30% |
| 1-σ move | 9.32% |
| ATM IV | 51.40% |
| RV60 | 41.76% |
| RV20 | 42.28% |
| IV > RV60? | YES |
| IV > RV20? | YES |

The 35 straddle (call $0.225, put $2.10, IV 54.12%) prints expected move
6.90%, 1-σ 9.81% — same reading. Liquidity gate: **FAILED → UNRELIABLE**
(bid/ask $0.60/$0.85 on a $0.725 mark, spread 34% > 10%; OI 5,069 / 2,856
and volume 199 / 188 pass the floor). Both windows read YES so the
stopgap label "elevated" applies — but the forward window spans a
scheduled print while the trailing windows contain the CEO-transition
shock and the August rally, so this is the market pricing a known
calendar item, not a finding. Timing check: NOT APPLICABLE — the pass
thesis requires no move; the one-way valve has nothing to cut.

Equity-as-option: omitted — net cash, normal leverage.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** price at or below ~$22 at unchanged fundamentals (scenario A
  clears the 9.0% hurdle at a $20.5B cap).
- **Shift —** the 2026-09-10 print shows US insurance units ex-CAT flat or
  positive *and* Q4 capex holds below 10% of revenue *and* management
  gives FY2027 unit guidance that implies double-digit fee-revenue growth
  — the combination that would make a 12–14% FCF path arguable. Any one
  alone does not move the arithmetic.
- **Shift —** a CCC deal announced at terms where combined FCF/share
  exceeds ~$2.15 (≈$2.0B on 926M shares) — implausible on CCC's $308M FCF,
  stated so it is checkable.

For an owner (sell):

- **Break —** a second named insurance account loss, or RB Global's Q3
  2026 8-K again claiming net share gains while Copart's US insurance
  units stay negative.
- **Break —** a CCC acquisition financed with >$3B of debt at a price
  above ~$6B EV — the balance sheet that made this a pass rather than a
  short is gone and the cash pile is converted into a software integration.
- **Shift —** capex back above 10% of revenue without unit growth.
- **Shift —** another quarter of YoY revenue decline.

**Reopen trigger:** 2026-09-11:
cprt-q4-print-us-insurance-units-ex-cat-flat-or-better-with-capex-below-10pct-of-revenue-or-ccc-deal-announced-or-price-at-or-below-22

## 6. UNKNOWNs

1. **Q4 FY2026 US insurance unit volume** — the reopen question itself.
   Comes from the 2026-09-10 release and call (Copart discloses global and
   US insurance units, reported and ex-CAT, on every call). Its absence
   does not kill the pass: scenario D already assumes reacceleration and
   fails.
2. **CCC deal existence, price and financing** — comes only from an 8-K
   (Item 1.01) by either company. Absence does not kill the pass (scenario
   G); a deal would change the balance-sheet leg of the *owner's* case.
3. **A true unit-for-unit share series vs IAA** — RB Global reports
   automotive lots including non-insurance; Copart reports US insurance
   units. Neither discloses the other's basis. The direction is now
   evidenced from both sides; the magnitude is not. Not fatal.
4. **FY2026 full-year capex and the FY2027 capex plan** — 10-K (late
   September) and the Q4 call. Scenario B reverts to the five-year average
   in its absence.
5. **DOJ anti-money-laundering inquiry** (10-K Note 15, since October
   2023) — carried from the prior run; unquantifiable; not load-bearing.
6. **Why the stock rose 20.7%** — the three dated events (President
   appointment, CCC report, JPM upgrade) coincide with the 8/14, 8/19 and
   9/3 sessions (+7.6%, +7.4%, +4.4%), but attribution is inference, not
   disclosure. Not load-bearing; the valuation is against the price,
   whatever caused it.

## 7. Sources

- **Primary:** SEC EDGAR, CIK 0000900075 — 8-K accession
  0001193125-26-354640 (Berger appointment, Ex. 99.1 press release
  2026-08-17); 8-K/A 0001193125-26-356968 (Pocock compensation,
  2026-08-19); Forms 3/4 accessions 0001193125-26-354464/354467/354472/
  355690/355725 (2026-08-17/18) and 0001193125-26-326503 (Liaw sale,
  2026-07-30); submissions index `data.sec.gov/submissions/CIK0000900075`.
  FY2025 10-K (accession 0001628280-25-042946) as cited in the prior run —
  Risk Factors, Note 15, cover page. RB Global 8-K Ex. 99.1, CIK
  0001046102, accession 0001628280-26-052570 (Q2 2026 results). Copart
  release "Copart, Inc. to Release Fourth Quarter Fiscal 2026 Results"
  (2026-09-01, BusinessWire). Transcripts via stockanalysis
  (primary-transcribed, Quartr): 2026-07-06 Investor Update, 2026-05-21 Q3
  FY26, 2026-02-19 Q2 FY26, 2025-11-20 Q1 FY26, 2025-09-04 Q4 FY25.
- **stockanalysis.com (vetted exception):** live 2026-09-06 —
  `/stocks/CPRT/statistics/`, `/stocks/CPRT/`,
  `/financials/income-statement/` (annual, quarterly),
  `/financials/cash-flow-statement/` (annual, quarterly),
  `/financials/balance-sheet/`, `/transcripts/` index and five full
  transcripts, `/ratings/`; `/stocks/CCC/statistics/` and `/stocks/CCC/`.
- **Broker/market microstructure:** Robinhood MCP — `get_equity_quotes`
  (CPRT, CCC, RBA), `get_earnings_results` (CPRT; actuals cross-checked
  against `sec_fundamentals` Q3 EPS $0.43 — agree), `get_equity_news`
  (CPRT, CCC), `get_equity_historicals` (92 daily closes from 2026-04-27),
  `get_option_chains`, `get_option_instruments`, `get_option_quotes`
  (2026-09-18 32.5/35 calls and puts). Admissible: no integrated official
  source covers live quotes, option chains, the estimate series, or a
  dated news feed for this ticker. `get_financials` not used.
- **Reference data:** Damodaran implied ERP 4.14% and 10Y T-bond 4.75%,
  as of 2026-09-01 (`home.htm`); cost-of-capital distribution (US median
  7.79%, 10th–90th 5.26–9.88%) from the January 2026 data update as
  carried in `references/damodaran-anchors.md`.
- **Point-in-time repo DBs:** `data/stocks.db` `v_latest` (price $33.58,
  cap $31.09B, roic 29.98, fcfYield 4.31, netDebtEbitda −2.09, beta 1.03 —
  agrees with the live probe within a day's move); `data/earnings.db`
  (calendar_now 2026-09-04; no 2026-09-10 event yet); `data/composite.db`
  (no CPRT row); `data/sec_fundamentals.db` `v_screener` (CPRT row, latest
  quarter only); `data/portfolio.db` `v_latest_positions` (19 symbols);
  `data/scorer.db` `decisions` (no prior CPRT row).
- **Low-confidence:** Bloomberg/MT Newswires "Market Chatter" on the CCC
  talks (rumor tier, unconfirmed); MT Newswires analyst-action items
  (Barclays $25, JPMorgan $40); Benzinga options-flow item (not used).

## Kill-thesis record

**Kill-thesis verdict: SOUND (on this pass).** conditions=5 (4 probable,
1 plausible), refuted=0, unknown=0.

Per-condition adjudication:

1. Base FCF not understated — **SURVIVED.** Attack: interest income on
   $4.2B cash inflates levered FCF and the cash is in the cap. Scenario E
   nets both out: 6.65%, the same answer. Attack: capex at a six-year low
   is the *understatement* direction — it flatters the base, and scenario
   B reverts it. Nothing found that raises the base.
2. Growth ceiling ≤ ~14% — **SURVIVED (closest attack).** Attack: FY21–25
   revenue CAGR 14.6% shows the rate is inside history. Evidence against
   repeating it: that window carried CAT volume, 2022–23 used-car
   inflation and a rising total-loss tailwind with units *growing* 4–5%;
   today units are negative in the core, consensus 3-year revenue growth
   is 3.76%, and even 12% for five years fails. The condition holds on
   today's evidence; it is the one a bull would attack first.
3. Hurdle ~9% — **SURVIVED.** Attack: the ERP is at a cycle low (4.14%)
   and beta is near 1, so the hurdle is already generous to the stock;
   raising either widens the gap. The company's own 9.88% WACC is above
   the hurdle used.
4. Share loss real — **SURVIVED.** Attack: RB Global's "net market share
   gains" could be non-insurance lots or BigIron-style M&A. Its 8-K
   attributes HE&T growth to BigIron and automotive growth to share and
   price separately; the CEO's own "an account was lost" closes it from
   Copart's side. Magnitude remains unknown (§6.3); direction is evidenced.
5. CCC cannot bridge the gap — **SURVIVED.** Attack: synergies. To reach
   ~$2.0B combined FCF from $1.38B pro forma needs ~$600M of synergies on
   a target with $318M EBITDA — more than doubling the target's cash
   generation. Arithmetic, not disclosure, carries it.

Standing checks: base rate — only ~29% of firms earn above their cost of
capital (Damodaran EVA dataset); Copart is one (ROIC 30%), which is why the
thesis is about price, not quality. Short case — the strongest short is
"a two-player salvage market where the incumbent lost an account, stopped
buying land, replaced its CEO with the founder's son-in-law, and is about
to lever up for a software company, at 23× FCF"; the pass adopts the
valuation half and not the operational half. Management incentives — the
new President's 279,000 hurdle options pay at +25%; the FY2026 buyback
($1.6B at ~$37 average) says management disagrees with this write-up's
price view, which is noted, not credited. Disconfirming search — JPM's
upgrade to $40 was read for the counter-case; its detail is not public
and it is low-confidence colour. Moat — mechanism (land, integration),
industry-level, unchanged; the pass does not rest on it.

Statistical checks: N/A — no backtest, screen or hit rate is relied upon;
the `candidates` screen entry path is calibration-only.

Options timing check: path 2 only, 2026-09-18 expiry, 12 DTE, bracketing
the 9/10 AMC print; liquidity gate FAILED (spread 34% of mark) →
UNRELIABLE; the pass thesis makes no move-dependent claim, so there is
nothing for the one-way valve to cut. Disclosed as run-for-context only.

**Closest attack:** the growth ceiling (condition 2) — a return to the
FY2021–25 growth rate for five years would clear the hurdle; today's
evidence says single digits.

**Flip evidence:** toward FLAWED — the 2026-09-10 print showing US
insurance units ex-CAT positive with FY2027 guidance implying
double-digit fee-revenue growth, which would move condition 2 from
probable to contested; or a CCC deal disclosed at terms where combined
FCF/share exceeds ~$2.15. Toward a stronger SOUND — Q4 US insurance units
negative again alongside RB Global's Q3 8-K repeating "net market share
gains," which would close the magnitude UNKNOWN in the direction the pass
assumes.
