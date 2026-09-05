# SNDK — Sandisk Corporation — 2026-08-06

Price $1,279.77 (Robinhood quote, 12:45 PM Phoenix, 2026-08-06) · market cap
$190.5B · next earnings 2026-11-05 (FQ1 print)

Entry path not recorded in original run.

## 1. Verdict and thesis

**PASS at $1,279.77.** kill-thesis: **SOUND** — conditions=5, refuted=0,
unknown=2.

The price embeds peak-cycle economics roughly in perpetuity: best-case
implied return ~13%/yr, ~11%/yr if the June-quarter peak merely holds flat
forever, ~4%/yr under a three-year −30%/yr reversion — and the structure
meant to prevent reversion (NBM floors) is one quarter old and untested. At
108.9% ATM IV, none of those figures deserves a decimal.

**Closest attack:** the respectable counter — if the floors hold, today's
buyer does well (detail in the Kill-thesis record).

Load-bearing conditions not enumerated in original run; condition tiers not
recorded in original run.

## 2. Business

- **Created:** NAND flash bits — enterprise SSDs for AI data centers (TLC
  compute + QLC "Stargate" capacity tiers), embedded flash for phones/PCs,
  retail SanDisk brand. Vertically integrated die-to-system via the Flash
  Ventures JV with Kioxia (~50% of JV output, substantially all of SNDK's
  wafers). Data center went 12% → 38% of bits in FY26.
- **Captured:** historically spot/quarterly pricing (pure cycle-taker).
  Since April 2026, "New Business Models": 8 customers, up to 5-year terms
  (weighted avg >4yr), fixed+variable pricing with floors and ceilings, ~80%
  contracted GM, $93.9B minimum revenue at floor, $16.5B in
  cash-deposit/financial-instrument guarantees, RPO $91.1B incl. two
  post-quarter deals. >50% of FY27 bits committed with POs; ~2/3 of FY28.
- **Protected:** one of ~5 NAND makers (Samsung, SK hynix/Solidigm,
  Kioxia+Sandisk, Micron, YMTC); BiCS8 node leadership claim; multi-$10B fab
  barrier; NBM contracts. The honest answer: NAND is a commodity — the moat
  has never held pricing in a glut. FY23–FY25: cumulative operating loss
  ~$3.9B, cumulative FCF negative. The NBM floors are the first structural
  counterexample and they are unproven.

**Operating leverage (Phase 0): positive** — violently positive. Revenue
FY25→FY26 $7.36B→$20.25B; operating income −$1.38B→+$12.39B. Quarterly
through FY26: revenue 2.31→3.03→5.95→8.97B, op income 0.18→1.07→4.11→7.04B
(Q4 op margin 78.5% GAAP). GM went 22.7%→86.5% (GAAP) in five quarters per
the CFO. Driver split, Q4: ~1/3 bits, ~2/3 price.

## 3. Threads pulled

- **Why margins exploded — and why it's symmetric.** SNDK pays 50% of Flash
  Ventures' fixed costs regardless of orders (FY25 10-K; Q3 FY26 10-Q).
  Wafer payments to the JV ran ~$0.9B/q, flat YoY, while ASPs multiplied.
  The same fixed-cost base drove FY23's $2.0B operating loss. Max disclosed
  JV loss exposure $2.97B; committed to fund ~50% of JV capex when JV cash
  flow is insufficient.
- **The Aug 5 print/call** (read in full). Q4: revenue $8,965M (+51% q/q,
  +372% y/y), non-GAAP GM 84.6%, non-GAAP EPS $39.25 vs $30–33 guided.
  FQ1'27 guide: $10.3–10.8B, GM 83–85% (first sequential flattening in five
  quarters — the proximate cause of the −5% day), EPS $44–46. Management:
  NAND TAM ~$300B CY2026 (3x y/y) → ~$500B CY2027; bits on allocation beyond
  CY2027. Nanya: $972M for 3.9% + multi-year DRAM supply deal (Q3 10-Q).
- **Edge is the under-discussed 60%.** FY26 edge revenue $12.16B of $20.25B;
  consumer $2.9B more. Smartphone/PC units down mid-teens CY2026
  (management), consumer revenue −32% q/q, and management concedes
  price-driven TAM impact. NBMs do include edge customers (CFO: "data center
  and edge") — split undisclosed. A stabilization-in-CY2027 guide is doing a
  lot of work for 60% of revenue.
- **Estimate-vs-actual pattern**: five consecutive large beats ($0.29 vs
  −$0.12 … $39.25 vs $33.38) — the street has chased spot pricing upward all
  year, so the forward PE of 6.0 rests on estimates with a demonstrated
  one-year error history in both directions of magnitude. FQ1'27 street
  $41.45 sits *below* the $44–46 guide.
- **Supply response (rival race, dated web search)**: 2026 industry NAND
  capex up only ~5% (TrendForce, Nov 2025); Samsung/Hynix prioritizing
  HBM/DRAM; but SK hynix committed ~$65B to a new Cheongju NAND fab and
  meaningful capacity lands late 2027–2028 — inside the NBM window.
  Low-confidence tier (trade press).
- **Options read (mandatory):** path 2 (Robinhood stopgap; SNDK not in CBOE
  catalog, no options.db history); table in §4.
- **Dead ends**: no SNDK row in sec_fundamentals.db (post-spinoff, out of
  universe) — GAAP cross-check of Robinhood actuals unavailable there;
  Robinhood actuals are non-GAAP (Q4 GAAP EPS $43.97 incl. $807M Nanya gain
  vs $39.25 non-GAAP). No Form 4 insider buys in edgar.db window; insiders
  own 0.55%. Composite flag: 1 bullish signal at 9% coverage —
  microstructure only, no information. FY26 10-K not yet filed (only the
  FY25 10-K and Q3 FY26 10-Q were available for commitments/risk).

## 4. Valuation

Reverse DCF, levered TTM FCF paired with market cap ($190,533,750,000,
stockanalysis hover), net-debt 0 (net cash $6.5B ignored, conservative).
Quoted to whole percents — ATM IV 108.9% makes finer precision arithmetic,
not knowledge.

No hurdle computed this run.

| Scenario | Base FCF | Growth path | Terminal | Implied return |
|---|---|---|---|---|
| Street path holds, then flat | $11.49B (TTM, incl. NBM deposits) | +80/+20/+5% | 0% | ~13%/yr |
| Q4 peak sustained forever | $20.1B (Q4 adj. FCF ×4) | 0/0/0% | 0% | ~11%/yr |
| Cycle reversion | $20.1B | −30%×3 | 0% | ~4%/yr |
| Deep reversion | $20.1B | −40%×3 | 2% | ~4%/yr |

Caveats: TTM statistics-route `fcf` ($11.49B) includes NBM customer
prepayments (Q4 alone $1.938B; company's own Q4 *adjusted* FCF excludes them
at $5.04B). Capex ~6% of revenue is real but only because fab capex sits
inside Flash Ventures — the commitment is the 50% fixed-cost + capex-funding
obligation, not the capex line. Terminal-risk check: the disclosed dominant
risk (cyclicality/oversupply + the FV fixed-cost obligation, FY25 10-K
Item 1A) is exactly what the 0% terminal rates assume; any positive terminal
growth would not survive it un-argued.

**Options-implied move** (path 2 — Robinhood stopgap; SNDK not in CBOE
catalog, no options.db history). Aug 14 expiry (brackets the Investor Day),
8 DTE, ATM 1280 straddle: call mark 82.55, put mark 81.95.

| metric | value |
|---|---|
| spot | 1,279.77 |
| ATM IV (mean) | 108.91% |
| expected absolute move (MEAN, not a ceiling) | 12.85% |
| 1-sigma move | 16.12% |
| RV60 | 135.5% |
| RV20 | 162.4% |
| IV > RV60? | NO |
| IV > RV20? | NO |

IV is *below* realized. The market prices continuous violence, not a
discrete catalyst. Liquidity thin (OI 46/35, vol 111/105) — treat levels as
indicative. Timing-check applicability not recorded in original run.

## 5. Falsifiers

What would flip the pass to interest in owning:

- NBM floor economics quantified (Investor Day, week of 2026-08-10, or FQ1
  print 2026-11-05) showing floor-price EPS that alone supports ~$1,280.
- Floors holding through the first real NAND contract-price decline —
  observable in GM vs the 83–85% guide and in the guarantees/RPO
  disclosures.
- Edge exabyte demand returning to growth in CY2027 as guided, without price
  concessions.
- NAND still on allocation beyond CY2027 with the 2028 SK hynix capacity
  absorbed.

For an owner, the sell-side falsifiers would be: GM guide below ~80%, any
NBM renegotiation/walk-away, edge decline accelerating, industry bit growth
above high-teens.

**Reopen trigger:** none stated.

## 6. UNKNOWNs

1. **Floor-price gross margin** — "attractive" (CFO), no number. Comes from
   Investor Day or FY26 10-K. Its absence is why the bull case is unprovable
   today; it does not kill the pass.
2. **Edge vs data-center split of NBM commitments** — undisclosed. Bounds
   how much of the 60%-of-revenue edge exposure is floored.
3. **NBM prepayment content of TTM FCF** — only Q4's $1.938B disclosed;
   full-year adjusted FCF not derivable from available documents. Bounded:
   true owner FCF is between ~$9.6B and $11.5B TTM.
4. **FY26 10-K** (not yet filed): updated commitments, NBM accounting,
   risk-factor changes.
5. **Guarantee structure per customer** (proportionality to RPO) —
   undisclosed.
6. **HBF (High Bandwidth Flash) timing/economics** — pre-revenue; management
   promises detail at Investor Day. Optionality, not valuation support.

## 7. Sources

- **Primary:** Q4 FY2026 earnings call 2026-08-05 (full transcript); FY2025
  10-K (SEC, filed 2025-08-21, CIK 2023554) — Flash Ventures fixed-cost
  obligation, Item 1A; Q3 FY2026 10-Q (filed 2026-05-01) — FV loss exposure
  $2.97B, Nanya agreement; 8-K 2026-08-05 (edgar.db capture).
- **stockanalysis.com (vetted exception):** /stocks/SNDK/statistics/ (market
  cap, ratios, TTM figures, 2026-08-06 live),
  /financials/income-statement/ annual+quarterly.
- **Broker/market microstructure** (admissible — no integrated official
  source covers these fields for SNDK): Robinhood quotes ($1,279.77 at
  12:45 PM Phoenix 2026-08-06), option chain/quotes (Aug 14 ATM), earnings
  estimate-vs-actual history, daily bars for the closes series.
- **Reference data:** none used.
- **Point-in-time repo DBs:** (read-only) stocks.db (prior capture
  $1,350.50), composite.db (1 bullish signal, 9% coverage), edgar.db (filing
  index, no Form 4s).
- **Low-confidence:** TrendForce via press (industry capex +5% 2026), Seoul
  Economic Daily / Blocks & Files (SK hynix ~$65B Cheongju NAND fab;
  Samsung/Hynix capex race), NAND TAM figures are management's own ($300B
  CY2026 / $500B CY2027 claims, unverified third-party).

## Kill-thesis record

**SOUND** — conditions=5, refuted=0, unknown=2. Ownership: PASS at
$1,279.77.

Per-condition adjudication not recorded in original run. Standing,
statistical, and options-timing checks not recorded in original run.

**Closest attack:** the respectable counter: 5.8x street forward earnings,
$6.5B net cash, third-party-collateralized contract floors, and a $15.5B
buyback authorization (~8% of the float per year at the Q4 pace). If the
floors hold, today's buyer does well. That evidence does not exist yet; it
starts arriving at the Investor Day (week of 2026-08-10) and the Nov 5
print.

**Flip evidence:** not recorded in original run (ownership falsifiers in
both directions are listed in §5).
