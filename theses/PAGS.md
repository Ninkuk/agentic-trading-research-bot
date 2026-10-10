# PAGS — PagSeguro Digital (PagBank) — 2026-09-13

Price $10.12 (official close, 2026-09-11) · market cap $2,789.5M · next
earnings 2026-11-11 AMC (tentative)

Unattended scheduled run. Held position (composite `portfolio_holding` 1.148,
the book's largest weight signal); supersedes `research/PAGS-2026-08-13.md`
(BUY at $8.72, UNPROVEN). Composite has never flagged PAGS on its own
signals — score 0/0, coverage 0.0; the two rows it carries
(`sa_fcf_yield` 37.75, `sa_fscore` 6.0) are annotations scored 0.

## 1. Verdict and thesis

**PASS at $10.12.** kill-thesis: **UNPROVEN** — conditions=6 (2 probable,
4 plausible), refuted=0, unknown=1, pending=4, not_obtained=0.

**p(beat SPY, 63 td): 0.46** · kill-thesis: 0.42 · **Disputed expectation:**
the market pays $10.12 for a stream whose *observed* two-year trajectory
(BRL net income +1.7% cumulative, i.e. a real decline against ~4.5% BRL
inflation) implies **13.70%/yr — 74bp BELOW** the 14.44% Brazil-adjusted
hurdle; only the flat-USD reading clears (+183bp). A Q3 print (2026-11-11)
with gross profit ≥ +8% y/y, NPL90 ≤ 3.5% and active banking clients
flat-or-up forces the revision back toward the August case.

The business has not changed since 2026-08-13; the **price** has, by +16.1%
in a month, and that move consumed the whole margin of safety the August BUY
rested on. That thesis's load-bearing property was that *every* scenario
cleared the hurdle — "even a −3%/yr fade clears it." At $8.72 the flat case
cleared by 411bp and the melt case by ~109bp. At $10.12 the flat case clears
by 183bp and **the melt case fails by 123bp**; the price at which the melt
case re-clears is ~$9.10. Meanwhile the news since is net negative: three
engagement denominators are shrinking (active clients −3.3%, active banking
−2.7%, banking-only −5.0% y/y), the credit-loss allowance expense grew 150%
against a book that grew 31%, the Basel ratio fell 22.5% from 29.6% against
the company's own 18–22% target, and the September 1 announcement that drove
+7.7% in one session was in substance a **29% reduction** in the guided
dividend run-rate. The one clean positive — a fourth buyback and the first
QoQ decline in financial costs in nine quarters — does not restore 228bp of
lost spread. This is a "the entry price is gone," not a "the business is
broken," call: an owner's sell falsifiers (§5) are not triggered.

**Closest attack:** PAGS's ROE is **14.53%** and Brazil's Selic is
**14.00%** — the local risk-free rate is the competition, so ~0.96× book is
the *correct* price for this bank, not a discount. The entire bull case is a
levered bet that Selic falls faster than priced, and management's own
year-end Selic assumption has already moved the wrong way, from ~12.5% at
guidance to 13.75–14% (Q2'26 call).

Load-bearing conditions of the **bull** case (the case for owning PAGS at
$10.12) — **six**, two probable and four plausible:

1. *probable* — **BRL net income does not decline over the forecast window.**
   FY2024 R$2,116M → FY2025 R$2,118M → TTM R$2,151M: flat through the worst
   of the Selic cycle. (Note what this is *not*: flat BRL is a real decline,
   and §4 shows that path fails the hurdle.)
2. *plausible* — **FY2026 gross profit grows 6–9% y/y**, i.e. H2 accelerates
   to ~+10% from H1's +2%. Settled by the Q3 print, 2026-11-11, and the FY
   print in early March 2027.
3. *plausible* — **the credit book's loss curve stays inside current
   provisioning** as the unsecured share rises past 24%. Settled by the Q3
   print's NPL90 / credit-loss-allowance table, 2026-11-11.
4. *plausible* — **capital return continues at the guided level without an
   equity raise**, on the 22.5% → 18% Basel glide. Settled by the Q3 Basel
   ratio, 2026-11-11, and the 2027 dividend declaration in Q1 2027.
5. *probable* — **the take rate holds at ~1.5% gross profit / TPV.** Held at
   exactly 1.5% in both Q2'26 and Q2'25 (0.0pp y/y); management says SMB
   acquiring pricing has been rational for ~24 months.
6. *plausible* — **the active-client decline does not become a revenue
   decline** — cash-in per active banking client (+26.7% y/y) keeps
   offsetting a −3.3% active base. Settled by the Q3 client table,
   2026-11-11.

**Dominant shared risk factor:** Brazilian policy-rate and currency regime
(Selic level plus BRL/USD) — shared by 0 of 19 other held names · 3
unlabelled (G, ORI, PRI carry theses with no factor line). Holdings read
from `composite.db` `portfolio_holding` rows, not `portfolio.db` (no
headless grant). The nearest adjacency is not a match: PYPL
("US and European online consumer") and EEFT ("cross-border movement of
people") would co-fall only in a global de-rating of payment multiples, a
different scenario from a Brazilian rate or currency shock.

## 2. Business

- **Created:** payments acceptance (POS / PIX / cards) plus a full digital
  bank — deposits, bill pay, investments, insurance, credit — for Brazilian
  micro/SMB merchants and consumers. 34.1M total clients (+3.1% y/y),
  deposits R$42.8B (+15.1%), on-platform 91.6% of deposits, cash-in R$97.0B
  in the quarter (+23.3%). One app replaces a bank-plus-acquirer pair for
  merchants too small for the incumbents to serve well. **The engagement
  numbers now cut the other way:** active clients 17.1M vs 17.7M (−3.3%),
  active banking clients 16.9M vs 17.4M (−2.7%), banking-only 10.9M vs
  11.5M (−5.0%), active merchants 6.2M (−0.3%). Total clients grew and
  *active* clients shrank — the gap is inactive signups.
- **Captured:** four distinct mechanisms, not one. (i) acquiring MDR on
  R$133.4B quarterly TPV; (ii) the prepayment spread on the R$52.4B expanded
  receivables portfolio — this is the balance sheet, R$59.8B of receivables
  against R$75.7B of assets; (iii) deposit float and the funding-cost spread
  — deposits pay 83.3% of CDI versus 89.2% a year ago, checking accounts
  38.0% of CDI; (iv) lending NIM on the R$5.1B credit book plus fees on
  banking, insurance and investments. Gross profit is revenue net of
  transaction costs, financial costs and credit losses, and has held at 1.5%
  of TPV.
- **Protected:** no moat in acquiring — a commodity terminal against three
  scaled rivals (Stone, Mercado Pago, CloudWalk). The one real mechanism is
  banking principality: on-platform deposits that fund the receivables book
  below market, plus transaction-history underwriting data. That mechanism is
  **measurably weakening on both legs**: the active banking base is shrinking
  2.7% a year, and management said on the Q2 call that deposit cost
  stabilises "around these low 80s, 83%" — the funding-cost lever that drove
  nine consecutive quarters of improvement is close to exhausted. Valuation
  below assumes excess returns fade; the moat is not load-bearing.
- **Control:** UOL retains super-voting control through a dual-class
  structure. Float is 143.4M of 275.6M shares (52.0%); insiders 3.80%. An
  unsolicited takeover and any activist path are foreclosed; minority
  holders' only lever is the exit.

**Operating leverage (Phase 0): positive at the operating line, flat at the
bottom line — and the gap is the Selic.** (BRL millions; stockanalysis
income statement, TTM through Q2'26.)

| | 2021 | 2022 | 2023 | 2024 | 2025 | TTM |
|---|---|---|---|---|---|---|
| Revenue | 10,299 | 15,159 | 15,680 | 18,334 | 19,743 | 19,804 |
| Operating income | 2,122 | 5,073 | 5,385 | 5,959 | 7,412 | 7,478 |
| Operating margin | 20.6% | 33.5% | 34.3% | 32.5% | 37.5% | 37.8% |
| Net income | 1,166 | 1,505 | 1,654 | 2,116 | 2,118 | 2,151 |
| Net margin | 11.3% | 9.9% | 10.6% | 11.5% | 10.7% | 10.9% |

Revenue +92% since 2021 while operating income rose +252% — genuine positive
operating leverage. Net income rose only +84%, and net margin is *lower*
than 2021. The entire operating gain has been absorbed below the line by
interest expense (TTM −R$4,903M against R$7,478M of operating income). Over
the last two years the bottom line has been flat outright: R$2,116M →
R$2,151M, +1.7% cumulative against ~4.5% annual BRL inflation. Stated
plainly: PAGS's earnings are a levered short position on Brazilian interest
rates, and the last two years are what that costs when rates rise.

## 3. Threads pulled

- **The September 1 announcement — the thread that explains the price.**
  6-K 2026-09-01 (0001554855-26-001939) authorises a **fourth** repurchase
  programme of **up to US$150M** in Class A shares, effective immediately,
  no fixed expiration, and targets "at least R$2.0 billion in dividends
  during 2027 and 2028 (R$1.0 billion per year)," subject to "market and
  company financial conditions" and Board discretion. The stock closed +7.7%
  the next session (9.14 → 9.84) and ran to 10.13 by 09-10. **Read against
  the 2026 plan, the dividend line is a step-down, not a raise:** 2026 is a
  planned R$1.4B; the 2027–28 *floor* is R$1.0B/yr, 29% lower. The buyback
  authorisation is also 25% smaller than the $200M programme it follows.
  "At least" leaves room above, and the no-expiry structure means the $150M
  need not be a one-year figure — but nothing in the 6-K commits to more.
  This is the single largest disagreement between the price action and the
  document.
- **Why the dividend guide fell — the Basel thread.** Q2'26 release
  (6-K 0001554855-26-001793): BIS ratio **22.5%**, down from **29.6%** a year
  earlier, against a stated target range of **18%–22%**. That is a 7.1pp
  drawdown in one year with 4.5pp left to the company's own floor, while the
  book grew (total credit +30.7%, expanded portfolio +9.0%) and R$2.0B was
  returned to shareholders over the LTM. Sustainable equity growth is
  retention × ROE ≈ 10% × 14.5% ≈ 1.5%/yr; the gap between that and the
  balance-sheet growth has been paid out of the capital buffer, and the
  buffer is nearly spent. The R$1.4B → R$1.0B dividend guide is what that
  arithmetic looks like when the board acts on it. This also constrains the
  2029 ambition below.
- **The 2029 ambition, checked against the capital.** The Q2 release
  restates it: "R$25 billion Credit Portfolio, gross profit CAGR of
  approximately 10% and EPS CAGR above 16% between 2025 and 2029." R$5.1B →
  R$25B is ~49%/yr of risk-weighted-asset growth. EPS CAGR >16% against GP
  CAGR ~10% needs ~6pp/yr of share shrink — and the buyback just got 25%
  smaller while dividends were prioritised. High growth, heavy distribution
  and a falling capital ratio cannot all hold; one of the three gives.
- **Credit book — the alarm thread, now with the Q2 numbers.** Total book
  R$5.1B (+30.7%); secured R$3.8B (86.9% → 75.7% of the book), unsecured
  R$1.2B (+142.7%, 13.1% → 24.3%). Payroll R$3.4B (+17.5%), cards R$1.1B
  (+34.8%), working capital R$0.6B (+203.6%, July origination ~R$80M).
  NPL90 3.4% vs 2.5% a year ago — and a denominator that grew 30.7%
  mechanically dilutes that ratio, so the vintages are worse than +0.9pp
  looks. **Credit loss allowance expenses R$70M vs R$28M (+150%)** and
  provision for losses R$0.4B vs R$0.3B (+49.1%): losses are compounding at
  roughly five times the book's growth rate. Offsets, honestly stated: R$70M
  is 3.5% of quarterly gross profit (R$1,999M); the book is 34% of R$15.0B
  equity; a 10% total loss on today's book (R$510M) is ~0.9 quarters of net
  income — painful, not fatal. At the R$25B ambition the same event exceeds a
  full year's earnings. On the call, asked directly by Neha Agarwala (HSBC)
  for NPL and cost of credit by product, management refused: "We do not
  disclose any information regarding individual products here in terms of
  credit appetite."
- **Selic and the funding cost.** Selic is **14.00%** after four consecutive
  cuts since June 2026, with a September 15–16 Copom meeting priced at ~95%
  for a 25bp cut to 13.75% (low-confidence: press). Management's original
  2026 guidance assumed a ~12.5% year-end Selic; on the Q2 call they revised
  to **13.75–14%** — the easing is arriving slower than the plan assumed.
  The genuine positive: Q2 financial costs fell 5% QoQ, the first decline in
  nine quarters (R$1,274M, −0.4% y/y, 37.7% of ex-ITC revenue vs 38.5%).
- **Guidance arithmetic.** FY26 guide (Q2 call): gross profit +6–9%, diluted
  non-GAAP EPS +9–13%, explicitly assuming **no additional buybacks**. H1
  gross profit ran +2% and Q2 +2.8%. Reaching even the bottom of the range
  needs H2 at roughly +10%. Management: "we continue to expect to deliver a
  full year performance in line with the guidance range… probably not by the
  top of the range." Asked by Guilherme Grespan (JPMorgan) what drives 2027
  if rate tailwinds reverse, Gustavo Sechin deferred: "Too early to discuss
  2027."
- **Engagement — the new adverse thread.** Revenue +0.4% y/y (ex-ITC +1.7%)
  and TPV +3.0% are being produced on a *shrinking* active base. Three of
  four engagement denominators fell (above). The offset, cash-in per active
  banking client +26.7%, is a volume metric that does not monetise
  one-for-one — Pix cash-in carries a lower take than card. If deepening
  plateaus while the base keeps shrinking ~3%/yr, revenue turns negative,
  and that is precisely the scenario (§4 run C) that now fails the hurdle.
- **Earnings-estimate pattern (broker tier).** Five hair-thin beats
  Q4'24–Q4'25, then two misses: Q1'26 0.39 vs 0.40, Q2'26 0.388 vs 0.40.
  Q3'26 estimate 0.41, report 2026-11-11 AMC (tentative). The managed-
  guidance cadence broke this year and has not resumed.
- **Ownership filings.** EDGAR company index shows **no Form 3, 4 or 5 filed
  since 2026-08-01** — no insider buying into the +16% run, and no repeat of
  the July Form 4 (Principal Executive Officer Ricardo Dutra, 50,000 Class A
  at $9.24–9.27, that holding line to zero) recorded in the prior thesis.
  Silence here reads as neutral-to-mildly-negative: nobody with a desk at the
  company bought this move.
- **Options read (mandatory):** path 2 only (Robinhood stopgap) — PAGS is not
  in the 24-symbol CBOE catalog and `data/options.db` carries no PAGS row, so
  path 1 is structurally unavailable. Metric table, liquidity verdict and
  timing applicability in §4.
- **Dead ends.** `sec_fundamentals.db` carries a PAGS row but only assets
  (R$74.4B) and liabilities (R$59.8B) — no revenue, income, margin or EPS
  (foreign private issuer filing IFRS on 20-F/6-K, so the XBRL facts the
  screener harvests are absent); live probe and EDGAR used throughout.
  `earnings.db` has no PAGS row (`v_upcoming` empty for the symbol), so the
  earnings date came from the broker tier and stockanalysis. `composite.db`
  has never flagged PAGS — and its one quantitative annotation on the name,
  `sa_fcf_yield` 37.75%, is precisely the receivables/deposit artifact §4
  rejects; a screen reading that as a 37% FCF yield is reading noise. The
  Q2 call contains **no** discussion of the October 2026 Brazilian election,
  taxation or regulation beyond a generic reference to "regulatory milestones
  that can change the credit landscape… especially on the collateral
  products" — searched for and absent, which is itself the finding.

## 4. Valuation

**The pairing, and why the default is refused here.** stockanalysis's plain
`fcf` for PAGS is R$5,108M TTM (ncfo R$6,049M + capex −R$941M), which against
a $2,789.5M market cap prints a ~36% FCF yield. That number is an artifact,
not owner cash: `ncfo` for a prepayment bank absorbs the receivables and
deposit swings (TTM `changeAR` −R$9,518M, `changeOtherNetOperAssets`
+R$4,741M, `otheroperating` +R$6,584M), and the statement's own alternative
measures disagree violently — `leveredFCF` is **−R$1,856M** and
`unleveredFCF` +R$1,208M on the identical period. The base here is **TTM
GAAP net income, $415.21M** (stockanalysis's USD conversion of R$2,151.1M at
~5.18 BRL/USD), paired with **market cap $2,789.5M** ($10.12 × 275.646M
shares); net debt 0 by the pairing rule. SBC is $24.29M TTM (0.64% of
revenue) and is already charged in GAAP net income — no further haircut. No
minority interest (`minorityInterest` null on the income statement).

**The leverage gate does not fire, deliberately.** Reported debt is R$1.7B
against R$15.0B of equity, book equity is positive and large, there is no
going-concern language, and assets/equity is 5.0×. The R$60.7B of
liabilities are deposits, merchant payables and funding — operating
liabilities of a bank, not a claim on operating assets that makes the equity
a call option. `tools.valuation.equity_option` is the wrong lens and was not
run; the DCF frame governs §1's ownership call.

**Hurdle:** rf **4.95%** (`DGS10`, fred.db, 2026-09-10) + beta **1.27**
(stockanalysis overview, live) × Brazil **total ERP 7.47%** (Damodaran
`ctryprem.html`, January 5, 2026 vintage — ~100% Brazilian revenue, so the
country premium replaces the headline US number) = **14.44%**. Beta is just
outside the 0.8–1.2 stable band on the high side, which raises the hurdle —
no clamp applied, since the thin-float rule (float 52.0% of shares out)
only floors a *sub*-band beta and flooring upward would be a free pass.
Vintage note: Damodaran's own implied ERP is **4.14%** as of September 1,
2026 against his 4.75% T-bond rate, while the country table is the January
vintage; one vintage per calculation, so the January Brazil total ERP is
used throughout. On the US headline ERP the hurdle would be 10.21% and every
scenario would clear by 300–600bp — the Brazil premium *is* the discipline
here. Note also that 14.44% sits far outside Damodaran's US cost-of-capital
distribution (median 7.79%, 80% band 5.26–9.88%, 2026 update); that is
expected for a single-country Brazilian issuer, not a red flag.

**Terminal-growth ceiling: 2.36%** — the 10-year breakeven (`T10YIE`,
fred.db, 2026-09-11). Because the flow is USD-converted BRL earnings, the
USD breakeven is the right ceiling: a nominal-BRL stream growing at BRL
inflation, in a currency depreciating at the inflation differential, is flat
in real terms and grows at US inflation in USD. Anything above 2.36% claims
perpetual real growth, which retained earnings must fund.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A flat USD earnings | $415M | 0%/yr | 2.36% | **~16%** | **+183bp** |
| B mgmt-path | $311M (75% of NI, growth-capital retention) | +8%/yr | 2.36% | **~17%** | **+207bp** |
| C melt | $415M | −3%/yr | 0% | **~13%** | **−123bp** |
| D enacted-tax drag | $386M (NI −7%) | 0%/yr | 2.36% | **~15%** | **+84bp** |
| E observed path (BRL flat) | $415M | −2.1%/yr | 0% | **~14%** | **−74bp** |

Returns are quoted to the nearest whole percent: ATM IV is 49.5% and the put
leg alone prints 56.5%, so a figure like "16.27%" would be arithmetic, not
knowledge. Exact solver outputs, for the record: A 16.27%, B 16.51%,
C 13.21%, D 15.28%, E 13.70%.

**Run E is the one to read, and it is not a bear case.** It sets BRL net
income flat — exactly what the company has delivered for two years — and
lets the USD stream drift down at the ~2.1% BRL/USD inflation differential.
That is the *observed* trajectory extrapolated, and it misses the hurdle by
74bp. The same portfolio of runs at the August price (market cap $2,403.6M)
put run A at +411bp; the 16.1% price move cost **228bp** of spread and moved
the melt and observed-path cases from clearing to failing. The price at
which run C re-clears the hurdle is ~$9.10 (at $9.00, +46bp).

**Integrity checks.**

- **Reinvestment warning, answered.** Runs A and D trip `growth without
  reinvestment`: base FCF equals base earnings (a 100%-payout construction),
  yet terminal growth is 2.36%. The answer the skill prescribes applies
  cleanly here — 2.36% is the USD-inflation repricing of existing assets,
  which needs no reinvestment; real growth beyond it would. Actual payout is
  ~90% of net income (R$916M dividends + R$1,011M buybacks against R$2,151M
  TTM), so roughly 10% *is* retained. Run C and run E set terminal growth to
  zero and do not trip it.
- **Implied terminal ROE.** Run B prints 9.44%, below the 14.44% hurdle: the
  terminal period assumes PAGS destroys value on retained capital. That is
  deliberate conservatism, and it is also the right default — only ~29% of
  firms earn above their cost of capital (Damodaran EVA dataset).
- **Market-share sentence.** Run B's +8%/yr puts USD earnings near $610M by
  2031. PagBank holds ~10% of Brazilian acquiring TPV and under 1% of most
  banking verticals; nowhere near a bigger-than-the-market path. The 2029
  credit ambition (R$5.1B → R$25B) is the aggressive number in the company's
  own materials, and it is not in any run above.
- **Base-year cash tax rate.** Effective tax 17.3% TTM against a statutory
  34% moving to 37% (2026–27) and 40% (2028+) under LC 224/2025 for payment
  institutions (20-F FY2025, carried from the 2026-08-13 run's read of
  0001554855-26-000826; not re-read this run). Run D prices the ~7% net-income
  drag that implies by 2028; run C and run E envelope it.
- **Terminal risk vs terminal growth.** The dominant structural risks in the
  20-F's risk factors are Pix displacing card economics (Pix MDR < debit <
  credit) and the enacted tax escalation — both carried from the prior run's
  read, and both bear directly on whether cash flows still grow in year 10.
  A 0–2.36% terminal range survives them only because runs A/D assume no real
  growth at all and C/E assume none whatsoever; a terminal rate above the
  breakeven would not survive either risk.
- **Serial-acquirer and cash-heavy clamps: not applicable.** No material
  acquisition spend (`cashAcquisition` null TTM); cash and investments are
  R$1.4B against R$75.7B of assets — the balance sheet is receivables, not an
  idle cash pile, so no excess-cash adjustment applies.
- **The exogenous input the table cannot hold.** BRL/USD is a §4 scenario
  input, not a condition. Every USD figure above uses ~5.18. A move to 6.00
  (−14%, well inside a Brazilian election-year range) takes base USD earnings
  to ~$358M with zero operational change, and the flat case then lands
  between runs C and E — i.e. below the hurdle. The 7.47% country ERP prices
  Brazilian *risk* generically; it does not price a specific 14% currency
  move inside the horizon. Brazil's first-round presidential vote is
  **October 4** with a likely **October 25** runoff currently polling as a
  statistical tie (low-confidence: press), both inside the 63-day horizon.

**Options-implied move — path 2 only (Robinhood stopgap).** PAGS is not in
the CBOE catalog and `data/options.db` has no PAGS history, so path 1 is
structurally unavailable and no own-history IV percentile exists. Expiry
**2026-11-20, 68 DTE**, ATM strike 10.0 — chosen because it brackets both the
election (Oct 4 / Oct 25) and the Q3 print (Nov 11 AMC). ATM IV is the mean
of the call's 42.45% and the put's 56.53%.

| metric | value |
|---|---|
| spot | 10.12 |
| expected absolute move (MEAN, not a ceiling) | 16.80% |
| 1-σ move | 21.36% |
| ATM IV | 49.49% |
| RV60 | 32.07% |
| RV20 | 40.09% |
| IV > RV60? | YES |
| IV > RV20? | YES |

Both windows read YES, so IV is **elevated** on this comparison — with the
stopgap caveat that a 68-day window containing an election, a runoff and an
earnings print is exactly the case where a forward IV mechanically exceeds
trailing realized vol without that being a discovery. Note also that RV20
(40.09%) is itself far above RV60 (32.07%): realized vol has already risen
sharply, so the IV premium over the recent window is only ~9 points.

**Liquidity gate: FAILED → UNRELIABLE.** Call volume 2 and put volume 15
(floor is 100); call spread $0.55 on a $0.825 mark (67%) and put spread $0.45
on a $0.875 mark (51%), against a 10%-of-mark gate; and a 14-point call/put
IV disagreement consistent with stale marks. Call OI 1,766, put OI 37. The
table is context, not evidence.

**Timing check: NOT APPLICABLE.** The bull case makes dated *disclosure*
claims (conditions 2, 3, 4, 6 all settle at the 2026-11-11 print) but no
dated **price-move** claim, and the 2-sigma refutation only applies to the
latter. Recorded as skipped with the reason, not as a pass.

## 5. Falsifiers

**For the pass (flip toward buy):**

- **Shift —** price at or below **~$9.10**, where run C (the −3%/yr melt)
  re-clears the 14.44% hurdle and the August structure — every scenario
  clearing — is restored.
- **Shift —** Q3'26 gross profit growth **≥ +8% y/y** with financial costs
  down ≥ 5% y/y, confirming the H2 acceleration the FY guide requires and
  that the Selic easing is reaching the P&L.
- **Shift —** active banking clients flat or growing y/y, ending the
  engagement-decline thread.
- **Shift —** Basel ratio **≥ 21%** at Q3 with the 2027 dividend declared at
  or above R$1.2B, showing the capital constraint is looser than the
  September 1 guide implies.

**For an owner (sell):**

- **Break —** NPL90 accelerating past **~4.5%**, or credit-loss allowance
  expense exceeding ~15% of quarterly gross profit (R$70M / R$1,999M = 3.5%
  today) — the credit engine is broken and the melt case takes over.
- **Break —** take-rate war resumption: gross profit / TPV falling decisively
  below 1.4%, or the gross-profit guide withdrawn.
- **Break —** an equity raise, or the 2027 dividend declared below R$1.0B
  alongside a Basel ratio under 19% — the capital arithmetic has broken and
  the distribution that carries the flat-earnings case is gone.
- **Shift —** effective tax rate above ~30% (the enacted escalation tracking
  worse than the −7% estimate) — rerun the DCF.
- **Shift —** BRL/USD beyond ~6.00 without a matching BRL-earnings response —
  revalue; the USD stream has permanently reset.
- **Shift —** a Selic re-tightening cycle — delays, does not kill, the case.

**Reopen trigger:** 2026-11-11: `pags-q3-26-print-gross-profit-growth-at-or-above-8pct-with-npl90-at-or-below-3-5pct-and-active-banking-clients-flat-or-up-and-bis-ratio-at-or-above-21pct-or-price-at-or-below-9-10`

## 6. UNKNOWNs

1. **UNKNOWN — the through-cycle loss rate of the unsecured book.** No
   filing, past or future within the horizon, carries it: the working-capital
   and card vintages are under two years old and have not seen a Brazilian
   downturn, and management explicitly refuses product-level credit
   disclosure (Q2 call, to HSBC). It would only come from several more years
   of quarterly NPL and coverage data, or from a cycle. This is load-bearing
   and it is why the verdict is UNPROVEN: at $10.12 the cushion in the flat
   case is 183bp, and a bad unsecured vintage is exactly what turns run A
   into run C.
2. **UNKNOWN — the industry NPL comparison.** Management asserts NPL90 of
   3.4% against a Brazilian market average of 6.2% (Q2 call). Verifying it
   needs BCB series this repo does not ingest; unverified for a second
   consecutive run.
3. **PENDING 2026-11-11 — the Basel trajectory.** The 22.5% → 18% glide is
   measured backwards (29.6% → 22.5% in a year) but forward it is a forecast.
   The Q3 ratio settles whether the buffer is being managed down deliberately
   or consumed faster than the distribution guide assumes.
4. **NOT OBTAINED — management's compensation metrics.** They exist in the
   20-F FY2025 remuneration disclosure (0001554855-26-000826, Item 6.B),
   which this run did not read. It would settle whether the EPS-CAGR-above-16%
   ambition is an incentive target — and therefore whether shrinking the
   buyback was discipline or capitulation. Not load-bearing on any of the six
   conditions, so it is not counted in the ledger, but it is a fixable miss.
5. **UNKNOWN — UOL controller intentions.** Capital-allocation continuity
   rests on the controlling shareholder, who has no disclosure obligation
   before the fact. Structural; unresolvable.

Option value (*possible* tier, deliberately not numbered as a condition): a
faster Selic easing cycle than the 13.75–14% year-end management now assumes
would drop financial costs (R$1,274M/q, 37.7% of ex-ITC revenue) far faster
than any run above allows and could restore double-digit gross-profit growth
on its own. Cannot be dated or sized; it is why this is a PASS on price and
not a negative view of the business.

## 7. Sources

- **Primary:** (SEC) 6-K 2026-09-01 (0001554855-26-001939 — fourth
  repurchase programme US$150M, 2027–28 dividend target R$2.0B); 6-K
  2026-08-11 (0001554855-26-001793 — Q2'26 release: all financial, credit,
  funding, client, Basel and repurchase figures); EDGAR company filing index
  for CIK 0001712807 (no Form 3/4/5 since 2026-08-01). Q2 2026 earnings call
  transcript, 2026-08-11 — primary-transcribed, obtained via stockanalysis
  (`/stocks/PAGS/transcripts/638318-q2-2026/`). 20-F FY2025
  (0001554855-26-000826) — tax law LC 224/2025, Pix risk factor; **carried
  from the 2026-08-13 run, not re-read this run.**
- **stockanalysis.com (vetted exception):** `/stocks/PAGS/` overview (market
  cap, beta, analyst count and target, dividend, shares out — live probe
  2026-09-13); `/financials/income-statement/`, `/balance-sheet/`,
  `/cash-flow-statement/` (BRL TTM and annual history, the `fcf` vs
  `leveredFCF` vs `unleveredFCF` divergence); `/statistics/` (ROE 14.53%,
  block structure).
- **Broker/market microstructure:** (Robinhood MCP) official close $10.12
  (2026-09-11); earnings estimate-vs-actual pattern for eight quarters and
  the 2026-11-11 AMC date; option chain, ATM instruments and quotes for the
  implied-move table; 89 daily closes 2026-05-06 → 2026-09-11 for RV20/RV60.
  Admissible: no already-integrated official source covers PAGS quotes,
  options or consensus estimates — `sec_fundamentals.db` has no FPI income
  statement and `earnings.db` has no PAGS row.
- **Reference data:** (Damodaran, below primary) implied ERP 4.14% and T-bond
  4.75% as of September 1, 2026 (`home.htm`); Brazil total ERP 7.47%, CRP
  3.24%, Ba1 (`ctryprem.html`, last updated January 5, 2026); US
  cost-of-capital distribution median 7.79% / 80% band 5.26–9.88% (2026 Data
  Update 5); excess-return base rate ~29% (EVA dataset).
- **Point-in-time repo DBs:** `fred.db` — DGS10 4.95% (2026-09-10), T10YIE
  2.36% (2026-09-11). `stocks.db` snapshot 2026-09-09 — beta 1.266, float
  143.43M, shares out 275.65M, insiders 3.80%, institutions 47.07%, SBC
  $24.29M, SBC/revenue 0.64%, analyst count 16, chYTD −31.1%, 52-week range
  8.42–12.32. `composite.db` snapshot 75 — `in_portfolio`=1,
  `portfolio_holding` 1.148, score 0/0 coverage 0.0, and the holdings list
  used for the factor-overlap count. `sec_fundamentals.db` — assets/
  liabilities only. `options.db` — PAGS absent from the 24-symbol catalog.
- **Low-confidence:** press colour for the Selic level (14.00%, four cuts
  since June 2026) and the ~95% market-implied odds of a 25bp cut at the
  September 15–16 Copom; press colour for the October 4 / October 25
  Brazilian election dates and the tied-runoff polling. None of these carries
  a numbered condition; the Selic level bears on §4 as a scenario input only.

## Kill-thesis record

**UNPROVEN** — conditions=6, refuted=0, unknown=1, pending=4,
not_obtained=0. (Survived=2. `not_obtained=0` because the one NOT OBTAINED
item, the 20-F remuneration note, attaches to no numbered condition — §6.4.)

Per-condition adjudication of §1's **bull-case** list:

1. **SURVIVED** (*probable*) — BRL net income flat over two years
   (R$2,116M → R$2,151M) through the worst of the Selic cycle. The attack
   that nearly landed: flat nominal BRL is a ~4.5%/yr real decline, and run E
   prices exactly that at 74bp *below* the hurdle. The condition as stated
   stands; the valuation frame that quoted it as "conservative" does not.
2. **PENDING 2026-11-11** — FY26 gross profit +6–9%. Attacked with the
   arithmetic: H1 ran +2%, Q2 +2.8%, so H2 must reach ~+10%. The available
   lever is financial costs (R$1,274M/q), and a ~5% reduction in the average
   Selic is worth roughly R$60M/q ≈ 3% of gross profit — enough for the
   bottom of the range, not obviously for the middle. Management has already
   pre-announced a below-top outcome. Not refuted, because guidance was
   affirmed.
3. **PENDING 2026-11-11** — loss curve inside provisioning. Attacked hard:
   credit-loss allowance expense +150% y/y against a book +30.7%; unsecured
   share 13.1% → 24.3%; working capital +203.6%; NPL90 diluted by a
   fast-growing denominator; management refuses product-level disclosure.
   Base rate applied: rapidly extended unsecured credit into a thin-file
   population usually ends badly. Survives only on scale — R$70M is 3.5% of
   quarterly gross profit and a 10%-of-book loss is ~0.9 quarters of
   earnings. The through-cycle curve behind it is the UNKNOWN.
4. **PENDING 2026-11-11** — capital return without an equity raise.
   Internal-consistency attack, and it landed partially: 49%/yr credit growth
   to the 2029 ambition, ~90%-of-earnings distribution, and a Basel ratio
   falling 7.1pp/yr with 4.5pp to the company's own 18% floor cannot all
   hold. The board has *already* conceded one leg — the 2027–28 dividend
   floor is R$1.0B/yr against 2026's R$1.4B, and the buyback authorisation
   shrank from $200M to $150M. That concession is what keeps the condition
   as-stated alive rather than refuted.
5. **SURVIVED** (*probable*) — gross profit / TPV at 1.5%, flat y/y, four
   stable quarters, with management asserting ~24 months of rational SMB
   pricing. Noted cost of the survival: price is being held by ceding volume
   growth (TPV +3.0%, active merchants −0.3%).
6. **PENDING 2026-11-11** — active-client decline does not become revenue
   decline. Attacked with the Q2 table: active clients −3.3%, active banking
   −2.7%, banking-only −5.0%, while total clients grew 3.1% (inactive
   signups). Revenue is +0.4% and the offset is cash-in per client (+26.7%),
   a volume metric with a lower take rate than card. Adverse but not yet
   refuted — revenue is still positive.

**Standing checks.** *Base rate:* three ran — only ~29% of firms out-earn
their cost of capital (Damodaran EVA), which cuts little because runs A/C/E
assume fading excess returns; rapid unsecured credit extension into thin-file
borrowers usually ends badly, which cuts directly at condition 3; and an EM
bank whose ROE equals the local risk-free rate is worth about book, which is
where it trades. *Short case:* a commodity acquirer growing TPV 3% on a
shrinking merchant base, whose growth engine has moved to unsecured consumer
credit underwritten through one benign cycle, whose capital buffer funding
R$2.0B of LTM returns fell 7.1pp in a year with 4.5pp left, whose statutory
tax rate goes to 40% by 2028, and whose equity is a levered claim on
Brazilian rates and the BRL three weeks before a tied presidential runoff —
up 16% in a month on a headline that was, in substance, a smaller dividend.
*Management incentives:* UOL super-voting control; the stated EPS-CAGR-above-
16% ambition runs *through* buybacks, and the buyback was just cut 25% in
favour of dividends — action against the stated incentive, which reads as
either discipline or capital capitulation; the deciding disclosure (20-F
Item 6.B) was NOT OBTAINED. No insider bought the +16% move (no Form 3/4/5
since 2026-08-01). *Disconfirming search:* ran on three fronts — the Selic
path (management's year-end assumption moved 12.5% → 13.75–14%), the
September 1 announcement (the dividend guide is a step-down), and the
election (absent from the call entirely) — all three cut against the bull.
*Moat as mechanism:* banking principality is a real mechanism, not a label,
and both of its legs are measurably weakening — the active banking base is
shrinking 2.7%/yr and the deposit-cost lever is exhausted at 83% of CDI by
management's own account.

**Statistical checks:** not applicable — no backtest, screen or signal
underpins this thesis. Recorded finding instead: composite's one quantitative
annotation on PAGS, `sa_fcf_yield` 37.75%, is the receivables artifact §4
rejects, and is scored 0 by design.

**Options timing check: NOT APPLICABLE and disclosed as such** — the bull
case makes no dated price-move claim, only dated disclosure claims. Coverage,
stated plainly: path 1 is structurally unavailable (PAGS is not in the CBOE
catalog, `options.db` has no rows), and path 2's chain FAILED the liquidity
gate (volumes 2 and 15, spreads 51–67% of mark, 14-point call/put IV
disagreement) — UNRELIABLE, context only, and it moved nothing.

**Closest attack:** ROE 14.53% against a Selic of 14.00%. A bank earning its
return on equity at the local risk-free rate is worth about book value, and
PAGS trades at 0.96× book — so the "6.6× earnings, 0.96× book" cheapness is
not cheapness, it is arithmetic. Everything above the hurdle in runs A, B and
D is a bet that Selic falls faster than the company's own revised assumption.
Second-closest: the +7.7% session on September 2 repriced the stock on an
announcement whose dividend line was 29% *lower* than the current-year plan.

**Flip evidence:** SOUND if the 2026-11-11 Q3 print shows gross profit ≥ +8%
y/y, NPL90 ≤ 3.5%, active banking clients flat-or-up and a BIS ratio ≥ 21%.
FLAWED if NPL90 > 4.5%, or gross-profit growth < 3% with the FY guide
withdrawn, or a BIS ratio < 19% alongside a 2027 dividend guided below
R$1.0B.

**p(beat SPY, 63 td): 0.42** — written before re-reading §1. A coin-flip
election and a 49.5% ATM IV inside the window, against a rate-cutting cycle
that has genuinely begun and a multiple that is hard to compress much
further.
