# SMOX — Horizon Small/Mid Cap Core Equity ETF — 2026-08-26

Price $30.4429 (official close, 2026-08-26) · net assets $124.16M (AUM; 4.10M
shares) · next earnings none scheduled (this is a fund, not an operating
company)

Entry path: `composite` flag — SMOX carries two bearish ticker-grain signals
(`score_sum` −3, coverage 0.18). Unattended scheduled run.

## 1. Verdict and thesis

> **PASS at $30.4429.** kill-thesis: **UNPROVEN** — conditions=5, refuted=0,
> unknown=1.

SMOX is not a business. It is an actively managed wrapper around 300 US
small/mid-cap stocks, priced at 0.75% a year against 0.05% (IJH) and 0.06%
(IJR) for the passive exposure it is ~97% made of. Its 300 names come out of a
~1,093-stock eligible universe (IJH 414 + IJR 679) at 0.7–1.3% each, with a
portfolio P/E of 19.83 sitting neatly between IJR's 18.63 and IJH's 21.81 —
that is an optimized index tilt, and a portfolio that tracks its benchmark
closely cannot plausibly out-earn a certain ~70bp fee gap. The base rate agrees:
86.18% of Mid-Cap Core funds and 83.46% of Small-Cap Core funds underperformed
their S&P benchmarks over ten years. There is nothing here to own that cannot
be owned for a fifteenth of the price.

**Closest attack:** the risk-adjusted base rate stacked on the drawdown
evidence. SMOX runs a discretionary index put-spread overlay, and in the
Feb–Mar 2026 drawdown it fell −7.20% on weekly closes against IJH −8.48% and
IJR −8.42%. If the overlay genuinely suppresses volatility, then the applicable
SPIVA column is the risk-adjusted one, not the absolute one — Mid-Cap Core
80.49% and Small-Cap Core 79.92% at ten years — which lifts the prior from
~14–17% to ~20%, in exactly the direction the drawdown points. The correction
is real and I have applied it below. It does not clear 70bp of certain fee on a
single 8-week episode, but it is the attack that came closest.

Load-bearing conditions (5):

1. *probable* — **SMOX's economics decompose into SMID beta + manager skill −
   0.75%.** 97.59% US equity, 2.73% government money-market fund, 1.05% other
   assets and liabilities; 300 holdings, top-10 12.47%, largest equity position
   ATI at 1.28%. Nothing in the holdings file sits outside that decomposition.
2. *probable* — **A ~5bp passive substitute exists for the same exposure.**
   IJH 0.05% / $124.97B / 414 holdings and IJR 0.06% / $110.82B / 679
   holdings, both live since 2000-05-22, betas 1.02 and 1.03.
3. *probable* — **The prior on manager skill exceeding the fee gap is
   ~15–20%.** SPIVA US Scorecard Mid-Year 2025, as of 2025-06-30: on absolute
   return, 86.18% of Mid-Cap Core and 83.46% of Small-Cap Core funds trailed
   over ten years; on risk-adjusted return, 80.49% and 79.92%.
4. *probable* — **The 8.8-month record is not evidence of skill.** Effective
   n = 1 — one cumulative window, one regime, one drawdown. And the headline
   excess is an artifact of an assumed benchmark: +61bp vs a 50/50 IJH/IJR
   blend, +367bp vs IJH alone, −245bp vs IJR alone. The prospectus names no
   index, so the sign of the number is chosen by the analyst.
5. *possible* — **The put-spread overlay is not separately worth ≥70bp/yr.**
   This is the one condition I could not attack: SMOX's actual option
   positioning is not disclosed in any document I could reach. Upside option
   value, not base case — see §6.

**Dominant shared risk factor:** US domestic small/mid-cap earnings cycle —
holdings unavailable in this session.

## 2. Business

**Created:** one ticker that delivers a diversified 300-stock US small/mid-cap
portfolio with intraday liquidity, in-kind creation/redemption tax efficiency,
and a discretionary index put-spread overlay layered on top. That is a real
service — the packaging, rebalancing and tax plumbing are work the buyer would
otherwise do badly or not at all.

**Captured:** through exactly one lever. A 0.75% unitary management fee on net
assets, accrued daily, paid to Horizon Investments, LLC. No 12b-1 fee, no
performance fee, no waiver, and "Other Expenses" stated at 0.00% — the unitary
structure means the adviser absorbs fund operating costs and pays the
sub-adviser, Exchange Traded Concepts, LLC, out of that same 0.75%. At current
size that is **$931,205 a year**, which is **14.9% of the fund's $6.26M of
look-through portfolio earnings**. The critical point for a buyer: this
capture mechanism is not one you own, it is one you pay. The prospectus's own
example is **$930 of cost per $10,000 over ten years**; IJH's 0.05% costs
roughly $64 over the same span on the same 5% assumption. The gap, ~$866 per
$10,000, is 8.7% of the initial stake, and it is certain.

**Protected:** nothing protects the *shareholder*. There is no mechanism
stopping any issuer from launching an identical multi-factor SMID ETF tomorrow
— the strategy is described in a public prospectus in four paragraphs, and its
inputs (value, momentum, quality, volatility, sentiment) are the five most
widely replicated factors in the industry. What protects *Horizon Investments*
is distribution: adviser-platform shelf space across a 16-ETF and 12-mutual-fund
lineup, three of which launched in December 2025. That moat, such as it is,
accrues to the private adviser, not to SMOX holders. Honest answer: **no moat.**

**Control:** ETF shareholders have no vote over the portfolio. Oversight sits
with the Horizon Funds board of trustees; the adviser states outright that the
Fund's "investment strategies, including its use of options, are subject to
change based on Horizon's ongoing assessment of market conditions." Only the
80%-of-net-assets small/mid-cap policy is name-rule protected (60 days' notice).
This is worse than the null answer: the holder has no control *and* the strategy
is explicitly mutable underneath them. The only lever is to sell — into a tape
that trades ~$120k a day.

**Operating leverage (Phase 0): not applicable — category refusal, restated.**
A fund has no revenue and no operating income; the income statement the Phase 0
print reads does not exist for SMOX. The nearest true analogue runs the wrong
way for the buyer: the 0.75% fee scales with assets, so every dollar of AUM
growth accrues 0.75% to Horizon Investments and nothing to the shareholder's
per-share economics. Direction, stated explicitly: **structurally negative for
the shareholder** — there is no operating leverage that accrues to a fund
holder, only fee leverage that accrues to the adviser. The look-through
substitute for the print: portfolio P/E 19.83 → $6.26M of trailing earnings
against $124.16M of net assets, of which $931,205 a year is taken as fee.

## 3. Threads pulled

- **The composite flags that brought this here are false positives by
  construction — and the mechanism is even cleaner than ETF plumbing.**
  `si_spike` fired at `base_ratio` 4.33 (settled 2026-07-31, 26 days stale
  against a 25-day budget) and `sv_ratio_spike` at `spike_ratio` 1.699 (dated
  2026-08-26); `score_sum` −3 on coverage 0.18, i.e. 2 of 11 signals populated.
  Both signals measure a ratio against the ticker's *own* trailing base — and
  SMOX has been listed for 8.8 months, so it has no stable short-interest base
  for a ratio to be taken against. On top of that, ETF short interest and
  FINRA short volume are dominated by authorized-participant and market-maker
  create/redeem mechanics rather than directional bets: at 4.10M shares
  outstanding and ~5k shares a day of tape, one institutional print handled as
  a short sale mechanically clears the 1.6 threshold. And nobody shorts a
  $124M SMID fund directionally when IJH and IJR offer the same exposure at
  $100B+ of liquidity and trivial borrow. This is a finding about the pipeline,
  not about SMOX: `CLAUDE.md` already documents composite's ticker layer as a
  microcap dislocation scanner, but does not yet say the universe should
  exclude ETFs.
- **The adviser's incentive is asset gathering, and the structure says so.**
  0.75% × AUM, no performance fee, sub-advised by Exchange Traded Concepts —
  a white-label operator whose business is standing up other firms' ETFs.
  Horizon ran a 2025 buildout capped by three December launches and now fields
  16 ETFs against roughly $124M in this one. A shelf-space strategy is paid for
  breadth, not for alpha, and the same economics that make a subscale fund
  worth launching make it worth closing.
- **The drawdown evidence, decomposed.** Peak-to-trough on weekly closes,
  2026-02-16 → 2026-03-16: SMOX −7.20% (27.858 → 25.8517), IJH −8.48%, IJR
  −8.42%, SPY −5.70%. Of the ~1.25pp gap, the 3.78% cash-and-other sleeve
  mechanically explains ~0.32pp (3.78% × 8.45%). The remaining ~0.93pp is
  unattributed between stock selection and the overlay, and I cannot split it.
  Note also that my first instinct — "a net-short put spread must hurt in a
  drawdown" — was too confident: the long lower-strike leg caps the spread's
  loss, so in an 8% decline the overlay's drag is plausibly near zero rather
  than clearly negative. The evidence does not settle this either way.
- **The strategy has a predecessor, and I could not read its record.** Horizon
  runs a Multi-Factor Small/Mid Cap *mutual* fund (HSMIX / HSMNX / HSMBX,
  Investor Class inception 2022-12-20, Advisor Class 2023-03-07, net expense
  1.09–1.22%) built on the same value/momentum/quality/volatility/sentiment
  process over the same S&P 400/600 ranges. Its ~3.5-year live record is the
  single most decision-relevant piece of evidence available on whether this
  process adds value, and it is out of reach this session: SEC EDGAR returned
  403 to every fetch (497K, 497, `browse-edgar`), the Horizon fund page shows
  "TBD" in every performance cell, stockanalysis has no route for the symbol
  (`/quote/mutf/HSMIX/` returns zero data nodes), and the one third-party page
  reachable dropped the connection. Recorded as UNKNOWN #1, not filled with a
  guess. The one figure that did surface — a 3-year return of 19.60% — is
  useless without the benchmark beside it, and is low-confidence besides.
- **Options read (mandatory): no listed options on SMOX.** The Robinhood
  chain query returned an empty `chains` array — there is no options market on
  this ticker, so neither path 1 (CBOE `iv30` from `data/options.db`) nor path
  2 (the broker stopgap) can run. §4 records this in place of the
  implied-move table. Not to be confused with the fund's *internal* use of
  options, which is a different object entirely and is treated in §6.
- **The provider attribution on the vetted source is wrong.** stockanalysis
  tags SMOX's `provider_page` as `horizon-kinetics`. The SEC-filed summary
  prospectus names the adviser as **Horizon Investments, LLC** (Charlotte, NC;
  horizonmutualfunds.com), which is a different firm from Horizon Kinetics
  (Murray Stahl's shop, NASDAQ: HKHC). The tag would have routed a reader to
  the wrong manager's track record and the wrong investment philosophy —
  Horizon Kinetics runs famously concentrated portfolios, the opposite of a
  300-name 12.47%-top-10 fund. Primary filing wins.
- **Dead ends.** (a) The fund's own website carries no performance, holdings,
  premium/discount or spread statistics — every cell reads "TBD" nine months
  after launch, so the issuer disclosed nothing the prospectus did not.
  (b) No portfolio turnover rate exists anywhere: inception postdates the
  November 30, 2025 fiscal year end, so the first one arrives with the first
  annual report. (c) `data/stocks.db` and `data/sec_fundamentals.db` have no
  SMOX row — both are US *operating-company* universes and an ETF is correctly
  absent; this ruled out the point-in-time cross-check rather than revealing a
  gap. (d) `data/short_interest.db` and `data/short_volume.db` are not granted
  to the headless slot, so the absolute short-interest level behind the
  `si_spike` flag stays unverified — the composite view supplied the ratio but
  not the level. (e) `data/portfolio.db` is likewise ungranted, so the §1
  factor-overlap count could not be run.

## 4. Valuation

**Inputs and pairing.** A reverse DCF on a fund is a category stretch and is
labelled as one: SMOX has no free cash flow of its own, only a claim on 300
companies' earnings. The honest substitute is a *look-through* run. Portfolio
P/E 19.83 against $124,160,644 of net assets gives **$6,261,977 of trailing
look-through earnings**; that flow is paired with net assets, and net debt is
zero by construction (a fund holds no debt). This is a market-level DCF, not a
company DCF — treat the *sign* of the spread as the finding and the absolute
level as soft. The one haircut that matters is the fee: 0.75% of net assets is
$931,205, so the shareholder's actual claim is **$5,330,772**.

**Hurdle.** rf 4.74% + beta 1.03 × ERP 4.28% = **9.15%** (Damodaran, as of
2026-08-01). SMOX publishes no beta — the fund is too young — so beta is taken
from its passive twins, IJH 1.02 and IJR 1.03, which sit inside the 0.8–1.2
stable band and need no clamp. Judgment call, stated: using the benchmark's
beta for a fund that tracks the benchmark closely is the least-assumption
choice available.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| Look-through earnings, gross of fund fee | $6.262M | 5.0% | 2.5% | 8.26% | −89bp |
| Same portfolio at a passive 0.055% fee | $6.194M | 5.0% | 2.5% | 8.20% | −95bp |
| **Net of SMOX's 0.75% fee (what a holder gets)** | **$5.331M** | **5.0%** | **2.5%** | **7.41%** | **−173bp** |
| Payout-based, 50% reinvestment charged | $3.131M | 5.0% | 2.5% | 5.40% | −375bp |

The fee's whole cost, expressed as return: **85bp** (8.26% → 7.41%) — slightly
more than the 75bp headline, because the fee is a perpetual claim on a growing
flow. Note that the passive-fee row lands within 6bp of the gross row, which is
the point: the choice is not between 8.26% and 7.41%, it is between 8.20% and
7.41%.

**Integrity checks.**

- *Reinvestment / terminal-ROE warning, answered.* The first run tripped the
  tool's `growth without reinvestment` warning — base FCF equal to base
  earnings leaves nothing retained, yet terminal growth was 2.5%. The
  payout-based row answers it: charging a 50% reinvestment rate drops the
  implied return to 5.40% and prints `implied_terminal_roe` 5.0%, well below
  the 9.15% hurdle, i.e. that configuration assumes the underlying companies
  destroy value forever. Neither extreme is right — a real SMID cohort earns
  roughly 10–12% on equity and retains ~25% to fund 2.5% terminal growth. The
  truthful read is a **range of 5.4%–8.3% gross**, with the fee taking ~85bp
  off whichever point in it is correct. Every point in the range sits below
  the 9.15% hurdle.
- *Market-share sentence.* Not applicable in the usual form — there is no
  company growing into a market. The structural analogue: at 5% nominal
  earnings growth for five years the look-through earnings reach $7.99M
  against $124.16M of assets, a 6.4% earnings yield. Nothing here needs the
  underlying companies to take share from anyone; that is the one respect in
  which this forecast is safer than a single-name one.
- *Terminal growth vs the disclosed terminal risk.* Item 1A has no counterpart
  in a fund prospectus; the equivalent sweep is the Principal Risks section,
  and the dominant structural one there is **New Fund Risk** — verbatim, "no
  assurance that the Fund will grow to or maintain an economically viable
  size." That is a terminal risk in the literal sense: the terminal value of a
  fund that closes is a taxable liquidation, not a perpetuity. SPIVA Report 2
  puts five-year survivorship at 85.57% for All Mid-Cap and 84.80% for All
  Small-Cap funds; at $124M the fund is above the usual closure threshold but
  not comfortably. 2.5% terminal growth survives this only because it is a
  claim about the *underlying companies*, which persist whether or not the
  wrapper does — the wrapper's own failure mode is a transfer cost, not a
  growth cut. Stated rather than assumed.
- *Distribution clamp.* The net-of-fee 7.41% sits inside Damodaran's 5.26%–
  9.88% 80% band but **below the 7.79% US median cost of capital**. Not a
  strong-pass trigger on its own; combined with the certain fee it is
  directionally consistent with the verdict rather than independent evidence
  for it.
- *SBC / minority-interest / cash haircuts.* None apply — a fund has no share
  compensation and no consolidated subsidiaries. The 2.73% money-market sleeve
  is the cash analogue and is small enough to leave in the base rather than
  net out; doing so would raise the implied return by roughly 20bp and change
  nothing.

**Options-implied move: no listed options.** `get_option_chains` for SMOX
returns an empty chain list, so neither path 1 (CBOE `iv30` percentile from
`data/options.db`) nor path 2 (the Robinhood stopgap) is available, and the
metric table is replaced by this sentence. The timing check is inapplicable in
any case: this thesis makes no dated claim. The IV precision rule therefore
never engages — but the §4 numbers are quoted to two decimals only because the
arithmetic is deterministic, not because the *forecast* is that precise; see
the 5.4%–8.3% range above.

**Equity as option:** omitted — a fund carries no debt, so the Phase 4 leverage
gate does not fire.

## 5. Falsifiers

**For the pass (what would flip it toward buy):**

- **Break — the put-spread overlay turns out to be a real, systematic,
  materially-sized position with a measurable contribution.** The first Form
  N-CSR annual report (fiscal year ending 2026-11-30) carries the full
  schedule of investments including the derivatives table. A continuously
  maintained spread of meaningful notional, plus a stated benchmark the fund
  beat net of fee, refutes conditions 1 and 5 together.
- **Shift — the predecessor mutual fund's record beats its benchmark net of
  its 1.09–1.22% fee over 3+ years.** HSMIX/HSMNX runs the same process at a
  higher fee; if it cleared that hurdle, SMOX at 0.75% is the same process
  ~40bp cheaper and condition 3's prior stops governing.
- **Shift — the fee comes down.** A waiver or a cut toward 0.35–0.40% roughly
  halves the certain drag and materially changes the arithmetic in §4.

**For an owner (what would say sell):**

- **Break — AUM falls below roughly $50M or the board files to liquidate.**
  Fund closure converts a holding into a forced taxable event on someone
  else's schedule. This is the risk the prospectus names itself.
- **Break — the adviser changes the strategy underneath the holder.** The
  prospectus reserves this right explicitly for the options sleeve; a
  materially different fund is a different decision.
- **Shift — the tracking difference vs a 50/50 IJH/IJR blend turns
  persistently negative over four or more quarters.** Net-of-fee
  underperformance is the base-rate outcome arriving on schedule.

**Reopen trigger:** 2027-01-31: `smox-first-ncsr-overlay-turnover-and-benchmark`
— the first Form N-CSR for the fiscal year ending 2026-11-30 (due ~60 days
after), which is the earliest document that must disclose the derivatives
schedule, the portfolio turnover rate, and a full-period return against a
named index. Every one of those three is an UNKNOWN today.

## 6. UNKNOWNs

1. **The predecessor strategy's live record.** HSMIX/HSMNX/HSMBX, ~3.5 years,
   same process. Would come from the Horizon Funds Form 497K or the Form
   N-CSR annual report on SEC EDGAR. EDGAR returned 403 to every attempt this
   session (a known fingerprint-sensitivity issue for this repo's HTML
   fetches, not a missing filing). **Does its absence kill the thesis?** No —
   it is the strongest available evidence *for* the fund, so its absence
   leaves the base rate governing, which is where the PASS already sits. But
   it is exactly the evidence that could flip the verdict, and a human with
   working EDGAR access should pull it before dismissing the name for good.
2. **SMOX's actual option positioning — size, tenor, whether it is on at
   all.** The Aug 12, 2026 holdings file shows no option line in the top 25,
   but the top 25 covers only ~22% of the fund and a short option's negative
   market value could net into the 1.05% "other assets and liabilities" line,
   so absence there proves nothing. Would come from the N-PORT schedule of
   investments or the first N-CSR. **Does its absence kill the thesis?** It is
   what makes the verdict UNPROVEN rather than SOUND. It does not change the
   PASS — under uncertainty you do not pay 70bp for a feature you cannot
   confirm exists — but it does mean condition 5 was never actually tested.
3. **The fund's stated benchmark.** The prospectus names none; it defines the
   universe by the *cap ranges* of the S&P MidCap 400 and SmallCap 600 without
   committing to either index or a blend. This is why §1's excess-return figure
   swings from −245bp to +367bp depending on the blend assumed. Would come from
   the first annual report, which is required to show a broad-based index
   comparison. **Does its absence kill the thesis?** No, but it makes any
   performance claim about this fund — including a favourable one — currently
   unfalsifiable.
4. **Portfolio turnover.** None disclosed; inception postdates the fiscal year
   end. Matters because the prospectus flags "frequent trading" as a principal
   strategy and a principal risk, and turnover in a taxable account is a
   second cost line on top of the 0.75%. Would come from the first N-CSR.
   **Does its absence kill the thesis?** No — it can only make the PASS
   stronger.
5. **The absolute short-interest level behind the `si_spike` flag.**
   `data/short_interest.db` is not granted to the headless slot; composite
   supplied the 4.33 ratio but not the shares-short level. **Does its absence
   kill the thesis?** No — the flag is not load-bearing for the ownership call
   in either direction, and §3 gives an inception-date mechanism for why the
   ratio is uninformative that does not depend on the level.
6. **Sector weights beyond the top line.** Industrials 22.38%, US 97.59%; the
   remaining ten sector weights exist in the source but the repo's probe
   collapses lists to their first element and cannot enumerate them.
   **Does its absence kill the thesis?** No — decorative at 300 holdings and a
   1.28% maximum position.
7. **The §1 factor-overlap count.** `data/portfolio.db` is ungranted in an
   unattended slot, so held symbols could not be read and the shared-factor
   overlap could not be computed. Stated refusal, not an omission.

## 7. Sources

- **Primary:** Horizon Small/Mid Cap Core Equity ETF Summary Prospectus dated
  March 29, 2026 (SEC Form 497K, filed by Horizon Funds; retrieved from the
  issuer at `horizonmutualfunds.com/assets/docs/`) — fee table (0.75%
  management / None 12b-1 / 0.00% other / 0.75% total), the $77/$240/$417/$930
  expense example, principal investment strategy including the put-spread and
  FLEX-options language, the ≥80% names-rule policy, principal risks including
  New Fund Risk and Quantitative Model Risk, adviser Horizon Investments LLC,
  sub-adviser Exchange Traded Concepts LLC, portfolio managers Scott Ladner /
  Mike Dickson / Zachary F. Hill / Clark Allen, NYSE Arca listing, and the
  absence of a turnover rate and performance history. Issuer fund page
  `horizonmutualfunds.com/smcc-fund.html` — inception 12/02/25, "TBD"
  performance and holdings cells, the "tactical use of put spreads" framing.
- **stockanalysis.com (vetted exception):** SMOX net assets $124.16M, expense
  ratio 0.75%, shares outstanding 4.10M, portfolio P/E 19.83, 300 holdings,
  top-10 12.47%, holdings file dated Aug 12, 2026, top-25 holdings and weights,
  Industrials 22.38%, US 97.59%, inception Dec 2 2025, dividend $0.0201 paid
  2025-12-26, category "Mid-Cap Blend"; IJH 0.05% / $124.97B / 414 holdings /
  P/E 21.81 / beta 1.02 and IJR 0.06% / $110.82B / 679 holdings / P/E 18.63 /
  beta 1.03, both inception 2000-05-22. Also the `provider_page:
  horizon-kinetics` mis-tag recorded in §3.
- **Broker/market microstructure:** Robinhood MCP — official close $30.4429 on
  2026-08-26 and the off-hours 15.23 × 45.69 quote; weekly dividend-adjusted
  OHLCV bars for SMOX/IJH/IJR/SPY from 2025-12-01 used for the since-inception
  and drawdown arithmetic; and the empty option-chain result. Admissible here
  because no already-integrated official source in this repo covers an ETF's
  price history, quote, or options availability — `stocks.db` and
  `sec_fundamentals.db` are operating-company universes and carry no SMOX row.
- **Reference data:** Damodaran implied ERP 4.28% and risk-free 4.74%, as of
  2026-08-01, from the NYU Stern home page; US median cost of capital 7.79%
  with an 80% band of 5.26%–9.88% (Data Update 5, 2026, via
  `references/damodaran-anchors.md`). S&P Dow Jones Indices, *SPIVA U.S.
  Scorecard Mid-Year 2025*, data as of 2025-06-30 — Report 1a (absolute
  return) and Report 1b (risk-adjusted return) 10- and 15-year underperformance
  rates for All/Core Mid-Cap and Small-Cap funds, and Report 2 five-year
  survivorship.
- **Point-in-time repo DBs:** `data/composite.db` — `v_latest_scorecard` for
  SMOX (bullish 0, bearish 2, score_sum −3, coverage 0.1818, worst staleness
  26.0 days, in_portfolio 0) and `v_signal_detail` (`si_spike` 4.33087 / score
  −1 / obs 2026-07-31 / 26.0 days; `sv_ratio_spike` 1.69857 / score −2 / obs
  2026-08-26 / 0.0 days). `data/stocks.db` and `data/sec_fundamentals.db`
  confirmed to carry no SMOX row. `data/short_interest.db`,
  `data/short_volume.db` and `data/portfolio.db` not readable in this slot.
- **Low-confidence:** a third-party summary reporting a 19.60% three-year
  return for the predecessor mutual fund, quoted in §3 only to record that it
  is useless without a benchmark; an ETF-industry news item noting Horizon
  capped a 2025 buildout with three December launches.

## Kill-thesis record

**Ledger:** UNPROVEN — conditions=5, refuted=0, unknown=1.

**Per-condition adjudication.**

1. *Economics decompose into SMID beta + skill − fee* — **SURVIVED.** Attacked
   by looking for anything in the holdings file that sits outside the
   decomposition: 97.59% US equity, a 2.73% government money-market sleeve, a
   1.05% other-assets line, 300 names, no leverage, no non-US structure, no
   securities-lending disclosure. Nothing found. The one candidate exception,
   the options overlay, is condition 5 and is adjudicated separately.
2. *A ~5bp passive substitute exists* — **SURVIVED, and strengthened by the
   attack.** I tried to make the comparator wrong. If SMOX is mid-tilted, the
   comparator is IJH at 0.05%; if small-tilted, IJR at 0.06%; the fee gap is
   ~70bp either way, so the assumption I could not verify (condition 3's
   blend) does not matter to this condition. Broader factor-SMID ETFs exist
   cheaper still, but I did not verify their fees and have not relied on them.
3. *The prior is ~15%* — **SURVIVED with a correction I am adopting.** Five
   attacks run. (a) *SPIVA measures mutual funds, not active ETFs* — partly
   fair, but the mechanism SPIVA measures is fee drag, and at 0.75% SMOX is
   not a cheap active ETF, so the mechanism applies in full. (b) *Overlapping
   windows* — within a single report the 10-year column is one window per
   fund, not a rolling series; the objection does not attach. (c) *Effective
   n* — Report 2 shows hundreds of funds per category at period start (All
   Mid-Cap 291, All Small-Cap 513 at the 5-year mark); n is real. (d)
   *Survivorship* — SPIVA corrects for it, which makes the rate harsher and
   more honest, not softer. (e) *Cherry-picking* — I quoted the two cells that
   match the fund's own category label rather than the friendliest cells, and
   I am now reporting both the absolute and risk-adjusted tables. **The
   correction:** headlining the absolute-return column while simultaneously
   arguing the fund may suppress volatility was inconsistent. On the
   risk-adjusted table the same categories read 80.49% (Mid-Cap Core) and
   79.92% (Small-Cap Core), so the prior is **~15–20%**, not ~15%. The
   condition survives at the wider number.
4. *The 8.8-month record is not evidence* — **SURVIVED, strengthened.** The
   attack was to try to make the +61bp meaningful. It cannot be: annualized
   ~82bp against a plausible 2–4% benchmark-relative tracking error over 0.73
   years gives a t-statistic of roughly 0.2–0.4. Worse for the original draft,
   the +61bp figure is an artifact — the prospectus names no benchmark, and
   the same fund is +367bp against IJH and −245bp against IJR. That finding
   cuts in the thesis's favour (the record is *less* informative than claimed)
   but it is a genuine error in the draft and is now stated in §1 and §6.
5. *The put-spread overlay is not worth ≥70bp* — **UNKNOWN.** This is the one
   that routes the verdict. The bull case is real: index put-write strategies
   have a long-documented variance-premium literature, and the Feb–Mar 2026
   drawdown (−7.20% vs −8.48%/−8.42%) is the shape a vol-suppressing overlay
   would produce. Two counters, one of which failed. The counter that holds:
   the premium argument requires *systematic, continuous* exposure, and the
   prospectus says the opposite — "may, at times, seek to generate income" and
   "may be opportunistic and vary based on Horizon's market outlook" — which
   is market timing, not premium harvesting. The counter that failed: my draft
   claim that a net-short put spread "should hurt" in a drawdown overstates
   it, because the long lower-strike leg caps the loss and the premium is
   already collected, so the overlay's drag in an 8% decline is plausibly near
   zero. Attribution attempt: the 3.78% cash sleeve explains ~0.32pp of the
   ~1.25pp gap, leaving ~0.93pp unsplit between selection and overlay. The
   evidence that would settle it — the derivatives schedule — does not exist
   in any document reachable this session (EDGAR 403 on four attempts; issuer
   site "TBD"; no option line in the visible top-25, which proves nothing at
   22% coverage). Not refuted, not credited: **unverifiable.**

**Standing checks.**

- *Base rate* — run and cited: SPIVA 10-year underperformance 86.18%
  (Mid-Cap Core) and 83.46% (Small-Cap Core) absolute, 80.49% and 79.92%
  risk-adjusted, as of 2025-06-30. Damodaran's ~29% EVA rate and the BLS
  seven-year survival rate were considered and correctly rejected as
  inapplicable — SMOX is not a firm. SPIVA Report 2's five-year fund
  survivorship (85.57% / 84.80%) is the right analogue and was used instead.
- *The short case* — inverted, because a PASS thesis's adversary is the buyer.
  The strongest long case is condition 5 and was attacked there. The literal
  short case is empty and that is itself informative: nobody borrows a $124M
  SMID fund to express a view when IJH and IJR are $100B+ and freely
  shortable, which is independent support for the §3 claim that the composite
  flags carry no directional information.
- *Management incentives* — 0.75% × AUM, no performance fee, white-label
  sub-adviser, 16 ETFs across the lineup, three launched in one December. The
  adviser is paid for gathering assets, not for beating a benchmark, and the
  thesis does not need them to act against that incentive — it assumes they
  act on it. Check supports the PASS.
- *Disconfirming search* — run genuinely and it drew blood twice: the drawdown
  comparison came out *against* the thesis and is reported at full strength in
  §1 and §3, and the hunt for the predecessor fund's record was a deliberate
  search for evidence that the process works.
- *Moat as mechanism, not checkbox* — asked and answered "no moat," with the
  mechanism named (the strategy is four paragraphs of public prospectus text
  over five commodity factors) and the real moat located where it actually
  sits, at the private adviser's distribution rather than at the fund.

**Statistical checks.**

- *Base rate is not 0.5* — satisfied by construction: the null here is the
  fund's own benchmark, which is exactly what SPIVA measures against. Equity
  drift cannot flatter this comparison.
- *Overlapping windows* — addressed for SPIVA above. For the SMOX record
  itself, the 38 weekly bars are non-overlapping but the *cumulative* return
  is one observation, which is the number that matters.
- *Multiple comparisons* — I read four cells from an 18×7 table but they were
  pre-specified by the fund's own category label, and both the absolute and
  risk-adjusted versions are now reported rather than the friendlier one.
- *Effective n* — the SMOX record is **n = 1**: one cumulative window, one
  regime (a rising SMID tape), one 8-week drawdown. Stated in §1 condition 4.
- *Mechanism vs inference* — separated explicitly in §3. "The fee is 0.75% and
  the passive twin is 0.05%" is a verifiable mechanism claim. "The manager
  will not overcome it" is an inference claim and is carried by SPIVA's null,
  not by assertion.

**Options-market timing check: N/A, both legs.** The thesis makes no dated
claim, and SMOX has no listed options chain (`get_option_chains` returned an
empty list), so neither the path-1 nor the path-2 procedure could run.
Disclosed rather than silently omitted, per the coverage rule.

**Closest attack:** stacking the risk-adjusted SPIVA column on the drawdown
evidence. If the overlay suppresses volatility, the correct base-rate column is
the risk-adjusted one (80.49% / 79.92% rather than 86.18% / 83.46%), lifting the
prior to ~20%, and the −7.20% vs −8.4% drawdown is one supporting observation
pointing the same way. The attack landed hard enough to change a number in the
thesis. It did not land hard enough to buy: ~20% is still a minority proposition
against a certain 70bp, and one 8-week episode with ~0.93pp of unattributed
excess is not a demonstrated feature.

**Flip evidence, both directions.**

- *To FLAWED:* the first N-CSR showing a continuously maintained,
  materially-sized put-spread position **and** the predecessor fund
  (HSMIX/HSMNX) beating its S&P 400/600 benchmark net of its 1.09–1.22% fee
  over three-plus years. Together those refute conditions 3 and 5 and make the
  overlay a demonstrated feature rather than a marketing line.
- *To SOUND:* the same N-CSR showing no material derivatives position (or a
  trivial one) **and** the predecessor fund at or below its benchmark net of
  fee. That closes the only UNKNOWN, and every condition then survives a real
  attack.
