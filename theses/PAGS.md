# PAGS — PagSeguro Digital (PagBank) — 2026-10-18

Price $11.00 (official close, 2026-10-16) · market cap $3,032.1M · next
earnings 2026-11-16 AMC (broker-verified; moved from the tentative 11-11)

Unattended scheduled run. Held position (composite `portfolio_holding`
1.183, snapshot 2026-10-15); supersedes `research/PAGS-2026-09-13.md` (PASS
at $10.12, UNPROVEN). That thesis's reopen trigger has not formally fired
(the Q3 print is still ahead), but its price leg did: PAGS closed **$8.80–9.09
on eight sessions, 2026-09-23 → 10-02**, under the ~$9.10 flip level, and no
run was dispatched before the 2026-10-05 election gap took it back above
$10.9. Composite has never flagged PAGS on its own signals (score 0/0,
coverage 0.0; `sa_fcf_yield` 32.71 and `sa_fscore` 6.0 are annotations scored 0).

## 1. Verdict and thesis

**PASS at $11.00.** kill-thesis: **UNPROVEN** — conditions=6 (2 probable,
4 plausible), refuted=0, unknown=1, pending=3, not_obtained=0.

**p(beat SPY, 63 td): 0.44** · kill-thesis: 0.42 · **Disputed expectation:**
at $11.00 the market prices PAGS's flat USD earnings through a post-election
Brazil regime: flat-USD earnings clear the 14.36% hurdle by +76bp, or +115bp
at the post-first-round BRL. The *observed* two-year path (BRL earnings flat)
misses it by **−178bp**. Prediction markets give Flávio Bolsonaro 76–79%
odds, so a Bolsonaro runoff win (2026-10-25) is already mostly in the price.
A Lula win, or a Q3 print (2026-11-16) without the H2 gross-profit
acceleration, forces the revision down.

The business has not changed since 2026-09-13. No print, no 6-K and no
guidance change has landed since. What has changed is the price (+8.7%, $10.12
→ $11.00), and nearly all of that move came in one session: **+21.4% on
2026-10-05** (9.02 → 10.95, 18.8M shares against a ~3M norm), the Monday after
a first round that put Flávio Bolsonaro ahead of Lula, 47.0% to 45.2%. That
was a re-rating of Brazilian country risk, not news about PagBank. At $11 the
only scenarios that clear the hurdle need USD earnings to hold flat or grow.
The two that extrapolate what the company has actually done (BRL earnings
flat) or a modest fade fail by 178–224bp, wider than in September. Two
pieces of insider evidence lean the same way. A director filed to sell his
entire holding into the rally. The founder-controller left the chair in
August, a 6-K the prior run did not record. This is again a "the entry price
is gone" call. The cheap window ($8.80–9.09) came and went between runs.

**Closest attack:** ROE 14.53% against a Selic of 13.75%. A bank earning
roughly the local risk-free rate is worth about book, and PAGS now trades at
1.05× book (up from 0.96× in September). The 2026-10-05 gap repriced the stock
from below book to above it on an election poll, not on earnings. The runoff
is a statistical tie in polls (Datafolha 51/49 valid votes, 10-15; CNT/MDA
50.5/49.5, 10-16), so the market has paid in advance for an outcome the polls
cannot yet call.

Load-bearing conditions of the **bull** case (the case for owning PAGS at
$11.00): **six**, two probable and four plausible. The election and BRL
regime is an exogenous policy/currency input and sits in §4 as a scenario,
not a condition.

1. *probable* — **BRL net income does not decline over the forecast window.**
   FY2024 R$2,116M → FY2025 R$2,118M → TTM R$2,151M (stockanalysis, TTM
   through Q2'26; no new quarter since). Flat nominal BRL is a real
   decline, and §4 run E shows that path fails the hurdle.
2. *plausible* — **FY2026 gross profit grows 6–9% y/y**, i.e. H2 accelerates
   to ~+10% from H1's +2%. Settled by the Q3 print, 2026-11-16, and the FY
   print (2027-03-03, tentative).
3. *plausible* — **the credit book's loss curve stays inside current
   provisioning** as the unsecured share (24.3%) rises. The Q3 NPL90 /
   credit-loss table (2026-11-16) is a reading. The through-cycle curve is
   UNKNOWN (§6.1).
4. *plausible* — **capital return continues at the guided level without an
   equity raise** on the 22.5% → 18% Basel glide. Settled by the Q3 BIS ratio
   (2026-11-16) and the 2027 dividend declaration (Q1 2027).
5. *probable* — **the take rate holds at ~1.5% gross profit / TPV.** It was
   exactly 1.5% in Q2'26 and in Q2'25 (6-K 0001554855-26-001793).
6. *plausible* — **the active-client decline (−3.3% y/y) does not become a
   revenue decline.** Settled by the Q3 client table, 2026-11-16.

**Dominant shared risk factor:** Brazilian policy-rate and currency regime
(Selic level plus BRL/USD, now carrying the 2026-10-25 runoff) — shared by 1
of 24 other held names (TIMB) · 0 unlabelled. Holdings come from
`composite.db` `in_portfolio` rows (snapshot 2026-10-15), not
`portfolio.db`, because the headless slot has no grant for it. TIMB is a new
holding since the prior run. Its line ("Brazilian macro — the BRL/USD path
and the Selic/IPCA indexation channel") fails in exactly this scenario, so
the book now holds two names that fall together on a BRL shock. PYPL and EEFT
remain non-matches, as in the prior run.

## 2. Business

Unchanged from `research/PAGS-2026-09-13.md` §2. There has been no new
quarter since. The figures below are the Q2'26 release (6-K
0001554855-26-001793), carried.

- **Created:** payments acceptance (POS / Pix / cards) plus a full digital
  bank for Brazilian micro/SMB merchants and consumers. 34.1M total clients
  (+3.1%), deposits R$42.8B (+15.1%). Engagement denominators are shrinking:
  active clients 17.1M (−3.3%), active banking 16.9M (−2.7%), banking-only
  10.9M (−5.0%).
- **Captured:** four mechanisms: (i) acquiring MDR on R$133.4B quarterly TPV;
  (ii) the prepayment spread on the R$52.4B receivables book; (iii) deposit
  float at 83.3% of CDI; (iv) lending NIM on the R$5.1B credit book plus
  banking/insurance/investment fees. Gross profit holds at 1.5% of TPV.
- **Protected:** no moat in acquiring, which is a commodity terminal against
  Stone, Mercado Pago and CloudWalk. Banking principality (cheap on-platform
  deposits plus transaction-history underwriting) is a real mechanism and is
  weakening on both legs. The active banking base is shrinking, and
  management says deposit cost stabilises "around these low 80s". Valuation
  assumes excess returns fade.
- **Control:** UOL / founder Luis Frias holds super-voting control through
  a dual-class structure. **New:** Frias resigned as Director and Chairman
  effective 2026-08-21 after nine years. Maria Judith de Brito, an existing
  director, is Chairman, and Eduardo Alcaro remains Vice-Chairman. The 6-K
  states Frias "will continue as the Company's indirect controlling
  shareholder" (6-K 0001554855-26-001913). The board is 7 members, 3
  independent. Takeover and activist paths remain foreclosed. The change
  moves the controller from the chair to the shareholder register and does
  not change the vote.

**Operating leverage (Phase 0): positive at the operating line, flat at the
bottom line, and the gap is the Selic.** (BRL millions; stockanalysis, TTM
through Q2'26; no new quarter since the prior run.)

| | 2021 | 2022 | 2023 | 2024 | 2025 | TTM |
|---|---|---|---|---|---|---|
| Revenue | 10,299 | 15,159 | 15,680 | 18,334 | 19,743 | 19,804 |
| Operating income | 2,122 | 5,073 | 5,385 | 5,959 | 7,412 | 7,478 |
| Operating margin | 20.6% | 33.5% | 34.3% | 32.5% | 37.5% | 37.8% |
| Net income | 1,166 | 1,505 | 1,654 | 2,116 | 2,118 | 2,151 |

Revenue rose +92% since 2021 and operating income +252%, which is genuine
positive operating leverage. Net income rose only +84%. Interest expense
(TTM −R$4,903M) absorbs the operating gain, and the bottom line has been flat
for two years.

## 3. Threads pulled

- **The 2026-10-05 gap: the thread that explains the price.** Robinhood
  daily bars: 10-02 close 9.02 → 10-05 open 10.30, close 10.95, volume
  18,829,081 (the 30-day average is 4.49M). The trigger was the first round
  on 10-04. Flávio Bolsonaro (PL) took 47.0% and Lula (PT) 45.2%, and PL won
  the largest blocs in both chambers (low-confidence: Washington Post,
  Wikipedia, Rio Times). The BRL strengthened from ~5.21 to ~5.03/USD by
  10-13 (low-confidence: Rio Times). Nothing company-specific was filed on
  or near that date. The EDGAR index shows no 6-K after 2026-09-01. This was
  a Brazil-beta move on a 1.24-beta, single-country stock. **Runoff
  2026-10-25.** Polls are a technical tie: Datafolha 10-15 51/49 valid,
  CNT/MDA 10-16 50.5/49.5, Veritá 10-17 51.1/48.9. Polymarket is 76–79%
  Flávio (low-confidence; these are bets, not polls). The stock has held
  $10.51–11.16 since the gap. The market has not given back the first-round
  move ahead of a runoff the polls cannot call.
- **Insider selling into the rally: the new adverse thread.** Director
  Alexandre Magnani filed Form 144 on 2026-10-09 (0001554855-26-002102) for
  **507,390 Class A shares, his entire holding** (207,390 personal plus
  300,000 via Carcara Investments Ltd., which he controls), aggregate $5.42M
  through Merrill Lynch. The shares were acquired as "employee compensation
  awards" between 2022-01-31 and 2026-01-30. Form 4s show the sales:
  100,000 at $10.60 on 10-07 (0001554855-26-002100), then 300,000 at $10.95
  wtd. avg. ($10.735–11.16) on 10-09 and 35,677 at $11.20 on 10-12
  (0001554855-26-002109). That is **435,677 sold of ~607,390 held before
  10-07 (~72%)**: 335,677 of the 144's 507,390 so far, with 171,713 left. Neither Form 4 extract showed whether the
  10b5-1 box was checked. The compensation-award provenance fits a current
  or former executive monetising vested pay, which is a weak signal on its
  own (insider sales are weakly predictive; purchases are the informative
  side). It still cuts one way: a board member with full information chose
  to sell everything at $10.60–11.20, and no insider has bought since the
  July Form 4 recorded in the prior thesis.
- **The chair change: a miss carried from the prior run.** The 2026-08-21
  6-K (Frias resigns as chair, stays controller) predates the 2026-09-13
  thesis, which did not record it. It is recorded now in §2. Read alongside
  Magnani's exit, the board has lost its founder-chair and a long-tenured
  insider has fully divested within two months. That is not evidence of a
  problem, but it is what a reader would want to know before relying on
  controller continuity (§6.5).
- **Selic.** Copom cut 25bp to **13.75%** on 2026-09-16 (BCB statement, 281st
  meeting), the fifth consecutive cut. The next decision is **2026-11-04**,
  and the Focus consensus is 13.50% (low-confidence: secondary press). This
  is in line with management's revised year-end assumption of 13.75–14% (Q2
  call), not ahead of it. The easing is reaching the curve on schedule and
  gives no surprise tailwind.
- **Latest call: carried, not re-read.** The most recent transcript is still
  Q2 2026 (2026-08-11). The prior run read it in full (guidance GP +6–9%,
  "probably not by the top of the range"; refusal to give product-level NPL;
  "too early to discuss 2027"). No call, letter or 6-K has been released
  since, so silence since the call is the reading.
- **Earnings-estimate pattern (broker tier).** Unchanged: five hair-thin
  beats Q4'24–Q4'25, then misses in Q1'26 (0.39 vs 0.40) and Q2'26 (0.388 vs
  0.40). The Q3'26 estimate is 0.41, reported **2026-11-16 AMC (verified)**.
  The date moved five days later than the prior thesis's tentative 11-11,
  and the reopen date moves with it.
- **Sell-side colour.** Consensus target $11.52 (+4.7%), 16 analysts, "Buy"
  (stockanalysis). Short interest is 17.34M shares, 11.45% of shares out
  (stockanalysis). That is high for a 7.6× P/E bank and a crowded short into
  a binary runoff, which cuts both ways. A Seeking Alpha piece (10-07,
  low-confidence) calls loan-book growth the main risk, which matches
  condition 3.
- **Options read (mandatory):** path 2 only (Robinhood stopgap). PAGS is not
  in the CBOE catalog and `data/options.db` has no PAGS rows. Table,
  liquidity verdict and timing applicability are in §4.
- **Dead ends.** `earnings.db` `v_upcoming_earnings` has no PAGS row; the
  date came from the broker tier. `sec_fundamentals.db` still carries only
  assets and liabilities (FPI on IFRS), not an income statement. The PagBank
  IR press room's only item since September is a 2026-10-06 investment-
  product launch (low-confidence: search summary), which is not material.
  Damodaran's home page was not reachable through WebFetch (frameset), so the
  September 1 implied-ERP vintage is not refreshed. The country table used
  for the hurdle is unchanged (January 5, 2026). Robinhood's
  `shares_outstanding` (277.5M) disagrees with stockanalysis (275.65M). The
  stockanalysis figure is kept for consistency with the prior run's market
  cap, and the 0.7% gap moves no conclusion.

## 4. Valuation

**Inputs and pairing.** The pairing is unchanged from the prior run, and so
is the refusal of stockanalysis `fcf`. That `fcf` is TTM $1.01B (a ~33%
"yield", the `sa_fcf_yield` annotation composite carries). It is the
receivables/deposit artifact of a prepayment bank, and `leveredFCF` on the
same period is negative. The base is **TTM GAAP net income $415.21M**
(stockanalysis USD conversion of R$2,151.1M at ~5.18), paired with **market
cap $3,032.1M** ($11.00 × 275.646M shares); net debt 0 by the pairing rule.
SBC is $24.29M (0.64% of revenue; stocks.db) and is already charged in GAAP
income, so there is no further haircut. There is no minority interest. Run F
reconverts the same BRL earnings at the post-first-round spot (~5.03,
low-confidence press level), giving **$427.6M**.

**The leverage gate does not fire.** Book equity is R$15.0B against R$1.7B of
reported debt. Liabilities are deposits and merchant payables, there is no
going-concern language, and the DCF frame governs §1. `equity_option` was
not run.

**Hurdle:** rf **5.10%** (`DGS10`, fred.db, 2026-10-15) + beta **1.24**
(stockanalysis 5Y, live; stocks.db 1.244) × Brazil **total ERP 7.47%**
(Damodaran `ctryprem.html`, January 5, 2026 vintage; ~100% Brazilian revenue)
= **14.36%**. Beta is just above the 0.8–1.2 band. No clamp is applied,
because flooring upward would be a free pass. The figure sits far outside
the US cost-of-capital band (median ~7.8%), as expected for a single-country
Brazilian issuer.

**Terminal-growth ceiling: 2.35%**, the 10-year breakeven (`T10YIE`,
fred.db, 2026-10-16). The flow is USD-converted BRL earnings, so US
inflation is the zero-reinvestment growth rate in USD.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A flat USD earnings | $415M | 0%/yr | 2.35% | **~15%** | **+76bp** |
| B mgmt-path | $311M (75% of NI retained-growth) | +8%/yr | 2.35% | **~15%** | **+105bp** |
| C melt | $415M | −3%/yr | 0% | **~12%** | **−224bp** |
| D enacted-tax drag | $386M (NI −7%) | 0%/yr | 2.35% | **~14%** | **−15bp** |
| E observed path (BRL flat) | $415M | −2.1%/yr | 0% | **~13%** | **−178bp** |
| F flat at spot BRL ~5.03 | $428M | 0%/yr | 2.35% | **~16%** | **+115bp** |

Whole percents only: ATM IV is ~72%. Exact solver outputs, for the record:
A 15.13%, B 15.41%, C 12.12%, D 14.22%, E 12.59%, F 15.52%.

**Read against September.** At $10.12 the spreads were A +183, B +207,
C −123, D +84, E −74. The 8.7% move cost ~100bp across the board, and the
tax-drag case now fails too. Three of six scenarios fail, and the three that
clear need USD earnings at least flat in perpetuity. Run F is the
election-regime case: it clears by 115bp only if the BRL holds its
post-first-round gain. Prices at which the conservative cases re-clear: the
melt case at ~$9.30 ($9.10 → +36bp) and the observed path at ~$9.70 ($9.50 →
+25bp). Both traded at the late-September/early-October lows.

**Integrity checks.**

- **Reinvestment warning, answered.** Runs A, D and F trip `growth without
  reinvestment` (base FCF = base earnings, terminal growth 2.35%). As before,
  2.35% is the USD-inflation repricing of existing assets and needs no
  reinvestment. Real growth beyond it would. Actual payout is ~90% of net
  income. A first pass of run D paired the haircut FCF with *unhaircut*
  earnings and printed a 33.5% terminal ROE. That is an artifact of
  mismatched bases, and the rerun with consistent earnings is what the
  table quotes.
- **Implied terminal ROE.** Run B prints 9.40%, below the 14.36% hurdle,
  which means value-destroying retention in the terminal period. That is
  deliberate and matches the ~29% base rate of firms earning above their cost
  of capital (Damodaran EVA).
- **Market-share sentence.** Run B's +8%/yr takes USD earnings to ~$460M of
  FCF (~$610M NI) by 2031. PagBank holds ~10% of Brazilian acquiring TPV and
  under 1% of most banking verticals, so the path does not need a
  bigger-than-the-market share. The company's own 2029 credit ambition
  (R$5.1B → R$25B) is the aggressive number, and it is in no run.
- **Cash tax.** TTM effective tax is 17.3% against a statutory rate rising
  to 37% (2026–27) and 40% (2028+) under LC 224/2025 (20-F FY2025, carried).
  Run D prices the drag and now fails.
- **Terminal risk.** The 20-F risk factors name Pix displacing card economics
  and the enacted tax escalation (carried). A 0–2.35% terminal range
  survives them only because no run assumes real growth.
- **Serial-acquirer / cash-heavy clamps:** not applicable (no acquisition
  spend; cash R$1.4B of R$75.7B assets).
- **The exogenous input: the runoff.** BRL/USD and Brazil country risk are
  scenario inputs. The 10-25 runoff is the dated event. A Bolsonaro win is
  ~77% priced by prediction markets, so its upside is mostly spent, and run
  F is roughly that state. A Lula win plausibly unwinds the first-round move
  (the stock gapped 21% on it). At BRL back at ~5.2 and a re-widened country
  premium, the flat case reverts to run A or worse while the price falls
  toward the pre-election $9. Neither outcome is a condition. It is the
  reason the 63-day probability sits near 0.4.

**Options-implied move — path 2 only (Robinhood stopgap).** PAGS is not in
the CBOE catalog and `data/options.db` has no PAGS history, so path 1 is
structurally unavailable. Expiry **2026-11-20, 33 DTE** (from 2026-10-18),
strike 11.0 ATM. It brackets the runoff (10-25), the Copom decision (11-04)
and the Q3 print (11-16 AMC). ATM IV is the mean of the put's 69.09% and the
call's 74.48% (marks 10-16 close). Realized vol was computed by hand from
Robinhood daily closes (log returns, ×√252). Both windows contain the 10-05
gap (+19.4% log), so ex-gap figures are given beside them.

| metric | value |
|---|---|
| spot | 11.00 |
| expected absolute move (straddle/spot; MEAN, not a ceiling) | 17.0% |
| 1-σ move | 21.6% |
| ATM IV | 71.8% |
| RV60 | 52.6% (34.6% ex-gap) |
| RV20 | 75.5% (30.9% ex-gap) |
| IV > RV60? | YES |
| IV > RV20? | NO (incl. gap) / YES (ex-gap) |

IV jumped from 49.5% (prior run, 68 DTE) to ~72% (33 DTE) against ~31–35%
ex-gap realized vol. The options market is pricing the runoff-plus-print
window as a second gap-sized event. That is consistent with a binary vote,
and it is not a discovery.

**Liquidity gate: FAILED → UNRELIABLE.** Put volume 0 (OI 40), call volume 70
(OI 2,893), both under the 100 floor. Spreads are $0.45 on a $0.875 put mark
(51%) and $0.30 on a $1.00 call mark (30%), against a 10% gate, with a
5-point call/put IV disagreement. The table is context only.

**Timing check: NOT APPLICABLE.** The bull case's dated claims are
disclosures (the 11-16 print), not price moves.

## 5. Falsifiers

**For the pass (flip toward buy):**

- **Shift —** price at or below **~$9.30**, where run C (the −3%/yr melt)
  re-clears the hurdle. At ≤ ~$9.70 the observed path re-clears. Both
  traded on 2026-09-23 → 10-02, and a Lula runoff win would likely revisit
  them.
- **Shift —** Q3'26 gross profit **≥ +8% y/y** with financial costs down
  ≥ 5% y/y, confirming the H2 acceleration the FY guide needs.
- **Shift —** active banking clients flat or up y/y at Q3.
- **Shift —** BIS ratio **≥ 21%** at Q3, with the 2027 dividend at or above
  R$1.2B.

**For an owner (sell):**

- **Break —** NPL90 past **~4.5%**, or credit-loss allowance expense above
  ~15% of quarterly gross profit (3.5% at Q2).
- **Break —** gross profit / TPV decisively below 1.4%, or the FY
  gross-profit guide withdrawn.
- **Break —** an equity raise, or a 2027 dividend below R$1.0B with BIS
  under 19%.
- **Shift —** BRL/USD beyond ~6.00 without a BRL-earnings response (a Lula
  runoff win is the dated path to a weaker real).
- **Shift —** further full-stake insider exits, or a controller-level
  transaction by Frias/UOL after his chair resignation. Revalue the
  controller-continuity assumption.
- **Shift —** effective tax above ~30%, or a Selic re-tightening.

**Reopen trigger:** 2026-11-16: `pags-q3-26-print-gp-growth-ge-8pct-npl90-le-3-5pct-active-banking-flat-or-up-bis-ge-21pct-or-price-le-9-30`

## 6. UNKNOWNs

1. **UNKNOWN — the through-cycle loss rate of the unsecured book.** No
   filing carries it. The working-capital and card vintages are under two
   years old, and management refuses product-level disclosure (Q2 call, to
   HSBC). It is load-bearing on condition 3, which is why the verdict is
   UNPROVEN. At $11 the flat case's cushion is 76bp, so a bad unsecured
   vintage turns run A into run C.
2. **UNKNOWN — the industry NPL comparison** (management: 3.4% vs a market
   average of 6.2%). It needs BCB series the repo does not ingest. This is
   the third consecutive run it is unverified.
3. **PENDING 2026-11-16 — the Basel trajectory** (29.6% → 22.5% in a year,
   4.5pp above the company's 18% floor). The Q3 ratio will show whether the
   glide is managed or consumed.
4. **NOT OBTAINED — management compensation metrics** (20-F FY2025
   0001554855-26-000826, Item 6.B). This run did not read them. They would
   show whether the EPS-CAGR >16% ambition is an incentive target. It is not
   attached to a numbered condition and not counted.
5. **UNKNOWN — controller intentions after the chair change.** Frias left
   the chair (2026-08-21) and stays the indirect controller. He has no
   obligation to disclose plans before the fact. A director's full-stake
   144 within seven weeks makes this harder to wave away than in September,
   but it is still unresolvable from filings.
6. **UNKNOWN — Magnani's current or former executive role and 10b5-1
   status.** The Form 144 says the shares are compensation awards from
   2022–2026. The Form 4 extracts did not show the plan checkbox. That
   changes how informative the sale is, not any condition.

Option value (*possible* tier, unnumbered): a runoff outcome that compresses
Brazil's country premium durably, *and* a Selic path below the 13.50%
consensus, would lift every run in §4 at once. It cannot be dated beyond
10-25 / 11-04 or sized, and prediction markets already price most of the
first leg.

## 7. Sources

- **Primary:** (SEC, EDGAR CIK 0001712807) Form 144 2026-10-09
  (0001554855-26-002102: 507,390 shares, $5.42M, compensation awards
  2022–2026, prior 3-month sale of 100,000) and the 2026-10-07 144
  (0001554855-26-002077, index only); Form 4 2026-10-09
  (0001554855-26-002100: 100,000 at $10.60 on 10-07); Form 4 2026-10-13
  (0001554855-26-002109: 300,000 at $10.95 on 10-09 via Carcara, 35,677 at
  $11.20 on 10-12, 171,713 held after); 6-K 2026-08-21
  (0001554855-26-001913: Frias resigns as chair, stays indirect controller,
  Brito appointed); 6-K 2026-09-01 and 6-K 2026-08-11 Q2 release (carried);
  EDGAR filing index (no 6-K after 2026-09-01). Q2 2026 call transcript
  (2026-08-11; primary-transcribed via stockanalysis; carried, not re-read).
  20-F FY2025 (carried). BCB Copom statement, 281st meeting (Selic 13.75%,
  2026-09-16).
- **stockanalysis.com (vetted exception):** `/stocks/pags/statistics/`
  (WebFetch, 2026-10-18): market cap $3.03B, EV $3.11B, P/E 7.60, forward
  6.05, P/B 1.05, ROE 14.53%, beta 1.24, FCF $1.01B, net income $415.21M,
  shares 275.65M, target $11.52 / 16 analysts, short interest 17.34M
  (11.45%). Income-statement history carried from the prior run.
- **Broker/market microstructure:** (Robinhood MCP) official close $11.00
  (2026-10-16); fundamentals (P/B 1.045, 30-day average volume 4.49M,
  52-week 8.42–12.32); daily bars 2026-07-10 → 10-16 (the 10-05 gap, RV20/
  RV60); earnings estimate/actual for eight quarters and the verified
  2026-11-16 PM date; option chain and 2026-11-20 $11 put/call quotes.
  Admissible: no integrated official source covers PAGS quotes, options or
  consensus, and `earnings.db` has no PAGS row.
- **Reference data:** Damodaran `ctryprem.html` (January 5, 2026): Brazil
  Ba1, CRP 3.24%, total ERP 7.47%. US cost-of-capital distribution and the
  ~29% EVA base rate (anchors reference, carried).
- **Point-in-time repo DBs:** `fred.db`: DGS10 5.10% (2026-10-15), T10YIE
  2.35% (2026-10-16). `stocks.db` latest: beta 1.244, insiders 3.64%,
  institutions 46.25%, float 140.95M, shares 275.65M, SBC $24.29M, SBC/rev
  0.64%, 16 analysts. `composite.db` snapshot 110: PAGS score 0/0,
  `in_portfolio`=1, `portfolio_holding` 1.183, plus the 25-name holdings list
  used for the overlap count. `earnings.db`: no PAGS row.
  `sec_fundamentals.db`: assets/liabilities only.
- **Low-confidence:** election results and runoff polls (Washington Post,
  Wikipedia, Rio Times, AS/COA), Polymarket odds, BRL/Ibovespa levels (Rio
  Times, Latin Times), the Focus Selic consensus and the 2026-11-04 Copom date
  (ricoaospoucos), the Seeking Alpha 10-07 piece, PagBank IR press-room
  search summary. None of these carries a numbered condition.

## Kill-thesis record

**UNPROVEN** — conditions=6, refuted=0, unknown=1, pending=3,
not_obtained=0. (Survived=2. The drafted seventh condition, "the regime the
10-05 gap priced survives the runoff", was moved to §4. It is an exogenous
policy/currency input, and the condition it hid, that the price clears the
hurdle on the stated path, is what §4's table attacks directly.)

Per-condition adjudication of §1's **bull-case** list:

1. **SURVIVED** (*probable*) — BRL net income flat for two years. There is
   no new quarter to attack it with. The attack that lands is on the frame,
   not the condition: flat BRL is run E, −178bp.
2. **PENDING 2026-11-16** — FY26 gross profit +6–9%. H1 was +2%, so H2 must
   reach ~+10%. The Selic path is exactly management's revised 13.75–14%
   assumption with no upside surprise, and the ~R$60M/q financial-cost
   relief that buys reaches the bottom of the range, not obviously the
   middle. Guidance was reaffirmed and nothing since contradicts it, so it
   is not refuted.
3. **UNKNOWN** — the loss curve inside provisioning. Credit-loss allowance
   expense is +150% against a book +30.7%, unsecured credit has gone from
   13.1% to 24.3% of the book, and management refuses product-level
   disclosure. The base rate for rapidly extended unsecured credit to
   thin-file borrowers is poor. The Q3 print (11-16) gives one more reading,
   but the through-cycle curve that decides it is in no filing (§6.1).
4. **PENDING 2026-11-16** — capital return without a raise. The internal
   inconsistency stands (49%/yr credit growth to the 2029 ambition, ~90%
   payout, BIS −7.1pp/yr). The board's 2027–28 dividend step-down (R$1.4B →
   R$1.0B floor) keeps it alive.
5. **SURVIVED** (*probable*) — take rate at 1.5%, flat y/y. The cost of
   holding it is ceded volume (TPV +3.0%).
6. **PENDING 2026-11-16** — active-client decline does not reach revenue.
   Revenue was +0.4% at Q2. It is adverse but not refuted.

**Standing checks.** *Base rate:* ~29% of firms out-earn their cost of
capital (Damodaran EVA). An EM bank with ROE ≈ local risk-free is worth about
book, and it now trades above book. Rapid unsecured extension usually ends
badly. Insider *sales* carry little predictive information on average, so
Magnani's exit is weighted lightly. *Short case:* a commodity acquirer on a
shrinking active base, levered to unsecured credit underwritten in one
benign cycle, trades above book after a 21% one-day gap on a first-round
poll lead. The runoff is a polling tie, a director just sold his whole
stake into the move, the founder left the chair, statutory tax steps to 40%
by 2028, and 11.45% of shares are short. *Management incentives:* the
EPS-CAGR >16% ambition runs through buybacks while the buyback shrank (20-F
Item 6.B NOT OBTAINED). A director monetising compensation awards in full is
action consistent with "the price is full". *Disconfirming search:* run on
the election (the polls are tied while the price assumes a win), Selic (on
schedule, no surprise) and insiders (sales only). All three cut against the
bull. *Moat as mechanism:* banking principality is real and weakening on
both legs, as in September.

**Statistical checks:** not applicable. No backtest or signal underpins the
thesis. Composite's `sa_fcf_yield` 32.71% is the receivables artifact §4
rejects and is scored 0.

**Options timing check: NOT APPLICABLE and disclosed.** The bull case has no
dated price-move claim. Coverage: path 1 is unavailable (not in the CBOE
catalog), and path 2 FAILED the liquidity gate (volumes 0 and 70, spreads
30–51% of mark), so it is UNRELIABLE and moved nothing.

**Closest attack:** P/B rose from 0.96 to 1.05 on an election poll while ROE
(14.53%) still roughly equals the Selic (13.75%). The stock paid in advance
for a runoff outcome that the polls call a tie. On the company's own
observed earnings path, the price fails the hurdle by 178bp.

**Flip evidence:** SOUND if the 11-16 print shows GP ≥ +8%, NPL90 ≤ 3.5%,
active banking flat-or-up and BIS ≥ 21%, *and* a further quarter of loss data
narrows §6.1. FLAWED if NPL90 > 4.5%, GP growth < 3% with the guide
withdrawn, or BIS < 19% with a 2027 dividend below R$1.0B.

**p(beat SPY, 63 td): 0.42** — written before re-reading §1. The window
holds a tied runoff (where the favoured outcome is mostly priced and the
unfavoured one is a ~20% gap risk), a print that has to show acceleration
after two misses, and a 72% IV. Against that, there is a rate-cutting cycle
and a 7.6× P/E that limits multiple downside if the vote breaks right.
