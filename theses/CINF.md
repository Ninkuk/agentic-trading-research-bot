# CINF — Cincinnati Financial — 2026-08-03

Price $177.66 (2026-07-31 close) · market cap $27.27B · next earnings
2026-10-26 PM (tentative, unverified)

Entry path: not recorded (pre-template run).

## 1. Verdict and thesis

**PASS at $177.66.** kill-thesis: **UNPROVEN** — conditions=5, refuted=0,
unknown=2 (reserve adequacy unreviewed, forward equity returns unknowable).

High-quality, conservatively run P&C insurer whose headline cheapness
(trailing PE 8.4, "FCF yield" 12.5%) is an accounting illusion — strip the
ASU 2016-01 equity marks and float growth and the market is paying ~20×
forward operating earnings / 1.63× book entering a softening P&C cycle.
Becomes interesting near ~$145 (≈1.33× book, ~12% implied on economic
earnings).

**Closest attack:** the $145 target leans on 1.63× book being historically
elevated, and no historical P/B series was fetched. Detail in the
Kill-thesis record.

Load-bearing conditions: not enumerated in the original run (count 5).
Condition tiers not recorded in original run.

## 2. Business

**Created:** Commercial + personal P&C insurance (plus small life sub) sold
exclusively through ~2,000 appointed independent agencies. The agent gets an
above-average profit-sharing contract keyed to underwriting profit and field
claims service that makes the agent look good to their client; the insured
gets broad coverage forms and fast claims handling. High-net-worth personal
lines is the growth engine — now >60% of personal lines premiums (Q2 2026
call).

**Captured:** Underwriting margin (combined ratio ~93–96% across the cycle)
on $10.4B TTM earned premiums, plus investment income ($1.24B TTM, growing
~12% on new-money yields of 5.66% vs 5.08% portfolio average) on a float- and
equity-heavy investment book. Uniquely among P&C peers, CINF runs a large
common-stock portfolio — $8.9B net unrealized gain position at Q2 2026
(call) — so book value compounds with the equity market, not just with bond
coupons.

**Protected:** Agent loyalty as a mechanism, not a label: the profit-sharing
contract pays the agency for *underwriting profit*, not volume, and 65
consecutive years of dividend increases (statistics route) select for
agencies that stay. Net cash at the holdco ($874M net cash; debt $876M vs
$16.7B equity). This is a real but modest moat — pricing is competitive and
cyclical, and nothing stops Chubb/Travelers from courting the same agents.

**Operating leverage (Phase 0):** premiums earned 6.48B→10.40B (2021→TTM,
~10%/yr); operating income is direction-less noise at the GAAP line (marks),
but underwriting profit decomposed: 2021 ~+$603M (CR ~90), 2022 ~+$21M
(CR ~99), 2023 ~+$275M (CR ~96), 2024 ~+$463M (CR ~94), TTM ~+$652M
(CR ~93) — my calc from the statement route, whole-company approximation.
Positive but cyclical; the compounding engine is investment income
(714M→1,237M, +73% over 4.5yr), not underwriting.

## 3. Threads pulled

- **Is the screen's 12.7% FCF yield real?** No. TTM "FCF" $3.40B ≈ NCFO,
  which for an insurer is premiums collected ahead of claims (float growth) —
  not distributable. TTM GAAP net income $3.33B contains **$2.27B pretax of
  net investment gains** (income-statement route,
  `net_gains_losses_on_investments`); 2022 shows the mirror image (−$1.47B,
  GAAP loss −$487M in an ordinary underwriting year). The screen misread the
  accounting. **Dead end for the value case; the load-bearing finding of
  this run.**
- **Q2 2026 print + call (Jul 27/28, primary):** operating income $224M vs
  $311M LY (−28%); P&C CR 100.8% (+5.9pts, of which cats +2.3); H1
  accident-year ex-cat CR 87.8% ≈ flat YoY; NWP +3% (⅔ rate, ⅓ exposure);
  commercial large-loss uptick ($112M vs $101M YTD) framed as volatility, not
  trend; California homeowners retrenchment post-wildfire; buybacks 2.4M
  shares YTD ("maintenance plus"); expense ratio target <30%.
- **Post-call sweep:** BofA downgrade to Neutral 2026-07-30 on slowing
  homeowners growth (explains the $184→$175 dip); Roth PT raise to $200 on
  7/28. Nothing structural since the call.
- **Earnings-estimate pattern** (broker tier): operating EPS beat 6 straight
  quarters (Q4'24 3.14 vs 1.87 through Q1'26 2.10 vs 1.94), then **Q2'26
  missed** (1.43 vs 1.73) — the first crack, cat-driven. Next report
  2026-10-26 PM (tentative, unverified). Robinhood "actual" here is non-GAAP
  operating EPS, not GAAP (cross-checked: GAAP Q2 EPS ≈ $8.05 per SEC facts).
- **SEC cross-check:** Q2 GAAP net income $1,255M / equity $16,671M
  (sec_fundamentals.db v_screener) matches the call's "nearly $1.3B" and the
  statistics route's book value. ✓
- **Composite/DB state:** not flagged by composite (no ticker_scores row);
  not in the CBOE options catalog (path 2 only).
- **Options read (mandatory):** path 2 only — Robinhood stopgap; path 1 n/a,
  not in the CBOE catalog. See §4's table for the metric read and the
  liquidity-gate outcome.
- **Dead ends:** not separately recorded in the original run beyond the
  first bullet's finding, marked there "dead end for the value case."

## 4. Valuation

Reverse DCF, market cap $27.27B (statistics route hover), three framings. No
hurdle was computed in the original run, so no `vs hurdle` column is shown:

| scenario | base flow | growth ×3yr | terminal | implied return |
|---|---|---|---|---|
| A. as-reported levered FCF (float-inflated — **wrong flow, shown to expose the trap**) | $3.40B | 3% | 2.5% | **15.45%** |
| B. normalized operating earnings (95 CR on $10.4B premiums + $1.24B inv income − interest, ~19% tax) | $1.38B | 6% | 2.5% | **8.21%** |
| C. B + after-tax equity-portfolio appreciation (~6.5% on ~$12–13B equity book × 0.79) | $2.00B | 5% | 2.5% | **10.54%** |

Run B cross-checks consensus: fwd PE 20.18 → fwd operating EPS ≈ $8.80 ≈
$1.35B. Run C is the honest economic-earnings view but its equity-book size
is approximate (see UNKNOWNs). Terminal risk (10-K Item 1A dominant risk):
catastrophe/climate loss escalation — 2.5% terminal survives it only because
P&C repricing is annual (cat trend passes through premiums with a lag); the
unhedgeable version is the equity portfolio, which makes book value
market-correlated.

**Options-implied move (path 2 — Robinhood stopgap; path 1 n/a, not in CBOE
catalog):** Sep 18 2026 expiry (46 DTE, no earnings inside), ATM 180 strike,
quotes as of 7/31 close:

| metric | value |
|---|---|
| spot | 177.66 |
| expected absolute move (MEAN, not a ceiling) | 6.81% |
| 1-σ move | 8.39% |
| ATM IV | 23.64% |
| RV60 | 26.20% |
| RV20 | 34.48% |
| IV > RV60? | NO |
| IV > RV20? | NO |

IV below both realized windows — the market prices calm, not stress.
**Liquidity gate FAILED** (call spread 42% of mark, put OI 0, both volumes 0)
→ UNRELIABLE, informational only. No dated thesis claim, so no timing
refutation was attempted.

## 5. Falsifiers

What would make this PASS wrong:

- **Shift —** Price at/below ~$145 (≈1.33× book) with the franchise intact →
  re-run, likely buy.
- **Shift —** Renewal pricing re-accelerating (hard-market turn) in two
  consecutive quarterly calls → premium growth thesis leg fails in the
  favorable direction; re-underwrite the pass.
- Expense ratio structurally below ~28% or CR persistently ≤92 → normalized
  earnings ~20% higher than modeled and 20× fwd is no longer full.

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **Reserve adequacy** — Schedule P triangles not reviewed this run;
   favorable-development record asserted from reputation, not evidence.
   Source: statutory filings / 10-K loss development tables. Absence does
   not kill a PASS; it would gate any future BUY.
2. **Equity portfolio composition and exact fair value** — call gives the
   $8.9B net gain position, not the split; ~$12–13B book size is my
   estimate. Source: Q2 supplemental (investors.cinfin.com) / 10-Q. Bounds
   Run C's precision, not its direction.
3. **Normalized cat load** — I used history (~7–9 CR pts); climate drift
   could be worse. Source: 10-K cat tables. Wide error bars accepted in
   condition 2's 93–96 range.

## 7. Sources

- **Primary:** Q2 2026 earnings call transcript (Quartr via stockanalysis
  transcripts route, 2026-07-28 — primary, transcribed).
- **stockanalysis.com (vetted exception):** /stocks/CINF/statistics/ (market
  cap, multiples, dividends, shares — hover values),
  /financials/income-statement/ (premium/investment split, 6 periods),
  overview news feed (downgrade/PT items, headline-tier).
- **Broker/market microstructure:** Robinhood quotes, option chain + ATM
  quotes, daily bars (RV inputs), earnings estimate-vs-actual history — no
  integrated official source covers these fields for CINF.
- **Reference data:** none used.
- **Point-in-time repo DBs:** SEC facts via data/sec_fundamentals.db
  v_screener (GAAP net income, equity, EPS cross-check); composite.db (no
  ticker_scores row); CBOE options catalog membership check (not present —
  path 2 only).
- **Low-confidence:** none used.

## Kill-thesis record

Ledger line restated: **UNPROVEN** — conditions=5, refuted=0, unknown=2
(reserve adequacy unreviewed, forward equity returns unknowable).

**Closest attack:** "$145 target leans on 1.63× book being historically
elevated, and no historical P/B series was fetched" (mitigated by fwd PE
20.18 as independent evidence of fullness).

Per-condition adjudication, the standing/statistical/options-timing checks,
and flip evidence were not recorded in the original run (pre-template); the
options timing line — no dated thesis claim, so no timing refutation was
attempted — is in §4.
