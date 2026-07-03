# CFTC Disaggregated + TFF COT Extension — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [CFTC Commitments of Traders](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm),
served via the same Socrata SODA host the `cftc_screener` already uses —
`https://publicreporting.cftc.gov/resource/{dataset}.json`. New datasets:
**Disaggregated Futures-Only** `72hh-3qpy` and **Traders in Financial Futures
(TFF) Futures-Only** `gpe5-46if`. No API key required; the same optional
`CFTC_APP_TOKEN` (`X-App-Token` header) lifts anonymous rate limits.
**Confidence:** 🟢 verified (endpoints live-checked 2026-07-03; supplemental
dataset id and combined-F&O variant ids tagged 🟡 — confirm live at
implementation time).

## Goal

Extend the existing CFTC positioning reader from a single report family to the
**three trader-classification families CFTC publishes**, so the bot can read the
*same markets through finer lenses*:

- **Legacy** (already shipped): Non-Commercial vs Commercial vs Non-Reportable —
  the broad speculator/hedger cut across every market, 1986→now.
- **Disaggregated**: splits the commercial block into **Producer/Merchant/
  Processor/User** vs **Swap Dealers**, and the speculator block into **Managed
  Money** vs **Other Reportables** — physical commodities (ags, energy, metals,
  softs).
- **TFF (Traders in Financial Futures)**: **Dealer/Intermediary** · **Asset
  Manager/Institutional** · **Leveraged Funds** · **Other Reportables** —
  financial futures (equity index, rates, FX, VIX).

The payoff is two sharper gauges the Legacy report cannot express: **Managed-
Money net** (the dedicated commodity-CTA speculator, Disaggregated) and
**Leveraged-Funds net** (the hedge-fund speculator in financials, TFF). Both feed
the same **COT-Index** (multi-year rolling percentile) logic the legacy screener
already computes — now per `(family, code)`.

This is an **extension of the fifth screener**, not a sixth. The CFTC design spec
pre-committed to exactly this shape: *"adding TFF's 'Leveraged Funds' detail
later is an additive second dataset (a `report_family` distinction + a second
catalog), not a rewrite."* This document cashes that in.

## Recommendation: a `report_family` dimension inside `cftc_screener`

**Extend the existing package with a family axis** rather than spawn sibling
packages. Concretely:

1. Keep the dispatcher name **`cftc`**. Add one flag: `--family
   {legacy,disaggregated,tff,supplemental}`, **default `legacy`** — so every
   existing invocation and test is byte-for-byte back-compatible.
2. A family selects a `(dataset_id, catalog, fact_table, field_map)` bundle; the
   fetch/backoff/token/lookback machinery and the run orchestration are shared
   verbatim.
3. Each family gets its own curated catalog and its own fact table, keyed the
   same way (`(code, report_date)`), reusing the one `markets` dimension.

### Why the family extension wins over sibling packages

| | `report_family` extension (chosen) | Sibling packages (`cftc_disagg/`, `cftc_tff/`) |
|---|---|---|
| Socrata fetch (backoff, token, `$where`/`$order`/`$limit`) | reused as-is, one code path | copy-pasted 3× |
| 10-week revision lookback + `--full` | inherited unchanged | re-implemented per package |
| `markets` dimension | one shared table | duplicated, drifts |
| Dispatcher surface | one name (`cftc`), one flag | three names to register + document |
| COT-Index / positioning views | one parametrized shape per family | re-derived per package |
| Cost of a 4th family (supplemental) | add a catalog + field-map + table | a whole new package |

The datasets differ **only** in *which trader columns exist* — the transport,
the key `(code, report_date)`, the revision behavior, and the analytics
(net = long − short; COT-Index = rolling percentile of the key speculator net)
are identical. That is the textbook signal for a **parametrized dimension**, not
parallel packages. Sibling packages would triplicate the Socrata client and the
lookback logic that `2026-07-03-cftc-revision-lookback-design.md` just finished
hardening — and every future fix would have to land three times.

## Source notes (confirmed 2026-07-03)

- **Datasets, same host as legacy** (`publicreporting.cftc.gov/resource/{id}.json`):
  - Disaggregated Futures-Only = **`72hh-3qpy`** 🟢
  - TFF Futures-Only = **`gpe5-46if`** 🟢
  - Supplemental (Commodity Index Traders, 13 agricultural markets, **combined
    futures + options only**) = dataset id 🟡 **confirm live at implementation
    time**.
  - Combined-futures-and-options variants of Disaggregated and TFF exist as
    **separate dataset ids** 🟡 confirm live — out of scope for the first cut
    (the legacy screener is futures-only by design; keep families consistent).
- **Bulk fallback:** historical zipped comma-delimited files at
  [cftc.gov HistoricalCompressed](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)
  — a backfill/verification source only; the Socrata JSON API is the primary path
  (matches legacy).
- **History depth:** Disaggregated begins **September 2009**; TFF begins **20 Jul
  2010** (a consolidated historical file backcasts TFF to **2006**). Legacy's
  1986→now is unchanged. The COT-Index is history-hungry (a 156-week window), so
  the shorter Disaggregated/TFF spans mean early years yield a `NULL` index until
  the window fills — the same behavior the legacy `v_cot_index` already handles
  (`CASE WHEN hi <> lo`).
- **Cadence:** weekly, released **Friday 15:30 ET** on a **Tuesday-close**
  snapshot; holiday weeks shift the release. Identical to legacy → the same
  10-week `>=` revision lookback re-absorbs CFTC's after-the-fact corrections,
  and `--full` forces a deep re-pull.
- **Query params** (`$where`, `$order`, `$select`, `$limit` max 50000, `$offset`)
  behave exactly as in the legacy screener; the stable key is
  `cftc_contract_market_code`, and markets are pinned by exact code (verified
  live at implementation time, like the FRED/legacy catalogs). 🟡 The **field
  names** for each family's trader columns (e.g. `swap_positions_long_all`,
  `m_money_positions_long_all`, `lev_money_positions_long_all`) must be confirmed
  against the live dataset schema — same "confirm exact codes live" caveat the
  legacy spec applied to contract codes.

## Data-shape classification: still a *panel*, now family-tagged

No new shape. Each family is the same **panel** as legacy — many markets × weekly
report dates × ~30 positioning metrics — keyed `(code, report_date)` and
**upserted**, with `snapshots` recording only fetch-run provenance. The one new
axis is `report_family`, resolved to a distinct fact table (see below). History
is not snapshot-scoped and survives pruning, exactly as `cot` does.

## Module layout (extends `cftc_screener` in place)

```
cftc_screener/
  __init__.py
  catalog.py        # legacy CATALOG (existing) + per-family catalogs +
                    #   FAMILIES registry; select_ids() reused unchanged
  fetch.py          # +family param → (dataset_id, field_map); backoff/token reused
  db.py             # +cot_disagg / cot_tff [/ cot_supp] tables + family views
  run.py            # +--family flag; routes family → dataset/catalog/table/views
```

No new dispatcher entry — `registry.py` still maps `"cftc": cftc_main`. Nothing
in `.env.example` changes (the token var already exists).

### 1. Catalog (`catalog.py`)

Reuse the frozen `Market` dataclass and `select_ids(all, only, exclude, add)`
verbatim. Add **per-family catalogs** and a small registry:

```python
DISAGG_CATALOG: list[Market] = [ ... ]   # physical commodities: ags/energy/metals/softs
TFF_CATALOG:    list[Market] = [ ... ]   # financials: equity_index/rates/fx (+ VIX)
SUPP_CATALOG:   list[Market] = [ ... ]   # 13 ag markets (supplemental), 🟡 confirm

@dataclass(frozen=True)
class Family:
    name: str            # legacy | disaggregated | tff | supplemental
    dataset_id: str      # Socrata resource id
    catalog: list[Market]
    fact_table: str      # cot | cot_disagg | cot_tff | cot_supp
    field_map: list      # (db_column, socrata_field) pairs for this family

FAMILIES = {f.name: f for f in (LEGACY, DISAGG, TFF, SUPPLEMENTAL)}
```

Family codes overlap the legacy catalog (same contracts, different report) — e.g.
Gold `088691` appears in both Legacy and Disaggregated; E-mini S&P `13874A` in
both Legacy and TFF. Codes reused from the verified legacy catalog carry over;
any family-only code is verified live and dropped if it returns no rows.

### 2. Fetch (`fetch.py`)

The one structural change: today `API_URL` and `_INT_FIELDS`/`_FLOAT_FIELDS` are
module constants pinned to the legacy dataset. Parametrize them by family:

- `_build_url(code, dataset_id, since=None, start=None, limit=_LIMIT)` — same
  `$where`/`$order`/`$limit` clause, only the resource id varies. The strict
  `since` primitive and the inclusive `start` floor stay (still unit-tested).
- `parse_rows(records, field_map)` — same coercion (`_num`, `report_date[:10]`,
  code/date guards), driven by the family's `(db_column, socrata_field)` map
  instead of the hardcoded legacy lists.
- `fetch_market_rows(code, dataset_id, field_map, app_token=None, since=None,
  start=None, get=_http_get, opener=None)` — unchanged flow, extra params
  threaded through.
- **Unchanged and reused:** `_RETRY_STATUS = {429,500,502,503,504}`, bounded
  backoff, `X-App-Token` opener (`_make_opener`), UA
  `agentic-trading-bot ninadk.dev@gmail.com`.

### 3. Schema (`db.py`)

**Chosen: one fact table per family** (`cot_disagg`, `cot_tff`, later `cot_supp`),
each mirroring the existing `cot` table's shape with that family's native trader
columns as first-class fields. Rationale over a single family-tagged super-table:
the three families have **disjoint** trader categories, so a shared table would
be a wide sparse union with mostly-`NULL` columns and a `family` discriminator on
every query; per-family tables keep each report's columns meaningful, indexes
tight, and views readable — and `cot` (legacy) needs no migration. The cost (a
little repeated DDL) is exactly the kind the field-map already centralizes.

Every fact table keeps `PRIMARY KEY (code, report_date)`,
`REFERENCES markets(code)`, and `CREATE INDEX ... ON <t>(report_date)`.

```sql
-- Disaggregated: producer/merchant + swap dealers (hedgers); managed money +
-- other reportables (speculators); nonreportable (small). Each reportable block
-- carries long/short and — except producer/merchant — spreading.
CREATE TABLE IF NOT EXISTS cot_disagg (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,          -- YYYY-MM-DD
    open_interest INTEGER,
    prod_merc_long INTEGER, prod_merc_short INTEGER,             -- producer/merchant/processor/user
    swap_long INTEGER, swap_short INTEGER, swap_spread INTEGER,  -- swap dealers
    mm_long INTEGER, mm_short INTEGER, mm_spread INTEGER,        -- managed money (the key spec gauge)
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    -- WoW changes, %OI, trader counts, top-4/8 net concentration (same fields as cot)
    chg_oi INTEGER, chg_mm_long INTEGER, chg_mm_short INTEGER, chg_swap_long INTEGER, chg_swap_short INTEGER,
    pct_oi_mm_long REAL, pct_oi_mm_short REAL, pct_oi_swap_long REAL, pct_oi_swap_short REAL,
    traders_total INTEGER, traders_mm_long INTEGER, traders_mm_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL, conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);

-- TFF: dealer/intermediary (sell-side); asset manager/institutional; leveraged
-- funds (the key spec gauge); other reportables; nonreportable. All four
-- reportable blocks carry long/short/spreading.
CREATE TABLE IF NOT EXISTS cot_tff (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    dealer_long INTEGER, dealer_short INTEGER, dealer_spread INTEGER,
    asset_mgr_long INTEGER, asset_mgr_short INTEGER, asset_mgr_spread INTEGER,
    lev_long INTEGER, lev_short INTEGER, lev_spread INTEGER,      -- leveraged funds
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    chg_oi INTEGER, chg_lev_long INTEGER, chg_lev_short INTEGER, chg_asset_mgr_long INTEGER, chg_asset_mgr_short INTEGER,
    pct_oi_lev_long REAL, pct_oi_lev_short REAL, pct_oi_asset_mgr_long REAL, pct_oi_asset_mgr_short REAL,
    traders_total INTEGER, traders_lev_long INTEGER, traders_lev_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL, conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
-- cot_supp (Supplemental / Commodity Index Traders) added later, same shape,
-- 🟡 columns confirmed live. The legacy `cot`, `markets`, and `snapshots`
-- tables are UNCHANGED.
```

Writers reuse the legacy shapes, parametrized by table + column list:
- `write_family(conn, family, code, rows) -> int` — the `write_cot` upsert
  generalized over `(fact_table, family_cols)`; dedupe within batch by
  `report_date` (last wins); revised weeks overwrite in place.
- `max_report_date(conn, family, code)` — `MAX(report_date)` over the family's
  table (drives the lookback floor).
- `upsert_markets`, `write_snapshot`, `prune` — **unchanged**. `prune` stays the
  FRED-style single-table delete of `snapshots` only; it must **not** cascade
  into any `cot*` fact table (positioning history is the store).

### 4. Views (per-family, reusing the legacy shapes)

Each family gets its own view set computing net = long − short and the COT-Index
over **that family's key speculator net** — Managed-Money for Disaggregated,
Leveraged-Funds for TFF. The SQL is the legacy `v_net` → `v_cot_index` →
`v_positioning` → `v_extremes` chain with the speculator column swapped:

```sql
-- Disaggregated net primitives (managed money is the speculator of record)
CREATE VIEW IF NOT EXISTS v_disagg_net AS
SELECT code, report_date, open_interest,
       mm_long - mm_short           AS net_mm,        -- managed money
       swap_long - swap_short       AS net_swap,      -- swap dealers
       prod_merc_long - prod_merc_short AS net_prod_merc,
       other_rept_long - other_rept_short AS net_other
FROM cot_disagg;

-- COT-Index of managed-money net over its trailing 156-week range (legacy math)
CREATE VIEW IF NOT EXISTS v_disagg_cot_index AS ...  -- MIN/MAX OVER 155 PRECEDING

-- Managed-money positioning at an extreme (the Disaggregated watchlist)
CREATE VIEW IF NOT EXISTS v_managed_money_extremes AS
SELECT * FROM v_disagg_positioning WHERE cot_index >= 90 OR cot_index <= 10;

-- TFF: leveraged-funds positioning board (net, COT-Index, %OI, WoW)
CREATE VIEW IF NOT EXISTS v_tff_net AS
SELECT code, report_date, open_interest,
       lev_long - lev_short         AS net_lev,        -- leveraged funds
       asset_mgr_long - asset_mgr_short AS net_asset_mgr,
       dealer_long - dealer_short   AS net_dealer
FROM cot_tff;
CREATE VIEW IF NOT EXISTS v_leveraged_funds_positioning AS ...  -- v_latest ⋈ COT-index ⋈ %OI/chg
```

The generic legacy views (`v_net`, `v_cot_index`, `v_positioning`, `v_extremes`)
stay untouched and continue to serve the legacy family; the two family view sets
above are additive.

### 5. CLI & orchestration (`run.py`)

Add `family="legacy"` to `run(...)` and a `--family` flag to `main`. The run body
is unchanged except that it resolves the family once and threads it through:

```python
fam = catalog.FAMILIES[family]           # dataset_id, catalog, fact_table, field_map
codes = catalog.select_ids([m.code for m in fam.catalog], only, exclude, add=add)
# per code: floor = _fetch_floor(conn, fam.fact_table, code, start, full)
#           rows = fetch_rows(code, fam.dataset_id, fam.field_map, app_token=..., start=floor)
#           db.upsert_markets(...); db.write_family(conn, fam, code, rows)
```

The 10-week `_LOOKBACK_WEEKS` lookback, `--full`, skip-and-continue (log only
`type(e).__name__`, never `str(e)`/`e.url`), empty-snapshot-on-total-failure, and
`prune` all carry over unchanged.

CLI (`python main.py cftc`):
```
--family {legacy,disaggregated,tff,supplemental}   default: legacy (back-compatible)
--db cftc.db
--only / --exclude / --add   contract codes (resolved against the family's catalog)
--start YYYY-MM-DD           floor for the first fetch (default: family's full history)
--full                       re-pull, ignoring the incremental lookback
--keep-days N                prune snapshot provenance only
```

Default `--db cftc.db` holds all families side by side (separate fact tables, one
`markets` dimension). Operators who prefer isolation can pass `--db
cftc_tff.db`; nothing forces it.

## Defaults (approved)

- **Family:** `legacy` — preserves today's behavior exactly. Disaggregated and
  TFF are opt-in.
- **History:** each family's full span on first run (Disaggregated ~2009, TFF
  ~2010/2006-backcast), floored by `--start`. Incremental re-runs re-fetch the
  trailing 10 weeks (`_LOOKBACK_WEEKS`) so revisions are re-absorbed.
- **Universe:** Disaggregated → the physical-commodity slice (ags, energy,
  metals, softs); TFF → the financial slice (equity_index, rates, fx, VIX). Each
  family's catalog is scoped to the markets that family actually reports.
- **COT-Index extremes:** the legacy 90/10 thresholds, per family, over the
  156-week window.

## Testing (mirror `test_cftc_*`, add a family axis)

- `test_cftc_catalog.py` — extend: each family's catalog is non-empty; `FAMILIES`
  resolves all four names; `select_ids` behavior unchanged (already covered).
- `test_cftc_fetch.py` — `_build_url` targets the right dataset id per family;
  `parse_rows` maps Disaggregated and TFF field maps (managed-money / leveraged-
  funds columns coerced, absent → `None`, date truncated); token header attached
  when present; backoff on 429/5xx — via an injected fake opener, **network never
  hit**.
- `test_cftc_db_schema.py` — `cot_disagg`, `cot_tff`, and the two family view
  sets create idempotently; legacy `cot`/views still present.
- `test_cftc_db_write.py` — `write_family` upserts a revised Disaggregated week in
  place (no duplicate dates); managed-money net survives round-trip; `prune` still
  deletes snapshots only and leaves every `cot*` table intact.
- `test_cftc_db_views.py` — COT-Index math per family: seed a synthetic market
  whose managed-money (Disaggregated) / leveraged-funds (TFF) net walks a known
  range; assert the family `v_*_cot_index` = 100 at max, 0 at min, ~50 mid-range;
  `v_managed_money_extremes` / `v_leveraged_funds_positioning` surface the seeded
  extreme.
- `test_cftc_run.py` — `--family disaggregated` writes to `cot_disagg` with the
  right dataset id passed to the injected fetch; `--family` default stays
  `legacy`; incremental lookback floor = `max_stored − 10 weeks` per family;
  skip-and-continue on a failing market; `now_iso` pinned; secret-hygiene
  assertion that a raising market logs the exception **class** to stderr, never
  its message.
- `test_registry.py` — unchanged (still one `"cftc"` entry); optionally assert
  `--family` reaches `run` via `main`.

## Non-goals (YAGNI)

- **Do not re-pull Legacy** — it is shipped and complete (1986→now); this is
  purely additive.
- **Combined futures + options** variants of Disaggregated/TFF — separate dataset
  ids, optional later (legacy is futures-only; keep families consistent for now).
- **Supplemental (`cot_supp`)** — scaffolded in the `FAMILIES` registry but its
  dataset id and columns are 🟡; implement once confirmed live. It is
  combined-F&O-only and covers just 13 ag markets, so it is the lowest-priority
  family.
- No cross-family joins or blended signals in SQL — consumers correlate
  Managed-Money (Disaggregated) against Non-Commercial (Legacy) in the bot, not
  in a view.
- No price data / backtesting — this screener only *stores positioning*.

## Environment

**No new variables.** The optional Socrata token already documented for the
legacy screener covers all families:
```
CFTC_APP_TOKEN= # optional Socrata app token (lifts rate limits; not required)
```
