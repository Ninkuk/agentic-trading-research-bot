# CBOE Options Screener — Design Spec

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Package:** `cboe_options/` (dispatcher name: `options`)

## 1. Purpose

Add a daily options-data screener that snapshots rich per-contract options data
(implied volatility, greeks, open interest, volume) for a curated watchlist of
tickers and stores it in SQLite. The screener follows the existing
`fetch` / `db` / `run` triad convention (closest template: `finra_short_volume/`)
and registers in the central dispatcher as `options`.

The daily snapshot **is** the product: the highest-value signals (IV Rank,
open-interest change) do not exist in any free feed and must be manufactured by
accumulating daily snapshots and comparing against our own history. Value
compounds the longer the job runs — Vol/OI spikes and put/call ratios are
available day 1; true IV Rank lights up once ~1 year of history accumulates.

## 2. Data source

**Primary (and only, for v1): CBOE delayed-quotes CDN JSON.**

- Equities/ETFs: `https://cdn.cboe.com/api/global/delayed_quotes/options/{TICKER}.json`
- Indices: `https://cdn.cboe.com/api/global/delayed_quotes/options/_{TICKER}.json`
  (leading underscore — e.g. `_SPX.json`, `_VIX.json`)

**Why this source** (verified live 2026-07-03):
- Free, no API key, no account, no ToS gray area — it is the public data behind
  CBOE's own delayed-quote web widget.
- One GET per ticker returns the **entire chain across all expirations** with
  per-contract greeks + IV. `AAPL.json` returned 3,650 contracts (~1.6 MB).
- ~15-minute delayed — fine for an end-of-day daily job.

**Rejected alternatives** (see research notes in conversation):
- *Robinhood MCP* — equally rich and already integrated, but its ToS prohibits
  automated access (account-risk gray area for an unattended cron). Deferred: the
  schema carries a `source` column so it can be layered in later as a cross-check.
- *Polygon / Alpha Vantage / Marketdata* — cost money or serve placeholder data on
  free tiers; Polygon free (5 req/min) is too slow for a watchlist.
- *CBOE daily-statistics dashboard page* (the URL originally proposed) — aggregate
  market stats only, no per-ticker chains, requires HTML scraping. Superseded.

**Gotchas to handle:**
- Undocumented/unofficial endpoint — can change without notice. Isolate parsing so
  a schema drift fails loudly in one place.
- Deep-OTM / illiquid contracts often report `iv: 0.0`, `delta` at 0 or 1, and
  zero greeks. Store as-is (do not special-case); downstream views filter.
- Index payloads are large (`_SPX.json` ≈ 13 MB). Acceptable, but indices are the
  heaviest requests in the run.
- Data is delayed and reflects the most recent session. On weekends/holidays the
  endpoint returns the prior session — `snapshot_date` must be derived from the
  payload, not the wall clock (see §5).

## 3. Response shape (fields we consume)

Top level: `{ "timestamp", "symbol", "data": { ... } }`

`data` (underlying-level) fields used:
- `current_price`, `close`, `prev_day_close`, `volume`
- `iv30` — 30-day implied volatility; the IV-Rank input we accumulate
- `options` — array of per-contract objects

Per-contract (`data.options[i]`) fields used:
- `option` — OCC symbol, e.g. `AAPL260717C00220000` (parsed for expiration / type / strike)
- `bid`, `ask`, `bid_size`, `ask_size`, `last_trade_price`, `theo`
- `iv`, `delta`, `gamma`, `theta`, `vega`, `rho`
- `open_interest`, `volume`

**OCC symbol parsing** (`{ROOT}{YYMMDD}{C|P}{STRIKE*1000, 8 digits}`):
- root = leading alpha (variable length; may differ from request symbol for
  adjusted contracts — trust the parsed root, keyed under the request `underlying`)
- expiration = `20YY-MM-DD` from the 6 digits after root
- type = `C` → `call`, `P` → `put`
- strike = trailing 8 digits / 1000.0

## 4. Universe (catalog)

`cboe_options/catalog.py` — a frozen dataclass list in the `cftc_screener/catalog.py`
shape, with `select_symbols(all, only, exclude, add)` resolution and `--only`,
`--exclude`, `--add` CLI flags (comma-split). Each entry records the request symbol
and whether it is an index (drives the `_` prefix).

Starter set (~24, editable):
- Mega-cap tech: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA
- High-volume single names: AMD, NFLX, AVGO, PLTR, COIN, MSTR, SMCI
- Liquid other: JPM, BAC, XOM, DIS, BABA
- ETFs: SPY, QQQ, IWM
- Indices (`_` prefix): _SPX, _VIX

## 5. Storage (SQLite)

Connection via shared `screener_common.connect` (WAL). Schema is
`CREATE TABLE/VIEW IF NOT EXISTS` only, applied idempotently by `ensure_schema`
at the top of every `run()`. Default DB path `cboe_options.db`.

**`snapshot_date` derivation:** the trading date the data represents — the
underlying's `data.last_trade_time` date, falling back to the top-level
generation `timestamp` date, and finally to `now_iso[:10]` in `run()` if neither
parses. NOT the wall-clock run date — so a weekend re-run keys to the real prior
session instead of creating a bogus dated row.

### Tables

`underlyings` — dimension:
- `symbol TEXT PRIMARY KEY`, `is_index INTEGER`, `first_seen TEXT`, `last_seen TEXT`
- upsert with `first_seen = MIN(...)`, `last_seen = MAX(...)`

`option_snapshots` — core fact, one row per contract per day per source:
- PK `(snapshot_date, occ_symbol, source)`
- `underlying TEXT`, `expiration TEXT`, `strike REAL`, `type TEXT`
- `bid REAL, ask REAL, mark REAL, last REAL, theo REAL`
  (`mark` is derived: midpoint `(bid + ask) / 2` when both present, else `NULL`;
  `last` = `last_trade_price`; `theo` = CBOE `theo`. CBOE has no native mark field.)
- `iv REAL, delta REAL, gamma REAL, theta REAL, vega REAL, rho REAL`
- `open_interest INTEGER, volume INTEGER`
- `underlying_price REAL`
- `vol_oi_ratio REAL` — precomputed `volume / max(open_interest, 1)`
- `source TEXT DEFAULT 'cboe'`, `fetched_at TEXT`
- indexes on `(underlying, snapshot_date)` and `(snapshot_date)`

`underlying_daily` — per-ticker daily rollup:
- PK `(snapshot_date, underlying)`
- `iv30 REAL` (IV-Rank input)
- `total_call_volume INTEGER, total_put_volume INTEGER, put_call_volume_ratio REAL`
- `total_call_oi INTEGER, total_put_oi INTEGER, put_call_oi_ratio REAL`
- `underlying_price REAL`

`days` — provenance: `snapshot_date TEXT`, `underlying TEXT`, `fetched_at TEXT`,
`row_count INTEGER`, PK `(snapshot_date, underlying)`.

`snapshots` — run header: `id INTEGER PRIMARY KEY AUTOINCREMENT`,
`captured_at TEXT`, `symbol_count INTEGER`, `row_count INTEGER`.

### Views

- `v_unusual_activity` — contracts for the latest `snapshot_date` ordered by
  `vol_oi_ratio DESC` with a sane floor on `open_interest` and `volume`. Works day 1.
- `v_iv_rank` — for each underlying's latest `iv30`, its rank/percentile within
  that underlying's trailing `underlying_daily.iv30` history. Returns meaningful
  values only after history accumulates (documented in a view comment).

### Write semantics

**Replace-per-day, per-ticker** (FINRA `replace_day` pattern): within a
transaction, `DELETE FROM option_snapshots WHERE snapshot_date=? AND underlying=? AND source='cboe'`
then bulk-insert the parsed rows; upsert the `underlying_daily` and `days` rows.
Makes a same-day re-run idempotent and lets a shrunk chain leave no orphans.
Column list defined once as a module constant, reused for INSERT columns +
`:named` placeholders. Every writer ends with `conn.commit()`.

### Pruning

Single-table `prune(conn, keep_days, now_iso)` that deletes only `snapshots`
run-header rows older than the cutoff (`fromisoformat(now_iso) - timedelta(days=keep_days)`
compared as string against `captured_at`). **Historical `option_snapshots` /
`underlying_daily` data is never pruned** — the accumulated history is the asset.
Docstring must state this explicitly (mirrors FINRA/CFTC prune warnings).

## 6. Modules

`cboe_options/fetch.py`:
- Constants: `BASE = "https://cdn.cboe.com/api/global/delayed_quotes/options"`,
  `_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}`,
  `_RETRY_STATUS = frozenset({429, 503})`, `_MAX_ATTEMPTS`, `_BASE_DELAY`.
- `chain_url(symbol, is_index)` → applies `_` prefix for indices.
- `_http_get(url, opener=_urlopen, ...)` — thin `http_client.http_get` wrapper.
- `parse_occ(option) -> (root, expiration, type, strike)`.
- `parse_chain(payload) -> (underlying_dict, list[contract_dict])` — pure, no I/O;
  coerces numbers with a `_num(raw, cast)` helper returning `None` on blank.
- `fetch_chain(symbol, is_index, get=_http_get) -> payload | None` — returns `None`
  on 404 (delisted/unavailable ticker) so `run()` skips it.

`cboe_options/db.py`:
- `from screener_common import connect` (re-exported in `__all__`).
- `_SCHEMA`, `_VIEWS`, `ensure_schema`.
- `upsert_underlying`, `replace_day` (contracts), `upsert_underlying_daily`,
  `record_day`, `write_snapshot`, `stored_days`, `prune`.

`cboe_options/run.py`:
- `run(db_path, symbols=None, keep_days=None, now_iso=None, fetch_chain=fetch.fetch_chain) -> (snapshot_id, symbol_count, row_count)`.
  Injectable `fetch_chain` + `now_iso` for deterministic tests. Per-ticker
  `try/except Exception`: `conn.rollback()`, print
  `warning: skipping {symbol}: {type(e).__name__}` to stderr (**never `str(e)`**),
  continue. Snapshot header always written, even with zero successes.
- `main(argv=None)` — argparse: `--db` (default `cboe_options.db`), `--only`,
  `--exclude`, `--add`, `--keep-days`. Prints a one-line summary.

`registry.py` — add `from cboe_options.run import main as options_main` and
`REGISTRY["options"] = options_main`.

## 7. Testing

Parallel test set in `tests/` (network never hit; fetch injected):
- `test_options_fetch.py` — `parse_occ` cases (call/put, index roots, adjusted
  roots), `parse_chain` from a saved JSON fixture, `fetch_chain` 404→`None`,
  backoff via fake opener + `sleep=list.append`, non-retryable status re-raises.
- `test_options_db_schema.py` — `connect(":memory:")`, `ensure_schema` twice
  (idempotent), assert all tables + views exist via `sqlite_master`.
- `test_options_db_write.py` — `replace_day` overwrites in place (no dup, no
  orphan on shrink), dimension upsert `first_seen`/`last_seen`, rollup ratios,
  `vol_oi_ratio` precompute.
- `test_options_run.py` — injected fake `fetch_chain`, real `tmp_path` DB,
  `now_iso` pinned; asserts snapshot header written, skip-and-continue on a
  failing ticker, and **secret hygiene**: stderr contains the symbol and the
  exception class name but NOT the exception message string.
- `tests/test_registry.py` — add `test_dispatch_lists_options`.

## 8. Non-goals (v1, YAGNI)

- No Robinhood source (schema-ready via `source` column; deferred for ToS reasons).
- No IV-skew / term-structure analytics.
- No alerting / notifications.
- No intraday polling — one EOD snapshot per day.

## 9. Usage

```
python main.py options --keep-days 90
python main.py options --only AAPL,NVDA
python main.py options --add _RUT --exclude BABA
```
