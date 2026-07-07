# Scorer Statistical Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add min-n gating + Wilson confidence intervals to the scorer's efficacy views, and grade crosswalked signal outcomes against matched asset-class benchmarks instead of SPY.

**Architecture:** `signal_outcomes` gains a per-row `benchmark` column resolved at registration from a scorer-owned reverse map (crosswalk ticker → class benchmark ETF; class proxies → NULL = unbenchmarked). Maturation grades each signal row against its own benchmark through the existing gap/basis guards. Both efficacy views gain `n_bench`, Wilson 95% `hit_ci_lo`/`hit_ci_hi`, and a `reliable` flag, computed entirely in SQL (sqlite math functions are available).

**Tech Stack:** Python 3.12 stdlib only (`sqlite3`), pytest (offline), managed with `uv`.

**Spec:** `docs/superpowers/specs/2026-07-06-scorer-stat-guardrails-design.md`

## Global Constraints

- Zero runtime third-party dependencies — stdlib only.
- No network in tests; no wall-clock in the hot path (time enters as injected `now_iso`).
- All four gates must pass before every commit: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`. The pre-commit hook runs them too (~2s).
- Do NOT add a Co-Authored-By line to commits (user's global instruction).
- The outcome tables are empty in production today — no data migration, only an idempotent column add.
- Preserve existing view column ORDER; append new columns at the end (nothing may read positionally, but don't gamble).
- The working tree has unrelated deleted docs (`docs/superpowers/{plans,specs}/2026-07-06-{composite-scorer,signal-combiner}*`) — never `git add -A`; stage files explicitly.
- **Deployment window:** the scorer launchd job runs nightly at 21:10 Phoenix from this working tree, and outcome rows are permanent. If Task 2 ships without Task 3 when that run first registers (2026-07-07 21:10 at the earliest), direct rows would register with `benchmark` NULL and permanently grade unbenchmarked. Complete Tasks 2–4 in one sitting before that run, or `launchctl unload` the scorer job for the duration (see `docs/SCHEDULE.md`).

---

### Task 1: Crosswalk benchmark map in scorer catalog

**Files:**
- Modify: `sources/combiners/scorer/catalog.py`
- Test: `tests/test_scorer_catalog.py`

**Interfaces:**
- Produces: `catalog.CROSSWALK_BENCHMARK: dict[str, str | None]` — keyed by crosswalk ticker; value is the matched benchmark symbol, or `None` for the class proxies themselves (unbenchmarked). Task 3 passes it into `db.register_snapshot`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scorer_catalog.py`:

```python
from sources.combiners.composite import catalog as composite_catalog


def test_crosswalk_benchmark_covers_composite_crosswalk():
    fanned = {t for ts in composite_catalog.CROSSWALK.values() for t in ts}
    # exact key set: drift in either combiner fails here
    assert set(catalog.CROSSWALK_BENCHMARK) == fanned


def test_crosswalk_benchmarks_are_unbenchmarked_class_proxies():
    for ticker, bench in catalog.CROSSWALK_BENCHMARK.items():
        if bench is None:
            continue  # class proxy: explicitly unbenchmarked
        # every benchmark is itself a crosswalk ticker mapping to None
        assert catalog.CROSSWALK_BENCHMARK.get(bench, "missing") is None, (
            f"{ticker} -> {bench}: benchmark must be a class proxy"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_catalog.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'CROSSWALK_BENCHMARK'`

- [ ] **Step 3: Implement the map**

Append to `sources/combiners/scorer/catalog.py`:

```python
# Matched benchmark per crosswalk ticker (composite's CROSSWALK fans asset
# classes out to these). Grading a commodity proxy as excess-vs-SPY flatters
# it whenever equities fall, so each crosswalked row is graded against its
# own asset class. The class proxies themselves map to None: self-benchmark
# is degenerate (excess identically 0), so they grade unbenchmarked (raw
# return only). Resolution uses .get(entity) — an unknown crosswalk ticker
# grades unbenchmarked, never silently vs SPY. A catalog test pins this map
# to composite.catalog.CROSSWALK.
CROSSWALK_BENCHMARK: dict[str, str | None] = {
    # energy -> XLE
    "XLE": None,
    "XOM": "XLE",
    "CVX": "XLE",
    "USO": "XLE",
    # metals -> GLD
    "GLD": None,
    "GDX": "GLD",
    "SLV": "GLD",
    "FCX": "GLD",
    "COPX": "GLD",
    # ags + softs -> DBA
    "DBA": None,
    "CORN": "DBA",
    "SOYB": "DBA",
    "WEAT": "DBA",
    # rates -> TLT
    "TLT": None,
    "IEF": "TLT",
    # equity_index -> SPY
    "SPY": None,
    "QQQ": "SPY",
    "IWM": "SPY",
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_catalog.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/catalog.py tests/test_scorer_catalog.py
git commit -m "feat(scorer): crosswalk-ticker -> class-benchmark map

Pinned to composite.catalog.CROSSWALK by test; class proxies map to
None (unbenchmarked), unknown tickers fail safe to None."
```

---

### Task 2: `benchmark` column + table/view schema split

**Files:**
- Modify: `sources/combiners/scorer/db.py` (the `_SCHEMA` string and `ensure_schema`)
- Test: `tests/test_scorer_db_schema.py`

**Interfaces:**
- Produces: `signal_outcomes.benchmark TEXT` column (nullable); `ensure_schema(conn)` signature unchanged, now idempotently adds the column to pre-existing DBs and rebuilds all views via DROP+CREATE.

**Why the split matters:** views (from Task 5 on) reference `signal_outcomes.benchmark`. SQLite accepts a CREATE VIEW referencing a missing column and only errors when the view is *queried* (verified empirically), so the real requirement is that the ALTER lands before anything queries the views — and the table must exist before `PRAGMA table_info` is useful. Tables → ALTER → views keeps the whole `ensure_schema` pass consistent, and the migration test below queries the view to prove it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scorer_db_schema.py`:

```python
_OLD_SIGNAL_OUTCOMES = """
CREATE TABLE signal_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    entity                TEXT NOT NULL,
    score                 INTEGER NOT NULL,
    via_crosswalk         INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon)
)
"""


def test_signal_outcomes_has_benchmark_column(tmp_path):
    conn = _conn(tmp_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    assert "benchmark" in cols


def test_benchmark_column_migrates_old_db(tmp_path):
    path = str(tmp_path / "old.db")
    raw = sqlite3.connect(path)
    raw.execute(_OLD_SIGNAL_OUTCOMES)
    raw.commit()
    raw.close()
    conn = db.connect(path)
    db.ensure_schema(conn)  # must ALTER the column in before creating views
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    assert "benchmark" in cols
    db.ensure_schema(conn)  # idempotent second run
    views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_signal_efficacy", "v_bucket_performance", "v_pending"} <= views
    # SQLite validates view column refs at QUERY time, not CREATE time —
    # actually querying proves the migrated column satisfies the views
    assert conn.execute("SELECT * FROM v_signal_efficacy").fetchall() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_db_schema.py -v`
Expected: `test_signal_outcomes_has_benchmark_column` FAILS (`'benchmark' in cols` is False); `test_benchmark_column_migrates_old_db` FAILS.

- [ ] **Step 3: Implement**

In `sources/combiners/scorer/db.py`:

**(a)** Rename `_SCHEMA` to `_TABLES` and cut it down to only the `CREATE TABLE` statements (drop the `f` prefix — the basis-break constants move to `_VIEWS`). Add the `benchmark` column to `signal_outcomes`:

```python
_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    harvested   INTEGER NOT NULL DEFAULT 0,
    registered  INTEGER NOT NULL DEFAULT 0,
    matured     INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prices (
    symbol     TEXT NOT NULL,
    price_date TEXT NOT NULL,
    close      REAL NOT NULL,
    PRIMARY KEY (symbol, price_date)
);

-- Registration marker: a composite snapshot is registered atomically with
-- all its outcome rows, or not at all.
CREATE TABLE IF NOT EXISTS registered_snapshots (
    composite_snapshot_id INTEGER PRIMARY KEY,
    composite_date        TEXT NOT NULL,
    entry_date            TEXT,     -- ledger window anchor (MIN price_date > composite_date); registration defers while none exists
    registered_at         TEXT NOT NULL,
    ticker_rows           INTEGER NOT NULL,
    signal_rows           INTEGER NOT NULL,
    skipped               INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    symbol                TEXT NOT NULL,
    score_sum             INTEGER NOT NULL,
    total                 INTEGER NOT NULL,
    bullish               INTEGER NOT NULL,
    bearish               INTEGER NOT NULL,
    in_portfolio          INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, symbol, horizon)
);

-- benchmark: the symbol this row's bench_* legs are graded against.
-- Direct rows get the global benchmark (SPY); crosswalked rows get their
-- matched class benchmark; NULL = explicitly unbenchmarked (class proxies
-- and unknown crosswalk tickers) -- graded on raw return only.
CREATE TABLE IF NOT EXISTS signal_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    entity                TEXT NOT NULL,
    score                 INTEGER NOT NULL,
    via_crosswalk         INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    benchmark             TEXT,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon)
);

CREATE TABLE IF NOT EXISTS regime_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    regime                TEXT,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    bench_entry_close     REAL NOT NULL,
    exit_date             TEXT,
    bench_exit_close      REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, horizon)
);
"""
```

**(b)** Add a `_VIEWS` f-string holding all five views, each preceded by `DROP VIEW IF EXISTS` so future view edits deploy on the next nightly run. In this task the view SELECTs are **verbatim what they are today** (Tasks 5–6 change them) — only the `CREATE VIEW IF NOT EXISTS` prefix changes:

```python
_VIEWS = f"""
DROP VIEW IF EXISTS v_bucket_performance;
CREATE VIEW v_bucket_performance AS
WITH m AS (
    SELECT CASE WHEN total < 2 THEN 'thin'
                WHEN score_sum >= 4 THEN 'strong_bull'
                WHEN score_sum >= 2 THEN 'bull'
                WHEN score_sum <= -4 THEN 'strong_bear'
                WHEN score_sum <= -2 THEN 'bear'
                ELSE 'neutral' END AS bucket,
           horizon, fwd_return, score_sum,
           fwd_return - bench_fwd_return AS excess
    FROM ticker_outcomes WHERE matured_at IS NOT NULL
)
SELECT bucket, horizon, COUNT(*) AS n_matured,
       AVG(fwd_return) AS avg_fwd_return,
       AVG(excess) AS avg_excess,
       AVG(CASE WHEN excess IS NULL THEN NULL
                WHEN score_sum > 0 THEN (excess > 0)
                WHEN score_sum < 0 THEN (excess < 0) END) AS hit_rate
FROM m GROUP BY bucket, horizon;

DROP VIEW IF EXISTS v_signal_efficacy;
CREATE VIEW v_signal_efficacy AS
SELECT signal_id, via_crosswalk, horizon, COUNT(*) AS n_matured,
       AVG((fwd_return - bench_fwd_return)
           * (CASE WHEN score > 0 THEN 1 ELSE -1 END))
           AS avg_directional_excess,
       AVG(CASE WHEN bench_fwd_return IS NULL THEN NULL
                WHEN score > 0 THEN (fwd_return > bench_fwd_return)
                ELSE (fwd_return < bench_fwd_return) END) AS hit_rate
FROM signal_outcomes
WHERE matured_at IS NOT NULL
GROUP BY signal_id, via_crosswalk, horizon;

DROP VIEW IF EXISTS v_regime_performance;
CREATE VIEW v_regime_performance AS
SELECT regime, horizon, COUNT(*) AS n_matured,
       AVG(bench_fwd_return) AS avg_bench_return,
       MIN(bench_fwd_return) AS min_bench_return,
       MAX(bench_fwd_return) AS max_bench_return
FROM regime_outcomes WHERE matured_at IS NOT NULL
GROUP BY regime, horizon;

DROP VIEW IF EXISTS v_basis_breaks;
CREATE VIEW v_basis_breaks AS
SELECT a.symbol,
       b.price_date AS prev_date, b.close AS prev_close,
       a.price_date, a.close,
       a.close / b.close AS ratio
FROM prices a
JOIN prices b ON b.symbol = a.symbol
 AND b.price_date = (SELECT MAX(c.price_date) FROM prices c
                     WHERE c.symbol = a.symbol AND c.price_date < a.price_date)
WHERE a.close < b.close * {BASIS_BREAK_LO} OR a.close > b.close * {BASIS_BREAK_HI};

DROP VIEW IF EXISTS v_pending;
CREATE VIEW v_pending AS
SELECT 'ticker' AS kind, composite_date, symbol AS entity, horizon,
       entry_date FROM ticker_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'signal', composite_date, signal_id || ':' || entity, horizon,
       entry_date FROM signal_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'regime', composite_date, COALESCE(regime, '?'), horizon,
       entry_date FROM regime_outcomes WHERE matured_at IS NULL;
"""
```

Keep the existing comment blocks that sit above `v_bucket_performance` (bucketing doc), `v_signal_efficacy`, `v_basis_breaks`, and `v_pending` — move them with their views into `_VIEWS`.

**(c)** Replace `ensure_schema`:

```python
def ensure_schema(conn) -> None:
    """Tables, then the idempotent benchmark-column migration, then views.
    Views are DROP+CREATEd every run so edits deploy nightly; the ALTER
    must precede them because views reference signal_outcomes.benchmark."""
    conn.executescript(_TABLES)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    if "benchmark" not in cols:
        conn.execute("ALTER TABLE signal_outcomes ADD COLUMN benchmark TEXT")
    conn.executescript(_VIEWS)
    conn.commit()
```

Note: `executescript` implicitly commits any open transaction first — all callers already call `ensure_schema` before opening transactions, so this is safe.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_schema.py tests/test_scorer_db_views.py tests/test_scorer_db_write.py tests/test_scorer_run.py -v`
Expected: ALL PASS (views verbatim, so existing view tests unaffected)

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_scorer_db_schema.py
git commit -m "feat(scorer): signal_outcomes.benchmark column + view rebuild on ensure_schema

Tables/views split so the idempotent ALTER lands before view creation;
views are now DROP+CREATEd each run so view edits deploy nightly."
```

---

### Task 3: Registration resolves and stores the per-row benchmark

**Files:**
- Modify: `sources/combiners/scorer/db.py` (`register_snapshot`)
- Modify: `sources/combiners/scorer/run.py` (pass the map)
- Test: `tests/test_scorer_db_write.py`, `tests/test_scorer_run.py`

**Interfaces:**
- Consumes: `catalog.CROSSWALK_BENCHMARK` (Task 1), `signal_outcomes.benchmark` column (Task 2).
- Produces: `db.register_snapshot(..., now_iso, crosswalk_benchmark=None)` — new optional trailing parameter (dict or None). Signal rows are written with `benchmark` = SPY (direct), map lookup (crosswalked), or NULL; `bench_entry_close` comes from the row's own benchmark.

- [ ] **Step 1: Write the failing unit test**

Append to `tests/test_scorer_db_write.py`:

```python
XW_BENCH = {"XOM": "XLE", "XLE": None}


def test_signal_benchmark_resolution(tmp_path):
    conn = _conn(tmp_path)
    for sym, start in (
        ("XOM", 100.0),
        ("XLE", 50.0),
        ("NEWX", 20.0),
        ("AAPL", 200.0),
        ("SPY", 500.0),
    ):
        _ledger(conn, sym, DAYS, start=start)
    signal_rows = [
        # crosswalked, mapped -> matched benchmark XLE
        dict(signal_id="cftc_energy", entity="XOM", score=2, via_crosswalk=1),
        # crosswalked class proxy -> explicitly unbenchmarked
        dict(signal_id="cftc_energy", entity="XLE", score=2, via_crosswalk=1),
        # crosswalked but unknown to the map -> fail safe to unbenchmarked
        dict(signal_id="cftc_energy", entity="NEWX", score=2, via_crosswalk=1),
        # direct ticker evidence -> global benchmark
        dict(signal_id="stocks_rsi", entity="AAPL", score=1, via_crosswalk=0),
    ]
    db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [],
        signal_rows,
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
        crosswalk_benchmark=XW_BENCH,
    )
    bench = dict(conn.execute("SELECT entity, benchmark FROM signal_outcomes"))
    assert bench == {"XOM": "XLE", "XLE": None, "NEWX": None, "AAPL": "SPY"}
    # bench_entry_close is the row's OWN benchmark's close at the entry
    # date (2026-07-02 = DAYS[5], close = start + 5)
    entry = dict(conn.execute("SELECT entity, bench_entry_close FROM signal_outcomes"))
    assert entry["XOM"] == 55.0  # XLE, not SPY
    assert entry["XLE"] is None
    assert entry["NEWX"] is None
    assert entry["AAPL"] == 505.0  # SPY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scorer_db_write.py::test_signal_benchmark_resolution -v`
Expected: FAIL with `TypeError: register_snapshot() got an unexpected keyword argument 'crosswalk_benchmark'`

- [ ] **Step 3: Implement in `db.py`**

**(a)** Add the parameter to `register_snapshot` (after `now_iso`):

```python
def register_snapshot(
    conn,
    csid,
    composite_date,
    ticker_rows,
    signal_rows,
    regime,
    horizons,
    benchmark,
    max_age_days,
    now_iso,
    crosswalk_benchmark=None,
) -> tuple:
```

Add to its docstring (after the dedupe-key paragraph):

```
    Per-row benchmarks: a direct signal row is graded against `benchmark`
    (SPY); a crosswalked row against crosswalk_benchmark[entity] — its
    matched asset-class proxy. A class proxy maps to None and an unknown
    crosswalk ticker resolves to None (never silently SPY): both grade
    unbenchmarked (raw return only). ticker/regime rows stay on `benchmark`.
```

**(b)** Replace the signal-rows loop body:

```python
        for r in signal_rows:
            entry = entry_for(conn, r["entity"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            if r["via_crosswalk"]:
                row_bench = (crosswalk_benchmark or {}).get(r["entity"])
            else:
                row_bench = benchmark
            bench = _bench_close(conn, row_bench, entry[0]) if row_bench else None
            for h in horizons:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO signal_outcomes"
                    " (composite_snapshot_id, composite_date, signal_id,"
                    "  entity, score, via_crosswalk, horizon, entry_date,"
                    "  entry_close, benchmark, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        csid,
                        composite_date,
                        r["signal_id"],
                        r["entity"],
                        r["score"],
                        r["via_crosswalk"],
                        h,
                        entry[0],
                        entry[1],
                        row_bench,
                        bench,
                    ),
                )
                registered += cur.rowcount
```

**(c)** In `run.py`, wire the map through — change the `db.register_snapshot(` call to add the final argument:

```python
                    reg, skip = db.register_snapshot(
                        conn,
                        csid,
                        cdate,
                        fetch.read_ticker_scores(conn, csid),
                        fetch.read_signal_rows(conn, csid),
                        fetch.read_regime(conn, csid),
                        catalog.HORIZONS,
                        catalog.BENCHMARK,
                        catalog.ENTRY_MAX_AGE_DAYS,
                        now_iso,
                        crosswalk_benchmark=catalog.CROSSWALK_BENCHMARK,
                    )
```

- [ ] **Step 4: Run unit test to verify it passes**

Run: `uv run pytest tests/test_scorer_db_write.py -v`
Expected: ALL PASS (existing tests pass `crosswalk_benchmark` implicitly as None; their signal rows are all `via_crosswalk=0` → benchmark "SPY", unchanged behavior)

- [ ] **Step 5: Write the failing end-to-end test**

In `tests/test_scorer_run.py`, change `_mini_composite`'s signature and signal list to accept extras:

```python
def _mini_composite(dirpath, date="2026-07-01", extra_signals=None):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, f"{date}T21:05:00+00:00", 1)
    signals = [
        dict(
            signal_id="stocks_rsi",
            grain="ticker",
            entity="AAPL",
            raw_value=25.0,
            score=1,
            obs_date=date,
            staleness_days=0.0,
        )
    ] + list(extra_signals or [])
    composite_db.write_signal_values(conn, sid, signals)
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()
```

Append the new test:

```python
def test_crosswalked_signal_gets_matched_benchmark(tmp_path):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0, "XOM": 80.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0, "XLE": 50.0})
    _mini_composite(
        tmp_path,
        extra_signals=[
            dict(
                signal_id="cftc_energy",
                grain="ticker",
                entity="XOM",
                raw_value=1.0,
                score=1,
                obs_date="2026-07-01",
                staleness_days=0.0,
                via_crosswalk=1,
            )
        ],
    )
    out = str(tmp_path / "scorer.db")
    run_mod.run(out, str(tmp_path), now_iso=NOW)
    conn = sqlite3.connect(out)
    rows = dict(
        conn.execute("SELECT entity, benchmark FROM signal_outcomes WHERE entity IN ('XOM','AAPL')")
    )
    assert rows == {"XOM": "XLE", "AAPL": "SPY"}
```

- [ ] **Step 6: Run it — should already pass (run.py wired in step 3c); verify it exercises the wiring**

Run: `uv run pytest tests/test_scorer_run.py -v`
Expected: ALL PASS. Sanity check it fails without the wiring: temporarily delete the `crosswalk_benchmark=catalog.CROSSWALK_BENCHMARK,` line from `run.py`, re-run — `test_crosswalked_signal_gets_matched_benchmark` must FAIL (`{"XOM": None, ...}` — crosswalked row falls back to unbenchmarked, proving the map flows through run.py). Restore the line, re-run, PASS.

- [ ] **Step 7: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py sources/combiners/scorer/run.py tests/test_scorer_db_write.py tests/test_scorer_run.py
git commit -m "feat(scorer): registration stores per-row matched benchmark

Crosswalked rows resolve via CROSSWALK_BENCHMARK (class proxy/unknown
-> NULL = unbenchmarked); direct rows keep SPY. bench_entry_close now
comes from the row's own benchmark."
```

---

### Task 4: Maturation grades each signal row against its own benchmark

**Files:**
- Modify: `sources/combiners/scorer/db.py` (`_MATURE_SYMBOL`, `mature`)
- Test: `tests/test_scorer_db_write.py`

**Interfaces:**
- Consumes: `signal_outcomes.benchmark` (Tasks 2–3).
- Produces: `mature(conn, now_iso, benchmark="SPY")` — signature unchanged; `signal_outcomes` rows now mature against their stored `benchmark` (NULL benchmark → `bench_fwd_return` NULL, benchmark-leg break scan self-disables); `ticker_outcomes`/`regime_outcomes` still use the `benchmark` argument.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scorer_db_write.py`:

```python
def _register_signal(conn, entity, xw_bench, horizons=(2,)):
    """Register one bullish crosswalked signal opinion on DAYS[4] (2026-07-01)."""
    return db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [],
        [dict(signal_id="cftc_energy", entity=entity, score=2, via_crosswalk=1)],
        "risk_on",
        horizons,
        "SPY",
        7,
        NOW,
        crosswalk_benchmark=xw_bench,
    )


def test_crosswalk_row_matures_vs_own_benchmark(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XOM", DAYS, start=100.0, step=1.0)  # entry 105 -> exit 107
    _ledger(conn, "XLE", DAYS, start=50.0, step=5.0)  # entry 75 -> exit 85
    _ledger(conn, "SPY", DAYS, start=500.0, step=0.0)  # flat: SPY excess would be ~0
    _register_signal(conn, "XOM", {"XOM": "XLE"})
    db.mature(conn, NOW)
    row = conn.execute(
        "SELECT fwd_return, bench_fwd_return, matured_at FROM signal_outcomes"
    ).fetchone()
    assert row[2] is not None
    assert abs(row[0] - (107.0 / 105.0 - 1)) < 1e-9
    # graded against XLE's move, NOT SPY's flat 0.0
    assert abs(row[1] - (85.0 / 75.0 - 1)) < 1e-9


def test_unbenchmarked_row_matures_with_null_bench(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XLE", DAYS, start=50.0)
    _ledger(conn, "SPY", DAYS, start=500.0)
    _register_signal(conn, "XLE", {"XLE": None})
    db.mature(conn, NOW)
    row = conn.execute(
        "SELECT fwd_return, bench_fwd_return, matured_at FROM signal_outcomes"
    ).fetchone()
    assert row[2] is not None and row[0] is not None
    assert row[1] is None


def test_matched_benchmark_split_blocks_row(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XOM", DAYS, start=100.0)
    # XLE 2:1 split between DAYS[2] and DAYS[3] -- inside the (2,) window
    closes = [100.0, 101.0, 99.5, 50.2, 50.0, 50.5, 49.8, 50.1]
    db.insert_prices(conn, list(zip(["XLE"] * 8, DAYS, closes, strict=True)))
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(
        conn,
        1,
        DAYS[0],
        [],
        [
            dict(signal_id="cftc_energy", entity="XOM", score=2, via_crosswalk=1),
            dict(signal_id="stocks_rsi", entity="XOM", score=1, via_crosswalk=0),
        ],
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
        crosswalk_benchmark={"XOM": "XLE"},
    )
    db.mature(conn, NOW)
    rows = dict(conn.execute("SELECT signal_id, matured_at IS NOT NULL FROM signal_outcomes"))
    # the XLE-benchmarked row is held pending by the benchmark-leg break;
    # the SPY-benchmarked row for the same entity matures fine
    assert rows == {"cftc_energy": 0, "stocks_rsi": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_db_write.py -k "own_benchmark or unbenchmarked or benchmark_split" -v`
Expected: `test_crosswalk_row_matures_vs_own_benchmark` FAILS — pre-fix maturation mixes legs: SPY's exit close over XLE's stored entry close, bench_fwd_return = 500.0/75.0 − 1 ≈ 5.667, not XLE's 0.1333; `test_matched_benchmark_split_blocks_row` FAILS (both rows mature — the scan only checks SPY). `test_unbenchmarked_row_matures_with_null_bench` may already pass (bench_entry_close IS NULL guard); keep it as a regression pin.

- [ ] **Step 3: Implement**

In `sources/combiners/scorer/db.py`:

**(a)** In `_MATURE_SYMBOL`, replace the two hardcoded benchmark references with a `{bench}` slot. The `bench_fwd_return` assignment becomes:

```python
  bench_fwd_return = CASE WHEN bench_entry_close IS NOT NULL THEN
      (SELECT close FROM prices
       WHERE symbol = {bench} AND price_date = x.xdate)
      / bench_entry_close - 1 END,
```

and the benchmark-leg break scan line becomes:

```python
    + _BREAK_SCAN.format(who="{bench}", t="{table}")
```

(The graded-leg scan stays `_BREAK_SCAN.format(who="{table}.{sym}", t="{table}")`.)

**(b)** In `mature`, supply the slot per table:

```python
    for table, sym, bench in (
        ("ticker_outcomes", "symbol", ":bench"),
        ("signal_outcomes", "entity", "signal_outcomes.benchmark"),
    ):
        cur = conn.execute(_MATURE_SYMBOL.format(table=table, sym=sym, bench=bench), params)
        n += cur.rowcount
```

**(c)** Extend the maturation NOTE comment block (above `_BREAK_SCAN`) with:

```
# signal_outcomes rows grade against their own stored benchmark column
# ({bench} slot): the benchmark-leg break scan self-disables when
# benchmark IS NULL (a.symbol = NULL matches nothing), so unbenchmarked
# rows mature with bench_fwd_return NULL, while a break in a matched
# benchmark (e.g. XLE splits) holds its dependent rows pending — the
# same refuse-to-grade principle as SPY today.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_write.py tests/test_scorer_db_views.py -v`
Expected: ALL PASS (existing signal rows registered with benchmark="SPY" behave identically; `test_benchmark_break_blocks_symbol_rows` still passes — ticker path unchanged)

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_scorer_db_write.py
git commit -m "feat(scorer): mature signal rows against their stored benchmark

NULL benchmark self-disables the benchmark-leg break scan (row matures
unbenchmarked); a basis break in a matched benchmark holds its rows
pending, same refuse-to-grade principle as SPY."
```

---

### Task 5: Guardrail columns on `v_signal_efficacy`

**Files:**
- Modify: `sources/combiners/scorer/db.py` (constants, `_wilson`, `_VIEWS`)
- Test: `tests/test_scorer_db_views.py`

**Interfaces:**
- Produces: `db.WILSON_Z = 1.96`, `db.RELIABLE_MIN_N = 30`; `v_signal_efficacy` columns, in order: `signal_id, via_crosswalk, horizon, n_matured, avg_directional_excess, hit_rate` (existing order preserved) then appended `avg_directional_return, n_bench, hit_ci_lo, hit_ci_hi, reliable, benchmarks`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scorer_db_views.py`:

```python
def _signal_row(conn, sig, entity, score, fwd, bench_fwd, benchmark="SPY", xw=0):
    """Insert one matured signal outcome directly (views read the table)."""
    conn.execute(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, ?, 5, '2026-07-02', 100.0, ?, ?,"
        " '2026-07-10', 100.0, ?, ?, ?)",
        (
            sig,
            entity,
            score,
            xw,
            benchmark,
            None if benchmark is None else 500.0,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def _efficacy(conn, sig):
    return conn.execute(
        "SELECT n_matured, n_bench, hit_rate, hit_ci_lo, hit_ci_hi,"
        " reliable, avg_directional_return, benchmarks"
        " FROM v_signal_efficacy WHERE signal_id = ?",
        (sig,),
    ).fetchone()


def test_wilson_interval_hand_computed(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 3 hits out of 4 (bullish rows, hit = fwd > bench_fwd)
    for i, fwd in enumerate((0.02, 0.02, 0.02, 0.00)):
        _signal_row(conn, "sig_a", f"T{i}", 1, fwd, 0.01)
    n, nb, hr, lo, hi, rel, _, _ = _efficacy(conn, "sig_a")
    assert (n, nb) == (4, 4)
    assert abs(hr - 0.75) < 1e-9
    # Wilson 95% for 3/4, hand-computed: z=1.96, z^2=3.8416
    # center=0.75+3.8416/8, margin=1.96*sqrt(0.75*0.25/4+3.8416/64),
    # denom=1+3.8416/4 -> (0.300636, 0.954414)
    assert abs(lo - 0.300636) < 1e-4
    assert abs(hi - 0.954414) < 1e-4
    assert rel == 0


def test_wilson_all_hits_not_degenerate(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(5):
        _signal_row(conn, "sig_a", f"T{i}", 1, 0.02, 0.01)  # 5/5 hits
    _, nb, hr, lo, hi, _, _, _ = _efficacy(conn, "sig_a")
    assert (nb, hr) == (5, 1.0)
    # Wald would say 100% +/- 0; Wilson: lo = 1/(1+3.8416/5) ~ 0.565509
    assert abs(lo - 0.565509) < 1e-4
    # float rounding can land a hair above 1.0 (1.0000000000000002)
    assert abs(hi - 1.0) < 1e-9


def test_reliable_flag_boundary(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(db.RELIABLE_MIN_N):
        _signal_row(conn, "sig_30", f"T{i}", 1, 0.02, 0.01)
    for i in range(db.RELIABLE_MIN_N - 1):
        _signal_row(conn, "sig_29", f"T{i}", 1, 0.02, 0.01)
    assert _efficacy(conn, "sig_30")[5] == 1
    assert _efficacy(conn, "sig_29")[5] == 0


def test_unbenchmarked_rows_labeled_not_hidden(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 2 unbenchmarked (class-proxy) rows + 1 benchmarked, all bullish wins
    _signal_row(conn, "cftc_energy", "XLE", 2, 0.05, None, benchmark=None, xw=1)
    _signal_row(conn, "cftc_energy", "DBA", 2, 0.03, None, benchmark=None, xw=1)
    _signal_row(conn, "cftc_energy", "XOM", 2, 0.04, 0.01, benchmark="XLE", xw=1)
    n, nb, hr, lo, hi, rel, avg_ret, benchmarks = _efficacy(conn, "cftc_energy")
    assert (n, nb) == (3, 1)  # n_matured - n_bench = 2 unbenchmarked
    assert hr == 1.0  # over the 1 benchmarked row only
    assert benchmarks == "XLE"  # states what it was measured against
    # raw directional return covers ALL rows, benchmarked or not
    assert abs(avg_ret - (0.05 + 0.03 + 0.04) / 3) < 1e-9


def test_zero_bench_rows_null_ci(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _signal_row(conn, "cftc_ags", "DBA", 2, 0.03, None, benchmark=None, xw=1)
    n, nb, hr, lo, hi, rel, _, benchmarks = _efficacy(conn, "cftc_ags")
    assert (n, nb) == (1, 0)
    assert hr is None and lo is None and hi is None
    assert rel == 0
    assert benchmarks is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_db_views.py -v`
Expected: new tests FAIL with `sqlite3.OperationalError: no such column: n_bench`; existing tests PASS.

- [ ] **Step 3: Implement in `db.py`**

**(a)** Add constants below `BASIS_BREAK_HI` and a fragment builder above `_VIEWS`:

```python
# Guardrail constants for the efficacy views. Wilson (not Wald): Wald
# collapses to zero width on small all-hit samples (5/5 -> "100% +/- 0"),
# which is exactly the n=12-looks-brilliant failure these views must not
# have. Crude by design — with ~144 simultaneous rows (24 signals x 3
# horizons x crosswalk split), ~7 look significant at 95% by chance alone;
# the human reads the CI with that in mind. sqrt() needs SQLite math
# functions (present in CPython 3.12's bundled SQLite 3.45+).
WILSON_Z = 1.96  # 95% score interval on hit_rate
RELIABLE_MIN_N = 30  # benchmarked-sample floor for the reliable flag


def _wilson(sign: str) -> str:
    """Wilson score bound (+1 upper / -1 lower via sign) as a SQL aggregate
    fragment over a 0/1 `hit` column; NULL hits are excluded by COUNT/AVG."""
    z, n, p = str(WILSON_Z), "COUNT(hit)", "AVG(hit)"
    return (
        f"CASE WHEN {n} > 0 THEN"
        f" ({p} + {z}*{z}/(2.0*{n})"
        f" {sign} {z} * sqrt({p}*(1-{p})/{n} + {z}*{z}/(4.0*{n}*{n})))"
        f" / (1 + {z}*{z}/{n}) END"
    )
```

**(b)** Replace the `v_signal_efficacy` block inside `_VIEWS` (keep the DROP line):

```sql
-- Per-signal grade, direction-adjusted: excess * sign(score). Crosswalked
-- evidence is split out so mapped scores are graded separately. Guardrails:
-- n_bench is the binomial n (rows with a gradable benchmark; hit_rate,
-- avg_directional_excess and the CI only see those); n_matured - n_bench
-- is the unbenchmarked count, which avg_directional_return (raw, no
-- benchmark) still covers. reliable gates on n_bench, not n_matured.
DROP VIEW IF EXISTS v_signal_efficacy;
CREATE VIEW v_signal_efficacy AS
WITH m AS (
    SELECT signal_id, via_crosswalk, horizon, benchmark,
           (fwd_return - bench_fwd_return)
               * (CASE WHEN score > 0 THEN 1 ELSE -1 END) AS dir_excess,
           fwd_return * (CASE WHEN score > 0 THEN 1 ELSE -1 END) AS dir_return,
           CASE WHEN bench_fwd_return IS NULL THEN NULL
                WHEN score > 0 THEN (fwd_return > bench_fwd_return)
                ELSE (fwd_return < bench_fwd_return) END AS hit
    FROM signal_outcomes WHERE matured_at IS NOT NULL
)
SELECT signal_id, via_crosswalk, horizon,
       COUNT(*) AS n_matured,
       AVG(dir_excess) AS avg_directional_excess,
       AVG(hit) AS hit_rate,
       AVG(dir_return) AS avg_directional_return,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable,
       GROUP_CONCAT(DISTINCT benchmark) AS benchmarks
FROM m
GROUP BY signal_id, via_crosswalk, horizon;
```

(`_VIEWS` is already an f-string; `{_wilson("-")}` and `{RELIABLE_MIN_N}` interpolate at import. `_wilson` must be defined above `_VIEWS` in the module.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_views.py -v`
Expected: ALL PASS, including the pre-existing `test_signal_efficacy_direction_adjusted` (its columns kept their names and order).

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_scorer_db_views.py
git commit -m "feat(scorer): Wilson CI + reliable flag on v_signal_efficacy

n_bench is the binomial n; unbenchmarked rows are counted and covered
by a raw avg_directional_return; benchmarks column states the yardstick."
```

---

### Task 6: Guardrail columns on `v_bucket_performance`

**Files:**
- Modify: `sources/combiners/scorer/db.py` (`_VIEWS`)
- Test: `tests/test_scorer_db_views.py`

**Interfaces:**
- Consumes: `_wilson`, `RELIABLE_MIN_N` (Task 5).
- Produces: `v_bucket_performance` columns, in order: `bucket, horizon, n_matured, avg_fwd_return, avg_excess, hit_rate` (existing order preserved) then appended `n_bench, hit_ci_lo, hit_ci_hi, reliable`. Buckets stay SPY-benchmarked (ticker rows carry no crosswalk provenance).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scorer_db_views.py`:

```python
def _ticker_row(conn, symbol, score_sum, fwd, bench_fwd, total=3):
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, in_portfolio, horizon,"
        " entry_date, entry_close, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, 0, 0, 0, 5, '2026-07-02', 100.0,"
        " ?, '2026-07-10', 100.0, ?, ?, ?)",
        (
            symbol,
            score_sum,
            total,
            None if bench_fwd is None else 500.0,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def test_bucket_guardrail_columns(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # strong_bull bucket: one hit, one miss, one benchmark-less row
    _ticker_row(conn, "A", 4, 0.02, 0.01)  # hit
    _ticker_row(conn, "B", 4, 0.00, 0.01)  # miss
    _ticker_row(conn, "C", 4, 0.02, None)  # unbenchmarked
    row = conn.execute(
        "SELECT n_matured, n_bench, hit_rate, hit_ci_lo, hit_ci_hi, reliable"
        " FROM v_bucket_performance WHERE bucket = 'strong_bull'"
    ).fetchone()
    assert (row[0], row[1]) == (3, 2)
    assert abs(row[2] - 0.5) < 1e-9
    # Wilson 95% for 1/2: hand-computed (0.094529, 0.905471)
    assert abs(row[3] - 0.094529) < 1e-4
    assert abs(row[4] - 0.905471) < 1e-4
    assert row[5] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scorer_db_views.py::test_bucket_guardrail_columns -v`
Expected: FAIL with `sqlite3.OperationalError: no such column: n_bench`

- [ ] **Step 3: Implement**

Replace the `v_bucket_performance` block inside `_VIEWS` (keep the bucketing comment and DROP line):

```sql
-- Bucketing lives in views (ELT): stored rows keep raw score_sum/total.
-- Buckets: strong_bull >= +4, bull +2..+3, neutral -1..+1, bear -3..-2,
-- strong_bear <= -4; rows with total < 2 bucket as 'thin' regardless.
-- hit = excess in the score's direction (bull: excess > 0; bear: < 0);
-- score_sum = 0 rows have no direction and contribute NULL hits. Buckets
-- are SPY-benchmarked throughout (ticker rows carry no crosswalk
-- provenance), so n_bench counts rows with a computable hit (a gradable
-- SPY leg AND a direction).
DROP VIEW IF EXISTS v_bucket_performance;
CREATE VIEW v_bucket_performance AS
WITH m AS (
    SELECT CASE WHEN total < 2 THEN 'thin'
                WHEN score_sum >= 4 THEN 'strong_bull'
                WHEN score_sum >= 2 THEN 'bull'
                WHEN score_sum <= -4 THEN 'strong_bear'
                WHEN score_sum <= -2 THEN 'bear'
                ELSE 'neutral' END AS bucket,
           horizon, fwd_return,
           fwd_return - bench_fwd_return AS excess,
           CASE WHEN bench_fwd_return IS NULL THEN NULL
                WHEN score_sum > 0 THEN (fwd_return > bench_fwd_return)
                WHEN score_sum < 0 THEN (fwd_return < bench_fwd_return) END AS hit
    FROM ticker_outcomes WHERE matured_at IS NOT NULL
)
SELECT bucket, horizon, COUNT(*) AS n_matured,
       AVG(fwd_return) AS avg_fwd_return,
       AVG(excess) AS avg_excess,
       AVG(hit) AS hit_rate,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable
FROM m GROUP BY bucket, horizon;
```

(The `hit` CASE is the old expression rewritten against `bench_fwd_return` directly — `excess IS NULL` iff `bench_fwd_return IS NULL`, and `excess > 0` iff `fwd_return > bench_fwd_return`, so behavior is identical.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_views.py -v`
Expected: ALL PASS, including the pre-existing `test_bucket_performance`.

- [ ] **Step 5: Gates + commit**

```bash
uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest
git add sources/combiners/scorer/db.py tests/test_scorer_db_views.py
git commit -m "feat(scorer): Wilson CI + reliable flag on v_bucket_performance"
```

---

### Task 7: Prune roadmap item 4

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Edit the roadmap**

**(a)** Replace the whole `### 4. Statistical guardrails on efficacy views` section (heading through the end of the section — the `**Size.**` paragraph wraps onto a second line ending `contaminated rows).`) with a parenthetical under the `## Next — evaluation hardening` heading, matching the shipped-item style of the "Now" tier:

```markdown
## Next — evaluation hardening

*(Item 4, statistical guardrails: `v_signal_efficacy` / `v_bucket_performance`
expose `n_bench`, a Wilson 95% CI on hit_rate, and a `reliable` flag
(n_bench >= 30); crosswalked outcomes grade against matched class benchmarks
(CROSSWALK_BENCHMARK), class proxies explicitly unbenchmarked. Shipped
2026-07-06. Residual: ticker-grain buckets stay SPY-benchmarked — see
item 8.)*
```

**(b)** In item 6, change the dependency line:

```markdown
**Size.** L. **Depends on.** #4 (shipped 2026-07-06 — advice should cite
`reliable` efficacy rows), plus a volatility input (ATR already in
`stocks.db` metrics).
```

**(c)** In item 8, update the weighting bullet:

```markdown
- **Weighting the composite** — still a human decision; revisit only when
  the efficacy guardrails (shipped 2026-07-06) say the evidence is
  reliable (`reliable` = 1 and the Wilson CI clears 0.5).
```

**(d)** In item 8, append a bullet capturing the new residual:

```markdown
- **Matched benchmarks at ticker grain** (residual from shipped item 4) —
  `ticker_outcomes` buckets grade vs SPY even for tickers whose score is
  dominated by crosswalked commodity votes; per-ticker benchmark needs
  crosswalk provenance on ticker_scores first.
```

- [ ] **Step 2: Gates + commit**

```bash
uv run pytest
git add docs/ROADMAP.md
git commit -m "docs(roadmap): item 4 shipped — statistical guardrails on efficacy views"
```

---

## Verification (after all tasks)

- [ ] `uv run pytest` — full suite green.
- [ ] `uv run ruff check && uv run ruff format --check && uv run mypy` — clean.
- [ ] Live smoke test against real data — note this intentionally applies the
  migration to the production DB (the same thing the next nightly run would do):
  `uv run python -c "from sources.combiners.scorer import db; c = db.connect('data/scorer.db'); db.ensure_schema(c); print(c.execute('SELECT * FROM v_signal_efficacy').fetchall())"`
  Expected: `[]` (outcome tables are empty until snapshots mature) and, critically, **no OperationalError** — proves the migrated schema + new views parse against the production DB. Then `sqlite3 data/scorer.db "PRAGMA table_info(signal_outcomes)"` shows the `benchmark` column.
