# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A signal-collection layer for a trading bot: ~20 independent **screeners** (point-in-time data
readers) and event-date **monitors** (forward-looking calendars) that each fetch one official
data source (SEC, FRED, CFTC, FINRA, CBOE, Treasury, NY Fed, EIA, USDA, …) into a per-source
SQLite database, then derive signals in SQL views. Downstream consumption (the "signal → candidate"
pipeline) is designed in `docs/research/` but not yet built.

**Zero runtime third-party dependencies** — everything is stdlib (`urllib`, `sqlite3`, `json`,
`argparse`). Python 3.12, managed with `uv`. The only dev dependency is `pytest`.

## Commands

```bash
# Run a screener/monitor (dispatched by name; see registry.py for the 20 names)
uv run python main.py fred --db fred.db --keep-days 90
uv run python main.py cftc --family disaggregated
uv run python main.py --list          # print all registered dispatcher names

# Tests (fully offline — no network, no real API keys needed)
uv run pytest                          # full suite (~600 tests, <1s)
uv run pytest tests/test_fred_run.py   # one file
uv run pytest -k regime                # by name substring
uv run pytest tests/test_fred_run.py::test_run_upserts_observations  # single test

# Dependencies are stdlib-only by design. Avoid adding runtime deps; if genuinely
# unavoidable, add via `uv add` and justify it (it breaks the "plain checkout" property).
```

API keys (`FRED_API_KEY`, `EIA_API_KEY`, `NASS_API_KEY`, optional `CFTC_APP_TOKEN`) live in `.env`
— see `.env.example`. Most sources (SEC, FINRA, CBOE, Treasury, NY Fed) need no key.

## Architecture: one shape, ~20 slices

Every screener is a package of the **same four files** (learn one, know all):

- **`fetch.py`** — network + *pure* parsing. Builds URLs, GETs via `http_client`, parses the
  response into plain dicts/lists. Network is behind an injectable `get=`/`opener=` seam.
- **`db.py`** — SQLite schema (`CREATE TABLE ... IF NOT EXISTS`), idempotent `ensure_schema`,
  upsert writers, **ELT views** (`v_latest`, `v_yoy_change`, `v_zscore`, …) that compute the
  actual signals in SQL, and a `prune`.
- **`run.py`** — orchestration. A testable `run(...)` function with injected seams (fetch fns,
  `now_iso`, api key) + a thin `main(argv)` argparse wrapper. Skip-and-continue per item.
- **`catalog.py`** — the curated list of what to pull (FRED series ids, CFTC targets, EIA
  facets…) plus `select_ids(only, exclude, add)` selection helpers.

Exceptions to the four-file rule: `sources/monitors/market_calendar/compute.py` (pure
OPEX/holiday math), `sources/screeners/stock_analysis_screener/probe.py` + `typing.py`
(SvelteKit `__data.json` "devalue" decoder), `sources/screeners/usda_screener/wasde.py`.

### File tree

Every screener/monitor package lives under `sources/`, nested by kind:

```
sources/
├── common/       # screener_common.py, monitor_common.py, http_client.py
├── screeners/    # 16 point-in-time data readers (import screener_common)
└── monitors/     # 4 event-date calendars (import monitor_common)
```

`registry.py` and `main.py` stay at repo root — `registry.py` is the CLI dispatch table, not a
source itself. Import a screener/monitor's internals as `sources.screeners.<name>.<module>` /
`sources.monitors.<name>.<module>`.

### Shared spine

- **`registry.py`** (repo root) — `REGISTRY` dict maps name → each screener's `main`;
  `dispatch()` routes `main.py <name> [args...]`. **A screener "ships" only once registered
  here** (this is the source of truth for `docs/ROADMAP.md`).
- **`sources/common/screener_common.py`** — `connect()` (opens SQLite in **WAL** mode) and a
  generic snapshot cascade `prune()`.
- **`sources/common/monitor_common.py`** — the event-date **monitor framework**: a forward
  `events` table keyed `(event_type, event_date, subtype)`, `upsert_events` (dates firm up in
  place: tentative → confirmed), `replace_forward_window` (cancellation-aware; **never touches
  past events**), `v_upcoming`/`v_imminent` views, and a snapshot-only prune. Monitors
  (`econ_calendar`, `fomc`, `market_calendar`, `earnings`, and Treasury's
  `v_upcoming_auctions`) build on this.
- **`sources/common/http_client.py`** — bounded exponential-backoff `http_get` (honors
  `Retry-After`), `make_opener(headers)`, and a `RateLimiter` token bucket. Note the
  process-wide `SEC_RATE_LIMITER` (9 req/s) keyed on `SEC_HOST_KEY="sec.gov"` — **all** SEC
  fetchers (`edgar`, `ftd`, `fundamentals`) must acquire under that one key so the per-IP cap
  is shared, not doubled across `www.` / `data.` hosts.

### Data model conventions

- Every DB has a `snapshots` table (one row per run = provenance header). Domain rows are either
  **snapshot-scoped** (child rows FK to `snapshot_id`, pruned via the shared cascade) or
  **upsert-keyed history** (e.g. FRED `observations` keyed `(series_id, date)` — these are the
  historical store and are **NOT** snapshot-scoped; their `prune` deletes only old snapshot
  headers, never observations). Check `db.py`'s `prune` docstring before assuming a cascade.
- **ELT, not ETL**: store the raw/lightly-parsed data; compute signals (z-scores, YoY, regime
  flags, stocks-to-use, blackout windows) in SQL `v_*` views. Views `LEFT JOIN` so a partial
  `--only` run yields NULLs instead of erroring.

## Invariants (these repeat across the codebase — preserve them)

- **Determinism / no wall-clock in the hot path.** Time enters as an injected `now_iso` (UTC
  `isoformat()`) parameter. Monitor views filter on the `calendar_now.today` singleton row (set
  via `set_today(conn, now_iso)`), **never** `date('now')` — this is what makes tests reproducible.
- **No network in tests.** `fetch.py` functions take a `get=`/`opener=` seam and `run()` takes
  `fetch_*=` seams; tests inject fakes. The whole suite is offline — keep it that way.
- **Secret hygiene on errors.** A urllib `HTTPError` carries the request URL (which may embed
  `api_key`) in both its message and `.url`. On per-item failure: `conn.rollback()` then print
  **only** `type(e).__name__` — never `str(e)`, `repr(e)`, or `e.url`.
- **Prune correctness depends on fixed-width timestamps.** `prune` compares `captured_at` to a
  cutoff as a *plain string* (lexicographic `<`), which is only correct because every writer
  stores a UTC `isoformat()` (identical width incl. `+00:00`). Don't feed naive/differently
  formatted timestamps.
- **Live-verify source schemas.** External feeds routinely disagree with their own docs (CFTC
  Socrata `_all` suffix inconsistencies, FINRA positional column order, FRED release-ids). When
  adding/adjusting a fetcher, confirm field names/column positions against a real response — a
  wrong assumption silently drops rows rather than erroring.

## Workflow for a new screener/monitor

The repo follows **spec → plan → build**, all under `docs/`:

- `docs/ROADMAP.md` — parent tracker of every screener/monitor and its status (Built ✅ = in
  `registry.py`). Update it as work lands.
- `docs/superpowers/specs/<date>-<name>-design.md` — design spec (one per screener).
- `docs/superpowers/plans/<date>-<name>.md` — implementation plan.
- `docs/FOLLOWUPS.md` — deferred follow-ups, live endpoint-verification tasks, and the idea backlog.

**Data-source policy:** official primary sources only, with one approved exception —
**stockanalysis.com** (already trusted; used by `stocks` and `earnings`). `reddit` (ApeWisdom)
predates the policy and stays as-is.

Tests mirror the module layout: `tests/test_<name>_<layer>.py` where layer ∈
{`catalog`, `fetch`, `db_schema`, `db_write`, `db_views`, `run`}. Register the new `main` in
`registry.py` and add a `test_registry.py` entry.
