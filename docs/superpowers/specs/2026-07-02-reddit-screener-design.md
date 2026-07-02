# Reddit Sentiment Screener (ApeWisdom) — Design

**Date:** 2026-07-02
**Status:** Approved, ready for implementation planning
**Data source:** [ApeWisdom API](https://apewisdom.io/api/) — `https://apewisdom.io/api/v1.0/filter/{filter}/page/{n}`

## Goal

Pull Reddit/4chan stock-and-crypto mention data from ApeWisdom into SQLite as a
time-series, so the trading bot can query sentiment **momentum** (rising mentions,
climbing rank, upvote conviction) — not just a static leaderboard.

This is the second screener in what will become a **family** of screeners. The
design therefore also introduces the shared CLI seam (a registry + dispatcher)
that future screeners plug into.

## Guiding principles

- **Store raw, derive in views (ELT).** Snapshots are the immutable source of
  truth; every signal is a SQL view that can be rewritten later without losing or
  re-fetching data.
- **Static schema.** Unlike the stock screener, ApeWisdom returns a fixed 7-field
  shape. No dynamic-column / data-point-catalog machinery is needed.
- **One entry point for a family of screeners** via a lightweight registry.
- **Rule of three:** do NOT extract a shared `Screener` base class yet. The two
  existing screeners are genuinely different shapes; wait for the third before
  abstracting internals. Only the CLI dispatch layer is shared now.
- **Reuse proven patterns** from `screener/`: snapshot + prune, dependency
  injection into `run()`, TDD.

## The API (verified 2026-07-02)

- **Endpoint:** `https://apewisdom.io/api/v1.0/filter/{filter}/page/{pageNbr}`
- **Response:** `{count, pages, current_page, results: [ {row}, ... ]}`, 100
  results per page.
- **Row fields:** `rank, ticker, name, mentions, upvotes, rank_24h_ago,
  mentions_24h_ago`.
- **Filters:** `all`, `all-stocks`, `all-crypto`, `4chan`, `CryptoCurrency`,
  `CryptoCurrencies`, `Bitcoin`, `SatoshiStreetBets`, `CryptoMoonShots`,
  `CryptoMarkets`, `stocks`, `wallstreetbets`, `options`, `WallStreetbetsELITE`,
  `Wallstreetbetsnew`, `SPACs`, `investing`, `Daytrading`.

**Empirically confirmed quirks (must be handled):**

1. **Type inconsistency.** Live pages return numeric fields as `int`; the docs
   example shows them as strings. The fetcher MUST coerce numeric fields to
   `int` defensively.
2. **Nulls for new entrants.** `rank_24h_ago` / `mentions_24h_ago` can be absent
   for tickers new to the board. Coercion must tolerate `None` (store as NULL).
3. **HTML entities in names.** e.g. `SPDR S&amp;P 500`, `Wendy’s`. Names are
   `html.unescape`'d once at ingest.
4. **Crypto ticker suffix.** Crypto tickers carry a `.X` suffix (`BTC.X`), used to
   classify `asset_type`.

## Default boards

Default pull each run: **`all-stocks`** and **`4chan`**. Overridable via
`--filters`. (`all-stocks` is the core aggregate stock signal; `4chan` /biz is a
distinct, early-signal community.)

## Module structure

New self-contained package `reddit_screener/`, parallel to `screener/`:

```
reddit_screener/
    __init__.py
    fetch.py     # paginated fetch of one filter; type coercion; name unescape
    db.py        # static schema + views; write_snapshot; prune
    run.py       # orchestrate multi-filter fetch -> write; the registered run fn
```

**Shared CLI seam** (the only thing shared between screeners for now):

```
main.py          # thin dispatcher: `python main.py <name> [args...]`, `--list`
screeners.py     # (or a dict in main.py) registry: name -> run/main callable
```

- `main.py` refactored to route subcommands: `main.py stocks ...` (existing
  screener, behaviour unchanged) and `main.py reddit ...` (new).
- `main.py --list` prints registered screeners.
- Each screener keeps its own `run.py`/argument parser; the dispatcher only
  selects which one to invoke and forwards remaining argv.

## Data model

### Tables

```sql
CREATE TABLE snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,     -- ISO-8601 UTC
    filter       TEXT NOT NULL,     -- board, e.g. 'all-stocks'
    ticker_count INTEGER NOT NULL   -- rows stored for this (filter, capture)
);

CREATE TABLE observations (
    snapshot_id       INTEGER NOT NULL REFERENCES snapshots(id),
    ticker            TEXT NOT NULL,
    name              TEXT,
    rank              INTEGER,
    mentions          INTEGER,
    upvotes           INTEGER,
    rank_24h_ago      INTEGER,      -- nullable
    mentions_24h_ago  INTEGER,      -- nullable
    PRIMARY KEY (snapshot_id, ticker)
);
CREATE INDEX ix_observations_ticker ON observations(ticker);

CREATE TABLE tickers (
    ticker      TEXT PRIMARY KEY,
    name        TEXT,               -- latest clean (unescaped) name
    asset_type  TEXT,               -- 'crypto' if ticker ends in '.X', else 'stock'
    first_seen  TEXT,               -- ISO capture of first observation
    last_seen   TEXT                -- ISO capture of most recent observation
);
```

- One `snapshots` row per `(filter, run)`. A run pulling 2 filters writes 2
  snapshot rows sharing one `captured_at`.
- `observations` is the immutable fact table.
- `tickers` is a small dimension upserted each run: deduped clean name, asset
  classification, and first/last-seen for "new arrival" detection.

### Derived-signal views ("rich" lives here)

- **`v_latest`** — rows from the most recent snapshot **per filter**.
- **`v_signals`** — `v_latest` plus computed columns, using the API's 24h-ago
  fields:
  - `mention_delta = mentions - mentions_24h_ago`
  - `mention_pct_change = (mentions - mentions_24h_ago) / mentions_24h_ago` (NULL
    when `mentions_24h_ago` is NULL or 0)
  - `rank_delta = rank_24h_ago - rank` (positive = climbing toward rank 1)
  - `upvote_ratio = upvotes / mentions` (NULL when `mentions` is 0)
- **`v_trending`** — `v_signals` ordered by `mention_pct_change DESC` (biggest
  movers first), NULL pct changes excluded.
- **`v_history`** — a ticker's full time-series across snapshots (same filter),
  ordered by `captured_at`, with deltas computed **between consecutive stored
  snapshots** via `LAG(...)` window functions — more accurate than the API's
  fixed 24h-ago once local history accrues.

All views are created idempotently (`CREATE VIEW IF NOT EXISTS`) alongside the
schema.

## Fetch behaviour (`reddit_screener/fetch.py`)

- `fetch_filter(filter, url_base=...) -> list[dict]`:
  1. GET page 1, read `pages`.
  2. Loop pages `1..pages`, accumulate `results`.
  3. For each row: coerce `rank, mentions, upvotes, rank_24h_ago,
     mentions_24h_ago` to `int` (tolerating `None`), `html.unescape` the `name`.
  4. Return the normalised list of dicts.
- Pure parsing (`parse_page(raw) -> (rows, total_pages)`) is separated from the
  HTTP call so it can be unit-tested against fixtures without network.
- Uses `urllib` + a `User-Agent` header, matching the existing screener's
  dependency-free approach (no new packages).

## Orchestration (`reddit_screener/run.py`)

`run(db_path, filters, keep_days=None, fetch_filter=fetch.fetch_filter,
now_iso=None) -> list[(snapshot_id, count)]`:

1. `captured_at = now_iso or datetime.now(timezone.utc).isoformat()` (shared
   across all filters in this run).
2. `conn = db.connect(db_path); db.ensure_schema(conn)`.
3. For each filter: `rows = fetch_filter(filter)`;
   `db.write_snapshot(conn, captured_at, filter, rows)`;
   `db.upsert_tickers(conn, rows, captured_at)`.
4. If `keep_days is not None`: `db.prune(conn, keep_days, captured_at)`.
5. Return list of `(snapshot_id, ticker_count)` per filter.

`fetch_filter` is injected for testability (mirrors the stock screener's DI).

CLI (`main` in `run.py`, invoked via the dispatcher):
`--db reddit.db` · `--filters all-stocks,4chan` (default) · `--keep-days N`
(default None = keep all).

## Error handling

- **HTTP / network failure on a filter:** the exception propagates and aborts the
  run. Because each filter commits its own `write_snapshot` + `upsert_tickers`,
  filters processed *before* the failure stay persisted; the failing filter and
  those after it are not written. This partial-run outcome is acceptable for a
  scheduled job and is documented, not silently swallowed. The failing filter
  leaves no snapshot row (its write never began).
- **Empty results for a filter:** write a snapshot with `ticker_count = 0` and
  emit a `warning: filter '{f}' returned 0 tickers` to stderr (mirrors the stock
  screener's short-universe warning). The run does not abort.
- **Malformed payload** (missing `results`/`pages`): `parse_page` raises
  `ValueError` with a clear message.

## Retention

Reuse the `prune(keep_days, now_iso)` pattern: delete `observations` +
`snapshots` older than `keep_days` before `now_iso`. `tickers.first_seen` is left
intact (historical provenance). Default: keep all (no prune unless `--keep-days`).

## Testing (TDD, mirrors existing `tests/`)

- `test_reddit_fetch.py` — `parse_page` against fixtures: type coercion
  (string→int), null `*_24h_ago`, HTML-entity unescape, multi-page accumulation,
  malformed-payload `ValueError`.
- `test_reddit_db_schema.py` — `ensure_schema` idempotent; all tables + 4 views
  exist; re-running is a no-op.
- `test_reddit_db_write.py` — `write_snapshot` stores rows keyed by
  `(snapshot_id, ticker)`; `ticker_count` correct; `upsert_tickers` sets
  asset_type from `.X`, updates `last_seen`, preserves `first_seen`; view math
  (`v_signals` deltas/ratios, NULL guards for zero/NULL denominators).
- `test_reddit_run.py` — `run()` with injected `fetch_filter`: multi-filter
  single-capture, empty-filter warning + zero-count snapshot still written,
  `keep_days` prune, second-run append (history grows), HTTP-failure leaves no
  snapshot for the failing filter.
- `test_registry.py` — dispatcher routes `stocks`/`reddit`, `--list` output,
  unknown name errors cleanly, existing `stocks` path unchanged.

Live smoke (manual, like the stock screener's 5591-row check): pull `all-stocks`
+ `4chan` into a temp DB, assert non-zero rows and numeric `v_signals` output.

## Out of scope (YAGNI)

- Shared `Screener` base class / protocol — deferred to screener #3 (rule of
  three).
- Sentiment scoring / NLP beyond the mention/upvote counts the API provides.
- Joining Reddit tickers to the stock screener's fundamentals (a future
  cross-screener query, not this module).
- Incremental/delta fetch — the API has no cursor; full pull per run is fine at
  this size (~1–11 pages per filter).
- Auth / API keys — the v1.0 endpoint is public and unauthenticated.
```
