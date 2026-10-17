# BCPL — BNY Mellon Core Plus ETF — 2026-10-14

Price $23.74 (official close, 2026-10-14) · market cap (fund AUM) $327.4M ·
next earnings none scheduled (a fund has no earnings).

Entry path: user-directed ticker (not on the `candidates` screen, no
`stocks.db` row, no composite flag). Unattended scheduled run.

## 1. Verdict and thesis

> **PASS at $23.74.** kill-thesis: **FLAWED** — conditions=1 (1 probable),
> refuted=1, unknown=0, pending=0, not_obtained=0.

**p(beat SPY, 63 td): 0.40** · kill-thesis: 0.38
**Disputed expectation:** the price is a bond portfolio marked to today's
curve (10y 5.21%), so nothing about the issuer is "priced in". The only way
it beats SPY over a quarter is a rate rally or an equity drawdown, which is a
macro call, not a research finding.

BCPL is not a company. It is an actively managed intermediate core-plus bond
ETF: 397 holdings of Treasuries and Treasury futures, agency MBS, foreign
sovereigns and IG/HY corporates, with 3–8 year duration and a 0.40% fee. It
has no revenue, operating income, free cash flow or moat, so every
instrument in this skill (business analysis, operating leverage, reverse
DCF, equity-as-option) is a category error here. Its forward return is
roughly yield-to-maturity minus 0.40%, plus duration × −Δyield, plus or
minus spread change. That is a rates-and-credit allocation decision. The
pass is "out of scope, and dominated on expectation by SPY", not "bad fund".

**Closest attack:** the 10y at 5.21% (fred.db, 2026-10-13) is a high carry
by recent standards, and the fund is already 10.6% off its 2026-03-02 high,
so duration upside is real if rates fall. That is still a rate forecast,
and it only flips the comparison if the decline is large or equities fall.

**Load-bearing conditions of the bull case (own BCPL to beat SPY, 63 td):**

1. Net carry plus duration P&L on the central (flat-rates) path exceeds
   SPY's expected quarter. *probable* (evidence exists today, and it stands
   against the claim): YTM ~5.96% (low-confidence, BNY page as of
   2026-07-31) less 0.40% fee ≈ 5.56%/yr ≈ 1.38%/quarter. SPY's expected
   return is rf 5.21% + a positive ERP, so the bull case needs an ERP
   below ~0.35%/yr. Exogenous paths (the rate move, the equity drawdown,
   spread change) are §4 scenario inputs, not conditions.

**Dominant shared risk factor:** US term premium / long-rate rise (a 10y
selloff hits duration and equity multiples together) — holdings unavailable
in this session.

## 2. Business

**Created:** a diversified bond portfolio in one exchange-traded share.
Monthly income ($0.0977 paid 2026-10-06) and an active manager (Insight
Investment, if this strategy matches its sister fund; UNVERIFIED for BCPL)
allocate between Treasuries, MBS, ABS, IG/HY credit and non-US sovereigns.
The holder gets intraday liquidity and lower cost than the mutual fund's A
class (0.70% net), though not cheaper than its Y class (0.40%).

**Captured:** one mechanism: a 0.40% expense ratio on AUM, about $1.3M a
year on $327M, which goes to BNY, not to BCPL holders. A holder captures
coupon carry and price change. There is no other capture to unpack.

**Protected:** no moat in the sense this skill means. Core-plus bond ETFs
are a crowded category, and BCPL's edge, if any, is manager skill, which
competitors can't copy but which is also not durable. Its own record is
nine months old (inception 2026-01-12).

**Control:** an ETF trust share. Holders vote only on fund-level matters
(adviser contract, fundamental policies). BNY as sponsor controls the
adviser relationship. There is no takeover or activist path, and none is
needed: creation/redemption keeps price near NAV.

**Operating leverage (Phase 0): not applicable.** There is no revenue or
operating-income line. The fund's only "income statement" is coupon income
minus a fixed-rate fee, which has no fixed-cost base to lever.

## 3. Threads pulled

- **Route resolution:** `/symbol-lookup/?q=BCPL` → `!BCPL` "BNY Mellon Core
  Plus ETF", type ETF. That ended Phase 0: the skill's kill criteria
  (persistent losses, leverage vs cash generation) cannot be evaluated on a
  fund, so this is a fast kill on category, not on numbers.
- **Price path:** 52-week high $26.56 (2026-03-02), low $23.02 (2026-10-07),
  close $23.74. Price is −10.6% from the high. Adding roughly $0.77 of
  distributions, total return is about −7.7%, and 1-month TR is −1.29%
  (stockanalysis). A drawdown of this size from a 3–8y-duration bond fund
  implies a large rate rise since March. Consistent with that, the 10y
  stands at 5.21%. The drawdown is the curve, not a fund-specific event.
- **Yield:** the trailing 12-month dividend yield of 3.25% (stockanalysis)
  understates, because the fund has paid only ~9 months. The latest monthly
  $0.0977 × 12 = $1.17, a 4.94% run-rate. BNY's own page (via search,
  low-confidence) shows YTM 5.96% and effective duration 6.69y as of
  2026-07-31. Robinhood's 30-day SEC yield is null.
- **Holdings (2026-10-12, top 25):** UST 4.375% 2028 7.83%, then 2y/5y/Ultra
  UST futures (5.23/4.80/3.92%) and Australian 10y futures (3.19%), many
  agency MBS pools at ~1% each, JGB 2055, gilt 2054, JetBlue 2.95% 2028,
  and Oracle 6.25% 2032. The futures overlay means notional duration is
  managed with derivatives. The HY/non-US sleeve is the "plus".
- **Sister-fund colour (low-confidence: different vehicle):** the BNY Mellon
  Core Plus Fund mutual fund (DCPYX, $2.49B, sub-adviser Insight) factsheet
  as of 2026-08-31 shows effective duration 6.74y vs Agg 5.85y. Its Class Y
  30-day SEC yield is 4.82% at a 0.40% ER, with 5-year alpha 0.53 and
  2011–Q2'26 gross excess of 1.49%/yr. BCPL is not proven to share the
  strategy, and a search snippet names the "BNY Mellon Corporate Bond Fund"
  as predecessor, so this is colour only.
- **Options read (mandatory):** no listed options. Path 1: BCPL is absent
  from `data/options.db` `v_iv_rank` (0 of 24 underlyings). Path 2: the
  Robinhood `get_option_chains` result is empty. See §4.
- **Dead ends:** `stocks.db` `v_latest` has no BCPL row (ETF, outside the
  stock universe). There is nothing in `sec_fundamentals.db`, `earnings.db`
  or `composite.db` to read, by construction. Robinhood earnings results
  don't apply. The BNY ETF product URL returned 404 to WebFetch, so the
  factsheet that resolved was the mutual fund's, not BCPL's. No news items
  appear in the stockanalysis feed.

## 4. Valuation

**Inputs:** `reverse_dcf` was not run. There is no FCF stream: a bond
fund's cash flows are coupons it passes through, and its "implied return"
is already printed as YTM. Running the solver against AUM would mean
treating the distribution as FCF, which is the category error the refusal
path exists for. Substituted arithmetic: YTM ~5.96% (low-confidence,
2026-07-31) − 0.40% ER ≈ 5.56% expected annual return on a flat curve.

**Hurdle:** compared against the equity alternative, not a cost of equity.
rf (DGS10) 5.21% (fred.db, 2026-10-13); 10-year breakeven (T10YIE) 2.35%
(2026-10-14). SPY's expected return is rf + ERP. The Damodaran implied ERP
was not fetched this run, because any positive ERP settles the sign. BCPL's
net carry sits ~35bp above the 10y. That spread is the whole credit/term
premium the fund earns, net of fee.

| scenario | base (net YTM) | 10y Δ over quarter | duration P&L (6.7y) | 63-td return | vs SPY @ rf+ERP 4% (~2.3%/qtr) |
|---|---|---|---|---|---|
| flat curve | 5.56% | 0bp | 0% | ~+1.4% | ~−90bp |
| rates −50bp | 5.56% | −50bp | ~+3.3% | ~+4.7% | ~+240bp (ex equity reaction) |
| rates +50bp | 5.56% | +50bp | ~−3.3% | ~−1.9% | ~−420bp (ex equity reaction) |
| equity −10% | 5.56% | 0bp | 0% | ~+1.4% | beats by ~1,100bp |

The ERP 4% in the column header is an illustrative round number, not a
fetched input. The sign of the flat-curve row holds for any ERP above
~0.35%.

**Integrity checks:** the reinvestment/terminal-ROE checks, the market-share
sentence and Item 1A terminal risk do not apply to a fund. Distribution
clamp: a 5.6% expected nominal return is inside the 5–10% cost-of-capital
band but below the US median ~7.8%. That is expected for a debt asset.
Credit context: IG OAS 0.83% and HY OAS 3.16% (fred.db, 2026-10-13) are
tight, so the "plus" sleeve's spread tailwind is limited and widening risk
is the asymmetric direction.

**Options-implied move:** no listed options. Path 1: not in the CBOE
universe. Path 2: Robinhood chain empty. The table is replaced by this
sentence, and the timing check is not applicable (no dated catalyst).

## 5. Falsifiers

For the pass (flip toward buy):

- **Shift —** not a research falsifier. A deliberate decision to hold bond
  duration as an allocation (e.g. a stated plan to park cash with term
  exposure) is an asset-allocation choice. It should be evaluated against
  passive core funds (fee 0.03–0.05%) and against the DFF cash benchmark in
  the scorecard, not by research-ticker.
- **Shift —** ERP compresses toward zero, i.e. SPY's earnings yield falls
  to around the 10y. Revalue the flat-curve row.

For an owner (sell):

- **Break —** the fund trades persistently at a discount to NAV, or AUM
  shrinks toward closure risk (sub-$100M).
- **Shift —** 10y rises further. Each +50bp ≈ −3.3% on ~6.7y duration.

**Reopen trigger:** none stated. An ETF is out of scope for research-ticker.

## 6. UNKNOWNs

1. **NOT OBTAINED** — BCPL's own factsheet: YTM, effective duration, 30-day
   SEC yield, HY % and non-USD %, and the named predecessor fund and its
   record. It would come from BNY's BCPL page/factsheet or the 497K
   prospectus on EDGAR. Not load-bearing: the sign of the flat-curve
   comparison holds for any YTM below ~rf + ERP + fee.
2. **UNKNOWN** — whether Insight/BNY's active selection adds value net of
   0.40% in this vehicle. Nine months is no effective n. Not load-bearing
   for "beats SPY in 63 td": manager alpha of ~0.1–0.4%/quarter cannot
   close a ~90bp expected gap.
3. Premium/discount to NAV history and creation-unit liquidity were not
   checked. The after-hours quote showed a $20.18/$27.30 spread, which is an
   overnight artifact. Regular-session volume is 308.6k shares vs a 128k
   2-week average.

## 7. Sources

- **Primary:** none obtained for BCPL itself. The BNY Mellon Core Plus Fund
  (mutual fund, DCPAX/DCPIX/DCPYX) Enhanced Fact Sheet as of 2026-08-31,
  bny.com, is a different vehicle and is used as colour only.
- **stockanalysis.com (vetted exception):** `/symbol-lookup/?q=BCPL`,
  `/etf/BCPL/` (AUM $326.40M, ER 0.40%, inception 2026-01-12, 397 holdings,
  dividend $0.77 / 3.25%, monthly, ex-date 2026-10-01, price changes, 1m TR
  −1.29%), `/etf/BCPL/holdings/` (top 25, as of 2026-10-12), all fetched
  2026-10-14.
- **Broker/market microstructure:** Robinhood MCP `get_equity_quotes` (close
  $23.74, 2026-10-14), `get_equity_fundamentals` (market cap $327,366,302;
  shares 13,778,043; 52w range; description; distribution $0.09772), and
  `get_option_chains` (empty). Admissible: no integrated official source
  covers ETF quotes or chains for this ticker.
- **Reference data:** none used. The Damodaran ERP was not fetched; see §4.
- **Point-in-time repo DBs:** `fred.db` DGS10 5.21 (2026-10-13), T10YIE 2.35
  (2026-10-14), BAMLC0A0CM 0.83 and BAMLH0A0HYM2 3.16 (2026-10-13).
  `stocks.db` has no BCPL row. `options.db` `v_iv_rank` has no BCPL row.
- **Low-confidence:** web-search summary of bny.com BCPL page (effective
  duration 6.69y, YTM 5.96% as of 2026-07-31; predecessor described as BNY
  Mellon Corporate Bond Fund Class M). The page was not rendered directly.

## Kill-thesis record

**Ledger:** FLAWED — conditions=1, refuted=1, unknown=0, pending=0,
not_obtained=0. No reopen.

**Step 1 (enumerate):** the author's draft listed four conditions: equities
lag carry, rates stable/falling, spreads hold, and manager adds value. Three
are exogenous prices (equity path, rate path, spread path) and move to §4 as
scenario inputs. Manager alpha is not load-bearing for a 63-td SPY
comparison (§6 #2). What remains is the single attackable claim: on the
central path, the fund's net carry clears SPY's expected quarter.

**Condition 1: REFUTED.** Attack: SPY's expected return ≥ rf 5.21% plus any
positive ERP. BCPL's net expected return on a flat curve is ~5.56%, using
the low-confidence YTM. The bull case therefore needs ERP < ~0.35%/yr, far
below any published implied ERP. Even if YTM is off by 50bp in the fund's
favour, the needed ERP is still under 1%. The condition fails on the
evidence that exists today. It can only be rescued by an exogenous path
(rate rally or equity drawdown), which is a forecast this skill does not
make.

**Standing checks:**
- *Base rate:* investment-grade bond indices beat US equities in a minority
  of calendar quarters, roughly a third to two-fifths over long samples
  (low-confidence, folklore-grade, not measured this run). Either way it is
  below 0.5.
- *Short case:* tight IG/HY spreads (0.83%/3.16%) leave the plus sleeve
  asymmetric to widening. 6.7y duration in a market where the 10y has
  already risen ~10% of price since March means a further selloff costs
  ~3.3% per 50bp. Also: a 0.40% fee vs 0.03% passive core funds.
- *Management incentives:* the sponsor is paid on AUM. That incentive is to
  gather assets, not to beat SPY. No conflict with the (absent) bull case.
- *Disconfirming search:* the sister fund's 5-year alpha of 0.53 and
  24th-percentile 1-year rank argue the manager is competent. That bears on
  BCPL vs peers, not BCPL vs SPY, and does not move condition 1.
- *Moat:* n/a; a fund has no moat to test.

**Statistical checks:** n/a; no backtest or signal is claimed.
**Options timing check:** skipped. There is no dated claim and no listed
chain (path 1 absent, path 2 empty).

**Closest attack (in the bull's favour):** the 5.21% 10y gives a real carry
cushion, and a recession-driven rally would hand duration ~+3% per 50bp
while equities fall. That is a macro scenario, not evidence today.

**Flip evidence:** toward SOUND, an implied ERP near zero (SPY's earnings
yield ≈ the 10y) would make carry competitive on the central path. Toward a
firmer FLAWED, BCPL's own factsheet showing YTM below ~5.6%.

**p(beat SPY, 63 td):** 0.38. This is the kill pass's own figure, set from
the sub-0.5 base rate and the negative expected spread on the central path,
before re-reading §1.
