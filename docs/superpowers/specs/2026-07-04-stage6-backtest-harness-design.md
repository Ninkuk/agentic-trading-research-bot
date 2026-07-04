# Stage 6 — Backtest & Validation Harness (`trials`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 6 ·
[research §7](../../research/2026-07-03-signal-to-candidate-pipeline.md) (🟢).
**Must exist before Stage 2's thresholds get tuned** — the single most important
number in any backtest is how many variations were tried, and that count is only
right if it's logged from trial #1.

## Scope decision (the honest one)

A *retrospective* price backtest needs years of survivorship-clean price history,
which this repo deliberately does not store (official-sources policy; stockanalysis
snapshots only accumulate forward from when the screener started). So v1 is **not** a
historical simulator. It is three things the research says are non-optional, all
buildable now:

1. **Trial registry + Deflated Sharpe Ratio** — the multiple-testing ledger.
2. **Walk-forward evaluation** over the pipeline's own accumulated snapshots — leads
   and candidates are already stored per-run with `as_of_date`; as snapshots pile up,
   every past lead can be scored against subsequently-observed prices from later
   `stocks.db` snapshots. Slow, but zero look-ahead **by construction**.
3. **Point-in-time discipline** — tradability mask + ALFRED vintages — so the data
   feeding (2) is honest.

Retro price backfill (candidate source: stockanalysis historical endpoints — the
already-trusted exception) is a separate future decision, tracked in FOLLOWUPS, and
slots in *under* this harness without changing its schema.

**Retention prerequisite (pinned):** walk-forward is only as long as the snapshot
history it scores against, and today every DB it needs is run with `--keep-days 90`
(and `stocks.db`/`leads.db` cascade-prune their fact rows). The DBs this harness
evaluates — `stocks.db`, `etfs.db`, `leads.db`, `candidates.db` — must be run with
long retention (`--keep-days 3650`, or omit `--keep-days` so no prune fires) from the
moment Stage 1 ships. The Stage 5 scheduler's `argv_fn`s are where that retention
policy is set. Without this, "as snapshots pile up" is false by configuration.

## Package shape

`pipeline/trials/`: `catalog.py` (metric definitions), `stats.py` (pure math: Sharpe,
skew/kurtosis, DSR — replaces `fetch.py`; no I/O at all), `db.py` (`trials.db`),
`run.py` (`"trials"` in `registry.py`).

## 1. Trial registry — `trials.db`

```sql
trials(trial_id INTEGER PRIMARY KEY AUTOINCREMENT,
       registered_at TEXT NOT NULL,          -- injected now_iso
       stage TEXT NOT NULL,                  -- 'leads' | 'promote' | 'gate' | ...
       description TEXT NOT NULL,
       params TEXT NOT NULL,                 -- canonical JSON of every knob in the trial
       params_hash TEXT NOT NULL,            -- sha256 of params
       git_rev TEXT,
       family TEXT NOT NULL DEFAULT 'default', -- DSR trial-count scope (see below)
       UNIQUE (stage, family, params_hash)); -- family-scoped: identical params JSON in two
                                             -- different families/stages are DIFFERENT trials;
                                             -- a global UNIQUE would cross-contaminate their Ns

trial_results(trial_id INTEGER REFERENCES trials(trial_id),
              evaluated_at TEXT NOT NULL, window_start TEXT, window_end TEXT,
              n_obs INTEGER, sharpe REAL, skew REAL, kurtosis REAL,
              hit_rate REAL, avg_return REAL, max_drawdown REAL,
              dsr_at_eval REAL, n_at_eval INTEGER, -- DSR AS OF evaluation time, and the family
                                                   -- N it was computed against — stored DSRs go
                                                   -- stale as the family grows; the live number
                                                   -- comes from --leaderboard (below)
              detail TEXT,
              PRIMARY KEY (trial_id, evaluated_at));

snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          trial_count INTEGER, result_count INTEGER);
```
Append-only in spirit; `params_hash UNIQUE` makes re-registering a tried combination a
no-op that returns the existing `trial_id` (so the N in DSR never undercounts).
`family` scopes the DSR trial count: all variations aimed at the same decision (e.g.
"stage2-liquidity-floor") share a family; N = count of trials in the family.

**Discipline hook:** Stage 2's spec requires every threshold change to register a
trial. The workflow is `main.py trials --register` *before* running the variant.

## 2. DSR — `stats.py` (stdlib math, no numpy)

Bailey & López de Prado (🟢). All computable with `math` + `statistics.NormalDist`
(which provides both `cdf` and `inv_cdf`):

```
SR0  = sd_SR * ( (1-γ)·Φ⁻¹(1 - 1/N) + γ·Φ⁻¹(1 - 1/(N·e)) )   # expected max SR of N
                                                              # random trials
       γ = 0.5772156649 (Euler–Mascheroni), sd_SR = stdev of the family's trial SRs
DSR  = Φ( ( (SR - SR0) · sqrt(T - 1) )
          / sqrt( 1 - skew·SR + ((kurtosis - 1)/4)·SR² ) )
```
`T` = n_obs; skew/kurtosis of the trial's return series (moment formulas in
`stats.py`). **Kurtosis convention pinned: RAW (Pearson) fourth standardized moment,
normal = 3** — the published PSR/DSR denominator assumes it; an excess-kurtosis
(normal = 0) slip flips the term's sign at normality and corrupts every DSR. The test
fixtures include a normal-sample case asserting the denominator ≈
`sqrt(1 + 0.5·SR²)`. `sd_SR` = stdev over the family's trial SRs taking the **latest
evaluation per trial**. Caveat, stated for honesty: re-evaluating the same params on
new windows doesn't add to N (N counts *configurations searched*, per B&LdP) — but
cherry-picking the best *window* for one config is unpenalized selection; don't do it,
report latest-window results. Edge cases pinned: `N < 2` or `sd_SR = 0` → DSR is NULL
with a printed notice (never a fake 1.0).

Because Φ⁻¹ isn't available to SQLite, **live DSR (vs the family's current N) is
computed in Python by the `--leaderboard` command**, not in a SQL view; the stored
`dsr_at_eval`/`n_at_eval` are the frozen at-the-time record.

## 3. Walk-forward evaluation

`main.py trials --evaluate <trial_id>` scores a lead/candidate cohort against later
observed prices:

- Prices come from `stocks.db` (stocks) / `etfs.db` (ETF leads) — the `metrics` wide
  table's columns are **dynamic**, so the harness declares its **required data-point
  ids** (`price`, `low`, `averageVolume`) and fails up front with the missing-id list
  if a DB was built with `--only` excluding them (a clear error beats
  `OperationalError: no such column`).
- Entry price: `price` at the first snapshot **after** the lead's `as_of_date` (t+1
  discipline — never the same-day price).
- Exit: horizon-band default (`weeks` → 20 trading days, `months` → 60) or stop
  breach, whichever first. **Stop-breach caveat, stated honestly:** `low` is the
  snapshot day's low only — a breach on a day inside a snapshot gap is undetected and
  the exit prices at the next available snapshot. That is a wrong-exit-price risk
  (distinct from the n_obs shrinkage below); each evaluation records its
  `max_gap_days` in `detail` so results from gappy history are flagged, not silently
  trusted.
- **Tradability mask at data-load time** (🟢): a name absent from a given snapshot is
  untradable that day (delisted/halted/dropped) — its return path truncates at the
  last snapshot where it existed, and entries can't open on missing days. Trading
  days come from `market_calendar` (`--calendar-db`), never date arithmetic.
- Returns per lead → per-trial return series → `trial_results` row. Gaps in snapshot
  history (screener didn't run) shrink `n_obs` honestly rather than interpolating.

## 4. ALFRED vintages (prerequisite extension to `fred_screener`)

FRED `observations` are upserted in place — revisions overwrite, so any backtest of
the regime rule on today's `fred.db` is look-ahead (the
`incremental-since-misses-revisions` issue at backtest scale). Extension, spec'd here
but implemented in `fred_screener`:

- New table `observation_vintages(series_id, date, realtime_start, value,
  PRIMARY KEY (series_id, date, realtime_start))` — additive; existing tables/views
  untouched.
- `fetch_observations` gains a vintage mode using ALFRED's `realtime_start`/
  `realtime_end` parameters (same endpoint family, same API key, live-verify the
  parameter behavior per the FRED-gotcha memory).
- New view `v_asof(series_id, date, value, realtime_start)` — value as first published
  on or before a given as-of date (filtered via the `calendar_now` param-table
  pattern). The regime-rule evaluation path in this harness reads **only** `v_asof`.
- Backfill: one `--vintages` run per regime series (CPIAUCSL, UNRATE, T10Y2Y,
  BAMLH0A0HYM2) — small, bounded.

## Views

`v_family_leaderboard` (per family: trial count N, best SR, latest results — the "how
hard did we search" report; **live DSR is appended by the `--leaderboard` command in
Python**, since SQL lacks Φ⁻¹), `v_trial_history`, `v_evaluation_coverage`
(snapshot-gap report per window — how much data each evaluation actually had).

## CLI

```
uv run python main.py trials --db trials.db --register --stage promote \
  --family stage2-liquidity --description "ADV floor 5M" --params '{"dollar_volume_floor": 5000000}'
uv run python main.py trials --db trials.db --evaluate 17 \
  --leads-db leads.db --stocks-db stocks.db --etfs-db etfs.db \
  --calendar-db market_calendar.db [--candidates-db candidates.db] [--entry-lag 1]
uv run python main.py trials --db trials.db --leaderboard [--family stage2-liquidity]
```
`run(...)` seams: `connect_ro`, `now_iso`, `git_rev` (injected, not shelled-out in
tests).

## Testing

`tests/test_trials_{catalog,stats,db_schema,db_write,db_views,run}.py` + registry
entry. `stats.py` tested against hand-computed DSR fixtures (including the SR0
expected-max term); walk-forward tested on synthetic snapshot sequences with a known
planted edge and a planted delisting (mask truncation); duplicate-params_hash no-op;
NULL-DSR edge cases.

## Out of scope / deferred

Retro price backfill; transaction-cost modeling (log a fixed per-trade haircut
constant in `params` so it's at least visible); options; portfolio-level backtests
(v1 scores signals, not books); any UI beyond views.
