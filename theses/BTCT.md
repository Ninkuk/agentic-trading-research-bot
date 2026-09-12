# BTCT — BTC Digital Ltd. — 2026-08-21

Price $1.15 (live quote / venue last trade 16:00 ET, 2026-08-21; consolidated
close $1.14, after-hours $1.12) · market cap $10.9M (Robinhood, 9.52M shares)
/ $13.5M (stockanalysis, 11.80M shares) · next earnings none scheduled (last
was 2026-03-31 AMC, the FY2025 annual)

Unattended scheduled run. Entry path not verifiable in this slot — the
sandbox permits no DB read (see §3), so whether `composite` flagged this or
it arrived some other way could not be confirmed; the microstructure profile
(18.70% short interest, 639× average volume on 2026-08-20) is consistent
with a ticker-layer microstructure flag rather than a quality screen.

## 1. Verdict and thesis

> **PASS at $1.15.** kill-thesis: **UNPROVEN** — conditions=5 (4 probable,
> 1 plausible), refuted=0, unknown=1.

BTC Digital mines bitcoin at a negative gross margin, burns more free cash
flow in a year than its entire market capitalisation, and funds that burn by
issuing shares. Split-adjusted, the diluted share count has gone from ~22.7k
in 2021 to 9.52M today, and on 2026-07-29 the company registered a further
18.42M shares for resale — 194% of the shares currently outstanding. The
$1.15 price is the third day of a squeeze that took the market cap from
~$4.1M to $10.9M on 639× normal volume; it is a repricing of float scarcity,
not of the business. The "AI computing infrastructure" pivot is the third
business model in five years and carries no disclosed contracted revenue.

**Closest attack:** the negative gross margin is a bitcoin-price artifact,
not a permanent property. Gross margin was +14.94% in FY2022 and +0.99% in
FY2024; it went to −22.50% in FY2025 across the post-halving period. With
bitcoin above $71,000 in August 2026, FY2026 gross margin could well be
positive again. This lands — but it damages the *inference*, not the pass:
in FY2022, the best year in the file, a +14.94% gross margin still produced
only an +8.85% operating margin and −$39.9M of free cash flow.

Load-bearing conditions for the pass:

1. *probable* — **The company cannot fund itself from operations.** FY2025
   operating cash flow −$5.258M, capex −$8.519M, free cash flow −$13.777M,
   against year-end cash of $3.744M and net cash of $1.243M.
2. *probable* — **Dilution is structural and continuing, not a one-off.**
   Derived weighted-diluted share count: 22.7k (2021) → 683k (2022) → 1.49M
   (2023) → 3.01M (2024) → 8.22M (2025); 9.52M outstanding now. stockanalysis
   states shares rose 171.98% in the last year. On 2026-07-29 an F-1
   registered 18,421,050 shares for resale.
3. *probable* — **The mining operation does not cover its own direct cost.**
   FY2025 gross profit −$3.159M on $14.041M revenue (gross margin −22.50%);
   operating margin −62.74%.
4. *plausible* — **The AI-compute pivot cannot change (1)–(3) inside the
   funding runway.** Four press releases across Jan–Jul 2026 (Fog Computing
   framework, Aurora Energy JDA, a completed 10MW Georgia site, a Chief AI
   Business Growth Officer) name no contracted revenue, no customer, and no
   capital plan. I could not read the underlying filings (SEC 403, §3) — this
   is the run's one UNKNOWN.
5. *probable* — **The current price is a float squeeze, not new information.**
   2026-08-20: +79.97% regular session to $0.84, +111.55% after-hours to
   $1.77, on 147.56M shares against ~230,900 average — 639×. 2026-08-21:
   opened $1.47, high $1.53, low $1.12, closed $1.15 (−22.45%) on 17.07M
   shares against an 8.62M float. 52-week low $0.4305 was set four sessions
   ago on 2026-08-17.

## 2. Business

**Created:** Very little that a customer pays for. BTC Digital operates
bitcoin mining machines in the United States, resells and rents mining
machines, and hosts miners for third parties (stockanalysis company
description; 26 employees). Mining creates no customer surplus at all — the
"customer" is the Bitcoin protocol, which pays an identical, externally-set
block reward to whoever presents the hash. Hosting and machine resale do
serve real customers, but what those customers buy is cheap power and rack
space, which is a commodity sold on price. The company is now attempting to
sell that same power and space to AI compute tenants instead, around a
completed 10MW site in Georgia.

**Captured:** Three mechanisms, none of them working. (i) *Mining* — captures
the block reward less energy, hosting and depreciation cost; in FY2025 that
spread was negative, −$3.159M of gross profit on $14.041M of revenue. (ii)
*Machine resale and rental* — a hardware margin on ASICs whose resale value
tracks the bitcoin price and collapses after each halving. (iii) *Hosting* —
a per-megawatt fee. There is a fourth, unstated mechanism that has in fact
funded the company: *equity issuance*. Since 2021 the company has run a
1-for-30 reverse split (May 2022), a $6.0M registered direct offering (July
2025), and a $7M PIPE with up to $21M of warrant proceeds (June 2026). That
is the only line of business that has reliably produced cash.

**Protected:** Nothing. There is no answer to "what stops a competitor
tomorrow." Hashrate is perfectly fungible, the block reward is set by
protocol and split by global hashrate, and the only durable advantage in
mining is a long-dated low-cost power contract at scale — which a company
with 26 employees, $3.7M of cash and a 10MW site does not have against
operators running gigawatts. The AI-compute pivot inherits the same problem
one rung up: 10MW is a rounding error against hyperscaler and neocloud
capacity, and the customers doing the buying have all the negotiating power.
This silence is the finding.

**Operating leverage (Phase 0): negative**, sharply. Revenue grew 18.7% from
FY2022 to FY2025 while operating income fell by $9.86M.

| FY | Revenue | Gross profit | Operating income | Net income | Free cash flow | Wtd. dil. shares (derived) |
|---|---|---|---|---|---|---|
| 2021 | n/a | n/a | −1,064,446 | −60,494,758 | −83,800,806 | 22,725 |
| 2022 | 11,831,000 | 1,768,000 | 1,047,000 | 7,686,000 | −39,921,000 | 682,780 |
| 2023 | 9,073,000 | −1,135,000 | −2,481,000 | −2,824,000 | 1,307,000 | 1,494,180 |
| 2024 | 11,675,000 | 115,000 | −2,678,000 | −1,989,000 | −1,187,000 | 3,013,636 |
| 2025 | 14,041,000 | −3,159,000 | −8,809,000 | −9,061,000 | −13,777,000 | 8,222,890 |

Margins by year confirm the direction: gross 14.94% → −12.51% → 0.99% →
−22.50%; operating 8.85% → −27.35% → −22.94% → −62.74% (FY2022→FY2025).

The share-count column is **derived** (net income ÷ diluted EPS), not
disclosed; the FY2021 figure of 22,725 split-adjusted shares against 9.52M
today implies roughly a 419× increase in five years. The exact multiple
depends on stockanalysis's split-adjustment convention and should be treated
as an order of magnitude, not a precise figure — but the May-2022 1-for-30
reverse split alone accounts for 30× of it, and the direction is not in
doubt.

## 3. Threads pulled

**The company is on its third business model in five years.** Founded 2006 in
China as an English-language tutoring business, listed via the Meten EdtechX
SPAC, and destroyed by the 2021 tutoring crackdown — FY2021 net loss
$60.5M on a split-adjusted diluted EPS of −$2,662. Renamed BTC Digital Ltd.
in August 2023 and pivoted to bitcoin mining. In July 2025 it converted its
entire bitcoin reserve to Ethereum and bought $5M more ETH. From January 2026
it has been pivoting again, to AI computing infrastructure. A company that
has changed what it does three times in five years is not a business being
compounded; it is a listing being repurposed. Nothing in this history is
disqualifying on its own — the tutoring crackdown was exogenous — but it
means no operating track record carries forward, and the FY2025 numbers
describe a business the company is already abandoning.

**The warrant overhang is larger than the float.** The June 2026 PIPE sold
6,140,350 Common Units at $1.14, each unit being one ordinary share (or
pre-funded warrant) plus **two** PIPE warrants exercisable at $1.71. The
2026-07-29 F-1 registers 18,421,050 shares for resale: 5,175,437 already
issued, 964,913 from pre-funded warrants, and 12,280,700 from the common
warrants. Against 9.52M shares outstanding and an 8.62M float, the
not-yet-issued warrant shares alone (13.25M) are 139% of the share count and
154% of the float. The structure has a nasty property for a would-be owner:
the warrants only come into the money above $1.71, so **the exact path on
which the equity works is the path that more than doubles the share count.**
The $21M of warrant proceeds the company would receive is real, but it
arrives by selling stock to insiders at $1.71 on a rally.

**The runway is roughly six months and two of them are gone.** FY2025 free
cash burn was $13.777M. Year-end net cash was $1.243M. The June 2026 PIPE
added $7M gross (call it ~$6.3M net of fees). At the FY2025 burn rate that
funds about six months from 2026-06-29 — i.e. into roughly December 2026 —
before the next financing. This is the mechanism behind condition 2: the
dilution is not a choice management is making, it is the only funding source
available. Note the direction of the arithmetic: net cash went from $15.228M
at end-2024 to $1.243M at end-2025, a $14.0M destruction in one year, while
the share count rose 171.98%.

**Today's price is four sessions old.** The 52-week low of $0.4305 was set on
2026-08-17. On 2026-08-20 the stock rose 79.97% in the regular session to
$0.84 and a further 111.55% after hours to $1.77, on 147.56M shares against
an average of ~230,900 — 639× normal — with a market cap of about $4.1M
going in. The named drivers were bitcoin up ~9% through $71,000 and the AI
pivot / Chief-AI-Officer appointment. Today it opened $1.47, printed $1.53,
and closed $1.15, down 22.45% on 17.07M shares — 1.98× the entire float in
one session. The relevant reading is not that the stock is up; it is that at
an $8.6M float and 18.70% short interest, the price is being set by
positioning, and a 22% down day on no news is what that looks like unwinding.

**The bid/ask tells the same story.** At the close the bid was $1.08 against
a $25.00 ask. A $25 ask on a $1.15 stock is a stub quote, not a market — it
means one side of the book was effectively empty. Any position here has an
exit problem that does not show up in the average-volume figure.

**Options read (mandatory):** **No listed options.** `get_option_chains` for
BTCT returned an empty `chains` array (Robinhood MCP, 2026-08-21), so neither
path applies — path 1 is unavailable regardless (BTCT is not in the 24-symbol
CBOE catalog, so `data/options.db` has no history for it), and path 2 has no
chain to read. There is therefore no implied-move table in §4 and no
options-market check on the timing of anything here. Recorded as unchecked,
not as clear.

**Dead ends.** (i) *SEC EDGAR is unreachable from this slot.* All three routes
returned HTTP 403 to `WebFetch`: `browse-edgar`, the `data.sec.gov`
submissions JSON for CIK 1796514, and direct `Archives/` exhibit URLs. So the
FY2025 20-F, the June 2026 6-K, and the July 2026 F-1 were read only through
secondary summaries — no primary filing was opened in this run. This is the
single largest gap here and it is what caps the verdict at UNPROVEN. (ii)
*No point-in-time DB cross-check was possible.* The scheduled slot's sandbox
allows no `sqlite3`, so `sec_fundamentals.db`, `stocks.db`, `composite.db`,
`short_interest.db` and `earnings.db` were all unread; the FY2025 figures
below could not be cross-checked against `v_screener.eps_diluted` as Phase 0
normally requires. (iii) *Robinhood's earnings history is unusable here.*
`get_earnings_results` returns three unverified 2025 quarters all stamped
`2026-02-24` with an identical −$0.51 estimate — placeholder rows for a
foreign private issuer that reports semi-annually. Only the FY2025 actual
(−$0.77, 2026-03-31, verified) and the FY2024 rows are real, and −$0.77 is
not comparable to stockanalysis's −$1.102 annual diluted EPS. Nothing was
learned. (iv) *Ticker confusion is a live hazard and was ruled out.* Search
results for "BTC Digital Ethereum treasury" return mostly **Bit Digital
(BTBT)**, a different and far larger company (~155,444 ETH, ~$327M, as of
2026-03-31). None of the treasury figures in this document come from BTBT
material. (v) *Nasdaq listing compliance.* The company took a bid-price
deficiency letter in September 2022, did the 1-for-30 reverse split in May
2022, and regained compliance in September 2023. I found no evidence of a
current, open deficiency — but with a $0.4305 low four sessions ago, a fresh
30-day sub-$1.00 window is plainly in play and I could not confirm its status
either way (see §6).

## 4. Valuation

**Inputs.** All FY2025 (year ended 2025-12-31), from the stockanalysis
statistics and financials `__data.json` pools: revenue $14,041,000; gross
profit −$3,159,000; operating income −$8,809,000; net income to common
−$9,061,000; diluted EPS −$1.101924; operating cash flow −$5,258,000; capex
−$8,519,000; **free cash flow −$13,777,000**; cash $3,744,000; debt
$2,501,000; net cash $1,243,000. Market cap $10,944,527 (Robinhood, on
9,516,980 shares at $1.15) — note stockanalysis carries $13,452,646 on
11,800,567 shares, an unreconciled 24% disagreement in the share count (§6).
Enterprise value $12.21M per stockanalysis, on its own higher share count.
Pairing: `fcf` on this route is a levered (equity) flow, so it pairs with
**market cap**, and net debt is 0 by the pairing rule — but the company is in
a small net *cash* position ($1.243M, 11% of market cap), so the implied
return is biased slightly low, which only strengthens the pass. No minority
interest and no SBC haircut were applied; neither could be checked without
the filings.

**Hurdle.** rf 4.74% + beta × ERP 4.28% (Damodaran, as of 2026-08-01).
stockanalysis reports beta **5.48**, far outside the 0.8–1.2 clamp band; at
the clamped 1.2 the hurdle is **9.88%**, and unclamped it is **28.19%**. The
clamp normally exists because an extreme measured beta is capturing a
squeeze rather than systematic risk — which is exactly what happened here on
2026-08-20 — but on a name whose equity may not exist in twelve months, the
unclamped figure is the more honest required return. Both are quoted below.

**`reverse_dcf` refused.** Verbatim:

```
$ uv run python -m tools.valuation.reverse_dcf --market-cap 10944527 \
    --base-fcf -13777000 --growth 0.05 0.05 0.05 0.05 0.05 --terminal-growth 0.02
refused: base_fcf must be positive, got -13777000.0     (exit 2)
```

That is the correct behaviour and it is the finding: there is no free cash
flow to discount, so no implied return exists to compare against a hurdle.
Substituting the honest arithmetic — the required-FCF inversion — the
scenario table asks what steady free cash flow the current price would need
to justify:

| scenario | base FCF | growth ×5y | terminal | implied return | vs hurdle |
|---|---|---|---|---|---|
| actual TTM (FY2025) | −$13.777M | any | any | **undefined** (solver refused, exit 2) | n/a |
| required to justify $10.94M at clamped hurdle | **+$0.862M** | n/a (perpetuity) | 2.0% | 9.88% by construction | 0 bp |
| required to justify $10.94M at unclamped hurdle | **+$2.868M** | n/a (perpetuity) | 2.0% | 28.19% by construction | 0 bp |
| required at clamped hurdle, fully diluted (22.77M sh) | **+$1.900M** | n/a (perpetuity) | 2.0% | 9.88% by construction | 0 bp |

Read the middle row as the whole valuation: to be worth today's price on the
clamped hurdle, BTC Digital must produce **$0.862M of durable, 2%-growing
free cash flow every year, forever**, starting from −$13.777M. That is a
**$14.6M annual swing — 104% of total revenue**. The fully-diluted row prices
the equity at $1.71 (where the 12.28M warrants exercise), adds the $21.0M of
warrant proceeds to equity value and takes shares to 22.77M; the required
flow roughly doubles to $1.90M.

**Integrity checks.**

- *Reinvestment / terminal-ROE warning:* not reached — the solver refused
  before any terminal value was formed, so there is no `implied_terminal_roe`
  to read two-sided and no growth-without-reinvestment warning to answer.
  Recorded as N/A by refusal, not as passed. `--base-earnings` was likewise
  not passed for the same reason.
- *Market-share sentence:* the usual form does not apply with no growth path,
  so the equivalent: earning $0.862M of free cash flow at a generous 10% FCF
  margin requires **$8.6M of profitable revenue**. The company has $14.0M of
  revenue today and it throws off −$13.8M. The problem is not scale.
- *Terminal growth vs terminal risk:* 2.0% is below the 4.74% risk-free rate,
  so the tool's cap is respected. But the honest terminal question here is not
  the growth rate, it is whether there is a year 10 at all: Altman Z-Score
  **−1.66** and Piotroski F-Score **1** (of 9). stockanalysis's own gloss —
  "a Z-score under 3 suggests an increased risk of bankruptcy" — understates
  it; −1.66 is deep in the distress zone. Applying *any* positive terminal
  growth to this business is an assumption the disclosed risk does not
  support.
- *Distribution clamp:* the US median cost of capital is ~7.8% and ~80% of
  firms sit within 5–10%. The clamped 9.88% is inside that band and the
  unclamped 28.19% is far outside it. That is not a signal about the
  discount rate; it is a signal that the equity is being priced as an option
  on survival rather than as a claim on cash flows.
- *Excess-return base rate:* only ~29% of firms earn above their cost of
  capital (Damodaran EVA dataset). There is no moat argument here to defend a
  terminal excess return, so the default fade applies with nothing opposing
  it.

**Options-implied move: no listed options.** `get_option_chains` returned an
empty chain array for BTCT (Robinhood MCP, 2026-08-21). Path 1 does not apply
(BTCT is not in the CBOE catalog, so `data/options.db` holds no history) and
path 2 has no chain to quote. There is no expected-move table, no ATM IV, and
no DTE for this name; the timing check is unavailable, not passed. Because no
ATM IV exists, the IV>50% precision rule cannot be evaluated — but with a
beta of 5.48, a 639×-volume session three days ago and a −22.45% session
today, every figure in this section should be read to the nearest whole
percent regardless.

*Equity-as-option lens: omitted.* The Phase 4 leverage gate does not fire —
debt is $2.501M against a $12.21M enterprise value (20%, well under the
half-of-EV trigger), book equity is positive (price/book 0.376, Robinhood),
and I have no going-concern language to point to because I could not open the
20-F. The distress here is a **burn-rate** problem, not a leverage problem;
creditors are not the claimants who matter. Noting for completeness that had
the gate fired, the option frame would have made the case *less* bad, not
more — volatility is a shareholder asset under that lens. The DCF frame (or
rather its refusal) governed §1's ownership call.

## 5. Falsifiers

**For the pass (what would flip it toward buy):**

- **Break — a signed, disclosed AI-compute contract with named revenue.** Not
  a framework agreement, not an MOU, not an officer appointment: a customer,
  a term, and a dollar figure in a 6-K. Four announcements across Jan–Jul
  2026 have produced none. This is the single condition that would make the
  business real, and it would flip condition 4.
- **Shift — two consecutive halves of positive gross margin AND positive
  operating cash flow.** Gross margin alone is a bitcoin-price artifact (see
  the closest attack); operating cash flow is not. FY2023 had positive
  operating cash flow of $3.808M, so this is achievable — it just has not
  co-occurred with a positive gross margin in any year in the file.
- **Shift — a financing that ends the dilution cycle**, i.e. a raise large
  enough to fund the business past cash-flow breakeven rather than for six
  months, without a warrant coverage ratio above 1×. The June 2026 PIPE was
  the opposite: 2× warrant coverage on a $7M raise.

**For an owner (what should make you sell):**

- **Break — the warrants come into the money and the resale registration goes
  effective.** Above $1.71 the 12,280,700 PIPE warrants exercise into a
  9.52M-share company. The rally and the dilution are the same event.
- **Break — a fresh Nasdaq bid-price deficiency letter, or a reverse split
  announcement.** The stock printed $0.4305 four sessions ago; the company
  has done this once before (1-for-30, May 2022). A reverse split here is not
  a technicality, it is the marker of another round of the cycle.
- **Shift — cash falls below one quarter of the prior-half burn** in the next
  interim report, which forces the next raise into whatever price the market
  is offering.
- **Shift — a fourth pivot.** Whatever it is called.

**Reopen trigger:** event:btct-signed-ai-compute-contract — a 6-K disclosing
a named AI-compute customer with contracted revenue, or an interim report
showing positive operating cash flow in a half with positive gross margin.

## 6. UNKNOWNs

1. **Everything in the primary filings.** SEC EDGAR returned HTTP 403 on all
   three access routes tried (`browse-edgar`, `data.sec.gov/submissions`,
   direct `Archives/` exhibits), so the FY2025 20-F, the June 2026 6-K and
   the July 2026 F-1 were never opened. It would come from EDGAR from a slot
   with working access, or from a `fundamentals`/`edgar` screener run against
   CIK 1796514. **Does its absence kill the thesis?** No — it caps the
   verdict at UNPROVEN rather than SOUND, but the FY2025 income statement,
   cash flow and balance sheet are all available through stockanalysis (which
   sources S&P Global) and every load-bearing number in §1 rests on those.
   What is genuinely lost is management's own framing: the going-concern
   discussion, the Item-3D risk factors, related-party transactions, and
   management compensation.
2. **The current share count.** Robinhood reports 9,516,980 shares
   outstanding and stockanalysis 11,800,567 — a 24% disagreement, and neither
   obviously reflects the 5,175,437 shares issued in the June 2026 PIPE. It
   would come from the F-1 cover page or the latest 6-K. **Absence does not
   kill the thesis:** every figure in §4 is quoted on the lower (Robinhood)
   count, which is the *charitable* one — a higher count makes the
   required-FCF-per-share arithmetic worse, not better.
3. **Whether a Nasdaq bid-price deficiency is currently open.** The 52-week
   low of $0.4305 was set 2026-08-17 and the stock has traded below $1.00 for
   an unknown span before that. The 30-day clock and any notification letter
   would be in a 6-K. **Absence does not kill the thesis** — it is
   confirmatory of a pass either way — but an owner would need it.
4. **Any FY2026 financial data at all.** The most recent statements are FY2025
   (2025-12-31), eight months stale, and describe a business the company says
   it is exiting. As a foreign private issuer BTCT reports semi-annually, so
   H1-2026 results are likely due around September–October 2026; no source I
   have carries a scheduled date. **Absence does not kill the thesis**, but
   it means conditions 1 and 3 are asserted on FY2025 evidence and the pivot
   is unmeasured.
5. **Management compensation and incentives.** Not readable without the 20-F.
   The revealed behaviour — five financings, a reverse split, three pivots,
   and a resale registration filed one month after the PIPE — is a substitute
   for the disclosure but is not the disclosure. **Absence does not kill the
   thesis.**
6. **The ETH treasury's current size and whether it still exists.** The July
   2025 announcements (convert all bitcoin reserves to ETH, buy $5M ETH,
   2,135 ETH cumulative) are more than a year old and the FY2025 balance
   sheet shows only $3.744M of cash and $15.228M→$1.243M of net cash
   destruction. It is not clear whether crypto holdings are inside those
   figures or were liquidated to fund the burn. **Absence does not kill the
   thesis** — at 2,135 ETH the position is small relative to the burn — but
   it is a genuine hole in the asset picture.

## 7. Sources

- **Primary:** none used. SEC EDGAR returned HTTP 403 on `browse-edgar`,
  `data.sec.gov/submissions/CIK0001796514.json`, and direct `Archives/`
  exhibit URLs; no primary filing was opened in this run. CIK 1796514 was
  confirmed from the stockanalysis payload and from SEC URLs surfaced in
  search results. This is a coverage failure, recorded in §3 and §6, not an
  editorial choice.
- **stockanalysis.com (vetted exception):** `/stocks/BTCT/statistics/`,
  `/stocks/BTCT/`, `/stocks/BTCT/financials/` (`__data.json`, fetched
  2026-08-21) — the full FY2021–FY2025 income statement, cash flow and
  balance sheet series; margins; Altman Z −1.66; Piotroski F-Score 1; beta
  5.48; short interest 2.21M shares / 18.70% of shares outstanding; company
  description; the news index used to date the 2025–2026 announcements. The
  underlying financial source is S&P Global (`source: 'spg'`,
  `lastUpdated: 2025-12-31`).
- **Broker/market microstructure:** Robinhood MCP `get_equity_quotes`,
  `get_equity_fundamentals`, `get_option_chains`, `get_earnings_results`
  (2026-08-21) — live last trade $1.15, prior close $1.47, bid $1.08 / ask
  $25.00, session OHLCV, float 8.62M, shares outstanding 9.52M, market cap
  $10.94M, price/book 0.376, 52-week range $0.4305–$3.12, and the empty
  option chain. Admissible under the data-source policy: this is real-time
  market and quote state — the intraday range, the float, the stub ask, and
  the existence of an options chain — which no already-integrated official
  source covers for this ticker. `get_financials` was not called (banned).
  The `get_earnings_results` payload was checked and discarded as unusable
  (§3, dead end iii). Robinhood's `financial_status_indicator` returned
  `CC0` with an empty description and is therefore not interpreted here.
- **Reference data:** Damodaran, `pages.stern.nyu.edu` home page — implied
  ERP 4.28% and US risk-free 4.74%, both as of **2026-08-01**; the ~29%
  above-cost-of-capital base rate (EVA dataset) and the ~7.8% median /
  5–10% 80% cost-of-capital band cited in §4 come from
  `references/damodaran-anchors.md`.
- **Point-in-time repo DBs:** none read. The scheduled slot's sandbox permits
  no `sqlite3`, so `sec_fundamentals.db`, `stocks.db`, `composite.db`,
  `short_interest.db` and `earnings.db` were all unavailable and the Phase 0
  cross-check of live figures against the point-in-time record did not run.
  `data/options.db` was not consulted because BTCT is outside the 24-symbol
  CBOE catalog and has no history there by construction.
- **Low-confidence:** web colour, labelled as such — Benzinga, Timothy
  Sykes, StocksToTrade, Quiver Quant and Kalkine for the 2026-08-20 session
  detail (+79.97% regular, +111.55% after-hours, 147.56M shares vs ~230,900
  average, ~$4.1M market cap going in); StockTitan and MarketScreener for the
  June 2026 PIPE terms (6,140,350 units at $1.14, two warrants per unit at
  $1.71, $7M upfront / up to $28M) and the 2026-07-29 F-1 resale breakdown
  (5,175,437 + 964,913 + 12,280,700 = 18,421,050); Simply Wall St and
  secondary summaries for the September 2022 Nasdaq deficiency letter, the
  May 2022 1-for-30 reverse split and the September 2023 compliance
  restoration. Every one of these would normally be verified against the
  filing itself; none could be. Treat the PIPE and F-1 share counts as
  well-corroborated across two independent secondary sources but not primary.

## Kill-thesis record

**Ledger:** `2026-08-21 BTCT UNPROVEN conditions=5 refuted=0 unknown=1
reopen=event:btct-signed-ai-compute-contract`

**Per-condition adjudication.**

1. *Cannot fund itself from operations* — **SURVIVED.** Attack: the June 2026
   PIPE plus $21M of warrant exercise could fund it to self-sufficiency. It
   fails on two counts — the warrants strike at $1.71 against a $1.15 spot,
   so the $21M is contingent on precisely the rally that dilutes holders 139%;
   and the $7M actually received is roughly six months at the FY2025 burn,
   two of which are already spent. Second attack: FY2023 had *positive*
   operating cash flow of $3.808M, so the company has funded itself before.
   True, and it is why the falsifier list keeps this as a Shift rather than
   treating it as permanent — but FY2023 free cash flow was $1.307M against
   an FY2025 figure of −$13.777M, and the capex line has gone from −$2.501M
   to −$8.519M as the AI pivot spends.
2. *Structural continuing dilution* — **SURVIVED.** Attack: the 419× figure
   is arithmetic I derived (net income ÷ diluted EPS), not a disclosed share
   count, and could be an artifact of stockanalysis's split-adjustment.
   Partially lands — the precise multiple is unreliable and is flagged as
   such in §2. The condition survives because it does not depend on it: the
   May 2022 1-for-30 reverse split is separately sourced, stockanalysis
   states shares rose 171.98% in one year, and the 2026-07-29 F-1 registers
   18,421,050 shares against ~9.5M outstanding. Three independent facts, same
   direction.
3. *Mining does not cover direct cost* — **SURVIVED as stated, forward
   version UNKNOWN.** This drew the closest attack (below). The FY2025 fact
   is not in dispute; the inference that it is permanent is.
4. *AI pivot cannot change (1)–(3) in the runway* — **UNKNOWN.** I attacked
   it by disconfirming search — looking specifically for a contract, a
   customer, or a revenue figure attached to the Georgia site, Fog Computing,
   or Aurora Energy — and found none in any secondary source. But the F-1 and
   the June 2026 6-K would be where such a disclosure lives, and SEC returned
   403 on every route. This is the run's one UNKNOWN and it is what routes
   the verdict to UNPROVEN. Note it is a *tooling* gap, not a disclosure gap:
   the evidence exists, I could not reach it.
5. *Price is a float squeeze* — **SURVIVED.** Attack: bitcoin was genuinely up
   ~9% through $71,000 on 2026-08-20, so this is a rational sector repricing,
   not positioning. It does not hold: a 9% move in bitcoin does not produce a
   +80% regular session, a +111% after-hours print, and 639× average volume
   in a name whose gross margin on mining is negative — and the −22.45%
   session the following day on no news is the tell.

**Standing checks.**

- *Base rate:* only ~29% of firms earn above their cost of capital (Damodaran
  EVA dataset), and there is no moat argument here to place BTCT in that
  minority. The more specific base rate — survival odds for a serially-
  pivoting nanocap funding itself through warrant-heavy PIPEs — I do not have
  a measured figure for and did not invent one; recorded as UNKNOWN rather
  than asserted as folklore.
- *The short case:* inverted, since this document argues the bear side. The
  strongest **long** case: a $10.9M market cap at 0.376× book and ~0.78× TTM
  sales, a completed and real 10MW Georgia site, a bitcoin tailwind, 18.70%
  short interest against an 8.62M float, and a sector where AI-datacenter
  re-ratings of former miners have produced multi-bagger moves. That case is
  coherent and it may well pay. It is a **trade** — it is about float,
  positioning and narrative, and it says nothing about owning the business.
  This skill answers the ownership question, and the two answers can differ
  without contradiction.
- *Management incentives:* not readable (20-F unavailable). Revealed
  behaviour substitutes: three business models, one 1-for-30 reverse split,
  a $6.0M registered direct in July 2025, a $7M PIPE in June 2026 with 2×
  warrant coverage, and a resale registration filed one month after that
  PIPE. Management is compensated by the capital markets, not by customers.
  The thesis does not assume they act against that incentive — it assumes
  they act with it, which is the pass.
- *Disconfirming search:* run deliberately toward the bull case (the August
  2026 surge, the AI pivot, the PIPE) and it returned real bullish material —
  bitcoin through $71,000, the completed 10MW site, 639× volume, sub-book
  valuation. All of it is in §3 and in the long case above. Nothing found
  disconfirmed conditions 1, 2 or 5.
- *Moat as mechanism, not checkbox:* asked and answered in §2. There is no
  mechanism. Hashrate is fungible, the block reward is protocol-set, and
  10MW is not a scale position in either mining or AI compute.

**Statistical checks:** largely N/A — this thesis rests on disclosed
financials, not on a backtest, screen or repo signal, so there is no null to
compare against, no window-overlap problem and no multiple-comparisons
correction owed. The one data-derived claim is the share-count trajectory in
§2, which is a *mechanism* claim (arithmetic on two disclosed lines) rather
than an inference claim, and its derivation and unreliability are flagged in
place.

**Options-market timing check: NOT APPLICABLE, and doubly so.** The thesis
makes no dated claim — the reopen trigger is deliberately `event:`, not a
date — and BTCT has no listed options chain at all (`get_option_chains`
returned `chains: []`). Either condition alone would skip the check. Recorded
explicitly so this document does not read as more thoroughly vetted than it
is: no options-market evidence bears on anything here.

**Closest attack:** the negative gross margin is a bitcoin-price artifact
rather than a permanent property of the business. FY2022 gross margin was
+14.94% and FY2024 was +0.99%; FY2025's −22.50% spans the post-halving
period, and bitcoin has since run above $71,000. On the FY2026 numbers,
condition 3 may simply be false. What blunts it: at the best margin in the
five-year file (+14.94% gross, FY2022) the operating margin was still only
+8.85% and free cash flow was −$39.9M, so even a full margin recovery does
not produce the $0.862M of durable free cash flow §4 shows the current price
requires. The attack damages condition 3 without reaching the ownership call.

**Flip evidence — toward SOUND:** reading the FY2025 20-F and the July 2026
F-1 directly and confirming that no contracted AI-compute revenue is
disclosed would close the single UNKNOWN and take this to SOUND without
changing a word of the analysis.

**Flip evidence — toward FLAWED:** a 6-K disclosing a signed AI-compute
customer with named contracted revenue at the Georgia site, or an H1-2026
interim showing positive operating cash flow on a positive gross margin,
would refute condition 4 (and, in the second case, condition 3) and make the
pass wrong — not merely unlucky.
