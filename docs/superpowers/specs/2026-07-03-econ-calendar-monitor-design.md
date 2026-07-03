# Economic Release Calendar Monitor (FRED backbone) — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [FRED `releases/dates`](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html)
and [`release/dates`](https://fred.stlouisfed.org/docs/api/fred/release_dates.html) —
requests go to `https://api.stlouisfed.org/fred/...`, authenticated with
`?api_key=` + `&file_type=json`. **Reuses the existing `FRED_API_KEY`** already
in `.env` (same key the `fred_screener` uses).
**Confidence:** 🔵 light-research (single-pass source scan, not adversarially
verified) — confirm endpoints at implementation.

## Goal

Ingest the **forward schedule of U.S. economic data releases** — CPI, PPI, the
Employment Situation (nonfarm payrolls / unemployment), GDP, Retail Sales, PCE,
JOLTS — into the shared `events` table, so the bot **knows what prints when** and
can **de-risk or size positions around high-impact releases** before they land.

This is the **first monitor** of the new event-date kind (see
[2026-07-03-event-monitor-framework-design.md](./2026-07-03-event-monitor-framework-design.md)),
and — per that spec's build order — **the highest-value, lowest-effort monitor in
the whole family**: it rides one API the bot already authenticates to, needs no
new credential and no HTML scraping, and one endpoint covers most of the
economic-release calendar.

Package `econ_calendar`, dispatcher name `econ_calendar`. It uses
`monitor_common` for the schema, write helpers, shared views, prune, and
`now_iso` discipline, and **reuses `fred_screener.fetch`'s HTTP scaffolding and
`require_api_key`** (import-adjacent, so the FRED client is written once).

## Why FRED is the backbone (the whole trick)

FRED models every published dataset as a **release** with an id, and exposes each
release's **calendar of publication dates — including future ones.** Because the
bot already holds a working `FRED_API_KEY`, a single authenticated API replaces
scraping BLS, BEA, and Census calendars separately. The catch is one query
parameter, described below.

### Endpoints

- **All upcoming release dates (the backbone call):**
  ```
  GET https://api.stlouisfed.org/fred/releases/dates
      ?api_key=KEY&file_type=json
      &include_release_dates_with_no_data=true
      &sort_order=asc&order_by=release_date
      &realtime_start={today}
  ```
  - **`include_release_dates_with_no_data=true` is the key parameter.** The
    default (`false`) **strips future dates** — a not-yet-published release has
    "no data" yet, so FRED omits it. Flipping this to `true` is what surfaces the
    *forward* calendar at all. Without it, the endpoint is backward-looking and
    useless for a monitor.
  - **`realtime_start={today}`** restricts the result to dates from today
    forward, so the response is the upcoming calendar rather than all history.
    (`{today}` is bound from the injected `now_iso`.)

- **Per-release calendar** (used when pulling only the curated set):
  ```
  GET https://api.stlouisfed.org/fred/release/dates
      ?release_id={id}&include_release_dates_with_no_data=true
      &api_key=KEY&file_type=json&realtime_start={today}&sort_order=asc
  ```
  Same `include_release_dates_with_no_data=true` requirement.

- **Discover release ids** (one-off, at catalog-curation time, not per run):
  ```
  GET https://api.stlouisfed.org/fred/releases?api_key=KEY&file_type=json
  ```

> These endpoints and the `include_release_dates_with_no_data` behaviour are from
> a single-pass read of the FRED docs (🔵) — confirm live at implementation, the
> same way the `fred_screener` catalog ids were probed once before shipping.

## Source notes / gotchas

- **FRED gives the release DATE, not the intraday TIME.** The `event_time`
  column stays populated from a **small known-time lookup keyed by release** in
  `catalog.py`: most U.S. macro releases hit at **08:30 ET** (CPI, PPI,
  Employment Situation, Retail Sales, GDP, PCE), a few differ. FRED will never
  supply the time, so this lookup is the only source of `event_time` and is
  documented as a hand-maintained constant.
- **Lead time:** agencies publish schedules **up to ~1 year ahead**, so a single
  fetch populates a long forward horizon; runs mostly *firm up* existing rows.
- **Rate limit** is FRED's 120 req/min — a run makes at most a few dozen calls
  (one all-releases call, or one per curated id); comfortably under the cap, same
  as `fred_screener`.

## Data shape: forward calendar

Standard monitor shape (see framework spec). Each FRED release-date maps to one
`events` row:

- `event_type` — a stable per-release slug, e.g. `'cpi_release'`,
  `'employment_situation'`, `'ppi_release'`, `'gdp_release'`,
  `'retail_sales_release'`, `'pce_release'` (from the catalog).
- `event_date` — the release date (`YYYY-MM-DD`).
- `event_time` — from the known-time lookup (`'08:30'` for most), else NULL.
- `subtype` — `str(release_id)` (part of the natural key; never NULL).
- `title` — the release name.
- `status` — `'scheduled'` normally; FRED marks provisional/estimated dates,
  which map to `'tentative'`.
- `source` — `'fred'`.
- `payload` — optional JSON (`release_id`, raw `date_type`).

## Curated release catalog (`econ_calendar/catalog.py`)

A hardcoded, curated catalog mirrors `fred_screener.catalog` / the
`stock_analysis_screener` catalog pattern: `release_id → (event_type slug, label,
impact, category, release_time)`.

```python
@dataclass(frozen=True)
class Release:
    release_id: int      # FRED release id
    event_type: str      # 'cpi_release', ...
    label: str           # 'Consumer Price Index'
    impact: str          # 'high' | 'med'
    category: str        # 'inflation'|'labor'|'growth'|'consumer'
    release_time: str    # 'HH:MM' ET known time, e.g. '08:30'
```

Known ids (from a single-pass source scan — **confirm live**, and any id that
404s is dropped with a note, exactly as the FRED spec prescribes):

| Release | `release_id` | Impact | Confidence |
|---|---|---|---|
| CPI (Consumer Price Index) | 10 | high | 🔵 |
| Employment Situation (NFP / unemployment) | 50 | high | 🔵 |
| PPI (Producer Price Index) | 46 | high | 🔵 |
| GDP | 53 | high | 🔵 |
| Advance Retail Sales | ~99 | high | 🟡 confirm live |
| PCE / Personal Income & Outlays | *tbd* | high | 🟡 confirm live |
| JOLTS (Job Openings) | *tbd* | med | 🟡 confirm live |

**High-impact set** = CPI, Employment Situation, PPI, GDP, Retail Sales, PCE —
these drive `v_imminent_high_impact`.

`select_ids(only, exclude)` resolves which catalog release_ids to pull — same
strip/dedupe/blank-drop logic as `fred_screener.catalog.select_ids`.

## Module layout

```
econ_calendar/
    __init__.py
    catalog.py  # Release dataclass, curated release_id catalog, known-time lookup, select_ids
    fetch.py    # FRED releases/dates + release/dates (reuses fred_screener.fetch HTTP + require_api_key)
    db.py       # ensure_schema (via monitor_common) + econ-specific views
    run.py      # fetch upcoming -> upsert events -> snapshot -> prune; argparse main
```

- Register `"econ_calendar"` in `registry.py` (import `run.main as
  econ_calendar_main`).
- `.env.example` unchanged — **reuses `FRED_API_KEY`.**

### `fetch.py`

- Reuses `fred_screener.fetch`'s opener, `_http_get` (bounded backoff on
  `429`/`5xx`), and **`require_api_key`** (missing/empty key raises *before* any
  network call; the key value is never echoed).
- `fetch_all_release_dates(api_key, today, get=...) -> list[dict]` — the
  backbone `releases/dates` call with `include_release_dates_with_no_data=true`
  and `realtime_start=today`. Returns raw `{release_id, release_name,
  date, ...}` rows.
- `fetch_release_dates(release_id, api_key, today, get=...) -> list[dict]` — the
  per-release `release/dates` variant (same required param).
- `parse_release_dates(payload, catalog) -> list[event dict]` — **pure**: filter
  to catalog release_ids, map to `events` rows, attach `event_time` from the
  known-time lookup, set `status`/`source`. Testable against JSON fixtures with
  no network.

### `db.py` — views (layer on `monitor_common`'s `v_upcoming` / `v_imminent`)

`ensure_schema` calls `monitor_common.ensure_schema(conn)` then creates:

- **`v_upcoming_releases`** — `v_upcoming` events of the econ types joined to the
  catalog's `impact` / `label` / `category`, `event_date >= :today` ordered.
- **`v_imminent_high_impact`** — the next `N` days (`event_date BETWEEN :today AND
  date(:today,'+N days')`) filtered to `impact='high'`. **The headline "what
  big print is about to land" readout.**
- **`v_this_week`** — releases from `:today` through the end of the current week
  (`date(:today,'weekday 5')` / Sunday boundary), for a weekly planning glance.

All bind `:today` from the injected `now_iso` — never `date('now')`.

### `run.py` — orchestration + CLI

`run(db_path, only=None, exclude=None, horizon_days=None, keep_days=None,
     api_key=None, fetch_dates=..., now_iso=None) -> (snapshot_id, event_count)`:

1. `api_key = require_api_key(api_key or os.environ["FRED_API_KEY"])`.
2. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`; `today =
   date(now_iso)`.
3. Resolve release_ids: `catalog.select_ids(only, exclude)` (or the all-releases
   endpoint filtered to the catalog).
4. `conn = monitor_common.connect(db_path); ensure_schema(conn)`.
5. Fetch upcoming dates for the selected releases, `parse_release_dates`, then
   **`upsert_events`** (releases only ever get *added* or *firmed up* /
   *rescheduled*, and FRED keeps listing them — upsert is the right primitive; a
   pulled release is rarely retracted, so `replace_forward_window` is optional
   and off by default here).
6. Per-release failure is **skip-and-continue**: `conn.rollback()`, log
   **`warning: skipping {release_id}: {type(e).__name__}`** (never `str(e)` /
   `e.url` — the URL embeds the API key), continue.
7. `write_snapshot(now_iso, event_count, source='fred')`; then `prune(conn,
   keep_days, now_iso)` if `--keep-days` given (snapshots only — **never** future
   events).
8. Return `(snapshot_id, event_count)`.

Fetchers + `now_iso` injected for deterministic, network-free tests.

**CLI** (`prog="econ_calendar"`):
- `--db` (default `econ_calendar.db`)
- `--only ID,...` / `--exclude ID,...` (release_ids)
- `--horizon-days N` (imminence window for the views; default 7)
- `--keep-days N` (prune snapshot provenance only)

## Defaults (approved)

- **Horizon:** `--horizon-days 7` drives `v_imminent_high_impact`.
- **Retention:** keep the full forward calendar and past events; `--keep-days`
  prunes only run-provenance snapshots (framework rule).
- **Catalog:** curated high/med-impact releases above; extend via `--only`/`--add`
  or by editing `catalog.py`.
- **Times:** `08:30 ET` default per the known-time lookup; per-release overrides
  in the catalog.

## Signal

Knowing precisely **when CPI / jobs / PPI / GDP / retail land** lets the bot
**de-risk or size positions around high-impact prints** — cut gross into a CPI
morning, avoid initiating just before nonfarm payrolls, widen stops through a GDP
release. This is the **single highest-value, lowest-effort monitor**: one API the
bot already authenticates to, no scraping, no new secret.

## Testing (mirror `test_fred_*` / the monitor conventions)

- `test_econ_calendar_fetch.py` — `parse_release_dates` (catalog filter,
  `event_time` from the known-time lookup, `status`/`source` mapping, non-catalog
  ids dropped); URL builder includes `include_release_dates_with_no_data=true` +
  `realtime_start`; `require_api_key` raises before any call; backoff on
  `429`/`503` via injected fake opener + `sleep`. **Secret-hygiene assertion: a
  raised/logged failure never contains the api_key or a full URL.**
- `test_econ_calendar_catalog.py` — `select_ids` only/exclude/strip/dedupe;
  catalog integrity (unique ids, valid `impact`/`category`, every release has a
  `release_time`).
- `test_econ_calendar_db_schema.py` — `ensure_schema` idempotent; `events` +
  `snapshots` + the three econ views exist.
- `test_econ_calendar_db_write.py` — `upsert_events` firms up in place
  (tentative→confirmed, no duplicate `(event_type,event_date,subtype)`);
  `v_imminent_high_impact` filters to `impact='high'` inside the horizon with a
  **pinned `now_iso`** (imminence boundary); `v_upcoming_releases` ordering.
- `test_econ_calendar_run.py` — `run()` with injected fetchers + **pinned
  `now_iso`**: happy-path counts, skip-and-continue on one release raising,
  `--only`/`--exclude`, second-run firm-up (row updates, not duplicated),
  `keep_days` prunes snapshots but **not** future events.
- `test_registry.py` — extend to assert `"econ_calendar"` dispatches.

## Non-goals (YAGNI)

- **Consensus / actual / surprise values.** This monitor stores *when* a release
  publishes, not the printed number — the value lands in FRED observations (the
  `fred_screener`'s job). A future join can pair schedule with outcome.
- **Non-U.S. releases** (ECB, BoE, etc.) — U.S.-only for v1.
- **The full FRED release universe.** The curated high/med-impact catalog ships a
  working reader; scheduling every FRED release is noise.
- **Intraday-precise timing.** `event_time` is a best-effort `HH:MM` ET from a
  hand-maintained lookup, not a live feed.

## Environment

- **No new credential — reuses `FRED_API_KEY`** from `.env` (`require_api_key`
  raises clearly if absent, never echoing the value).
- Dependency-free (`urllib` + stdlib) via the shared `fred_screener.fetch` /
  `http_client` scaffolding; UA `agentic-trading-bot ninadk.dev@gmail.com`;
  bounded backoff on `429`/`5xx`.
- **Secret hygiene:** per-release errors log only `type(e).__name__`; the API key
  (embedded in the request URL) is never printed. Writers end with
  `conn.commit()`.
