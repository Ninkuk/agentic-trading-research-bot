# SEC EDGAR Filing-Activity Screener — Design

**Date:** 2026-07-02
**Status:** Approved, ready for implementation planning
**Data source:** [SEC EDGAR daily-index](https://www.sec.gov/Archives/edgar/daily-index/) —
`https://www.sec.gov/Archives/edgar/daily-index/{yr}/QTR{n}/master.{YYYYMMDD}.idx`
plus the [CIK→ticker map](https://www.sec.gov/files/company_tickers.json).

## Goal

Pull the SEC EDGAR daily filing feed into SQLite as a time-series so the trading
bot can screen on **filing activity** — insider trades, material events, activist
stakes, and new offerings — the day they hit EDGAR.

This is the **third** screener in the family. Per the "rule of three" flagged in
the reddit spec, this design also decides how much (little) shared machinery to
extract.

## Key realization (why this is an *events* screener)

The daily-index is an **events feed**; XBRL financials are **quarterly facts**.
Companies don't refile a balance sheet every day, so a *daily* screener is
naturally a *filing-activity* screener. Fundamentals are a slower, separate
cadence and belong to a future screener — not this one. Trying to make one job
serve both fights the grain of the data.

## Source verification (all confirmed first-hand 2026-07-02, HTTP 200)

The user originally cited `form.{date}.idx`. That URL is correct, but **all five
sibling files in a daily-index QTR directory carry the same set of filings** —
they differ only in format, sort order, and columns:

| File | Size | Format | Key columns | Verdict |
|---|---|---|---|---|
| **master.idx** | **439 KB** | pipe-delimited | `CIK \| Company \| Form \| Date \| path.txt` | **Chosen** — smallest, trivial parse, has CIK |
| form.idx *(original)* | 995 KB | fixed-width | same, sorted by form | Same data, 2× bigger, brittle column-offset parse |
| company.idx | 750 KB | fixed-width | same, sorted by name | No unique value |
| crawler.idx | 924 KB | fixed-width | gives `-index.htm` landing URL | URL is derivable from master's `path` |
| sitemap.xml | 1.1 MB | XML | only URLs + `lastmod` | Useless for screening — no CIK/form/company |

**Decision: use `master.idx`.** From its `path` column
(`edgar/data/1000623/0001562180-25-004291.txt`) both the **accession number**
(`0001562180-25-004291`) and crawler's `-index.htm` URL are derivable, so master
subsumes the other four at the smallest size and easiest parse (`line.split("|")`).

**Empirically confirmed facts that shape the design:**

1. **SEC requires a declared `User-Agent`** with contact info (a generic client
   gets `403`). Fair-access policy caps clients at ~10 requests/sec. A run makes
   only ~1–6 requests (one ticker map + a few index probes), so this is
   comfortable. UA: `agentic-trading-bot ninadk.dev@gmail.com`.
2. **Form 4 rows are listed under the ISSUER's CIK** (e.g. `1000623 → Mativ
   Holdings → MATV`), not the individual insider's. So the CIK→ticker join works
   directly for insider trades — the highest-value signal. (Verified against
   Mativ/MATV, Riley/REPX.)
3. **The CIK→ticker map has occasional gaps** (e.g. Sealed Air came back
   untickered despite being public). Unjoined filings are stored with
   `ticker = NULL`, not dropped; they can be enriched later.
4. **8-K item codes and Form 4 dollar amounts are NOT in any index file.** They
   live in the `submissions` API / filing XML. Index-only Phase 1 therefore
   classifies by **form type** (rich in breadth); item-code / amount **depth** is
   a deferred Phase 1.5 enrichment. This is a deliberate, documented boundary —
   not an oversight.

## Guiding principles

- **Store raw, derive in views (ELT).** Snapshots are the immutable source of
  truth; every signal is a SQL view that can be rewritten without re-fetching.
- **Static schema.** The index row shape is fixed (CIK, company, form, date,
  path) — no dynamic-column / data-point-catalog machinery (unlike `stock_analysis_screener/`).
- **Dependency-free.** `urllib` + stdlib only, matching both existing screeners.
- **Reuse proven patterns** from `reddit_screener/`: snapshot → observation →
  dimension, `prune`, dependency injection into `run()`, TDD.

## Rule of three — minimal shared code, no base class

A filing event is not shaped like a ranked-mention ticker, so a shared
`Screener` base class would be an awkward fit. Instead extract only the two
genuinely-duplicated pieces into a small module:

```
screener_common.py
    connect(path) -> sqlite3.Connection      # the WAL-mode pragma, identical in reddit/edgar
    prune(conn, keep_days, now_iso, *, child_table, child_fk="snapshot_id") -> int
        # delete snapshots older than keep_days, cascading to their child rows first
```

`prune` is cascade-aware because both screeners have a two-table
snapshot→child shape: it deletes the child rows (`child_table` where `child_fk`
points at the doomed snapshot ids) *before* the parent `snapshots` rows, in one
transaction. reddit passes `child_table="observations"`, edgar passes
`child_table="filings"`.

`reddit_screener` and `edgar_screener` both call these. Schemas, fetchers, and
views stay per-screener. The existing CLI dispatcher (`registry.py`) is already
the shared entry point. `stock_analysis_screener/` (stocks) is a different shape and is left
untouched.

> Migrating `reddit_screener` onto `screener_common` is a small, optional
> refactor. It is **in scope** for this work (it's the point of the rule-of-three
> extraction) but must leave reddit's behaviour and tests unchanged.

## Module structure

New self-contained package `edgar_screener/`, parallel to the others:

```
edgar_screener/
    __init__.py
    fetch.py   # ticker map load; master.idx download + parse; form classification
    db.py      # schema + ELT views; write_snapshot; upsert_issuers
    run.py     # resolve date -> fetch -> classify -> join -> write; registered run fn
```

Registered in `registry.py`: `"edgar": edgar_main` (alongside `stocks`, `reddit`).

## Fetch behaviour (`edgar_screener/fetch.py`)

Pure parsers are separated from HTTP calls so they unit-test against fixtures
without network.

- `parse_master(text) -> list[dict]`
  - Skip the header block (lines through the `---...` divider).
  - Split each remaining non-empty line on `|` into
    `cik, company, form, filed_date, path`.
  - Derive `accession` from `path` (basename without `.txt`).
  - Malformed lines (wrong field count) are skipped and counted, not fatal.
  - `filed_date` normalized `YYYYMMDD` → `YYYY-MM-DD`.
- `classify(form) -> str` — map raw form type to a signal bucket:
  - `insider`  ← `4`, `4/A`
  - `event`    ← `8-K`, `8-K/A`
  - `stake`    ← `SC 13D`, `SC 13D/A`, `SC 13G`, `SC 13G/A`
  - `offering` ← `S-1`, `S-1/A`, `424B*` (prefix match)
  - `periodic` ← `10-K`, `10-K/A`, `10-Q`, `10-Q/A`
  - `other`    ← everything else
- `fetch_ticker_map(url=...) -> dict[int, dict]` — GET `company_tickers.json`,
  return `{cik: {"ticker": ..., "title": ...}}`.
- `index_url(index_date) -> str` — build the `master.{YYYYMMDD}.idx` URL from a
  date, computing the correct `QTR{n}` (`month → (month-1)//3 + 1`).
- `fetch_daily_index(index_date, get=_http_get) -> list[dict] | None` — GET the
  index for a date; return parsed rows, or `None` on `404` (no filings that day).
- Single `User-Agent` header with contact info on every request.

## Date resolution (`edgar_screener/run.py`)

- Explicit `--date YYYY-MM-DD` → fetch exactly that day; a `404` raises a clear
  `"no EDGAR index for {date}"` error (the user asked for a specific day).
- Default (no `--date`) → **walk back** from `now`'s date up to 5 days, using the
  first day whose index exists. Skips weekends/holidays cheaply (≤5 small GETs).
  If none of the last 5 days has an index, raise a clear error.
- `now_iso` is injected (like the other screeners) so date resolution is
  deterministic in tests.

## Data model

### Tables

```sql
CREATE TABLE snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,   -- ISO-8601 UTC: when the run executed
    index_date   TEXT NOT NULL,   -- the filing day pulled (YYYY-MM-DD)
    filing_count INTEGER NOT NULL -- rows stored for this snapshot
);

CREATE TABLE filings (            -- immutable fact table
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    accession   TEXT NOT NULL,    -- e.g. 0001562180-25-004291
    cik         INTEGER NOT NULL,
    company     TEXT,
    ticker      TEXT,             -- joined from company_tickers.json; NULL if untickered
    form        TEXT NOT NULL,    -- raw form type, e.g. '8-K'
    bucket      TEXT NOT NULL,    -- insider|event|stake|offering|periodic|other
    filed_date  TEXT NOT NULL,    -- YYYY-MM-DD
    path        TEXT NOT NULL,    -- edgar/data/<cik>/<accession>.txt
    PRIMARY KEY (snapshot_id, accession, cik)
);
CREATE INDEX ix_filings_ticker ON filings(ticker);
CREATE INDEX ix_filings_bucket ON filings(bucket);

CREATE TABLE issuers (            -- dimension, upserted each run
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,
    company    TEXT,
    first_seen TEXT,              -- ISO capture of first observation
    last_seen  TEXT               -- ISO capture of most recent observation
);
```

- One `snapshots` row per run (one `index_date`).
- `filings` is the immutable fact table. A single accession can list under
  multiple CIKs, hence the composite PK `(snapshot_id, accession, cik)`.
- `issuers` is upserted each run: latest ticker/company, first/last-seen for
  "new filer" detection. `first_seen` is preserved on conflict.

### Derived-signal views ("rich" lives here)

All `CREATE VIEW IF NOT EXISTS`, created with the schema:

- **`v_latest`** — every filing from the most recent snapshot.
- **`v_tickered`** — `v_latest` where `ticker IS NOT NULL` (tradeable universe).
- **`v_insider_activity`** — latest snapshot, `bucket='insider'`, `COUNT(*)` per
  `ticker` ordered desc → insider **cluster** detection.
- **`v_events`** — latest `bucket='event'` (8-K) filings per ticker.
- **`v_stakes`** — latest `bucket='stake'` (13D/13G) filings.
- **`v_offerings`** — latest `bucket='offering'` (S-1 / 424B) filings.
- **`v_activity_history`** — filings-per-`(ticker, index_date)` across all stored
  snapshots, with `LAG()` deltas → filing-activity **spikes** over time (more
  accurate than a single day once local history accrues).

## Write behaviour (`edgar_screener/db.py`)

- `ensure_schema(conn)` — create tables + views idempotently.
- `write_snapshot(conn, captured_at, index_date, rows) -> (snapshot_id, count)` —
  insert one snapshot header + its filing rows via `executemany`.
- `upsert_issuers(conn, rows, captured_at)` — upsert `issuers`: refresh
  ticker/company/last_seen, preserve first_seen (`ON CONFLICT(cik) DO UPDATE`).
- `connect` / `prune` come from `screener_common`.

## Orchestration (`edgar_screener/run.py`)

`run(db_path, index_date=None, keep_days=None, fetch_index=fetch.fetch_daily_index,
     fetch_map=fetch.fetch_ticker_map, now_iso=None) -> (snapshot_id, count)`:

1. Resolve `index_date` (explicit, or walk-back to latest available).
2. `tmap = fetch_map()`.
3. `rows = fetch_index(index_date)`.
4. For each row: `bucket = classify(form)`; attach `ticker` from `tmap.get(cik)`.
5. `conn = connect(db_path); ensure_schema(conn)`.
6. `write_snapshot(...)`; `upsert_issuers(...)`.
7. If `keep_days is not None`: `prune(conn, keep_days, captured_at, child_table="filings")`.
8. Return `(snapshot_id, filing_count)`.

Fetchers are injected for testability (mirrors the other screeners' DI).

CLI (`main` in `run.py`, invoked via the dispatcher):
`--db edgar.db` · `--date YYYY-MM-DD` (default: latest available) ·
`--keep-days N` (default None = keep all).

## Error handling

- **Ticker-map fetch failure:** aborts the run — the CIK→ticker join is core, and
  a run without it would silently store an all-NULL-ticker snapshot. Fail loud.
- **Index `404` on an explicit `--date`:** raise `"no EDGAR index for {date}"`.
- **Index `404` in default mode:** walk back up to 5 days; if all miss, raise.
- **Malformed index line:** skipped and counted; the run continues.
- **Empty (but present) index:** write a snapshot with `filing_count = 0` and warn
  on stderr (mirrors the reddit screener's zero-count behaviour).

## Retention

Reuse `prune(conn, keep_days, now_iso, child_table="filings")`: delete `filings` +
`snapshots` older than `keep_days` before `now_iso`. `issuers.first_seen` is left
intact (historical provenance). Default: keep all (no prune unless `--keep-days`).

## Testing (TDD, mirrors existing `tests/`)

- `test_edgar_fetch.py` — `parse_master` (header skip, `|` split, accession
  derivation, `YYYYMMDD`→`YYYY-MM-DD`, malformed-line skip); `classify` buckets
  incl. `424B*` prefix and `/A` amendments; `index_url` quarter math;
  `fetch_daily_index` `404` → `None`.
- `test_edgar_db_schema.py` — `ensure_schema` idempotent; all tables + views
  exist; re-run is a no-op.
- `test_edgar_db_write.py` — `write_snapshot` keyed by `(snapshot_id, accession,
  cik)`; `filing_count` correct; `upsert_issuers` refreshes last_seen, preserves
  first_seen; view math (`v_insider_activity` counts, `v_activity_history` deltas,
  `v_tickered` NULL filter).
- `test_edgar_run.py` — `run()` with injected fetchers: default latest-date
  walk-back, explicit-date `404` error, ticker join (tickered + untickered→NULL),
  `keep_days` prune, second-run append (history grows), zero-count snapshot +
  warning.
- `test_screener_common.py` — `connect` sets WAL; `prune` deletes the right
  snapshots by table/timestamp.
- `test_registry.py` — extend: dispatcher routes `edgar`; `--list` includes it;
  existing `stocks`/`reddit` paths unchanged.
- Reddit tests unchanged after the `screener_common` migration.

Live smoke (manual, like the other screeners): pull a recent trading day into a
temp DB, assert non-zero `filings`, non-zero `v_tickered`, and a populated
`v_insider_activity`.

## Out of scope (YAGNI)

- **8-K item codes / Form 4 dollar amounts** — Phase 1.5 enrichment via the
  `submissions` API / filing XML for the tickered subset. Designed-for, not built.
- **XBRL fundamentals** (`companyfacts` / `frames`) — a separate future screener
  with a quarterly cadence, not part of a daily job.
- **Shared `Screener` base class** — the shapes differ too much; only
  `connect`/`prune` are extracted.
- **Multi-day backfill in one run** (`--back N`) — single `--date` for now.
- **Cross-screener joins** (EDGAR ↔ reddit ↔ stocks) — future query layer.
