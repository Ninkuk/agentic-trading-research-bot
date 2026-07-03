# SEC Fails-to-Deliver (FTD) Screener — Design

**Date:** 2026-07-03
**Status:** Approved, ready for implementation planning
**Data source:** [SEC Fails-to-Deliver Data](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data),
served as semi-monthly ZIP files at
`https://www.sec.gov/files/data/fails-deliver-data/cnsfails{YYYYMM}{a|b}.zip`.
No API, no key — plain HTTP file downloads. The SEC throttles anonymous
downloads with **HTTP 403** (same as EDGAR), so the same 403-retry backoff and a
descriptive `User-Agent` are required.

## Goal

Pull the SEC's **fails-to-deliver (FTD)** dataset — the shares that failed to
settle at the clearing agency, per security, per settlement date — into SQLite,
so the trading bot has a **settlement-stress reader**: which securities are
persistently or unusually failing to deliver, ranked by shares *and* dollar
value, with a proxy for the **Reg SHO threshold-list** persistence signal.

This is the **sixth** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`, `ftd`). It reuses `screener_common`, the `http_client`
bounded-backoff, and the CFTC module layout, but takes a **fourth data shape**.

## What FTD data is (and why a screener over it)

- A **fail-to-deliver** is a trade that didn't settle — the seller didn't deliver
  the shares by settlement. It arises from both long and short sales for many
  benign reasons; **the SEC explicitly warns it is NOT proof of naked shorting.**
  So this is a *screener that surfaces candidates*, not a verdict.
- Each file reports, per `(settlement date, security)`, the **cumulative
  outstanding balance** of shares still failing on that date — a running
  snapshot, *not* that day's new fails. A name failing 500k shares for 20
  straight days is structurally different from a one-day spike that clears.
- The canonical signal is the **Reg SHO threshold list**: a security lands on it
  after **5 consecutive settlement days** with fails ≥ **10,000 shares** *and* ≥
  **0.5% of shares outstanding**. Persistent fails are read (with debate) as
  structural short pressure — a short-squeeze precursor.

### Enrichment we can and can't do from this file alone

- **Dollar value of fails = `quantity × price`** — computed and stored. This is
  the single most useful enrichment: 1M failed penny-stock shares ≠ 1M failed
  mega-cap shares.
- **Persistence (shares half of Reg SHO):** reproducible directly — consecutive
  settlement days with `quantity ≥ 10,000`. Shipped as `v_persistent`.
- **The `0.5% of shares outstanding` half is NOT reproducible** from this file —
  it has no shares-outstanding column. Rather than pull in a second dataset, we
  ship the **shares-based persistence proxy** and document the gap. (YAGNI; a
  shares-outstanding join is an additive future enhancement.)

## Key realization: this is a *periodic full-universe dump* (a fourth data shape)

- `stocks`/`reddit`/`edgar` are **cross-sectional** (snapshot-scoped state).
- `fred` is **time-series** (few series × dated observations).
- `cftc` is a **panel** you assemble by querying **one instrument at a time**.
- `ftd` is the inverse of CFTC: each publication is a **full-universe bulk file**
  — *every* security with open fails for a half-month, in one ZIP. You choose
  **time periods to ingest**, not instruments to query. There is no ticker
  catalog to curate; the natural key is `(settlement_date, cusip)` and the fact
  table is **period-scoped and replaced per file**, not snapshot-scoped. The fail
  history persists across pruning; `snapshots` only records run provenance.

## Source verification (confirmed first-hand 2026-07-03)

The URL the user cited is **correct**. Verified live:

1. **Landing page** `.../fails-deliver-data` lists downloadable ZIPs named
   `cnsfails{YYYYMM}{a|b}.zip`, from **`cnsfails200907a`** (July 2009) to the
   current half-month. (Pre-2009 fails exist in a different, legacy layout — out
   of scope.)
2. **File URL pattern** `https://www.sec.gov/files/data/fails-deliver-data/cnsfails202505a.zip`
   downloaded HTTP 200 (~1.2 MB zipped → ~3.3 MB unzipped). The ZIP contains a
   **single member** named like the archive without extension (`cnsfails202505a`).
   *The parser reads whichever single member is present — it does not assume the
   name.*
3. **`a` = settlement dates 1–15 of the month, `b` = 16–end.** Confirmed: the `a`
   sample's distinct settlement dates ran `20250501 … 20250514`.
4. **Format** — pipe-delimited, one header line, then rows, then a two-line
   trailer:
   ```
   SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE
   20250501|B38564108|CMBT|111|CMB.TECH NV (BEL)|9.51
   ...
   Trailer record count 52964
   Trailer total quantity of shares 2195999709
   ```
   - `SETTLEMENT DATE` = `YYYYMMDD`. `CUSIP` is the **stable key** (SYMBOL is
     reused/reassigned and is sometimes blank). `QUANTITY` = integer shares.
     `PRICE` = prior-day close, float, **may be blank**. `DESCRIPTION` may contain
     non-ASCII bytes.
   - The **trailer `record count`** is used to validate the parse (warn on
     mismatch).
5. **403 throttling** behaves like EDGAR — a descriptive `User-Agent` plus the
   403/429/503 retry set clears it.

## Architecture

Mirrors `cftc_screener` module-for-module.

```
ftd_screener/
  __init__.py
  fetch.py     # ZIP download (bytes opener) + unzip + pipe parse + trailer check
  db.py        # schema (securities/fails/periods/snapshots) + writers + views + prune
  run.py       # period enumeration, skip-and-continue orchestration, argparse CLI
```

Registered in `registry.py` as `"ftd": ftd_main`. Reuses
`screener_common.connect` (WAL). **No `catalog.py`** — the ingest unit is a time
period, not a curated instrument list, so there is nothing to curate.

### 1. Fetch (`fetch.py`)

Reuses `http_client.http_get` (bounded exponential backoff, `Retry-After`
honored) and `http_client.retry_delay`, with `_RETRY_STATUS = {403, 429, 503}`
(the EDGAR set — SEC throttles with 403). **Divergence from the other fetchers:**
the payload is a **binary ZIP**, so the shared text opener (which UTF-8-decodes)
is *not* used. `fetch.py` supplies a **local bytes opener** (`resp.read()`
returns `bytes`); `http_get` returns those bytes unchanged, so no change to
`http_client` is needed.

Functions:
- `period_url(period) -> str` — build the file URL for a period id like
  `"202505a"`.
- `settlement_bounds(period) -> (start, end)` — the `YYYY-MM-DD` date range a
  period covers (`a` → 01–15, `b` → 16–end-of-month), for provenance and
  period-replace deletes.
- `parse_file(text) -> list[dict]` — split on `|`, skip the header line, **stop
  at the first `Trailer` line**, coerce `quantity` to `int`, `price` to `float`
  (blank/unparseable → `None`), normalize `settlement_date` to `YYYY-MM-DD`,
  compute `dollar_value = quantity * price` (`None` if price missing). Rows with
  no CUSIP or unparseable quantity are skipped. Returns
  `(rows, trailer_count)` so the caller can validate.
- `fetch_period(period, get=..., opener=...) -> (rows, trailer_count) | None` —
  download the ZIP bytes, read the single member, decode with
  `errors="replace"`, parse. Returns `None` on **HTTP 404** (period not yet
  published — same 404→None convention as `edgar.fetch_daily_index`).

Decoding: ZIP bytes → member bytes → `.decode("utf-8", "replace")`. (Latin-1
would also be lossless; `replace` matches the codebase convention in
`http_client.make_opener` and never raises.)

### 2. Schema (`db.py`)

```sql
CREATE TABLE IF NOT EXISTS securities (
    cusip       TEXT PRIMARY KEY,
    symbol      TEXT,          -- most recent non-blank SYMBOL seen
    description TEXT,          -- most recent DESCRIPTION seen
    first_seen  TEXT,          -- earliest settlement_date this cusip appears
    last_seen   TEXT           -- latest settlement_date this cusip appears
);

CREATE TABLE IF NOT EXISTS fails (
    cusip           TEXT NOT NULL REFERENCES securities(cusip),
    settlement_date TEXT NOT NULL,   -- YYYY-MM-DD
    period          TEXT NOT NULL,   -- e.g. '202505a' (provenance + replace key)
    symbol          TEXT,
    quantity        INTEGER NOT NULL,
    price           REAL,
    dollar_value    REAL,            -- quantity * price, NULL if price NULL
    PRIMARY KEY (cusip, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_fails_date   ON fails(settlement_date);
CREATE INDEX IF NOT EXISTS ix_fails_period ON fails(period);
CREATE INDEX IF NOT EXISTS ix_fails_symbol ON fails(symbol);

CREATE TABLE IF NOT EXISTS periods (
    period        TEXT PRIMARY KEY,  -- '202505a'
    settle_start  TEXT NOT NULL,
    settle_end    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    trailer_count INTEGER            -- from the file's trailer, for validation
);

CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    period_count INTEGER NOT NULL,   -- periods ingested this run
    row_count    INTEGER NOT NULL
);
```

Writers:
- `upsert_securities(conn, rows)` — refresh `symbol`/`description`, extend
  `first_seen`/`last_seen` from each row's `settlement_date` (preserve the
  min/max across runs; only overwrite `symbol`/`description` from rows at or after
  the stored `last_seen` so the "latest" label is stable).
- `replace_period(conn, period, rows) -> int` — **`DELETE FROM fails WHERE
  period=?` then bulk `INSERT`.** Period-replace (not upsert) is deliberate: the
  unit of publication is the whole file, and SEC *reposts* occasionally revise a
  period — a plain upsert would leave behind rows the repost dropped. Returns rows
  written.
- `record_period(conn, period, bounds, fetched_at, row_count, trailer_count)` —
  upsert the `periods` provenance row.
- `write_snapshot(conn, captured_at, period_count, row_count) -> id`.
- `max_period(conn) -> str | None`, `has_period(conn, period) -> bool` — for
  incremental skip.
- `prune(conn, keep_days, now_iso)` — **single-table delete of old `snapshots`
  only** (CFTC/FRED shape). **Do NOT cascade into `fails`** — fail history is the
  store. (Consequence: re-running with a later `--start` never deletes older
  rows; the DB is append-only for fails. Documented, not a bug.)

### 3. Views (the screener — the derived signals)

```sql
-- convenience: every fail joined to its security, newest first
CREATE VIEW IF NOT EXISTS v_security_history AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip;

-- (1) latest-date leaderboard, orderable by shares OR dollars
CREATE VIEW IF NOT EXISTS v_latest_fails AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip
WHERE f.settlement_date = (SELECT MAX(settlement_date) FROM fails);

-- global dense rank of distinct settlement dates (settlement days aren't
-- contiguous calendar days — this is the ordinal used for "consecutive")
CREATE VIEW IF NOT EXISTS v_date_rank AS
SELECT settlement_date,
       DENSE_RANK() OVER (ORDER BY settlement_date) AS drank
FROM (SELECT DISTINCT settlement_date FROM fails);

-- gaps-and-islands: one row per (cusip, unbroken run of >=10k-share days)
CREATE VIEW IF NOT EXISTS v_fail_streaks AS
WITH q AS (
  SELECT f.cusip, f.settlement_date, f.quantity, dr.drank,
         dr.drank - ROW_NUMBER() OVER (PARTITION BY f.cusip
                                       ORDER BY f.settlement_date) AS grp
  FROM fails f JOIN v_date_rank dr USING (settlement_date)
  WHERE f.quantity >= 10000)
SELECT cusip, COUNT(*) AS streak_days,
       MIN(settlement_date) AS streak_start,
       MAX(settlement_date) AS streak_end,
       MAX(quantity) AS peak_quantity
FROM q GROUP BY cusip, grp;

-- (2) Reg SHO threshold PROXY: shares-based persistence (>=5 consecutive
-- settlement days at >=10k shares). Missing the "0.5% of shares outstanding"
-- half by design (no shares-outstanding source). Currently-active streaks first.
CREATE VIEW IF NOT EXISTS v_persistent AS
SELECT k.cusip, s.symbol, s.description, k.streak_days,
       k.streak_start, k.streak_end, k.peak_quantity,
       (k.streak_end = (SELECT MAX(settlement_date) FROM fails)) AS active
FROM v_fail_streaks k JOIN securities s ON s.cusip = k.cusip
WHERE k.streak_days >= 5;

-- (3) spikes: latest fails vs the security's own trailing 20-settlement-day
-- average (excludes the current day). ratio >= 3 => notable jump.
CREATE VIEW IF NOT EXISTS v_spikes AS
WITH w AS (
  SELECT cusip, settlement_date, quantity,
         AVG(quantity) OVER (PARTITION BY cusip ORDER BY settlement_date
                             ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS base
  FROM fails)
SELECT w.cusip, s.symbol, s.description, w.settlement_date,
       w.quantity, w.base,
       CASE WHEN w.base > 0 THEN w.quantity / w.base END AS spike_ratio
FROM w JOIN securities s ON s.cusip = w.cusip
WHERE w.settlement_date = (SELECT MAX(settlement_date) FROM fails)
  AND w.base > 0;
```

Consumers `ORDER BY`/`WHERE` on top (e.g. `v_latest_fails ORDER BY dollar_value
DESC LIMIT 50`; `v_spikes WHERE spike_ratio >= 3`).

### 4. CLI & orchestration (`run.py`)

Period enumeration `periods_in_range(start_month, now)` yields
`["YYYYMMa","YYYYMMb", …]` from the floor month through the current month
(both halves). Default floor = **24 months before `now`**. `--start YYYY-MM`
overrides.

`run(db_path, start=None, keep_days=None, full=False, fetch_period=fetch.fetch_period, now_iso=None)`:
for each period in range, **oldest → newest**:
- **Skip** if `db.has_period` and *not* in the trailing re-fetch window (the last
  `_REFETCH_PERIODS = 2`) and *not* `--full`. (Cheap incremental: don't
  re-download 48 files each run; re-pull only the two newest already-stored
  periods so SEC reposts are absorbed, plus everything new.)
- `fetch_period(period)`; **`None` (404) → not yet published → skip.**
- Validate parsed count vs trailer; warn on mismatch but still write.
- `upsert_securities` + `replace_period` + `record_period`, inside a
  **skip-and-continue** try/except that `conn.rollback()`s and logs only
  `type(e).__name__` (never `str(e)`/`e.url`, matching CFTC's leak-safe logging).

Then `write_snapshot` and optional `prune`. Returns
`(snapshot_id, period_count, row_count)`.

CLI (`main`): `python main.py ftd`
```
--db ftd.db
--start YYYY-MM   earliest publication month (default: 24 months back)
--full            re-ingest every period in range, ignoring the incremental skip
--keep-days N     prune snapshot provenance older than N days (never fails history)
```

### 5. Testing (mirror `test_cftc_*`)

- `test_ftd_fetch.py` — `parse_file`: pipe split, header skipped, **trailer
  stops parsing** and its count is returned, quantity/price coercion (int/float/
  blank→None), `dollar_value` math, date normalization, blank-CUSIP rows skipped;
  `fetch_period` returns `None` on a 404 opener; backoff retries on 403/503 via a
  fake opener; ZIP handling reads the single member regardless of its name.
- `test_ftd_db_schema.py` — schema + all views create idempotently.
- `test_ftd_db_write.py` — `replace_period` **replaces** a period in place (a
  repost that drops a row leaves no orphan; a revised quantity overwrites);
  `upsert_securities` preserves `first_seen`, extends `last_seen`, refreshes
  `symbol`/`description` from the newest row only.
- `test_ftd_db_views.py` — seed a synthetic security failing `≥10k` for 6
  consecutive settlement dates → `v_persistent.streak_days = 6, active = 1`; a
  one-day gap splits the streak; `v_spikes.spike_ratio` ≈ known value on a seeded
  jump; `v_latest_fails` returns only the max settlement date.
- `test_ftd_run.py` — period enumeration bounds (`a`/`b`, 24-month default);
  incremental **skip** of already-stored periods outside the re-fetch window;
  re-fetch of the trailing 2; `None`/404 periods skipped; skip-and-continue on a
  failing period; empty run writes an empty snapshot.
- `test_registry.py` — extend to assert `"ftd"` dispatches.

## Non-goals (YAGNI)

- **Shares-outstanding join** for the full Reg SHO 0.5% rule (additive later;
  needs a second source such as the share-count data in company filings).
- **Pre-2009 legacy FTD files** (different layout/location).
- **Rolling deletion of old `fails`** — history is the store; `--keep-days`
  prunes only `snapshots` provenance, matching CFTC/FRED.
- **Price/return backtesting or T+35-cycle modeling** — this screener only
  *stores* fails and basic signals; strategy logic lives elsewhere in the bot.
- **Automated scheduling** — invoked on demand like the other screeners.

## Environment

No new secrets. FTD needs no API key; the existing descriptive `User-Agent`
(shared with EDGAR) suffices. Nothing added to `.env.example`.
