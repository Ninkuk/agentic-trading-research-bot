# FINRA Daily Short Sale Volume Screener — Design

**Date:** 2026-07-03
**Status:** Approved, ready for implementation planning
**Data source:** [FINRA Daily Short Sale Volume Files](https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files),
served as one pipe-delimited text file per trading day at
`https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt`.
No API, no key — plain HTTP file downloads over Cloudflare. A normal
`User-Agent` is required (a blank UA can trip Cloudflare bot rules), and the
same bounded-backoff on 403/429/503 used by the other screeners applies.

## Goal

Pull FINRA's **daily short sale volume** — how much of each trading day's
consolidated volume, per security, was executed as short sales — into SQLite, so
the trading bot has a **daily shorting-pressure reader**: which listed tickers
are being shorted most heavily *right now*, whose short participation is spiking
versus their own baseline, and which are under sustained short pressure across
consecutive sessions.

This is the **seventh** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`, `ftd`, and now `short_volume`). It reuses `screener_common`, the
`http_client` bounded-backoff, and the **FTD module layout**, but over a
per-trading-day flat file instead of a per-half-month ZIP.

## What this data is (and what it is NOT)

- The `CNMS` file is the **Consolidated NMS** short sale volume: aggregated
  short-sale volume by security for trades executed and reported to a FINRA TRF,
  the ADF, or the ORF during normal market hours, across NYSE/Nasdaq/BATS venues.
  It covers **exchange-listed** securities — the tickers a bot actually trades.
- Each row is `(date, symbol)` → `ShortVolume`, `ShortExemptVolume`,
  `TotalVolume`, and a `Market` venue tag. Published every trading day since
  2009-08-03.
- **This is short *volume* (a daily flow), NOT short *interest* (a standing
  position).** A stock can post a high short-volume ratio every day yet carry
  tiny short interest, because market makers routinely sell short intraday and
  cover by the close — that flow inflates the ratio without any lasting bearish
  position. Days-to-cover and open short interest are a *different* FINRA dataset
  (Equity Short Interest, bi-monthly, OTC-only via the free API) and are out of
  scope here. So this is a **screener that surfaces shorting-pressure candidates,
  not a verdict on bearish positioning.**

### Enrichment we compute from the file alone

- **`short_ratio = ShortVolume / TotalVolume`** — the single most useful
  enrichment and the basis of every view. Computed at parse time and stored.
  `None` when `TotalVolume` is 0 or missing (avoids divide-by-zero; such rows are
  excluded from ratio-based views).
- **`ShortExemptVolume`** kept as its own column (short-exempt sales are a
  distinct regulatory category; not folded into the ratio, but retained for
  downstream analysis).

## Data shape: a *daily full-universe dump* (same family as FTD)

- `stocks`/`reddit`/`edgar` are **cross-sectional** (snapshot-scoped state).
- `fred` is **time-series** (few series × dated observations).
- `cftc` is a **panel** assembled one instrument at a time.
- `ftd` is a **periodic (half-month) full-universe dump**.
- `short_volume` is a **daily full-universe dump** — the same shape as FTD, one
  cadence faster. History is **not** snapshot-scoped; it accumulates
  `(symbol, date)` facts that persist across runs.

## Module layout (mirrors every screener; closest to FTD)

```
finra_short_volume/
    __init__.py
    fetch.py   # network + parse (simpler than FTD — plain text, no zipfile)
    db.py      # schema + writes + screening views
    run.py     # calendar enumeration + incremental orchestration + CLI
```

Plus:
- Register `"short_volume"` in `registry.py` (import `run.main as short_volume_main`).
- Document nothing new in `.env.example` — **no credentials required.**

### `fetch.py`

- `day_url(date, base=FILES_BASE) -> str` — URL for a `YYYY-MM-DD` date,
  formatting the `CNMSshvol{YYYYMMDD}.txt` filename.
- `parse_file(text) -> list[dict]` — pipe-delimited
  `Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market`. Drops the
  header row naturally (its non-numeric fields fail coercion). Skips any trailer
  or malformed line (fewer than 6 fields, or a row missing symbol / a valid
  `YYYYMMDD` date / a valid `TotalVolume`). Computes
  `short_ratio = short_volume / total_volume` (`None` if `total_volume` is 0).
  Reuses the `_norm_date` / `_num` coercion helpers modeled on FTD's.
- `fetch_day(date, ...)` — download + parse one day. Returns `rows`, or **`None`
  on HTTP 404** (non-trading day / not-yet-published). Text download via
  `http_client.make_opener` (no `zipfile`, unlike FTD). Bounded backoff retries
  403/429/503 and transient network errors; 404 is non-retryable and surfaces as
  `None`.
- Constants: `FILES_BASE = "https://cdn.finra.org/equity/regsho/daily"`, a
  descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`),
  `_RETRY_STATUS = frozenset({403, 429, 503})`.

### `db.py` — schema

```sql
CREATE TABLE securities (            -- thin dimension: this feed has no name field
    symbol      TEXT PRIMARY KEY,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE short_volume (          -- the fact table
    symbol              TEXT NOT NULL REFERENCES securities(symbol),
    date                TEXT NOT NULL,        -- YYYY-MM-DD
    short_volume        INTEGER NOT NULL,
    short_exempt_volume INTEGER,
    total_volume        INTEGER NOT NULL,
    short_ratio         REAL,                 -- short_volume/total_volume, NULL if total 0
    market              TEXT,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX ix_sv_date   ON short_volume(date);
CREATE INDEX ix_sv_symbol ON short_volume(symbol);
CREATE TABLE days (                  -- per-day provenance (like FTD `periods`)
    date       TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE snapshots (             -- per-run header
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    day_count   INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
```

### `db.py` — writes (mirror FTD's names/semantics)

- `ensure_schema(conn)` — create tables, indexes, views. Idempotent.
- `upsert_securities(conn, rows)` — upsert `symbol` dimension, extending
  `first_seen`/`last_seen` to min/max date seen.
- `replace_day(conn, date, rows) -> int` — **delete all `short_volume` rows for
  that date, then bulk-insert** (replace, not upsert), so a FINRA file repost
  that drops a row leaves no orphan. Dedupe within the batch by `(symbol, date)`.
- `record_day(conn, date, fetched_at, row_count)` — upsert the `days`
  provenance row.
- `write_snapshot(conn, captured_at, day_count, row_count) -> id` — run header.
- `stored_days(conn) -> list[str]` — ingested dates, sorted ascending.
- `prune(conn, keep_days, now_iso) -> int` — delete **snapshot headers only**
  older than `keep_days`; **never** touches `short_volume` history (same
  single-table prune as FTD).

### `db.py` — screening views (the analytical payoff)

Liquidity floor `total_volume >= 100000` and ratio threshold `0.50` are constants
baked into the view SQL and documented here.

1. **`v_latest`** — most recent stored date, one row per liquid symbol
   (`total_volume >= 100000`), carrying `short_volume`, `total_volume`,
   `short_ratio`, `market`. The "who is most-shorted today" leaderboard; consumers
   `ORDER BY short_ratio` or `short_volume`.
2. **`v_high_short_ratio`** — latest date filtered to
   `short_ratio >= 0.50 AND total_volume >= 100000`. The heavy-short-participation
   shortlist.
3. **`v_ratio_spikes`** — latest `short_ratio` vs each symbol's **trailing
   20-day average ratio** (window `ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING`,
   excluding the current day), on the newest date, liquid only. `spike_ratio =
   short_ratio / trailing_avg`; a high value flags a fresh jump in short
   participation.
4. **`v_short_streaks`** — gaps-and-islands over **elevated** days
   (`short_ratio >= 0.50 AND total_volume >= 100000`): one row per `(symbol,
   unbroken run)` with `streak_days`, `streak_start`, `streak_end`,
   `peak_ratio`, and `active=1` when the run reaches the newest stored date.
   Trading days are not contiguous calendar days, so a `v_date_rank`
   (`DENSE_RANK()` over distinct dates) defines "consecutive", exactly as FTD does.
5. **`v_symbol_history`** — per-symbol time series (`symbol, date, short_volume,
   total_volume, short_ratio, market`) for drill-down.

### `run.py` — orchestration + CLI

- Enumerate **calendar days** from `--start` (default: **6 months back**)
  through today (inclusive). For each: skip if already stored, **except** re-fetch
  the trailing `_REFETCH_DAYS = 2` stored days so FINRA reposts are re-absorbed by
  `replace_day`. `--full` re-ingests every day in range.
- `fetch_day` returning `None` (404 — weekend/holiday/not-yet-published) is
  skipped silently. Any per-day exception rolls back that day's uncommitted
  writes and continues, logging **only `type(e).__name__`** (never `str(e)` /
  `e.url`) — the repo-wide secret-hygiene rule.
- After the loop: `write_snapshot`, then `prune` if `--keep-days` given.
- Returns `(snapshot_id, day_count, row_count)`.
- **CLI** (`prog="short_volume"`):
  - `--db` (default `short_volume.db`)
  - `--start YYYY-MM-DD` (default: 6 months back)
  - `--full` (re-ingest every day in range)
  - `--keep-days N` (prune snapshot provenance only)

## Defaults (approved)

- **Lookback:** 6 months (~126 trading days, ~1M rows, ~126 requests). Enough for
  the 20-day baselines and streaks with margin; extend toward 2009 via `--start`.
  Deliberately lighter than FTD's 24 months because daily × ~8k symbols is a
  heavier first run.
- **Retention:** keep all short-volume history; `--keep-days` prunes only
  run-provenance snapshots — never the facts (same as FTD).
- **Market segment:** `CNMS` (consolidated exchange-listed) only. The other
  segment files (`FNSQ`, `FNYX`, `FNQC`, `FORF`, `FNRA`) are out of scope; adding
  a `--segment` switch is a clean future enhancement.
- **View thresholds:** `total_volume >= 100000` liquidity floor and
  `short_ratio >= 0.50` elevated threshold, baked into view SQL.

## Testing (mirror `test_ftd_*`)

- `test_finra_shorts_fetch.py` — `parse_file` (header dropped, malformed/trailer
  lines skipped, `short_ratio` computed, zero-`TotalVolume` → `None`);
  `day_url` formatting; `fetch_day` 404 → `None` via an injected fake opener.
- `test_finra_shorts_db_schema.py` — `ensure_schema` idempotent; tables, indexes,
  and the five documented views exist (plus the internal `v_date_rank` helper
  that `v_short_streaks` builds on, as FTD does).
- `test_finra_shorts_db_write.py` — `upsert_securities` first/last_seen;
  `replace_day` replaces (repost dropping a row leaves no orphan) and dedupes;
  `record_day`/`write_snapshot`/`stored_days`; `prune` removes snapshot headers
  only and leaves facts intact.
- `test_finra_shorts_db_views.py` — `v_latest` liquidity filter and latest-date
  scoping; `v_high_short_ratio` threshold; `v_ratio_spikes` trailing-average
  math; `v_short_streaks` consecutive-day runs and `active` flag on seeded data.
- `test_finra_shorts_run.py` — enumeration + incremental skip + trailing-refetch
  + `--full`, with injected `fetch_day` (including a `None`/404 day) and
  `now_iso`, asserting returned counts and that a skipped day is not re-fetched.
- `test_registry.py` — extend to assert `"short_volume"` dispatches.

## Out of scope (YAGNI)

- Equity Short Interest (open positions / days-to-cover) — a separate dataset;
  can be a future `finra_short_interest` package.
- Non-CNMS segment files; a `--segment` switch.
- Shares-outstanding / float joins to turn short volume into % of float.
- The OAuth2 higher-rate FINRA API tier — the anonymous CDN files suffice.
