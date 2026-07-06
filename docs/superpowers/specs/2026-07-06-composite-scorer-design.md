# Composite Scorer (`scorer`) — Design Spec

Date: 2026-07-06
Status: approved design, pre-implementation

## Purpose

The `composite` combiner states opinions nightly (regime tag, per-ticker vote scores);
nothing measures whether those opinions predict anything. The scorer is the measuring
instrument: it materializes **forward returns for every matured composite score** into a
permanent dataset, so questions like "do +3 tickers outperform −3 tickers over the next
two weeks?", "which of the 23 signals actually predicts?", and "do risk_off nights
precede weak markets?" get answered by data instead of vibes.

Design consequence, stated up front: **the scorer grades; it never influences.** No code
path feeds outcomes back into the composite. Any future re-weighting of the catalog is a
human decision made by reading scorer views — that separation is why this is a second
combiner and not an extension of `composite`.

## Placement

```
sources/combiners/
├── composite/        # states opinions (existing)
└── scorer/           # grades them (this spec)
    ├── __init__.py
    ├── catalog.py    # HORIZONS, buckets, benchmark, price-source list
    ├── fetch.py      # harvest (symbol, price_date, close) from attached sources
    ├── db.py         # scorer.db schema, registration/maturation writers, views, prune
    └── run.py        # harvest → register → mature; main(argv)
```

Registered as `scorer` in `registry.py`; DB at `data/scorer.db`; nightly launchd slot at
**9:10pm** (after `composite` at 9:05, before `daily-summary` at 9:15) — the 29th
`com.tradingbot.*` LaunchAgent. All existing combiner invariants apply verbatim: stdlib
only, no network, sources attached `file:...?mode=ro` one at a time (connection opened
`uri=True`), injected `now_iso`, skip-and-continue printing `type(e).__name__` only,
offline tests with miniature source DBs built by each source's own `ensure_schema`
(including **composite.db itself** — the schema-drift guard now covers the
composite→scorer seam).

## Verified data facts this design rests on (2026-07-06)

- Scored tickers' prices live in `stocks.db`; SPY/QQQ/TLT/XLE and all other crosswalk
  ETFs live in `etfs.db`. Both expose `(symbol, priceDate, price, close, …)` per
  snapshot via the same schema; `close` is the official close for `priceDate`.
- `priceDate` is a correct trading-day sequence (holiday gaps already handled by the
  source) → **"N trading days later" = the Nth distinct `priceDate` after entry.** No
  holiday arithmetic anywhere in the scorer.
- `stocks.db`/`etfs.db` prune at `--keep-days 30`, while a 21-trading-day horizon
  matures ~29–31 calendar days out → scoring lazily at maturity would race the prune.
  Hence the **price ledger**: prices are harvested into `scorer.db` nightly, and the
  scorer never needs a source price after harvest night.

## The three-step nightly run (all idempotent)

1. **Harvest.** Attach `stocks.db`, copy tonight's `(symbol, price_date, close)` for
   symbols the scorer tracks (anything appearing in composite `ticker_scores` or
   ticker-grain `signal_values`, plus the benchmark) into the `prices` ledger
   (`INSERT OR IGNORE`); detach. Repeat for `etfs.db`. Multiple source snapshots sharing
   a `priceDate` dedupe naturally through the ledger's primary key.
2. **Register.** Attach `composite.db`; for every composite snapshot not yet registered,
   write **pending** outcome rows (`INSERT OR IGNORE`) with the entry side filled in
   immediately: entry `price_date` = last ledger date ≤ the composite snapshot's date,
   entry close, and the benchmark's close on the same date. One row per (entity ×
   horizon) for each of the three outcome kinds (below). **One grading per trading
   window:** weekend and same-day-rerun composite snapshots share a benchmark entry
   date; only the first registers outcome rows (later ones record a marker only), so
   duplicate copies of one window can never be counted as independent samples. Detach.
3. **Mature.** Pure SQL inside `scorer.db`: for every pending row where the ledger now
   contains the Nth distinct `price_date` after entry for that symbol, `UPDATE` exit
   date, exit close, forward return, benchmark return, and `matured_at = now_iso`.
   Pending rows whose data hasn't arrived stay pending; missed nights self-heal because
   every step re-scans.

A composite snapshot with no same-day price data (weekend/holiday runs) registers
against the most recent trading close — by construction, since entry is "last ledger
date ≤ snapshot date."

### Scoring convention (documented optimism)

Entry = the close of the last trading day **on or before** the composite snapshot date
("signal-at-close, enter-at-close"). The composite runs after the close using data
through that close, so this is the standard efficacy convention; it is mildly optimistic
versus real next-morning execution. Acceptable because the scorer's question is
**ranking** (do +3s beat −3s?), not P&L simulation. Corollary: scorer results must never
be quoted as achievable returns — the views exist to compare buckets against each other
and against the benchmark under one shared convention.

## What gets scored

Three outcome kinds, each at horizons **5, 10, and 21 trading days** (`catalog.HORIZONS`):

1. **Ticker outcomes** — every `ticker_scores` row of every composite snapshot: carries
   `score_sum`, `total`, `bullish`, `bearish`, `in_portfolio` (copied at registration so
   outcomes are self-contained), entry/exit prices, forward return, and SPY's return
   over the identical window.
2. **Signal outcomes** — every ticker-grain `signal_values` row (`signal_id`, `entity`,
   `score`, `via_crosswalk`): identical mechanics. This is the table that answers
   "which of the 23 signals predicts" — the input to any future catalog re-weighting or
   pruning (~4.3k rows/night measured 2026-07-06; ~8.5k/night across all outcome
   tables, ~3M rows/year — trivial for SQLite).
3. **Regime outcomes** — one row per composite snapshot per horizon: the regime tag
   scored against the benchmark's (SPY's) own forward return.

Market-grain and asset-class-grain signal rows are NOT scored directly in v1 — the
asset-class evidence already reaches ticker grain via the crosswalk (`via_crosswalk=1`
rows are scored and distinguishable), and market-grain signals are graded collectively
through regime outcomes.

## Schema (`data/scorer.db`)

```sql
snapshots(id, captured_at, harvested, registered, matured)   -- run header (counts)

prices(                       -- the ledger; ~1.5k rows/night
  symbol TEXT, price_date TEXT, close REAL,
  PRIMARY KEY (symbol, price_date))

ticker_outcomes(
  composite_snapshot_id INT, composite_date TEXT, symbol TEXT,
  score_sum INT, total INT, bullish INT, bearish INT, in_portfolio INT,
  horizon INT,                              -- 5 | 10 | 21 (trading days)
  entry_date TEXT, entry_close REAL,
  bench_entry_close REAL,
  exit_date TEXT, exit_close REAL,          -- NULL until matured
  fwd_return REAL, bench_fwd_return REAL,   -- (exit/entry) - 1
  matured_at TEXT,
  PRIMARY KEY (composite_snapshot_id, symbol, horizon))

signal_outcomes(
  composite_snapshot_id INT, composite_date TEXT,
  signal_id TEXT, entity TEXT, score INT, via_crosswalk INT,
  horizon INT, entry_date TEXT, entry_close REAL, bench_entry_close REAL,
  exit_date TEXT, exit_close REAL, fwd_return REAL, bench_fwd_return REAL,
  matured_at TEXT,
  PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon))

regime_outcomes(
  composite_snapshot_id INT, composite_date TEXT, regime TEXT,
  horizon INT, entry_date TEXT, bench_entry_close REAL,
  exit_date TEXT, bench_exit_close REAL, bench_fwd_return REAL, matured_at TEXT,
  PRIMARY KEY (composite_snapshot_id, horizon))
```

**Outcome tables are permanent — never pruned.** They are the paper-trading dataset;
deleting them is deleting the experiment. `prune(keep_days)` trims only run headers and
`prices` rows older than 90 days (constant in db.py; must stay > 21 trading days ≈ 31
calendar days with margin). A symbol that IPO'd/delisted mid-window simply never
matures; `v_pending` keeps such rows visible rather than silently dropping them.

## Views (the deliverable)

All bucketing happens here, not in stored data (ELT):

- `v_bucket_performance` — bucket (`strong_bull` ≥ +4, `bull` +2..+3, `neutral` −1..+1,
  `bear` −2..−3, `strong_bear` ≤ −4, each requiring `total >= 2`; single-signal rows
  bucket as `thin`) × horizon: n_matured, avg `fwd_return`, avg excess
  (`fwd_return − bench_fwd_return`), hit rate (share with excess > 0), and — since the
  score is directional — sign-adjusted hit rate for bear buckets (share with excess < 0).
- `v_signal_efficacy` — per signal_id × horizon: n, avg excess **in the score's
  direction** (excess × sign(score)), hit rate; `via_crosswalk` split out so mapped
  evidence is graded separately from direct evidence.
- `v_regime_performance` — per regime tag × horizon: n, avg/min/max `bench_fwd_return`.
- `v_pending` — registered-but-unmatured rows with their earliest possible maturity
  date ("when do results arrive").
- Every view exposes `n` — with weeks of data the counts are tiny, and hiding that
  would manufacture false confidence. No significance testing in v1; the counts are the
  honesty mechanism.

## Error handling

Same skip-and-continue shape as the composite: a missing source DB fails that step for
the night, prints the exception type name only, and the run header records honest
counts. Steps are ordered harvest → register → mature so a harvest failure still allows
maturation of previously-ledgered rows. A registration wave for a composite snapshot is
all-or-nothing per snapshot (transaction), so partially registered snapshots cannot
exist.

## Testing

`tests/test_scorer_{catalog,fetch,db_schema,db_write,db_views,run}.py`, fully offline.
Fixtures build miniature `stocks.db`/`etfs.db`/`composite.db` via those packages' own
`ensure_schema` (drift guard). Must-cover behaviors: trading-day arithmetic via ledger
dates (incl. gaps: entry Friday → +5 lands the following Friday); the prune race
(register with entry, delete the source, mature later from ledger alone); idempotent
re-runs (same night twice = no dupes); pending rows without sufficient forward data stay
pending; weekend composite snapshots enter at Friday's close; benchmark missing → that
night's registrations still write with NULL bench columns rather than failing.

## Ops

- `registry.py` + `test_registry.py`: `scorer`.
- `deploy/launchd/install.py`: `"scorer": (job("scorer", "--keep-days", "365"), weekly(range(7), 21, 10))`
  before `daily-summary`; `docs/SCHEDULE.md` row (after composite 9:05pm, before
  summary 9:15pm; agent count 28 → 29); CLAUDE.md file-tree line for `scorer/`.
- `--keep-days` governs run headers only (outcomes are never pruned; prices ledger has
  its own 90-day constant).

## Out of scope for v1 (deliberate)

Feeding results back into composite weights (human decision, made by reading views);
statistical significance testing (counts are exposed instead); dividend/split
adjustment (close-to-close ≤ 21 trading days; splits surface as outliers — documented
limitation); intraday/next-open entry conventions; ntfy digest lines; scoring
market-grain or asset-class-grain signal rows directly.
