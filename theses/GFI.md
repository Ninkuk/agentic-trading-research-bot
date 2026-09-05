# GFI — Gold Fields Limited (NYSE ADR) — 2026-07-27

Price $32.90 · market cap $29.21B · next earnings 2026-08-21 BMO (H1
results)

Entry path: not recorded (pre-template run); researched in the same-day gold
cohort (AEM, OGC).

## 1. Verdict and thesis

**PASS at $32.90.** kill-thesis: **UNPROVEN** — conditions=4, refuted=0,
unknown=2.

GFI is a fairly-priced bet on gold staying near its corrected level
(~$4,035/oz, −28% from the Jan 29, 2026 peak of $5,595), with a live Ghana
tail: the price implies ~9%/yr on flat-spot assumptions and ~5%/yr if gold
mean-reverts toward $3,200 — market-rate payment for commodity and
jurisdiction uncertainty, not an edge.

**Closest attack:** the strongest bull attack on this pass — FY2025's $2.97B
adj FCF was earned 13% below today's spot, so the trailing "cheapness" is
real, not a peak-price artifact. It fails only because it is still a
gold-price bet (see §3).

Load-bearing conditions: four counted; not individually enumerated in the
original run (0 refuted, 2 structurally unverifiable — the gold path;
Ghana's undisclosed Tarkwa renewal terms). Condition tiers not recorded in
original run.

## 2. Business

**Created:** produces ~2.5Moz gold-eq/yr across 9 mines (Australia, Ghana,
South Africa, Chile, Peru, Canada in build). Customers buy a commodity;
nothing is created for a customer that a rival's ounce doesn't provide
identically.

**Captured:** the spread between realized price and all-in cost. FY2025:
realized $3,496/oz vs AISC $1,645 / AIC $1,927 → adjusted FCF $2,970M
(FY2024: $605M at $2,418/oz — the entire swing is price). FY2026 guided:
2.4–2.6Moz, AISC $1,800–2,000, AIC $2,075–2,300, capex $1.9–2.1B incl.
Windfall C$495M. [FY2025 results 6-K; Q1 2026 6-K]

**Protected:** **no moat — price taker.** Protection is asset quality only:
48.3Moz attributable P&P reserves (~19 yrs, grew 4.0Moz net of 2.5Moz
depletion in 2025), Salares Norte at steady state ($808M FCF in 2025, AISC
$1,144/oz — group's best), net debt $1,304M = 0.19× adj EBITDA at Q1 2026.
[20-F; 6-Ks]

**Operating leverage (Phase 0): strongly positive** — 2021→2025 revenue 2.1×
($4.20B→$8.75B), operating income 3.6× ($1.47B→$5.30B) — but it is leverage
to gold, not to a mechanism.

## 3. Threads pulled

- **The −47% drawdown ($61.64 Jan 28 → $32.90).** Two causes, not one: gold
  −28% off peak (US–Iran war → inflation 4.2% → Fed-tightening odds; company
  cites the war for suspending buyback execution), plus **Ghana**. Jun 22
  Tarkwa-lease 6-K day: −10.3%.
- **Ghana (the load-bearing thread).** Five Tarkwa leases AND the
  fiscal-stabilization Development Agreement expire **April 2027**. Renewal
  application filed Nov 2025; negotiations "focusing on the terms" with no
  agreement (Jun 22 6-K). 20-F risk factor: non-renewal ⇒ "cease mining
  operations at Tarkwa entirely." Precedents both adverse: royalty moved
  from flat 5% to a **5–12% sliding scale effective March 2026** (20-F), and
  **Damang was handed to the state April 2026** after a 12-month wind-down
  extension. Sizing: Tarkwa = $474M of $3,171M mine-level adj FCF (~15%),
  ~470koz of 2.4Moz. A 12% top-scale royalty ≈ ~$140M/yr pre-tax at $4,000
  gold (~4% of group FCF) — material, not thesis-killing; non-renewal is the
  tail. GFGL is 90%-held (Ghana 10% carried). Ghana mining-law overhaul
  colour (12% top royalty, 10-yr renewals, renewal "not automatic"):
  low-confidence web only.
- **Spot vs the record.** FY2025's $2.97B adj FCF was earned at $3,496/oz —
  **13% below today's ~$4,035 spot** (GLD $374.57 ≈ $4,035/oz, broker
  tier). Q4 2025 realized $4,184. The trailing "cheapness" (P/E 8.2, FCF
  yield 10.6%) is not peak-trailing-price artifact; H1 2026 averaged well
  above spot, so the Aug 21 print likely shows a near-net-cash balance
  sheet. That is the strongest bull attack on this pass — it fails only
  because it is still a gold-price bet.
- **Execution.** Q1 2026 on plan: 633koz (+15% YoY), guidance reaffirmed;
  Gruyere (rain, ground instability) and Agnew (seismicity) are the
  wobbles, Salares (173koz, +245% YoY) the offset.
- **M&A cadence (risk, not support).** Osisko 2024, Gold Road $1.42B net
  Oct 2025 (full Gruyere), Windfall FID due H2 2026, Cerro Corona
  divestment being assessed. Serial acquisition at rising gold prices is the
  sector's classic top-of-cycle failure mode.
- **Options read (mandatory):** path 2 (Robinhood stopgap; GFI not in the
  CBOE catalog, `options.db` has no history for it). See §4's table.
- **Dead ends:** Robinhood `get_earnings_results` — all-null (semi-annual
  20-F filer, no quarterly estimates; cross-check N/A). stockanalysis
  `/transcripts/` — empty for GFI; no call transcript ingested (results
  announcement + Q1 update read instead). `data/sec_fundamentals.db` — no
  GFI row (20-F filer outside the screener universe). `data/composite.db` —
  never flagged GFI. FRED — no gold series. `/financials/` route FCF
  ($2,374M) disagrees with `/statistics/` ($3,089M); primary source
  ($2,970M adjusted FCF) used instead of either.

## 4. Valuation

Reverse DCF, levered flows against **market cap** $29,207,673,553 (894.42M
ADS × $32.90; hover-exact from stockanalysis). NCI ≈ 2.1% of profit
($78M/$3,645M) — noted, not separately haircut; Case A's discount to
actuals absorbs it. ATM IV 53.5% > 50% ⇒ quoted to whole percent only. No
Damodaran hurdle was computed in the original run.

| case | base FCF | growth | terminal | implied return |
|---|---|---|---|---|
| A: flat spot gold, flat production | $2.7B | 0,0,0 | 0% | **~9%/yr** |
| B: gold ~$3,200 + Ghana degradation | $1.5B | 0,0,0 | 0% | **~5%/yr** |
| C: FY2025 actual holds | $2.97B | 2%×3 | 0% | **~11%/yr** |

Case A base: ~2.5Moz × ($4,035 − ~$2,190 mid-AIC) less ~31% cash tax ≈
$2.7B — deliberately below FY2025 actual to absorb the guided cost/capex
step-up and NCI. Terminal 0% nominal (negative real) is the rate that
survives the 20-F's disclosed terminal risks: license/fiscal degradation in
Ghana and reserve replacement (reserves currently growing, 19-yr life). No
Windfall credit anywhere (FID not taken — C$495M is committed 2026 spend,
the mine is not). Read: **the high implied return exists only on the
non-conservative anchor.** Flat-spot is not conservative after a 160%
six-year gold run; on the genuinely conservative anchor the price implies
~5% — a bad bet by this repo's own rule.

**Options-implied move** (path 2 — Robinhood stopgap; GFI not in CBOE
catalog, `options.db` has no history for it): Aug 21, 2026 expiry (brackets
Aug 21 BMO H1 results):

| metric | value |
|---|---|
| spot | 32.90 |
| dte (calendar days) | 25 |
| ATM IV | 53.53% |
| 1-sigma move | 14.01% |
| straddle mean | 12.46% (inflated — nearest strike 35 sits 6.4% from spot on a $5 ladder; put has $2.10 intrinsic) |
| RV60 | 58.37% |
| RV20 | 39.92% |

The windows **disagree** (RV60 carries the June crash; tape cooling since),
so IV is *not* "elevated" under the two-window rule. Liquidity: call OI
5,234 / vol 10; put OI 1,607 / vol 0 — thin; read is approximate. No timing
claim asserted, so nothing to refute.

## 5. Falsifiers

What would make an owner sell / keeps me out:

1. Gold sustained below ~$3,200 — Case B becomes the base; 5% implied is a
   pass at any label.
2. Tarkwa non-renewal, or renewal terms beyond the 12% scale (state equity
   above the 10% carry, export/repatriation restrictions).
3. FY2026 delivery break: production < 2.3Moz or AISC > $2,100.
4. A new large cash acquisition announced at current gold prices.

**Reopen trigger:** event: a signed Tarkwa renewal with quantified fiscal
terms + gold ≥ ~$3,800 ⇒ re-run; the spot-anchored ~9–11% would then be
creditable.

## 6. UNKNOWNs

1. **The gold path** — structurally unknowable; both my "conservative"
   $3,200 and "flat spot" are assumptions. This alone caps the verdict at
   UNPROVEN.
2. **Ghana's actual demands on Tarkwa** — exists in no disclosure; resolves
   only when the negotiation concludes (or leaks via govt gazette). Absence
   doesn't kill the pass; it kills conviction in either direction. (The
   reopen trigger in §5 keys on this.)
3. **Windfall FID economics** (capex, first-gold date) — FID H2 2026;
   unpriced here.
4. **CMD Nov 2025 multi-year path** — deck not ingested; FY2026 guidance
   carries the near term.
5. **Management comp structure** — 20-F comp section unread; M&A incentive
   alignment unverified.
6. **New royalty-scale brackets** — 5–12% bounds are primary (20-F); the
   intermediate bracket thresholds were not extracted.

## 7. Sources

- **Primary:** FY2025 reviewed results 6-K (Feb 19–20, 2026, incl. rr
  exhibit); Q1 2026 operational update 6-K (May 7, 2026); 20-F FY2025
  (filed 2026-03-30, acc. 0001628280-26-021904 — Tarkwa/DA risk factor,
  royalty legislation, reserves 48.3Moz); Tarkwa clarification 6-K (Jun 22,
  2026); chair-election 6-K (May 26) and dealing notice (Jun 24 — MacKenzie
  bought 500 shs ≈ $15k, token).
- **stockanalysis.com (vetted exception):** statistics/financials/news for
  GFI; noted intra-site FCF disagreement resolved to primary.
- **Broker/market microstructure:** (admissible — no integrated official
  source covers live quotes/chains/GLD for this name) Robinhood equity
  quote, option chain/instruments/quotes, daily bars (closes for RV), GLD
  quote as spot-gold proxy.
- **Reference data:** none used.
- **Point-in-time repo DBs:** `data/sec_fundamentals.db` (no GFI row — 20-F
  filer outside the screener universe); `data/composite.db` (never flagged
  GFI); `data/options.db` (no history for GFI); FRED (no gold series).
- **Low-confidence:** web colour on gold-price narrative (goldsilver.com,
  discoveryalert, Yahoo) and Ghana mining-law overhaul details;
  GuruFocus/TheFly headlines for PT cuts (JPM $75→$55, Scotiabank $60→$52,
  RBC $50→$49).

## Kill-thesis record

**Kill-thesis verdict: UNPROVEN** — conditions=4, refuted=0, unknown=2 (the
gold path; Ghana's undisclosed Tarkwa renewal terms — both structurally
unverifiable).

Per-condition adjudication: not recorded in original run (the four
conditions were not individually enumerated).

Standing/statistical/options-timing checks: not recorded in original run,
beyond §4's note that no timing claim is asserted, so nothing to refute.

**Closest attack:** the spot-vs-record bull attack — FY2025's $2.97B adj FCF
was earned 13% below today's spot, so the trailing cheapness is real; it
fails only because it is still a gold-price bet.

**Flip evidence:** not recorded as a labelled pair in the original run; §5's
falsifiers and reopen trigger carry the directional evidence.
