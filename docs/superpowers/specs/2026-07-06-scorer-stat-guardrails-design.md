# Scorer statistical guardrails — design

Roadmap item 4. The scorer's efficacy views (`v_signal_efficacy`,
`v_bucket_performance`) render a 68% hit rate on n = 12 identically to one
on n = 200, while ~144 simultaneous experiments (24 signals × 3 horizons ×
crosswalk split) guarantee some rows look brilliant by chance. Separately,
crosswalked commodity proxies are graded as excess vs SPY — a mismatched
benchmark that flatters commodity signals whenever equities fall.

## Goals

1. Sample-size honesty: every efficacy row exposes how much evidence backs
   it (n, a binomial confidence interval, a `reliable` flag). Nothing is
   hidden — thin rows are labeled, not filtered.
2. Matched benchmarks: crosswalked signal outcomes are graded against a
   same-asset-class proxy; where no honest benchmark exists, the row is
   explicitly unbenchmarked and graded on raw return only.

Non-goals: t-statistics on mean excess (the roadmap asks for a *crude*
binomial CI on hit rate only); re-benchmarking `ticker_outcomes` /
`regime_outcomes` (ticker rows don't carry crosswalk provenance — residual
noted in roadmap item 8); any multiple-comparison correction beyond
documentation (Bonferroni at 144 experiments would need years of data to
clear; the human reads the caveat instead).

## Approach (chosen: per-row benchmark column)

Rejected alternatives: **view-only matched excess** (re-join `prices` at
read time) bypasses the basis-break guard on the benchmark leg — a split in
the matched ETF would fabricate excess; **unbenchmarking all crosswalk
rows** discards excess grading for the whole commodity book. The chosen
approach stores the benchmark per row at registration and grades it through
the existing maturation SQL, guards intact.

Timing note: `ticker_outcomes` / `signal_outcomes` are empty today (item
2's migration wiped pre-fix pending rows; next-day entry defers steady-state
registration), so there is no historical data to migrate or re-benchmark —
only an idempotent column add.

## 1. Constants — `sources/combiners/scorer/db.py`

Next to `BASIS_BREAK_*` (they parameterize view SQL the same way):

- `WILSON_Z = 1.96` — 95% Wilson score interval.
- `RELIABLE_MIN_N = 30` — minimum benchmarked-sample count for the
  `reliable` flag.

A comment on the efficacy view documents the multiplicity caveat: at 95%,
~144 simultaneous rows imply ~7 chance-significant ones; the CI is
deliberately crude and the human applies judgment.

Wilson is chosen over the Wald interval because Wald collapses to zero
width on small all-hit samples (5-for-5 → "100% ± 0%"), which is exactly
the n=12-looks-brilliant failure this item exists to fix. `sqrt()` is
available (SQLite 3.45.3 math functions confirmed in this environment).

## 2. Matched-benchmark map — `sources/combiners/scorer/catalog.py`

A scorer-owned reverse map keyed by crosswalk ticker (the composite's
`CROSSWALK` fans asset classes out to these):

```python
CROSSWALK_BENCHMARK = {
    # energy -> XLE
    "XLE": None, "XOM": "XLE", "CVX": "XLE", "USO": "XLE",
    # metals -> GLD
    "GLD": None, "GDX": "GLD", "SLV": "GLD", "FCX": "GLD", "COPX": "GLD",
    # ags + softs -> DBA
    "DBA": None, "CORN": "DBA", "SOYB": "DBA", "WEAT": "DBA",
    # rates -> TLT
    "TLT": None, "IEF": "TLT",
    # equity_index -> SPY
    "SPY": None, "QQQ": "SPY", "IWM": "SPY",
}
```

- Class proxies map to `None`: self-benchmarking is degenerate (excess
  identically 0 would bias hit_rate down), so those rows are explicitly
  unbenchmarked and graded on raw return.
- Resolution for a crosswalked row: `CROSSWALK_BENCHMARK.get(entity)` — an
  *unknown* crosswalk ticker (composite adds one later) resolves to `None`
  (unbenchmarked), never falls back to SPY; falling back would silently
  reintroduce the mismatched-benchmark bug this spec removes.
- Sync guard: a catalog test asserts the map's keys equal exactly the union
  of composite `CROSSWALK` ticker lists, and that every non-None benchmark
  is itself a key mapping to None. Drift between the combiners fails CI.
- All five benchmarks are themselves crosswalk tickers, so their closes are
  already harvested into the ledger — no new price source.

Direct (non-crosswalked) signal rows keep `catalog.BENCHMARK` (SPY).

## 3. Schema — `signal_outcomes.benchmark`

- `signal_outcomes` gains `benchmark TEXT` (nullable; NULL = unbenchmarked).
  The `CREATE TABLE` gains the column; `ensure_schema` adds the idempotent
  `PRAGMA table_info` + `ALTER TABLE ADD COLUMN` pattern (as in
  `stock_analysis_screener/db.py`) for DBs created before this change.
- Views switch from `CREATE VIEW IF NOT EXISTS` to `DROP VIEW IF EXISTS` +
  `CREATE VIEW` in `_SCHEMA`, so view edits (this one and future ones)
  deploy on the next nightly run instead of silently staying stale.

## 4. Registration — `register_snapshot`

For each signal row: resolve the row's benchmark symbol (crosswalked → map
lookup; direct → SPY), store it in the new column, and look up
`bench_entry_close` for *that* symbol at the row's entry date (NULL
benchmark → NULL close). The map is passed in as a parameter
(`crosswalk_benchmark`) from `run.py`, keeping `db.py` free of catalog
imports for config the caller owns — consistent with how `benchmark` and
`horizons` already flow.

`ticker_outcomes` and `regime_outcomes` registration is unchanged (SPY).

## 5. Maturation — per-row benchmark

`_MATURE_SYMBOL` gains a `bench` format slot for the three places the
benchmark symbol appears (exit-close lookup, `bench_fwd_return`, the
benchmark-leg break scan):

- `ticker_outcomes`: `:bench` (SPY), as today.
- `signal_outcomes`: the row's own `benchmark` column.

Consequences, both intended:

- Unbenchmarked rows (`benchmark IS NULL`) mature normally with
  `bench_fwd_return` NULL — the break scan's `a.symbol = NULL` matches
  nothing, so the benchmark-leg guard self-disables.
- A basis break in a *matched* benchmark (e.g. XLE splits inside the
  window) holds its dependent rows pending forever — the same
  refuse-to-grade principle the guard already applies to SPY.

`_MATURE_REGIME` is unchanged.

## 6. Views

`v_signal_efficacy` (grouped by `signal_id, via_crosswalk, horizon` as
today) gains:

- `n_bench` — count of matured rows with a computable hit (non-NULL
  `bench_fwd_return`). This — not `n_matured` — is the binomial n, because
  `hit_rate` already skips benchmark-less rows. `n_matured - n_bench` is
  the explicit unbenchmarked count.
- `avg_directional_return` — `AVG(fwd_return * sign(score))`, so
  unbenchmarked rows still show a graded number alongside
  `avg_directional_excess` (which is NULL-skipped for them).
- `hit_ci_lo`, `hit_ci_hi` — Wilson score interval on `hit_rate` at
  `WILSON_Z`, NULL when `n_bench = 0` (CASE-guarded).
- `reliable` — `n_bench >= RELIABLE_MIN_N` (0/1).
- `benchmarks` — `GROUP_CONCAT(DISTINCT benchmark)`: each row states what
  it was measured against.

`v_bucket_performance` gains the same guardrail columns (`n_bench`,
`hit_ci_lo`, `hit_ci_hi`, `reliable`); its benchmark stays SPY throughout
so no `benchmarks`/`avg_directional_return` columns are needed. Rows with
`score_sum = 0` have no direction and contribute NULL hits (as today);
their CI/`reliable` columns follow the same `n_bench` accounting.

`v_regime_performance` has no hit rate — untouched.

Wilson at confidence z, with p = observed hit rate and n = `n_bench`:

```
center = p + z²/2n
margin = z * sqrt(p(1-p)/n + z²/4n²)
ci     = (center ± margin) / (1 + z²/n)
```

## 7. Testing (offline, as always)

- `test_scorer_catalog`: map/composite `CROSSWALK` sync (exact key set);
  every non-None benchmark maps to None; constants sane.
- `test_scorer_db_schema`: `benchmark` column present on fresh create; an
  old-shape DB (table created without the column) gains it via
  `ensure_schema`, idempotently.
- `test_scorer_db_write`: benchmark resolution on register — matched
  (XOM→XLE), direct (→SPY), class proxy (XLE→NULL), unknown crosswalk
  ticker (→NULL); `bench_entry_close` comes from the row's own benchmark.
- `test_scorer_db_views`: one Wilson interval verified against a
  hand-computed value; `reliable` boundary at n = 29 vs 30; small all-hit
  sample yields a non-degenerate CI; `n_bench` < `n_matured` when
  unbenchmarked rows exist; hit computed vs the matched benchmark, not SPY.
- `test_scorer_run` (mature): a signal row matures against its own
  benchmark; an unbenchmarked row matures with NULL `bench_fwd_return`; a
  split in the matched benchmark holds dependent rows pending while other
  rows mature.

## 8. Docs

- Prune roadmap item 4; item 6's "depends on #4" and item 8's weighting
  note reference the shipped guardrails.
- No `SCHEDULE.md` change (no cadence or job change).
