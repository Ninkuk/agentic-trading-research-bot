# FRED Macro / Regime Screener — Design

**Date:** 2026-07-02
**Status:** Approved, ready for implementation planning
**Data source:** [FRED API](https://fred.stlouisfed.org/docs/api/fred/) (docs) —
requests go to `https://api.stlouisfed.org/fred/...`, authenticated with
`?api_key=` + `&file_type=json`. Key read from `FRED_API_KEY` in `.env`.

## Goal

Pull a curated set of key U.S. macroeconomic **time series** from FRED into SQLite
so the trading bot has a **macro/regime reader** — growth, inflation, rates, labor,
credit spreads, housing, and sentiment — with enough history to compute trend,
year-over-year change, and how extreme the current reading is versus each series'
own past.

This is the **fourth** screener in the family (`stocks`, `reddit`, `edgar`, `fred`).
It reuses the proven `screener_common` machinery but takes a **different data
shape** from the first three.

## Key realization (why this is a *time-series* screener, not cross-sectional)

The three existing screeners are **cross-sectional**: a universe of entities
(tickers / filings / posts) × metrics captured *at one moment*. Each snapshot is
a wide, self-contained state-of-the-world.

FRED is **time-series**: a small set of economic series, each with *decades of
dated observations*. The "rich data" is the **history**, not a wide row. A macro
regime is only legible across time — you cannot tell whether `UNRATE = 4.2%` is
loose or tight from one number; you need its trend and its distribution. So the
schema stores the full observation history per series and derives regime signals
in views, rather than storing one latest-value row per run.

This means the fact table is keyed by `(series_id, date)` and **upserted** (not
snapshot-scoped like `filings`/`observations` in the other screeners), because an
observation for a given date is an immutable-ish fact that statistical agencies
*revise* — a re-run must overwrite the revised value in place, never duplicate the
date. `snapshots` here records *fetch runs* (provenance + counts), and the
observation history persists across pruning.

## Source verification (confirmed first-hand 2026-07-02)

The user cited `https://fred.stlouisfed.org/docs/api/fred/`. **That is the correct
docs URL** — it returns `403` to bots (same fingerprint-blocking the EDGAR docs
domain uses), but it is the right page. The verified facts:

1. **API base is `https://api.stlouisfed.org/fred/`** (not the docs host). Probed
   `GET /fred/series/observations?series_id=GNPCA&file_type=json` → clean JSON
   error `"Variable api_key is not set"`, confirming endpoint + auth shape.
2. **Auth is a query param** `api_key=...`, read from `FRED_API_KEY` in `.env`
   (present and working — verified live against `UNRATE`). `file_type=json`
   returns JSON (default is XML).
3. **`/fred/series?series_id=X`** returns rich metadata: `title`,
   `observation_start`/`observation_end`, `frequency`(`_short`), `units`
   (`_short`), `seasonal_adjustment`(`_short`), `last_updated`, `popularity`,
   `notes`. (Verified — `UNRATE` returned all of these.)
4. **`/fred/series/observations?series_id=X`** returns `observations: [{date,
   value, realtime_start, realtime_end}, ...]`. **Missing values arrive as the
   string `"."`** and must be stored as `NULL`. Supports `observation_start`,
   `sort_order`, `limit`. (Verified — `UNRATE` returned 942 monthly obs.)
5. **Rate limit is 120 requests/minute.** A run makes ~2 calls per series
   (metadata + observations); the curated catalog is ~40 series ⇒ ~80 calls,
   comfortably under the cap even without throttling.

## Guiding principles

- **Store raw, derive in views (ELT).** Observations are the source of truth;
  every regime signal is a SQL view that can be rewritten without re-fetching.
- **Reuse proven patterns.** `connect`/`prune` from `screener_common`; the
  package layout, dependency-injected `run()`, and TDD from the other screeners.
- **Reuse the EDGAR backoff verbatim.** FRED can throttle (`429`) and has
  transient `5xx`; the bounded exponential-backoff `_http_get` already written for
  EDGAR is the right tool. (See [[edgar-sec-rate-limit-followup]].)
- **Dependency-free.** `urllib` + stdlib only, matching all existing screeners.
- **Never log the API key.** It is a secret query param; error messages and
  stderr must not echo the full request URL.

## Module structure

New self-contained package `fred_screener/`, parallel to the others:

```
fred_screener/
    __init__.py
    catalog.py  # curated macro series catalog (Series dataclass, themes) + select_ids
    fetch.py    # FRED HTTP client (api_key, backoff), series metadata + observations
    db.py       # schema + ELT views; upsert_series; write_observations; write_snapshot
    run.py      # resolve series -> fetch each -> upsert -> write snapshot; registered run fn
```

Registered in `registry.py`: `"fred": fred_main` (alongside `stocks`, `reddit`, `edgar`).

## Series selection (`fred_screener/catalog.py`)

A hardcoded, curated catalog is the default — it ships a working regime reader and
mirrors `stock_analysis_screener`'s `catalog.py` + `select_ids` pattern.

```python
@dataclass(frozen=True)
class Series:
    series_id: str   # FRED id, e.g. "T10Y2Y"
    theme: str       # growth|inflation|rates|labor|credit|housing|sentiment
```

`CATALOG: list[Series]` — ~35–45 series grouped by theme:

- **growth** — `GDPC1`, `INDPRO`, `PAYEMS`, `RSAFS`
- **inflation** — `CPIAUCSL`, `CPILFESL`, `PCEPILFE`, `T5YIE`, `T10YIE`
- **rates** — `DFF`, `DGS2`, `DGS10`, `DGS30`, `T10Y2Y`, `T10Y3M`
- **labor** — `UNRATE`, `ICSA`, `CIVPART`, `AHETPI`, `JTSJOL`
- **credit** — `BAMLH0A0HYM2`, `BAMLC0A0CM`, `TEDRATE`/`SOFR`, `DRSFRMACBS`
- **housing** — `HOUST`, `PERMIT`, `CSUSHPINSA`, `MORTGAGE30US`
- **sentiment** — `UMCSENT`, `VIXCLS`, `STLFSI4`, `NFCI`

`select_ids(only, exclude)` — resolve which catalog ids to pull: `only` (or the
full catalog) minus `exclude`, stripped/deduped/blank-dropped. Same defensive
logic as `stock_analysis_screener.run.select_ids`.

CLI escape hatch `--add SERIES_ID` (repeatable) pulls ad-hoc series **not** in the
catalog (theme recorded as `"custom"`), so the tool isn't limited to the curated
list without editing code.

> Final catalog membership is confirmed at implementation time by probing each id
> once (live) — a typo'd or discontinued id must not silently ship. Any id that
> 404s is dropped from the catalog with a note, not left dead.

## Fetch behaviour (`fred_screener/fetch.py`)

Pure parsers separated from HTTP so they unit-test against fixtures without
network. The EDGAR `_http_get` (bounded exponential backoff, honors `Retry-After`,
retryable on `429`/`5xx` + transient network errors) is reused; retry status set
extended to FRED's throttling (`429`, `503`).

- `_build_url(path, params) -> str` — assemble `api.stlouisfed.org/fred/{path}`
  with `api_key` (from arg/env) + `file_type=json` + caller params, URL-encoded.
- `fetch_series(series_id, api_key, get=_http_get) -> dict` — `GET /fred/series`,
  return the single `seriess[0]` metadata dict.
- `parse_observations(payload) -> list[dict]` — pure: map each observation to
  `{"date": ..., "value": float|None}`, converting `"."` → `None` and numeric
  strings → `float`.
- `fetch_observations(series_id, api_key, start=None, get=_http_get) -> list[dict]`
  — `GET /fred/series/observations` (optional `observation_start`), return parsed
  rows. Full history by default.
- API key: accepted as an argument (injected by `run`), which reads it from
  `os.environ["FRED_API_KEY"]`. A missing/empty key raises a clear error **before**
  any network call. The key is never included in raised messages or logs.

## Data model

### Tables

```sql
CREATE TABLE snapshots (             -- one row per fetch run (provenance)
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,  -- ISO-8601 UTC: when the run executed
    series_count      INTEGER NOT NULL, -- series successfully fetched this run
    observation_count INTEGER NOT NULL  -- total obs rows upserted this run
);

CREATE TABLE series (                -- dimension, upserted each run
    series_id                 TEXT PRIMARY KEY,   -- e.g. "T10Y2Y"
    theme                     TEXT,               -- catalog grouping (from catalog, not API)
    title                     TEXT,
    frequency                 TEXT,
    frequency_short           TEXT,
    units                     TEXT,
    units_short               TEXT,
    seasonal_adjustment_short TEXT,
    observation_start         TEXT,
    observation_end           TEXT,
    last_updated              TEXT,
    popularity                INTEGER,
    notes                     TEXT,
    first_seen                TEXT,   -- ISO capture of first time we stored this series
    last_seen                 TEXT    -- ISO capture of most recent run touching it
);

CREATE TABLE observations (          -- fact table, upserted by (series_id, date)
    series_id TEXT NOT NULL REFERENCES series(series_id),
    date      TEXT NOT NULL,          -- observation date, YYYY-MM-DD
    value     REAL,                   -- NULL for FRED "." missing marker
    PRIMARY KEY (series_id, date)
);
CREATE INDEX ix_observations_date ON observations(date);
```

- `observations` is **upserted** on `(series_id, date)`: re-runs overwrite revised
  values in place and never duplicate a date. This is the key structural
  difference from the snapshot-scoped fact tables in the other screeners.
- `series` is a dimension upserted each run: refresh metadata + `last_seen`,
  preserve `first_seen` (`ON CONFLICT(series_id) DO UPDATE`).
- `snapshots` records run metadata only; observations are **not** snapshot-scoped
  (a `snapshot_id` FK on observations would be wrong — the same date's value is
  shared across runs).

### Derived-signal views ("rich" / regime reader lives here)

All `CREATE VIEW IF NOT EXISTS`, created with the schema:

- **`v_latest`** — most recent observation per series (`series_id, date, value`)
  joined to `series` metadata (`title, theme, units_short, frequency_short`).
  Uses a windowed "latest non-null obs per series" so a trailing `"."` doesn't
  blank a series.
- **`v_yoy_change`** — latest value vs. the observation ~1 year prior, absolute and
  percent change. (Approximate-nearest match on date, tolerant of frequency.)
- **`v_zscore`** — latest value expressed as a z-score over that series' full
  stored history `(value - avg) / stddev`, i.e. how extreme the current reading is
  versus its own past → regime **extremity**.
- **`v_regime_signals`** — a curated derived-flags view assembled from `v_latest`,
  e.g. `yield_curve_inverted` (`T10Y2Y < 0`), `hy_spread` level, `real_policy_rate`
  (`DFF - CPI YoY`), presented as one row of named macro flags. This is the
  headline "what regime are we in" readout.

Views degrade gracefully when a referenced series wasn't selected (LEFT JOINs /
NULLs), so `--only`/`--exclude` runs don't error on missing inputs.

## Write behaviour (`fred_screener/db.py`)

- `ensure_schema(conn)` — create tables + views idempotently.
- `upsert_series(conn, meta_rows, captured_at)` — upsert `series` dimension:
  refresh metadata + `last_seen`, preserve `first_seen`.
- `write_observations(conn, series_id, obs_rows) -> int` — `INSERT ... ON
  CONFLICT(series_id, date) DO UPDATE SET value=excluded.value`; returns rows
  written. Dedupes by date within the batch (last wins).
- `write_snapshot(conn, captured_at, series_count, observation_count) -> id` —
  insert the run header.
- `connect` / `prune` come from `screener_common`.

## Orchestration (`fred_screener/run.py`)

`run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
     api_key=None, fetch_series=fetch.fetch_series,
     fetch_obs=fetch.fetch_observations, now_iso=None) -> (snapshot_id,
     series_count, observation_count)`:

1. Resolve `api_key` (arg or `FRED_API_KEY` env); raise clearly if absent.
2. Resolve the series list: `select_ids(catalog, only, exclude)` + any `--add`.
3. `conn = connect(db_path); ensure_schema(conn)`.
4. For each `series_id` (**skip-and-continue** on failure):
   - `meta = fetch_series(...)`; `obs = fetch_obs(..., start=start)`.
   - On any exception for that series: log a one-line warning to stderr (id +
     error class, **no URL/key**), skip it, continue. Track failure count.
   - On success: `upsert_series([meta])`; `n = write_observations(id, obs)`.
5. `write_snapshot(captured_at, series_count=successes,
   observation_count=Σ n)`.
6. If **zero** series succeeded: still write the snapshot (0/0) and warn loudly —
   mirrors the other screeners' zero-count behaviour; does not raise.
7. If `keep_days is not None`: `db.prune(conn, keep_days, captured_at)` — a FRED
   local single-table prune of stale `snapshots` only; **not** the shared cascade
   helper (see Retention note).
8. Return `(snapshot_id, series_count, observation_count)`.

Fetchers + `now_iso` injected for deterministic, network-free tests (mirrors the
other screeners' DI).

CLI (`main` in `run.py`, invoked via the dispatcher):
`--db fred.db` · `--only ID,...` · `--exclude ID,...` · `--add ID` (repeatable) ·
`--start YYYY-MM-DD` (default: full history) · `--keep-days N` (default None).

## Error handling

- **Missing/empty `FRED_API_KEY`:** raise before any request, with a clear
  message pointing at `.env` (no key value echoed).
- **Per-series fetch failure** (HTTP error after retries, parse error, empty
  metadata): **skip-and-continue** — warn on stderr, run proceeds with the rest.
  *(User-confirmed preference: resilient partial snapshot over abort.)*
- **All series fail:** write a `(0, 0)` snapshot, warn loudly, return normally.
- **Missing value `"."`:** stored as `NULL`, not skipped (preserves the date).
- **Throttling / transient `5xx`:** absorbed by the reused bounded backoff.

## Retention

`observations` is a growing historical fact table keyed by `(series_id, date)`,
**not** snapshot-scoped — so the shared `prune` (which cascades a `child_table`
off `snapshot_id`) does **not** apply to observations, and must not delete them.

- Default (no `--keep-days`): keep everything (the point of a history store).
- With `--keep-days N`: prune only stale **`snapshots`** rows (run provenance);
  `series` and `observations` are preserved. Because `snapshots` has no child
  table here, `fred_screener/db.py` implements its own `prune` as a plain
  single-table delete of old run headers (`DELETE FROM snapshots WHERE
  captured_at < cutoff`) rather than delegating to the shared cascade `prune` in
  `screener_common`. *(This deviation from the other screeners' cascade is called
  out explicitly in `db.py` so a future reader doesn't wire observations into a
  cascade by reflex.)*

## Testing (TDD, mirrors existing `tests/`)

- `test_fred_fetch.py` — `parse_observations` (`"."` → `None`, numeric → float,
  ordering); `_build_url` (encodes params, includes key + `file_type=json`);
  `fetch_series`/`fetch_observations` against JSON fixtures via injected `get`;
  backoff retry on `429`/`503` with injected fake opener + `sleep` (like EDGAR);
  missing-key raises before any call.
- `test_fred_catalog.py` — `select_ids` (only/exclude, strip/dedupe/blank-drop,
  `--add` merge, custom theme); catalog integrity (unique ids, valid themes).
- `test_fred_db_schema.py` — `ensure_schema` idempotent; tables + all views exist;
  re-run is a no-op.
- `test_fred_db_write.py` — `write_observations` upsert keyed by `(series_id,
  date)`: re-write of same date **updates in place** (no duplicate rows), revised
  value overwrites; `"."`→NULL persisted; `upsert_series` refreshes metadata +
  last_seen, preserves first_seen; view math (`v_latest` picks latest non-null,
  `v_yoy_change` delta, `v_zscore` sign/magnitude on a known distribution).
- `test_fred_run.py` — `run()` with injected fetchers: happy path counts,
  **skip-and-continue** (one series raises → others still stored, failure warned),
  all-fail → `(0,0)` snapshot + loud warning, `--only`/`--exclude`/`--add`
  selection, second-run upsert (history grows, revised value overwrites),
  `keep_days` prunes snapshots but **not** observations.
- `test_registry.py` — extend: dispatcher routes `fred`; `--list` includes it;
  existing `stocks`/`reddit`/`edgar` paths unchanged.
- `test_screener_common.py` — unchanged (already covers `connect`/`prune`).

Live smoke (manual, like the other screeners): pull the curated catalog into a
temp DB with the real key; assert non-zero `series`, non-zero `observations`, a
populated `v_latest`, and a sane `v_regime_signals` row.

## Out of scope (YAGNI)

- **ALFRED real-time / vintages** (`realtime_start`/`realtime_end` history) — we
  store the *current* value per date, not the full revision-vintage cube. A future
  enrichment if point-in-time backtesting needs it.
- **Categories / releases / tags / sources endpoints** — the catalog is
  hand-curated by series id; category-driven discovery is a deferred alternative
  (the user chose the curated catalog).
- **International / non-FRED-hosted series** and unit transformations (`units=chg`,
  `pc1`, etc.) — we pull raw levels and derive changes in views instead.
- **Shared `Screener` base class** — shapes still differ; only `connect`/`prune`
  are shared, as decided in the EDGAR spec.
- **Cross-screener joins** (FRED regime ↔ stocks/edgar signals) — future query
  layer.
