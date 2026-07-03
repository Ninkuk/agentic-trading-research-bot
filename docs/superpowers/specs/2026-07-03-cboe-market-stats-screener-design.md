# CBOE Market Statistics Screener (Put/Call + VIX) — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** CBOE historical options-volume & put/call ratios
([market statistics historical data](https://www.cboe.com/us/options/market_statistics/historical_data/))
and CBOE VIX / volatility-index history
([VIX historical data](https://www.cboe.com/tradable-products/vix/vix-historical-data/)) —
free, no key; downloadable daily CSVs behind CBOE's public site, fetched off the
CBOE CDN with the same descriptive UA the `cboe_options` screener uses.
**Confidence:** 🟡 endpoints located but not adversarially verified — confirm the
exact CSV download routes and column headers live at implementation time.
**Package:** `cboe_stats/` · **Dispatcher:** `cboe_stats`

## Goal

Accumulate a small set of **market-wide options-sentiment time series** into SQLite
so the bot has a daily contrarian/regime reader for the *whole* options tape rather
than any single name:

- **Put/call ratios** by product (Total, Equity, Index) — the classic contrarian
  gauge: extreme highs = fear (bullish contrarian), extreme lows = complacency.
- **VIX and the vol-index complex** (VIX, VIX3M, VIX9D, VVIX) — level plus term
  structure (VIX vs VIX3M) as a fear/complacency and stress signal.
- **Total CBOE options volume** — the denominator/context for the ratios.

Like FRED (`fred_screener`), the value is the **history**: a put/call ratio or a
VIX level is only legible against its own trailing distribution. So this is a
time-series screener — observations accumulate and are upserted by key, and every
signal is derived in a view.

## Scope delineation vs. `cboe_options` (read this first)

There are **two** CBOE screeners and they must not be conflated:

| | `cboe_options` (dispatcher `options`) | `cboe_stats` (dispatcher `cboe_stats`, this spec) |
|---|---|---|
| Grain | **Per-ticker, per-contract** | **Market-wide aggregates** |
| Data | Full option chains: greeks, IV, OI, volume per contract for a watchlist | Daily put/call ratios by product, VIX & vol indices, total volume |
| Shape | Cross-sectional daily snapshot (replace-per-day) | Time-series (upsert by key, FRED-style) |
| Signal | IV Rank, unusual per-contract Vol/OI, per-name put/call | Market sentiment: aggregate put/call extremes, VIX term structure |
| Source | `cdn.cboe.com/api/global/delayed_quotes/options/{TICKER}.json` | CBOE market-statistics + VIX-history CSVs |

They share **only** the CBOE-CDN User-Agent convention
(`agentic-trading-bot ninadk.dev@gmail.com`) and the bounded-backoff HTTP helper —
**nothing else** (no shared tables, catalog, DB, or code). `cboe_options` answers
"what is happening in AAPL's chain today"; `cboe_stats` answers "is the whole tape
fearful or complacent". See
[2026-07-03-cboe-options-screener-design.md](2026-07-03-cboe-options-screener-design.md).

## Data-source notes

**A. Put/call ratios + total volume** — 🟡
[`https://www.cboe.com/us/options/market_statistics/historical_data/`](https://www.cboe.com/us/options/market_statistics/historical_data/)
publishes daily options volume and put/call ratios by product (Total, Equity,
Index, ETP) as downloadable CSV. The **Equity** and **Total** put/call ratios are
the headline contrarian sentiment gauges. *Confirm live at implementation time:*
the exact CSV download URL(s) and their column headers (product breakdown, ratio
vs. raw call/put volume columns) — isolate the parse so a header change fails
loudly in one place.

**B. VIX & vol-index history** — 🟡
[`https://www.cboe.com/tradable-products/vix/vix-historical-data/`](https://www.cboe.com/tradable-products/vix/vix-historical-data/)
serves VIX daily OHLC as a CSV (historically `.../us_indices/daily_prices/VIX_History.csv`
on the CDN), with sibling files for related indices (VIX3M, VIX9D, VVIX) where
free. *Confirm live at implementation time:* the per-index CSV URLs and header rows
(some CBOE index CSVs carry a preamble line before the header).

**Gotchas to handle:**
- Undocumented download routes — can move without notice; one parse module, fail
  loudly on drift.
- CBOE CDN returns **403** on some missing/withdrawn files rather than 404; treat a
  403/404 on a specific feed as *skip that feed*, not a retry (mirrors the
  `finra_short_volume` CDN-403 handling), and never retry it into the ground.
- Dates come from the CSV, not the wall clock — a weekend/holiday re-run must key to
  the real prior session, never invent a dated row.
- Missing/blank cells → `NULL`, never `0.0`.

## Data-shape classification

**Time-series**, exactly like FRED — a handful of daily series with long history,
upserted by key. The fact rows are **not** snapshot-scoped; `snapshots` records
fetch-run provenance only, and the history persists across pruning. Contrast
`cboe_options`, which is cross-sectional replace-per-day.

## Module layout

Self-contained package `cboe_stats/`, following the `fetch`/`db`/`run` triad +
`catalog` convention:

```
cboe_stats/
    __init__.py
    catalog.py  # ingestable feeds (Feed dataclass) + select_ids(all, only, exclude, add)
    fetch.py    # CBOE-CDN CSV client (shared UA, bounded backoff) + pure CSV parsers
    db.py       # from screener_common import connect; schema + views; upsert writers
    run.py      # resolve feeds -> fetch each -> upsert -> snapshot; argparse main
```

Registered in `registry.py`: `REGISTRY["cboe_stats"] = cboe_stats_main`.
**(Not modified by this spec — implementation task.)**

### `catalog.py`

The "ids" are the ingestable **feeds**, so `--only/--exclude/--add` compose the same
way as every other screener via `select_ids(all, only, exclude, add)` (verbatim the
FRED helper — strip / dedupe / drop-blank, `add` appended):

```python
@dataclass(frozen=True)
class Feed:
    feed_id: str   # "PCR" | "VIX" | "VIX3M" | "VIX9D" | "VVIX"
    kind: str      # "pcr" | "vix"  (which parser + which table it writes)
```

Default catalog: `PCR` (the product put/call + total-volume CSV) plus the vol
indices `VIX`, `VIX3M`, `VIX9D`, `VVIX`. `--add RVX` (repeatable) pulls an ad-hoc
vol index not in the catalog (kind `vix`), so the tool isn't locked to the curated
list. *Confirm each feed's URL resolves live at implementation time; drop any that
404/403 with a note rather than shipping a dead id.*

## Schema (SQL)

`CREATE TABLE/VIEW IF NOT EXISTS` only, applied idempotently by `ensure_schema` at
the top of every `run()`. Default DB path `cboe_stats.db`. WAL via
`from screener_common import connect`.

```sql
CREATE TABLE IF NOT EXISTS snapshots (        -- one row per fetch run (provenance)
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,               -- ISO-8601 UTC run time
    feed_count   INTEGER NOT NULL,            -- feeds fetched OK this run
    row_count    INTEGER NOT NULL             -- total obs rows upserted this run
);

CREATE TABLE IF NOT EXISTS pcr_daily (        -- market-wide put/call + volume
    date         TEXT PRIMARY KEY,            -- session date YYYY-MM-DD (from CSV)
    total_pcr    REAL,
    equity_pcr   REAL,
    index_pcr    REAL,
    total_volume INTEGER
);

CREATE TABLE IF NOT EXISTS vix_daily (        -- VIX OHLC + sibling index levels
    date   TEXT PRIMARY KEY,                  -- session date YYYY-MM-DD (from CSV)
    open   REAL, high REAL, low REAL, close REAL,   -- VIX itself
    vix3m  REAL,                              -- VIX3M close
    vix9d  REAL,                              -- VIX9D close
    vvix   REAL                               -- VVIX close
);
```

**Upsert-by-key, column-merge.** Each feed writes only the columns it owns onto the
shared `date` row: the `VIX` feed upserts `(date, open, high, low, close)`; `VIX3M`
upserts `(date, vix3m)`; `VVIX` upserts `(date, vvix)`; the `PCR` feed owns
`pcr_daily`. Writers use
`INSERT ... ON CONFLICT(date) DO UPDATE SET <only this feed's columns>=excluded...`
so a partial `--only VIX` run never blanks a sibling column already stored. Every
writer ends with `conn.commit()`.

## Views

Tight — three, all `CREATE VIEW IF NOT EXISTS`, LEFT JOINs so a partial `--only`
run yields NULLs instead of erroring:

- **`v_pcr_extremes`** — latest `total_pcr` / `equity_pcr` vs. their trailing
  percentile over stored history (e.g. rank within the last ~1y of sessions), with
  contrarian flags: `equity_pcr` in a high percentile → *fear / bullish-contrarian*;
  in a low percentile → *complacency / bearish-contrarian*.
- **`v_vix_term_structure`** — latest `close / vix3m` ratio plus a
  `backwardation` flag (`close > vix3m` → backwardation → stress; `< vix3m` →
  contango → calm). Optionally surfaces `vix9d`/`close` for near-term kink.
- **`v_latest_sentiment`** — single-row at-a-glance readout: latest date, equity &
  total put/call, VIX close, and the term-structure state, joining the latest row
  of each table.

## Run / CLI

```python
run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
    now_iso=None,
    fetch_pcr=fetch.fetch_pcr, fetch_vix=fetch.fetch_vix) -> (snapshot_id, feed_count, row_count)
```

1. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
2. Resolve feeds: `catalog.select_ids([f.feed_id for f in CATALOG], only, exclude, add)`.
3. `conn = connect(db_path); ensure_schema(conn)`.
4. Per feed, **skip-and-continue** on any failure: dispatch to `fetch_pcr` /
   `fetch_vix` by `kind`, upsert rows (optionally filtered to `date >= start`).
   On exception: `conn.rollback()`, print
   `warning: skipping {feed_id}: {type(e).__name__}` to **stderr** — never `str(e)`
   / `e.url` — and continue.
5. Always `write_snapshot(now_iso, feed_count=successes, row_count=Σ)`, even at zero
   (warn loudly, do not raise).
6. If `keep_days is not None`: single-table prune of stale `snapshots` only.

`main(argv)` — argparse: `--db` (default `cboe_stats.db`), `--only`, `--exclude`,
`--add` (repeatable), `--start YYYY-MM-DD` (optional; filters parsed rows, default
full history), `--keep-days` (default None). Prints a one-line summary. Fetchers +
`now_iso` injected for deterministic, network-free tests.

## Defaults

- DB path `cboe_stats.db`; catalog = `PCR, VIX, VIX3M, VIX9D, VVIX`.
- `--start` default None → full history from each CSV.
- `--keep-days` default None → keep everything (the history is the asset).

### Pruning (FRED-style single-table)

`prune(conn, keep_days, now_iso)` deletes only stale `snapshots` run-headers
(`DELETE FROM snapshots WHERE captured_at < cutoff`) — **never** `pcr_daily` /
`vix_daily`, which are the accumulated fact history. This is a plain single-table
delete, **not** the `screener_common` cascade helper; the `db.py` docstring must
warn a future reader not to wire the fact tables into a cascade (verbatim the FRED
prune warning).

## Testing (TDD, mirrors `tests/`)

- `test_cboe_stats_fetch.py` — `parse_pcr_csv` / `parse_vix_csv` from saved CSV
  fixtures (date parse, blank→None, comma-stripped ints); a 403/404 feed →
  skip-signal (returns None / raises the skip), not an infinite retry; backoff over
  `{429, 503}` via fake opener + `sleep=list.append`; non-retryable status re-raises.
- `test_cboe_stats_db_schema.py` — `ensure_schema` twice is idempotent; all tables +
  views present via `sqlite_master`.
- `test_cboe_stats_db_write.py` — column-merge upsert: `VIX` then `VIX3M` on the same
  date fills both without blanking; re-write of a date overwrites in place (no dup);
  `pcr_daily` upsert.
- `test_cboe_stats_db_views.py` — `v_pcr_extremes` percentile/flag on a known series,
  `v_vix_term_structure` backwardation boundary, `v_latest_sentiment` one-row shape;
  partial-selection LEFT JOIN yields NULLs, not errors.
- `test_cboe_stats_run.py` — injected fake fetchers, real `tmp_path` DB, pinned
  `now_iso`: happy-path counts, skip-and-continue on a failing feed, zero-success
  snapshot written + loud warning, `keep_days` prunes snapshots but not facts, and
  **secret hygiene**: stderr carries the feed id and exception class name but not
  `str(e)`. (No API key exists here, so the "key never in output" assertion is
  trivially satisfied — still assert the class-name-only warning to keep the pattern
  uniform with the keyed screeners.)
- `tests/test_registry.py` — extend: dispatcher routes `cboe_stats`; `--list`
  includes it; existing routes unchanged.

## Non-goals (YAGNI)

- **Per-ticker chains / greeks / IV Rank** — that is `cboe_options`; do not duplicate.
- **OCC cleared-volume** ([`https://www.theocc.com/market-data/market-data-reports/volume-and-open-interest/daily-volume`](https://www.theocc.com/market-data/market-data-reports/volume-and-open-interest/daily-volume))
  — cross-market cleared volume/OI is a natural **future add** (a third fact table
  in this same package), deferred for v1.
- Intraday polling — one EOD refresh per day.
- Alerting / notifications; skew or full-surface analytics.

## Environment

- **No API key.** `.env` / `.env.example` unchanged.
- Reuses `http_client.make_opener` with the shared CBOE-CDN UA
  `agentic-trading-bot ninadk.dev@gmail.com` and `http_client.http_get` with
  `_RETRY_STATUS = frozenset({429, 503})`.
- Dependency-free (`urllib` + stdlib `csv`), matching every existing screener.
