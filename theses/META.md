# META — Meta Platforms, Inc. — 2026-07-29

Price ~$541.31 (after-hours, 2026-07-29; regular close $587.00) · market cap
≈ $1,374B (after-hours decision price) · next earnings 2026-10-28
(tentative)

Run on the evening of the Q2'26 print (released after today's close; stock −8.8%
after hours at ~$541.31 vs the $587.00 regular close as of ~4:00pm PT quotes).
All "today" prices are that after-hours tape unless labeled otherwise.

Entry path: not recorded (pre-template run).

## 1. Verdict and thesis

**PASS at ~$541.** kill-thesis: **UNPROVEN** — conditions=5, refuted=0,
unknown=3.

The core ad business is compounding at ~27% and is probably
worth the market cap on its own, but the price only implies ~**10–11%/yr** if two
conditions — capex discipline by 2028 and productive use of ~$490B of committed
infrastructure — resolve favorably, and **neither is verifiable in any disclosure
today**; the trough-FCF reading implies ~**7%/yr**.

Thesis as attacked: the derating is a cash-flow-visibility problem, not a
demand problem — FCF crushed to ~$0.8B/quarter by the AI buildout, funded by
debt and SPVs with buybacks suspended — and if ad growth holds near consensus
while the buildout eventually decelerates, today's price is paying roughly an
equity-market return for a much-better-than-market business.

**Closest attack:** not recorded (pre-template run).

Load-bearing conditions: not enumerated in the original run (pre-template);
the original references conditions 3–5 only in passing (§4 terminal-risk
check, §6). Condition tiers not recorded in original run.

## 2. Business

**Created:** 3.60B people use a Meta app daily (DAP, June 2026, +3% YoY);
free connection/entertainment funded by ads whose relevance is now the product —
LLM-ranked feeds drove Instagram time spent up double digits YoY (Q2 call).

**Captured:** not "advertising" — an auction over ~14%-more impressions at
12%-higher average price (Q2 print), plus a fast-growing second lane: FoA "other
revenue" hit $1.0B/quarter, +73% YoY (WhatsApp paid messaging, Meta One
subscriptions), plus nascent model API / business agents / compute sales (no
disclosed revenue yet). Reality Labs remains a −$4.6B/quarter cost center.

**Protected:** mechanism, not label — impression supply at a scale and CPM
efficiency no rival can assemble (advertiser auction density = better price
discovery per impression), a creative/targeting data flywheel, and now compute
scale. The tested competitor (TikTok) was contained by Reels rather than fatally
wounding the franchise.

**Operating leverage (Phase 0): positive 2021→2025** (revenue +70%,
operating income +78%, FY25 margin 41.4%) — **negative in 2026**: H1
revenue +30.4% vs expenses +45.6%; Q2 margin 31% vs 43% LY (ex $2.4B legal +
$1.18B severance charges, op income +9% YoY vs revenue +28%).

## 3. Threads pulled

- **Earnings-print timing.** Entered triage with earnings.db showing the report
  due today AMC; the stockanalysis trust-block timestamp (~21:30 UTC) resolved
  that the print had *just* landed, already ingested. The whole run is therefore
  on fresh post-print data, not into an unresolved binary.
- **The commitments footnote (the "asset-light is a balance-sheet question"
  check) — the biggest find.** 10-Q (Q1'26): **$237.67B non-cancelable purchase
  commitments** ($42.25B due 2026, $47.65B due 2027; +$24B added April 2026),
  **$182.88B leases signed but not yet commenced** (terms to 30 years,
  commencing 2026–2036), contingent cloud purchases up to $14.72B, a $5.0B
  escrow tied to a multi-year purchase agreement, and an unconsolidated
  data-center JV (VIE) with **max loss exposure $45.99B** (leases + funding
  commitments + residual value guarantee) plus $5.79B other VIEs. Elevated
  spend is contractually locked well past 2027 — any "FCF snaps back in 2027"
  scenario is refuted by the issuer's own schedule.
- **Funding mix shift.** Q2: $24.9B debt raised; LT debt $83.7B (from $58.7B at
  YE25); **buybacks $0 in H1'26** vs $22.9B H1'25; dividends ~$1.35B/q; shares
  now creeping up QoQ (+0.08%) with SBC at $7.66B/q (+58% YoY, 12.6% of
  revenue). Capital return has effectively stopped while dilution resumed.
- **EPS miss decomposition.** First GAAP miss in ≥7 quarters ($6.18 vs $7.18
  est; prior six were beats of $0.59–$1.27 — broker tier). ~$1.18/share of the
  miss is the $2.4B legal + $1.18B severance charges; ex-charges roughly
  in line. Robinhood's "actual" matches the 8-K's GAAP $6.18 — no definition
  trap this quarter. Q1'26's outsized EPS ($10.44) contained a ~$5.0B one-time
  tax benefit (10-Q) — normalize before trending.
- **Insider filings.** Forms 4 arrive on a steady weekly cadence via the same
  filing agent (latest: Olivan, COO) — consistent with programmatic 10b5-1
  sales. Dead end; no signal.
- **Composite's view.** Mild +1 (1 bullish/0 bearish signals); informational
  signals only (`earnings_imminent`, iv30 50.8, PCR 0.41, sa_fscore 5,
  sa_fcf_yield 3.2%). Nothing the machine flagged contradicts or anticipates
  the print.
- **Options read (mandatory):** path 2 (Robinhood stopgap; path 1 gate
  unmet, `n_days`=19 < 60) — see §4.
- **Dead ends:** META absent from `sec_fundamentals.db` v_screener (EPS
  cross-check done against the 8-K directly); stockanalysis `/financials/`
  payload shape changed vs the catalog doc (data now under `sections[].rows`,
  noted for the repo); `debt=112.3B` on stockanalysis reconciles as $83.7B LT
  debt + $28.7B operating leases — not a data error.

## 4. Valuation

Reverse DCF, levered TTM FCF paired with **market cap** (fcf = ncfo + capex is
post-interest). Decision price: after-hours $541.31 × 2.5384B shares ≈ **$1,374B**.
Precision: iv30 is 50.8 (>50), so implied returns are quoted to the whole
percent only.

Hurdle: not computed in the original run (pre-template).

| scenario | base FCF | growth path | implied return |
|---|---|---|---|
| A — trough FCF held low | $41.0B (TTM, stockanalysis defn) | 10%×5, tg 2.5% | **~7%/yr** |
| B — normalized earnings power | $76.5B (TTM pretax + $3.6B one-time charges, at 16% tax) | 12/12/12/10/8, tg 2.5% | **~11%/yr** |
| C — FCF recovery on capex plateau | $41.0B | 40/35/25/18/12, tg 2.5% | **~10%/yr** |

Stated per skill: a flat single-rate run (A) understates a business mid
investment cycle, so B models steady-state earnings power and C an explicit
recovery path — but **C's 2027 leg is refuted by the commitments schedule**
(recovery cannot start before 2028), so read C as an upper band, and note the
company's own FCF definition (incl. finance-lease principal: $784M in Q2,
$13.2B H1) runs ~$3B/yr below the $41.0B base used. At today's *regular* close
($587, $1,490B cap) subtract roughly 1 point from each scenario.

Terminal risk vs terminal growth: the 10-K's dominant structural risk is ad
concentration ("substantially all of our revenue... from marketers advertising
on Facebook and Instagram") plus legal/regulatory (youth trials flagged as
potentially material in the print itself). tg=2.5% (≈nominal GDP) survives
only if attention and the auction survive the agent era in some monetized
form; it does not survive a structural remedy or feed disintermediation — both
carried as falsifiers, condition 5 and 4 below.

**Options-implied move** (path 2 — Robinhood stopgap; path 1 gate unmet,
`n_days`=19 < 60): Jul-31 expiry (DTE 2), pre-print 4pm marks — ATM straddle
$50.40 on $587 spot:

| metric | value |
|---|---|
| spot | 587 |
| expected absolute move (MEAN, not ceiling) | 8.59% |
| 1-sigma move | 11.12% |
| ATM IV | 150.26% |
| RV60 | 41.94% |
| RV20 | 54.02% |
| IV > RV60? | YES |
| IV > RV20? | YES |

Both YES = "elevated", the mechanical earnings-week reading. The realized
−8.8% AH move landed on the priced mean — tonight's drop is not a surprise
to the options market, which per the one-way valve is evidence for nothing.

## 5. Falsifiers

Would make me stay out / a holder sell:

1. FoA ad growth <12% YoY for two consecutive quarters while the capex guide
   rises again.
2. 2027 capex guided >30% above the 2026 range with still no disclosed
   external compute/API revenue run rate.
3. Any impairment or renegotiation of DC leases/VIEs, or the residual value
   guarantee triggering.
4. Youth-trial or regulatory outcome that forces structural ad-model changes
   (not a fine — fines in the $5–20B range are absorbable at ~$91B normalized
   pretax).
5. Susan Li's stated commitment broken: FY26 operating income fails to exceed
   FY25's $83.3B.
6. Buybacks stay at zero while share count grows >2%/yr.

**Reopen trigger:** revisit at the Q3'26 print (2026-10-28, tentative),
where the first 2027 capex outlook and any external compute/API revenue
disclosure would convert the two central UNKNOWNs into testable claims.

## 6. UNKNOWNs

1. **2027 capex** — refused on the call ("not providing a specific outlook").
   Comes from the Q3/Q4 prints. Its absence is why the verdict is UNPROVEN, not
   a kill by itself.
2. **External compute/API/enterprise revenue** — zero disclosed ("more to share
   soon"); "offers at a significant premium" is an unquantified management
   claim. Would come from segment or supplemental disclosure. Absence blocks
   condition 3 from verification.
3. **Composition of the $2.4B legal charge** — not broken out in the 8-K;
   10-Q (August) may disclose. Bounded-ness of legal risk is the issuer's own
   stated unknown ("cannot be estimated... may be material in the aggregate").
4. **True maintenance capex of the AI fleet** (server replacement cycle) —
   determines terminal FCF conversion; not disclosed anywhere. Absence forces
   the A/B scenario spread; it does not kill the thesis but keeps it wide.
5. **Muse model competitiveness vs frontier labs** — domain science I cannot
   evaluate; bounded by observable proxies (Meta AI DAU +60% since Muse Spark
   integration — company claim; OpenRouter distribution just started). Marked
   UNKNOWN, counted inside condition 3.
6. **Ad-uplift figures** (8.3% clicks, 15.7% conversions, 1% app-event
   conversions) — company-reported A/Bs with no independent null; treated as
   directional, never as measured fact.

## 7. Sources

**Primary:** Q2'26 8-K + Ex-99.1 press release (acc
0001628280-26-050596, filed 2026-07-29) — all Q2 financials, segment split,
guidance, buyback/dividend, balance sheet; 10-Q Q1'26 (acc
0001628280-26-028526) — commitments, VIE, leases, Q1 tax benefit; 10-K FY25
(acc 0001628280-26-003942) — Item 1A ad-concentration risk; Forms 4 (weekly,
Davis Polk agent; latest 0000950103-26-011342, Olivan).

**stockanalysis.com (vetted exception):** /stocks/META/statistics/ (market
cap hover 1,486,526,071,055 pre-AH; TTM figures; shares out 2,538,423,304),
/financials/ annual + quarterly (FY21–25 and Q2'24–Q2'26 series),
/transcripts/657318-q2-2026/ (full call transcript, Quartr-sourced —
primary-transcribed).

**Broker/market microstructure:** (Robinhood MCP; admissible — real-time
price and options state not covered by an integrated official source)
after-hours quote $541.31 (23:01Z), 8-quarter estimate-vs-actual EPS pattern
(estimates side only is new), META option chain / Jul-31 ATM quotes, daily
bars for RV. `get_financials` not used (banned; SEC covers it).

**Reference data:** none used.

**Point-in-time repo DBs:** data/earnings.db (event date/time),
data/options.db v_iv_rank (iv30 51.4, n_days 19 — path-1 gate unmet),
data/composite.db (META +1, signal detail).

**Low-confidence:** none used. Call-transcript management claims are primary
as *statements* but labeled as claims where unverifiable (ROI, compute
offers, ad-uplift A/Bs).

## Kill-thesis record

**Kill-thesis verdict: UNPROVEN** — 5 load-bearing conditions; 0 refuted, 3
UNKNOWN. The two central UNKNOWNs — capex discipline by 2028 and productive
use of ~$490B of committed infrastructure — are verifiable in no disclosure
today; the Q3'26 print is where they become testable claims.

Per-condition adjudication: not recorded in the original run (pre-template).
Standing/statistical/options-timing checks: not recorded in the original
run. **Closest attack:** not recorded (pre-template run). **Flip
evidence:** not recorded (pre-template run).
