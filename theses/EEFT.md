# EEFT — Euronet Worldwide — 2026-08-04

Price $76.07 (live quote, 2026-08-04) · market cap $2,896M ($76.07 ×
38,075,094 basic shares; statistics hover 2,911,221,687 at snapshot) · next
earnings 2026-10-22 pm, tentative

Entry path: not recorded (pre-template run).

## 1. Verdict and thesis

**BUY at $76.07.** kill-thesis: **UNPROVEN** — conditions=6, refuted=0,
unknown=2.

A diversified payments company at ~9.5× levered FCF and ~12× GAAP earnings,
with per-share GAAP EPS compounded ~16%/yr 2022–2025 on real share shrink,
where even a stress-case reverse DCF (depressed TTM FCF, 3% growth, 1%
terminal) implies ~12.5%/yr. The market is pricing simultaneous permanent
decline in both legacy engines (European ATM cash, US retail remittance);
the disclosed evidence supports policy-cyclical pressure plus a genuinely
growing digital mix (26% of revenue, +31% YoY), not a cliff.

**Closest attack:** not recorded (pre-template run).

Load-bearing conditions: not enumerated in the original run (pre-template);
the ledger counts 6 conditions with 2 unknown. Condition tiers not recorded
in original run.

## 2. Business

**Created:** three networks. (a) Payments Infrastructure (formerly EFT,
~30% of revenue): 57,814 ATMs plus POS acquiring and the Ren/CoreCard
processing stack — tourists and locals get cash access and merchants get
acquiring; banks outsource ATM fleets. (b) epay (~25%): prepaid/digital
content distribution across ~739k POS terminals and 355k retailer locations
— game publishers (new: direct deals with Capcom; Yahoo/Rakuten in Japan)
reach consumers they can't reach alone. (c) Cross-Border Payments (~40%):
Ria/xe remittances across ~651k network locations plus the Dandelion
wholesale payout network (new partner: Mastercard Move).

**Captured:** per-transaction fees everywhere — ATM withdrawal and
dynamic-currency fees, interchange, content distribution commissions,
remittance fees and FX spread, and now SaaS processing fees (CoreCard, sold
as "Ren" suite). Q2 2026: revenue $1,108.4M (+3%), operating income $137.1M
(-14%), adjusted EBITDA $192.8M (-6%). [8-K ex-99.1]

**Protected:** physical network density (an ATM estate and 651k payout
locations are slow, capital-heavy, regulator-heavy to replicate); ~40
country money-transfer licenses; payout-network breadth (management claims
best-in-class payout for xe — unverified); CoreCard is per management one
of only "two, maybe three" credit-processing platforms at scale [call,
low-confidence management claim, but corroborated by the Unibanca
competitive displacement win]. The moat is real but not deep — remittance
pricing is competitive and ATM economics erode as cash usage declines.

**Operating leverage (Phase 0): positive 2021→2025, negative in the TTM.**
Revenue 2021→2025: $2,995.5M→$4,244.2M with op income $184.0M→$529.8M
(margin 6.1%→12.5%, strongly positive); but TTM op income $505.1M sits
*below* FY2025 on higher revenue — H1 2026 leverage is negative.
[stockanalysis financials]

## 3. Threads pulled

- **Why the drawdown:** Q2 2026 adjusted EPS $2.82 missed the $2.91
  estimate (broker-tier data); stock fell $83.67 → $71.33 in two sessions,
  since bounced to ~$76. Driver: cross-border op income -34% on US
  immigration enforcement (first US outbound remittance market decline in
  over a decade; Brookings: 2025 net migration ≈ zero/negative, cited by
  management) plus a tough comp (non-recurring Pakistan fee rebate,
  one-time FX gains in Q2'25).
- **The adjusted-EPS wedge (short case's best weapon).** Q2 reconciliation:
  GAAP net income $77.4M → adjusted $110.0M via FX, intangible amortization
  ($9.6M), **share-based comp $15.7M**, tax effects. SBC is a real economic
  cost (~$59M TTM); aggregate GAAP net income has been flat three years
  ($306.0M → $309.5M → $288.4M TTM). The honest engine is per-share:
  diluted GAAP EPS $4.41 (2022) → $6.84 (2025) on buybacks (53.5M → 45.8M
  diluted shares). Adjusted EPS growth overstates owner-earnings growth;
  the buyback compounding is nonetheless real cash-funded shrink. [8-K
  ex-99.1; 10-K]
- **FCF volatility decoded.** Reported FCF swings
  ($314M/$644M/$549M/$616M/$434M/$305M TTM) are dominated by
  ATM-cash working-capital timing (seasonal peak funding; net debt +$125.3M
  in Q2 partly for ATM cash). Anchor: net income ≈ FCF ≈ $290–320M. The
  $500–600M years were WC-inflated — **not** a normalized base. Dead end: I
  initially framed "FCF normalizes to $430M"; the reconciliation killed
  that framing, thesis restated at the $305M base.
- **Convert overhang checked and dismissed:** $1,000M 2030 converts at
  0.625% convert at ~$127; $33M 2049 converts at ~$188. Both far out of the
  money at $76; GAAP diluted count (46.2M) if-converts them, adjusted count
  (39.1M) excludes them. Dilution needs the stock +67% first. [10-K]
- **Balance sheet:** total debt $2,654.0M vs total cash $2,220.7M (≈$1B of
  it deployed *inside* ATMs); net debt ≈ $623M vs ~$700M+ annual adjusted
  EBITDA — modest. €700M 1.375% senior notes repaid at maturity May 2026
  via revolver: interest headwind ≈ +$6M for 2H 2026. [8-K ex-99.1; call]
- **Estimate pattern (broker tier):** trailing 8 quarters mostly small
  beats (Q1'26 +13%), two small misses (Q2'25 -0.8%, Q2'26 -3.1%). No
  chronic guide-down pattern. Next report 2026-10-22 (pm, tentative).
- **Post-call sweep:** no 8-K after the Jul 30 print; only a 13G/A (Jul
  31). No insider Form 4s after the drawdown — no insider-buying signal
  either way.
- **Options read (mandatory):** path 2 stopgap only — EEFT is not in the
  CBOE catalog; no `options.db` history — see the §4 table. Liquidity gate
  FAILS; the read is UNRELIABLE, context only.
- **Dead ends:** EEFT absent from `data/sec_fundamentals.db` (v_screener
  and companies) and from composite's flag history — no repo point-in-time
  cross-check available; GTA VI (Nov 19 release) is an epay tailwind but
  management explicitly doesn't forecast single titles; World Cup travel
  distortion discussed on the call is plausible but unquantifiable.

## 4. Valuation

Reverse DCF (`tools.valuation.reverse_dcf`), levered TTM FCF paired with
**market cap** (live: $76.07 × 38,075,094 basic shares = $2,896M; converts
far OTM so basic is the right count), 5-year horizon.

Hurdle: not computed in the original run; the `vs hurdle` column is
omitted.

| scenario | base FCF | growth | terminal | implied return |
|---|---|---|---|---|
| A (base) | $305.5M TTM | 5%×5 | 2.0% | **~14%/yr** |
| B (optimistic) | $434.3M FY2025 | 5%×5 | 2.0% | ~19%/yr (not credited — WC-inflated base) |
| C (if-converted cap $3,558M) | $434.3M | 5%×5 | 2.0% | ~16%/yr |
| D (stress) | $305.5M | 3%×5 | 1.0% | **~12.5%/yr** |

Scenario A is the anchor: the TTM base is itself depressed (remittance
downturn, negative TTM leverage), growth 5% sits below guided revenue+mix,
and terminal 2% must survive the 10-K's disclosed structural risk —
contactless/NFC adoption reducing cash need and hence ATM transactions
[10-K Item 1A]. It survives only because the digital mix (26% of revenue,
+31%) grows through the decline; if cash displacement accelerates to a
cliff, terminal 2% is wrong — that is condition 2 below. High implied
return on conservative assumptions — the interesting quadrant.

**Options-implied move** (path 2 stopgap only — EEFT is not in the CBOE
catalog; no `options.db` history). Nov-20-2026 expiry (brackets the Oct 22
Q3 print, the thesis's nearest evidence event), spot $76.07, DTE 108:

| metric | value |
|---|---|
| spot | 76.07 |
| dte (calendar days) | 108 |
| ATM IV | 45.61% |
| expected absolute move (MEAN, not a ceiling) | 19.65% |
| 1-sigma move | 24.81% |
| RV60 | 44.40% |
| RV20 | 51.80% |
| IV > RV60? | YES |
| IV > RV20? | NO |

**Liquidity gate FAILED → UNRELIABLE** (call spread 14.8% of mark, put
33.6%; OI 2/352) — context only. The RV windows disagree (RV20 still
carries the earnings gap) — that disagreement is the finding; not
"elevated". The thesis makes no dated move claim, so no 2-sigma timing
refutation applies.

## 5. Falsifiers

What would make me sell:

- **Break —** A **second** annual decline in the US outbound remittance
  market (2026 full year), or Mexico-corridor volumes re-deteriorating
  after the claimed stabilization.
- **Break —** Digital accelerator revenue growth below ~15% for two
  consecutive quarters.
- **Break —** FY2026 adjusted EPS guidance cut below the 10–15% range, or
  FY FCF (ex ATM-cash WC swings) below ~$280M.
- **Break —** Net debt / adjusted EBITDA above ~1.5× from buybacks or an
  acquisition materially larger than CoreCard.
- **Break —** PI segment constant-currency revenue turning negative (the
  ATM-cliff tell).

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **US-outbound share of Cross-Border revenue** — not disclosed at
   corridor granularity anywhere in the 10-K/10-Q; management's "4 months
   of Mexico recovery" is call color resting on third-party market data.
   Absence does not kill the thesis (segment is 40% of revenue and its op
   income decline is already in the TTM base) but it blocks sizing the
   worst case. Would come from: enhanced segment disclosure, or Banxico
   corridor data (external).
2. **Digital accelerator profitability** — the 26%/31% framework is
   revenue-only; no margin disclosure exists for the bucket. If accelerator
   growth is margin-dilutive at maturity, the mix-shift story weakens.
   Would come from: future segment re-reporting.
3. **Management comp metrics** (DEF 14A not read this run) — whether
   adjusted EPS is the bonus metric matters for how hard the addback wedge
   gets pushed.
4. **Composite/sec_fundamentals cross-checks unavailable** (EEFT outside
   both universes) — stockanalysis + EDGAR are the only structured sources
   here.

## 7. Sources

- **Primary:** 10-K FY2025 (filed 2026-02-26; conversion prices, Item 1A
  cash-displacement risk, debt structure); Q2 2026 8-K ex-99.1 (filed
  2026-07-30; all Q2 figures, adjusted-EPS reconciliation, balance sheet);
  EDGAR filing index (post-call sweep).
- **stockanalysis.com (vetted exception):** statistics page (market cap
  hover 2,911,221,687 at snapshot; TTM/FY financialData series;
  fcf/ncfo/capex; short interest 13.9% of float); Q2 2026 call transcript
  (primary-transcribed) + summary.
- **Broker/market microstructure:** Robinhood MCP (no integrated official
  source covers these fields for EEFT): live quote $76.07 (2026-08-04
  ~10:53 Phoenix), daily bars (closes array, drawdown path), earnings
  estimate/actual pattern, option chain/quotes for the implied-move table.
- **Reference data:** none used.
- **Point-in-time repo DBs:** none available — EEFT absent from
  `data/sec_fundamentals.db` (v_screener and companies) and from
  composite's flag history (§3).
- **Low-confidence:** management claims on call (payout-network
  superiority, "two, maybe three platforms at scale", Mexico
  stabilization); Brookings migration figure as relayed by management.

## Kill-thesis record

Kill-thesis detail not recorded in the original run (pre-template). The
ledger line as originally stated: **UNPROVEN** — 6 load-bearing conditions,
0 refuted, 2 UNKNOWN. Per-condition adjudication, the
standing/statistical checks, closest attack, and flip evidence were not
recorded; the options timing check is in §4 (no dated move claim, so no
2-sigma timing refutation applied).
