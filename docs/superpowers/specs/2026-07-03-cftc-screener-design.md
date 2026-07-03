# CFTC COT Positioning Screener — Design

**Date:** 2026-07-03
**Status:** Approved, ready for implementation planning
**Data source:** [CFTC Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm),
served via the Socrata SODA API at
`https://publicreporting.cftc.gov/resource/6dca-aqww.json` — the **Legacy
Futures-Only** report. No API key required; an optional Socrata app token
(`CFTC_APP_TOKEN` in `.env`) lifts anonymous rate limits.

## Goal

Pull weekly **Commitments of Traders (COT)** positioning for a curated set of
futures markets into SQLite, so the trading bot has a **positioning reader** —
how speculators, hedgers, and small traders are positioned across index futures,
rates, FX, metals, energy, and grains — with enough history to compute each
market's **COT Index** (where current net speculator positioning sits within its
own multi-year range).

This is the **fifth** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`). It reuses the proven `screener_common` machinery and the FRED
module layout, but takes a **third data shape**.

## Key realization: this is a *panel* (a third data shape)

- The first three screeners (`stocks`, `reddit`, `edgar`) are **cross-sectional**:
  a universe of entities × metrics captured at one moment; each snapshot is a
  wide, self-contained state-of-the-world, snapshot-scoped.
- `fred` is **time-series**: a few series, each with decades of dated
  observations, upserted by `(series_id, date)`.
- `cftc` is a **panel**: many markets × weekly report dates × ~30 positioning
  metrics per row. Like FRED, the "rich data" is the *history* (a COT regime is
  only legible across time — you cannot tell whether net-spec = +120k contracts
  is crowded or neutral from one number), so the fact table is keyed by
  `(code, report_date)` and **upserted**, not snapshot-scoped. `snapshots`
  records fetch-run provenance; the positioning history persists across pruning.

## Why the Legacy Futures-Only report

CFTC publishes several report families. We start with **Legacy Futures-Only**
(`6dca-aqww`):

| Report | Trader breakdown | Coverage | History | Dataset |
|---|---|---|---|---|
| **Legacy** (chosen) | Non-Commercial (speculators) · Commercial (hedgers) · Non-Reportable (small) | **All markets** | **1986→now** | `6dca-aqww` |
| Disaggregated | Producer/Merchant vs Swap Dealer; Managed-Money vs Other | Physical commodities | ~2006→now | `72hh-3qpy` |
| TFF | Dealer · Asset Manager · Leveraged Funds | Financial futures | ~2010→now | `gpe5-46if` |

Rationale:

1. **One report spans the whole universe.** Legacy is the only family covering
   every market (index, rates, FX, metals, energy, ags) in a single endpoint.
   Disaggregated and TFF each cover only a slice.
2. **The COT Index is history-hungry.** It is a 3-year rolling percentile;
   Legacy's 1986 start is a real advantage. TFF only reaches back to ~2010.
3. **Still genuinely rich** — ~89 fields per market-week (long/short/net per
   trader type, WoW changes, % of open interest, trader counts, top-4/top-8
   concentration). We keep the analytically useful ~30 and derive signals in
   views.
4. **Not a dead end.** All families share the same shape; adding TFF's
   "Leveraged Funds" detail later is an additive second dataset (a
   `report_family` distinction + a second catalog), not a rewrite. Out of scope
   here (YAGNI).

## Source verification (confirmed first-hand 2026-07-03)

Both URLs the user cited are correct. Verified live via the Socrata API:

1. **Endpoint** `https://publicreporting.cftc.gov/resource/6dca-aqww.json`
   returns clean JSON. `min(report_date_as_yyyy_mm_dd)=1986-01-15`,
   `max=2026-06-23`, `count(*)=284,882` rows across all markets.
2. **Stable market key is `cftc_contract_market_code`**, NOT the name. The same
   code appears under multiple `market_and_exchange_names` over time (e.g.
   `13874A` = "E-MINI S&P 500" has been renamed 3×). Filtering by code pulls the
   full history across all name variants in one query. Look-alikes must be
   pinned by exact code: crude is `067651` (NYMEX/WTI) vs `067411` (ICE).
3. **Verified codes:** Gold(COMEX)=`088691`, E-mini S&P=`13874A`, Euro
   FX=`099741`, WTI Crude(NYMEX)=`067651`. Remaining catalog codes are verified
   live at implementation time (like the FRED catalog); any that return no rows
   are dropped.
4. **Socrata query params** work as expected: `$where`, `$order`, `$select`,
   `$group`, `$limit` (default 1000, max 50000), `$offset`. Missing numeric
   cells arrive absent or as strings and are stored as `NULL`.

## Architecture

Mirrors `fred_screener` module-for-module.

```
cftc_screener/
  __init__.py
  catalog.py   # curated Market list + select_ids() filter (copied shape from FRED)
  fetch.py     # Socrata client: bounded backoff, per-market query, row parsing
  db.py        # schema (markets/cot/snapshots) + upserts + ELT views + prune
  run.py       # skip-and-continue orchestration + argparse CLI (main)
```

Registered in `registry.py` as `"cftc": cftc_main`. Reuses
`screener_common.connect` (WAL). Prune is FRED-style single-table (positioning
history is NOT snapshot-scoped, so it must NOT use the `screener_common` cascade
prune).

### 1. Catalog (`catalog.py`)

```python
@dataclass(frozen=True)
class Market:
    code: str          # cftc_contract_market_code, the stable key
    name: str          # human label (for readability; canonical name refreshed
                       # from the newest fetched row at write time)
    asset_class: str   # equity_index | rates | fx | metals | energy | ags | softs
```

`CATALOG: list[Market]` — ~30 markets spanning:
- **equity_index:** E-mini S&P 500 `13874A`, Nasdaq-100 (E-mini), Russell 2000,
  Dow, VIX.
- **rates:** 2Y / 5Y / 10Y T-Note, T-Bond, Fed Funds, SOFR.
- **fx:** Euro FX `099741`, Japanese Yen, British Pound, Swiss Franc, Canadian
  Dollar, Australian Dollar, US Dollar Index.
- **metals:** Gold `088691`, Silver, Copper, Platinum.
- **energy:** WTI Crude `067651`, Natural Gas, RBOB Gasoline, Heating Oil.
- **ags:** Corn, Soybeans, Wheat (Chicago), Soybean Oil, Live Cattle, Lean Hogs.
- **softs:** Sugar, Coffee, Cotton, Cocoa.

`select_ids(all_codes, only, exclude, add)` — identical logic to
`fred_screener.catalog.select_ids` (ordered, de-duplicated, blank/exclude-aware).
Exact codes are verified live during implementation; any that return no rows are
dropped with a note.

### 2. Fetch (`fetch.py`)

Reuses the FRED HTTP scaffolding (`_http_get` with bounded exponential backoff,
`_RETRY_STATUS = {429, 500, 502, 503, 504}`, `Retry-After` honored, max 5
attempts). Differences from FRED:

- **No API key.** Optional `CFTC_APP_TOKEN` sent as an `X-App-Token` request
  header (not a query param) when present. `require_*` is not needed — anonymous
  works; the token only raises rate limits. If the token is absent, proceed
  without it (log nothing sensitive).
- **Per-market query, incremental:**
  ```
  GET /resource/6dca-aqww.json
      ?$where=cftc_contract_market_code='{code}'[ AND report_date_as_yyyy_mm_dd > '{since}']
      &$order=report_date_as_yyyy_mm_dd
      &$limit=50000
  ```
  `since` is the max `report_date` already stored for that market (full history
  on first run; only new weeks thereafter). `--start YYYY-MM-DD` sets a floor for
  the first run.
- **`parse_rows(payload) -> list[dict]`** maps each Socrata record to the curated
  column set, coercing numeric strings to `int`/`float` and absent/blank cells to
  `None`. Report date normalized to `YYYY-MM-DD`.

### 3. Schema (`db.py`)

```sql
CREATE TABLE IF NOT EXISTS markets (
    code        TEXT PRIMARY KEY,   -- cftc_contract_market_code
    name        TEXT,               -- newest market_and_exchange_names seen
    asset_class TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);

CREATE TABLE IF NOT EXISTS cot (
    code           TEXT NOT NULL REFERENCES markets(code),
    report_date    TEXT NOT NULL,   -- YYYY-MM-DD (report_date_as_yyyy_mm_dd)
    open_interest  INTEGER,
    -- non-commercial (speculators)
    noncomm_long   INTEGER, noncomm_short  INTEGER, noncomm_spread INTEGER,
    -- commercial (hedgers)
    comm_long      INTEGER, comm_short     INTEGER,
    -- non-reportable (small)
    nonrept_long   INTEGER, nonrept_short  INTEGER,
    -- week-over-week changes
    chg_oi         INTEGER,
    chg_noncomm_long INTEGER, chg_noncomm_short INTEGER,
    chg_comm_long  INTEGER, chg_comm_short INTEGER,
    -- % of open interest
    pct_oi_noncomm_long REAL, pct_oi_noncomm_short REAL,
    pct_oi_comm_long    REAL, pct_oi_comm_short    REAL,
    -- trader counts
    traders_total  INTEGER,
    traders_noncomm_long INTEGER, traders_noncomm_short INTEGER,
    traders_comm_long INTEGER, traders_comm_short INTEGER,
    -- concentration (top 4 / top 8, net)
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_date ON cot(report_date);
```

`snapshots` (provenance): `id`, `captured_at`, `market_count`, `row_count`.

Writers:
- `upsert_markets(conn, rows, captured_at)` — refresh `name`/`asset_class`/
  `last_seen`, preserve `first_seen` (FRED `upsert_series` shape). `name` taken
  from the newest fetched row.
- `write_cot(conn, code, rows)` — upsert by `(code, report_date)`, dedupe within
  batch (last wins); revised weeks overwrite in place, dates never duplicated
  (FRED `write_observations` shape). Returns rows written.
- `write_snapshot(conn, captured_at, market_count, row_count) -> id`.
- `prune(conn, keep_days, now_iso)` — FRED-style single-table delete of old
  `snapshots` only. **Do NOT cascade into `cot`** (positioning history is the
  store).

### 4. Views (the derived signals)

```sql
-- net positions per row (long - short), the analytical primitive
CREATE VIEW IF NOT EXISTS v_net AS
SELECT code, report_date, open_interest,
       noncomm_long - noncomm_short AS net_noncomm,
       comm_long    - comm_short    AS net_comm,
       nonrept_long - nonrept_short AS net_nonrept
FROM cot;

-- latest week per market, joined to the market dimension
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
  SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
  FROM v_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_noncomm, r.net_comm, r.net_nonrept
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

-- COT Index: 3-year (156-week) rolling percentile of net non-commercial position
CREATE VIEW IF NOT EXISTS v_cot_index AS
WITH w AS (
  SELECT code, report_date, net_noncomm,
         MIN(net_noncomm) OVER win AS lo,
         MAX(net_noncomm) OVER win AS hi
  FROM v_net
  WINDOW win AS (PARTITION BY code ORDER BY report_date
                 ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_noncomm, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_noncomm - lo) / (hi - lo) END AS cot_index
FROM w;

-- latest COT index + net + %OI + WoW change, side by side (positioning board)
CREATE VIEW IF NOT EXISTS v_positioning AS ...  -- v_latest ⋈ latest v_cot_index ⋈ cot pct/chg

-- markets currently at a positioning extreme (bot watchlist)
CREATE VIEW IF NOT EXISTS v_extremes AS
SELECT * FROM v_positioning
WHERE cot_index >= 90 OR cot_index <= 10;
```

### 5. CLI & orchestration (`run.py`)

`run(db_path, only, exclude, add, start, keep_days, app_token, fetch_rows=..., now_iso=...)`
— for each selected code: read the market's max stored `report_date`, fetch new
rows (skip-and-continue on any per-market error, logging only
`type(e).__name__`), `upsert_markets` + `write_cot`, accumulate counts; then
`write_snapshot` and optional `prune`. Returns
`(snapshot_id, market_count, row_count)`.

CLI (`main`): `python main.py cftc`
```
--db cftc.db
--only CODES        comma-separated contract codes (default: catalog)
--exclude CODES     comma-separated codes to skip
--add CODE          extra code not in the catalog (repeatable)
--start YYYY-MM-DD  floor for the first fetch (default: full history)
--keep-days N       prune snapshot provenance older than N days
```
App token read from `CFTC_APP_TOKEN` env; never printed.

### 6. Testing (mirror `test_fred_*`)

- `test_cftc_catalog.py` — `select_ids` only/exclude/add/dedupe.
- `test_cftc_fetch.py` — `parse_rows` coercion (ints/floats/None, date
  normalization); backoff retries on 429/5xx via a fake opener; app-token header
  attached when present, absent otherwise.
- `test_cftc_db_schema.py` — schema + views create idempotently.
- `test_cftc_db_write.py` — `write_cot` upsert overwrites a revised week in place
  (no duplicate dates); `upsert_markets` preserves `first_seen`, refreshes
  `name`.
- `test_cftc_run.py` — skip-and-continue on a failing market; incremental fetch
  passes the correct `since`; empty-run writes an empty snapshot.
- COT-index math: seed a synthetic market whose net-spec walks a known range;
  assert `v_cot_index` = 100 at the max, 0 at the min, ~50 mid-range.
- `test_registry.py` — extend to assert `"cftc"` dispatches.

## Non-goals (YAGNI)

- Disaggregated / TFF report families (additive later).
- Combined futures+options report (`6dca-aqww` is futures-only by design).
- Price data / signal backtesting — this screener only *stores positioning*;
  signal consumption lives elsewhere in the bot.
- Automated scheduling — invoked on demand like the other screeners.

## Environment

Add to `.env.example`:
```
CFTC_APP_TOKEN= # optional Socrata app token (lifts rate limits; not required)
```
