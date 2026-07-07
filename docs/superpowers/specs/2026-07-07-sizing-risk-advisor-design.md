# Sizing / Risk Advisor Combiner — Design

**Date:** 2026-07-07
**Roadmap item:** 6 (Later — new layers)
**Status:** approved design, pre-plan

## Purpose

Nothing joins the composite scorecard against actual holdings. `portfolio.db`'s
docstring already promises the consumers ("real exposure, whole-book heat")
that don't exist. The advisor is that consumer: a third combiner that reports
current book heat, holdings the composite disagrees with, and a vol-scaled
size cap for newly flagged tickers. Decision *support* only — no order
generation, no automatic sizing; the human stays the execution layer.

## Architecture

New combiner package `sources/combiners/advisor/` with the standard four
files (`catalog.py`, `fetch.py`, `db.py`, `run.py`). It extends the one-way
combiner pipeline: composite forms opinions → scorer grades them → advisor
joins opinions against the real book. The advisor writes only
`data/advisor.db` and never writes back into anything it reads.

`fetch.py` has no network. It ATTACHes source DBs read-only
(`file:...?mode=ro`, connection opened with `uri=True`), one at a time,
scorer-style:

1. **composite.db** — latest snapshot's `ticker_scores`, `market_regime`,
   `v_flagged`, plus contributing `signal_values.signal_id`s per flagged
   ticker and the snapshot's `captured_at` for provenance.
2. **portfolio.db** — `v_latest_positions` and `v_latest_account`, plus
   the `snapshots` header for that snapshot's `captured_at` (read-only,
   never writes, never raw position/account rows — the portfolio
   invariant).
3. **stocks.db, then etfs.db** — `v_latest` rows (`atr`, `close`,
   `priceDate`) for the union of held and flagged symbols. stocks.db wins
   when a symbol appears in both; etfs.db is what resolves crosswalk proxies
   (SPY, XLE, GLD, …).
4. **scorer.db** — `v_signal_efficacy` `reliable` flags for the contributing
   signal ids.

**One-clock rule:** `run.py` binds its own `:today = now_iso[:10]`, used only
for staleness arithmetic. The advisor never reads any
`calendar_now`-dependent view.

Dispatched as `main.py advisor --db data/advisor.db [--keep-days N]`;
registered in root `registry.py` as `"advisor"`.

## Data model (advisor.db — all snapshot-scoped, shared prune cascade)

### Tables

- `snapshots(id, captured_at, equity, cash, buying_power,
  portfolio_captured_at, composite_captured_at, regime, sources_failed)` —
  one row per run. Account scalars and upstream provenance freeze into the
  header because every derived number depends on them; `sources_failed`
  counts upstream DBs that could not be read this run, distinguishing a
  genuinely empty book from a failed read that left the tables empty.
- `position_heat(snapshot_id, symbol, group_name, quantity, market_value,
  atr, price, price_date, heat_dollars, heat_pct, weight_pct, score_sum,
  bullish, bearish, total, atr_stale)` — one row per held position.
  PK `(snapshot_id, symbol)`. ATR-derived columns NULL when the symbol has
  no metrics row; score columns NULL when the composite has no opinion.
- `size_caps(snapshot_id, symbol, direction, score_sum, atr, price,
  cap_shares, cap_dollars, group_name, group_heat_pct, reliable_signals,
  total_signals, exceeds_buying_power, already_held)` — one row per ticker
  in composite's `v_flagged` at run time. PK `(snapshot_id, symbol)`.
  `direction` is `'bullish'`/`'bearish'` from the sign of `score_sum`.

### Views (latest-snapshot scoped, matching the `v_latest_*` idiom)

- `v_latest_heat` — per-position heat rows (latest snapshot).
- `v_book_heat` — one row of book totals: total `heat_dollars`/`heat_pct`,
  position count, `heat_coverage` = share of book market value carrying
  a non-NULL ATR (so missing metrics can never silently understate heat),
  and the header's `sources_failed` (0 positions is only believable when
  0 sources failed).
- `v_group_heat` — CROSSWALK groups collapsed to one bet: `group_name`,
  summed `heat_dollars`/`heat_pct`, member symbol list. Ungrouped symbols
  appear as their own single-member rows.
- `v_disagreements` — held positions where `score_sum < 0`, with
  `strong = (score_sum <= -4 AND total >= 3)` (the `v_flagged` threshold).
- `v_latest_caps` — latest `size_caps` rows.

## Math (catalog.py constants, all tunable)

- **Heat:** `heat_dollars = quantity × ATR`; `heat_pct = heat_dollars /
  equity` — the fraction of equity lost on a one-ATR adverse day. Book heat
  is the sum; group heat sums over CROSSWALK members (exposure adds; the
  group counts as one bet for concentration).
- **Risk budget:** `RISK_BUDGET = 0.01` (1% of equity per position per
  one-ATR adverse day — user-chosen default, 2026-07-07).
- **Size cap** for a flagged ticker:
  `allowed_heat = max(0, RISK_BUDGET × equity − existing_group_heat_dollars)`
  (already carrying the bet through a group sibling shrinks the cap), then
  `cap_shares = allowed_heat / ATR` — **fractional** (Robinhood supports
  fractional shares; flooring to whole shares zeroes every cap on a small
  account) — and `cap_dollars = cap_shares × close`.
  Bearish-direction flags carry NULL cap columns: the book is long-only,
  so a buy-sized cap on an avoid signal would be wrong advice — the row
  itself (direction, score, group) is the advice.
  `exceeds_buying_power = 1` when `cap_dollars > buying_power`
  (informational only, not a second cap). Same-group sibling caps each see
  the same remaining budget — alternatives, not a shopping list.
- **Groups:** `TICKER_GROUP` is built in `advisor/catalog.py` from
  `composite.catalog.CROSSWALK` at import time (direct import — unlike the
  scorer's `CROSSWALK_BENCHMARK` it is not a transformation, so duplication
  buys nothing). A pin test asserts consistency with composite.
- **Efficacy citation:** `reliable_signals` / `total_signals` per flagged
  ticker = how many contributing `(signal_id, via_crosswalk)` evidence
  pairs have a `reliable = 1` row in scorer's `v_signal_efficacy`. Pairs,
  not bare signal ids — the scorer grades the direct and crosswalked
  splits separately, and a signal reliable only on its crosswalked split
  must not cite as direct evidence. `reliable` is the scorer's sample-size
  floor (n_bench ≥ 30), not proof a signal works. Annotation only — it
  never gates or scales the cap; re-weighting stays a human decision.

## Edge & error handling

- **Missing ATR:** `position_heat` row still written with NULL heat columns;
  `heat_coverage` in `v_book_heat` exposes the gap. A flagged ticker with
  no ATR gets a `size_caps` row with NULL `cap_shares`/`cap_dollars` —
  visible, not skipped.
- **Staleness:** `atr_stale = 1` when `priceDate` is more than
  `ATR_MAX_AGE_DAYS = 5` days before the advisor's `:today`. Portfolio age
  is derivable from `portfolio_captured_at`; the advisor runs daily even
  though the portfolio job is Mon–Fri, and simply reports the older snapshot.
- **Empty upstream** (no composite snapshot yet, or empty book): the run
  completes and writes a snapshot header with zero child rows; views yield
  empty results, not errors.
- **Per-item failure:** skip-and-continue with `conn.rollback()`, printing
  only `type(e).__name__` (secret-hygiene rule).
- **Partial source read:** each source's reader applies its results
  all-or-nothing — a failure mid-source leaves that source fully unread
  (never real equity with zero positions masquerading as an empty book)
  and increments `sources_failed` in the header.

## Testing

Fully offline, mirroring the scorer layout:
`tests/test_advisor_{catalog,fetch,db_schema,db_write,db_views,run}.py` plus
a `test_registry.py` entry. Fixtures build minimal composite / portfolio /
stocks / etfs / scorer DBs in tmp dirs. Pin tests: `TICKER_GROUP` ↔
`composite.catalog.CROSSWALK`, `RISK_BUDGET` default, stocks-over-etfs
precedence.

## Schedule & ops

- Slot: **9:12pm America/Phoenix, daily** (`weekly(range(7), 21, 12)`,
  `--keep-days 365`) — after composite (9:05) and scorer (9:10), before
  daily-summary (9:15).
- Update both `deploy/launchd/install.py` (source of truth) and
  `docs/SCHEDULE.md`.

## Out of scope (deliberate)

- Options positions (not present in portfolio.db).
- Folding advisor output into the daily-summary digest (revisit once the
  views prove useful interactively).
- Any automatic sizing, ordering, or composite re-weighting — the advisor
  reports; the human decides.
