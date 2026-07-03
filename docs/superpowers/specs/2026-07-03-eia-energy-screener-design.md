# EIA Energy Inventories Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [EIA Open Data API v2](https://www.eia.gov/opendata/)
(base `https://api.eia.gov/v2/`) — weekly U.S. petroleum & natural-gas inventory
series (crude incl. Cushing, gasoline, distillate, production, imports, NG
storage). Free JSON API, requires a **free API key** (`EIA_API_KEY`).
**Confidence:** 🟡 endpoints located but not adversarially verified — confirm the
exact v2 routes and facet ids live at implementation time.
**Package:** `eia_screener/` · **Dispatcher:** `eia`

## Goal

Pull a curated set of **weekly EIA energy-inventory time series** into SQLite so the
bot can read inventory **surprises** — builds/draws vs. the prior week — which move
crude, gasoline, and natural-gas futures and the energy complex (XLE, USO, UNG).
The Cushing, OK hub number is the WTI physical-delivery stock and gets its own
series.

Structurally this is a near-clone of `fred_screener`: a small `series` dimension +
a keyed observation table, upserted by `(series_id, period)`, with signals derived
in views. The history is the product — a raw stock level means little; the
week-over-week delta versus the series' own path is the signal.

## Data-source notes

**EIA Open Data API v2** — 🟡. Base `https://api.eia.gov/v2/`. JSON. Free key from
[`https://www.eia.gov/opendata/`](https://www.eia.gov/opendata/); stored as
`EIA_API_KEY` in `.env`, read via a `require_api_key` helper (verbatim the FRED
pattern) — the key is a **query param** and is **never** printed or logged.

Route/query pattern (*confirm each route + facet id live at implementation time*):

```
/v2/{route}/data/?api_key=KEY
    &frequency=weekly
    &data[0]=value
    &facets[series][]=<FACET_ID>
    &start=YYYY-MM-DD
    &sort[0][column]=period&sort[0][direction]=desc
```

Series to ingest (route + facet ids to **confirm live** 🟡):

- **Weekly petroleum** — Weekly Petroleum Status Report (WPSR, released **Wed 10:30
  ET**). Crude oil stocks (incl. the **Cushing** hub), gasoline stocks, distillate
  stocks, production, imports. Under `petroleum/stoc/wstk` (stocks) and
  `petroleum/sum/sndw` (supply/disposition weekly). *Confirm the split of which
  metric lives under which route and the exact facet series ids.*
- **Weekly natural-gas storage** — `natural-gas/stor/wkly` (released **Thu 10:30
  ET**). Working-gas underground storage. *Confirm route + facet ids.*

**Bracket-array params quirk** (🟡): v2 uses repeated, bracketed keys
(`data[0]`, `facets[series][]`, `sort[0][column]`). Build the query as an **ordered
list of `(key, value)` tuples** passed to `urllib.parse.urlencode(pairs, doseq=True)`
so repeated `facets[series][]` keys survive — a plain dict would collapse them.
Confirm the encoding round-trips against the live API.

**Rate limits:** the free key has generous but real per-key limits; the curated
catalog is ~a dozen series ⇒ a handful of calls per run, well under the cap. Reuse
the bounded backoff (`_RETRY_STATUS = {429, 500, 502, 503, 504}`).

### Release schedule (for the monitor layer — cross-reference)

The WPSR schedule
([`https://www.eia.gov/petroleum/supply/weekly/schedule.php`](https://www.eia.gov/petroleum/supply/weekly/schedule.php))
and NG-storage schedule
([`https://ir.eia.gov/ngs/schedule.html`](https://ir.eia.gov/ngs/schedule.html))
give the Wed/Thu 10:30 ET cadence — **holiday weeks slip +1 day**. These inventory
prints are scheduled vol events; the calendar itself belongs to the event-monitor
layer (see
[2026-07-03-event-monitor-framework-design.md](2026-07-03-event-monitor-framework-design.md)),
**not** to this screener. Noted here only so the monitor can source EIA release
dates and so a future `v_release_calendar` could join against them.

## Data-shape classification

**Time-series** (like FRED). A small set of dated series, upserted by
`(series_id, period)`; statistical agencies **revise** weekly prints, so a re-run
must overwrite the revised value in place, never duplicate the period. `snapshots`
records fetch runs only; the observation history persists across pruning.

## Module layout

```
eia_screener/
    __init__.py
    catalog.py  # curated series (Series dataclass: id, route, facet, label, category) + select_ids
    fetch.py    # v2 HTTP client (api_key, bracket-param builder, backoff) + pure parser
    db.py       # from screener_common import connect; schema + views; upsert writers
    run.py      # resolve series -> fetch each -> upsert -> snapshot; argparse main
```

Registered in `registry.py`: `REGISTRY["eia"] = eia_main`.
**(Not modified by this spec — implementation task.)**

### `catalog.py`

Each series needs a **route + facet id** (unlike FRED's bare id), so the catalog
carries them; `--only/--exclude/--add` still compose via
`select_ids(all, only, exclude, add)` over the canonical `series_id`:

```python
@dataclass(frozen=True)
class Series:
    series_id: str  # canonical key we store, e.g. "WCESTUS1"  (confirm live)
    route: str      # v2 route, e.g. "petroleum/stoc/wstk"
    facet: str      # EIA facets[series][] value (often == series_id)
    label: str      # human label, e.g. "Crude oil stocks (ex-SPR)"
    category: str   # crude|cushing|gasoline|distillate|production|imports|natgas
```

`--add ROUTE:FACET` (repeatable) is the escape hatch for an ad-hoc series **not** in
the catalog: because EIA needs a route, the add token is `route:facet` (category
recorded as `"custom"`), parsed in `run()` — mirrors FRED's `--add` while respecting
that a bare id is unfetchable here. *Confirm every catalog route + facet resolves
live at implementation time; drop any that 404 with a note.*

## Schema (SQL)

`CREATE TABLE/VIEW IF NOT EXISTS` only, idempotent via `ensure_schema`. Default DB
path `eia.db`. WAL via `from screener_common import connect`.

```sql
CREATE TABLE IF NOT EXISTS snapshots (        -- one row per fetch run (provenance)
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,          -- ISO-8601 UTC run time
    series_count      INTEGER NOT NULL,       -- series fetched OK this run
    observation_count INTEGER NOT NULL        -- obs rows upserted this run
);

CREATE TABLE IF NOT EXISTS series (           -- dimension, upserted each run
    series_id   TEXT PRIMARY KEY,
    route       TEXT,
    label       TEXT,
    category    TEXT,                          -- catalog grouping
    unit        TEXT,                          -- from API response (e.g. "MBBL")
    frequency   TEXT,                          -- "weekly"
    first_seen  TEXT,
    last_seen   TEXT
);

CREATE TABLE IF NOT EXISTS eia_obs (          -- fact, upserted by (series_id, period)
    series_id TEXT NOT NULL REFERENCES series(series_id),
    period    TEXT NOT NULL,                   -- observation period YYYY-MM-DD
    value     REAL,                            -- NULL for missing/withheld
    PRIMARY KEY (series_id, period)
);
CREATE INDEX IF NOT EXISTS ix_eia_obs_period ON eia_obs(period);
```

- `eia_obs` **upserted** on `(series_id, period)`
  (`ON CONFLICT(series_id, period) DO UPDATE SET value=excluded.value`): revisions
  overwrite in place, periods never duplicate.
- `series` upserted each run: refresh `unit`/`frequency`/`label`/`category` +
  `last_seen`, preserve `first_seen`.
- Every writer ends with `conn.commit()`.

## Views

Three, `CREATE VIEW IF NOT EXISTS`, LEFT JOINs so a partial `--only` run yields
NULLs not errors:

- **`v_latest`** — most recent non-null obs per series, joined to `series`
  (`label, category, unit`) — the current inventory picture.
- **`v_weekly_change`** — latest value vs. the **immediately preceding period** for
  that series: `change_abs` and `change_pct` = the build (`+`) / draw (`−`) that
  moves the tape. (Prior period via a correlated `MAX(period) < latest` subquery,
  per-series.)
- **`v_series_history`** — full obs history per series joined to metadata, a
  convenience view for charting/backtests.

## Run / CLI

```python
run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
    api_key=None, now_iso=None,
    fetch_series_obs=fetch.fetch_series_obs) -> (snapshot_id, series_count, observation_count)
```

1. `api_key = fetch.require_api_key(api_key or os.environ.get("EIA_API_KEY"))` —
   raise clearly **before** any network call if absent (no key value echoed).
2. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
3. Resolve series: `catalog.select_ids([s.series_id for s in CATALOG], only,
   exclude, add)` + parse any `route:facet` `--add` tokens into ad-hoc `Series`.
4. `conn = connect(db_path); ensure_schema(conn)`.
5. Per series, **skip-and-continue** on any failure: fetch (route + facet + start),
   `upsert_series([meta])`, `write_observations`. On exception: `conn.rollback()`,
   print `warning: skipping {series_id}: {type(e).__name__}` to **stderr** — the key
   rides in the request URL, so **never** log `str(e)` / `e.url` (identical hazard to
   FRED). Continue.
6. Always `write_snapshot(now_iso, successes, Σ obs)`, even at zero (warn loudly, do
   not raise).
7. If `keep_days is not None`: single-table prune of stale `snapshots` only.

`main(argv)` — argparse: `--db` (default `eia.db`), `--only`, `--exclude`, `--add`
(repeatable, `route:facet`), `--start YYYY-MM-DD` (default: full available history),
`--keep-days` (default None). Prints a one-line summary. `fetch_series_obs` +
`now_iso` injected for deterministic, network-free tests.

## Defaults

- DB path `eia.db`; catalog = the curated WPSR + NG-storage series above.
- `--start` default None → full available history from the API.
- `--keep-days` default None → keep everything.

### Pruning (FRED-style single-table)

`prune(conn, keep_days, now_iso)` deletes only stale `snapshots` run-headers —
**never** `eia_obs` (the accumulated history) — as a plain single-table delete, not
the `screener_common` cascade. The `db.py` docstring must warn against wiring
`eia_obs` into a cascade (verbatim the FRED prune warning).

## Testing (TDD, mirrors `tests/`)

- `test_eia_fetch.py` — pure parser (nested `response.data`, `value` → float / None
  for withheld, `period` extraction, `unit` capture); `_build_url` encodes the
  bracket-array params correctly (`doseq`, repeated `facets[series][]`, key present
  + `data[0]=value`); backoff over `{429, 5xx}` via fake opener + `sleep`;
  **missing key raises before any call**.
- `test_eia_catalog.py` — `select_ids` (only/exclude, strip/dedupe/blank-drop,
  `route:facet` `--add` merge → custom category); catalog integrity (unique ids,
  every entry has route+facet, valid categories).
- `test_eia_db_schema.py` — `ensure_schema` idempotent; tables + all views present.
- `test_eia_db_write.py` — `write_observations` upsert by `(series_id, period)`
  (revision overwrites in place, no dup); `upsert_series` refreshes metadata +
  last_seen, preserves first_seen; `v_weekly_change` delta sign (build vs draw) on a
  known two-week fixture.
- `test_eia_run.py` — injected fetcher, real `tmp_path` DB, pinned `now_iso`:
  happy-path counts, skip-and-continue on a failing series, zero-success snapshot +
  loud warning, `keep_days` prunes snapshots but not obs, and **secret hygiene**:
  stderr carries `series_id` + exception class name but **not** `str(e)`, and
  **`EIA_API_KEY` never appears anywhere in stdout/stderr**.
- `tests/test_registry.py` — extend: dispatcher routes `eia`; `--list` includes it;
  existing routes unchanged.

## Non-goals (YAGNI)

- Intraday / real-time — one refresh per weekly print.
- Non-inventory energy series — **prices live in FRED** (`fred_screener`); this
  screener is inventories only.
- The **release-schedule monitor** itself — lives in the event-monitor layer
  ([2026-07-03-event-monitor-framework-design.md](2026-07-03-event-monitor-framework-design.md)).
- Regional/PADD micro-breakouts beyond the curated national + Cushing set (a future
  catalog extension, not a v1 concern).
- Alerting / notifications.

## Environment

- **Requires `EIA_API_KEY`** (free, register at `https://www.eia.gov/opendata/`).
  Add `EIA_API_KEY=` to `.env` **and to `.env.example`** with a short comment. Read
  via a `require_api_key` helper; **never** print or log the key.
- Reuses `http_client.make_opener` (descriptive UA
  `agentic-trading-bot ninadk.dev@gmail.com`) + `http_client.http_get` with bounded
  backoff.
- Dependency-free (`urllib` + stdlib `json`), matching every existing screener.
