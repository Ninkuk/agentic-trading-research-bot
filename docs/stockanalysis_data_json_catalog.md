# stockanalysis.com `__data.json` — Endpoint Catalog

Reverse-engineered reference for the unauthenticated, undocumented SvelteKit
data endpoint that backs every page on stockanalysis.com. This complements the
`stock_analysis_screener` module (which already consumes the screener slice).

> **Access note:** stockanalysis.com is an approved trusted source for this
> project. `robots.txt` disallows nothing for generic user agents. No auth, API
> key, or token is required. Be a polite client (sane rate, real User-Agent).

Probe any route yourself with the bundled decoder:

```bash
python -m stock_analysis_screener.probe /stocks/AAPL/statistics/
python -m stock_analysis_screener.probe --keys /markets/gainers/ /ipos/2024/
```

## 1. The technique

stockanalysis.com is a **SvelteKit** app. For every route `/{path}/` there is a
sibling `/{path}/__data.json` returning the exact server `load()` output — the
same data the page hydrates from.

- **URL rule:** append `__data.json` to the route (before any query string).
  `/stocks/AAPL/statistics/` → `/stocks/AAPL/statistics/__data.json`.
  Query params carry through: `/stocks/AAPL/financials/__data.json?p=quarterly`.
- **Limit:** a few hub/interactive routes (`/markets/`, `/quote/{index}/`,
  `/stocks/compare/`, `/etf/compare/`) stream their content client-side, so
  their `__data.json` contains only session cookies — nothing to harvest.

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
(e.g. `/quote/adx/2POINTZERO/`). ETFs under `/etf/{T}/…`.

### Per-ticker (stocks & international quotes)

| Route (+ `/__data.json`) | Key payload |
|---|---|
| `/stocks/{T}/` | Overview: revenue, netIncome, eps(+growth), peRatio/forwardPE, marketCap, beta, sharesOut, dividend, earningsDate, analyst target, infoTable, news |
| `/stocks/{T}/financials/` | Income statement (`financialData`, `map`, `period`, `availableSources`). `?p=quarterly` for quarterly |
| `…/financials/balance-sheet/` | Balance sheet (same shape) |
| `…/financials/cash-flow-statement/` | Cash-flow statement |
| `…/financials/ratios/` | Ratios |
| `…/financials/segments/` | **Pro-gated** — `info` placeholder only |
| `/stocks/{T}/statistics/` | 20 grouped blocks: valuation, margins, ratios, scores (Altman Z), fairValue (some `proOnly`), shortSelling, shares, dividends, taxes, analystForecasts |
| `/stocks/{T}/dividend/` | Full dividend history, yield, payout, chart |
| `/stocks/{T}/company/` | Profile: description, executives, contact, filings, logoURL |
| `/stocks/{T}/forecast/` | priceTargets (avg/median/low/high/count), per-analyst `ratings` (firm/analyst/PT/rating + track record), monthly consensus `recommendations`, EPS/revenue `estimates` |
| `/stocks/{T}/history/` | OHLCV bars `{o,h,l,c,a,v,t,ch}`, range-adjustable, back to 1982 |
| `/stocks/{T}/employees/` | Headcount history (annual/quarterly) + peers |
| `/stocks/{T}/market-cap/` | Market-cap history, performance, peers |

### Per-ETF

| Route | Key payload |
|---|---|
| `/etf/{T}/` | aum, nav, expenseRatio, dividendYield, payout*, holdings, performance, provider |
| `/etf/{T}/holdings/` | Holdings + sector/country/asset allocation |
| `/etf/{T}/dividend/` | Dividend history + chart |
| `/etf/provider/{slug}/` | All provider ETFs as a screener grid (e.g. `vanguard`) |

### Bulk universe dumps (see §4)

| Route | Rows | Selectable metrics |
|---|---|---|
| `/stocks/screener/` | **5,595 stocks** | **310** |
| `/etf/screener/` | **5,447 ETFs** | **110** |
| `/tools/mutf-screener/` | **23,922 funds** | **83** |

### Market movers & discovery (see §5 for the query DSL)

| Route | Contents |
|---|---|
| `/markets/gainers/` · `/losers/` · `/active/` | Ranked movers + full `query` filter object |
| `/markets/premarket/` · `/markets/premarket/gainers/` | Pre-market movers |
| `/trending/` | Most-viewed stocks (`views` metric) |
| `/analysts/top-stocks/` | Top analyst-rated stocks (screener grid) |

### Corporate actions — all `{action, data, fullCount, props, type}`

`/actions/acquisitions/` · `/bankruptcies/` · `/changes/` (ticker changes) ·
`/delisted/` · `/listed/` (new listings) · `/spinoffs/` · `/splits/`

### IPOs

`/ipos/` (recent + upcoming) · `/ipos/calendar/` (this/next-week/later) ·
`/ipos/statistics/` · `/ipos/withdrawn/` · `/ipos/{year}/` (e.g. `/ipos/2024/`)

### Analysts

`/analysts/` (directory) · `/analysts/{slug}/` (rank, scores, covered
sectors/industries, full ratings history) · `/analysts/top-stocks/`

### Other data-bearing routes

| Route | Contents |
|---|---|
| `/stocks/earnings-calendar/` | 75 days w/ before-open/after-close counts + 15 grouped weeks (~620 KB) |
| `/news/` · `/news/all-stocks/` · `/news/press-releases/` | News feeds |
| `/stocks/industry/` · `/industry/sectors/` · `/industry/all/` | Sector/industry directories |
| `/stocks/industry/{name}/` | Industry constituents + stats (e.g. `semiconductors`) |
| `/list/` · `/list/exchanges/` · `/list/{exchange}/` | Curated & per-exchange lists (stock + ETF grids) |
| `/private/{slug}/` | Private-company profiles (valuation, funding, Forge/Hiive links) |
| `/symbol-lookup/?q=…` | Autocomplete search |

## 4. Bulk screeners + the data-points API

Hitting `/stocks/screener/__data.json` returns the **entire universe in one
request** (~1 MB) with a fixed default column set
(`s, n, marketCap, price, change, industry, volume, peRatio`) plus a `dataPoints`
catalog and `dataPointCategories`. To pull *arbitrary* columns for the whole
universe, use the companion JSON API (already wired in `fetch.py`):

```
GET /_api/endpoints/screener/data-points?type=s&ids=<space-separated ids>
```

`type`: `s` stocks · `e` ETFs · `f` mutual funds. `ids` are the data-point ids
from §6. Response shape: `{data: {data: {TICKER: {id: value, ...}}}}`.
`catalog.fetch_catalog()` decodes the `dataPoints` catalog + universe count from
the screener `__data.json`; `fetch.fetch_data_points(ids, type_)` pulls values.

## 5. Screener / movers query DSL

The movers and trending pages expose the server-side query object under `query`
in their `__data.json`. It is the same filter grammar the screener uses:

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

`columns`, `main`, and `filters` all reference the §6 data-point ids, so any of
the 310 stock metrics is sortable/filterable. Observed presets:

| Page | `main` | `filters` |
|---|---|---|
| `/markets/gainers/` | `change` desc | `change-over-0`, `priceDate-isLastTradingDay` |
| `/markets/losers/` | `change` asc | `change-under-0`, `priceDate-isLastTradingDay` |
| `/markets/active/` | `volume` desc | `volume-over-0`, `priceDate-isLastTradingDay` |
| `/markets/premarket/gainers/` | `premarketChangePercent` desc | `premarketChangePercent-over-0`, `premarketDate-isLastTradingDay` |
| `/trending/` | `views` desc | `views-over-1` |

## 6. Stock screener data-points (310)

The full selectable metric catalog for `type=s`, grouped by category (the same
`id`s used as screener columns and as filter/sort keys in §5). ETF (`type=e`,
110 metrics) and fund (`type=f`, 83 metrics) catalogs are subsets/variants —
fetch them live with `catalog.fetch_catalog()` against the respective screener.

### Price & Volume (26)

| id | name |
|---|---|
| `price` | Stock Price |
| `change` | Price Change 1D |
| `volume` | Volume |
| `dollarVolume` | Dollar Volume |
| `open` | Open Price |
| `low` | Low Price |
| `high` | High Price |
| `close` | Previous Close |
| `priceDate` | Stock Price Date |
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

### Valuation & Ratios (29)

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
| `pOcfRatio` | P/OCF Ratio |
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

### Technical Analysis (15)

| id | name |
|---|---|
| `rsi` | Relative Strength Index (RSI) |
| `rsiWeekly` | Weekly RSI |
| `rsiMonthly` | Monthly RSI |
| `atr` | Average True Range (ATR) |
| `sharpeRatio` | Sharpe Ratio |
| `sortinoRatio` | Sortino Ratio |
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

### Revenue / Sales (7)

| id | name |
|---|---|
| `revenue` | Revenue |
| `revenueGrowth` | Revenue Growth |
| `revenueGrowthQ` | Revenue Growth (Q) |
| `revenueGrowth3Y` | Revenue Growth 3Y |
| `revenueGrowth5Y` | Revenue Growth 5Y |
| `revenueGrowthYears` | Revenue Growth Years |
| `revenueGrowthQuarters` | Revenue Growth Quarters |

### Net Income (8)

| id | name |
|---|---|
| `netIncome` | Net Income |
| `netIncomeGrowth` | Net Income Growth |
| `netIncomeGrowthQ` | Net Income Growth (Q) |
| `netIncomeGrowth3Y` | Net Income Growth 3Y |
| `netIncomeGrowth5Y` | Net Income Growth 5Y |
| `netIncomeGrowthYears` | Net Income Growth Years |
| `netIncomeGrowthQuarters` | Net Income Growth Quarters |
| `profitableYears` | Profitable Years |

### Earnings Per Share (EPS) (7)

| id | name |
|---|---|
| `eps` | EPS |
| `epsGrowth` | EPS Growth |
| `epsGrowthQ` | EPS Growth (Q) |
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

### Cash Flow (19)

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
| `adjustedFCF` | Free Cash Flow - SBC |
| `fcfPerShare` | FCF / Share |
| `fcfGrowth` | FCF Growth |
| `fcfGrowthQ` | FCF Growth (Q) |
| `fcfGrowth3Y` | FCF Growth 3Y |
| `fcfGrowth5Y` | FCF Growth 5Y |
| `ocfGrowth` | OCF Growth |
| `ocfGrowthQ` | OCF Growth (Q) |
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
