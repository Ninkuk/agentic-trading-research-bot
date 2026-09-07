# stockanalysis.com `__data.json` — Endpoint Catalog

Reverse-engineered reference for the unauthenticated, undocumented SvelteKit
data endpoint that backs every page on stockanalysis.com. This complements the
`stock_analysis_screener` module (which already consumes the screener slice).

> **Access note:** stockanalysis.com is an approved trusted source for this
> project. `robots.txt` disallows nothing for generic user agents. No auth, API
> key, or token is required. Be a polite client (sane rate, real User-Agent).

Probe any route yourself with the bundled decoder:

```bash
uv run python -m sources.screeners.stock_analysis_screener.probe /stocks/AAPL/statistics/
uv run python -m sources.screeners.stock_analysis_screener.probe --keys /markets/gainers/ /ipos/2024/
```

## 1. The technique

stockanalysis.com is a **SvelteKit** app. For every route `/{path}/` there is a
sibling `/{path}/__data.json` returning the exact server `load()` output — the
same data the page hydrates from.

- **URL rule:** append `__data.json` to the route (before any query string).
  `/stocks/AAPL/statistics/` → `/stocks/AAPL/statistics/__data.json`.
  Query params carry through: `/stocks/AAPL/financials/__data.json?p=quarterly`.
- **Canonical case:** page routes 301 to lowercase (`/stocks/AAPL/` →
  `/stocks/aapl/`). `urllib` follows it, so uppercase tickers are fine.
- **Limit:** a few interactive routes stream their content client-side, so
  their `__data.json` is a stub: `/stocks/compare/` and `/etf/compare/` carry
  `{streamed, tickers}`, `/chart/{T}/` `{info, noindex}`,
  `/tools/etf-reverse-lookup/` `{symbol, widthMode}`. `/markets/` itself is the
  404 error node below.

### Don't guess routes — read the app's own route table

The client bundle ships the complete SvelteKit route dictionary — the
authoritative list. `financials/` is a catch-all
(`…/financials/[...routes]`), so its statement slugs (`income-statement`, …)
resolve server-side and never appear in this table. Enumerate from it:

```bash
ENTRY=$(curl -sL --compressed https://stockanalysis.com/stocks/aapl/ \
        | grep -oE '_app/immutable/entry/app\.[A-Za-z0-9_-]+\.js' | head -1)
curl -sL --compressed "https://stockanalysis.com/$ENTRY" \
  | grep -oE '"/[^"]*":\[' | tr -d '":[' | sort
```

The same crawl over `_app/immutable/**` chunks finds the `_api` surface (§4) —
grep for `/_api/`. An entry in the table is not proof the route still serves
data: `/stocks/[symbol]/filings/[[id]]` is still listed but only as a redirect
shim to the top-level `/filings/[symbol]/[[id]]` — check for the redirect
envelope below.

**Three payload signatures mean "nothing here":**

- **JSON redirect envelope** — `{"type":"redirect","location":"/filings/AAPL/"}`,
  HTTP 200, no `nodes`. SvelteKit answers with it for lowercase→canonical
  (`/filings/cvna/` → `/filings/CVNA/`), **ticker changes** (`/stocks/CSU/` →
  `/stocks/snda/` — CSU is Sonida now, so a redirect can land on a different
  company than the one you asked for), and **moved routes** (`/stocks/{T}/filings/`
  → `/filings/{T}/`). urllib never sees a 3xx; a raw fetch decodes to zero nodes
  and `page_data` returns `None`. `probe.fetch_data_json` follows up to three
  hops and `resolve_data_json` returns the final path beside the payload.
- **Layout node only** (keys `ab`, `cookies`, `session`, `theme`, `user`, …) —
  the route has no server `load()`. E.g. `/tools/` and `/changelog/`.
- **Page node is `{"type":"error","status":404,"error":{"message":"not found"}}`**
  inside an HTTP 200. Pro-gated pages (`financials/segments/`,
  `financials/full/`), bogus slugs (`/stocks/AAPL/metrics/not-a-metric/`,
  `/markets/gainers/1w/`, `/list/nasdaq/`), `/quote/{T}/` *without* an exchange
  segment, hub pages (`/markets/`, `/blog/`) and **tickers the route has no data
  for** (`/stocks/CVNA/metrics/`) all return this identical node. `decode_nodes` drops it, so `page_data` hands back the
  node before it — the per-ticker layout `{info: …}` under `/stocks/{T}/…`,
  the bare root layout under a top-level route such as `/filings/…`. `{info}`
  alone therefore means "the page node errored", never "gated" specifically;
  `probe.page_error(raw)` reads the node, and the CLI prints it as `page_error`.
  Gated and absent carry the same 404 status on the wire — the catalog's own
  route notes are the only way to tell them apart.

**Do not exist** (HTTP 404 — don't re-probe):
`/stocks/{T}/` + `short-interest`, `institutional`, `insider-trading`,
`ownership`, `holders`, `peers`, `earnings`, `options`, `profile`,
`sec-filings`, `valuation`, `chart`, `holdings`. Short interest lives in the
screener data-points (`shortFloat`, `shortShares`, `shortRatio`, §6); ownership
in `sharesInsiders`/`sharesInstitutions`.

> ⚠️ **A 404 on one slug says nothing about the sibling.** `sec-filings` 404s but
> `/filings/{T}/` is real and carries direct PDF links (below); `chart` 404s
> under a ticker but exists at `/chart/{T}/`; `holdings` 404s under `/stocks/` but
> exists under `/quote/`.

## 2. Decoding the payload (`devalue`)

The body is **not** plain JSON. It is `devalue`-serialized:

```json
{"type":"data","nodes":[ {"type":"data","data":[ POOL ]}, ... ]}
```

Each node's `data` is a flat **pool** where `POOL[0]` is the root and every
integer is a back-reference into the pool (so repeated objects are stored once).
Negative integers are sentinels (`-1` undefined, `-2` hole, `-3` NaN, `-4/-5`
±Inf, `-6` -0). Arrays whose first element is a *string* are type-tagged
specials (`Date`, `Set`, `Map`, …); plain arrays contain only integer indices.

Nodes are the layout→page chain; the **last non-null node is the page data**.
Use `stock_analysis_screener.probe.page_data(path)` to get it decoded.

## 3. Route family reference

`{T}` = a ticker (e.g. `AAPL`). US equities live under `/stocks/{T}/…`;
non-US listings mirror the identical schema under `/quote/{exchange}/{T}/…`
(e.g. `/quote/tsx/CSU/`). ETFs under `/etf/{T}/…`.

The `exchange` segment is optional in the route (`/quote/[[exchange]]/[symbol]`)
but **omitting it yields the 404 error node** — always pass it. A US ticker
under `/quote/{exchange}/` JSON-redirects to `/symbol-lookup/?q=…`, never to
`/stocks/{T}/`. The `/quote/` overview carries ETF-shaped keys beside the
stock ones (`aum`, `holdings`, `holdingsTable`, `inception` — null for an
equity). The two families are not identical: `/stocks/` has `metrics/` and `/quote/` does not;
`/quote/` has `holdings/` and `/stocks/` does not (both 404 the other way). On
non-US equities `holdings/` returns the error node (`{info}`). Filings left
both families for the top-level `/filings/{SYMBOL}/` route (table below), where
non-US names **are** fed.

### Per-ticker (stocks & international quotes)

| Route (+ `/__data.json`) | Key payload |
|---|---|
| `/stocks/{T}/` | Overview: revenue, netIncome, eps(+growth), peRatio/forwardPE, marketCap, beta, sharesOut, dividend, earningsDate, analyst target, infoTable, news. Every numeric field here is a **suffixed string** (`marketCap` → `"4.64T"`); no full-precision variant on this route |
| `/stocks/{T}/financials/` | **Overview** (`financialData` is `null` here): data lives in `sections[]` — 7 themed sections (`revenue-income`, `revenue-segments`, `cash-debt`, `cash-flow-capex`, `margins`, `dividends`, `valuation`), each `{id, title, data, ttm, rows, prior, ttmPrior, …}`. `data` is column arrays (raw numbers), **fiscal years only: `datekey[0]` is the latest FY, no TTM row** — TTM sits in the section's `ttm` dict. `?p=quarterly` for quarterly |
| `…/financials/income-statement/` | Income statement (`financialData`, `map`, `period`, `availableSources`). `?p=quarterly` for quarterly. `financialData` arrays are **raw integers**, but **index 0 is `"TTM"`, not a fiscal year** — check `datekey` before indexing (AAPL `fcf[0]`=129.17B TTM vs `fcf[1]`=98.77B FY2025) |
| `…/financials/balance-sheet/` | Balance sheet (same shape as `income-statement/`). `debt` is gross; `netcash` (lowercase here, unlike the screener's `netCash`) is net **cash** (AAPL +62.17B), so a net-*debt* input takes its negative |
| `…/financials/cash-flow-statement/` | Cash-flow statement. Also `leveredFCF` (equity, post-interest) and `unleveredFCF` (firm) beside plain `fcf`. **`capex` is stored negative**, so `fcf` = `ncfo` **+** `capex` (AAPL TTM: 146.724B + −10.041B = 136.683B). All three differ — VZ TTM `fcf` 21.53B, `leveredFCF` 17.47B, `unleveredFCF` 22.06B — so **`fcf != leveredFCF`** (on AAPL `leveredFCF` and `unleveredFCF` coincide at 107.72B; VZ or CVNA shows the three apart). Plain `fcf` is post-interest, i.e. levered: pair it with **market cap**. Pair `unleveredFCF` with enterprise value |
| `…/financials/ratios/` | Ratios |
| `…/financials/segments/` | **Pro-gated** — `info` placeholder only |
| `…/financials/full/` | **Pro-gated** — `info` placeholder only |
| `/stocks/{T}/metrics/` | **Operating metrics & breakdowns**, all under one `data` key: `data.annualMetrics`/`quarterlyMetrics`/`trailingMetrics`, each `{name, category, type, valueType, count, values:[{x: date, y: number}]}` — **raw numbers** — with the matching `annualDates`/`quarterlyDates`/`trailingDates` axes. `category` ∈ Revenue by Segment, Revenue by Geography, Gross Profit/Margin by Type, Operating Expense Breakdown, plus company-specific Operating Metrics (AAPL: Global Active Devices). **Not** Pro-gated, unlike `financials/segments/` — this is the free path to segment and geography splits. Also `data.groups` (`{title, rows, annual}`), `navigationItems`, `sourceLastUpdated`. ⚠️ **Per-ticker coverage, not a gate:** a ticker with no breakdowns returns the 404 error node (§1) and `page_data` shows the layout `{info}`, identical to Pro-gating. 2026-09-06: AAPL, MSFT, VZ, IBM, TGT, LULU fed; CVNA, BBAI, GIII, FRNM, TJGC not. Absence says nothing about the 10-K's segment note (GIII reports segments and still errors) |
| `/stocks/{T}/metrics/{metric}/` | One breakdown in isolation: `{metric, data: {pageType, title, type, valueType, data: {quarterly, trailing}, navigationItems}}` — no annual series here. Slug = the `navigationItems` title kebab-cased: `revenue-by-segment`, `revenue-by-geography`, `gross-profit-by-type`, `gross-margin-by-type`, `operating-expense-breakdown`. An unknown slug returns **200 with the error node** (`page_data` shows `{info}`), not 404. Stocks only — `/quote/…/metrics/` 404s (HTML) |
| `/filings/{SYMBOL}/` | **IR document index with direct PDF URLs** — the only filings route; `/stocks/{T}/filings/` and `/quote/…/filings/` JSON-redirect here (§1). Keys `events`, `filingsSymbol`, `filingsMeta`, `metaInputs`, `info`, `selectedId`. `events` = fiscal events `{eventId, title, eventDate, fiscalYear, fiscalPeriod, filings:[{id, type, title, fileUrl}]}`; filing-level `title` is **null** — the event `title` ("Q3 2026", "J.P. Morgan Automotive Conference") names it. AAPL 88 events 2011→2026; CVNA 86, 2017→2026. `type` ∈ `earnings_release`, `quarterly_report`, `annual_report`, `proxy`, `slides`, `press_release`, `registration`, `shareholder_letter`. `fileUrl` is a **Quartr**-hosted PDF, *not* SEC EDGAR — for EDGAR use this repo's `edgar` screener. **The symbol form is the whole trick:** US names take the bare ticker (`/filings/AAPL/`); non-US names take `EXCHANGE:TICKER` (`/filings/TSX:CSU/` — 83 events back to 2007, so non-US filings *are* fed here). The wrong form (`/filings/NASDAQ:AAPL/`) returns the 404 error node, and because this is a top-level route the fallback node is the bare root layout, which reads like "no server `load()`" |
| `/filings/{SYMBOL}/{id}/` | **Same payload**, only `selectedId` differs — the id selects a PDF client-side. Don't fetch per-id; the index already has every `fileUrl`. An unknown id returns the error node |
| `/stocks/{T}/revenue/` | `stats` (revenue, revenue_growth, market_cap, employees, ps_ratio, revenue_per_employee, last_reported) + `data.annual`/`.quarterly`/`.trailing` series — **raw integers**, no suffix strings. Also `peers`, `news` |
| `/stocks/{T}/transcripts/` | Index under key `transcripts` (AAPL ~74 back to 2011; VZ ~77 only back to 2019 — depth varies sharply by ticker). Each `{id, quartrEventId, fiscalYear, quarterLabel, detailSlug, eventDate, eventTitle, audioUrl, summaryShort, files}`. ⚠️ **Not only earnings calls** — conference presentations and events are interleaved (VZ `eventTitle` "J.P. Morgan 54th Annual…", AAPL "Product Launch", `quarterLabel` "FY 2026"). Filter on `eventTitle`/`quarterLabel` if you want the quarterly calls alone |
| `/stocks/{T}/transcripts/{detailSlug}/` | **Full transcript** (35–50k chars ≈ 9–12k tokens each; a 76-call corpus is ~3M chars ≈ 750k tokens, but fetches in ~25s at 0.33s/call). `transcriptQuarter.transcriptTurns` = list of `{speakerName, role, company, paragraphs}`. ⚠️ **`paragraphs` is `list[list[dict]]`** — a list of paragraphs, each a list of *sentences* `{text, startSec, endSec}` (audio-aligned). Two levels, not one: `[s['text'] for p in turn['paragraphs'] for s in p]`. Plus `summaryShort`, `summaryLongHtml` (AI-generated — tier low-confidence), `audioUrl`, `files`. Source: Quartr |
| `/stocks/{T}/ratings/` | Per-analyst rating actions under `ratings`: `{action_rt, firm, analyst, slug, rating_new, rating_old, pt_now, pt_old, curr, date, time, scores}` |
| `/stocks/{T}/statistics/` | 19 grouped blocks (`valuation`, `evRatios`, `stockPrice`, `dates`, `shares`, `shortSelling`, `incomeStatement`, `balanceSheet`, `cashFlow`, `margins`, `ratios`, `financialPosition`, `financialEfficiency`, `taxes`, `dividends`, `stockSplits`, `scores` (Altman Z, Piotroski F), `fairValue`, `analystForecasts`), each `{data, text}`. `fairValue` rows carry `proOnly: true` but their values are populated. `data` rows are `{id, title, value, hover, url}` — **`hover` is the exact figure** (`'4,669,699,774,600'`), `value` the rounded display string. Cheapest exact source of market cap, `enterpriseValue`, `fcf`, `capex`, `debt` in one request. ⚠️ The market-cap row's id is **`marketcap`**, lowercased — everywhere else in this catalog it is `marketCap`. Keying on `marketCap` here silently finds nothing. ⚠️ **The `incomeStatement` block's TTM flow rows can disagree with `/financials/income-statement/`** — which route wins depends on the field; see the notes below the table |
| `/stocks/{T}/dividend/` | Full dividend history, yield, payout, chart |
| `/stocks/{T}/company/` | Profile: description, executives, contact, filings, logoURL |
| `/stocks/{T}/forecast/` | priceTargets (avg/median/low/high/count), per-analyst `ratings` (firm/analyst/PT/rating + track record), monthly consensus `recommendations`, EPS/revenue `estimates` |
| `/stocks/{T}/history/` | OHLCV bars `{o,h,l,c,a,v,t,ch}` under `data.data`, newest first, **fixed ~6-month window (129 bars)** — no query param widens it. Longer ranges come from the `/api/symbol/…/history` endpoint (§4), which the page's range menu calls. `other.firstYear` (AAPL 1982) only states availability. Header carries `source` (`spg`) + `updated` |
| `/stocks/{T}/employees/` | Headcount history (annual/quarterly) + peers |
| `/stocks/{T}/market-cap/` | Market-cap history, performance, peers |

> ⚠️ **Take `operatingIncome`, `ebitda` and their margins from
> `/financials/income-statement/`, not `/statistics/`.** The statement route's
> TTM is the sum of `?p=quarterly`'s four columns; `/statistics/`'s
> `incomeStatement` block is not guaranteed to be — it can exclude impairment-
> and restructuring-type charges (INTC TTM `opinc`, 2026-07-21: `/statistics/`
> +2,006.0M vs statement −2,214.0M). Both are labelled TTM and nothing marks the
> difference; `revenue`, `fcf`, `capex` and `ncfo` agree on both routes. Not the
> `[0]` TTM-vs-fiscal-year trap above — both figures are genuinely TTM.
>
> ⚠️ **Two "net income" lines.** `/statistics/` `netinc` is net income to
> **common** — the statement route's `netinccmn`, after preferred and deemed
> dividends (`preferredDividendsOther`); the statement route's `netinc` is
> before them. EOSE TTM: `netinc` −528.7M (= `pretax` −528.6M − tax; = the four
> quarterly columns), `netinccmn` −1,025.0M, `preferredDividendsOther` 496.3M.
> Pick the line deliberately, and reconcile `[0]` against `?p=quarterly`'s four
> columns — worst on names with large derivative marks.
>
> ⚠️ **`debt` is carrying value, not principal.** EOSE 2026-03-31: `debt` 642.9M vs
> 10-Q principal 943.6M — converts carried net of a bifurcated derivative.
> `debtEquity`, `netDebtEbitda` and `netCash` all inherit it. Confirm against the
> filing's debt note.

### Per-ETF

| Route | Key payload |
|---|---|
| `/etf/{T}/` | aum, nav, expenseRatio, dividendYield, payout*, holdings, performance, provider |
| `/etf/{T}/holdings/` | Holdings + sector/country/asset allocation |
| `/etf/{T}/dividend/` | Dividend history + chart |
| `/etf/{T}/history/` | OHLCV bars, same `{o,h,l,c,a,v,t,ch}` shape and 129-bar window as `/stocks/{T}/history/`; header carries `source` (`tiingo`) + `updated`. Same `/api/symbol/…/history` route (§4) for longer ranges |
| `/etf/provider/` | Provider directory (`etfs`, `default_columns`) |
| `/etf/provider/{slug}/` | All provider ETFs as a screener grid (e.g. `vanguard`) |
| `/etf/list/new/` | Newly listed ETFs as a screener grid |

The per-ticker ETF routes are only these four (`/`, `holdings/`, `dividend/`,
`history/`) — `/etf/{T}/metrics/` and the other stock tabs 404.

### Bulk universe dumps (see §4)

| Route | Rows | Selectable metrics |
|---|---|---|
| `/stocks/screener/` | **5,599 stocks** | **323** |
| `/etf/screener/` | **5,618 ETFs** | **114** |
| `/tools/mutf-screener/` | **23,927 funds** | **87** |
| `/ipos/screener/` | **459 IPOs** | 41, own catalog |

Row counts drift daily (the stock universe hovers around 5,600) — read them off
the page's `count` rather than hard-coding. The screener `__data.json` itself
carries only the first `perPage` (20) rows (`dataIsPartial: true`) beside
`count` and the `dataPoints` catalog; the universe comes from §4's `table`
endpoint, minding its `resultsCount` caveat.

### Market movers & discovery (see §5 for the query DSL)

| Route | Contents |
|---|---|
| `/markets/gainers/` · `/losers/` · `/active/` | Ranked movers + full `query` filter object |
| `/markets/premarket/` · `/premarket/gainers/` · `/premarket/losers/` | Pre-market movers (`premarketChangePercent`) |
| `/markets/afterhours/` · `/afterhours/gainers/` · `/afterhours/losers/` | After-hours movers (`postmarketChangePercent`). The bare `/premarket/` and `/afterhours/` each carry **both** `gainers` and `losers` plus `chartData` in one payload, and no `query` |
| `/markets/heatmap/` · `/markets/heatmap/nasdaq-100/` | Treemap (S&P 500; Nasdaq-100 under the only index slug that serves data — `sp500`, `dow-jones`, `nasdaq` return the error node): `heatmap.{labels, parents, values, text, urls, customdata, scale, indexSector, indexIndustries}` (index → sector → constituent), `indexQuotes`, `time` (`1D`), `title`, `expanded` |
| `/markets/gainers/{range}/` · `/losers/{range}/` | `range` ∈ `week`, `month`, `ytd`, `year` — sorted on `ch1w`/`ch1m`/`chYTD`/`ch1y` with the `priceDate-isRecent` filter, plus `range` and `config`. Any other slug (`1w`, `3m`) returns the error node (`{widthMode}`) |
| `/trending/` · `/trending/most-alerted/` | Most-viewed stocks (`views`) · most-alerted (`alertCount`) |
| `/analysts/top-stocks/` | Top analyst-rated stocks (screener grid) |

The mover pages carry `tradingTimestamps` alongside `query` — use it rather than
inferring the session from a `priceDate`.

### Corporate actions — all `{action, data, fullCount, props, type}`

`/actions/acquisitions/` · `/bankruptcies/` · `/changes/` (ticker changes) ·
`/delisted/` · `/listed/` (new listings) · `/spinoffs/` · `/splits/`

### IPOs

`/ipos/` (recent + upcoming) · `/ipos/calendar/` (this/next-week/later) ·
`/ipos/statistics/` · `/ipos/withdrawn/` · `/ipos/{year}/` (e.g. `/ipos/2024/`) ·
`/ipos/filings/` (S-1s in registration) · `/ipos/lockups/` (this/next-week/later
+ `expiredData`, `conditionalData`) · `/ipos/news/` · `/ipos/screener/` (459 rows,
own 41-point `dataPoints` catalog)

### Analysts

`/analysts/` (directory, `total` ~4,700) · `/analysts/{slug}/` (rank, scores,
covered sectors/industries/countries, full ratings history) ·
`/analysts/top-stocks/` · `/analysts/most-followed/` (`{analysts, isPro}`).
`/analysts/ratings/` is a logged-in feed (`{canUse, isLoggedIn, …}`) — nothing
unauthenticated.

### Other data-bearing routes

| Route | Contents |
|---|---|
| `/stocks/earnings-calendar/` | 75 days w/ before-open/after-close counts + 15 grouped weeks (~620 KB) |
| `/news/` · `/news/all-stocks/` · `/news/press-releases/` | News feeds |
| `/stocks/industry/` · `/stocks/industry/sectors/` · `/stocks/industry/all/` | Sector/industry directories (`industries`/`sectors` + `default_columns`). The bare `/industry/…` forms are HTTP 404 |
| `/stocks/industry/{name}/` | Industry constituents + stats (e.g. `semiconductors`) |
| `/stocks/sector/{sector}/` | Sector constituents (500-row page, `isPaginated`) + aggregate `stats`: `stocks`, `marketCap`, `revenue`, `grossProfit`, `operatingIncome`, `netIncome`, `fcf` |
| `/list/` · `/list/exchanges/` · `/list/{slug}/` | Curated & per-exchange lists (stock + ETF grids). The segment is a **slug**, not an exchange code — `/list/nasdaq-stocks/`, not `/list/nasdaq/` |
| `/private/{slug}/` · `/private/{slug}/valuation/` | Private-company profiles (valuation, funding, Forge/Hiive links) · funding rounds, `valuationHistory`, `pricePoints` |
| `/symbol-lookup/?q=…` | Autocomplete search (`{count, query, results}`; `/lookup/` JSON-redirects here) |
| `/market-bullets/` · `/market-bullets/{permalink}/` | Market-commentary newsletters |
| `/help/` · `/help/{category}/{slug}/` | Help-centre index (`articles`: slug, title, category, updated) · one article (`article` + `articles`) — the only editorial content with page data; `/term/`, `/blog/`, `/article/` do not exist |
| `/chart/{T}/` | `{info, noindex}` — series load client-side; use `/stocks/{T}/history/` |
| `/tools/etf-reverse-lookup/` | `{symbol, widthMode}` — client-side; no ETF-holder data server-side |

## 4. The `_api/endpoints` surface

Behind the pages sits a plain-JSON API (no `devalue`, no auth, no key). All
endpoints answer `{"status": 200, "data": …}`. Found by grepping the
`_app/immutable/**` chunks for `/_api/`.

`/stocks/screener/__data.json` carries the `dataPoints` catalog,
`dataPointCategories` and the universe `count`, but only the first 20 rows
(`perPage`, `dataIsPartial: true`) in the default column set
(`s, n, marketCap, price, change, industry, volume, peRatio`).
`catalog.fetch_catalog()` decodes that catalog + count (`type_` `s` or `e`
only; funds are `/tools/mutf-screener/`). For rows — any rows — use the API
below.

### `screener/table` — the general query endpoint

```
GET /_api/endpoints/screener/table?type=s&i=stocks&m=marketCap&s=desc&c=s,n,marketCap,fcf
```

| Param | Meaning |
|---|---|
| `type` | `s` stocks · `e` ETFs · `f` mutual funds |
| `i` | index: `stocks` · `etf` · `funds` · `stock-movers` |
| `m` | main / sort field (any §6 id); appended to `c` if absent |
| `s` | sort direction, `asc` \| `desc` |
| `c` | columns, comma-separated §6 ids |
| `sc` | secondary sort column |
| `cn` | row cap (page size). **Omit to get the whole universe** |
| `f` | filters, comma-separated §5 terms (each URL-encoded; a literal `%` is sent as a space) |
| `se` | free-text search over ticker **and** name |
| `p` | page number — ignored when `se` is present |
| `dd` | `true` to dedupe |
| `bypassCache` | `true` to skip the edge cache |

This strictly dominates `data-points`: arbitrary columns, plus filtering,
sorting, and search. With no `cn` it returns the whole universe (5,599 stock
rows, ~850 KB with the default columns) in one response.

> ⚠️ **`i` is not optional in practice.** Without it the query spans every
> listing worldwide and reports market cap **in the listing currency**. Sorting
> by `marketCap` desc then returns `BVC-NVDACO` at `1.7e16` (Colombian pesos)
> before any US row. With `i=stocks` you get `NVDA` at `5.6e12` USD. The same
> holds for `type=f` without `i=funds` (`TYO-1557` at `1.3e14` yen). A harvest
> that omits `i` is silently denominated in a mix of currencies.

> ⚠️ **`resultsCount` is the number of rows in *this* response**, always equal to
> `len(data)`. It is not the total number of matches, so you cannot use it to
> size a pagination loop.

**Single-name lookup:** `se` is a substring search, so
`?se=AAPL&c=<any columns>` returns exactly one row with full-precision values —
the arbitrary-column, single-ticker query. Match on ticker is not guaranteed
unique (`se=apple` also matches *Maui Land & Pineapple*), so verify the returned
`s` field. `se` takes one term; it is not a comma-separated symbol list.

Values are full-precision and cross-check against the other routes: `se=AAPL`
with `c=s,n,marketCap,fcf` yields `marketCap=4669699774600` (= the `hover` on
`/statistics/`) and `fcf=136683000000` (= `financialData.fcf[0]`, the **TTM**
figure, not FY2025's 98.77B). Flow metrics on this endpoint are trailing-twelve,
so don't mix them with a fiscal-year row pulled from a `/financials/` statement
sub-route (or from the overview's `sections[].data`, which is fiscal-years-only).

### The rest

| Endpoint | Returns |
|---|---|
| `screener/data-points?type=s&ids=marketCap+fcf` | `{data:{data:{TICKER:{id:value}}}}` — whole universe (5,599 rows), **no ticker filter**. `ids` are `+`-joined (a URL-encoded space). Wired as `fetch.fetch_data_points(ids, type_)` |
| `screener/data-point?type=s&id=peRatio` | Singular. `{data:{data:[[TICKER, value], …]}}` — **sparse**: rows with no value are dropped (2,985 of 5,599 for `peRatio`). Optional `&c={country}`, `&mod=variable` |
| `market-cap/chart?symbol=AAPL` | `[[epoch_ms, marketCap], …]` back to 1998 |
| `custom/financialsWidget?symbol=AAPL&period=quarterly` | `[{period, revenue, earnings, revenueGrowth, earningsGrowth}]` — raw integers |
| `watchlist?symbols=A,B&columns=…` | ⚠️ **Trap.** Reads like the ideal ticker×column endpoint, but unauthenticated it returns `{s, n:""}` stubs and **silently ignores `columns`** — HTTP 200, no error. Use `screener/table` with `se`. |

### `/api/symbol/{s|e}/{T}/history` — price history beyond the 129-bar page

A separate plain-JSON route (under `/api/`, not `/_api/endpoints/`; same
`{"status": 200, "data": …}` envelope; no auth). `s` and `e` both accept a
US stock or ETF symbol; no symbol form for a non-US listing works here
(`TSX:CSU`, `tsx/CSU`, `CSU.TO` all 404/400).

| Query | Returns |
|---|---|
| `?range={3M\|6M\|YTD\|1Y\|5Y\|10Y}&period={Daily\|Weekly\|Monthly\|Quarterly}` | `data` = bare list of `{t,o,h,l,c,a,v,ch}` bars, newest first (AAPL Daily: 3M 65 · 6M 129 · YTD 170 · 1Y 253 · 5Y 1,255 · 10Y 2,513). Weekly/Monthly/Quarterly bars are stamped on the period's first day. **Any other `range` — `MAX`, `ALL`, `20Y`, a typo — silently returns the 1Y window**: the page's "Full History" menu item is Pro-gated, and the API enforces it by falling back, not by erroring. 10Y is the OHLCV ceiling |
| `?type=chart` | `[[epoch_ms, adjusted_close], …]`, oldest first, **the whole listing history, ungated** — AAPL 11,070 points from 1982-10-04, SPY 8,458 from 1993. Split-adjusted (AAPL 1982 = 0.0837). Closes only: this is the free path to full-history prices when OHLCV beyond 10Y is not needed. `range` is ignored here |
| no params | The page payload: `{data: [129 bars], news, other: {firstChartDate}}` |

The remaining `_api` families (`admin/*`, `alerts/*`, `brokerage/*`,
`notifications/*`) are authenticated account surfaces — out of scope.

## 5. Screener / movers query DSL

The movers and trending pages expose the server-side query object under `query`
in their `__data.json`. It is the same filter grammar the screener uses — and the
same object §4's `table` endpoint takes apart into query params (`index`→`i`,
`main`→`m`, `sortDirection`→`s`, `columns`→`c`, `count`→`cn`, `filters`→`f`). So
a `query` lifted from any mover page can be replayed against `table` verbatim.

```jsonc
{
  "type": "s",                    // s=stocks, e=ETFs, f=funds
  "index": "stock-movers",        // "stock-movers" | "stocks" (full universe)
  "main": "change",               // sort field = any data-point id from §6
  "sortDirection": "desc",        // "asc" | "desc"
  "count": 20,                    // page size
  "page": 1,
  "columns": ["no","s","n","change","price","volume","marketCap"],
  "filters": ["change-over-0", "priceDate-isLastTradingDay"]
}
```

**Filter grammar:** `"{dataPointId}-{operator}-{value}"`. Observed operators:

| Operator | Meaning | Example |
|---|---|---|
| `over` | `field > value` | `change-over-0`, `views-over-1` |
| `under` | `field < value` | `change-under-0` |
| `isLastTradingDay` | field's date == last trading day (no value) | `priceDate-isLastTradingDay` |
| `isRecent` | field's date is recent (no value) — the ranged mover pages | `priceDate-isRecent` |
| `is` / `isnot` | categorical equality; a `%` in the value stands for a space | `analystRatingsTop-is-Strong%Buy`, `industry-isnot-Biotechnology` |

`columns`, `main`, and `filters` all reference the §6 data-point ids, so any of
the 323 stock metrics is sortable/filterable. Observed presets:

| Page | `main` | `filters` |
|---|---|---|
| `/markets/gainers/` | `change` desc | `change-over-0`, `priceDate-isLastTradingDay` |
| `/markets/losers/` | `change` asc | `change-under-0`, `priceDate-isLastTradingDay` |
| `/markets/active/` | `volume` desc | `volume-over-0`, `priceDate-isLastTradingDay` |
| `/markets/premarket/gainers/` | `premarketChangePercent` desc | `premarketChangePercent-over-0`, `premarketDate-isLastTradingDay` |
| `/markets/gainers/week/` | `ch1w` desc | `ch1w-over-0`, `priceDate-isRecent` |
| `/trending/` | `views` desc | `views-over-1` |
| `/trending/most-alerted/` | `alertCount` desc | `alertCount-over-0` |
| `/analysts/top-stocks/` | `priceTargetChangeTop` desc, 50 rows | `priceTargetChangeTop-over-0`, `analystRatingsTop-is-Strong%Buy`, `analystCountTop-over-9`, `industry-isnot-Biotechnology`, `marketCap-over-1000000000` |

## 6. Stock screener data-points (323)

The full selectable metric catalog for `type=s`, grouped by category (the same
`id`s used as screener columns and as filter/sort keys in §5). The ETF catalog
(`type=e`, 114 metrics) is a variant — fetch it live with
`catalog.fetch_catalog("e")`; the fund catalog (87 metrics) is only on
`/tools/mutf-screener/`'s `dataPoints`.

### Price & Volume (26)

> ⚠️ **`close` is NOT the close for `priceDate`.** These fields are named from a
> live-quote perspective: **`price` is the last close for `priceDate`**, while
> **`close` is the PREVIOUS session's close**. Verified against CBOE and the
> `/history/` endpoint (SPY `priceDate=2026-07-07`: `price=747.71` = that day's
> close, `close=751.28` = 07-06's close). Harvesting `close` as the close for
> `priceDate` shifts every row forward one trading day. Use `price`.

| id | name |
|---|---|
| `price` | Stock Price — **the close for `priceDate`** |
| `change` | Price Change 1D |
| `volume` | Volume |
| `dollarVolume` | Dollar Volume |
| `open` | Open Price |
| `low` | Low Price |
| `high` | High Price |
| `close` | **Previous Close** — the session *before* `priceDate`. Not what you want. |
| `priceDate` | Stock Price Date — the session `price` closed on |
| `premarketPrice` | Premarket Price |
| `premarketChangePercent` | Premarket % Change |
| `premarketVolume` | Premarket Volume |
| `preClose` | Premarket Close |
| `postmarketPrice` | After-Hours Price |
| `postmarketChangePercent` | After-Hours % Change |
| `postClose` | After-Hours Close |
| `low52` | 52-Week Low Price |
| `high52` | 52-Week High Price |
| `averageVolume` | Average Volume |
| `relativeVolume` | Relative Volume |
| `daysGap` | Day's Gap (%) |
| `changeFromOpen` | Change From Open (%) |
| `positionInRange` | Position in Range (%) |
| `beta` | Beta (5Y) |
| `beta1y` | Beta (1Y) |
| `beta2y` | Beta (2Y) |

### Valuation & Ratios (31)

| id | name |
|---|---|
| `marketCap` | Market Cap |
| `enterpriseValue` | Enterprise Value |
| `marketCapCategory` | Market Cap Group |
| `peForward` | Forward PE |
| `sectorPe` | Sector PE |
| `sectorPeFwd` | Sector Forward PE |
| `industryPe` | Industry PE |
| `industryPeFwd` | Industry Forward PE |
| `peRatio` | PE Ratio |
| `psRatio` | PS Ratio |
| `psForward` | Forward PS |
| `pbRatio` | PB Ratio |
| `pFcfRatio` | P/FCF Ratio |
| `pFcfRatioSbc` | P/FCF-SBC Ratio |
| `pOcfRatio` | P/OCF Ratio |
| `pOcfRatioSbc` | P/OCF-SBC Ratio |
| `pegRatio` | PEG Ratio |
| `evSales` | EV/Sales |
| `evSalesForward` | Forward EV/Sales |
| `evEarnings` | EV/Earnings |
| `evEbitda` | EV/EBITDA |
| `evEbit` | EV/EBIT |
| `evFcf` | EV/FCF |
| `priceEbitda` | Price/EBITDA Ratio |
| `earningsYield` | Earnings Yield |
| `fcfYield` | FCF Yield |
| `fcfEvYield` | FCF / EV Yield |
| `ptbvRatio` | Price / Tangible Book Value |
| `peRatio3Y` | Average PE Ratio (3Y) |
| `peRatio5Y` | Average PE Ratio (5Y) |
| `peRatio10Y` | Average PE Ratio (10Y) |

### Technical Analysis (19)

| id | name |
|---|---|
| `rsi` | Relative Strength Index (RSI) |
| `rsiWeekly` | Weekly RSI |
| `rsiMonthly` | Monthly RSI |
| `atr` | Average True Range (ATR) |
| `sharpeRatio` | Sharpe Ratio |
| `sharpeRatio3y` | Sharpe Ratio (3Y) |
| `sharpeRatio5y` | Sharpe Ratio (5Y) |
| `sortinoRatio` | Sortino Ratio |
| `sortinoRatio3y` | Sortino Ratio (3Y) |
| `sortinoRatio5y` | Sortino Ratio (5Y) |
| `ma20` | 20-Day Moving Average |
| `ma50` | 50-Day Moving Average |
| `ma150` | 150-Day Moving Average |
| `ma200` | 200-Day Moving Average |
| `ma20ch` | Price Change 20-Day MA |
| `ma50ch` | Price Change 50-Day MA |
| `ma150ch` | Price Change 150-Day MA |
| `ma200ch` | Price Change 200-Day MA |
| `ma50vs200` | 50 vs. 200-Day MA |

### Company Info (26)

| id | name |
|---|---|
| `n` | Name |
| `industry` | Industry |
| `sector` | Sector |
| `exchange` | Exchange |
| `country` | Country |
| `usState` | U.S. State |
| `employees` | Employees |
| `employeesChange` | Employees Change |
| `employeesChangePercent` | Employees Growth |
| `founded` | Founded |
| `ipoDate` | IPO Date |
| `lastReportDate` | Financial Report Date |
| `fiscalYearEnd` | Fiscal Year End |
| `last10kFilingDate` | Last 10-K Release Date |
| `isSpac` | Is SPAC |
| `isPrimaryListing` | Is Primary Listing |
| `optionable` | Options |
| `inIndex` | In Index |
| `tags` | Tag |
| `priceCurrency` | Price Currency |
| `financialCurrency` | Financial Currency |
| `sic` | SIC Code |
| `cik` | CIK Code |
| `isin` | ISIN Number |
| `cusip` | CUSIP Number |
| `website` | Website |

### Earnings Report (8)

| id | name |
|---|---|
| `earningsDate` | Earnings Date |
| `lastEarningsDate` | Last Earnings Date |
| `nextEarningsDate` | Next Earnings Date |
| `earningsTime` | Earnings Time |
| `earningsRevenueEstimate` | Earnings Revenue Estimate |
| `earningsRevenueEstimateGrowth` | Revenue Estimated Growth |
| `earningsEpsEstimate` | Earnings EPS Estimate |
| `earningsEpsEstimateGrowth` | EPS Estimated Growth |

### Performance (12)

| id | name |
|---|---|
| `low52ch` | Price Change 52W Low |
| `high52ch` | Price Change 52W High |
| `high52Date` | 52-Week High Date |
| `low52Date` | 52-Week Low Date |
| `allTimeHigh` | All-Time High |
| `allTimeHighChange` | All-Time High Change (%) |
| `allTimeHighDate` | All-Time High Date |
| `allTimeLow` | All-Time Low |
| `allTimeLowChange` | All-Time Low Change (%) |
| `allTimeLowDate` | All-Time Low Date |
| `ipr` | Return From IPO Price |
| `iprfo` | Return From IPO Open |

### Price Change (11)

| id | name |
|---|---|
| `ch1w` | Price Change 1W |
| `ch1m` | Price Change 1M |
| `ch3m` | Price Change 3M |
| `ch6m` | Price Change 6M |
| `chYTD` | Price Change YTD |
| `ch1y` | Price Change 1Y |
| `ch3y` | Price Change 3Y |
| `ch5y` | Price Change 5Y |
| `ch10y` | Price Change 10Y |
| `ch15y` | Price Change 15Y |
| `ch20y` | Price Change 20Y |

### Total Return (11)

| id | name |
|---|---|
| `tr1w` | Total Return 1W |
| `tr1m` | Total Return 1M |
| `tr3m` | Total Return 3M |
| `tr6m` | Total Return 6M |
| `trYTD` | Total Return YTD |
| `tr1y` | Total Return 1Y |
| `tr3y` | Total Return 3Y |
| `tr5y` | Total Return 5Y |
| `tr10y` | Total Return 10Y |
| `tr15y` | Total Return 15Y |
| `tr20y` | Total Return 20Y |

### Annual Return (6)

| id | name |
|---|---|
| `cagr1y` | Return CAGR 1Y |
| `cagr3y` | Return CAGR 3Y |
| `cagr5y` | Return CAGR 5Y |
| `cagr10y` | Return CAGR 10Y |
| `cagr15y` | Return CAGR 15Y |
| `cagr20y` | Return CAGR 20Y |

### Forecasts, Analysts & Price Targets (18)

| id | name |
|---|---|
| `analystRatings` | Analyst Rating |
| `analystCount` | Analyst Count |
| `priceTarget` | Price Target |
| `priceTargetChange` | Price Target Upside (%) |
| `analystRatingsTop` | Top Analyst Rating |
| `analystCountTop` | Top Analyst Count |
| `analystPriceTargetTop` | Top Analyst Price Target |
| `priceTargetChangeTop` | Top Analyst Price Target Upside (%) |
| `epsThisQuarter` | EPS Growth This Quarter |
| `epsNextQuarter` | EPS Growth Next Quarter |
| `epsThisYear` | EPS Growth This Year |
| `epsNextYear` | EPS Growth Next Year |
| `revenueThisQuarter` | Rev. Growth This Quarter |
| `revenueNextQuarter` | Rev. Growth Next Quarter |
| `revenueThisYear` | Rev. Growth This Year |
| `revenueNextYear` | Rev. Growth Next Year |
| `eps3y` | EPS Growth Next 3Y |
| `revenue3y` | Rev. Growth Next 3Y |

### Dividends & Buybacks (15)

| id | name |
|---|---|
| `dividendYield` | Dividend Yield |
| `dps` | Dividend Per Share ($) |
| `lastDividend` | Last Dividend ($) |
| `dividendGrowth` | Dividend Growth |
| `dividendGrowthYears` | Dividend Growth Years |
| `dividendYears` | Dividend Payment Years |
| `divCAGR3` | Dividend Growth (3Y) |
| `divCAGR5` | Dividend Growth (5Y) |
| `divCAGR10` | Dividend Growth (10Y) |
| `payoutRatio` | Payout Ratio |
| `payoutFrequency` | Dividend Payout Frequency |
| `buybackYield` | Buyback Yield / Dilution |
| `totalReturn` | Shareholder Yield |
| `exDivDate` | Ex-Dividend Date |
| `paymentDate` | Payment Date |

### Shares Outstanding (7)

| id | name |
|---|---|
| `sharesOut` | Shares Outstanding |
| `float` | Float |
| `floatPercent` | Float Percentage |
| `sharesYoY` | Shares Change (YoY) |
| `sharesQoQ` | Shares Change (QoQ) |
| `sharesInsiders` | Shares Insiders |
| `sharesInstitutions` | Shares Institutions |

### Revenue / Sales (8)

| id | name |
|---|---|
| `revenue` | Revenue |
| `revenueGrowth` | Revenue Growth |
| `revenueGrowthQ` | Revenue Growth (Q) |
| `revenueGrowthQoQ` | Revenue Growth (QoQ) |
| `revenueGrowth3Y` | Revenue Growth 3Y |
| `revenueGrowth5Y` | Revenue Growth 5Y |
| `revenueGrowthYears` | Revenue Growth Years |
| `revenueGrowthQuarters` | Revenue Growth Quarters |

### Net Income (10)

| id | name |
|---|---|
| `netIncome` | Net Income |
| `netIncomeGrowth` | Net Income Growth |
| `netIncomeGrowthQ` | Net Income Growth (Q) |
| `netIncomeGrowthQoQ` | Net Income Growth (QoQ) |
| `netIncomeGrowth3Y` | Net Income Growth 3Y |
| `netIncomeGrowth5Y` | Net Income Growth 5Y |
| `netIncomeGrowthYears` | Net Income Growth Years |
| `netIncomeGrowthQuarters` | Net Income Growth Quarters |
| `profitableYears` | Profitable Years |
| `profitableQuarters` | Profitable Quarters |

### Earnings Per Share (EPS) (8)

| id | name |
|---|---|
| `eps` | EPS |
| `epsGrowth` | EPS Growth |
| `epsGrowthQ` | EPS Growth (Q) |
| `epsGrowthQoQ` | EPS Growth (QoQ) |
| `epsGrowth3Y` | EPS Growth 3Y |
| `epsGrowth5Y` | EPS Growth 5Y |
| `epsGrowthYears` | EPS Growth Years |
| `epsGrowthQuarters` | EPS Growth Quarters |

### Other Profits (12)

| id | name |
|---|---|
| `grossProfit` | Gross Profit |
| `grossProfitGrowth` | Gross Profit Growth |
| `grossProfitGrowthQ` | Gross Profit Growth (Q) |
| `grossProfitGrowth3Y` | Gross Profit Growth 3Y |
| `grossProfitGrowth5Y` | Gross Profit Growth 5Y |
| `operatingIncome` | Operating Income |
| `operatingIncomeGrowth` | Op. Income Growth |
| `operatingIncomeGrowthQ` | Op. Income Growth (Q) |
| `operatingIncomeGrowth3Y` | Op. Income Growth 3Y |
| `operatingIncomeGrowth5Y` | Op. Income Growth 5Y |
| `ebit` | EBIT |
| `ebitda` | EBITDA |

### Margins (7)

| id | name |
|---|---|
| `grossMargin` | Gross Margin |
| `operatingMargin` | Operating Margin |
| `pretaxMargin` | Pretax Margin |
| `profitMargin` | Profit Margin |
| `fcfMargin` | FCF Margin |
| `ebitdaMargin` | EBITDA Margin |
| `ebitMargin` | EBIT Margin |

### Cash Flow (22)

| id | name |
|---|---|
| `operatingCF` | Operating Cash Flow |
| `depreciationAmortization` | Depreciation & Amortization |
| `netBorrowing` | Net Borrowing |
| `investingCF` | Investing Cash Flow |
| `financingCF` | Financing Cash Flow |
| `netCF` | Net Cash Flow |
| `capex` | Capital Expenditures |
| `fcf` | Free Cash Flow |
| `adjustedOCF` | Operating Cash Flow - SBC |
| `adjustedFCF` | Free Cash Flow - SBC |
| `fcfPerShare` | FCF / Share |
| `fcfGrowth` | FCF Growth |
| `fcfGrowthQ` | FCF Growth (Q) |
| `fcfGrowthQoQ` | FCF Growth (QoQ) |
| `fcfGrowth3Y` | FCF Growth 3Y |
| `fcfGrowth5Y` | FCF Growth 5Y |
| `ocfGrowth` | OCF Growth |
| `ocfGrowthQ` | OCF Growth (Q) |
| `ocfGrowthQoQ` | OCF Growth (QoQ) |
| `ocfGrowth3Y` | OCF Growth 3Y |
| `ocfGrowth5Y` | OCF Growth 5Y |
| `ocfGrowth10Y` | OCF Growth 10Y |

### Expenses (4)

| id | name |
|---|---|
| `shareBasedComp` | Stock-Based Compensation |
| `sbcByRevenue` | SBC / Revenue |
| `researchAndDevelopment` | Research & Development |
| `rndByRevenue` | R&D / Revenue |

### Cash & Debt (9)

| id | name |
|---|---|
| `cash` | Total Cash |
| `debt` | Total Debt |
| `debtGrowth` | Debt Growth (YoY) |
| `debtGrowthQoQ` | Debt Growth (QoQ) |
| `debtGrowth3Y` | Debt Growth (3Y) |
| `debtGrowth5Y` | Debt Growth (5Y) |
| `netCash` | Net Cash (Debt) |
| `netCashGrowth` | Net Cash Growth |
| `netCashByMarketCap` | Cash / Market Cap |

### Assets, Liabilities, Equity (15)

| id | name |
|---|---|
| `assets` | Total Assets |
| `equity` | Shareholders' Equity |
| `bvPerShare` | Book Value Per Share |
| `tangibleBookValue` | Tangible Book Value |
| `tangibleBookValuePerShare` | TBV Per Share |
| `ppne` | Property, Plant & Equipment |
| `goodwill` | Goodwill |
| `currentAssets` | Current Assets |
| `longTermAssets` | Long-Term Assets |
| `currentLiabilities` | Current Liabilities |
| `longTermLiabilities` | Long-Term Liabilities |
| `liabilities` | Total Liabilities |
| `workingCapital` | Working Capital |
| `netWorkingCapital` | Net Working Capital |
| `workingCapitalTurnover` | Working Capital Turnover |

### Balance Sheet Strength (9)

| id | name |
|---|---|
| `currentRatio` | Current Ratio |
| `quickRatio` | Quick Ratio |
| `debtEquity` | Debt / Equity |
| `debtEbitda` | Debt / EBITDA |
| `debtFcf` | Debt / FCF |
| `netDebtEquity` | Net Debt / Equity |
| `netDebtEbitda` | Net Debt / EBITDA |
| `netDebtFcf` | Net Debt / FCF |
| `interestCoverage` | Interest Coverage |

### Short Selling Statistics (3)

| id | name |
|---|---|
| `shortFloat` | Short % Float |
| `shortShares` | Short % Shares |
| `shortRatio` | Short Ratio |

### Financial Performance (9)

| id | name |
|---|---|
| `roe` | Return on Equity |
| `roa` | Return on Assets |
| `roic` | Return on Invested Capital |
| `roce` | Return on Capital Employed |
| `roe5y` | Return on Equity (5Y) |
| `roa5y` | Return on Assets (5Y) |
| `roic5y` | Return on Capital (5Y) |
| `revPerEmployee` | Revenue Per Employee |
| `profitPerEmployee` | Profits Per Employee |

### Stock Splits (2)

| id | name |
|---|---|
| `lastSplitType` | Last Stock Split Type |
| `lastSplitDate` | Last Stock Split Date |

### Taxes (3)

| id | name |
|---|---|
| `incomeTax` | Income Taxes |
| `taxRate` | Effective Tax Rate |
| `taxByRevenue` | Tax / Revenue |

### REIT Metrics (2)

| id | name |
|---|---|
| `ffo` | Funds From Operations (FFO) |
| `pFFO` | P/FFO Ratio |

### Fair Value (5)

| id | name |
|---|---|
| `lynchFairValue` | Lynch Fair Value |
| `grahamNumber` | Graham Number |
| `lynchUpside` | Lynch Upside |
| `grahamUpside` | Graham Upside |
| `wacc` | WACC |

### Other (5)

| id | name |
|---|---|
| `assetTurnover` | Asset Turnover |
| `inventoryTurnover` | Inventory Turnover |
| `zScore` | Altman Z-Score |
| `fScore` | Piotroski F-Score |
| `views` | Views |
