# ZTO — ZTO Express (Cayman) Inc. (NYSE: ZTO / SEHK: 2057) — 2026-08-25 (reconfirmation of 2026-08-19)

Price $21.40 (Robinhood close 2026-08-25) · market cap $16,264,283,015 (stockanalysis
live) · next earnings 2026-11-18 AMC · prior thesis `research/ZTO-2026-08-19.md`
(BUY at $21.41, kill-thesis UNPROVEN, reopen 2026-11-19).

**Reconfirmation, not a reopen.** No reopen trigger fired; the question asked was
whether the six-day-old BUY still holds at today's price and what the options
market prices for the 24 days to 2026-09-18. Sections unchanged from the 08-19
run are referenced, not restated.

## 0. The question, answered first

1. **The BUY holds.** Price is flat (−$0.01), market cap is flat (+0.08%), and no
   event since the Q2 print touches any of the five load-bearing conditions. The
   conservative implied return recomputes to **10.57%/yr vs the 6.69% hurdle
   (+387bps)** — identical to the 08-19 figure within rounding.
2. **A +7.9% move by 2026-09-18 is a 1.26-sigma event the market prices at ~21%**
   (table in §4). It is not refuted (the 2-sigma line is not crossed), and it is not
   supported either: the thesis has **no catalyst inside that window** — its
   evidence installments arrive at the Q3 print (Nov 18) and the reopen (Nov 19).
   Options evidence only cuts; a 21% probability is a statement about vol, not
   about the thesis.

## 1. Verdict and thesis

**BUY at $21.40.** kill-thesis: **UNPROVEN** — carried from 08-19 (conditions=5,
refuted=0, unknown=1); no condition changed, so the record was not re-run. The
one new attack (below) targets timing, which the thesis never asserted.

Thesis, conditions (5: 4 probable, 1 plausible), and closest attack: unchanged —
see `research/ZTO-2026-08-19.md` §1.

**New attack considered (timing):** "the options market prices only ~21% odds of
the +8% move a Sep-18 call needs." Does not land on the thesis — no dated
condition falls before Nov 18. It lands squarely on any *calendar* bet layered on
the thesis, which this skill does not evaluate.

**Dominant shared risk factor:** China consumption / policy stance (carried).
Book overlap: held symbols BR CAH CI EEFT G HIG INTU KTB LOPE MORN ORI PAGS PRI
SAP WRB YOU ZTO — PAGS (Brazil credit/Selic) and the rest are labelled on other
factors in their own theses; **0 matches** on the China factor besides ZTO
itself. Unlabelled: none checked this run beyond the factor lines already
recorded on 08-19 (unchanged book since).

## 2. Business

Unchanged — `research/ZTO-2026-08-19.md` §2. Operating leverage: positive
(Q2'26 revenue +23.0%, operating income +30.4%).

## 3. Threads pulled (since 2026-08-19)

- **Post-print sweep.** Robinhood daily bars: 08-19 $21.51 → 08-25 $21.40 on
  normal volume (1.6–1.8M/day after the 4.0M print day). EDGAR mirror
  (`data/edgar.db`, fresh to 2026-08-24) carries no ZTO rows — 6-K filers are
  outside its buckets; web sweep found only the routine buyback 6-K (291,396
  ADS at ~$23 on Aug 12–13, $6.68M, for cancellation) — mechanism working,
  condition 3 unchanged. Dead end otherwise: no guidance change, no insider
  filing, no VIE/regulatory item.
- **Peer/regulator colour (low-confidence, BigGo):** State Post Bureau opened a
  safety-management investigation into STO Express on 2026-08-04 and STO
  terminated a RMB3B convertible the same day. Direction is mildly supportive
  of condition 1 (regulator active in the sector; STO's own revenue per parcel
  RMB2.10 → 2.33 Q1'26) but it is not pricing enforcement and is not weighted.
- **Options read (mandatory) — path 2 only** (ZTO is not in the CBOE catalog;
  `data/options.db` has no history). Expiry chosen: 2026-09-18, the date the
  question named — **NOT a thesis catalyst** (nearest is Nov 18 AMC → the
  Dec 18 expiry, read on 08-19). ATM $21 straddle: call mark 0.725 (bid 0.35 /
  ask 1.10, OI 116, vol 0), put mark 0.35 (bid 0.30 / ask 0.40, OI 63, vol 1).
  **Liquidity gate: FAIL on the call leg** — spread 0.75 vs mark 0.725 (>10%,
  >2 ticks) and zero volume. Table is therefore labelled UNRELIABLE for verdict
  purposes; it is reported because it was asked for.

## 4. Valuation

Pairing unchanged: levered FCF ↔ market cap. Live inputs (stockanalysis
statistics, 2026-08-25): market cap $16,264,283,015 · EV $14,899,905,438 ·
TTM fcf $1,464,122,969 (ncfo 2,200,739,539 + capex −736,616,570) · beta −0.22
(5Y). Haircut base $1.1B and hurdle 4.74% + 0.38 × 5.14% = **6.69%** carried
from 08-19 (Damodaran as-of Aug 1, 2026).

```
uv run python -m tools.valuation.reverse_dcf --market-cap 16173081428 \
  --base-fcf 1100000000 --growth 0.06 0.06 0.06 0.06 0.06 --terminal-growth 0.025 \
  --risk-free 0.0474 --beta 0.38 --erp 0.0514
implied_discount_rate: 0.1057 (10.57%/yr)   spread_vs_hurdle: +387 bps
```
(stocks.db cap 16,173,081,428 used; the live cap is 0.56% higher → ~10.5%.)

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| conservative | $1,100M | 6% | 2.5% | **10.57%/yr** | **+387bps** |
| conservative @ beta 1.0 | $1,100M | 6% | 2.5% | 10.57% | +69bps (hurdle 9.88%) |
| truce-break bound | $1,100M flat | — | 0% | ~6.8% | ≈ hurdle |

Integrity checks unchanged (08-19 §4).

**Options-implied move** (path 2 — Robinhood stopgap; expiry 2026-09-18, 24 DTE;
ATM IV = mean(0.2248, 0.2500); closes = 90 daily bars 2026-04-17..08-25):

```
spot                                          21.40
dte (calendar days)                           24
ATM IV                                        23.74%
expected absolute move (MEAN, not a ceiling)  5.02%
1-sigma move                                  6.09%
RV60                                          24.12%
IV > RV60?                                    NO
RV20                                          33.28%
IV > RV20?                                    NO
thesis requires                               7.94%
that is                                       1.26 sigma
P(|move| >= required)                         20.943676%
refutes timing claim (> 2 sigma)?             NO
```

Read: IV is **not elevated** — below both realized windows (RV20 is inflated by
the −7.0% print day inside it). The 7.94% figure is the question's break-even,
not a thesis requirement; the thesis states no move by Sep 18. Liquidity gate
failed (§3) — UNRELIABLE, may not move a verdict. Precision: IV < 50%, so the
10.57% implied return is quotable to two decimals.

## 5. Falsifiers

Unchanged — `research/ZTO-2026-08-19.md` §5.

**Reopen trigger:** 2026-11-19: zto-q3-asp-discipline-second-installment

## 6. UNKNOWNs

Unchanged (5) — `research/ZTO-2026-08-19.md` §6. Nothing since the print
resolved or added one.

## 7. Sources

- **Primary:** none new; Q2'26 6-K and FY2025 20-F carried.
- **stockanalysis.com (vetted exception):** `/stocks/ZTO/statistics/` live
  2026-08-25 (market cap, EV, TTM fcf/ncfo/capex, beta, fcf yield).
- **Broker/market microstructure (Robinhood MCP):** equity quote and 90 daily
  bars; Sep-18 chain, $21 call/put quotes (marks, IV, OI, volume) — no
  integrated official source covers ZTO options or intraday bars.
- **Reference data:** Damodaran rf/ERP carried as-of Aug 1, 2026.
- **Point-in-time repo DBs:** `stocks.db` (cap, candidates row: roic 18.2,
  fS 6, rsi 27.5), `edgar.db` (no ZTO rows; fresh to 08-24),
  `portfolio.db` `v_latest_positions` (held symbols), `earnings.db` (no ZTO
  row inside its window; Nov 18 carried from the 08-19 run).
- **Low-confidence colour:** TipRanks/Globe and Mail buyback note; BigGo on
  the STO investigation; Bamboo Works / State Post Bureau volume and
  revenue-per-parcel figures.

## Kill-thesis record

Carried from 2026-08-19 (UNPROVEN; conditions=5, refuted=0, unknown=1). Not
re-run: no condition, falsifier, or UNKNOWN changed in six days. The single
new attack (a 24-day timing claim) is not a claim the thesis makes and was
recorded in §1 rather than adjudicated.
