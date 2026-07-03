# USDA WASDE / NASS Commodity Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [USDA NASS Quick Stats API](https://quickstats.nass.usda.gov/api/)
(`https://quickstats.nass.usda.gov/api/api_GET/?key=KEY&...`) for commodity
production / stocks / supply series, plus the monthly **WASDE** supply/demand
balance sheets (WAOB/OCE via ESMIS). Free JSON/CSV API, requires a **free API key**
(`NASS_API_KEY`).
**Confidence:** 🟡 endpoints located but not adversarially verified — confirm the
Quick Stats params and the machine-readable WASDE data access live at
implementation time.
**Package:** `usda_screener/` · **Dispatcher:** `usda`

## Goal

Pull USDA crop **supply/demand and ending-stocks** data (corn, soybeans, wheat)
into SQLite so the bot can read the balance-sheet gauge that drives grains + softs
futures and ag equities: the **stocks-to-use ratio** (ending stocks / total use).
A tightening ratio is bullish for the commodity; a loosening one bearish. WASDE
release days are major ag-vol events.

This is a **panel** screener (commodity × metric × period), upserted by key, signals
derived in views — kept deliberately tight (tier-3).

## Data-source notes

**A. NASS Quick Stats API** — 🟡.
`https://quickstats.nass.usda.gov/api/api_GET/?key=KEY&format=JSON&commodity_desc=CORN&...`.
Free key from [`https://quickstats.nass.usda.gov/api/`](https://quickstats.nass.usda.gov/api/);
stored as `NASS_API_KEY` in `.env`, read via a `require_api_key` helper (FRED
pattern) — the key is a **query param** and is **never** printed or logged. *Confirm
live at implementation time:* exact filter param names (`commodity_desc`,
`statisticcat_desc`, `short_desc`, `agg_level_desc=NATIONAL`, `year__GE`) and that
each query stays under the **50,000-row cap** (NASS errors past it) by narrowing to
national + annual + a specific `short_desc`.

**B. WASDE balance sheets (WAOB/OCE)** — 🟡. The monthly *World Agricultural Supply
and Demand Estimates* supply/demand balance sheets are distributed via USDA
OCE / ESMIS, **not** Quick Stats. Quick Stats covers NASS survey series
(production, stocks); the full WASDE ending-stocks/use balance may require the
**OCE/ESMIS downloadable data files**. *Confirm the machine-readable WASDE access at
implementation time* — v1 sources what Quick Stats exposes (production, stocks) and
flags the WASDE-native balance-sheet ingestion as confirm-live-then-wire.

### Report calendar (for the monitor layer — cross-reference)

NASS publishes the Agricultural Statistics Board calendar as machine-readable
**iCalendar (.ics)**
([`https://www.nass.usda.gov/Publications/Calendar/`](https://www.nass.usda.gov/Publications/Calendar/));
the WASDE/ESMIS release calendar is at
[`https://esmis.nal.usda.gov/release-calendar`](https://esmis.nal.usda.gov/release-calendar).
WASDE days are major ag-vol events. The calendar belongs to the event-monitor layer
(see
[2026-07-03-event-monitor-framework-design.md](2026-07-03-event-monitor-framework-design.md)),
**not** this screener — noted only so the monitor can source USDA release dates.

## Data-shape classification

**Panel** — commodity × metric × period. Upserted by `(commodity, metric, period)`;
USDA revises estimates month to month, so a re-run overwrites in place, never
duplicates a period. `snapshots` records fetch runs only; history persists across
pruning.

## Module layout

```
usda_screener/
    __init__.py
    catalog.py  # curated (commodity, metric) targets + NASS query params + select_ids
    fetch.py    # Quick Stats HTTP client (key, backoff) + pure parser
    db.py       # from screener_common import connect; schema + views; upsert writer
    run.py      # resolve targets -> fetch each -> upsert -> snapshot; argparse main
```

Registered in `registry.py`: `REGISTRY["usda"] = usda_main`.
**(Not modified by this spec — implementation task.)**

### `catalog.py`

Each target is a `(commodity, metric)` pair carrying the NASS filter that fetches
it; `--only/--exclude/--add` compose via `select_ids(all, only, exclude, add)` over
the composite id `f"{commodity}:{metric}"`:

```python
@dataclass(frozen=True)
class Series:
    commodity: str  # CORN | SOYBEANS | WHEAT
    metric: str     # PRODUCTION | ENDING_STOCKS | TOTAL_USE | SUPPLY  (our label)
    query: dict     # NASS Quick Stats filter (short_desc, statisticcat_desc, agg_level_desc, ...)
```

Composite id `"CORN:ENDING_STOCKS"`. `--add COMMODITY:METRIC` is supported only for
catalog-known pairs; genuinely novel `short_desc` targets are added to `catalog.py`
(a NASS query dict can't be expressed as a bare CLI token cleanly). *Confirm each
catalog query returns rows under the row cap at implementation time.*

## Schema (SQL)

`CREATE TABLE/VIEW IF NOT EXISTS` only, idempotent via `ensure_schema`. Default DB
path `usda.db`. WAL via `from screener_common import connect`. No separate DB
dimension table — the `(commodity, metric)` catalog lives in `catalog.py`; `unit`
rides on the fact row (keeps it tight).

```sql
CREATE TABLE IF NOT EXISTS snapshots (        -- one row per fetch run (provenance)
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,          -- ISO-8601 UTC run time
    series_count      INTEGER NOT NULL,       -- (commodity,metric) targets fetched OK
    observation_count INTEGER NOT NULL        -- obs rows upserted this run
);

CREATE TABLE IF NOT EXISTS usda_obs (         -- panel fact, upserted by key
    commodity TEXT NOT NULL,
    metric    TEXT NOT NULL,
    period    TEXT NOT NULL,                   -- marketing year / period label
    value     REAL,                            -- NULL for withheld "(D)"/blank
    unit      TEXT,
    PRIMARY KEY (commodity, metric, period)
);
CREATE INDEX IF NOT EXISTS ix_usda_obs_period ON usda_obs(period);
```

Writer upserts `ON CONFLICT(commodity, metric, period) DO UPDATE SET
value=excluded.value, unit=excluded.unit` — revisions overwrite in place, periods
never duplicate. Every writer ends with `conn.commit()`.

## Views

Three, `CREATE VIEW IF NOT EXISTS`, LEFT JOINs so a partial `--only` run yields
NULLs not errors:

- **`v_latest_balance`** — latest period per `(commodity, metric)`: the current
  balance-sheet line items at a glance.
- **`v_stocks_to_use`** — per commodity per period, `ending_stocks / total_use`
  (the key gauge), assembled by self-joining `usda_obs` on the two metrics; NULL when
  either leg is absent (partial selection).
- **`v_series_history`** — full history per `(commodity, metric)`.

## Run / CLI

```python
run(db_path, only=None, exclude=None, add=None, keep_days=None,
    api_key=None, now_iso=None,
    fetch_target=fetch.fetch_target) -> (snapshot_id, series_count, observation_count)
```

1. `api_key = fetch.require_api_key(api_key or os.environ.get("NASS_API_KEY"))` —
   raise clearly **before** any network call if absent (no key value echoed).
2. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
3. Resolve targets: `catalog.select_ids([s.id for s in CATALOG], only, exclude, add)`.
4. `conn = connect(db_path); ensure_schema(conn)`.
5. Per target, **skip-and-continue** on any failure: fetch (NASS query + key), upsert
   parsed rows. On exception: `conn.rollback()`, print
   `warning: skipping {commodity}:{metric}: {type(e).__name__}` to **stderr** — the
   key rides in the request URL, so **never** log `str(e)` / `e.url`. Continue.
6. Always `write_snapshot(now_iso, successes, Σ obs)`, even at zero (warn loudly).
7. If `keep_days is not None`: single-table prune of stale `snapshots` only.

`main(argv)` — argparse: `--db` (default `usda.db`), `--only`, `--exclude`, `--add`
(repeatable, `COMMODITY:METRIC`), `--keep-days` (default None). Prints a one-line
summary. `fetch_target` + `now_iso` injected for deterministic, network-free tests.

## Defaults

- DB path `usda.db`; catalog = corn/soy/wheat × {production, ending stocks, total
  use} (year range bounded inside each catalog query).
- `--keep-days` default None → keep everything.

### Pruning (FRED-style single-table)

`prune(conn, keep_days, now_iso)` deletes only stale `snapshots` run-headers —
**never** `usda_obs` — as a plain single-table delete, not the `screener_common`
cascade. The `db.py` docstring must warn against wiring `usda_obs` into a cascade
(verbatim the FRED prune warning).

## Testing (TDD, mirrors `tests/`)

- `test_usda_fetch.py` — pure parser (NASS `data[]` → `{period, value, unit}`,
  comma-stripped numbers, withheld `(D)`/blank → None); `_build_url` includes the
  key + `format=JSON` + catalog filter params; backoff over `{429, 5xx}` via fake
  opener + `sleep`; **missing key raises before any call**.
- `test_usda_catalog.py` — `select_ids` (only/exclude, strip/dedupe/blank-drop,
  `COMMODITY:METRIC` `--add`); catalog integrity (unique composite ids, every entry
  has a query dict).
- `test_usda_db_schema.py` — `ensure_schema` idempotent; table + all views present.
- `test_usda_db_write.py` — upsert by `(commodity, metric, period)` (revision
  overwrites in place, no dup); `v_stocks_to_use` ratio on a known
  ending-stocks/total-use fixture; partial selection → NULL, not error.
- `test_usda_run.py` — injected fetcher, real `tmp_path` DB, pinned `now_iso`:
  happy-path counts, skip-and-continue on a failing target, zero-success snapshot +
  loud warning, `keep_days` prunes snapshots but not obs, and **secret hygiene**:
  stderr carries `commodity:metric` + exception class name but **not** `str(e)`, and
  **`NASS_API_KEY` never appears anywhere in stdout/stderr**.
- `tests/test_registry.py` — extend: dispatcher routes `usda`; `--list` includes it;
  existing routes unchanged.

## Non-goals (YAGNI)

- **NASS survey minutiae** — county/state breakouts, non-balance-sheet categories;
  the catalog stays national + the core balance-sheet metrics.
- The **release-calendar monitor** itself — lives in the event-monitor layer
  ([2026-07-03-event-monitor-framework-design.md](2026-07-03-event-monitor-framework-design.md)).
- **Price data** — grains/softs prices live elsewhere (FRED / market feeds), not here.
- Intraday; alerting / notifications.

## Environment

- **Requires `NASS_API_KEY`** (free, register at
  `https://quickstats.nass.usda.gov/api/`). Add `NASS_API_KEY=` to `.env` **and to
  `.env.example`** with a short comment. Read via a `require_api_key` helper;
  **never** print or log the key.
- Reuses `http_client.make_opener` (descriptive UA
  `agentic-trading-bot ninadk.dev@gmail.com`) + `http_client.http_get` with bounded
  backoff (`_RETRY_STATUS = {429, 500, 502, 503, 504}`).
- Dependency-free (`urllib` + stdlib `json`), matching every existing screener.
