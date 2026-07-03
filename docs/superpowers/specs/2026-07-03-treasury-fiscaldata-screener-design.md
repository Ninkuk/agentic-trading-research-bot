# U.S. Treasury Fiscal Data Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [U.S. Treasury Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/)
(docs) — requests go to
`https://api.fiscaldata.treasury.gov/services/api/fiscal_service/{dataset}`,
returning JSON (`?format=json`, the default), CSV, or XML. **No API key.** Plus
the official [Daily Treasury Par Yield Curve](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)
XML feed for the canonical curve. One-line: federal cash flows (TGA), total
public debt, average coupon rates, and the Treasury-auction forward calendar +
results — the fiscal/liquidity plumbing FRED does not carry.
**Confidence:** 🟡 endpoints located but not adversarially verified — confirm
exact dataset paths/fields live at implementation time.

## Goal

Pull a curated set of **U.S. Treasury fiscal + debt-market datasets** into SQLite
so the trading bot has a **liquidity & supply reader** — the Treasury General
Account (TGA) cash balance, total public debt, the average interest cost of the
debt, the announced-auction forward calendar, and realized auction demand
(bid-to-cover, high yield) — plus the official par yield curve for curve-shape /
2s10s signals. The headline signal is **system liquidity**: TGA swings drain or
add bank reserves, and the auction calendar is the forward supply schedule.

This is the **next** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`, `ftd`, `short_volume`, `options`, …). It reuses the proven
`screener_common` machinery and the FRED/CFTC module layout, and takes the same
**time-series/panel data shape** as `fred`/`cftc`.

## Data shape: this is a *time-series / panel* screener (like FRED/CFTC)

- The early screeners (`stocks`, `reddit`, `edgar`) are **cross-sectional**: a
  universe of entities × metrics captured at one moment, snapshot-scoped.
- `fred` is **time-series** (a few series × dated observations, upserted by
  `(series_id, date)`); `cftc` is a **panel** (many markets × weekly dates ×
  metrics, upserted by `(code, report_date)`).
- **Treasury is the same family**: each dataset is `record_date` (± a security /
  account dimension) × fiscal metrics, where the analytical value is the
  *history* — you cannot tell whether a TGA balance of `$750B` is a drain or a
  refill, or whether a `2.6×` bid-to-cover is weak, from one number. So every
  fact table is keyed by its natural `(…, record_date)` key and **upserted**, not
  snapshot-scoped. Fiscal agencies also *restate* recent rows (revised DTS
  figures, re-announced auctions), so a re-run must overwrite in place and never
  duplicate a date. `snapshots` records fetch-run provenance; the fiscal history
  persists across pruning.

## Data-source notes (🟡 confirm live at implementation time)

The Fiscal Data API is a well-documented, key-free JSON:API service. Verified
from docs; exact slugs/fields **confirmed live at implementation time** (like the
FRED and CFTC catalogs — any dataset that 404s or renames a field is fixed then,
not left dead).

1. **Base + shape.** `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/`
   + a dataset path. Responses are JSON:API-style:
   `{ "data": [ {record…}, … ], "meta": { "count", "total-count",
   "total-pages", "labels", "dataTypes" }, "links": { "self", "first", "prev",
   "next", "last" } }`. Pagination is `page[number]` / `page[size]` (default
   size 100, max 10000) — iterate until `links.next` is null (or
   `meta.total-pages`). 🟡 confirm max page size + null-`next` sentinel live.
2. **Query params** (all optional, no auth):
   - `fields=` — column projection (pull only the curated columns).
   - `filter=record_date:gte:YYYY-MM-DD` — incremental floor (also `lte`, `eq`,
     `in:(…)`).
   - `sort=-record_date` — newest first (or `record_date` ascending).
   - `page[size]=` / `page[number]=` — pagination.
   - `format=json` — default; we never request CSV/XML from this host.
3. **Datasets to ingest** (each slug 🟡 confirm live):
   - **Daily Treasury Statement — operating cash balance (TGA):**
     `v1/accounting/dts/operating_cash_balance`. **Daily.** One row per
     `record_date` × `account_type` (the TGA closing balance is the row we
     center on). *Signal:* TGA level swings = system liquidity (drains/adds bank
     reserves). 🟡 confirm the exact `account_type` label for the TGA closing
     balance and the balance field names (`open_today_bal` / `close_today_bal`).
   - *(optional secondary)* **DTS deposits/withdrawals:**
     `v1/accounting/dts/deposits_withdrawals_operating_cash` — daily flow detail
     into/out of the TGA. Off by default (level suffices for v1); available via
     `--add`. 🟡 confirm slug.
   - **Debt to the Penny:** `v2/accounting/od/debt_to_penny`. **Daily** total
     public debt outstanding (+ held-by-public / intragovernmental split).
     🟡 confirm slug + field `tot_pub_debt_out_amt`.
   - **Average Interest Rates on Treasury securities:**
     `v2/accounting/od/avg_interest_rates`. **Monthly**, per security type /
     description. *Signal:* the rising average coupon = the debt-service cost
     ramp. 🟡 confirm slug + `avg_interest_rate_amt` field.
   - **Upcoming (announced) Auctions:** `v1/accounting/od/upcoming_auctions`.
     Announcement / auction / issue dates + security type/term for scheduled
     auctions. **This doubles as the Treasury-auction forward-calendar signal** —
     cross-referenced by the event-monitor framework spec
     (`2026-07-03-event-monitor-framework-design.md`); the auction calendar
     lives **here** (exposed as `v_upcoming_auctions`) rather than in a separate
     monitor. 🟡 confirm slug + date field names; CUSIP may be blank pre-issue.
   - **Auction Results (query):** `v1/accounting/od/auctions_query` — realized
     demand: high yield, **bid-to-cover ratio**, offering / accepted amounts,
     per CUSIP. 🟡 confirm slug + `bid_to_cover_ratio` field.
4. **Official yield curve.** The canonical **Daily Treasury Par Yield Curve
   Rates** is served as an **XML feed**
   (`https://home.treasury.gov/treasury-daily-interest-rate-xml-feed`, e.g.
   `.../pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=YYYY`) —
   one entry per business day with a rate per tenor (1Mo…30Yr). *Signal:* curve
   level/shape, **2s10s inversion**. 🟡 confirm the exact XML query path and
   element names; if FiscalData exposes the same par curve under an
   `accounting/od/...` slug, prefer that JSON path and drop the XML branch. This
   is the one dataset needing an `xml.etree.ElementTree` parse branch.
5. **No credentials, no throttle gymnastics.** Fiscal Data has generous public
   limits; we still route through the shared bounded-backoff client (retry
   `429`/`5xx`) and send the descriptive UA. No key/token handling at all.

## Guiding principles

- **Store raw, derive in views (ELT).** Records are the source of truth; every
  liquidity/supply signal is a SQL view that can be rewritten without
  re-fetching.
- **Reuse proven patterns.** `connect` (WAL) from `screener_common`; the
  `http_client.make_opener` + `http_client.http_get` bounded-backoff scaffolding
  (`_RETRY_STATUS = {429, 500, 502, 503, 504}`); the FRED/CFTC package triad +
  dependency-injected `run()` + TDD.
- **Per-dataset tables over one long table.** Each Treasury dataset has a
  different natural width (cash balances vs. debt vs. per-security rates vs.
  auction rows). Separate tables keyed on their own date key are far clearer than
  one `(dataset, date, key, value)` EAV blob — and the views read cleanly.
- **Dependency-free.** `urllib` + `json` + `xml.etree` (stdlib only), matching
  all existing screeners.
- **Secret hygiene by reflex.** These endpoints carry no secret, but the house
  rule still holds: per-item failures log **only `type(e).__name__`**, never
  `str(e)`/`e.url`. Writers end with `conn.commit()`.

## Module structure

New self-contained package `treasury_screener/`, mirroring `fred_screener`
module-for-module:

```
treasury_screener/
    __init__.py
    catalog.py  # curated Dataset list (Dataset dataclass) + select_ids
    fetch.py    # FiscalData paged JSON client + XML yield-curve branch; per-dataset parsers
    db.py       # per-dataset schema + ELT views; upserts; write_snapshot; prune
    run.py      # resolve datasets -> fetch each -> upsert -> snapshot; argparse main
```

Registered in `registry.py`: `"treasury": treasury_main` (alongside `stocks`,
`reddit`, `edgar`, `fred`, `cftc`, `ftd`, `short_volume`, `options`). **This spec
does not modify `registry.py`; registration is an implementation step.**

## Catalog (`treasury_screener/catalog.py`)

A hardcoded, curated catalog of **datasets** (not series) is the default —
mirrors `fred_screener.catalog` / `cftc_screener.catalog` and their `select_ids`.

```python
@dataclass(frozen=True)
class Dataset:
    dataset_id: str   # local key, e.g. "dts_cash"
    endpoint: str     # FiscalData path or "xml:yield_curve" sentinel
    table: str        # target table
    date_field: str   # API record-date field, e.g. "record_date"
    frequency: str    # daily | monthly | event
```

`CATALOG: list[Dataset]` — the default set:

- `dts_cash`      → `v1/accounting/dts/operating_cash_balance`   (daily)
- `debt_penny`    → `v2/accounting/od/debt_to_penny`             (daily)
- `avg_rates`     → `v2/accounting/od/avg_interest_rates`        (monthly)
- `upcoming_auctions` → `v1/accounting/od/upcoming_auctions`     (event)
- `auction_results`   → `v1/accounting/od/auctions_query`        (event)
- `yield_curve`   → `xml:yield_curve` (Treasury XML feed)        (daily)

`select_ids(all_ids, only, exclude, add)` — identical logic to
`fred_screener.catalog.select_ids` (ordered, de-duplicated, blank/exclude-aware),
resolving over **dataset ids**. `--add ID` pulls an ad-hoc dataset id not in the
catalog (e.g. `deposits_withdrawals_operating_cash`); its endpoint/parser must
already be known to `fetch`, else it is skipped with a warning.

> Final catalog membership + every slug/field is confirmed live at
> implementation time by probing each dataset once; a typo'd or renamed slug is
> fixed then, not shipped dead. Any dataset that 404s is dropped with a note.

## Fetch behaviour (`treasury_screener/fetch.py`)

Pure parsers separated from HTTP so they unit-test against fixtures without
network. Reuses the shared bounded-backoff client verbatim.

```python
API_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_urlopen = http_client.make_opener(_UA)
```

- `_build_url(endpoint, *, fields=None, filter=None, sort=None, page_size, page_number) -> str`
  — assemble a FiscalData URL, URL-encoding `fields`/`filter`/`sort`/`page[...]`.
- `fetch_dataset(endpoint, *, fields=None, since=None, get=_http_get) -> list[dict]`
  — page through the JSON:API `data` arrays (append `filter=record_date:gte:since`
  when `since` is set), following pagination until `links.next` is null or
  `meta.total-pages` is reached. Returns the raw records.
- Per-dataset pure parsers map raw records → the curated column dicts, coercing
  numeric strings to `float`/`int` and absent/blank cells to `None`, and
  normalizing dates to `YYYY-MM-DD`:
  `parse_dts_cash`, `parse_debt_penny`, `parse_avg_rates`,
  `parse_upcoming_auctions`, `parse_auction_results`.
- `fetch_yield_curve(year, get=_http_get) -> list[dict]` — the XML branch: GET
  the Treasury feed, parse with `xml.etree.ElementTree`, return one dict per
  business day mapping tenor → rate. No JSON:API pagination.
- **No API key / token** — nothing sensitive in any URL. Retries `429`/`5xx` +
  transient network errors via the bounded backoff; other HTTP errors raise.

## Data model (`treasury_screener/db.py`)

Per-dataset tables, each keyed on its own natural date key. All
`CREATE TABLE/VIEW IF NOT EXISTS`.

```sql
CREATE TABLE IF NOT EXISTS snapshots (   -- one row per fetch run (provenance)
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,         -- ISO-8601 UTC
    dataset_count INTEGER NOT NULL,      -- datasets successfully fetched
    row_count     INTEGER NOT NULL       -- total rows upserted this run
);

-- Daily Treasury Statement — operating cash balance (TGA level)
CREATE TABLE IF NOT EXISTS dts_cash (
    record_date   TEXT NOT NULL,         -- YYYY-MM-DD
    account_type  TEXT NOT NULL,         -- e.g. "Treasury General Account (TGA)"
    open_balance  REAL,                  -- open_today_bal
    close_balance REAL,                  -- close_today_bal
    PRIMARY KEY (record_date, account_type)
);

-- Debt to the Penny (total public debt outstanding)
CREATE TABLE IF NOT EXISTS debt_penny (
    record_date      TEXT PRIMARY KEY,   -- YYYY-MM-DD
    tot_pub_debt_out REAL,               -- total public debt outstanding
    debt_held_public REAL,
    intragov_hold    REAL
);

-- Average interest rates on Treasury securities (monthly, per security)
CREATE TABLE IF NOT EXISTS avg_rates (
    record_date        TEXT NOT NULL,    -- month-end YYYY-MM-DD
    security_type_desc TEXT NOT NULL,    -- e.g. "Marketable"
    security_desc      TEXT NOT NULL,    -- e.g. "Treasury Notes"
    avg_interest_rate  REAL,             -- percent
    PRIMARY KEY (record_date, security_type_desc, security_desc)
);

-- Daily Treasury Par Yield Curve (from the XML feed), wide by tenor
CREATE TABLE IF NOT EXISTS yield_curve (
    record_date TEXT PRIMARY KEY,        -- YYYY-MM-DD
    mo1 REAL, mo2 REAL, mo3 REAL, mo4 REAL, mo6 REAL,
    yr1 REAL, yr2 REAL, yr3 REAL, yr5 REAL, yr7 REAL,
    yr10 REAL, yr20 REAL, yr30 REAL
);

-- Upcoming (announced) auctions — the forward calendar
CREATE TABLE IF NOT EXISTS upcoming_auctions (
    cusip             TEXT,              -- may be blank pre-assignment
    security_type     TEXT NOT NULL,     -- Bill | Note | Bond | TIPS | FRN | CMB
    security_term     TEXT NOT NULL,     -- e.g. "10-Year"
    announcement_date TEXT,
    auction_date      TEXT NOT NULL,     -- YYYY-MM-DD
    issue_date        TEXT,
    PRIMARY KEY (auction_date, security_type, security_term)
);

-- Auction results — realized demand
CREATE TABLE IF NOT EXISTS auction_results (
    cusip              TEXT NOT NULL,
    auction_date       TEXT NOT NULL,    -- YYYY-MM-DD
    security_type      TEXT,
    security_term      TEXT,
    high_yield         REAL,
    bid_to_cover_ratio REAL,
    offering_amt       REAL,
    total_accepted     REAL,
    PRIMARY KEY (cusip, auction_date)
);
```

- Every fact table is **upserted** on its natural key
  (`INSERT … ON CONFLICT(…) DO UPDATE`): revised DTS/debt figures and
  re-announced auctions overwrite in place; dates/keys are never duplicated.
  Batches dedupe by key (last wins) — the FRED `write_observations` shape.
- `snapshots` records run metadata only; **no** fact table carries a
  `snapshot_id` (the same date's row is shared across runs).
- 🟡 the exact source-field names behind each column are confirmed live and
  mapped in the parsers at implementation time.

Writers: `ensure_schema(conn)` (idempotent), one `write_<table>(conn, rows)
-> int` per dataset (upsert, dedupe, `return len`), and
`write_snapshot(conn, captured_at, dataset_count, row_count) -> id`.

### Derived-signal views (the "rich" liquidity/supply reader)

All `CREATE VIEW IF NOT EXISTS`, created with the schema; LEFT JOINs so a partial
`--only` run yields NULLs instead of erroring on a missing dataset.

- **`v_tga_trend`** — TGA closing balance per `record_date` (from `dts_cash`
  filtered to the TGA `account_type`) with its week-over-week change
  (`LAG` ~5 business days), i.e. the reserve drain/add signal.
- **`v_debt_trend`** — `tot_pub_debt_out` per date + change vs. the prior stored
  date (and ~1-month/1-year deltas).
- **`v_yield_curve_latest`** — the most recent `yield_curve` row with the
  **2s10s spread** (`yr10 - yr2`) and an **`inverted` flag** (`yr10 - yr2 < 0`),
  plus 3m10y for good measure.
- **`v_upcoming_auctions`** — the forward calendar: announced auctions with
  `auction_date >= date('now')`, ordered by `auction_date`
  (announcement/auction/issue dates + type/term). The event-monitor framework
  reads this view rather than re-deriving the calendar.
- **`v_auction_demand`** — bid-to-cover trend from `auction_results`, latest per
  `security_term` + the recent average, so weakening demand at a given tenor is
  legible.

## Orchestration (`treasury_screener/run.py`)

```python
run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
    fetch_dataset=fetch.fetch_dataset, fetch_yield_curve=fetch.fetch_yield_curve,
    now_iso=None) -> (snapshot_id, dataset_count, row_count)
```

1. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
2. Resolve datasets: `select_ids([d.dataset_id for d in CATALOG], only, exclude,
   add)`.
3. `conn = db.connect(db_path); db.ensure_schema(conn)`.
4. For each selected dataset (**skip-and-continue** on failure):
   - Compute `since` = the max stored `record_date` for that table (full history
     on first run; only new dates thereafter; `--start` floors the first run).
     Like CFTC, incremental daily datasets re-fetch a small trailing window with
     an inclusive floor so restated recent rows are re-absorbed by the upsert.
   - Dispatch to the right fetch + parser + writer (yield-curve takes the XML
     branch).
   - On any exception: `conn.rollback()`, print
     `f"warning: skipping {dataset_id}: {type(e).__name__}"` to stderr (**no
     URL, no `str(e)`**), continue; track failures.
5. `write_snapshot(now_iso, dataset_count=successes, row_count=Σ rows)`.
6. If **zero** datasets succeeded: still write the `(0, 0)` snapshot and warn
   loudly; do not raise (mirrors the other screeners).
7. If `keep_days is not None`: `db.prune(conn, keep_days, now_iso)`.
8. Return `(snapshot_id, dataset_count, row_count)`.

Fetchers + `now_iso` injected for deterministic, network-free tests.

CLI (`main` in `run.py`, invoked via the dispatcher — `python main.py treasury`):

```
--db treasury.db
--only IDS         comma-separated dataset ids   (default: catalog)
--exclude IDS      comma-separated dataset ids to skip
--add ID           extra dataset id not in the catalog (repeatable)
--start YYYY-MM-DD  record_date floor for the first fetch (default: full history)
--keep-days N       prune snapshot provenance older than N days (default: None)
```

## Defaults & retention

- **Default selection:** the full catalog (`dts_cash`, `debt_penny`, `avg_rates`,
  `upcoming_auctions`, `auction_results`, `yield_curve`).
- **Default `--start`:** none → full available history per dataset.
- **Retention (FRED-style single-table prune).** The fact tables are the
  historical store and are **not** snapshot-scoped, so the shared cascade
  `prune` in `screener_common` (which deletes a `child_table` off `snapshot_id`)
  **must not** touch them. With `--keep-days N`, `treasury_screener/db.py`
  implements its own `prune` as a plain single-table delete of stale
  **`snapshots`** rows only (`DELETE FROM snapshots WHERE captured_at < cutoff`),
  exactly as `fred_screener.db.prune` does. Default (no `--keep-days`) keeps
  everything. *(This deviation from the cascade is called out in `db.py` so a
  future reader doesn't wire the fact tables into a cascade by reflex.)*

## Testing (TDD, mirrors existing `tests/`)

- `test_treasury_fetch.py` — `_build_url` (encodes `fields`/`filter`/`sort`/
  `page[...]`); pagination follows `links.next` and stops on null; each
  `parse_*` (numeric coercion, blank → None, date normalization) against JSON
  fixtures; `fetch_yield_curve` against an XML fixture; backoff retry on
  `429`/`503` with an injected fake opener + `sleep`.
- `test_treasury_catalog.py` — `select_ids` (only/exclude/add, strip/dedupe/
  blank-drop); catalog integrity (unique ids, known endpoints/frequencies).
- `test_treasury_db_schema.py` — `ensure_schema` idempotent; all tables + views
  exist; re-run is a no-op.
- `test_treasury_db_write.py` — each `write_*` upsert keyed correctly: re-write
  of the same key **updates in place** (no duplicate rows), revised value
  overwrites; blank → NULL persisted.
- `test_treasury_db_views.py` — view math on seeded rows: `v_tga_trend` WoW
  change; `v_yield_curve_latest` 2s10s spread + `inverted` flag sign;
  `v_upcoming_auctions` filters to future `auction_date` ordered; `v_debt_trend`
  delta; `v_auction_demand` latest-per-term.
- `test_treasury_run.py` — `run()` with injected fetchers: happy-path counts;
  **skip-and-continue** (one dataset raises → others still stored, failure
  warned, **secret-hygiene assertion**: stderr contains the class name, never a
  URL/`str(e)`); all-fail → `(0, 0)` snapshot + loud warning;
  `--only`/`--exclude`/`--add`; second-run incremental upsert (history grows,
  restated row overwrites); `keep_days` prunes snapshots but **not** fact tables.
  `now_iso` pinned for determinism.
- `test_registry.py` — extend: dispatcher routes `treasury`; `--list` includes
  it; existing paths unchanged.

Live smoke (manual, like the other screeners): pull the catalog into a temp DB;
assert non-empty `dts_cash`, `debt_penny`, `yield_curve`, a populated
`v_yield_curve_latest` with a sane 2s10s spread, and a `v_upcoming_auctions` with
future-dated rows.

## Non-goals (YAGNI)

- **Don't duplicate FRED's Treasury yields.** FRED already serves `DGS2`/`DGS10`/
  `T10Y2Y` etc. (in the `fred` catalog); this screener's value is the data FRED
  **lacks or lags** — DTS/TGA cash flows, the auction calendar + results, and
  debt-to-the-penny. We ingest the par yield curve here only for a self-contained
  2s10s/inversion view and same-day freshness, not to re-carry FRED's series.
- **Full DTS detail tables** (every DTS table — public-debt transactions,
  income-tax refunds, etc.) — only the operating-cash-balance level (+ optional
  deposits/withdrawals via `--add`) in v1.
- **Auction-participation microstructure** (indirect/direct/primary-dealer award
  splits) beyond bid-to-cover / high-yield — a later enrichment of
  `auction_results`.
- **A separate auction event-monitor** — the calendar lives in
  `v_upcoming_auctions` here; the event-monitor framework
  (`2026-07-03-event-monitor-framework-design.md`) consumes this view.
- **Shared `Screener` base class** — shapes still differ; only `connect`/backoff
  are shared, as decided in the EDGAR/FRED specs.

## Environment

**No credentials required.** The Fiscal Data API and the Treasury XML feed are
public and key-free — **do not** add a variable to `.env.example`. The only
network config is the descriptive User-Agent baked into the fetcher
(`agentic-trading-bot ninadk.dev@gmail.com`).
