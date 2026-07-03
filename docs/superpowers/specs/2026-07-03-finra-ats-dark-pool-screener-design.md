# FINRA OTC / ATS (Dark Pool) Transparency Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [FINRA OTC Transparency](https://www.finra.org/filing-reporting/otc-transparency),
the FINRA Rule 6110/6610 program that publishes **weekly** over-the-counter /
dark-pool trading volume per security per ATS. Accessed via the **File Download
API** on `api.finra.org`, group `otcMarket` — the same anonymous query mechanics
as the Equity Short Interest POST API (JSON `compareFilters`, CSV or JSON via the
`Accept` header, no auth, no key). Downloadable weekly files also exist as a
fallback.
**Confidence:** 🟢 program semantics + access mechanics verified 2026-07-03;
🟡 the exact weekly-ATS dataset `name` values on the File Download API — confirm
live at implementation time.

## Goal

Pull FINRA's **OTC (ATS & Non-ATS) Transparency** data — how much of each
security's volume trades **off-exchange**, broken out **per dark pool** — into
SQLite, so the bot gains a **market-microstructure reader** it does not have
today: *which* ATSs (dark pools) trade a given name, *how much* of that name's
volume prints off-exchange, and how concentrated that off-exchange flow is across
venues.

This is a **new signal with no overlap** to any existing screener. The
short-volume and short-interest screeners read *shorting*; the COT screeners read
*futures positioning*; this reads **venue structure** — the ATS-vs-lit and
per-MPID composition of a stock's trading. It is the **ninth** screener in the
family, and it introduces a **weekly per-venue panel** shape.

## What this data is

- Under FINRA Rules **6110/6610**, ATSs and OTC-trading member firms report their
  over-the-counter trades to FINRA's equity trade-reporting facilities (the
  **TRFs**, the **ADF**, and the **ORF**). FINRA aggregates and publishes the
  resulting **weekly** volumes — **trade counts and share quantities** — **per
  security per ATS**, with each ATS identified by its **MPID**. Coverage spans
  **NMS Stocks** and **OTC Equity Securities**.
- The attributed ATS data answers "which dark pools trade this ticker, and how
  much." A parallel **non-ATS** (OTC member) series is published for the
  off-exchange volume that does *not* run through an ATS; **de-minimis** non-ATS
  volume is aggregated and published **non-attributed** (no MPID).
- This is a **venue-composition** signal, orthogonal to price and to shorting: it
  measures *where* a name trades, not its direction.

## Publication delay (structural — document prominently)

FINRA deliberately lags this data:

| Segment | Delay before publication |
|---|---|
| Tier-1 NMS stocks (most liquid) | **~2 weeks** |
| All other NMS stocks + OTC equity securities | **~4 weeks** |
| Non-ATS (monthly) | **~1 month** |

So the "latest" week this screener can ingest is **structurally weeks behind
today**. `run.py` must choose its fetch window with that lag built in — asking for
last week's file simply 404s. This is analogous to the short-interest
~8-business-day delay, only larger, and it is a *feature of the source*, not a
bug to route around.

## Source notes (confirmed 2026-07-03)

- **Access — the FINRA File Download / Query API**, `api.finra.org`, group
  `otcMarket`: `POST` a JSON body with `compareFilters` (e.g. `weekStartDate
  EQUAL 2026-06-08`), the `Accept` header selecting **CSV or JSON**. **No auth, no
  key** — the same anonymous mechanics as the `EquityShortInterest` POST API.
  🟡 The **weekly ATS dataset `name`(s)** (e.g. a weekly NMS-stock ATS dataset and
  a weekly OTC-equity ATS dataset) must be confirmed against the live API catalog
  at implementation time — the program is verified, the exact `name` slugs are
  not.
- **Downloadable weekly files** exist as a fallback for the same weekly data.
  Primary path is the query API (server-side week filter → one request per week);
  the flat files are a backfill/verification source.
- **POST, not GET** — a small departure from the CDN screeners. The fetch builds a
  closure that captures the JSON filter body and POSTs it, then funnels the call
  through the shared `http_client.http_get` backoff loop unchanged (see fetch).

## Data-shape classification: a *weekly per-venue panel*

A new shape — a **three-way panel**: `symbol × ATS(MPID) × week`.

- `cftc` is a `market × week` panel; this adds the **venue (MPID)** as a second
  panel axis, so the key is `(week_start, symbol, mpid)`.
- History is **not** snapshot-scoped; it accumulates `(week, symbol, mpid)` facts
  that persist across runs. A **replace-by-week** write (delete the week's rows,
  then bulk-insert) makes a FINRA re-post leave no orphan, exactly like
  `replace_day` / `replace_settlement`.

## Module layout (mirrors the FINRA screeners; POST-based fetch)

```
finra_ats/
    __init__.py
    fetch.py   # api.finra.org query API: POST compareFilters, parse CSV/JSON rows
    db.py      # schema (venues/ats_volume/weeks/snapshots) + views + FRED prune
    run.py     # week enumeration (delay-aware) + incremental orchestration + CLI
```

Plus:
- Register `"ats"` in `registry.py` (import `run.main as ats_main`).
- Nothing new in `.env.example` — **no credentials required.**

### `fetch.py`

- `week_body(week_start) -> dict` — the JSON `compareFilters` payload selecting one
  week (`weekStartDate EQUAL 'YYYY-MM-DD'`), plus any dataset-name/limit fields the
  API requires.
- `parse_rows(payload, fmt) -> list[dict]` — map each record to the curated column
  set (`week_start, symbol, mpid, ats_name, trade_count, share_quantity, tier`),
  coercing numeric strings to `int` and absent/blank cells to `None`. Handles the
  chosen response format (JSON list, or CSV via `csv.reader`); records missing a
  symbol or `week_start` are skipped. Non-attributed de-minimis rows (no MPID)
  are tagged with a sentinel MPID (e.g. `"NON_ATS_DEMINIMIS"`) so the PK holds.
- `fetch_week(week_start, get=_http_get, opener=None)` — POST + parse one week.
  Returns `rows`, or **`None` on HTTP 403/404** (week not yet published / absent),
  skipped by the runner. Bounded backoff retries `429/503` + transient network
  errors; 403/404 are non-retryable → `None`.
- **POST reuse of the backoff loop:** `http_client.http_get(url, opener, ...)`
  only calls `opener(url)`, so a closure that captures the request body and issues
  a POST (`urllib.request.Request(url, data=json_bytes, headers=..., method="POST")`)
  drops straight into the existing retry machinery — no change to `http_client`.
- Constants: `API_URL = "https://api.finra.org/data/group/otcMarket/name/{dataset}"`,
  descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`),
  `_RETRY_STATUS = frozenset({429, 503})`.

### `db.py` — schema

```sql
CREATE TABLE IF NOT EXISTS venues (        -- ATS/MPID dimension
    mpid        TEXT PRIMARY KEY,
    ats_name    TEXT,                        -- newest ATS name seen for this MPID
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS ats_volume (    -- the fact table (weekly per-venue panel)
    week_start      TEXT NOT NULL,           -- YYYY-MM-DD (weekStartDate)
    symbol          TEXT NOT NULL,
    mpid            TEXT NOT NULL REFERENCES venues(mpid),
    trade_count     INTEGER,
    share_quantity  INTEGER,
    tier            TEXT,                     -- T1 NMS / other NMS / OTC (drives the delay)
    PRIMARY KEY (week_start, symbol, mpid)
);
CREATE INDEX IF NOT EXISTS ix_ats_week   ON ats_volume(week_start);
CREATE INDEX IF NOT EXISTS ix_ats_symbol ON ats_volume(symbol);
CREATE TABLE IF NOT EXISTS weeks (         -- per-week provenance
    week_start TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (     -- per-run header
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    week_count  INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
```

### `db.py` — writes (mirror the FINRA screener names/semantics)

- `ensure_schema(conn)` — create tables, indexes, views. Idempotent.
- `upsert_venues(conn, rows)` — upsert the `mpid` dimension, refreshing `ats_name`
  to the newest seen and extending `first_seen`/`last_seen` to the min/max week.
- `replace_week(conn, week_start, rows) -> int` — **delete all `ats_volume` rows
  for that week, then bulk-insert** (replace, not upsert). Dedupe within the batch
  by `(week_start, symbol, mpid)`.
- `record_week(conn, week_start, fetched_at, row_count)` — upsert the `weeks`
  provenance row.
- `write_snapshot(conn, captured_at, week_count, row_count) -> id`.
- `stored_weeks(conn) -> list[str]` — ingested weeks, ascending.
- `prune(conn, keep_days, now_iso) -> int` — delete **snapshot headers only**
  older than `keep_days`; **never** touches `ats_volume` history (the FRED-style
  single-table prune used across the history-accumulating screeners).

### `db.py` — screening views (the microstructure payoff)

1. **`v_latest_off_exchange`** — for the newest stored week, off-exchange share by
   symbol: `SUM(share_quantity)` and `SUM(trade_count)` across all venues per
   symbol, ordered descending. The "which names trade most off-exchange right now"
   board. (When a lit/consolidated reference is available it can be joined to a
   true off-exchange %; absent that, total ATS share volume is the ranking key.)
2. **`v_top_dark_pools`** — venues ranked by total `share_quantity` on the newest
   week, joined to `venues` for `ats_name`. The "biggest dark pools this week"
   leaderboard.
3. **`v_symbol_venue_history`** — per-`(symbol, mpid)` weekly time series
   (`week_start, trade_count, share_quantity, ats_name`) for drill-down into how a
   name's venue mix shifts over time.

### `run.py` — orchestration + CLI

- Enumerate **weeks** (`weekStartDate`, Monday-anchored) from `--start` (default:
  **~6 months back**) through the **most recent week the publication delay allows**
  — i.e. no more recent than ~2 weeks ago for Tier-1 and ~4 weeks for the rest, so
  the runner does not chase weeks that structurally cannot exist yet. For each:
  skip if already stored, **except** re-fetch the trailing `_REFETCH_WEEKS = 2`
  stored weeks so FINRA re-posts are re-absorbed by `replace_week`. `--full`
  re-ingests every week in range.
- `fetch_week` returning `None` (403/404 — not-yet-published / absent) is skipped
  silently. Any per-week exception rolls back that week's uncommitted writes and
  continues, logging **only `type(e).__name__`** (never `str(e)` / `e.url`) — the
  repo-wide secret-hygiene rule.
- After the loop: `write_snapshot`, then `prune` if `--keep-days` given.
- Returns `(snapshot_id, week_count, row_count)`.
- A `weeks_in_range(start, end)` helper enumerates Monday week-starts (the
  analogue of `days_in_range`), so enumeration is unit-testable without the
  network.
- **CLI** (`prog="ats"`):
  - `--db` (default `finra_ats.db`)
  - `--start YYYY-MM-DD` (default: ~6 months back)
  - `--full` (re-ingest every week in range)
  - `--keep-days N` (prune snapshot provenance only)

## Defaults (approved)

- **Lookback:** ~6 months (≈26 weeks, ≈26 requests) — enough weekly history to see
  a venue-mix shift; extend via `--start`.
- **Delay-aware end:** the newest fetched week is floored by the ~2/~4-week
  publication delay so the runner does not repeatedly 404 on the current weeks.
- **Retention:** keep all `ats_volume` history; `--keep-days` prunes only
  run-provenance snapshots — never the facts.
- **Scope:** the weekly **ATS** (attributed dark-pool) datasets are primary;
  the **monthly non-ATS** series is out of scope for the first cut (a clean future
  add — its ~1-month delay and non-attributed de-minimis handling differ).

## Testing (mirror the other FINRA screeners)

- `test_finra_ats_fetch.py` — `parse_rows` over both CSV and JSON fixtures
  (numeric coercion, blanks → `None`, non-attributed de-minimis MPID sentinel,
  symbol/week guards); `week_body` payload shape; `fetch_week` POST via an
  injected fake opener and 403/404 → `None`. **Network never hit.**
- `test_finra_ats_db_schema.py` — `ensure_schema` idempotent; tables, indexes, and
  the three documented views exist.
- `test_finra_ats_db_write.py` — `upsert_venues` ats-name refresh + first/last_seen;
  `replace_week` replaces (repost dropping a venue leaves no orphan) and dedupes by
  `(week_start, symbol, mpid)`; `record_week`/`write_snapshot`/`stored_weeks`;
  `prune` removes snapshot headers only and leaves facts intact.
- `test_finra_ats_db_views.py` — `v_latest_off_exchange` newest-week aggregation
  and ordering; `v_top_dark_pools` venue ranking + `ats_name` join;
  `v_symbol_venue_history` per-venue series on seeded data.
- `test_finra_ats_run.py` — delay-aware week enumeration + incremental skip +
  trailing-refetch + `--full`, with injected `fetch_week` (including a `None`/404
  week) and pinned `now_iso`; asserts counts, that a skipped week is not
  re-fetched, and the **secret-hygiene** assertion that a raising week logs the
  exception **class** to stderr but **not** its message.
- `test_registry.py` — extend to assert `"ats"` dispatches.

## Non-goals (YAGNI)

- **Monthly non-ATS** (OTC member, non-dark-pool) series — a clean future add;
  the weekly attributed ATS data is the target signal.
- **True off-exchange %** against a consolidated/lit volume reference — requires a
  separate volume feed; `v_latest_off_exchange` ranks by ATS share volume until
  one is wired in.
- **Real-time / low-latency** consumption — pointless against a source that is
  structurally 2–4 weeks delayed.
- **Symbol curation** — the feed is full-universe per week; no catalog is needed
  (unlike CFTC/FRED), so no `catalog.py`.
- Merging with the shorting screeners — independent DB; consumers correlate venue
  structure against shorting/positioning in the bot, not in a view.

## Environment

**No new variables** — the FINRA query API is anonymous. `.env.example` is
unchanged.
