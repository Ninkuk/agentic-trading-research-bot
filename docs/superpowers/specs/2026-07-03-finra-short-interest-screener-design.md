# FINRA Equity Short Interest Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [FINRA Equity Short Interest](https://www.finra.org/finra-data/browse-catalog/equity-short-interest),
served as one bulk file per settlement date at
`https://cdn.finra.org/equity/otcmarket/biweekly/shrt{YYYYMMDD}.csv`.
No API, no key — a plain HTTP file download over Cloudflare, same CDN and the
same descriptive-`User-Agent` requirement as the daily short-volume screener.
**GOTCHA:** despite the `.csv` extension the file is **pipe-delimited**, so it
reuses the existing FINRA pipe parser and `_norm_date`/`_num` helpers.
**Confidence:** 🟢 verified (CDN path + bi-monthly cadence live-checked
2026-07-03; exact column order and the alternate POST API's dataset name tagged
🟡 — confirm live at implementation time).

## Goal

Pull FINRA's **settled equity short interest** — the standing short *position* in
each security as of each bi-monthly settlement date — into SQLite, so the bot has
a **squeeze / days-to-cover reader**: which listed tickers carry the largest open
short positions, whose short interest is *building* settlement-over-settlement,
and which would take the most days of average volume to buy back.

This is the **settled-position complement** to the daily short-volume screener,
and the concrete build-out of the `finra_short_interest` package that the
short-volume spec named in its own out-of-scope. It is the **eighth** screener in
the family (`stocks`, `reddit`, `edgar`, `fred`, `cftc`, `ftd`, `short_volume`,
and now `short_interest`), and it mirrors the `finra_short_volume` module layout
most closely of any — same CDN, same pipe parser, same FRED-style single-table
prune — over a **bi-monthly settlement file** instead of a daily one.

## Short *interest* vs short *volume* (why this is a different screener)

The short-volume screener already in the tree measures a **daily flow**: how much
of a session's volume printed as short sales. This screener measures the
**standing position**: how many shares are *held* short as of a settlement date,
reported by broker-dealers to FINRA twice a month.

- **Short volume** inflates on intraday market-making that covers by the close —
  a high daily short-volume ratio can coexist with *tiny* open short interest.
- **Short interest** is the durable bearish position, and — divided by average
  daily volume — yields **days-to-cover**, the classic squeeze gauge. That number
  simply does not exist in the short-volume feed.

So the two are complementary, not redundant: short volume surfaces *today's*
shorting pressure; short interest surfaces *accumulated* short positioning and the
squeeze setups it implies. FINRA computes `daysToCoverQuantity` in the file
itself, so days-to-cover is stored, not re-derived.

## Source notes (confirmed 2026-07-03)

- **Bulk file:** `https://cdn.finra.org/equity/otcmarket/biweekly/shrt{YYYYMMDD}.csv`,
  where `{YYYYMMDD}` is the **settlement date**, not the publication date. FINRA
  publishes on the **FINRA/exchange short-interest settlement schedule** — the
  **mid-month** (~15th) and **month-end** settlement dates → **two files per
  month** ("bi-monthly" / twice-monthly). Each file is a full-universe snapshot of
  open short positions as of that settlement.
- **Pipe-delimited despite `.csv`.** The body is `|`-separated, so the existing
  `finra_short_volume` parse path (split on `|`, drop the header by coercion
  failure, skip short/malformed lines) is reused wholesale, along with `_norm_date`
  (`YYYYMMDD → YYYY-MM-DD`) and `_num`.
- **Columns** (🟡 **confirm exact order live**): `accountingYearMonthNumber`,
  `symbolCode`, `issueName`, `marketClassCode`, `currentShortPositionQuantity`,
  `previousShortPositionQuantity`, `changePercent`, `averageDailyVolumeQuantity`,
  `daysToCoverQuantity`, `revisionFlag`, `stockSplitFlag`, `newIssueFlag`,
  `settlementDate`. The parser maps by position but must be pinned to the live
  header at implementation time (as the short-volume parser is to its 6-field
  layout).
- **Alternate access — the FINRA Query API** (the filtered/incremental path, not
  the primary): `POST https://api.finra.org/data/group/otcMarket/name/EquityShortInterest`
  returns **CSV or JSON** (the `Accept` header picks the format) and accepts a
  JSON `compareFilters` payload for server-side filtering — e.g. `settlementDate
  EQUAL 2026-06-15` returns exactly one settlement's rows. **No auth, no key.**
  (XML output was discontinued 2019-01-01.) We recommend the **anonymous CDN bulk
  file as primary** — it matches the short-volume screener exactly and needs no
  request body — and note the POST API as the alternative when a single
  settlement must be pulled without guessing its `shrt{YYYYMMDD}.csv` URL.
- **COVERAGE CUTOFF (important for lookback/backfill):** consolidated
  **exchange-listed** short interest is available only from **June 2021 onward**;
  files before that are **OTC-only**. Document this — a `--start` earlier than
  2021-06 will pull OTC-only universes, and the "listed" leaderboard is only
  meaningful from mid-2021.
- **Publication delay:** each settlement's file is published **~8 business days
  after** the settlement date. `run.py` accounts for this when choosing which
  recent settlements are expected to exist yet (a not-yet-published settlement
  404s → skipped, like the short-volume screener).

## Data-shape classification: a *bi-monthly full-universe dump* (short-volume's slower sibling)

Same shape as `short_volume` and `ftd`, one cadence slower:

- `stocks`/`reddit`/`edgar` are **cross-sectional** (snapshot-scoped state).
- `fred` is **time-series**; `cftc` is a **panel**.
- `ftd` is a **half-month full-universe dump**; `short_volume` is a **daily**
  one.
- `short_interest` is a **bi-monthly (settlement-dated) full-universe dump**.
  History is **not** snapshot-scoped; it accumulates `(symbol, settlement_date)`
  facts that persist across runs. A **replace-by-settlement** write (delete the
  settlement's rows, then bulk-insert) makes a FINRA repost that drops a symbol
  leave no orphan, exactly like `replace_day`.

## Module layout (mirrors `finra_short_volume` closely)

```
finra_short_interest/
    __init__.py
    fetch.py   # CDN download + pipe parse (reuses the short-volume parser shape)
    db.py      # schema + writes + squeeze views + FRED-style prune
    run.py     # settlement-date enumeration + incremental orchestration + CLI
```

Plus:
- Register `"short_interest"` in `registry.py` (import `run.main as short_interest_main`).
- Nothing new in `.env.example` — **no credentials required.**

### `fetch.py`

- `settlement_url(date, base=FILES_BASE) -> str` — URL for a `YYYY-MM-DD`
  settlement date, formatting `shrt{YYYYMMDD}.csv`.
- `parse_file(text) -> list[dict]` — pipe-delimited parse over the columns above.
  Drops the header line by coercion (its non-numeric fields fail `_num`); skips
  any trailer/short/malformed line (missing `symbolCode`, an invalid settlement
  date, or an unparseable `currentShortPositionQuantity`). Reuses `_norm_date` /
  `_num`. Keeps `daysToCoverQuantity` and `changePercent` as stored fields (FINRA
  computes them; we do not re-derive), coercing blanks to `None`.
- `fetch_settlement(date, ...)` — download + parse one settlement. Returns `rows`,
  or **`None` on HTTP 403/404** (settlement with no file / not-yet-published) —
  the CDN 403s for absent dates exactly as in the short-volume screener, so 403
  and 404 both map to `None`. Bounded backoff retries `429/503` and transient
  network errors; 403/404 are non-retryable and surface as `None`.
- Constants: `FILES_BASE = "https://cdn.finra.org/equity/otcmarket/biweekly"`, a
  descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`),
  `_RETRY_STATUS = frozenset({429, 503})`.

### `db.py` — schema

```sql
CREATE TABLE IF NOT EXISTS securities (   -- dimension (has an issue name, unlike short_volume)
    symbol      TEXT PRIMARY KEY,
    issue_name  TEXT,                       -- newest issueName seen
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS short_interest (   -- the fact table
    symbol              TEXT NOT NULL REFERENCES securities(symbol),
    settlement_date     TEXT NOT NULL,        -- YYYY-MM-DD
    current_short_qty   INTEGER NOT NULL,
    previous_short_qty  INTEGER,
    avg_daily_volume    INTEGER,
    days_to_cover       REAL,                 -- FINRA-computed daysToCoverQuantity
    change_pct          REAL,                 -- FINRA-computed changePercent
    revision_flag       TEXT,
    market_class        TEXT,                 -- marketClassCode (NNM/OTC/etc.)
    PRIMARY KEY (symbol, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_si_settlement ON short_interest(settlement_date);
CREATE INDEX IF NOT EXISTS ix_si_symbol     ON short_interest(symbol);
CREATE TABLE IF NOT EXISTS settlements (   -- per-settlement provenance (like short_volume `days`)
    settlement_date TEXT PRIMARY KEY,
    fetched_at      TEXT NOT NULL,
    row_count       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (     -- per-run header
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    settlement_count INTEGER NOT NULL,
    row_count        INTEGER NOT NULL
);
```

### `db.py` — writes (mirror the short-volume names/semantics)

- `ensure_schema(conn)` — create tables, indexes, views. Idempotent.
- `upsert_securities(conn, rows)` — upsert the `symbol` dimension, refreshing
  `issue_name` to the newest seen and extending `first_seen`/`last_seen` to the
  min/max settlement date.
- `replace_settlement(conn, settlement_date, rows) -> int` — **delete all
  `short_interest` rows for that settlement, then bulk-insert** (replace, not
  upsert), so a FINRA repost dropping a symbol leaves no orphan. Dedupe within the
  batch by `(symbol, settlement_date)`.
- `record_settlement(conn, settlement_date, fetched_at, row_count)` — upsert the
  `settlements` provenance row.
- `write_snapshot(conn, captured_at, settlement_count, row_count) -> id`.
- `stored_settlements(conn) -> list[str]` — ingested settlement dates, ascending.
- `prune(conn, keep_days, now_iso) -> int` — delete **snapshot headers only**
  older than `keep_days`; **never** touches `short_interest` history (the same
  FRED-style single-table prune as `short_volume`/`ftd`/`cftc`).

### `db.py` — screening views (the squeeze payoff)

Liquidity floor `avg_daily_volume >= 100000` and a days-to-cover threshold
`days_to_cover >= 5.0` are constants baked into the view SQL and documented here.

1. **`v_latest`** — most recent stored settlement, one row per symbol, carrying
   `current_short_qty`, `avg_daily_volume`, `days_to_cover`, `change_pct`,
   `market_class`. The "who is most-shorted right now" leaderboard; consumers
   `ORDER BY current_short_qty` or `days_to_cover`.
2. **`v_high_days_to_cover`** — latest settlement filtered to `days_to_cover >=
   5.0 AND avg_daily_volume >= 100000`. The **squeeze shortlist** — high open
   short *and* thin liquidity to buy it back.
3. **`v_short_interest_spikes`** — latest `current_short_qty` compared **both** to
   its own `previous_short_qty` (the file's built-in prior) **and** to the
   symbol's trailing settlement average (window `ROWS BETWEEN 6 PRECEDING AND 1
   PRECEDING` ≈ prior quarter), on the newest settlement. `si_change =
   current_short_qty / NULLIF(previous_short_qty, 0)`; a value well above 1 flags
   building short interest.
4. **`v_symbol_history`** — per-symbol time series (`symbol, settlement_date,
   current_short_qty, avg_daily_volume, days_to_cover, change_pct`) for drill-down.

### `run.py` — orchestration + CLI

- Enumerate **settlement dates** (the ~15th and each month-end), **not calendar
  days**, from `--start` (default: **~12 months back**) through the most recent
  settlement expected to be published (accounting for the ~8-business-day delay).
  For each: skip if already stored, **except** re-fetch the trailing
  `_REFETCH_SETTLEMENTS = 2` stored settlements so FINRA reposts/revisions are
  re-absorbed by `replace_settlement`. `--full` re-ingests every settlement in
  range.
- `fetch_settlement` returning `None` (403/404 — not-yet-published or absent
  settlement) is skipped silently. Any per-settlement exception rolls back that
  settlement's uncommitted writes and continues, logging **only
  `type(e).__name__`** (never `str(e)` / `e.url`) — the repo-wide secret-hygiene
  rule.
- After the loop: `write_snapshot`, then `prune` if `--keep-days` given.
- Returns `(snapshot_id, settlement_count, row_count)`.
- A `settlement_dates(start, end)` helper generates the mid-month + month-end
  schedule between two dates (the analogue of `days_in_range`), so enumeration is
  unit-testable without hitting the network.
- **CLI** (`prog="short_interest"`):
  - `--db` (default `short_interest.db`)
  - `--start YYYY-MM-DD` (default: ~12 months back)
  - `--full` (re-ingest every settlement in range)
  - `--keep-days N` (prune snapshot provenance only)

## Defaults (approved)

- **Lookback:** ~12 months (≈24 settlements, ≈24 requests) — enough for the
  trailing-settlement spike baselines with margin; extend toward the June-2021
  listed-coverage start via `--start`. Lighter cadence than short-volume means the
  first run is cheap.
- **Retention:** keep all short-interest history; `--keep-days` prunes only
  run-provenance snapshots — never the facts.
- **Coverage floor:** a `--start` before **2021-06** yields OTC-only universes;
  the listed-name views are only meaningful from mid-2021 onward (documented, not
  enforced — the file is ingested as-published).
- **View thresholds:** `avg_daily_volume >= 100000` liquidity floor and
  `days_to_cover >= 5.0` squeeze threshold, baked into view SQL.

## Testing (mirror `test_finra_shorts_*`)

- `test_finra_short_interest_fetch.py` — `parse_file` (header dropped,
  malformed/trailer lines skipped, `days_to_cover`/`change_pct` retained,
  blank numerics → `None`); `settlement_url` formatting; `fetch_settlement`
  403/404 → `None` via an injected fake opener. **Network never hit.**
- `test_finra_short_interest_db_schema.py` — `ensure_schema` idempotent; tables,
  indexes, and the four documented views exist.
- `test_finra_short_interest_db_write.py` — `upsert_securities` issue-name refresh
  + first/last_seen; `replace_settlement` replaces (repost dropping a symbol
  leaves no orphan) and dedupes; `record_settlement`/`write_snapshot`/
  `stored_settlements`; `prune` removes snapshot headers only and leaves facts
  intact.
- `test_finra_short_interest_db_views.py` — `v_latest` latest-settlement scoping;
  `v_high_days_to_cover` threshold + liquidity filter; `v_short_interest_spikes`
  prior-vs-current and trailing-average math on seeded data.
- `test_finra_short_interest_run.py` — settlement enumeration + incremental skip +
  trailing-refetch + `--full`, with injected `fetch_settlement` (including a
  `None`/404 settlement) and pinned `now_iso`; asserts returned counts, that a
  skipped settlement is not re-fetched, and the **secret-hygiene** assertion that
  a raising settlement logs the exception **class** to stderr but **not** its
  message.
- `test_registry.py` — extend to assert `"short_interest"` dispatches.

## Non-goals (YAGNI)

- The **FINRA Query API** (POST `compareFilters`) as the primary path — the
  anonymous CDN bulk file suffices; the POST API is documented as the alternative
  only, not wired up.
- **Float / shares-outstanding joins** to compute short-interest-as-%-of-float —
  a separate reference dataset; days-to-cover already gives a squeeze proxy.
- **Pre-2021 OTC-only backfill** as a default — reachable via `--start` but not
  pursued (the listed universe is the target).
- Merging with `short_volume` — the two screeners stay independent DBs; consumers
  correlate settled interest against daily flow in the bot, not in a view.
- The OAuth2 higher-rate FINRA API tier — unnecessary for a twice-monthly pull.

## Environment

**No new variables** — the CDN bulk file needs no credentials. `.env.example` is
unchanged.
