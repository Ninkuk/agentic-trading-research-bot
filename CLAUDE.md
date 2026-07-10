# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A signal-collection layer for a trading bot: ~20 independent **screeners** (point-in-time data
readers) and event-date **monitors** (forward-looking calendars) that each fetch one official
data source (SEC, FRED, CFTC, FINRA, CBOE, Treasury, NY Fed, EIA, USDA, …) into a per-source
SQLite database, then derive signals in SQL views.

**Zero runtime third-party dependencies** — everything is stdlib (`urllib`, `sqlite3`, `json`,
`argparse`). Python 3.12, managed with `uv`. The only dev dependency is `pytest`.

## Commands

```bash
# Run a screener/monitor (dispatched by name; see registry.py for the names)
uv run python main.py fred --db data/fred.db --keep-days 90   # DBs live in data/
uv run python main.py cftc --family disaggregated
uv run python main.py --list          # print all registered dispatcher names
# NOTE: every --db default is a bare cwd-relative filename (e.g. fred.db); always pass
# data/<name>.db or you'll create a stray DB at repo root.

# Tests (fully offline — no network, no real API keys needed)
uv run pytest                          # full suite (~1150 tests, ~2s)
uv run pytest tests/test_fred_run.py   # one file
uv run pytest -k regime                # by name substring
uv run pytest tests/test_fred_run.py::test_run_upserts_observations  # single test

# Reverse DCF: what annual return does today's price already imply?
uv run python -m tools.valuation.reverse_dcf \
  --market-cap 1000 --base-fcf 100 --growth 0.05 0.05 0.05 --terminal-growth 0.02
# exit 0 solved · 1 no solution in (g, 1.0) · 2 refused input

# Lint / format / types (config in pyproject.toml; all must pass before commit)
uv run ruff check                      # lint (add --fix for autofixes)
uv run ruff format                     # format in place (--check to only verify)
uv run mypy                            # type-check sources/, main.py, registry.py

# Dependencies are stdlib-only by design (ruff/mypy/pytest are dev-group only).
# Avoid adding runtime deps; if genuinely unavoidable, add via `uv add` and
# justify it (it breaks the "plain checkout" property).
```

The pre-commit hook (`.githooks/pre-commit`) runs all four gates in ~2s. It's wired via
`core.hooksPath`; on a fresh clone run `git config core.hooksPath .githooks` once.
Bypass an intentionally-red WIP commit with `git commit --no-verify`.

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

One inverted slice: `portfolio` has no network in `fetch.py` at all — live Robinhood
state is fetched by Claude via MCP (see `.claude/skills/account-positions`) and piped in
as JSON via `main.py portfolio --input <file|->`. Live account state enters the system
only through that dispatcher; never write SQL against `portfolio.db` directly.

**Combiners are the third source kind.** Unlike screeners/monitors, a combiner's `fetch.py`
never touches the network — it reads the other `data/*.db` files ATTACHed read-only and
derives a cross-source view (e.g. `composite`: a market regime + a per-ticker scorecard). It
binds its own `:today` instead of reading a source's `calendar_now`-dependent views (monitor
`v_upcoming`/`v_imminent`, `treasury.v_upcoming_auctions`, `fred.v_asof`), so it stays on one
clock without depending on any single source's calendar state. Otherwise it ships like any
other source: registered in `registry.py`, dispatched via `main.py composite ...`. The
`scorer` combiner grades composite opinions against forward returns and never feeds back —
re-weighting the catalog is a human decision made by reading `v_signal_efficacy`/
`v_bucket_performance`. The scorer package also owns the decision journal (`main.py journal --input <file|->`, fed by the
`.claude/skills/journal-sync` MCP skill like `portfolio`): human fills and passes land in scorer.db `decisions` (never pruned) and are compared to
paper outcomes in `v_decision_outcomes`/`v_flag_response`/`v_human_filter`.
The `advisor` combiner joins the latest scorecard against real holdings
(portfolio.db read-only: `v_latest_*` views plus the `snapshots` header
timestamp) plus stocks/etfs ATR and scorer
efficacy: book heat, disagreements, and vol-scaled size caps — decision
support only, never order generation.
The `backtest` combiner replays composite's FRED/market signals against ALFRED vintages
(point-in-time — `publication_lag_days` keeps a report out of the replay until it was actually
released) and grades them in `v_replay_efficacy`. Read `excess`/`beats_baseline` there, never
`hit_rate` alone — the benchmarks drift upward, so a bullish flag "wins" by doing nothing;
`v_benchmark_baseline` is the null to compare against, and the flags are nominal and
uncorrected across ~48 comparisons. Weekly (Sat, after `fred-vintages`). Two read-only
reporters ship alongside:
`main.py scorecard` (grades the human's decisions from the journal views; SELECT-only) and
`main.py pricehistory` (manual one-shot ledger backfill — never scheduled).

### File tree

Every screener/monitor package lives under `sources/`, nested by kind:

```
sources/
├── common/       # screener_common.py, monitor_common.py, http_client.py
├── screeners/    # 17 point-in-time data readers (import screener_common)
├── monitors/     # 4 event-date calendars (import monitor_common)
└── combiners/    # 4 cross-source combiners (composite: opinions; scorer: grades;
                  #   advisor: sizes; backtest: point-in-time replay)
```

`registry.py` and `main.py` stay at repo root — `registry.py` is the CLI dispatch table, not a
source itself. Import a screener/monitor/combiner's internals as `sources.screeners.<name>.<module>` /
`sources.monitors.<name>.<module>` / `sources.combiners.<name>.<module>`.

`tools/` holds code that is neither a source nor a dispatcher — pure helpers with no
network, no DB, and no clock. Today: `tools/valuation/reverse_dcf.py`, the bisection
solver behind the `research-ticker` skill. Not registered in `registry.py`; it is not
a data pipeline.

### Shared spine

- **`registry.py`** (repo root) — `REGISTRY` dict maps name → each screener's `main`;
  `dispatch()` routes `main.py <name> [args...]`. **A screener "ships" only once registered
  here.**
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

- **Timestamps are UTC; calendar dates are Phoenix.** Never slice a date out of a timestamp
  (`now_iso[:10]`) — always `phx_date(now_iso)` from `sources/common/clock.py`. UTC midnight is
  17:00 Phoenix and eight launchd jobs run after it (cboe_stats 6pm .. daily-summary 9:15pm), so
  `[:10]` yields *tomorrow* for every one of them. `composite` stamps `obs_date` on the Phoenix
  date and `journal` matches fills on it; anything comparing against those must agree or ages
  come out a day high and a fill can appear to precede the opinion it answered. The offset is a
  bare `timedelta(hours=7)` only because America/Phoenix has no DST — an ET-anchored clock could
  not do this. Test fixtures for evening jobs must straddle the rollover (e.g.
  `2026-07-08T04:12:00+00:00`, not `...T21:12:00+00:00`) or they cannot catch a mixup.
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

The repo follows **spec → plan → build**. Design specs are transient working docs under
`docs/superpowers/specs/<date>-<name>-design.md`. Implementation plans are **checked in** at
`plans/<NNN>-<name>.md`, indexed by a status table in `plans/README.md` (TODO | IN PROGRESS |
DONE | BLOCKED | REJECTED) — they persist after shipping and record what adversarial review
broke, which is often the most useful thing in them.

**Everything runs on a launchd schedule** — see `docs/SCHEDULE.md` (durable reference:
per-job slots, scheduling constraints, ops). Source of truth is `deploy/launchd/install.py`;
after changing a screener's cadence assumptions, update both.

**Data-source policy:** official primary sources only, with one approved exception —
**stockanalysis.com** (already trusted; used by `stocks` and `earnings`). `reddit` (ApeWisdom)
predates the policy and stays as-is. `portfolio` is account state (Robinhood via MCP),
not a market data source, so the policy doesn't apply to it.

Tests mirror the module layout: `tests/test_<name>_<layer>.py` where layer ∈
{`catalog`, `fetch`, `db_schema`, `db_write`, `db_views`, `run`}. Register the new `main` in
`registry.py` and add a `test_registry.py` entry.

**Research output:** `research/` holds theses and analyses generated by the `research-ticker`
skill. Nothing in `sources/` reads it — it is human-facing only.
