# TVGNW — Tevogen Inc. Warrant (exp 2029-02-14) — 2026-09-01

Price $0.0531 (TVGNW last, 2026-09-01 15:45 ET) · underlying TVGN $7.17
(official close 2026-09-01) · TVGN market cap $45.58M · EV $53.94M / net debt
$8.36M · next earnings 2026-11-13

Entry path: `composite` flag on **TVGNW** (`si_spike`, `sv_ratio_spike`; score
−2, coverage 0.0909). Unattended scheduled run.

## 1. Verdict and thesis

> **PASS at $0.0531.** kill-thesis: **SOUND** — conditions=4 (4 probable),
> refuted=0, unknown=0.

TVGNW is not a company. It is a 2.46-year call option on Tevogen Inc. struck
80× above the current share price, on a pre-revenue clinical-stage biotech
whose clinical program is explicitly paused for lack of money and whose
insiders are asking shareholders for authority to issue 15.6× the current
share count. After the 1-for-50 reverse split of 2026-03-06 it takes fifty
warrants plus $575.00 to buy one share of a stock trading at $7.17. The
warrant needs Tevogen to be worth roughly $3.7 billion by 2029-02-14 to pay
its holder one cent, and every financing the company must do between here and
there raises that bar without touching the strike. The warrant's own price
implies a ~0.2% risk-neutral chance of finishing in the money — and that is
before the dilution the proxy is asking for.

**Closest attack:** the draft's "running out of money" framing. Cash of
$1,082,155 against $11.57M of trailing operating burn is ~34 days, but the
Patel Family has already funded Series A, Series C preferred, a $36.0M credit
facility and a May 2026 PIPE, and $11.0M of facility capacity plus a $7.0M
KRHP grant commitment plus a $50M ATM remain. Near-term insolvency is *less*
likely than the cash line suggests, and I softened the claim. It does not
rescue the warrant: every one of those sources funds the company by issuing
equity or equity-linked claims, so the sponsor's willingness to keep writing
checks is the warrant holder's problem, not their rescue.

Load-bearing conditions (4):

1. The warrant ratio adjusted proportionally for the reverse split, so the
   effective exercise price is $575.00 per share, not $11.50. *probable* —
   the Q2 2026 10-Q states the public warrants are exercisable at $575 per
   share; the 2026-03-04 8-K said shares underlying "outstanding equity
   awards and warrants" would be adjusted accordingly; and the alternative is
   arithmetically impossible (below, §4).
2. The ~80× move required by 2029-02-14 is not achievable at any defensible
   probability. *probable* — $575 / $7.17 = 80.2×, i.e. ~494%/yr compounded
   for 2.46 years, implying a ~$3.74B market cap on today's 6.51M shares,
   roughly 3× the company's own de-SPAC valuation, against zero revenue and
   18 employees.
3. Further dilution raises, never lowers, the required move, because SPAC
   warrant terms adjust for splits and dividends but not for ordinary
   issuance. *probable* — the 2026 proxy seeks +100,000,000 shares to the
   2024 equity plan (reserve → 103,179,028, ≈15.6× the 6,416,540 shares
   outstanding at 2026-07-23), and insiders control 65.6% of the vote.
4. The underlying's funding is not secured and clinical progress is paused
   pending it. *probable* — the Q2 2026 10-Q states the company "does not
   plan to initiate another clinical trial until additional funding is
   received."

**Dominant shared risk factor:** idiosyncratic — holdings unavailable in this
session.

## 2. Business

**Created:** Nothing yet, in the economic sense. Tevogen Inc. (formerly
Tevogen Bio Holdings) is a clinical-stage specialty immunotherapy company in
Warren, NJ, founded 2021, 18 employees, developing off-the-shelf allogeneic
cytotoxic T-cell therapies under a platform it calls ExacTcell — targeting
acute viral infection, post-viral sequelae, and viral and non-viral cancers.
Its lead asset TVGN 489 completed a Phase 1 in COVID-19 with, per the company,
no dose-limiting toxicities or significant treatment-related adverse events.
There is no product, no approval, and no revenue in any reporting period since
inception. The customer today is a capital provider, not a patient.

**Captured:** Nothing. There is no revenue line on the income statement in any
period. Every dollar the company has spent has come from equity, preferred
stock, related-party debt, or grants. Cumulative evidence of the exchange
rate: $133,179,568 of paid-in capital against a $150,868,744 accumulated
deficit — the company has destroyed more than it has ever raised.

**Protected:** UNKNOWN, and honestly so. ExacTcell is a platform claim resting
on HLA/T-cell target identification, latterly with a Microsoft Azure AI
collaboration (PredicTcell). Whether the underlying biology and the patent
estate around it exclude a competitor is domain science I cannot evaluate, and
I will not bluff it. What I can bound: nothing in the public record shows a
partner paying Tevogen for the platform, and the Microsoft relationship is
disclosed through press releases with no stated economics. An unassessed moat
is not an absent moat — but at 80× moneyness the platform would have to be
worth $3.7B inside 2.5 years, and a Phase 1 safety readout is not that.

**Control:** One class of common, but effectively a controlled company. Founder
CEO and chair Dr. Ryan Saadi beneficially owns ~57.8%; directors and executive
officers as a group ~65.6%. Insider ownership reads 70.2% in `stocks.db`
against a 1,938,083-share float on 6,511,540 shares outstanding. This
forecloses an unsolicited takeover and any activist path, and — the point that
matters here — it means the 100,000,000-share equity-plan authorization on the
2026 proxy does not need a single outside vote to pass.

**Operating leverage (Phase 0): undefined — there is no revenue to lever.**
Stating a direction would be a category error, so here is the print instead:

| period | revenue | operating income |
|---|---|---|
| TTM to 2025-06-30 | $0 | −$31,249,620 |
| TTM to 2026-06-30 | $0 | −$21,402,928 |

| H1 line | H1 2025 | H1 2026 |
|---|---|---|
| R&D | $5,895,059 | $6,417,367 |
| G&A | $9,905,824 | $4,645,929 |
| net loss | $15,871,040 | $11,208,195 |
| stock-based comp | $10,532,034 | $6,138,216 |

The 31% narrowing of the operating loss is a 53% cut to G&A, not leverage;
R&D rose 9%. Note the last row: stock compensation was $6.14M of an $11.21M
half-year loss — 55% of the loss is paid in the currency the warrant is
struck against.

## 3. Threads pulled

**The entry path is a machine artifact, and that is itself the finding.**
`composite` flagged **TVGNW** — the warrant symbol, not the common — at
`coverage 0.0909`: one of eleven signals had data. The firing signals are
`si_spike` (raw 24.36 on 2026-07-31, 4.88 on 2026-08-14) and, today,
`sv_ratio_spike` (2.99). Both are bearish; `score_sum` is −2. Short-interest
and short-volume ratios on a $0.05 warrant with a thin float are noise at
this base, the effective n for any inference is one signal on one name, and
the composite score was pointing *down* anyway. The ticker layer is
microstructure-only by design (`CLAUDE.md`), and it has no guard that keeps
warrant symbols out of the scored universe. Worth a look as a data-quality
item; it is not evidence about Tevogen.

**Options read (mandatory): no listed options.** `get_option_chains` on TVGN
returns `chains: []`, and `stocks.db` carries `optionable: No`. TVGN is not in
the 24-name CBOE catalog, so path 1 (`v_iv_rank`) is structurally unavailable
too; path 2 has no chain to read. Neither path ran. In place of it, §4 inverts
Black-Scholes on the warrant's own quoted price — that is my arithmetic on a
traded warrant, not a quoted IV from any chain, and it is labelled as such
wherever it appears.

**Was the warrant left unadjusted?** This was the attack most worth running,
because if the strike were still $11.50 against a $7.17 share, TVGNW at
$0.0531 would be one of the great mispricings on the tape. It is not. The Q2
2026 10-Q states the public warrants are exercisable at $575 per share. Two
independent confirmations: the 2026-03-04 8-K said the shares underlying
"outstanding equity awards and warrants" would be adjusted accordingly, and
the arithmetic forbids the alternative — a 2.46-year call struck at $11.50 on
a $7.17 share prices near $3.70 at even 100% volatility, seventy times the
warrant's actual price, on an instrument trading 457,055 units a day.

**The dilution thread, pulled to the end.** Three separate issuances since the
reverse split, all inside seven months: 375,000 pre-funded warrants at $0.0001
(the $3.0M May 2026 Patel Family PIPE, priced at $8.00, a 14% premium);
2,245,000 restricted shares granted July 2026 at $11,075,000 grant-date fair
value — a 52.8% increase on the 4,255,107 shares outstanding at quarter-end,
in one month; and the 2026 proxy's request for 100,000,000 more plan shares.
None of these touches the $575 strike. Every one lowers the fraction of the
company a warrant's 1/50-of-a-share claim represents.

**Nasdaq listing, and the clock on it.** A minimum-bid-price deficiency
(notice September 2025) was cured by the reverse split, with compliance
confirmed 2026-03-20. Two new deficiencies opened within a month: market value
of listed securities below $50M (notice 2026-04-16, cure by 2026-10-13) and
market value of publicly held shares below $15M (notice 2026-04-17, cure by
2026-10-14). Robinhood's fundamentals feed carries
`financial_status_indicator: CC4`, `financial_status_description:
Noncompliant`. With market cap at $45.58M the first test is currently failing.
A delisting of the common would take the warrant with it.

**Access.** TVGNW is not a Robinhood-tradable instrument. Three surfaces
agree: `get_equity_quotes` silently drops the symbol, `get_equity_fundamentals`
returns it in `not_found`, and `search` returns an empty result list — which
the tool's own guide reads as "no Robinhood-tradable match." Recorded as a
fact; deliberately *not* counted as a load-bearing condition, since the pass
stands on the arithmetic whether or not the instrument is reachable.

**Dead ends.** (a) SEC EDGAR is unreachable from this session — `browse-edgar`,
`data.sec.gov/submissions`, and direct `Archives/` document URLs all returned
HTTP 403, so every filing citation here is filing content reached through a
secondary summary rather than a direct read; the Robinhood `get_sec_filing_*`
tools are not granted to this slot. (b) No transcripts exist for TVGN on
stockanalysis (`/transcripts/` returns `{info}` only), so the Phase 2
"read the latest call" step could not run and the corpus search has nothing to
search. (c) `data/short_interest.db` and `data/short_volume.db` are outside
this slot's sqlite3 grants, so the composite `si_spike` raw multiples could not
be traced back to the FINRA rows behind them. (d) A bull-case search returned
only Microsoft/Azure partnership press releases with no disclosed economics —
it ruled nothing out and confirmed nothing.

## 4. Valuation

**`reverse_dcf` refuses this input, correctly.** Run with the TTM levered flow
against market cap:

```
refused: base_fcf must be positive, got -11634422.0
```

Exit 2 — a category error, not a failure. TTM FCF is −$11,634,422 (NCFO
−$11,569,983 plus capex −$64,439) against a $45,580,780 market cap. There is
no discount rate that makes a perpetually negative flow equal a positive
price; the price is entirely an option on a future that has not started. So
the section runs the moneyness arithmetic instead, which is the honest
substitute.

**Hurdle:** rf 4.75% + beta 0.8 × ERP 4.14% = **8.06%** (Damodaran, as of
2026-09-01). The beta is clamped: the raw figure is **0.19**, which is exactly
the thin-float, insider-controlled artifact the anchors reference warns about
— a stock down 85% in a year does not have a 0.19 beta, it has a share
register too closed to co-move. The clamped 8.06% is still not a credible
hurdle for this name; a 185%-vol pre-revenue biotech dependent on one related
party belongs far above the 5.26–9.88% band that holds 80% of US firms. The
hurdle is printed for form. It does not bind anything below, because there is
no positive flow to discount.

**The moneyness table — this is the finding:**

| leg | figure |
|---|---|
| TVGNW last (2026-09-01 15:45 ET) | $0.0531 |
| warrants required per share | 50 |
| exercise price per share | $575.00 |
| all-in cost per share (50 × $0.0531 + $575.00) | $577.66 |
| TVGN spot (official close 2026-09-01) | $7.17 |
| appreciation to zero payoff | 80.2× |
| appreciation to break even on the warrant | 80.6× |
| time to expiry (2029-02-14) | 2.46 years |
| required compound annual return to zero payoff | ~494%/yr |
| implied TVGN market cap at the strike (6.51M shares) | ~$3.74B |
| implied vol backed out of $0.0531 (my arithmetic) | ~185% |
| risk-neutral P(in the money at expiry), N(d2) | ~0.2% |

Precision discipline, per the IV rule: at ~185% implied vol every figure in
the bottom third of that table is quoted to a whole percent or a single
significant figure, and the range around them is wide. The 0.2% is the shape
of the answer, not a measurement.

Two readings of that table are worth separating. The ~185% implied vol is not
a red flag — it is the market pricing this correctly. A deep-out-of-the-money,
long-dated warrant on a name like this *should* carry enormous vol, and at
185% the warrant even shows a delta of roughly 0.5 share-equivalents per fifty
warrants. What kills it is that vol this high still leaves N(d2) at 0.2%: the
convexity is real and it is already fully in the price. Buying it is not
buying cheap optionality; it is paying a fair price for a 500-to-1 shot whose
denominator grows every time the company raises money.

**Integrity checks.** The terminal-value and reinvestment machinery does not
apply — there is no base earnings, no positive FCF, and no terminal period to
grow. The market-share sentence, in its market-cap form: the strike implies a
$3.74B valuation, roughly 3× the ~$1.2B at which Tevogen de-SPAC'd in February
2024, for a company that has since shed 98.6% of its peak share price, has one
completed Phase 1 and no trial running. The distribution clamp is moot for the
same reason the hurdle is. The Item 1A terminal-risk sweep **did not run** —
EDGAR 403'd (§3, §6); from the disclosures I could reach, the dominant
structural risk is plainly the pairing of single-related-party funding
dependence with an open Nasdaq delisting clock.

**Equity as option (leverage gate fires: book equity is −$8,888,760).** The
common itself is a call on the firm, struck at the debt. Firm value = market
EV $53,941,457; debt face $10,048,000 (gross debt $9,442,832 plus ~$605k of
cumulated coupons at the $302,567 TTM interest run-rate); duration assumed 2.0
years (the Patel facility's maturity is UNKNOWN); rf 4.75%.

| vol source | firm vol | equity value | debt value | implied debt yield | P(covers debt) | option/market |
|---|---|---|---|---|---|---|
| Damodaran industry (Drugs–Biotechnology, Jan 2026, 496 firms) | 68.76% | $45,067,788 | $8,873,669 | 6.41% | 90.98% | 0.99× |
| distressed legs (equity 150%, debt 25%, D-weight 17.5%) | 125.98% | $47,393,804 | $6,547,653 | 23.88% | 54.21% | 1.04× |

Read it with the two inversions stated: volatility here is a shareholder asset
and a creditor cost, and a maturity extension is equity value. The lens is
also circular by construction — I fed it market EV because a DCF of assets in
place is not computable on a pre-revenue company, so `option/market ≈ 1.0` is
close to an identity and says nothing about whether the common is mispriced.
What it does say is which vol is credible: a 6.41% implied yield on an
unsecured related-party facility to a company with $1.08M of cash is not a
market rate, so the industry row understates this name. The distressed row —
23.88% implied yield, a 46% risk-neutral chance the firm fails to cover even
$10M of debt in two years — is the believable picture. **The option frame, not
a DCF, governs §1's ownership call**, and it governs it twice over: TVGNW is a
warrant on an equity that is itself an option on the firm, a compound option
whose inner leg has a coin-flip's chance of being worth anything at all.

## 5. Falsifiers

**For the pass (what would flip it toward buy):**

- **Break — the strike moves.** An 8-K disclosing a warrant amendment,
  repricing, or exchange offer that cuts the effective exercise price
  materially below $575, or exchanges warrants for common. This is the only
  realistic path by which TVGNW becomes an ordinary option rather than a
  lottery stub, and de-SPACs do it.
- **Shift — the underlying re-rates by an order of magnitude.** TVGN above
  ~$115 (a 16× move) would put the required further appreciation inside 5×
  and change the arithmetic class of the instrument, even though it is only a
  fifth of the way to the strike.
- **Shift — a funded, disclosed partnership.** A licensing or collaboration
  agreement with stated economics large enough to fund the pipeline without
  equity issuance would break the dilution leg (condition 3) and the funding
  leg (condition 4) at once.

**For an owner (what would confirm the sell):**

- **Break — delisting.** Failure to cure either Nasdaq deficiency by
  2026-10-13 / 2026-10-14 without an extension. The warrant follows the common
  off the exchange.
- **Break — the 100M-share authorization passes and is used.** Any material
  drawdown of the 103,179,028-share plan reserve.
- **Shift — the sponsor stops.** The Patel Family declining to fund a
  subsequent draw, or the ATM being used at a discount, against $1.08M of
  cash.

**Reopen trigger:** 2026-11-13:
tvgnw-q3-10q-warrant-exercise-price-amended-below-575-or-exchange-offer-filed-or-tvgn-above-115

## 6. UNKNOWNs

1. **Number of public and private warrants outstanding.** Would come from the
   10-Q warrant note or the 10-K cover; EDGAR was unreachable (§3). Does not
   kill the thesis — it sizes the overhang, not the moneyness, and the pass
   turns entirely on moneyness.
2. **Direct filing provenance for the $575 strike.** The figure is attributed
   to the Q2 2026 10-Q through a secondary summary, not read from the filing
   itself, because every sec.gov URL returned 403. Triangulated two other ways
   (§3) and I am confident in the fact; the *provenance* is a notch weaker
   than this repo's standard and is flagged rather than laundered.
3. **The Patel Family facility's maturity.** Assumed 2.0 years for the
   `equity_option` duration input. A longer duration raises the equity option
   value and lowers the implied debt yield; it does not move the warrant's
   moneyness at all.
4. **Whether ExacTcell is technically defensible.** Domain science I cannot
   grade (§2). Marked unassessed, not absent. It does not change the verdict
   because the required valuation is $3.7B by February 2029 regardless of how
   good the biology is.
5. **The base rate for deep-OTM de-SPAC warrants expiring worthless.** I
   believe it is very high and did not measure it, so I decline to quote a
   number. The thesis does not rest on it — the 0.2% risk-neutral figure is
   computed from this warrant's own price.
6. **Item 1A risk factors.** The 10-K sweep did not run (EDGAR 403). The
   terminal-risk read in §4 is assembled from the 10-Q and the Nasdaq notices
   instead, and is weaker for it.

## 7. Sources

**Primary:** Tevogen Q2 2026 10-Q (period ended 2026-06-30) — cash
$1,082,155, total liabilities $13,616,501, stockholders' deficit $8,888,760,
H1 R&D/G&A/net loss/SBC figures, Patel Family loan $6,400,000 drawn with
$11,000,000 available, KRHP $3.0M received / $7.0M committed, $50.0M ATM,
4,255,107 shares outstanding, July 2026 grant of 2,245,000 restricted shares
at $11,075,000 grant-date fair value, the "does not plan to initiate another
clinical trial until additional funding is received" statement, public
warrants exercisable at $575 per share, TVGN 489 Phase 1 complete with no
dose-limiting toxicities. Tevogen 8-K 2026-03-04 — 1-for-50 reverse split
effective 2026-03-06, warrants and equity awards adjusted accordingly. Tevogen
424B3 filed post-split — "$11.50 per share" cover-page text (stale
pre-split boilerplate) and the $0.0346 warrant close of 2026-03-24. Tevogen
2026 proxy (PRE/DEF 14A) — 100,000,000-share plan increase to a 103,179,028
reserve, 6,416,540 shares outstanding at 2026-07-23, Saadi 57.8% / insiders
65.6%. Tevogen May 2026 8-K/PIPE — 375,000 pre-funded warrants at $0.0001,
$8.00 issue price, 9.99% beneficial-ownership cap, $36.0M Patel facility and
Series C 7.5% cumulative preferred. Warrant terms of record — $11.50 pre-split
exercise price, exercisable from 2024-03-15, expiring 2029-02-14. Nasdaq
notices — bid-price deficiency cured 2026-03-20; MVLS below $50M (2026-04-16,
cure 2026-10-13) and MVPHS below $15M (2026-04-17, cure 2026-10-14). *All
reached through secondary summaries; direct EDGAR reads returned HTTP 403 (see
UNKNOWN 2).* Nasdaq corporate-action alert ECA2026-132 — split effective
2026-03-06, new CUSIP 88165K200.

**stockanalysis.com (vetted exception):** `/stocks/TVGN/statistics/`,
`/financials/income-statement/`, `/financials/balance-sheet/`,
`/financials/cash-flow-statement/`, `/stocks/TVGN/` overview — TTM through
2026-06-30: opex $21,402,928, operating income −$21,402,928, net income
−$21,612,587, net income to common −$22,240,423, EPS −$6.32, NCFO
−$11,569,983, capex −$64,439, FCF −$11,634,422, SBC add-back $11,829,043,
common issued $7,164,348, net debt issued $2,000,000, cash $1,082,155, debt
$9,442,832, net cash −$8,360,677, equity −$8,888,760, BVPS −$4.157,
accumulated deficit −$150,868,744, paid-in capital $133,179,568, working
capital −$4,141,324, beta 0.19, price path (1y $45.50, max $496.84). Prior-TTM
comparatives from the same routes. `/stocks/TVGNW/` returns a layout-only
payload — the warrant is not a covered symbol. `/stocks/TVGN/transcripts/`
returns `{info}` only.

**Broker/market microstructure:** Robinhood MCP — TVGN quote (last $7.00,
official close $7.17, bid $6.01 / ask $8.01, 2026-09-01), fundamentals
(market cap $45,580,780, float 2,139,777, shares out 6,511,540, volume 2,742
vs 30-day average 7,756, 52-week $3.6364–$49.50, 18 employees, CEO Ryan Saadi,
`financial_status_indicator` CC4 / `Noncompliant`), `get_option_chains` empty,
and `search` / `get_equity_fundamentals` returning no match for TVGNW.
Admissible: no already-integrated official source covers a live warrant quote,
warrant tradability, or the Nasdaq compliance-status flag, and the option-chain
check has no other source. The TVGNW price of $0.0531 (2026-09-01 15:45 ET,
volume 457,055, 52-week $0.0253–$0.0685) is *not* from this tier — see
low-confidence below.

**Reference data:** Damodaran — implied ERP 4.14% and risk-free 4.75%, as of
2026-09-01; industry standard deviations (Drugs–Biotechnology, last updated
January 2026, 496 firms): equity 75.68%, firm value 68.76%; cost-of-capital
distribution (US median 7.79%, 80% band 5.26–9.88%); EVA base rate ~29% of
firms earning above cost of capital.

**Point-in-time repo DBs (read-only):** `composite.db` — TVGNW `ticker_scores`
(bullish 0, bearish 1–2, `score_sum` −2, `coverage` 0.0909, `in_portfolio` 0)
and `signal_values` (`si_spike` 24.36 on 2026-07-31 and 4.88 on 2026-08-14,
`sv_ratio_spike` 2.99 on 2026-09-01). `stocks.db` v_latest for TVGN, captured
2026-08-31 — price $6.98, fScore 2.0, ATR 0.4978, RSI 57.78, short float
3.03% / 58,741 shares, insiders 70.24%, institutions 1.69%,
`lastSplitType` Reverse / `lastSplitDate` 2026-03-06, `optionable` No,
`nextEarningsDate` 2026-11-13. `sec_fundamentals.db` v_screener (CIK 1860871)
— net income −$5,761,940, assets $4,727,741, liabilities $13,616,501, equity
−$8,888,760, shares 4,255,107, diluted EPS −1.52. `portfolio.db` and the
short-interest DBs were not readable in this slot.

**Low-confidence:** TVGNW's live price ($0.0531, +6.20%, volume 457,055,
52-week $0.0253–$0.0685) and the 2026-08-25 print near $0.045 come from
consumer quote aggregators, not from a broker feed or an exchange — labelled
as colour, though the verdict is unchanged anywhere in a wide band around it.
Microsoft/Azure "PredicTcell" collaboration coverage is company press-release
material with no disclosed economics.

## Kill-thesis record

**Ledger:** SOUND — conditions=4 (4 probable), refuted=0, unknown=0. The
draft's fifth condition ("TVGNW is not purchasable in this account") was
attacked successfully *as a condition* and demoted: the pass stands entirely
on the arithmetic whether or not the instrument is reachable. It survives as a
fact in §3, verified across three Robinhood surfaces.

**Per-condition adjudication:**

1. *Warrant adjusted to a $575 effective strike* — **SURVIVED.** Attack: the
   post-split 424B3 cover page still reads "each exercisable for one share of
   Common Stock for $11.50 per share," which if literal would make TVGNW near
   the money and grossly underpriced. Rebutted three ways — the Q2 2026 10-Q's
   own $575 figure, the 8-K's adjustment language, and the arithmetic (a
   $11.50-struck 2.46-year call on a $7.17 share is worth ~$3.70 at 100% vol,
   ~70× the traded price of a warrant doing 457k units a day). The cover text
   is stale boilerplate.
2. *80× move not achievable at a defensible probability* — **SURVIVED.**
   Attack: risk-neutral probability is not real-world probability, and biotech
   return distributions have fat right tails. Granted as a direction, refused
   as a rescue — the real-world probability would have to be ~30× the
   risk-neutral one to reach even a 5% chance, and the sign of that bias is
   not established for high-vol controlled microcaps.
3. *Dilution raises the bar* — **SURVIVED, and harder than drafted.** The
   attack was that the July grant is a one-off. It is not: the 2026 proxy
   seeks 100,000,000 additional plan shares (≈15.6× shares outstanding),
   insiders control 65.6% of the vote, and 375,000 pre-funded warrants at
   $0.0001 were already issued in May. Warrant terms adjust for splits and
   dividends, not for ordinary issuance.
4. *Funding not secured, clinical progress paused* — **SURVIVED with the claim
   softened.** See "closest attack" in §1.

**Standing checks.** *Base rate* — Damodaran's EVA dataset puts ~29% of firms
above their cost of capital, so persistence is a 3-in-10 proposition before
any Tevogen-specific evidence; the deep-OTM de-SPAC-warrant expiry rate is
believed very high and deliberately left unquantified (UNKNOWN 5). *The short
case* — degenerate here, since the thesis *is* the short case; the inverted
check is the strongest long case, and it is real: a controlled microcap with a
1.94M-share float, an AI-partnership narrative, a clean Phase 1 safety
readout, 185% vol and a sponsor who keeps funding could move the common
several hundred percent on one catalyst. Several hundred percent is not 8,000%.
*Management incentives* — Saadi holds 57.8% of the common and the July grant
paid insiders in shares; the proxy asks for 15.6× more. Management is
compensated in the exact currency that dilutes the warrant, and the thesis
does not ask them to act against that incentive — it assumes they act on it.
*Disconfirming search* — two ran; the bull-case sweep returned only
press-release material with no economics, and the financing sweep surfaced the
100M-share proxy, which cut against the bull case rather than for it. *Moat as
mechanism* — asked as a mechanism and answered UNKNOWN (§2, UNKNOWN 4), not
ticked as a checkbox.

**Statistical check on the entry path.** The `composite` flag that produced
this run is not evidence: coverage 0.0909 (one of eleven signals), effective n
of one signal on one name, on short-interest and short-volume ratios whose
base is a $0.05 warrant with a thin float — and the score was −2, bearish,
pointing the same way as this verdict.

**Options-timing check: N/A, disclosed.** No listed chain on TVGN
(`chains: []`, `optionable: No`) and TVGN is outside the CBOE catalog, so
neither path 1 nor path 2 could run. No timing condition was refuted by
options evidence, because none was tested. The Black-Scholes inversion in §4
is my own arithmetic on the traded warrant, not a chain-derived IV, and it is
used to describe the instrument, never to confirm the thesis.

**Closest attack:** the funding leg — the Patel Family's demonstrated
willingness to fund makes near-term insolvency less likely than $1.08M of cash
implies, and the draft overstated it.

**Flip evidence — toward FLAWED:** a filed 8-K amending the warrant exercise
price materially below $575 or offering a common-share exchange; or a
disclosed, funded partnership with economics large enough to end the equity
treadmill. **Toward SOUND (i.e. confirming):** the 100M-share authorization
passing and being drawn on, or either Nasdaq deficiency going uncured past
2026-10-13 / 2026-10-14.
