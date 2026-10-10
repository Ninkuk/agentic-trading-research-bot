# BCAX — Bicara Therapeutics Inc. — 2026-09-28

Price $18.80 (official close, 2026-09-28) · market cap $1.24B (stockanalysis
lookup; $1.29B on basic + pre-funded shares) · EV ~$0.78B · net cash $496.1M
(6/30/26) · next earnings 2026-11-09 BMO (unverified per broker; absent from
`earnings.db`)

Entry path: composite flag (snapshot 90: `si_days_to_cover` +2 at 22.08 days,
`stocks_rsi` +1 at 28.7; 2 of 11 signals). Unattended scheduled run.

## 1. Verdict and thesis

> **PASS at $18.80.** kill-thesis: **SOUND** (on this pass) — conditions=4
> (1 probable, 3 plausible), refuted=0, unknown=0, pending=3, not_obtained=0.

**p(beat SPY, 63 td): 0.42** · kill-thesis: 0.40

**Disputed expectation:** at $18.80 the market prices roughly a coin flip
that FORTIFI-HN01's mid-2027 interim supports accelerated approval (success
value ~$2.5B vs ~$0.28B cash floor, §4); Genmab's LiGeR-HN1 topline in Q4 2026
is the first randomized read on the class and revises that probability before
Bicara's own data does.

Phase 0 kills this as a fast kill: Bicara is a pre-revenue, single-asset
clinical biotech with an operating loss of $202.0M TTM that has roughly
doubled every year, so there is no cash flow to discount and the reverse DCF
refuses. The unattended run could not ask whether to go on, so it went on far
enough to price the bet honestly. What the price buys is a binary readout:
ficerafusp alfa (EGFR × TGF-β bifunctional antibody) plus Keytruda in
first-line HPV-negative head and neck cancer, interim topline mid-2027. The
balance sheet is clean and funds the readout; the question is the probability
of success, which rests on oncology science this skill cannot evaluate, and
the payoff lands outside the 63-trading-day horizon. That makes it a pass, not
a short: nothing here is refuted, it is unassessable.

**Closest attack:** petosemtamab (Genmab, $8.0B Merus deal) chases the same
1L PD-L1+ HNSCC population on the same pembrolizumab backbone, reads out
~6–9 months earlier (LiGeR-HN1 topline guided Q4 2026) and posted a higher
early ORR (67% vs ficerafusp's 54%, cross-trial, different follow-up) — so
even on success Bicara is likely second to market against a better-funded
incumbent.

Bull-case load-bearing conditions (4):

1. FORTIFI-HN01's interim analysis shows benefit sufficient for accelerated
   approval — *plausible*: Breakthrough Therapy designation and phase 1b data
   (ORR 54%, mOS 21.3 mo, 2-yr OS 46% in HPV-neg 1L) exist; the decisive
   disclosure is the interim topline, guided "mid-2027" (Q2'26 8-K).
2. Ficerafusp's randomized efficacy is at least competitive with
   petosemtamab's in the same setting — *plausible*: settled cross-trial by
   LiGeR-HN1 topline (Genmab guidance Q4 2026) plus the FORTIFI interim
   (mid-2027); no head-to-head will ever run.
3. Cash funds the company through the readout without a raise at a depressed
   price — *probable*: $497.3M cash + securities at 6/30/26 vs H1'26 operating
   burn of $81.7M; runway guided "into first half of 2029" (Q2'26 8-K / 10-Q).
4. The success-case equity value is ≥ ~$2.5B (what the price needs at p=0.5
   to clear the hurdle, §4) — *plausible*: Genmab paid $8.0B for the lead
   EGFR-bispecific in this indication and projects ≥$1B sales by 2029; a
   second entrant's value depends on the readout magnitude (same dates as 1–2).

**Dominant shared risk factor:** idiosyncratic

## 2. Business

**Created:** a first-line add-on to Keytruda for recurrent/metastatic
HPV-negative head and neck squamous cell carcinoma, a population where
checkpoint therapy alone responds in a minority. Ficerafusp binds EGFR (a
validated target — cetuximab) and traps TGF-β in the tumour
microenvironment, which the company argues lets immune cells and the drug
penetrate the tumour. The patient gets, if the data hold, deeper and more
durable responses (phase 1b: ORR 54%, mDOR 21.7 mo, mOS 21.3 mo — JCO
two-year update). Whether the TGF-β arm adds anything that EGFR plus
pembrolizumab would not is exactly the biology this run cannot judge.

**Captured:** nothing today — no revenue in any period (stocks.db
`revenue` null; no `Revenues` fact in sec_fundamentals.db). On approval it
would capture value as a specialty oncology biologic: a per-dose price to US
infusion centres, reimbursed under Part B, over a treatment duration set by
progression-free survival. Ex-US would likely be licensed. There is one
mechanism and it does not yet exist.

**Protected:** composition-of-matter patents licensed from Johns Hopkins
(10-Q) and Breakthrough designation for the 1L PD-L1+ HPV-neg label. No moat
beyond patent and regulatory exclusivity on the molecule; the *indication* is
contested by at least two EGFR-directed bispecifics (petosemtamab/Genmab,
amivantamab/J&J), both with big-pharma commercial infrastructure.

**Control:** one class of common stock (DEF 14A, record date 2026-04-15:
65,600,370 shares); staggered three-class board; directors removable only for
cause by two-thirds. Biocon (Kiran Mazumdar-Shaw's company, founding
incubator) held ~10% post-IPO (low-confidence press; not verified against a
13D this run); Mazumdar-Shaw retired from the board July 2026 (8-K
2026-07-28). No controller, but the staggered board and for-cause removal
slow an activist and deter an unsolicited bid. Founder-CEO Claire Mazumdar
(Mazumdar-Shaw's niece, named in May 2026 as her eventual Biocon successor)
hands the CEO role to COO Ryan Cohlhepp on 2027-01-01 (Q2'26 8-K).

**Operating leverage (Phase 0): negative** — no revenue; operating loss
widening every year:

| year | revenue | operating income | op. cash flow |
|---|---|---|---|
| FY2023 | 0 | −$39.9M | −$45.6M |
| FY2024 | 0 | −$82.4M | −$74.8M |
| FY2025 | 0 | −$155.6M | −$106.8M |
| TTM 6/26 | 0 | −$202.0M | −$134.8M |

(EDGAR XBRL companyconcept; TTM from stocks.db, reconciles to the quarterly
sum −40.7 −41.1 −60.2 −60.0.) Q2'26 R&D $45.8M (+85% YoY), G&A $14.2M (+97%)
as the pivotal trial scales and the company builds pre-commercial staff
(employees 103, +87% YoY).

## 3. Threads pulled

- **Why the stock is down 38% from its July high ($30.99 → $18.80).** Three
  events: (a) 2026-08-11 Q2 print with a wider loss (−$0.82 vs −$0.81 est)
  and a full C-suite reshuffle — founder-CEO stepping to vice chair, new CFO
  immediately, new CEO 2027-01-01 — stock −14% that day (bars: $27.73 →
  $23.76); (b) steady insider selling — 125,500 shares / ~$3.5M in 90 days
  incl. incoming CEO Cohlhepp selling 17,500 at $22.90 on 2026-09-08 (Form 4
  2026-09-10; Form 144s 9/8, 8/10) — likely 10b5-1/tax, not verified; (c)
  2026-09-23 −10% ($22.78 → $20.49) on an HSBC downgrade to equal weight
  (MarketBeat, low-confidence; no 8-K that day). No clinical news explains
  the drawdown; the data have not changed since the May 2026 3-year OS
  update.
- **The CEO transition.** Framed as "next era of execution"; the plausible
  subtext is Claire Mazumdar's Biocon succession (May 2026 press). A founder
  leaving before the pivotal readout is a governance flag, not a data flag —
  she stays as vice chair and the new CEO is the internal COO. Read as
  neutral-to-mildly negative; not load-bearing.
- **Rival race (the load-bearing thread).** Genmab bought Merus for $8.0B
  ($97/sh, announced 2025-09-29) for petosemtamab; LiGeR-HN1 (~500 pts, 1L
  PD-L1+ HNSCC, petosemtamab + pembro vs pembro) topline guided Q4 2026,
  LiGeR-HN2 Q1 2027, launch targeted 2027 (Genmab conference commentary via
  Investing.com, low-confidence transcript summary). Petosemtamab 1L ORR 67%
  (95% CI 45–84%, n small, 3.6-mo follow-up) vs ficerafusp 54% (HPV-neg,
  25-mo follow-up). Amivantamab: 42% ORR in 2L+ post-IO/chemo HNSCC
  (OrigAMI-4, JCO 2026). Ficerafusp's interim is mid-2027 → Bicara is
  second into 1L. The LiGeR-HN1 readout inside the 63-td window is a
  two-sided class read-through: a win validates EGFR-bispecific + pembro
  (bullish for the mechanism, bearish for Bicara's share); a miss hurts
  both.
- **Dilution and cash.** Feb 2026 $150M follow-on at $16.00 (7.175M shares +
  2.2M pre-funded warrants at $0.0001, unexercised at 6/30); shares +36.5%
  YoY. Options outstanding 11.74M at $11.50 WAEP (7.91M unvested) — in the
  money, ~4.6M treasury-method shares at $18.80. Cash $497.3M ($96.6M cash +
  $400.7M securities) covers ~2.5–3 years at the rising burn. The 10-Q's
  going-concern paragraph is the standard "at least one year" language, not
  a doubt.
- **Commitments.** IQVIA CRO SOW (upfront $12.8M; $21.3M owed at 6/30);
  Syngene (Biocon affiliate) manufacturing and research agreements to
  2027–2031 ($2.7M H1 spend); new Boston sub-sublease from Wayfair,
  ~$105K/month to 2028-09-30 (8-K 2026-08-25). Related-party flow to Biocon
  entities is small (<$3M/half). Nothing here threatens the runway.
- **Earnings pattern (broker estimates vs SEC actuals).** 7 quarters: misses
  (larger loss) in 4, in line in 2, one beat. Actuals cross-check exactly
  against `sec_fundamentals.db` (Q1'25 −0.68, Q1'26 −0.93, Q2'26 −0.82). For
  a clinical biotech the miss pattern just means spend outran models —
  execution risk only in the budgeting sense.
- **Short interest.** 30.3% of float, 22.4 days to cover (stocks.db) — the
  composite flag. Shorts are positioned for a failed or late-comparison
  readout; on a positive rival read-through or clean interim this is fuel.
  Not a thesis.
- **Options read (mandatory):** path 2 only (BCAX is not in the 24-symbol
  CBOE catalog, so no path-1 history). Chain listed; ATM quotes fail the
  liquidity gate badly → UNRELIABLE. Table in §4.
- **Dead ends:** `earnings.db` has no BCAX row (next date from stocks.db /
  broker, unverified); no earnings-call transcript fetched — Bicara reports
  by press release and the stockanalysis probe could not be decoded in this
  sandbox (see §6); the July 2026 board 8-K added two directors and recorded
  Mazumdar-Shaw's retirement with no stated reason — nothing further; the
  Aug 2026 Item 1.01 was an office sublease, not a licensing deal.

## 4. Valuation

**Inputs and pairing.** `reverse_dcf` was run with the levered TTM FCF
−$135,248,000 (stocks.db, `ncfo + capex`) against market cap $1,244,051,159
and refused:

`refused: base_fcf must be positive, got -135248000.0` (exit 2)

There is no cash flow to discount until approval (2028 at the earliest), so
the honest substitute is a binary-outcome inversion: what success-case value
does today's price require? Equity at $18.80 on 68.37M basic + pre-funded
shares = $1,285M ($1,371M on ~72.9M fully diluted incl. treasury-method
options). SBC $22.2M TTM and the 11.7M-option overhang are carried by using
the basic+PFW count and noting the diluted figure. Cash at readout: $497.3M
less ~4 quarters at ~$50M (H1'26 averaged $41M and is rising) ≈ $297M;
failure value set at $275M (cash less wind-down; residual mCRC programme at
zero). Minority interest, pension, litigation: none.

**Hurdle:** rf 5.17% (DGS10, 2026-09-25) + beta 1.2 × ERP 4.14% (Damodaran
implied ERP, 2026-09-01) = 10%. Beta: stocks.db's headline `beta` is −0.82
on a two-year listing history, `beta2y` 1.39, `beta1y` 0.94 — clamped to 1.2.
Terminal-growth ceiling (10-yr breakeven, T10YIE 2026-09-28): 2.34% — unused,
no terminal value is solvable.

Required success-case equity value at the interim (~0.75 yr out) for today's
price to earn the 10% hurdle: `V = (1,382 − 275·(1−p)) / p`, where $1,382M is
$1,285M compounded at the hurdle.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| p(success)=0.35 | n/a (refused) | — | — | needs V ≥ $3.4B (~$50/sh) | — |
| p(success)=0.50 | n/a (refused) | — | — | needs V ≥ $2.5B (~$36/sh) | — |
| p(success)=0.65 | n/a (refused) | — | — | needs V ≥ $2.0B (~$29/sh) | — |

The Street median target of $35 (15 analysts, stocks.db) sits on the p=0.5
row — the market and the sell side both price roughly a coin flip. Anchor:
Genmab paid $8.0B for the class leader with phase-2 data; a second entrant at
$2–3.5B is not absurd, but whether p is 0.35 or 0.65 is the whole bet and it
rests on biology this run cannot assess.

- **Reinvestment/terminal-ROE warning:** not reachable — the solver refused
  at the base. No terminal claim is made.
- **Market-share sentence:** V ≈ $2.5B needs roughly $0.6–0.8B of peak sales
  at a 3–4× multiple — 60–80% of the ≥$1B Genmab projects for the first
  entrant by 2029. For a second-to-market drug in the same line that is a
  demanding share of a shared market, not a small one.
- **Terminal risk (Item 1A):** not swept this run (10-K NOT OBTAINED for
  Item 1A); the dominant structural risk is visible without it — single-asset
  dependence on one indication.
- **Distribution clamp:** n/a (no implied rate). Cash is 39% of market cap
  (`netCashByMarketCap` 39.0), so the enterprise the market pays for is
  ~$0.78B.

**Options-implied move — path 2 (Robinhood stopgap), ATM $20 strike.**
Expiry 2027-12-17 (445 DTE) brackets the mid-2027 FORTIFI interim; expiry
2026-11-20 (53 DTE) brackets the Q3 print and sits just ahead of LiGeR-HN1's
Q4 topline.

| metric | 2027-12-17 (445 DTE) | 2026-11-20 (53 DTE) |
|---|---|---|
| spot | 18.80 | 18.80 |
| expected absolute move (MEAN, not a ceiling) | 63.83% | 28.72% |
| 1-σ move | 81.13% | 34.79% |
| ATM IV | 73.48% | 91.30% |
| RV60 | 57.06% | 57.06% |
| RV20 | 48.26% | 48.26% |
| IV > RV60? | YES | YES |
| IV > RV20? | YES | YES |

Liquidity gate: **FAILED → UNRELIABLE.** Dec-2027 legs bid 3.50 / ask 8.50
on a $6.00 mark (83% spread), OI 30 and 0, volume 0; Nov-2026 legs bid
0.50 / ask 4.90 on $2.70, OI 0. The marks are model midpoints, not trades.
Read as "elevated" on both windows but the numbers may not move a verdict.
Timing check: the success case needs +94% ($36.40) by the Dec-2027 expiry —
0.82 σ, P(|move| ≥ required) 41.4%, `refutes timing claim (> 2 sigma)? NO`
(UNRELIABLE either way; not evidence for anything). IV > 50%, so every
implied figure above is quoted to whole percents in prose.

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** LiGeR-HN1 topline (Q4 2026) positive with a modest effect size
  or a tolerability problem (skin/EGFR toxicity, infusion burden) that leaves
  room for a second entrant — validates the class without closing the door.
- **Shift —** price falls toward the cash floor while the programme is intact
  (e.g. < $12, equity ≈ 2× cash at readout): the required success value
  drops below $1.5B even at p=0.35.

For an owner (sell):

- **Break —** FORTIFI-HN01 interim misses or the FDA declines an ORR-based
  accelerated path.
- **Break —** LiGeR-HN1 fails on its primary endpoint for a reason that
  implicates EGFR + pembro in 1L HNSCC generally.
- **Shift —** petosemtamab's randomized result is clearly superior (e.g. ORR
  gap > 10 pts with similar safety) — shrinks the success value below the
  ~$2.5B the price needs.
- **Shift —** enrollment misses "substantially enrolled by year-end 2026"
  (Q4'26 print), pushing the interim past mid-2027.

**Reopen trigger:** 2026-12-31: bcax-liger-hn1-topline-class-readthrough-and-fortifi-enrollment-status

## 6. UNKNOWNs

1. UNKNOWN — the probability that ficerafusp's TGF-β arm adds randomized
   benefit over EGFR + pembrolizumab. It is domain science; this run cannot
   evaluate it. Bounded only by the oncology phase-3 base rate (roughly one
   in two to one in three for BTD-designated assets, folklore-grade) and the
   phase 1b single-arm data. Does not kill the analysis — it is exactly why
   the call is PASS rather than BUY.
2. PENDING 2027-08-16 — FORTIFI-HN01 interim topline (guided mid-2027;
   backstop the Q2 2027 10-Q).
3. PENDING 2026-12-31 — LiGeR-HN1 topline (Genmab guidance Q4 2026).
4. NOT OBTAINED — the latest management commentary beyond the Q2'26 press
   release: no call transcript fetched (stockanalysis probe values could not
   be decoded in this sandbox; the CLI prints schema only). Non-load-bearing:
   the press release carries the milestones.
5. NOT OBTAINED — 10-K Item 1A risk-factor sweep and the proxy's
   beneficial-ownership table (the fetched DEF 14A excerpt lacked it);
   Biocon's current stake is from press, not a 13D. Non-load-bearing.
6. UNKNOWN — the 1L HPV-neg PD-L1+ R/M HNSCC addressable patient count and
   price; no filing read this run states it. Needed to firm up the
   market-share sentence; does not change the pass.
7. *(possible, unnumbered in §1)* M&A: a strategic acquirer following the
   Genmab/Merus precedent. Option value only.

## 7. Sources

- **Primary:** Bicara 10-Q for 6/30/26 (cash, burn, commitments, options,
  pre-funded warrants, related-party agreements); Q2'26 8-K / press release
  2026-08-11 (milestones, runway, R&D/G&A, leadership); 8-K 2026-07-28 (board
  changes); 8-K 2026-08-25 (Wayfair sub-sublease); DEF 14A 2026-04-27 (share
  class, staggered board, removal for cause); Form 4 2026-09-10 and Forms 144
  (insider sales); EDGAR submissions JSON; XBRL companyconcept
  OperatingIncomeLoss and NetCashProvidedByUsedInOperatingActivities
  (FY2023–Q2'26); 424B5 / company release on the Feb 2026 $150M offering;
  Genmab release on the Merus acquisition ($97/sh, ~$8.0B); JCO / ASCO
  abstracts for ficerafusp (ORR 54%, mOS 21.3 mo) and petosemtamab (ORR 67%);
  ClinicalTrials.gov NCT06788990, NCT06525220.
- **stockanalysis.com (vetted exception):** symbol lookup (price $18.80,
  market cap $1,244,051,159). Full statistics decode not obtained this run.
- **Broker/market microstructure:** Robinhood MCP — live quote and official
  close ($18.80, 2026-09-28), 8-quarter EPS estimate/actual history, option
  chain, ATM quotes/IV/OI, daily bars 2026-05-21→09-28. Admissible: no
  integrated official source covers the estimates, the chain, or today's
  quote for this ticker (`options.db` has no BCAX history; `earnings.db` no
  row).
- **Reference data:** Damodaran implied ERP 4.14% (2026-09-01); DGS10 5.17%
  (2026-09-25) and T10YIE 2.34% (2026-09-28) from `data/fred.db`.
- **Point-in-time repo DBs:** `stocks.db` v_latest (snapshot 63, price date
  2026-09-25: $19.21, cap $1.27B, net cash $496.1M, TTM op loss −$202.0M, SBC
  $22.2M, short float 30.3%, analyst median $35); `sec_fundamentals.db`
  v_screener/facts (Q2'26 net loss −$55.4M, EPS −0.82); `composite.db`
  snapshot 90 (bullish 2, score_sum 3); `options.db` (no BCAX rows);
  `earnings.db` (no BCAX row). Live probe wins for price; the DBs are one
  session stale.
- **Low-confidence:** MarketBeat (HSBC downgrade 2026-09-23, insider-sale
  tally); Simply Wall St (Aug drawdown framing); medicaldialogues.in (Claire
  Mazumdar as Biocon successor, Biocon ~10% stake); Investing.com summary of
  Genmab's LiGeR-HN1 Q4 2026 timing; OncLive/CancerNetwork cross-trial
  summaries.
- **Holdings overlap:** holdings unavailable in this session (unattended run;
  no `portfolio.db` grant) — moot for an `idiosyncratic` factor line.

## Kill-thesis record

**Ledger:** SOUND (on this pass) — conditions=4 (1 probable, 3 plausible),
refuted=0, unknown=0, pending=3, not_obtained=0. The label grades the bull
case's robustness; the PASS comes from §1 (the pending conditions cannot be
underwritten today and pay off outside the horizon).

**Per-condition adjudication (bull case):**

1. Interim supports accelerated approval — **PENDING 2027-08-16.** Attack:
   single-arm phase 1b ORR in HNSCC routinely shrinks in randomized trials
   (the control arm here is active pembrolizumab, which responds ~20% in
   CPS≥1); the dose changed (1500 mg weekly selected; FORTIFI-FLEX tests
   loading/Q3W), so the pivotal regimen is not the one that produced the
   54%. Nothing today stands against it; the readout is dated.
2. Competitive with petosemtamab — **PENDING 2026-12-31.** Attack: the only
   comparison available today is cross-trial and favours petosemtamab on ORR
   (67% vs 54%); ficerafusp's case rests on longer OS follow-up petosemtamab
   has not had time to show. Cross-trial ORR on small n with a 45–84% CI is
   not a refutation. First randomized class data arrive with LiGeR-HN1.
3. Cash funds the readout — **SURVIVED** (probable). Attack: burn is
   accelerating (H1'26 $81.7M vs $53.7M H1'25; R&D +85%) and headcount +87%.
   Even at $60M/quarter, $497M covers the ~4 quarters to the interim twice
   over; the Feb 2026 raise was at $16, near today's price, so a raise is
   not needed before the data.
4. Success-case value ≥ ~$2.5B — **PENDING 2027-08-16.** Attack: the $8.0B
   Merus anchor bought the class leader with first-mover timing, a
   multi-indication antibody and Genmab's own ≥$1B 2029 projection; a
   second entrant needs 60–80% of that sales figure to be worth $2.5B.
   Demanding but not refuted today; it hangs on the two readouts' relative
   magnitude.

**Standing checks.**
- *Base rate:* phase-3 oncology success runs well under one half even with
  Breakthrough designation (folklore-grade; no measured rate cited this run),
  and second-to-market drugs in a line usually take the smaller share.
- *Short case:* 30% of float is short, and the strongest version writes
  itself — a founder leaving before pivotal data, insiders selling into
  weakness, a better-funded rival with a higher ORR reading out first, and a
  TGF-β mechanism with a history of failed trials across oncology
  (bintrafusp alfa's randomized failures are the precedent a short cites;
  not researched further this run).
- *Management incentives:* 11.7M options at $11.50 are in the money; the new
  CEO sold 17,500 shares on 9/8. Nothing assumes management acts against
  incentive; the founder's exit is the governance flag.
- *Disconfirming search:* run on the rival (petosemtamab, amivantamab) and on
  the drawdown; it produced the closest attack and no refutation.
- *Moat:* checkbox — patents on the molecule, no mechanism protecting the
  indication.

**Statistical checks:** the composite flag (days-to-cover, RSI) is a
microstructure signal on one ticker-date; effective n = 1, not evidence.

**Options timing check:** ran on path 2 (stopgap) against the Dec-2027
expiry that brackets the dated interim; success case needs +94% = 0.82 σ,
`refutes timing claim (> 2 sigma)? NO`. Liquidity gate FAILED → UNRELIABLE,
so the check could not cut even had it crossed the line.

**Factor-line attack:** "idiosyncratic" is attackable — small-cap biotech
risk appetite (funding windows, XBI) moves this name with every other
clinical-stage holding. The readout's binary dominates that factor at this
horizon, so the label stands; holdings could not be read to test overlap.

**Closest attack:** second-to-market behind petosemtamab, whose early ORR is
higher and whose randomized data land first (Q4 2026).

**Flip evidence:** toward FLAWED — LiGeR-HN1 fails for a class reason, or
its randomized effect is clearly superior to anything ficerafusp's single-arm
data can match (refutes 2 and 4). Toward a BUY-worthy SOUND — a positive but
modest LiGeR-HN1 plus confirmation FORTIFI-HN01 is fully enrolled on time.

**p(beat SPY, 63 td):** 0.40 — a two-sided class readout inside the window
on a 90%-IV, heavily shorted name; the median outcome of that distribution
trails SPY even if the mean does not.
