# Signal Combiner (`composite`) — Design Spec

Date: 2026-07-06
Status: approved design, pre-implementation

## Purpose

The ~21 per-source DBs each answer a local question ("is copper positioning extreme?",
"is the curve inverted?"). The combiner answers the global one: **"given everything we
collected, what is the market picture right now, and which tickers stand out?"** — and
records that answer with the same snapshot provenance as every other source, so the
composite's own history becomes the dataset a future paper-trading loop is scored against.

Consumers are deliberately unspecified: the output is a machine-queryable SQLite DB
(`data/composite.db`). Claude sessions query it directly; a nightly ntfy digest or a rule
engine are later `SELECT`s over the same tables, not v1 concerns.

## Placement: a third source kind

The combiner reads no external feed, so it is neither a screener nor a monitor. New kind:

```
sources/
├── common/
├── screeners/      # read the outside world
├── monitors/       # track forward event dates
└── combiners/      # read our own DBs
    └── composite/
        ├── __init__.py
        ├── catalog.py   # SIGNALS + CROSSWALK (the curated judgment)
        ├── fetch.py     # pure extraction against an attached conn (no network)
        ├── db.py        # composite schema, views, prune
        └── run.py       # run(...) + main(argv)
```

`sources/combiners/__init__.py` is added. The package imports `screener_common`
(`connect`, `prune`) like screeners do; no new common module is needed for one combiner.
Registered as `composite` in `registry.py` (a source "ships" only once registered).

## Architecture: two-phase run

SQLite's attached-DB limit is 10 (verified on this machine's Python); we have 21+ source
DBs. Therefore extraction is **sequential per source**, never all-at-once:

**Phase 1 — extract.** For each source in the catalog: `ATTACH 'file:data/<src>.db?mode=ro'`,
run that source's extraction SQLs binding `:today`, write normalized rows into
`signal_values`, `DETACH`. A source failure (missing file, schema drift, empty table) is
skip-and-continue: print `type(e).__name__` only (secret-hygiene invariant), record
nothing for that signal, move on. A collector that failed last night must not take down
the composite.

**Phase 2 — combine.** With all extractions written, compute `market_regime` (one row)
and `ticker_scores` (one row per ticker) inside `composite.db` from this snapshot's
`signal_values`. No source DB is attached during phase 2.

### The one-clock rule

The combiner NEVER reads a source view that depends on that source's `calendar_now`
singleton (each was set by that source's own last run — joining across them mixes clocks,
and read-only attaches can't `set_today`). Affected modules: all four monitors
(`v_upcoming`/`v_imminent`/derivatives), `treasury.v_upcoming_auctions`, `fred.v_asof`.
For those, extraction SQL queries the base tables (`events`, `observation_vintages`, …)
with the combiner's own injected `:today` bound parameter. All other screener views
(e.g. `cftc.v_cot_index_latest`, `finra.v_ratio_spikes`) are safe to read directly.

Time enters `run()` solely as injected `now_iso` (UTC isoformat), per the repo invariant.
`:today` is `now_iso[:10]`.

## catalog.py — where the judgment lives

```python
Signal = {
    "signal_id":       "cftc_mm_extreme",     # stable name, unique
    "db":              "cftc.db",             # file under --db-dir
    "grain":           "asset_class",         # market | asset_class | ticker
    "sql":             "SELECT ... :today ...",  # returns rows (entity, raw_value, score, obs_date)
    "staleness_budget_days": 10,              # advisory; recorded, never filtered on
}
SIGNALS = [ ... ]                             # ~15–20 entries for v1
```

Score semantics: **integer −2…+2, positive = bullish for that entity**, with any
contrarian interpretation (e.g. crowded shorts → bullish squeeze risk) applied inside the
extraction SQL, not by consumers. Thresholds live in the SQL (percentile/z cutoffs per
signal); `signal_values` stores both `raw_value` and `score` so thresholds are auditable
and revisable.

`CROSSWALK`: curated mapping `asset_class/theme → [tickers]`, e.g.
`energy → XLE, XOM, CVX`; `metals → GDX, FCX, COPX`; `rates → TLT`;
`equity_index → SPY, QQQ`; `ags`/`softs` → DBA, and per-commodity ETFs as coverage grows.
An asset-class signal contributes its score to each mapped ticker, tagged
`via_crosswalk = 1` in `signal_values` so direct and mapped evidence are distinguishable.

`select_ids(only, exclude, add)` selection helpers, same shape as every other catalog.

### v1 signal starter set (illustrative, finalized during implementation)

- **market**: fred T10Y2Y level/inversion, HY spread, VIX level, VIX term backwardation,
  equity PCR percentile (cboe base tables + `:today`), FOMC blackout flag (fomc `events`),
  count of imminent high-impact releases (econ_calendar `events`), days to next OPEX
  (market_calendar `events`), RRP trend (nyfed), TGA trend (treasury base tables).
- **asset_class**: CFTC managed-money COT-index extremes per asset class (disagg),
  leveraged-funds extremes (TFF), EIA weekly crude/nat-gas surprise direction,
  USDA stocks-to-use extremes.
- **ticker**: FINRA days-to-cover spikes and short-interest spikes, short-volume ratio
  spikes/streaks, FTD persistence/spikes, Reddit trending, EDGAR insider-activity
  clusters, stocks.db technicals (RSI extremes, `ma50vs200` cross, `positionInRange`),
  ATS dark-pool share anomalies.

Ticker universe = whatever the ticker-grain extractions + crosswalk + portfolio holdings
actually produce. No curated universe list to maintain.

## db.py — schema

All three domain tables are **snapshot-scoped** (FK to `snapshots(id)`, pruned by the
shared cascade — the composite's value is its replayable history):

```sql
snapshots(id, captured_at, ...)                    -- standard provenance header

signal_values(
  snapshot_id, signal_id, grain, entity,           -- entity: '*' | asset_class | ticker
  raw_value REAL, score INTEGER,                   -- score in −2..+2
  obs_date TEXT, staleness_days REAL,              -- vs. run's :today
  via_crosswalk INTEGER DEFAULT 0,
  PRIMARY KEY (snapshot_id, signal_id, entity))

market_regime(
  snapshot_id PRIMARY KEY,
  t10y2y REAL, curve_inverted INT, hy_spread REAL, vix REAL, vix_backwardation INT,
  equity_pcr_pctile REAL, in_fomc_blackout INT, imminent_high_impact INT,
  days_to_opex INT, rrp_trend TEXT, tga_trend TEXT,
  regime TEXT,                                     -- 'risk_on' | 'risk_off' | 'mixed'
  inputs_expected INT, inputs_present INT)         -- coverage, always visible

ticker_scores(
  snapshot_id, symbol,
  bullish INT, bearish INT, total INT,             -- counts of signals with score >0 / <0 / present
  score_sum INT,                                   -- sum of scores (−2..+2 each)
  coverage REAL,                                   -- total / applicable ticker signals
  worst_staleness_days REAL,
  in_portfolio INT DEFAULT 0,
  PRIMARY KEY (snapshot_id, symbol))
```

**Combination rule for v1 is counting, not weighting.** Weighted composites are the
highest-overfitting-risk component; if ever wanted they are a later view over
`signal_values`, not a schema change. `regime` is a simple SQL CASE over the regime
fields (documented in the view), not a fitted model.

Views (LEFT JOIN everywhere; NULLs and visible coverage instead of errors):

- `v_latest_regime` — most recent `market_regime` row.
- `v_latest_scorecard` — most recent `ticker_scores`, joined to per-signal detail counts.
- `v_flagged` — tickers from the latest snapshot with `ABS(score_sum) >= 4 AND total >= 3`
  (constants named at the top of db.py's SQL; tunable, documented as such).
- `v_score_history` — `(captured_at, symbol, score_sum, coverage)` over all snapshots —
  the future paper-trading dataset.

`prune`: standard `screener_common` snapshot cascade over the three domain tables
(`--keep-days`, fixed-width UTC isoformat timestamps as everywhere).

## run.py

`run(conn, db_dir, now_iso, only=None, exclude=None, add=None)` with seams for tests
(`now_iso` injected; extraction goes through `fetch.py` functions that take a connection).
Per-signal skip-and-continue with `conn.rollback()` + `type(e).__name__` on failure.
Thin `main(argv)`: `--db` (default `composite.db` — pass `data/composite.db`, same
gotcha as every source), `--db-dir data`, `--only/--exclude/--add`, `--keep-days`.

## Testing

Mirrors the standard layout: `tests/test_composite_{catalog,fetch,db_schema,db_write,db_views,run}.py`.
Fixtures build **real miniature source DBs in tmp_path by calling each source's own
`ensure_schema` and inserting a few rows** — combiner tests then fail loudly if a source
schema drifts. Fully offline; `now_iso` injected; includes: missing source file →
coverage drops but run succeeds; crosswalk fan-out; staleness computation; one-clock rule
(monitor events filtered by `:today`, not the source's stale `calendar_now`).

## Ops

- Register `composite` in `registry.py` + add `test_registry.py` entry.
- One new LaunchAgent (`com.tradingbot.composite`) slotted **after** the nightly
  collectors in `deploy/launchd/install.py`; update `docs/SCHEDULE.md` (both, per repo rule).
- `CLAUDE.md`: add `combiners/` to the file-tree section and note the third kind.

## Out of scope for v1 (deliberate)

Weighted/fitted composites, regime-conditional scorecards, digest/ntfy formatting,
paper-trade recording, any ML, additional combiners (the `combiners/` dir earns its
plural later). All are views or small consumers over `signal_values`.
