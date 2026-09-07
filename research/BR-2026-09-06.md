# BR — Broadridge Financial Solutions — 2026-09-06

Price $172.88 (official close, 2026-09-04) · market cap $19,712,088,357
(114,021,798 shares × $172.88) · next earnings 2026-11-03 BMO

Unattended scheduled run, user-directed on the ticker. Supersedes
`research/BR-2026-08-04.md`; that thesis's own reopen trigger
(2026-11-03: q1-fy27-print-final-rule-check) is **not** yet due, so this is a
fresh run at a new price, not a reopen — no §0.

## 1. Verdict and thesis

**PASS at $172.88.** kill-thesis: **UNPROVEN** — conditions=6, refuted=0,
unknown=2.

**p(beat SPY, 63 td): 0.45** · kill-thesis: 0.44 — **Disputed expectation:**
the market at $172.88 pays for the FY27 guide delivered *and* the NYSE
processing-fee schedule surviving the SEC's delivery modernization, an
implied 8.5–9.9%/yr depending entirely on whether the M&A that buys 1pt of
the guided growth is charged against the cash flow; what revises it is the
final Reg E-Delivery adopting release's treatment of processing fees and the
2026-11-03 Q1 print against a record $114M event-driven comp.

The business is unchanged and good. The price is what moved. This is the same
franchise the 2026-07-30 run bought at $153.37 — a fee-scheduled network that
sits between ~1,000 brokers and every US issuer, with eight straight years of
positive operating leverage (FY19 revenue $4,362.2M / operating income
$652.7M / 14.96% margin → FY26 $7,476.8M / $1,300.6M / 17.40%) and a FY27
guide of 6–8% recurring constant-currency and 8–12% adjusted EPS. But at
$172.88 it is 27.6% above the 2026-06-29 trough of $135.44 and 2.2% above the
post-print price the last run called a thinner buy, and the margin of safety
that made it interesting has been consumed by the recovery rather than by any
new fact. The two constructions in which the acquisition spend that buys the
guided M&A growth is actually charged against the base cash flow (§4 D and E)
land at −6bp and −64bp against an 8.56% hurdle. It is a fine business at a
fair price, and "fair" is not a reason to initiate.

**Closest attack:** the acquisition charge is a single-year figure. Charging
the six-year mean ($143.8M) instead of FY26's $282.7M moves the same
construction from −6bp to **+80bp** — an 85bp swing on one modelling choice,
which is most of the distance between this PASS and a buy.

Load-bearing conditions (6):

1. *probable* — **The 8.56% hurdle is the right bar, or too low.**
   rf 4.75% + beta 0.92 × ERP 4.14% (Damodaran, as of 2026-09-01); beta
   0.91605 sits inside the 0.8–1.2 stable band, no clamp. Damodaran's own
   mature-company companion (rf + 4.5% = 9.25%) is *higher*, and would push
   scenarios B, D and E negative.
2. *probable* — **FY26 company-defined FCF $1,233.0M is the right base.**
   NCFO $1,345.6M − capex $67.2M − capitalized software $45.4M, reconciling
   exactly to the 10-K MD&A figure; stockanalysis TTM `fcf` $1,278.4M omits
   the software line.
3. *plausible* — **The growth in the guide must be paid for.** 1pt of the
   6–8% recurring guide is acquisitions [Q4 FY26 call]. FY26 acquisition
   spend was $282.7M; against ~$4.7B of recurring revenue, 1pt ≈ $47M of
   acquired revenue, which at a 5–6× revenue bolt-on multiple costs roughly
   $235–280M — so charging FY26's spend to buy 7% growth is arithmetically
   consistent, not punitive. It is still one year of a lumpy series.
4. *plausible* — **Nothing since 2026-08-04 justifies the re-rate.** No 8-K,
   no 10-Q, no DEF 14A, no adverse news; one genuine positive (Payward /
   xStocks, 2026-08-05). The positive is optionality, not earnings.
5. *possible* — **Waiting for the final rule is worth the option cost.**
   Upside option value only: it may cost more than it saves (see §5). Not
   load-bearing for the base case.
6. *plausible* — **The 2026-11-03 print carries negative skew.** Q1 laps a
   record $114M event-driven quarter against a $60–70M average [CFO,
   Q4 FY26 call] — but management pre-announced it, so it is a disclosed
   risk, and disclosed risks are the least mispriced kind.

**Dominant shared risk factor:** US retail equity-account and position growth
— holdings unavailable in this session.

## 2. Business

**Created:** solves the many-to-many problem between ~1,000 broker-dealers
and effectively every US public issuer and fund, for 200M+ beneficial-owner
accounts — proxy distribution, voting, and regulatory disclosure at
mutualized cost that no single broker could reach alone. GTO adds
back/middle-office processing that lets banks retire legacy stacks.
Unchanged from `BR-2026-07-30.md` §2.

**Captured:** four distinct mechanisms, not one. (i) Per-position regulatory
processing fees set by the NYSE fee schedule under Rules 451/465 — the issuer
pays, the broker chooses the vendor, and the SEC reviews the schedule [SEC
comment file SR-NYSE-2020-96, which states that "a single intermediary,
Broadridge Financial Solutions, Inc., handles almost all processing and
distribution of proxy and other material to beneficial owners" in the US].
(ii) Recurring per-account and per-communication subscription fees.
(iii) GTO SaaS and license revenue. (iv) Event-driven work (proxy contests,
fund communications), guided to $250–300M in FY27 after a record FY26.
Distribution pass-through is low-to-no margin and is the leg the SEC is
modernizing.

**Protected:** the mechanism, not a label — SEC and NYSE rules *compel*
broker distribution at a scheduled fee, so a competitor cannot underprice a
regulated price, and taking share means rebuilding ~1,000 broker integrations
for a customer (the broker) who does not pay the bill. 98% revenue retention
[Q4 FY26 call]. The weakness is the same as the source: the rulebook that
grants the toll can amend it, and it is amending the delivery leg right now.

**Control:** one class of common stock, one vote per share, no controlling
holder — 114,021,798 shares outstanding as of 2026-07-31, reported as a
single class with no class axis in the FY26 10-K cover data [SEC XBRL
`dei:EntityCommonStockSharesOutstanding`, CIK 1383312]. The null answer:
nothing forecloses a takeover or an activist path structurally.

**Operating leverage (Phase 0): positive.** Revenue and operating income from
the SEC XBRL company-concept series (`Revenues…ExcludingAssessedTax`,
`OperatingIncomeLoss`; FY26 figures cross-check exactly against the
stockanalysis income-statement probe, 7,476.8 / 1,300.6):

| FY | revenue $M | operating income $M | margin |
|---|---|---|---|
| 2019 | 4,362.2 | 652.7 | 14.96% |
| 2020 | 4,529.0 | 624.9 | 13.80% |
| 2021 | 4,993.7 | 678.7 | 13.59% |
| 2022 | 5,709.1 | 759.9 | 13.31% |
| 2023 | 6,060.9 | 936.4 | 15.45% |
| 2024 | 6,506.8 | 1,017.1 | 15.63% |
| 2025 | 6,889.1 | 1,188.6 | 17.25% |
| 2026 | 7,476.8 | 1,300.6 | 17.40% |

Revenue +71.4% FY19→FY26; operating income +99.3%. The FY20–FY22 margin
trough is the Itiviti integration; leverage has been monotonic positive every
year since.

## 3. Threads pulled

- **What actually changed since the 2026-08-04 run: almost nothing filed.**
  EDGAR shows exactly one 8-K (2026-08-04, Items 2.02/8.01) and one 10-K
  (2026-08-04) since August 1, then only ownership forms. No 10-Q, no
  DEF 14A, no second 8-K. The +2.2% price change and the round trip through
  $185.45 (2026-08-24) happened on no disclosed news.
- **The one real post-call event: Payward / xStocks (2026-08-05).** Broadridge
  will carry shareholder communications and proxy voting for holders of
  xStocks, Payward's (Kraken's) tokenized-equity framework, authenticated via
  Web3 into ProxyVote.com [Broadridge press release, 2026-08-05]. xStocks
  holders previously had no vote on the underlying shares. This is the fourth
  tokenization model BR now governs — synthetic (Ondo), custodial (Alpaca),
  native on-chain (Galaxy), and now the largest retail tokenized-equity venue.
  It is the strongest single datum for condition 4 of the *old* thesis
  ("tokenization taxed, not fled") and it is revenue-immaterial today: Q4
  digital-asset revenue was one point of GTO's 5% quarterly growth [CFO].
  Narrative improvement, not cash-flow improvement.
- **Insider cluster, 2026-08-14 — a dead end, and a small find.** Six Form 4s
  filed 2026-08-14 (plus a Form 5 on 08-11 and a 4/A on 08-10). The one
  sampled (accession 0001225208-26-007122, Corporate VP and CHRO) is
  transaction code **A**: 2,172 shares at $0.00, PSUs "determined at the end
  of a three-year performance period" under the 2018 Omnibus Award Plan,
  vesting 2026-10-01. Not open-market selling. The incidental find: a
  three-year performance cycle just settled in shares — consistent with, but
  not proof of, the CFO's "five consecutive three-year objective cycles
  delivered" claim. The payout percentage is not in the Form 4.
- **The proxy is still not filed.** No DEF 14A appears on EDGAR through
  2026-09-06. Management comp metrics have now gone unread across three
  consecutive runs — but the gap is finally dated: BR's annual meeting is in
  November, so the proxy must appear before it. Carried as UNKNOWN #2 with a
  dated reopen.
- **Regulatory state: unchanged and still unresolved.** Reg E-Delivery
  (proposed 2026-07-16, Federal Register 2026-07-21) remains at the proposal
  stage; the comment period closes **2026-09-21**, with a proposed 60-day
  effective date after adoption and a **two-year transition** for moving
  recipients off paper [Federal Register 2026-14679; Skadden, Gibson Dunn and
  Alston & Bird client memos — low-confidence tier, corroborating scope].
  Scope is delivery default, not the fee schedule. A disconfirming search for
  any 2026 move on the NYSE Rule 451/465 processing-fee schedule itself
  returned only 2012–2016 material and no current proceeding — which is
  evidence of absence only to the depth a public search reaches.
- **The earnings-surprise pattern is managed, and the actuals are not GAAP.**
  Eight consecutive beats, all small: +0.07, +0.01, +0.05, +0.29, +0.24,
  +0.11, +0.07 (Q4 FY26 $3.82 vs $3.75) [Robinhood MCP, broker tier]. The
  FY26 quarterly actuals sum to $9.64 against reported adjusted EPS $9.60 —
  so these are the company's **adjusted** figures, not GAAP, exactly as the
  repo's standing note on this field says. The GAAP cross-check is
  unavailable: BR has no row in `data/sec_fundamentals.db`. Independently,
  stockanalysis's `epsdil` for FY26 is also **$9.60** — GAAP and adjusted
  coincide this year because the $227.0M Canton digital-asset gain
  (`gainAssets`, income statement) roughly offsets the $291.8M of
  intangible-asset amortization added back [SEC XBRL
  `AmortizationOfIntangibleAssets` FY26; FY25 $283.8M, FY24 $279.5M].
- **The unexplained Friday.** BR fell 3.37% on 2026-09-04 ($178.91 →
  $172.88) on 1.25M shares against a ~1.0M recent average, while SPY fell
  0.38%. Then stockanalysis's quote block records an **after-hours print of
  $178.76 (+3.40%) at 7:46 PM EDT** the same evening, while Robinhood's feed
  shows no trade after 4:15 PM EDT. No 8-K, no press release, and no news
  item explains either leg. Recorded as UNKNOWN #3; the valuation uses the
  official 4:00 PM close of $172.88 and ignores the after-hours tick.
- **Machine view: the repo has never had an opinion on this name.**
  `composite.db` snapshot 67 (2026-09-07T04:05Z = 2026-09-06 Phoenix) scores
  BR bullish=0 / bearish=0 / total=0 / **coverage 0.0**, `in_portfolio`=1.
  The only ticker-grain rows are informational and score 0: `sa_fscore` 7.0
  and `sa_fcf_yield` 6.267% (obs 2026-09-03), plus `portfolio_holding`
  0.1242% of book. No voting signal has ever flagged BR, so nothing in §4
  rests on a repo signal and the statistical checks in Phase 5 are N/A by
  construction.
- **Options read (mandatory):** path 2 only (Robinhood stopgap). Path 1 is
  N/A — BR is not in the 24-symbol CBOE catalog, so `data/options.db` has no
  history for it and no own-history IV percentile exists. The 2026-12-18 $175
  pair is the only listed expiry that brackets the 2026-11-03 print; it
  **FAILS the liquidity gate** on both legs. Table and verdict in §4.
- **Dead ends and coverage gaps:** (i) `data/portfolio.db` is not readable in
  this session — the headless slot has no grant — so the §1 factor-overlap
  count could not be produced; the factor itself is stated. (ii)
  `data/scorer.db` is likewise ungranted, so the prior verdict rows were read
  from `research/verdicts.log` instead. (iii) BR has no row in
  `data/sec_fundamentals.db` and none in `data/earnings.db`
  `v_upcoming_earnings` — both unchanged from the prior two runs; the
  2026-11-03 BMO date comes from `data/stocks.db` `v_latest`
  (`nextEarningsDate`/`earningsTime`) and Robinhood, which marks it
  unverified. (iv) The exact `hover` strings on `/stocks/BR/statistics/` were
  not retrievable this run: the scheduled slot permits only the probe module,
  whose CLI summarizes nested lists rather than printing them. Market cap is
  therefore derived from the 10-K cover share count × the official close, and
  reconciles to stockanalysis's own displayed $19.71B and to `stocks.db`'s
  $20,399,639,880 at the 2026-09-03 close of $178.91. (v) The XBRL
  acquisition-spend series looks incomplete — it reports $339.1M for FY2021,
  the year BR closed the ~$2.5B Itiviti purchase — so the six-year mean used
  in the closest attack is low-confidence; the FY26 figure itself
  ($282.7M) is a direct read and is not.

## 4. Valuation

**Inputs and pairing.** Levered FCF against **market cap $19,712,088,357**
(114,021,798 shares from the FY26 10-K cover × the 2026-09-04 official close
$172.88); net debt is **0 by the pairing rule** — the flow is post-interest,
so the debt has already been served. For reference only, net debt is
$3,116.7M (total debt $3,520.5M − cash $403.8M), 13.7% of enterprise value,
which is far below the Phase 4 leverage gate; the equity-as-option lens does
not apply and item 6 is omitted. Base flow is the **company-defined FY26 FCF
$1,233.0M** = NCFO $1,345.6M − capex $67.2M − capitalized software $45.4M
(the 10-K MD&A definition; stockanalysis's TTM `fcf` of $1,278.4M omits the
software line). No minority interests. Haircuts applied where scenarios say
so: SBC $93.9M (1.26% of revenue) and FY26 acquisition spend $282.7M. Base
earnings for the reinvestment test are **cash earnings $1,174.7M** = net
income $1,124.3M − the after-tax Canton gain ($227.0M × 0.7776) + after-tax
acquired-intangible amortization ($291.8M × 0.7776), at the FY26 effective
rate of 22.24%.

**Hurdle:** rf 4.75% + beta 0.92 × ERP 4.14% = **8.56%** (Damodaran implied
ERP and T-bond rate, as of 2026-09-01). Beta 0.91605 [`stocks.db`] sits
inside the 0.8–1.2 stable band — no clamp. His absolute companion for a
mature company, rf + 4.5% = **9.25%**, is 69bp *higher*; both are quoted
below because the gap changes three of six answers.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A — company FCF, organic-mid growth | $1,233.0M | 6% | 2.5% | 9.93% | **+137bp** |
| B — less SBC, organic-low growth | $1,139.1M | 5% | 2.0% | 8.70% | **+15bp** |
| C — guide-high, M&A growth unpaid | $1,233.0M | 8% | 2.5% | 10.55% | **+200bp** |
| D — less FY26 M&A spend, total-guide growth | $950.3M | 7% | 2.5% | 8.50% | **−6bp** |
| E — less SBC and M&A spend | $856.4M | 7% | 2.5% | 7.91% | **−64bp** |
| D′ — M&A charged at the 6yr mean $143.8M | $1,089.2M | 7% | 2.5% | 9.35% | **+80bp** |
| F — prior-run comparability (sa `fcf`, 3yr) | $1,278.4M | 6% ×3y | 2.5% | 9.81% | +125bp |

Against the 9.25% companion hurdle instead: A +68bp, B −55bp, C +130bp,
D −75bp, E −134bp, D′ +10bp, F +56bp. Row F is the same shape as the
2026-08-04 run's row D (9.81% now vs 10.09% then); the whole distribution has
shifted down roughly 25–30bp on the 2.2% price move, and the *paid-for-growth*
rows are new to this run.

**Integrity checks.**

- **Reinvestment / terminal-ROE.** The tool prints its `growth without
  reinvestment` warning on rows A, C and F, where base FCF exceeds cash
  earnings — answered, not left standing, by the two moves the skill allows:
  the earnings base is restated to cash earnings $1,174.7M (net income is
  understated by $291.8M of acquired-intangible amortization, exactly the
  BR case), and the acquisition spend that is BR's real reinvestment is
  charged in rows D, D′ and E. On those rows the warning clears and the
  implied terminal ROE reads 13.1% (D), 34.4% (D′) and 9.2% (E). Read
  two-sided: E's 9.2% sits ~65bp above the hurdle and is the fade-consistent
  case; D's 13.1% is ~4.5 points above and is defensible; D′'s 34.4% is
  "tough to do" in perpetuity and is why D′ should be read as the optimistic
  end of the paid-for-growth family, not the centre. B's 66.0% is not
  defensible as a perpetual return on incremental capital and is the reason
  B's +15bp should not be leaned on.
- **Base-year cash tax.** FY26 effective rate 22.24% ($321.6M on $1,445.9M
  pretax) against a ~24–25% blended US federal-plus-state marginal rate for
  this filer. The gap is roughly one point of after-tax income — no NOL or
  deferral story flattering the base, no haircut taken.
- **Market share.** 6% for five years puts FY2031 revenue at ~$10.0B, 1.34×
  FY26. The honest reading is that this cannot come from the proxy leg: the
  SEC's own comment record describes BR as handling "almost all" US
  beneficial-owner proxy processing, so that leg is already effectively fully
  penetrated and grows only with position counts and the fee schedule. The
  growth in every scenario above therefore has to come from GTO, wealth, and
  international — a materially less protected set of markets than the one the
  moat argument is about. This is the sharpest structural point in the
  valuation and it does not depend on the regulatory question at all.
- **Terminal growth vs the disclosed terminal risk.** The FY26 10-K's Item 1A
  carries two structural risks bearing on year-10 cash flows: physical
  delivery volumes falling, where "recurring revenue growth and distribution
  revenues will decrease… potential restructuring of our physical
  distribution operations," and a new tokenization **disintermediation**
  factor [Item 1A as read and quoted in the 2026-08-04 run; no 10-K has been
  filed since, so the wording is current]. A 2.0–2.5% terminal rate survives
  those only on the modernized-not-restructured fee outcome plus BR
  continuing to tax the tokenized rails — the first is the open UNKNOWN, the
  second is where the Payward deal is genuine evidence. Terminal growth is
  well under the 4.75% risk-free cap.
- **Distribution clamp.** The implied returns span 7.91%–10.55%, straddling
  the US median cost of capital of 7.79% and sitting inside the 5.26–9.88%
  band that holds 80% of US firms except for row C. Nothing here is a
  strong-pass-regardless-of-story number; nothing here is a bargain either.
  The excess-return base rate (~29% of firms earn above their cost of
  capital) says the default terminal assumption is fade, and the fade-shaped
  rows are the ones below the hurdle.

**Options-implied move.** Path 2 only (Robinhood stopgap); path 1 N/A — BR is
not in the 24-symbol CBOE catalog and `data/options.db` has no history for
it. BR lists exactly four expiries (2026-09-18, 2026-10-16, 2026-12-18,
2027-03-19); the only one that brackets the 2026-11-03 BMO print is
**2026-12-18, DTE 103** from today. ATM pair taken at the $175 strike against
a $172.88 spot; ATM IV is the mean of the call's 36.9623% and the put's
36.9325%. Note the 2026-09-03 ex-dividend ($1.09) sits behind the window and
another falls inside it, so nearest-strike is a slightly rougher proxy for
50-delta than usual.

| metric | value |
|---|---|
| spot | 172.88 |
| dte (calendar days) | 103 |
| ATM IV | 36.95% |
| expected absolute move (MEAN, not a ceiling) | 15.68% |
| 1-sigma move | 19.63% |
| RV60 | 33.97% |
| IV > RV60? | YES |
| RV20 | 30.19% |
| IV > RV20? | YES |

**Liquidity gate: FAILED → UNRELIABLE.** Call spread $12.10/$14.80 = $2.70,
20.1% of the $13.45 mark; put spread $12.30/$15.00 = $2.70, 19.8% of the
$13.65 mark — both twice the 10%-of-mark gate. Same-day volume 0 on both
legs; open interest 9 calls / 5 puts. Nothing in this table may move a
verdict. Both RV windows read below IV, which would ordinarily print
"elevated," but this is the stopgap's known artifact working exactly as
documented: the December IV spans a scheduled print while RV20 contains none
(RV60 does contain the 2026-08-04 +9.4% gap, which is why RV60 > RV20 here).
**Timing check: NOT APPLICABLE** — the thesis states no required move by any
date, so there is no timing claim to refute, and the read is recorded as the
mandatory thread only. Since ATM IV is 36.95%, under the 50% line, the
implied returns above are quoted to two decimals rather than whole percents.

## 5. Falsifiers

**For the pass (flip toward buy):**

1. **Shift —** the price returns to a level where a *paid-for-growth*
   construction clears the 9.25% companion hurdle. On row D that is roughly
   $17.9B of market cap, ~$157/share; on row D′ roughly $19.5B, ~$171.
2. **Shift —** the final Reg E-Delivery adopting release leaves the NYSE
   processing-fee schedule untouched **and** the stock has not already
   re-rated for it — removing UNKNOWN #1 raises the base case without moving
   the price.
3. **Shift —** the FY26 proxy discloses management comp tied to recurring
   revenue and adjusted EPS rather than to a total-revenue or
   deal-count metric, closing UNKNOWN #2.
4. **Shift —** two consecutive quarters where acquisition spend runs at the
   six-year mean rather than FY26's level while recurring growth holds in the
   6–8% band — the D-versus-D′ question resolved by the cash flow statement
   instead of by assumption.

**For an owner (sell):**

5. **Break —** the final rule touches processing fees or intermediary
   compensation rather than only the delivery default. This is the thesis
   killer, unchanged across all three runs.
6. **Break —** a Schwab- or Fidelity-scale broker announces issuer-direct
   communications or self-custody equity wallets that bypass the
   ProxyVote.com rails.
7. **Shift —** FY27 guidance cut below 5% recurring cc or below 8% adjusted
   EPS at any quarterly update.
8. **Shift —** equity position growth below 5% for two consecutive quarters,
   or revenue retention below 97%.
9. **Shift —** e-delivery transition quarters showing recurring (not just
   distribution) revenue declining with **no** quantified offset — the
   "largely offset with new solutions" claim failing in the prints.
10. **Shift —** tokenized-equity volume migrating to rails BR does not
    service: the Ondo / Alpaca / Galaxy / Payward relationships going quiet
    while tokenized float grows.

**Reopen trigger:** 2026-11-03: q1-fy27-print-proxy-and-price — the Q1 FY27
print (event-driven comp, guide reaffirmation, first post-comment-period
e-delivery commentary), by which date the FY26 DEF 14A must also have been
filed ahead of the November annual meeting; re-run the paid-for-growth rows
at whatever the price then is, and read the final rule whenever it adopts.

## 6. UNKNOWNs

1. **The final Reg E-Delivery rule.** The proposal resolved scope favorably
   (delivery default, not fee schedule), but the adopting release is the
   deciding document and does not exist; comments close 2026-09-21 and
   adoption is months away. Would come from the SEC adopting release.
   Its absence caps the verdict at UNPROVEN; it does not kill the thesis, and
   on a PASS it argues for waiting rather than against.
2. **Management compensation metrics.** The FY26 DEF 14A is not filed as of
   2026-09-06. Would come from the proxy, due before the November annual
   meeting. Absence does not kill the thesis but leaves the standing check
   "does the thesis assume management acts against its incentive" unrun for
   a third consecutive run.
3. **The 2026-09-04 price action.** A 3.37% decline on no filed news, and a
   +3.40% after-hours print at 7:46 PM EDT that appears in stockanalysis's
   quote block and not in Robinhood's feed. Would come from an 8-K (none
   filed), a press release (none), or a tick-level consolidated tape this
   session cannot reach. Does not kill the thesis; it does mean the entry
   price used here may be one session stale in a way the next run should
   check first.
4. **The e-delivery offset math.** No filing discloses fee mix by
   communication type, so "largely offset with new solutions" and "no
   significant impact on adjusted earnings growth" remain management
   assertions. Would come from a segment or fee-type disclosure BR has never
   made. Carried unchanged from both prior runs; load-bearing for the
   transition years, not for the base case.
5. **The multi-year acquisition-spend series.** The XBRL
   `PaymentsToAcquireBusinessesNetOfCashAcquired` history reports $339.1M for
   FY2021, the year the ~$2.5B Itiviti purchase closed, so the concept is not
   capturing the full spend. Would come from the 10-K cash-flow statements
   read directly. This is the input behind the closest attack, so its
   weakness is the reason that attack is a caveat rather than a verdict
   change.

## 7. Sources

- **Primary:** FY26 10-K (filed 2026-08-04, fiscal year ended 2026-06-30) via
  SEC XBRL company-concept API, CIK 1383312 — `OperatingIncomeLoss` FY19–FY26,
  `RevenueFromContractWithCustomerExcludingAssessedTax` FY19–FY26,
  `AmortizationOfIntangibleAssets` FY24–FY26,
  `PaymentsToAcquireBusinessesNetOfCashAcquired` FY21–FY26,
  `dei:EntityCommonStockSharesOutstanding` (114,021,798 at 2026-07-31, single
  class); EDGAR filing index for CIK 1383312 (form types and dates since
  2026-08-01); Form 4 accession 0001225208-26-007122 (2026-08-14, code A PSU
  settlement). Item 1A wording and the Q4 FY26 call detail are quoted from
  `research/BR-2026-08-04.md`, which read them directly; no 10-K, 10-Q or
  8-K has been filed since, so they are current. SEC comment file
  SR-NYSE-2020-96 (BR's share of US beneficial-owner proxy processing);
  Federal Register 2026-14679 (Reg E-Delivery, published 2026-07-21, comments
  due 2026-09-21). Broadridge press release, 2026-08-05 (Payward / xStocks).
- **stockanalysis.com (vetted exception):** `/stocks/BR/` overview (market cap
  $19.71B, shares 114.02M, beta 0.92, forward P/E 16.39, dividend $4.36,
  price path price1w 183.64 / price1m 157.34 / price1y 249.82, analyst
  consensus 9 analysts / $213.38 target), `/stocks/BR/financials/
  income-statement/` (TTM revenue 7,476.8M, opinc 1,300.6M, gainAssets
  227.0M, pretax 1,445.9M, taxexp 321.6M, netinc 1,124.3M, epsdil 9.60,
  taxrate 22.24%), `/stocks/BR/financials/cash-flow-statement/` (ncfo
  1,345.6M, capex −67.2M, salePurchaseIntangibles −45.4M, sbcomp 93.9M,
  cashAcquisition −282.7M, commonRepurchased −603.7M, fcf 1,278.4M),
  `/stocks/BR/transcripts/` (index; newest is still the Q4 FY26 call,
  2026-08-04), `/filings/BR/` (quote block, including the 2026-09-04
  after-hours print).
- **Broker/market microstructure:** Robinhood MCP — no already-integrated
  official source covers these fields for BR (BR has no `sec_fundamentals.db`
  row and no `earnings.db` row). Live quote and official closes ($172.97 last
  trade, $178.91 prior close); daily OHLCV bars 2026-04-27 → 2026-09-04 (the
  RV20/RV60 closes array); option chain (four expiries), the 2026-12-18 $175
  call/put instruments and quotes (marks, IV, spreads, OI, volume); earnings
  estimate-vs-actual for eight quarters plus the 2026-11-03 date, marked
  unverified.
- **Reference data:** Damodaran implied ERP 4.14% and T-bond rate 4.75%, as
  of 2026-09-01 (NYU Stern home page); mature-company cost-of-capital
  companion rf + 4.5%; US median cost of capital 7.79% with an 80% band of
  5.26–9.88% (Data Update 5, 2026); excess-return base rate ~29% (EVA
  dataset).
- **Point-in-time repo DBs:** `composite.db` snapshot 67 (2026-09-07T04:05Z)
  — BR coverage 0.0, no voting signal, `in_portfolio`=1, informational
  `sa_fscore` 7.0 and `sa_fcf_yield` 6.267%, `portfolio_holding` 0.1242%;
  `stocks.db` `v_latest` (shares 114,021,798, market cap 20,399,639,880 and
  EV 23,516,339,880 at the 2026-09-03 close, debt 3,520.5M, cash 403.8M, beta
  0.91605, ROE 40.92%, RSI 36.83, fScore 7, next earnings 2026-11-03 bmo,
  index membership SP500); `earnings.db` `v_upcoming_earnings` (empty for
  BR); `research/verdicts.log` (prior BR verdicts). `portfolio.db` and
  `scorer.db` were not readable in this session.
- **Low-confidence:** law-firm client memos on Reg E-Delivery scope and
  transition (Skadden, Gibson Dunn, Alston & Bird, DFIN); web search results
  for the 2026-09-04 price action, which returned nothing dated to that
  session.

## Kill-thesis record

**UNPROVEN** — conditions=6, refuted=0, unknown=2 (the final rule's fee
treatment; management comp metrics).

Per-condition adjudication:

1. **The 8.56% hurdle is right or too low — SURVIVED.** The attack was that
   beta 0.92 understates risk on a name whose realized vol has run 30–34%
   against a historically quieter tape. It fails on its own terms: beta
   measures relative, not total, risk, and BR's drawdown was idiosyncratic
   (a regulatory narrative), which lowers beta rather than raising it.
   0.91605 sits inside the stable band and needs no clamp. The finding runs
   the other way — Damodaran's own mature-company companion is 9.25%, 69bp
   higher, and it flips three of six scenarios negative.
2. **$1,233.0M is the right base flow — SURVIVED.** It reconciles exactly to
   the 10-K MD&A (1,345.6 − 67.2 − 45.4) and is the more conservative of the
   two available definitions. The attack that deducting SBC on top
   double-counts against the $603.7M buyback fails: the buyback is a use of
   the same cash flow, not an addition to it, and in a per-firm equity DCF
   SBC is compensation the owner does not keep.
3. **Growth must be paid for — SURVIVED, and this is where the closest attack
   landed.** The charge is not double-counting SBC: they are different claims
   (share-based compensation versus cash reinvestment). And the magnitude
   checks out — 1pt of ~$4.7B recurring revenue is ~$47M of acquired revenue,
   which at a 5–6× bolt-on multiple costs roughly $235–280M, so FY26's
   $282.7M is what 1pt of guided M&A growth actually costs. What the attack
   did land: FY26 is one year of a lumpy series, and charging the six-year
   mean ($143.8M) instead moves the same construction from −6bp to +80bp.
   That 85bp swing is most of the distance between this PASS and a buy. It is
   a caveat rather than a verdict change for two reasons: the underlying XBRL
   series is demonstrably incomplete (it reports $339.1M for the ~$2.5B
   Itiviti year), and charging less M&A logically requires growing slower —
   at $143.8M BR buys ~0.6pt not 1pt, and the matched 6.6% run gives +68bp,
   not +80bp.
4. **Nothing since 2026-08-04 justifies the re-rate — SURVIVED, qualified.**
   Partially dented by the Payward / xStocks agreement (2026-08-05), which is
   a real strategic datum: BR now governs all four tokenization models,
   including the largest retail tokenized-equity venue. But it is
   revenue-immaterial today (digital assets were one point of GTO's 5%
   quarterly growth), so it buys optionality, not earnings, and the price
   moved +2.2% net with a round trip through $185.45 on no filed news at all.
5. **Waiting for the final rule is worth the option cost — SURVIVED as the
   closest *conceptual* attack.** The strongest case against the PASS is that
   this exact reasoning has now been offered at $153.37, at $169.21 and at
   $172.88, and the stock rose 12.7% through the first two waits. "Wait for
   the deciding document" is not falsifiable on any schedule the investor
   controls. It survives because the asymmetry is real and points the same
   way: the benign *proposal* is plausibly already in the +27.6% recovery off
   the June trough, so adoption offers modest remaining upside while a
   fee-touching surprise is a step change down. Tagged *possible* and
   explicitly non-load-bearing for the base case in §1 for exactly this
   reason.
6. **The 2026-11-03 print carries negative skew — SURVIVED, weakly.**
   The record $114M event-driven comp against a $60–70M average is real, but
   management pre-announced it on the Q4 call, and a pre-announced comp is
   the least mispriced kind of risk. Weak evidence for a PASS; it is in the
   list because the reopen trigger hangs on the same date, not because it
   carries the verdict.

Standing checks. **Base rate:** only ~29% of firms earn above their cost of
capital (Damodaran EVA dataset), so "the excess return persists" is a
3-in-10 proposition before evidence. BR is currently in the 29% — ROE 40.9%,
ROIC 17.0% against an 8.56% cost of equity — but the base rate says fade, and
the fade-consistent constructions (D at 13.1% terminal ROE, E at 9.2%) are
precisely the ones below the hurdle. **The short case against the PASS** (the
strongest long argument): a regulated monopoly toll with 98% retention, eight
straight years of positive operating leverage, a 20th consecutive dividend
raise, a $1.5B buyback authorization, trading 32% below its August-2025 high
at 16.4× forward earnings with nine analysts averaging a $213.38 target —
and the historical record that buying a compounder at a fair price beats
waiting for a cheap one. That argument is not refuted here; it is the reason
the verdict is UNPROVEN and not FLAWED-for-the-buyer. **Management
incentives:** unrun for a third consecutive run — the DEF 14A is not filed.
Flagged, not credited. **Disconfirming search:** ran on the 2026-09-04 price
action (nothing found — UNKNOWN #3) and on any current NYSE Rule 451/465
fee-schedule proceeding (nothing current found, which is evidence of absence
only to the depth a public search reaches). **Moat as mechanism:** compelled
distribution under SEC/NYSE rules, plus the payer/chooser split, plus ~1,000
broker integrations for a customer who does not pay the bill — a mechanism,
not a checkbox. It survives, and the §4 market-share check is the sharper
point against it: the protected leg is already ~fully penetrated, so all
modelled growth must come from the less protected GTO/wealth/international
businesses.

Statistical checks: **N/A by construction.** The thesis rests on no backtest,
screen, hit rate, or repo signal — `composite` has coverage 0.0 on BR and has
never voted it. Nothing here needs a null.

Options timing check: **NOT APPLICABLE.** The thesis states no required move
by any date. Coverage disclosed anyway: path 2 only (path 1 N/A — BR is not
in the CBOE catalog), the only bracketing expiry is 2026-12-18 at DTE 103,
and both ATM legs FAIL the liquidity gate (spreads 20.1% and 19.8% of mark
against a 10% gate; volume 0/0; OI 9/5). UNRELIABLE; it moves nothing.

**Closest attack:** condition 3 — charging the six-year mean acquisition
spend ($143.8M) rather than FY26's $282.7M moves the paid-for-growth
construction from −6bp to +80bp against the hurdle, an 85bp swing on one
modelling choice, which is most of the distance between this PASS and a buy.

**Flip evidence:** (to SOUND for the PASS) the final rule touching processing
fees, or the Q1 FY27 print reaffirming guidance only at the low end with the
stock still above $170. (to FLAWED) a benign final adopting release arriving
while operating metrics hold and the stock re-rates — proving the wait was
the expensive choice — or two quarters of acquisition spend at the six-year
mean with recurring growth still in the 6–8% band, which would move the
paid-for-growth rows decisively above the hurdle.

**p(beat SPY, 63 td): 0.44.**
