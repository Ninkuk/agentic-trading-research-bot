# WB — Weibo Corporation — 2026-08-21

Price $7.04 (last trade 2026-08-21 16:00 ET; the official settled close was
only available for 2026-08-20 at $7.19) · market cap $1.73B · net cash
$769.2M · next earnings 2026-11-17 BMO (tentative)

Ticker-directed run. Unattended scheduled run. Entry path could not be
confirmed against `composite.db` / `stocks.db` — this slot has no SQLite
access (see §3).

## 1. Verdict and thesis

**PASS at $7.04.** kill-thesis: **UNPROVEN** — conditions=5 (3 probable,
2 plausible), refuted=0, unknown=1.

Weibo is genuinely cheap on cash flow and the cheapness is not an accounting
illusion: $2.64B of cash and short-term investments and ~$500M of annual free
cash flow against a $1.73B market cap. That is not the question. The question
is what fraction of that cash flow a minority ADS holder ever receives, and
the market has answered it with unusual precision — at $7.04, the price
implies you get the declared dividend ($0.61/ADS, 8.67%) and **nothing else,
forever**, which is 18bp *below* an 8.85% cost of equity. The pass says the
last five years continue: the controlling shareholder keeps ~$400M of Weibo's
cash out on a rolling intercompany loan, the payout ratio stays near a third,
and the constant-currency business keeps shrinking. On those assumptions the
return is 5.43% — 342bp short. Buying requires believing capture rises above
~31% of FCF, and the observable 2026 evidence points the other way: the
dividend was cut 26%, and a $200M buyback authorized on 2025-12-31 has no
disclosed execution eight months later.

**Closest attack:** the Cayman judgment is bullish, not bearish. Sina owes
>$1B and its main asset is Weibo stock, so it needs cash — and the pro-rata
route (a fat Weibo dividend) hands minorities their share too. The same
ruling ($105.26/share against a $43.30 merger price, a 143% uplift) also
makes a lowball Chao squeeze-out of Weibo minorities far more expensive than
it was in 2020. Minority protection arguably just went *up*. This lands
partially. It does not carry, because Sina has a second channel — the
standing intercompany loan — that costs it nothing pro-rata, and its revealed
preference across three years of loan flows and a 2026 dividend cut is for
that channel.

Load-bearing conditions of the pass:

1. *probable* — Break-even capture is ~31% of FCF. At $150M/yr (the declared
   dividend) the implied return is 8.67% vs an 8.85% hurdle (−18bp); at 40%
   capture it is 11.19% (+234bp). The whole decision is this one number.
2. *probable* — Realized capture has been ~31–33% and is falling. FY2024
   dividend $0.82/ADS (~$200M) on ~$600M FCF; FY2025 dividend $0.61/ADS
   (~$150M) on $477M FCF — a 26% per-share cut.
3. *probable* — The base business is shrinking, so the dividend being
   capitalized is shrinking too. Q2 2026 total revenue −4% and advertising
   −6% in constant currency; the +2% USD headline is RMB translation. DAU
   254M (Jun 2026) vs 252M (Dec 2025); MAU 561M vs 567M.
4. *plausible* — Retained cash is unlikely to reach minorities, because a
   controller with a >$1B judgment against him, pledged Weibo shares, and a
   standing ~$400M unsecured loan from Weibo has a cheaper non-pro-rata
   channel available. Reasoned from disclosed structure and the court's own
   findings; no 2026 primary filing read this run.
5. *plausible* — No dated catalyst forces the gap closed. The next capture
   datapoint is the FY2026 dividend declaration (~2027-03-17); the buyback
   authorization simply lapses on 2026-12-31 if unused.

## 2. Business

**Created:** Weibo is China's public square — a one-to-many broadcast feed
where the unit of value is *what is being talked about right now*, not what
your friends are doing. Users come for celebrity and IP accounts, breaking
news, and the trending-topic list (热搜), and stay for the comment threads
underneath. It is closer to X than to Douyin: the product's job is to make a
topic legible nationally within minutes. That is a real preference — 561M
people open it monthly — but it is a *low-frequency* preference. Only 45% of
monthly users open it daily (254M/561M), and management's own framing on the
Q2 2026 call was that "converting lower-frequency users remains a key
challenge," with handset pre-installation cuts creating roughly a 10%
headwind to user acquisition.

**Captured:** Three distinct businesses, not one.
(a) *Brand and performance advertising* — $381.0M in Q2 2026, 84% of revenue,
sold as promoted feed posts, trending-topic placements, and content-marketing
packages built around celebrity/IP accounts. This last is Weibo's genuinely
differentiated ad product: an advertiser buys a *conversation*, not an
impression. (b) *Value-added services* — $72.9M in Q2 2026, +19% YoY, from
memberships, games, and live/offline event proceeds. (c) *Alibaba* — a
related-party advertising relationship large enough to be called out
separately on the call (+10% in Q2, tied to AI application promotion). That
concentration is a captured-value mechanism and a dependency at the same time.

**Protected:** Weakly, and honestly the silence here is the answer. The moat
claim would be "the trending list is a national coordination point, and a
competitor cannot bootstrap one" — that is real, and it is why Weibo has held
561M MAU while its share of *time* collapsed. But it protects relevance, not
revenue: advertisers pay for attention-minutes, and those have gone to Douyin
and Xiaohongshu. The evidence is the margin line, not the user line. There is
no switching cost, no scale-economy in ad serving that Weibo wins, and no
regulatory barrier that protects Weibo specifically rather than the whole
sector.

**Operating leverage (Phase 0): negative.**

| period | revenue | GAAP operating income | margin |
|---|---|---|---|
| FY2020 | $1,689.9M | $506.8M | 30.0% |
| FY2024 | $1.75B | $494.3M | 28% |
| FY2025 | $1.76B | $464.8M | 26% |
| TTM (through Q2 2026) | $1,790.7M | $438.7M | 24.5% |

Revenue is +6.0% since FY2020; operating income is −13.4% over the same span,
and the margin has given up 5.5 points. Revenue peaked at $2,257.1M in FY2021
— TTM sits 20.7% below that peak while operating income is lower than it was
in 2020. This is a business whose top line stopped compounding five years ago
and whose cost base did not.

## 3. Threads pulled

**The Sina appraisal judgment (the thread that decided the run).** On
2025-12-31 Weibo disclosed that its controlling shareholder, Sina Corporation,
had received an adverse judgment in a Cayman Islands section 238 appraisal
proceeding arising from Sina's 2020/21 take-private by New Wave MMXV Ltd, an
entity owned and controlled by Charles Chao. The Grand Court held the $43.30
merger price undervalued Sina and set fair value at $105.26/share, producing a
judgment of **US$1,005,938,693 plus interest** — the largest section 238 award
to date. Sina appealed in April 2026; enforcement is stayed. Weibo's own
disclosure says a special committee of independent directors is "monitoring
the case and evaluating potential implications for Weibo's shareholding
structure, intercompany relationships and related-party transactions with
Sina." When a company forms a special committee to evaluate its own parent,
that is the company telling you where the risk is.

**The intercompany loan.** Weibo's 20-F disclosed short-term loans to and
interest receivable from Sina of **US$417.7M at 2024-12-31** and **US$445.2M
at 2023-12-31** — a balance that barely moves despite roughly US$3B of gross
loan flows across three years, i.e. a revolver that is continuously rolled
rather than repaid. I could triangulate the current balance without a primary
read: Weibo's 2026-06-30 balance sheet carries `receivables` of $777.834M
against `accountsReceivable` $337.565M and `otherReceivables` $43.269M,
leaving **$397.0M** unaccounted for — consistent with a ~$400M Sina balance
still standing. Sizing it against the equity: that is 23% of the entire market
capitalisation, lent unsecured to a counterparty that just lost a $1B judgment
and whose CFO testified to limited independent fundraising ability.

**Capital return, measured rather than announced.** FY2024 dividend $0.82/ADS
(~$200M, declared March 2025). FY2025 dividend $0.61/ADS (~$150M, record
2026-04-17, ADS payment on or around 2026-05-22) — a 26% per-share cut. A
$200M ADS repurchase authorization was announced 2025-12-31 running to
2026-12-31, funded from existing cash; neither the Q1 2026 (2026-05-28) nor
Q2 2026 (2026-08-19) release discloses any repurchase activity. Weighted basic
shares have gone from 226.9M (FY2020) to 239.3M (TTM) — up 5.4% — so the
multi-year direction is dilution, not retirement. I could not confirm 2026
repurchases either way from a primary filing (see §6.1).

**Cash generation vs GAAP earnings — a dead end that turned into a finding.**
The obvious bear read is "H1 2026 GAAP net income $102.1M vs H1 2025 $232.6M,
down 56%." That is true and it is misleading. Operating cash flow went the
other way: H1 2026 $214.5M (Q1 $164.0M + Q2 $50.5M) vs H1 2025 $138.1M —
**up 55%**. TTM OCF is $595.9M (Q3'25 $200.0M + Q4'25 $181.4M + Q1'26 $164.0M
+ Q2'26 $50.5M) against FY2025's $519.5M and FY2024's $639.9M. The GAAP
decline is largely non-cash: TTM `gainInvestments` is −$47.2M and equity-method
income of +$76.7M is real income but not cash. Cash generation is holding. So
the cheapness is not an earnings-quality mirage — which is precisely why the
verdict had to be decided on governance rather than on the income statement.

**The FX flatter.** Q2 2026 revenue was +2% in USD and −4% in constant
currency; advertising was −1% USD and −6% cc. Every USD figure in this
document, including the FCF base fed to the reverse DCF, carries an RMB
translation tailwind of roughly 6 points. A US owner is paid in USD so the
tailwind is not fake — but it is not operating performance, and it reverses.

**Post-print reconciliation.** The Q2 call (2026-08-19) is two days old, so
there is little to reconcile, but the price action is itself the event: the
stock closed 7.49 on print day, 7.19 on 8/20 (a fresh 52-week low, from above
$12 a year ago), and 7.04 on 8/21 — down 7.2% over two sessions on a quarter
that *beat* both lines (EPS $0.38 non-GAAP vs $0.36 estimate; revenue $453.8M
vs ~$442M). BofA cut its target to $6.50 from $7.00 on Underperform, citing
weaker macro, high e-commerce/food-delivery comps, weak handset advertising,
and lower-than-expected World Cup budgets for H2 2026. A beat that sells off
to a new low with the sell-side target *below* spot is a market voting on
something other than the quarter.

**Terminal / structural risk (20-F, FY2025).** VIEs in mainland China
contributed approximately **86% of revenues over 2023–2025**. The filing is
explicit that PRC action on VIE enforceability is uncertain, alongside data
security, anti-monopoly enforcement, and a standing HFCAA trading-ban risk if
PCAOB inspection access lapses. This is the disclosed endgame risk that any
terminal growth rate has to survive; see §4.

**Options read (mandatory):** path 2 only (Robinhood stopgap). WB is not in
the 24-symbol CBOE catalog, so path 1 is unavailable by construction, not by
a failed depth gate. Chain exists but is thin: five expirations, strikes on a
$2.50 ladder, so there is no true ATM contract for a $7.04 stock. Table and
liquidity-gate verdict in §4 — the gate **FAILED**, so the reading is
UNRELIABLE and does not move the verdict.

**Dead ends:** (a) `stockanalysis.com` has **no transcript corpus and no
operating-metrics breakdown** for WB — both `/stocks/WB/transcripts/` and
`/stocks/WB/metrics/` return the `{info}` placeholder, so the "read the single
most recent call" step ran off third-party call coverage plus the company's
own press release rather than a primary transcript. (b) **SEC EDGAR returned
HTTP 403 to every WebFetch attempt** this run, including
`data.sec.gov/submissions/` and the `Archives/` 6-K exhibits — the known
fingerprint-sensitive throttle. Every filing figure here therefore comes from
the company's own PR Newswire distribution of the same document, or from
search-surfaced quotations of the 20-F. (c) This scheduled slot grants no
SQLite access, so `sec_fundamentals.db`, `stocks.db`, `composite.db`,
`earnings.db`, and `options.db` were **all unread** — no point-in-time
cross-check on the live figures, and no confirmation of whether composite
flags WB. (d) Robinhood `get_earnings_results` shows 6 of the last 7 quarters
within ±$0.10 of estimate (Q4'25 missed by $0.06, Q2'25 beat by $0.11) — a
managed-guidance pattern with no execution blow-ups, which rules out
"the market is pricing an operational accident." Cross-check note: those
actuals are **non-GAAP** (Q2 2026 actual $0.38 = non-GAAP diluted EPS; GAAP
was $0.26), so they do not reconcile to `v_screener.eps_diluted` and should
not be compared to it.

## 4. Valuation

**Inputs and pairing.** Levered TTM free cash flow against **market cap**;
net debt is 0 by the pairing rule (`fcf = NCFO + capex` is post-interest under
US GAAP). Market cap $1,729.5M = 245.67M shares × $7.04. TTM OCF $595.9M less
FY2025 capex $42.4M as the TTM capex proxy = $553.5M. Haircuts applied to
every base: **SBC** $58.8M (the FY2025 GAAP-to-non-GAAP operating income gap;
the Q2 2026 gap was only $6.5M, so ~$26M is the current run-rate and $58.8M is
the conservative end) and **minority interest** $11.2M (TTM NCI net income —
3.5% of net income, immaterial but deducted). Conservative base uses FY2025
FCF ($519.5M − $42.4M = $477.1M) instead of TTM. Balance sheet at 2026-06-30:
cash and equivalents $1,639.148M + short-term investments $997.443M =
$2,636.591M; long-term debt $1,867.437M (convertible senior notes $325.5M,
unsecured senior notes $746.1M, long-term loans $795.8M) → **net cash
$769.154M**, 44% of market cap. Also on the balance sheet and *not* credited
anywhere below: $1,602.826M of non-current investments.

**Hurdle:** rf **4.74%** + beta **0.8** × ERP **5.14%** = **8.85%**.
Risk-free and the implied ERP are Damodaran's August 1, 2026 vintage; the ERP
is the **China total ERP** from the country-premium table (January 5, 2026
vintage), not the 4.28% US headline, because essentially all of Weibo's
revenue is Chinese. Reported beta is **0.17** — far outside the 0.8–1.2 stable
band and exactly the artificially-low print the clamp exists to catch (a
controlled, ADR-listed name whose returns are decoupled from the US market) —
so it is floored to 0.8 and the floor is stated. The mature-firm companion
(rf + 4.5% = 9.24%) sits slightly above the floored hurdle, which is a mild
argument that 8.85% is if anything too generous.

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| A — business stress | $407M | −10% | −2% | 14.94% | +609bp |
| B — business conservative | $407M | −5% | 0% | 19.62% | +1077bp |
| C — business base | $484M | 0% | 0% | 27.98% | +1913bp |
| D — business optimistic | $517M | +3% | +2% | 33.44% | +2459bp |
| E — C, net of net cash | $474.4M vs cap $960.4M | 0% | 0% | 49.40% | +4055bp |
| F — owner capture 40% of FCF | $193.6M | 0% | 0% | 11.19% | +234bp |
| G — owner capture = dividend only | $150M | 0% | 0% | 8.67% | −18bp |
| H — G with cc decline | $150M | −5% | −2% | 5.43% | −342bp |

Read A–E and F–H as two different questions. A–E ask *what are the cash flows
worth* and answer, unanimously and by absurd margins, "far more than $1.73B" —
even a −10%/yr-for-five-years-then-−2%-forever collapse on the lowest base
still clears the hurdle by 609bp. F–H ask *what does the owner receive*, and
that is where the price lives: scenario G reproduces the current dividend
yield almost exactly (8.67% vs the $0.61/$7.04 = 8.67% cash yield — a useful
arithmetic check on the perpetuity), and it sits 18bp under the hurdle. **The
break-even capture rate is ~31% of FCF, and realized capture over FY2024–25
was ~31–33%.** The market is not mispricing the cash flows; it is refusing to
capitalize the retained portion of them, and it is doing so with about one
decimal place of precision.

Integrity checks:

- **Reinvestment / terminal-ROE.** Scenarios A–C, E, F–H run terminal growth
  ≤ 0%, which claims no reinvestment and therefore owes none — the tool's
  negative `terminal_reinvestment_rate` is the arithmetic of FCF > earnings,
  not a flag. Only **D** triggered the explicit `growth without reinvestment`
  warning (2% terminal on a base FCF above earnings). The gap between FCF
  ($553.5M) and TTM net income ($318.5M) is explained, not assumed: equity-
  method income of +$76.7M is in earnings but not in OCF, TTM
  `gainInvestments` is −$47.2M of non-cash losses in earnings only, and D&A
  (~$62M/yr) exceeds capex ($42.4M). Even so, **D is not relied on** — the
  verdict rests on F–H, where the warning does not arise.
- **Market share.** D's +3% for five years puts revenue near $2.08B, roughly
  2% of China's digital advertising market. Nothing here is "bigger than the
  market"; the objection to D is that *any* growth contradicts −6% constant-
  currency advertising, not that the endpoint is implausibly large.
- **Terminal growth vs the disclosed terminal risk.** The 20-F's dominant
  structural risk — VIEs supplying ~86% of revenue under contracts of
  uncertain enforceability, plus HFCAA — is **binary, not a growth rate**.
  A 0% terminal survives it in the ordinary sense but does not price it; that
  is the honest reason the ownership call is not taken from the DCF.
- **Cash tax.** TTM effective rate 27.84% ($127.155M on $456.802M pretax) —
  a normal PRC-level rate, no NOL or deferral flattery to unwind.
- **Serial-acquirer charge:** not applicable. Weibo is not buying growth; if
  anything its investment portfolio is a drag.
- **Distribution clamp.** US median cost of capital 7.79%, with 80% of firms
  between 5.26% and 9.88% (Damodaran, Data Update 5, 2026). Scenarios C–E
  imply returns **far above the 90th percentile of the entire US cost-of-
  capital distribution** — which is not a signal that a cheap stock has been
  found, it is a signal that the market disbelieves the cash flows will reach
  the owner. Scenarios G (8.67%) and H (5.43%) sit inside the band, which is
  the tell that the leakage framing is the one the price is actually using.
- **Excess-return base rate.** Only ~29% of firms earn above their cost of
  capital (Damodaran EVA dataset). WB's `roic` was 11.9% a year ago against
  an 8.85% hurdle, but ROE has fallen from 10.73% to 8.52% over the same year
  — the excess return is fading in real time, which is the default assumption
  anyway.

**Options-implied move.** Path 2 (Robinhood stopgap) only; expiry
**2026-12-18**, **119 DTE**, which brackets the 2026-11-17 BMO Q3 print. Legs
are the $7.50 call and put — the nearest listed strike to a $7.04 spot, 6.5%
away, because the ladder is $2.50 wide. That approximation matters: the put
carries $0.46 of intrinsic value, so the straddle-derived "expected absolute
move" row is biased **high** and should not be quoted as the reading; the
1-sigma row (driven by IV) is the usable one.

| metric | value |
|---|---|
| spot | 7.04 |
| expected absolute move | 15.62% |
| 1-σ move | 18.47% |
| ATM IV | 32.34% |
| RV60 | 22.11% |
| RV20 | 22.91% |
| IV > RV60? | YES |
| IV > RV20? | YES |

**Liquidity gate: FAILED → UNRELIABLE.** Call bid $0.30 / ask $0.45 (a $0.15
spread on a $0.375 mark = 40%); put bid $0.65 / ask $0.80 ($0.15 on a $0.725
mark = 21%). Both exceed max(10% of mark, 2 ticks = $0.10). Same-day volume
was 15 contracts (call) and 0 (put), below the 100 floor; open interest 392
and 382. Both windows read "elevated," but this is the exact case the stopgap
label exists for — a 119-day IV spanning a scheduled earnings date compared
against trailing windows that contain one. **Timing check: NOT APPLICABLE** —
this thesis makes no dated move claim, so there is nothing for the 2-sigma
test to refute. ATM IV of 32.34% is below the 50% line, so the whole-percent
precision rule does not fire; the headline implied returns are nonetheless
rounded in prose because model risk dwarfs the second decimal.

Leverage gate: not run. Net debt is negative (−$769.2M net cash), book equity
is ~$4.07B positive, and there is no going-concern language — the equity is
not a call option on the firm and the DCF frame governs §1.

## 5. Falsifiers

**For the pass (flip toward buy)**

- **Shift —** Disclosed execution of the $200M ADS repurchase. Any 6-K or the
  FY2026 20-F equity note showing material 2026 repurchases lifts realized
  capture above the ~31% break-even; scenario F (40% capture) implies 11.19%,
  +234bp over the hurdle.
- **Shift —** FY2026 dividend declared at or above $0.61/ADS *and* a repeated
  or enlarged buyback — i.e. total capture above ~35% of FCF.
- **Shift —** Repayment, collateralization, or elimination of the ~$400M loan
  to Sina, or disclosure that it is secured by assets other than Weibo stock.
- **Shift —** Sina sells its Weibo stake to an unaffiliated buyer, or the
  Cayman appeal vacates the judgment. Either removes the extraction incentive;
  the first also removes the pledged-share overhang.
- **Shift —** Constant-currency advertising revenue returns to growth for two
  consecutive quarters. This does not by itself flip the verdict — capture
  still binds — but it changes the sign on the base being capitalized.

**For an owner (sell)**

- **Break —** Any *new* related-party loan, guarantee, or asset transfer to
  Sina beyond the standing balance, or the special committee disclosing an
  adverse finding.
- **Break —** A controller-led take-private proposal at or near the current
  price.
- **Break —** PRC action against the VIE structure, or an HFCAA
  re-determination that PCAOB inspection has lapsed.
- **Shift —** The FY2026 dividend cut again, or the $200M authorization
  lapsing unused on 2026-12-31.
- **Shift —** DAU below ~240M or MAU below ~540M — the level at which the
  "national coordination point" claim in §2 stops being defensible.

**Reopen trigger:** 2027-03-17: wb-fy26-capture-dividend-and-buyback

## 6. UNKNOWNs

1. **Whether any ADSs were repurchased in 2026** under the $200M
   authorization. Would come from the 6-K financial-statement exhibits or the
   FY2026 20-F equity note; SEC EDGAR returned HTTP 403 to every fetch this
   run, and neither 2026 quarterly release itemizes repurchases. Its absence
   does not kill the thesis but it *is* the decision — it is the ~31%
   break-even capture question stated in one number. This is the condition
   that makes the verdict UNPROVEN rather than SOUND.
2. **The exact amount due from Sina at 2026-06-30.** My $397.0M is an
   arithmetic inference from stockanalysis balance-sheet line items
   (`receivables` $777.834M − `accountsReceivable` $337.565M −
   `otherReceivables` $43.269M), corroborated by the 20-F-disclosed $417.7M
   (2024-12-31) and $445.2M (2023-12-31), not a primary read of the current
   related-party note.
3. **Onshore/offshore split of the $2.64B cash** and any PRC transfer
   restrictions. The 20-F discloses this; not fetched. Directly bears on how
   much of the balance could ever be distributed.
4. **Composition and marks of the $1,602.8M of non-current investments.**
   Determines whether the $76.7M of equity-method income is durable and
   whether the carrying value is realizable. Credited at zero throughout §4,
   so this can only be upside.
5. **TTM capex.** Q4 2025 capex was not separately found; §4 uses FY2025's
   $42.4M against TTM OCF. The 2026 run-rate is far lower ($15.0M in H1), so
   TTM FCF is if anything understated.
6. **H1 2025 OCF of $138.1M is derived** (FY2025 $519.5M − Q3 $200.0M − Q4
   $181.4M), not directly quoted. The +55% H1 YoY OCF comparison rests on it.
7. **The 270.266M diluted vs 245.67M outstanding share gap** — presumably
   convertible-note if-converted shares, unconfirmed. Affects per-share
   arithmetic, not the verdict.
8. **This repo's point-in-time record for WB** — `sec_fundamentals.db`,
   `stocks.db`, `composite.db`, `earnings.db`, `options.db` were all unread;
   this slot has no SQLite access. So there is no "what did the machine think
   and when" cross-check on any live figure here.

## 7. Sources

- **Primary:** Weibo Q2 2026 unaudited results (2026-08-19) and Q1 2026
  results (2026-05-28), via the company's PR Newswire distribution — revenue,
  advertising/VAS split, GAAP and non-GAAP operating income and net income,
  MAU/DAU, quarterly OCF and capex, cash and debt components; Weibo FY2025 and
  FY2024 results and annual dividend declarations (2026-03-18, 2025-03) — full
  year revenue, income, OCF, capex, dividend per ADS, record and payment dates;
  Weibo's 2025-12-31 disclosure of the Sina appraisal judgment and the $200M
  repurchase authorization; Weibo FY2025 Form 20-F risk factors (VIE
  enforceability, ~86% of revenue from VIEs, HFCAA) and the related-party note
  ($417.7M / $445.2M due from Sina), reached through search-surfaced
  quotations because EDGAR 403'd every direct fetch; Q2 2026 earnings-call
  management commentary (third-party call coverage — stockanalysis has no
  transcript for WB).
- **stockanalysis.com (vetted exception):** live `/stocks/WB/` and
  `/stocks/WB/financials/{income-statement,balance-sheet,cash-flow-statement}/`
  probes — TTM income statement and 2026-06-30 balance sheet at full
  precision, FY2020 prior column, `ttmPrior` block, shares outstanding, beta,
  PE, dividend, analyst distribution.
- **Broker/market microstructure:** Robinhood MCP `get_equity_quotes` (spot
  $7.04, prior close $7.19), `get_equity_historicals` (90 daily closes for the
  RV windows), `get_earnings_results` (8-quarter estimate-vs-actual pattern and
  the 2026-11-17 tentative date), `get_option_chains` / `get_option_instruments`
  / `get_option_quotes` (the Dec-18 $7.50 straddle). Admissible: no
  already-integrated official source in this repo covers WB's real-time quote,
  option chain, or forward analyst estimates, and this slot could not open
  `earnings.db` or `options.db` at all.
- **Reference data:** Damodaran risk-free 4.74% and implied ERP as of
  2026-08-01; country ERP table (China total 5.14%, US 4.46%) as of
  2026-01-05; cost-of-capital distribution (median 7.79%, 80% band
  5.26–9.88%), Data Update 5, 2026; excess-return base rate ~29% (EVA
  dataset).
- **Point-in-time repo DBs:** none used — no SQLite access in this slot (§6.8).
- **Low-confidence:** Cayman judgment mechanics and the $1,005,938,693 figure
  via offshore-law-firm client updates (Mourant, Maples, Collas Crill);
  Firefly Reads (Jane Moir, 2026-07-03) for the pledged-share and "no
  realistic expectation of repayment" characterizations; J Capital Research
  (2026-08-06), an avowedly critical research house, for the loan-flow and
  collateral framing; BofA's 2026-08 target cut to $6.50 (Underperform) via
  press coverage. None of these are load-bearing on their own — each claim
  they support is also carried by a primary or arithmetic source above.

## Kill-thesis record

**Ledger:** UNPROVEN — conditions=5 (3 probable, 2 plausible), refuted=0,
unknown=1.

**Per-condition adjudication**

1. *Break-even capture is ~31% of FCF* — **SURVIVED.** Attacked by trying to
   break the perpetuity arithmetic: scenario G returns 8.67%, which reproduces
   the $0.61/$7.04 cash yield of 8.67% to the basis point, so the model is not
   generating the number, the price is. Attacked again on the hurdle: the
   verdict does not depend on it. At beta 1.5 (hurdle 12.45%) the business
   scenarios A–E still clear and the capture scenarios G–H still fail; at the
   raw 0.17 beta (hurdle 5.61%) scenario G clears by 306bp and the pass would
   flip — which is exactly why the 0.8 floor and the mature-firm companion
   (9.24%) were both stated rather than buried.
2. *Realized capture ~31–33% and falling* — **SURVIVED.** The steelman is that
   the FY2025 dividend cut funded the $200M buyback, making total intended
   capture $350M (~73% of FY2025 FCF), which would be a large *increase*. It
   fails on evidence, not on logic: no repurchase is disclosed in either 2026
   quarterly release and weighted basic shares rose from 226.9M to 239.3M.
   But it fails *provisionally* — see UNKNOWN below.
3. *Constant-currency decline* — **SURVIVED.** Attacked with the USD headline
   (+2% revenue, +19% VAS, an EPS beat, and a 561M MAU base that has not
   cracked). The company's own constant-currency disclosure refutes the
   attack: −4% total, −6% advertising. Management's H2 framing ("consumer-
   demand recovery may take time") and BofA's cited H2 headwinds point the
   same way.
4. *Retained cash unlikely to reach minorities* — **SURVIVED**, at *plausible*
   tier only. This is the closest attack (below) and it is a reasoned
   inference from disclosed structure, not a measured fact. Under the
   uncertainty-never-credits rule it stays *plausible*, which is why it is
   tagged as such rather than promoted.
5. *No dated catalyst* — **SURVIVED.** Attacked by looking for one: the Q3
   print (2026-11-17) will not itemize repurchases if Q1 and Q2 did not, and
   the buyback authorization lapses silently on 2026-12-31. The first hard
   capture datapoint is the FY2026 declaration around 2027-03-17.

**UNKNOWN (1):** whether any ADSs were actually repurchased in 2026. The
evidence exists — it is in the 6-K financial statements and will be in the
FY2026 20-F — but EDGAR returned 403 to every fetch this run and no secondary
source carries the number. This is not a comfortable-but-unchecked condition;
it is the single number the verdict turns on, and it is unread. Hence
UNPROVEN, not SOUND.

**Standing checks.** *Base rate* — value traps in controlled Chinese ADRs
normally resolve by the discount persisting, not by closing; and only ~29% of
firms earn above their cost of capital (Damodaran EVA), with WB's ROE already
falling 10.73% → 8.52% year over year. *The short case* (strongest version) —
a structurally declining advertising asset whose controller has a $1B personal
judgment, pledged shares, and an established channel for moving Weibo's cash
onto his own balance sheet; BofA's $6.50 Underperform target sits below spot.
Uncomfortably, that short case *is* the pass thesis, which means this verdict
is consensus-aligned — a real weakness, since deep-value names are exactly
where consensus bearishness is most often the mistake. *Management incentives*
— Charles Chao controls Weibo through Sina's 3-vote super-voting shares and
personally controls the entity that owes >$1B. A buyback would be doubly
attractive to him (accretive at 4× earnings *and* it concentrates his stake
without spending his own money), so an authorization sitting unused for eight
months while the stock made a 52-week low is a strong revealed preference for
keeping the cash lendable. *Disconfirming search* — ran deliberately toward
the bull case (Seeking Alpha's "FCF machine trading far below its balance
sheet," the 17-analyst distribution with 7 buys and an $8.36 average target,
+18.9% above spot) and toward the strongest bullish reading of the judgment;
neither produced evidence that capture rises. *Moat as mechanism, not
checkbox* — §2 declines the "network effect" label and names what the trending
list actually protects (relevance) and what it does not (advertising revenue),
with the margin series as the evidence.

**Statistical checks.** Largely N/A — no backtest, screen, or repo signal is
load-bearing here. The one quasi-statistical claim, "realized capture ~31–33%,"
rests on **n=2 fiscal years**, which is a thin base for a perpetuity
assumption and is stated as such rather than dressed up.

**Options-timing check.** Ran and reported, but the thesis makes no dated move
claim, so the 2-sigma refutation is **NOT APPLICABLE**. Coverage disclosure:
path 2 (stopgap) only — WB is outside the CBOE catalog so path 1 is
structurally unavailable — and the liquidity gate FAILED on both legs, so the
table is UNRELIABLE and did not touch the verdict either way.

**Closest attack:** the Cayman judgment as a bullish catalyst. Sina needs
>$1B; the pro-rata route is a large Weibo dividend, which pays minorities
too; and the ruling's own arithmetic ($105.26 fair value against a $43.30
merger price) means a Chao squeeze-out of Weibo minorities would now be
priced by a court that has demonstrated it will award a 143% uplift. That is a
genuine, underpriced source of minority protection and it very nearly carries.
It does not, because the controller holds a second lever that costs him
nothing pro-rata — a ~$400M rolling unsecured loan already in place — and his
2026 revealed actions (dividend cut 26%, authorization unused) chose that
lever over the pro-rata one.

**Flip evidence, both directions.** → **SOUND** if the FY2026 disclosures show
zero 2026 repurchases and the FY2026 dividend cut again: capture is then
measured, not inferred, and condition 4 promotes from plausible to probable.
→ **FLAWED** if material 2026 repurchases surface, or the Sina loan is repaid
or collateralized: capture crosses the ~31% break-even, scenario F (+234bp)
becomes the live case, and the ownership call inverts to BUY on the same
cash-flow numbers already in §4.
