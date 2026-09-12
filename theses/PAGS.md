# PAGS — PagSeguro Digital (PagBank) — 2026-08-13

Price $8.72 (close, 2026-08-12) · market cap $2,403.6M · next earnings
2026-11-11

Entered via the `candidates` screen (composite never flagged PAGS — its
ticker layer is microcap-dislocation).

## 1. Verdict and thesis

**BUY at $8.72.** kill-thesis: **UNPROVEN** — conditions=7, refuted=0,
unknown=2 (the through-cycle loss curve of the young unsecured credit book
does not exist in any disclosure yet).

The price pays for permanent stagnation — flat USD earnings forever implies
~18%/yr against a 14.3% Brazil-adjusted hurdle, and even a −3%/yr fade clears
it — so Selic normalization and the credit build are a free option. The floor
does not need the 2029 plan; the unknowns kill only the upside leg.

**Closest attack:** the internal inconsistency between a ~93%-of-NI payout,
the 5× credit-book ambition, and the "low risk" framing — sharpened by the
completed, un-renewed buyback.

Load-bearing conditions not enumerated in original run; condition tiers not
recorded in original run.

## 2. Business

- **Created:** payments acceptance (POS/PIX/cards) plus a full digital bank
  (deposits, bill pay, investments, insurance, credit) for Brazilian
  micro/SMB merchants and consumers — 34.1M clients, deposits R$42.8B (>90%
  originated on-platform), Cash-In R$97B/q (+23% y/y). One app replaces a
  bank+acquirer pair for merchants too small for the incumbents to serve
  well.
- **Captured:** acquiring MDR + prepayment spread on receivables (Expanded
  Portfolio R$52.4B); deposit float; lending NIM on a R$5.1B credit book
  (payroll loans R$3.4B, cards R$1.1B, working capital); fees on
  banking/insurance/investments. Gross profit = revenue − transaction costs −
  financial costs − credit losses; held at 1.5% of TPV. Banking is now ~31%
  of gross profit, growing 41% y/y (Q1'26 call).
- **Protected:** no strong moat in acquiring (commodity terminal + price);
  moderate switching costs from banking principality (deposits, payroll,
  transaction-history underwriting data) and low-cost on-platform funding
  (deposit APY cut 6.2pp y/y while deposits grew 15%). The valuation below
  assumes excess returns fade — the moat is not load-bearing.

**Operating leverage (Phase 0):** not recorded in original run.

## 3. Threads pulled

- **Q2 2026 print (Aug 11, 6-K):** revenue R$5,080M +0.4% y/y (ex-ITC +1.7%);
  GAAP NI R$549M +2.3%; GAAP diluted EPS R$1.96 +10.1% — EPS growth is
  entirely share shrink. TPV +3.0%, third buyback (US$200M) fully completed,
  R$1.4B 2026 dividend plan on track. Market reaction −1.9%.
- **Credit book (the alarm thread):** R$5.1B +30.7% y/y; unsecured mix
  doubled 13.1%→24.3% in a year (working capital +204% y/y, cards +35%);
  NPL90 rose 2.5%→3.05%→3.4% over four quarters — and a +31% denominator
  mechanically dilutes that ratio, so vintage deterioration is worse than the
  headline. Offsets: credit-loss line is ~5% of quarterly gross profit
  (R$106M vs R$1,999M); book is 34% of equity; Basel 22.5%. A 10% total loss
  on today's book ≈ one quarter's NI — painful, not fatal. At the 2029
  ambition (R$25B) the same event exceeds a year's NI. Management (Q1 call):
  NPLs "almost half the industry" — unverified vs BCB data.
- **Selic mechanics:** financial costs roughly doubled since tightening began
  Oct 2024 (Q1 call, CFO); Selic 15% vs 13% a year earlier; management
  expects easing from Q2'26 and gross-profit recovery in H2. The thesis does
  NOT require the cuts — that is the free option, not the floor.
- **Tax law (found in 20-F, enacted):** LC 224/2025 raises
  payment-institution IRPJ+CSLL 34%→37% (2026–27)→40% (2028+); R$142.3M
  deferred-tax expense already booked in 2025; new dividend withholding for
  non-residents from Jan 2026. If the effective rate (17.3% TTM) tracks the
  +6pp statutory move, NI takes a ~7% hit by 2028 — inside the bear run's
  envelope.
- **Competition:** management says SMB acquiring pricing has been rational
  for ~24 months (players: PAGS, Stone, Mercado Pago, CloudWalk); the
  2021–22 price war is recent history, so this stays plausible-tier. Pix
  (20-F: Pix MDR < debit < credit) is a slow structural mix erosion; PAGS
  partially monetizes it via banking engagement.
- **Insiders/ownership:** Principal Exec Officer Ricardo Dutra sold 50,000
  Class A at $9.24–9.27 on Jul 20–21 (Form 4), taking that holding line to
  zero (~$460K — modest, but to zero). UOL retains super-voting control;
  short interest 13.3% of shares out.
- **Estimate pattern (Robinhood tier):** five hair-thin beats (Q4'24–Q4'25)
  then two small misses (Q1'26: 0.39 vs 0.40; Q2'26: 0.388 vs 0.40) — the
  managed-guidance cadence broke this year.
- **Options read (mandatory):** path 2 (Robinhood stopgap — PAGS not in the
  CBOE catalog, no options.db history); metric table, gate verdict and
  timing line in §4.
- **Dead ends:** `sec_fundamentals.db` has no PAGS rows (FPI/IFRS filer) —
  live probe + EDGAR used instead; composite.db never flagged PAGS (its
  ticker layer is microcap-dislocation, PAGS entered via `candidates`);
  earnings.db carries no PAGS row; the Q2 call transcript is not yet indexed
  (call Aug 11) — Q1'26 call used, reconciled against the newer Q2 release.

## 4. Valuation

FCF is float/credit-book contaminated (statement FCF whipsawed −R$4.5B in
2024, +R$6.5B in 2025) — **base is TTM GAAP net income**, paired with market
cap. Inputs: market cap $2,403.6M (statistics `hover`, 2026-08-13); TTM GAAP
NI $415.2M (stockanalysis USD conversion of R$2,151M); SBC is immaterial
($24M, already expensed in NI).

Hurdle: rf 4.74% (Damodaran, Aug 1 2026) + beta 1.28 (statistics page) ×
Brazil total ERP 7.47% (ctryprem, Jan 5 2026 vintage; ~100% Brazil revenue) =
**14.3%**. ATM IV ~50% → implied returns quoted to the nearest whole percent.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A conservative | $415M | 0%/yr | 2.0% | **~18%** | +405bp |
| B mgmt-path | $311M (75% of NI, growth-capital haircut) | +8%/yr | 2.5% | **~19%** | +445bp |
| C bear | $415M | −3%/yr | 0% | **~15%** | +109bp |

- Run A's `growth without reinvestment` warning: 2% terminal ≈ inflation
  repricing, which requires no reinvestment — accepted deliberately.
- Run B's implied terminal ROE 10% sits below the hurdle: the terminal
  assumes no value creation on retained capital — intentional conservatism.
- Market-share sentence: Run B's 8%/yr puts USD earnings ≈ $610M by 2031 —
  PagBank holds <1% share in most Brazilian banking verticals (Q1 call) and
  ~10% of acquiring TPV; nowhere near a bigger-than-market path.
- Terminal-risk sweep (20-F Item 3.D): dominant structural risks are Pix
  displacing card economics and the enacted tax escalation. A 0–2% terminal
  growth range survives both only because Runs A/C already assume no real
  growth and fading excess returns; Run C prices the melt.
- Base-year cash-tax check: effective 17.3% vs statutory 34% (37% from 2026)
  — the gap narrows by law through 2028; covered in Run C, flagged in
  falsifiers.

**Options-implied move (path 2 — Robinhood stopgap; PAGS not in the CBOE
catalog, no options.db history):** Nov 20 2026 expiry (99 DTE, brackets the
Nov 11 earnings), ATM strike 9.0:

| metric | value |
|---|---|
| spot | 8.72 |
| expected absolute move (MEAN, not a ceiling) | 20.93% |
| 1-σ move | 25.87% |
| ATM IV | 49.67% |
| RV60 | 31.11% |
| RV20 | 30.81% |
| IV > RV60? | YES |
| IV > RV20? | YES |

IV exceeds both windows, but **quotes are UNRELIABLE**: zero volume on both
legs, OI 38 (call) / 393 (put), spreads 60–96% of mark fail the spread gate,
and a 16-point put/call IV disagreement suggests stale marks. No dated thesis
claim, so no timing refutation applies.

## 5. Falsifiers

- **Break —** NPL90 accelerating past ~4.5%, or the credit-loss line
  exceeding ~15% of quarterly gross profit — the credit engine is broken;
  the melt case takes over.
- **Shift —** distribution stop without credit-growth justification (no
  fourth buyback program AND dividend plan cut) — the flat-earnings floor
  then depends on retained capital compounding at ~15% ROE at 0.83× book;
  revalue.
- **Break —** take-rate war resumption — gross profit/TPV falling decisively
  below 1.4% or GP guidance withdrawn.
- **Shift —** effective tax rate above ~30% (law tracking worse than the −7%
  estimate) — rerun the DCF.
- **Shift —** Selic re-tightening cycle — delays, does not kill, the floor.

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **Through-cycle loss rate of the new unsecured book** — does not exist in
   any disclosure (vintages < 2 years old). Would come from future quarterly
   NPL90/coverage disclosure. Absence does NOT kill the flat-earnings floor
   (book too small today); it forbids underwriting the 2029 plan.
2. **Industry NPL comparison** — management's "half the industry" claim
   needs BCB series; unverified this run.
3. **Fourth buyback authorization** — third program completed in Q2; no new
   program in the Q2 release. Watch the Q3 print.
4. **Net Selic sensitivity** — falling rates cut funding costs but also
   float income; management claims net positive (Q1 call) — management
   claim, not independently modeled.
5. **UOL controller intentions** — capital-allocation continuity rests on
   the controlling shareholder; no disclosure obligation before the fact.

## 7. Sources

- **Primary:** (SEC) 6-K 2026-08-11 (Q2'26 release: 0001554855-26-001793;
  interim financials: -001791; dividend: -001795); 20-F FY2025
  (0001554855-26-000826) — tax law, Pix risk, rates; Form 4 2026-07-23
  (Dutra sale, 0001292814-26-003872).
- **stockanalysis.com (vetted exception):** /stocks/PAGS/statistics/ (market
  cap, ratios, short interest, beta — live probe 2026-08-13);
  /financials/income-statement/ (BRL history); /transcripts/584762-q1-2026/
  (Q1'26 call); /filings/ (IR PDF index).
- **Broker/market microstructure:** (Robinhood MCP) live quote ($8.72 close
  Aug 12), earnings estimate-vs-actual pattern (estimates side only; actuals
  cross-checked against the 6-K), option chain/quotes for the implied-move
  table, daily closes for RV. Admissible: no integrated official source
  covers PAGS quotes/options/estimates (sec_fundamentals has no FPI
  coverage).
- **Reference data:** (Damodaran, below primary) rf 4.74% + implied ERP
  (home.htm, Aug 1 2026); Brazil total ERP 7.47% (ctryprem.html, Jan 5
  2026).
- **Point-in-time repo DBs:** stocks.db snapshot 2026-08-12 (metrics row);
  composite.db / earnings.db / sec_fundamentals.db — absence of PAGS
  coverage noted in §3 dead ends.
- **Low-confidence:** none used.

## Kill-thesis record

**UNPROVEN** — conditions=7, refuted=0, unknown=2 (through-cycle unsecured
loss curve; BCB industry NPL comparison). Load-bearing conditions were not
enumerated in the original run; per-condition adjudication and the
standing/statistical/options-timing checks were not recorded.

**Closest attack:** the internal inconsistency between a ~93%-of-NI payout,
the 5× credit-book ambition, and the "low risk" framing — sharpened by the
completed, un-renewed buyback.

**Flip evidence:** Q3'26 print (2026-11-11) — NPL90 ≤3.5% plus a fourth
repurchase program flips toward SOUND; NPL90 > ~4.5% or a distribution stop
flips toward FLAWED.
