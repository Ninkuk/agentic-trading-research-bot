# Stock Screener → SQLite — Design

**Date:** 2026-07-02
**Status:** Approved (design), pending implementation plan
**Component of:** agentic-trading-bot

## Goal

Pull a rich, whole-market stock dataset from stockanalysis.com and store it in
SQLite as append-only snapshots, so the trading bot can screen the current market
*and* backtest signals over historical runs.

## Data sources (verified empirically 2026-07-02)

Two anonymous endpoints, `User-Agent: Mozilla/5.0` header required.

### 1. Catalog — `__data.json` (metadata only)

```
GET https://stockanalysis.com/stocks/screener/__data.json
```

- SvelteKit **index-deduplicated** payload: `nodes[1].data` is a flat value pool;
  objects reference values by integer index into that pool. Requires a small
  dereferencing parser.
- Authoritative source of the **data-point catalog**: 310 entries, each
  `{ id, name (display), cat (category), proOnly? }`. Also exposes the universe
  `count`.
- Used **only** to build/refresh the `data_points` catalog table and to enumerate
  which IDs to request. We do not read stock rows from here.

### 2. Data — `data-points` (the workhorse)

```
GET https://stockanalysis.com/_api/endpoints/screener/data-points?type=s&ids=<id1>+<id2>+...
```

- Plain JSON: `data.data = { "<TICKER>": { "<fieldId>": value, ... }, ... }`.
- **A single request with all 310 IDs returns all 5,591 stocks × 310 fields:**
  HTTP 200, ~38 MB, ~7.5 s. No chunking, pagination, or auth needed.
- **`proOnly` fields (14 of them — Sharpe, Sortino, Graham Number, WACC, 10Y PE,
  top-analyst targets, etc.) are returned anonymously and populated.**
- Complete superset of the catalog: the map key IS the symbol; `n` is the name;
  `sector`/`industry`/`exchange`/`country` present alongside every metric.
- Field types: **273 numeric**, **36 string** (category strings like `sector`,
  ISO dates like `nextEarningsDate: "2026-10-16"`, currency codes, and `"Yes"/"No"`
  flags).

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Data scope | **All 310** data points; overridable via config | Full pull is one 7 s request — curating saves DB bytes, not fetch time |
| Table shape | **Wide** (one column per data point) | Natural for screening (`WHERE rsi < 30 AND zScore > 3`); within SQLite's 2000-col limit; columns auto-added if catalog grows |
| Storage model | **Snapshot history** — append one row per ticker per run | A trading bot must query point-in-time state and backtest signals; latest-only can't |
| Retention | `--keep-days N` prune (default: keep all) | A snapshot is ~8–12 MB; daily ≈ 3–4 GB/yr — bounded pruning keeps it sane |
| Stack | **Python stdlib only** (`urllib.request` + `sqlite3`) | One request + one transaction; keeps the screener a zero-dependency module |
| Types | numeric→`REAL`/`INTEGER`, string/date→`TEXT` (ISO) | SQLite dynamic typing handles the 273/36 split trivially |

## Schema

```sql
-- one row per run
CREATE TABLE snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,          -- ISO-8601 UTC, set at run time
    universe_count INTEGER NOT NULL,       -- tickers stored this run
    source         TEXT NOT NULL           -- 'stockanalysis.com'
);

-- the data-point catalog, upserted each run (self-documenting column dictionary)
CREATE TABLE data_points (
    id       TEXT PRIMARY KEY,             -- e.g. 'zScore'
    name     TEXT,                         -- e.g. 'Altman Z-Score'
    category TEXT,                         -- e.g. 'Technical Analysis'
    is_pro   INTEGER NOT NULL DEFAULT 0    -- 1 if proOnly in catalog
);

-- wide fact table: one row per (run, ticker), ~310 metric columns
CREATE TABLE metrics (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    symbol      TEXT NOT NULL,
    -- ~310 columns created dynamically from the catalog:
    --   numeric ids  -> REAL
    --   string ids   -> TEXT
    -- e.g. marketCap REAL, price REAL, sector TEXT, nextEarningsDate TEXT, ...
    PRIMARY KEY (snapshot_id, symbol)
);

CREATE INDEX ix_metrics_symbol ON metrics(symbol);

-- convenience: the current screen = newest snapshot
CREATE VIEW v_latest AS
SELECT m.* FROM metrics m
WHERE m.snapshot_id = (SELECT id FROM snapshots ORDER BY captured_at DESC LIMIT 1);
```

**Column typing rule:** a data-point id is `REAL` unless its catalog id appears in
the known string set (categories, `*Date`, currencies, `isSpac`/`optionable`/
`ma50vs200`, identifiers like `sic`/`cik`/`isin`/`cusip`/`website`). Type is
inferred from observed values with a string-set override, so new numeric metrics
default sensibly.

## Pipeline

1. **Fetch catalog** — GET `__data.json`; parse the SvelteKit pool; extract
   `[{id, name, category, proOnly}]` and universe count.
2. **Select IDs** — all catalog ids, minus any excluded by config.
3. **Fetch data** — GET `data-points?type=s&ids=<all ids>` → `{ticker: {field: value}}`.
4. **Ensure schema** — create tables if absent; `ALTER TABLE metrics ADD COLUMN`
   for any catalog id not yet a column (idempotent migration); upsert `data_points`.
5. **Write snapshot** — in one transaction: insert a `snapshots` row, then bulk
   `INSERT` one `metrics` row per ticker with `snapshot_id`.
6. **Prune** (optional) — if `--keep-days N`, delete snapshots older than N days
   (cascade removes their metrics).

## Module layout (proposed)

```
screener/
  __init__.py
  catalog.py     # __data.json fetch + SvelteKit deref parser -> catalog list
  fetch.py       # data-points fetch -> {ticker: {field: value}}
  db.py          # sqlite connection, schema create/migrate, snapshot insert, prune
  typing.py      # data-point id -> SQLite affinity (string-set + value inference)
  run.py         # CLI orchestration: catalog -> fetch -> ensure -> write -> prune
main.py          # thin entrypoint -> screener.run
```

Each unit is independently testable: the deref parser against a saved
`__data.json` fixture, the type inference against sample values, `db.py` against an
in-memory SQLite, and `fetch.py` against a recorded JSON fixture.

## CLI

```
python main.py [--db PATH] [--keep-days N] [--only ID,ID,...] [--exclude ID,ID,...]
```

- `--db` (default `screener.db`), `--keep-days` (default: keep all),
  `--only`/`--exclude` to subset the catalog.

## Error handling

- **HTTP failures** on either endpoint → abort the run, non-zero exit, no partial
  snapshot written (snapshot insert + metrics are one transaction).
- **Catalog/data mismatch** (a ticker with an unknown field id) → add the column
  on the fly; a field id absent for a ticker → `NULL`.
- **Empty/short universe** (e.g. count « expected) → warn but still write; the
  `universe_count` on the snapshot records what was captured.

## Testing

- Deref parser: known fixture → expected catalog subset.
- Type inference: numeric/date/`Yes-No` samples → expected affinities.
- Schema migration: adding a new catalog id ALTERs in a new column, idempotently.
- End-to-end (recorded fixtures): catalog + data JSON → snapshot row counts and a
  few spot-checked cell values; second run appends a second snapshot; `v_latest`
  returns only the newest.

## Out of scope (YAGNI for v1)

- Scheduling (use external cron); ETFs/funds (`type=e`); a separate slowly-changing
  `stocks` identity dimension; any querying/screening UI or the bot's consumption
  logic.
