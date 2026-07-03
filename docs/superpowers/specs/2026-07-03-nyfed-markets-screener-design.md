# NY Fed Markets Data Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [Federal Reserve Bank of New York Markets Data API](https://markets.newyorkfed.org/static/docs/markets-api.html)
(docs) — requests go to `https://markets.newyorkfed.org/api/{domain}/...json`,
returning JSON. **No API key.** One-line: the money-market plumbing the Desk
publishes — reference rates (SOFR/EFFR/…), repo & reverse-repo operations, SOMA
balance-sheet holdings, and primary-dealer positioning — the funding-stress /
liquidity signals FRED carries only partially and later.
**Confidence:** 🟡 endpoints located but not adversarially verified — confirm
exact dataset paths/fields live at implementation time.

## Goal

Pull a curated set of **NY Fed Markets datasets** into SQLite so the trading bot
has a **funding & liquidity reader** — the secured/unsecured overnight rates
(SOFR, EFFR, OBFR, BGCR, TGCR), the ON-RRP and repo operation results, and the
System Open Market Account (SOMA) holdings — with enough history to read
money-market stress and the QT/QE balance-sheet pace. The headline signals:
**SOFR level & its spread to IORB** (secured funding stress), **ON-RRP take-up**
(excess-liquidity gauge), and **SOMA week-over-week runoff** (QT pace).

This is the **next** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`, `ftd`, `short_volume`, `options`, …). It reuses the proven
`screener_common` machinery and the FRED/CFTC module layout, and takes the same
**time-series/panel data shape**.

## Data shape: this is a *time-series / panel* screener (like FRED/CFTC)

- The early screeners (`stocks`, `reddit`, `edgar`) are **cross-sectional**
  (entities × metrics at one moment, snapshot-scoped).
- `fred` is **time-series**; `cftc` is a **panel**. **NY Fed is the same
  family**: each domain is a `date` (± a rate-type / operation / security
  dimension) × metrics, where the value is the *history* — one SOFR print or one
  ON-RRP take-up number is meaningless without its trend and its spread. So every
  fact table is keyed by its natural `(series/operation, date)` key and
  **upserted**, not snapshot-scoped. The Desk *restates* recent operation results,
  so a re-run must overwrite in place and never duplicate a date. `snapshots`
  records fetch-run provenance; the money-market history persists across pruning.

## v1 scope: rates + RRP + SOMA first, dealers later

The API spans four domains of unequal payoff and complexity. The recommendation
is to **build the three highest-signal, simplest domains first** and defer the
fourth:

| Domain | v1? | Why |
|---|---|---|
| **Reference rates** (SOFR/EFFR/OBFR/BGCR/TGCR) | ✅ | Highest signal (SOFR + SOFR–IORB spread), flat daily series, trivial shape |
| **Reverse Repo (ON-RRP)** | ✅ | Excess-liquidity gauge; simple per-operation rows |
| **SOMA summary** | ✅ | QT/QE pace from weekly holdings; simple summary rows |
| **Repo operations** | ✅ (thin) | Funding-stress tell; same shape as RRP — folded into the repo-ops table |
| **Primary Dealer statistics** | ❌ later | Rich but wide (many series keys, positions/financing); an additive second phase |

Each sub-endpoint below is marked 🟡 **confirm live at implementation time**.

## Data-source notes (🟡 confirm live at implementation time)

The NY Fed Markets API is a documented, key-free JSON service. Verified from
docs; exact paths/fields **confirmed live at implementation time** (like the FRED
and CFTC catalogs — any path that 404s or renames a field is fixed then).

Base: `https://markets.newyorkfed.org/api`.

1. **Reference rates** (SOFR/EFFR/OBFR/BGCR/TGCR):
   - Latest all-rates: `/rates/all/latest.json`. 🟡 confirm.
   - History: `/rates/all/search.json?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`
     (or the secured/unsecured split under `/rates/secured/...` /
     `/rates/unsecured/...`, and `/rates/{type}/{rateType}/last/{n}.json`).
     🟡 confirm the exact history path + params.
   - Each record carries `effectiveDate`, `type`/`rateType` (e.g. `SOFR`),
     `percentRate`, `volumeInBillions`, and percentile fields. *Signal:* SOFR
     level & **SOFR-vs-IORB spread** = secured money-market funding stress. SOFR
     context: <https://www.newyorkfed.org/markets/reference-rates/sofr>.
     (IORB itself is not on this API — it is a Fed administered rate; pull it
     from FRED `IORB` and join, or store a small constants table. 🟡 decide at
     implementation; the spread view degrades to NULL if IORB is absent.)
2. **Reverse Repo & Repo operations:**
   - RRP results/propositions: `/rp/reverserepo/propositions/search.json?
     startDate=&endDate=` (and `/rp/all/latest.json`). 🟡 confirm.
   - Repo results: `/rp/repo/.../search.json?startDate=&endDate=`. 🟡 confirm.
   - Each operation record carries `operationId`, `operationDate`,
     `operationType`, `totalAmtAccepted` (the **award / take-up**),
     `totalAmtSubmitted`, and per-tranche detail. *Signal:* **ON-RRP take-up** =
     excess-liquidity gauge; repo-op usage = funding stress. Both fold into one
     `repo_ops` table distinguished by `operation_type`.
3. **SOMA holdings:**
   - Summary: `/soma/summary.json` — weekly holdings summary (par by security
     type: bills, notes/bonds, TIPS, FRN, MBS, agency, total). 🟡 confirm.
   - As-of dates: `/soma/asofdates/latest.json` (and `.../list.json` for the full
     history of as-of dates). 🟡 confirm.
   - *Signal:* **SOMA week-over-week balance change = QT (runoff) / QE pace.**
4. **Primary Dealer statistics** (deferred to phase 2):
   - `/pd/latest.json`, `/pd/get/all/timeseries.json`, `/pd/list/timeseries.json`.
     🟡 confirm. Dealer positions / financing by series key. *Signal:* dealer
     Treasury inventory / positioning. **Not in v1.**
5. **No credentials, no throttle gymnastics.** Public and key-free; we still
   route through the shared bounded-backoff client (retry `429`/`5xx`) and send
   the descriptive UA. No key/token handling at all.

## Guiding principles

- **Store raw, derive in views (ELT).** Records are the source of truth; every
  funding/liquidity signal is a SQL view rewritable without re-fetching.
- **Reuse proven patterns.** `connect` (WAL) from `screener_common`; the
  `http_client.make_opener` + `http_client.http_get` bounded-backoff scaffolding
  (`_RETRY_STATUS = {429, 500, 502, 503, 504}`); the FRED/CFTC package triad +
  dependency-injected `run()` + TDD.
- **Per-domain tables.** Rates, repo ops, and SOMA holdings have different
  natural widths; separate tables keyed on their own `(…, date)` key read far
  cleaner than one EAV blob.
- **Dependency-free.** `urllib` + `json` (stdlib only), matching all existing
  screeners.
- **Secret hygiene by reflex.** No secret in any URL here, but the house rule
  still holds: per-item failures log **only `type(e).__name__`**, never
  `str(e)`/`e.url`. Writers end with `conn.commit()`.

## Module structure

New self-contained package `nyfed_screener/`, mirroring `fred_screener`
module-for-module:

```
nyfed_screener/
    __init__.py
    catalog.py  # curated Domain list (Domain dataclass) + select_ids
    fetch.py    # NY Fed JSON client (bounded backoff, no key); per-domain parsers
    db.py       # per-domain schema + ELT views; upserts; write_snapshot; prune
    run.py      # resolve domains -> fetch each -> upsert -> snapshot; argparse main
```

Registered in `registry.py`: `"nyfed": nyfed_main` (alongside the others).
**This spec does not modify `registry.py`; registration is an implementation
step.**

## Catalog (`nyfed_screener/catalog.py`)

A hardcoded, curated catalog of **domains** is the default — mirrors
`fred_screener.catalog` / `cftc_screener.catalog` and their `select_ids`.

```python
@dataclass(frozen=True)
class Domain:
    domain_id: str   # "reference_rates" | "rrp" | "repo" | "soma" | "primary_dealer"
    endpoint: str    # NY Fed history path (or a per-domain sentinel)
    table: str       # target table
    date_field: str  # API date field, e.g. "effectiveDate" / "asOfDate"
```

`CATALOG: list[Domain]` — the **v1 default set**:

- `reference_rates` → `/rates/all/search.json`   → `reference_rates`
- `rrp`             → `/rp/reverserepo/propositions/search.json` → `repo_ops`
- `repo`            → `/rp/repo/.../search.json`  → `repo_ops` (same table, `operation_type`)
- `soma`            → `/soma/summary.json`        → `soma_holdings`

`primary_dealer` (→ `primary_dealer_stats`) is defined in the catalog but
**disabled by default** (phase 2); reachable via `--only primary_dealer` /
`--add` once its parser lands.

`select_ids(all_ids, only, exclude, add)` — identical logic to
`fred_screener.catalog.select_ids` (ordered, de-duplicated, blank/exclude-aware),
resolving over **domain ids**.

> Final catalog membership + every path/field is confirmed live at
> implementation time by probing each domain once; a typo'd or renamed path is
> fixed then, not shipped dead. Any domain that 404s is dropped with a note.

## Fetch behaviour (`nyfed_screener/fetch.py`)

Pure parsers separated from HTTP so they unit-test against fixtures without
network. Reuses the shared bounded-backoff client verbatim.

```python
API_BASE = "https://markets.newyorkfed.org/api"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_urlopen = http_client.make_opener(_UA)
```

- `_build_url(endpoint, params) -> str` — assemble a NY Fed URL, URL-encoding
  `startDate`/`endDate` (and any per-domain params).
- `fetch_domain(endpoint, *, start=None, end=None, get=_http_get) -> list[dict]`
  — GET the history endpoint (windowed by `startDate`/`endDate` when `start` is
  set), return the raw records from the domain's JSON envelope (the NY Fed wraps
  results under a domain key, e.g. `refRates`, `repo`, `soma` — 🟡 confirm the
  exact envelope keys live).
- Per-domain pure parsers map raw records → curated column dicts, coercing
  numeric strings to `float`/`int` and absent/blank cells to `None`, normalizing
  dates to `YYYY-MM-DD`: `parse_reference_rates`, `parse_repo_ops`,
  `parse_soma_holdings` (and later `parse_primary_dealer`).
- **No API key / token** — nothing sensitive in any URL. Retries `429`/`5xx` +
  transient network errors via the bounded backoff; other HTTP errors raise.

## Data model (`nyfed_screener/db.py`)

Per-domain tables, each keyed on its own natural `(…, date)` key. All
`CREATE TABLE/VIEW IF NOT EXISTS`.

```sql
CREATE TABLE IF NOT EXISTS snapshots (   -- one row per fetch run (provenance)
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,          -- ISO-8601 UTC
    domain_count INTEGER NOT NULL,       -- domains successfully fetched
    row_count    INTEGER NOT NULL        -- total rows upserted this run
);

-- Reference rates (SOFR/EFFR/OBFR/BGCR/TGCR), one row per (rate_type, date)
CREATE TABLE IF NOT EXISTS reference_rates (
    rate_type       TEXT NOT NULL,       -- SOFR | EFFR | OBFR | BGCR | TGCR
    effective_date  TEXT NOT NULL,       -- YYYY-MM-DD
    percent_rate    REAL,
    volume_bn       REAL,                -- volume in $bn
    pct_1  REAL, pct_25 REAL, pct_75 REAL, pct_99 REAL,  -- rate percentiles
    PRIMARY KEY (rate_type, effective_date)
);

-- Repo + Reverse-Repo operation results, one row per operation
CREATE TABLE IF NOT EXISTS repo_ops (
    operation_id    TEXT PRIMARY KEY,    -- NY Fed operationId
    operation_date  TEXT NOT NULL,       -- YYYY-MM-DD
    operation_type  TEXT NOT NULL,       -- repo | reverse_repo
    total_submitted REAL,                -- $ submitted
    total_accepted  REAL,                -- $ accepted (award / take-up)
    award_rate      REAL
);
CREATE INDEX IF NOT EXISTS ix_repo_ops_date ON repo_ops(operation_date);

-- SOMA holdings summary, one row per (as_of_date, security_type)
CREATE TABLE IF NOT EXISTS soma_holdings (
    as_of_date    TEXT NOT NULL,         -- YYYY-MM-DD (weekly)
    security_type TEXT NOT NULL,         -- bills | notesbonds | tips | frn | mbs | agency | total
    par_value     REAL,                  -- par holdings in $
    PRIMARY KEY (as_of_date, security_type)
);

-- Primary dealer statistics (phase 2), one row per (as_of_date, series_key)
CREATE TABLE IF NOT EXISTS primary_dealer_stats (
    as_of_date  TEXT NOT NULL,
    series_key  TEXT NOT NULL,           -- NY Fed PD series identifier
    value       REAL,
    PRIMARY KEY (as_of_date, series_key)
);
```

- Every fact table is **upserted** on its natural key
  (`INSERT … ON CONFLICT(…) DO UPDATE`): restated operation results / rates
  overwrite in place; keys/dates never duplicated. Batches dedupe by key (last
  wins) — the FRED `write_observations` shape.
- `snapshots` records run metadata only; **no** fact table carries a
  `snapshot_id`.
- 🟡 exact source-field names behind each column are confirmed live and mapped in
  the parsers at implementation time.

Writers: `ensure_schema(conn)` (idempotent), one `write_<table>(conn, rows)
-> int` per domain (upsert, dedupe, `return len`), and
`write_snapshot(conn, captured_at, domain_count, row_count) -> id`.

### Derived-signal views (the "rich" funding/liquidity reader)

All `CREATE VIEW IF NOT EXISTS`, created with the schema; LEFT JOINs so a partial
`--only` run yields NULLs instead of erroring on a missing domain.

- **`v_rrp_trend`** — ON-RRP take-up (`total_accepted` where
  `operation_type = 'reverse_repo'`) per `operation_date` + its day-over-day
  change, i.e. the excess-liquidity gauge trend.
- **`v_sofr_latest`** — the most recent `SOFR` row (rate + volume) and, when an
  IORB value is available, the **SOFR-vs-IORB spread** (`percent_rate - iorb`);
  the spread column is NULL if IORB is absent so the view never errors.
- **`v_soma_runoff`** — SOMA `total` par per `as_of_date` + week-over-week change
  (`LAG` 1 as-of date), i.e. the **QT/QE pace**.
- **`v_dealer_positioning`** — latest primary-dealer position series per
  `series_key` (populated only once phase 2 lands; empty otherwise).

## Orchestration (`nyfed_screener/run.py`)

```python
run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
    fetch_domain=fetch.fetch_domain, now_iso=None)
    -> (snapshot_id, domain_count, row_count)
```

1. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
2. Resolve domains: `select_ids([d.domain_id for d in ENABLED], only, exclude,
   add)` (default = the v1-enabled set; `primary_dealer` only via
   `--only`/`--add`).
3. `conn = db.connect(db_path); db.ensure_schema(conn)`.
4. For each selected domain (**skip-and-continue** on failure):
   - Compute `start` = the max stored date for that table (full history on first
     run; only new dates thereafter; `--start` floors the first run). Like CFTC,
     incremental domains re-fetch a small trailing window with an inclusive floor
     so restated recent operations are re-absorbed by the upsert.
   - Dispatch to the right fetch + parser + writer.
   - On any exception: `conn.rollback()`, print
     `f"warning: skipping {domain_id}: {type(e).__name__}"` to stderr (**no URL,
     no `str(e)`**), continue; track failures.
5. `write_snapshot(now_iso, domain_count=successes, row_count=Σ rows)`.
6. If **zero** domains succeeded: still write the `(0, 0)` snapshot and warn
   loudly; do not raise (mirrors the other screeners).
7. If `keep_days is not None`: `db.prune(conn, keep_days, now_iso)`.
8. Return `(snapshot_id, domain_count, row_count)`.

Fetchers + `now_iso` injected for deterministic, network-free tests.

CLI (`main` in `run.py`, invoked via the dispatcher — `python main.py nyfed`):

```
--db nyfed.db
--only IDS         comma-separated domain ids   (default: v1-enabled set)
--exclude IDS      comma-separated domain ids to skip
--add ID           extra domain id (e.g. primary_dealer) (repeatable)
--start YYYY-MM-DD  date floor for the first fetch (default: full history)
--keep-days N       prune snapshot provenance older than N days (default: None)
```

## Defaults & retention

- **Default selection:** the v1-enabled set (`reference_rates`, `rrp`, `repo`,
  `soma`). `primary_dealer` is opt-in until phase 2.
- **Default `--start`:** none → full available history per domain.
- **Retention (FRED-style single-table prune).** The fact tables are the
  historical store and are **not** snapshot-scoped, so the shared cascade
  `prune` in `screener_common` **must not** touch them. With `--keep-days N`,
  `nyfed_screener/db.py` implements its own `prune` as a plain single-table
  delete of stale **`snapshots`** rows only
  (`DELETE FROM snapshots WHERE captured_at < cutoff`), exactly as
  `fred_screener.db.prune` does. Default (no `--keep-days`) keeps everything.
  *(This deviation from the cascade is called out in `db.py` so a future reader
  doesn't wire the fact tables into a cascade by reflex.)*

## Testing (TDD, mirrors existing `tests/`)

- `test_nyfed_fetch.py` — `_build_url` (encodes `startDate`/`endDate`); each
  `parse_*` (numeric coercion, blank → None, date normalization, envelope-key
  extraction) against JSON fixtures; backoff retry on `429`/`503` with an
  injected fake opener + `sleep`.
- `test_nyfed_catalog.py` — `select_ids` (only/exclude/add, strip/dedupe/
  blank-drop); catalog integrity (unique ids, `primary_dealer` disabled by
  default).
- `test_nyfed_db_schema.py` — `ensure_schema` idempotent; all tables + views
  exist; re-run is a no-op.
- `test_nyfed_db_write.py` — each `write_*` upsert keyed correctly: re-write of
  the same key **updates in place** (no duplicate rows), revised value
  overwrites; blank → NULL persisted.
- `test_nyfed_db_views.py` — view math on seeded rows: `v_rrp_trend` take-up +
  change; `v_sofr_latest` picks the latest SOFR and computes the IORB spread
  (and NULLs it when IORB absent); `v_soma_runoff` WoW total change sign.
- `test_nyfed_run.py` — `run()` with injected fetchers: happy-path counts;
  **skip-and-continue** (one domain raises → others still stored, failure warned,
  **secret-hygiene assertion**: stderr contains the class name, never a
  URL/`str(e)`); all-fail → `(0, 0)` snapshot + loud warning;
  `--only`/`--exclude`/`--add`; second-run incremental upsert (history grows,
  restated operation overwrites); `keep_days` prunes snapshots but **not** fact
  tables. `now_iso` pinned for determinism.
- `test_registry.py` — extend: dispatcher routes `nyfed`; `--list` includes it;
  existing paths unchanged.

Live smoke (manual, like the other screeners): pull the v1 set into a temp DB;
assert non-empty `reference_rates` (with a `SOFR` row), `repo_ops`, and
`soma_holdings`, a populated `v_sofr_latest`, and a `v_soma_runoff` with a sane
WoW change.

## Non-goals (YAGNI)

- **Don't duplicate what FRED already gives you.** Several of these also live in
  FRED — `SOFR`, the ON-RRP award (`RRPONTSYD`), IORB (`IORB`). The value here is
  the **richer / fresher operation-level detail** (per-operation submitted vs.
  accepted, rate percentiles, SOMA holdings by security type, weekly as-of
  granularity) and same-day freshness, not re-carrying FRED's daily series. Where
  a single scalar suffices, prefer FRED; use NY Fed for the operation detail.
- **Primary-dealer statistics in v1** — defined in the catalog but disabled;
  phase 2 (wide series-key panel; additive, not a rewrite).
- **Agency-MBS operation detail / TBA schedules, securities-lending, FX-swap
  lines** — other Markets domains, out of scope for the funding/liquidity reader.
- **Price / signal backtesting** — this screener only *stores* the money-market
  data; signal consumption lives elsewhere in the bot.
- **Shared `Screener` base class** — shapes still differ; only `connect`/backoff
  are shared, as decided in the EDGAR/FRED specs.

## Environment

**No credentials required.** The NY Fed Markets API is public and key-free —
**do not** add a variable to `.env.example`. The only network config is the
descriptive User-Agent baked into the fetcher
(`agentic-trading-bot ninadk.dev@gmail.com`).
