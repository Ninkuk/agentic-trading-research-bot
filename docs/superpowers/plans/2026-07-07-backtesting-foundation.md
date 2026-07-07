# Backtesting Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship roadmap item 7 — FRED vintages backfilled + scheduled, an `SP500` benchmark series, and a new `backtest` combiner whose SQL views replay composite's two FRED regime signals point-in-time over ~10 years (the end-to-end proof). The bar-store decision is already recorded as an ADR in the spec (no build).

**Spec:** `docs/superpowers/specs/2026-07-07-backtesting-foundation-design.md` — read it first.

**Architecture:** A fourth combiner (`sources/combiners/backtest/`) in the standard four-file shape. `fetch.py` has **no network**: it ATTACHes `data/fred.db` read-only and copies vintage/benchmark rows into `backtest.db`. `db.py` derives everything in views: `v_pit_signal` (value-as-known-on-D via ALFRED vintages) → `v_replay_flags` (composite's exact CASE expressions, imported as constants) → `v_replay_returns` (forward SP500 returns, entry strictly after D) → `v_replay_efficacy` (Wilson-CI hit rates mirroring scorer). Composite gets a tiny behavior-preserving refactor hoisting its two FRED CASE expressions into importable constants.

**Tech Stack:** Python 3.12 stdlib only (`sqlite3`, `argparse`); `uv` + `pytest` for dev.

## Global Constraints

- **Zero runtime third-party dependencies** — stdlib only, no `uv add`.
- **No network in tests** — all tests run offline against temp SQLite DBs.
- **Secret hygiene:** on per-source failure print only `type(e).__name__`, never `str(e)`.
- **No wall-clock in the hot path:** time enters as injected `now_iso` (UTC `isoformat()`).
- **Fixed-width timestamps:** every `captured_at` writer stores UTC `isoformat()` (incl. `+00:00`).
- **All four gates green before each commit:** `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest` (the pre-commit hook runs these).
- **Never commit `data/*.db`.** Always pass `--db data/<name>.db` when running for real.
- **Do not add yourself as a co-author to commits.** Use `--no-gpg-sign` if signing hangs.

---

### Task 1: FRED `SP500` benchmark series

**Files:**
- Modify: `sources/screeners/fred_screener/catalog.py`
- Test: `tests/test_fred_catalog.py`

**Interfaces:**
- Produces: `Series("SP500", "benchmark")` in `CATALOG` — the nightly fred job will then fetch ~10y of daily S&P 500 closes into `fred.db observations` (and vintages once Task 9 lands). Task 7's harvest reads it as `catalog.BENCHMARK_SERIES = "SP500"`.

- [ ] **Step 1: Write the failing test**

In `tests/test_fred_catalog.py`, change the `VALID_THEMES` line and append a test:

```python
VALID_THEMES = {"growth", "inflation", "rates", "labor", "credit", "housing", "sentiment", "benchmark"}
```

```python
def test_catalog_includes_sp500_benchmark():
    themes = {s.series_id: s.theme for s in CATALOG}
    assert themes.get("SP500") == "benchmark"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fred_catalog.py -v`
Expected: `test_catalog_includes_sp500_benchmark` FAILS (`assert None == 'benchmark'`); all others PASS.

- [ ] **Step 3: Implement**

In `sources/screeners/fred_screener/catalog.py`:

Update the dataclass comment:

```python
    theme: str  # growth|inflation|rates|labor|credit|housing|sentiment|benchmark
```

Append to `CATALOG` after the sentiment group (before the closing `]`):

```python
    # benchmark (grading spine for the backtest combiner; FRED licensing
    # caps SP500 history at ~10 years)
    Series("SP500", "benchmark"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fred_catalog.py tests/test_fred_run.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sources/screeners/fred_screener/catalog.py tests/test_fred_catalog.py
git commit --no-gpg-sign -m "feat(fred): add SP500 benchmark series for backtest grading"
```

---

### Task 2: Hoist composite's FRED score CASEs into constants

**Files:**
- Modify: `sources/combiners/composite/catalog.py` (lines ~18–49: the `fred_curve` and `fred_hy_spread` entries)
- Test: `tests/test_composite_catalog.py`

**Interfaces:**
- Produces: `FRED_CURVE_SCORE: str` and `FRED_HY_SPREAD_SCORE: str` module constants in `sources.combiners.composite.catalog`, each a SQL `CASE ... END` expression over a column named `value`. Task 3 imports them. The rendered `SIGNALS` SQL must stay semantically identical (existing composite tests pass unchanged).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_composite_catalog.py`:

```python
def test_fred_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        FRED_CURVE_SCORE,
        FRED_HY_SPREAD_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert FRED_CURVE_SCORE in by_id["fred_curve"]["sql"]
    assert FRED_HY_SPREAD_SCORE in by_id["fred_hy_spread"]["sql"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_composite_catalog.py -v`
Expected: new test FAILS with `ImportError` (`FRED_CURVE_SCORE` not defined); all others PASS.

- [ ] **Step 3: Implement**

In `sources/combiners/composite/catalog.py`, immediately before `SIGNALS: list[dict[str, Any]] = [`, add:

```python
# Flag thresholds for the two FRED regime signals, hoisted so the backtest
# combiner replays the IDENTICAL expressions (both operate on a column
# named `value`). Interpolated back into SIGNALS below — rendered SQL is
# unchanged.
FRED_CURVE_SCORE = "CASE WHEN value < 0 THEN -1 ELSE 0 END"
FRED_HY_SPREAD_SCORE = (
    "CASE WHEN value >= 5.0 THEN -2"
    " WHEN value >= 4.0 THEN -1"
    " WHEN value < 3.5 THEN 1 ELSE 0 END"
)
```

Replace the two entries' `"sql"` values with f-strings (note the `f` prefix; everything else — including indentation — stays as-is):

```python
    {
        "signal_id": "fred_curve",
        "db": "fred.db",
        "grain": "market",
        "staleness_budget_days": 7,
        "sql": f"""
            SELECT '*', value,
                   {FRED_CURVE_SCORE},
                   date
            FROM src.observations
            WHERE series_id = 'T10Y2Y' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "fred_hy_spread",
        "db": "fred.db",
        "grain": "market",
        "staleness_budget_days": 7,
        "sql": f"""
            SELECT '*', value,
                   {FRED_HY_SPREAD_SCORE},
                   date
            FROM src.observations
            WHERE series_id = 'BAMLH0A0HYM2' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
```

- [ ] **Step 4: Run the full composite suite to prove no behavior change**

Run: `uv run pytest -k composite -v`
Expected: all PASS (this is the parity proof — the hoist must not change any rendered SQL semantics).

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/composite/catalog.py tests/test_composite_catalog.py
git commit --no-gpg-sign -m "refactor(composite): hoist FRED score CASEs into importable constants"
```

---

### Task 3: `backtest` catalog

**Files:**
- Create: `sources/combiners/backtest/__init__.py` (empty)
- Create: `sources/combiners/backtest/catalog.py`
- Test: `tests/test_backtest_catalog.py`

**Interfaces:**
- Consumes: `FRED_CURVE_SCORE`/`FRED_HY_SPREAD_SCORE` (Task 2), `sources.combiners.scorer.catalog.HORIZONS` (exists: `(5, 10, 21)`).
- Produces: `REPLAY_SIGNALS: list[dict]` with keys `signal_id`, `series_id`, `score_case`; `BENCHMARK_SERIES = "SP500"`; `FRED_DB = "fred.db"`; re-exported `HORIZONS`. Tasks 4–8 import all of these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_backtest_catalog.py`:

```python
from sources.combiners.backtest import catalog
from sources.combiners.composite.catalog import (
    FRED_CURVE_SCORE,
    FRED_HY_SPREAD_SCORE,
    SIGNALS,
)
from sources.combiners.scorer.catalog import HORIZONS


def test_replay_signals_reference_composite_case_constants():
    by_id = {s["signal_id"]: s for s in catalog.REPLAY_SIGNALS}
    assert by_id["fred_curve"]["score_case"] is FRED_CURVE_SCORE
    assert by_id["fred_hy_spread"]["score_case"] is FRED_HY_SPREAD_SCORE


def test_replay_signal_ids_exist_in_composite():
    composite_ids = {s["signal_id"] for s in SIGNALS}
    assert {s["signal_id"] for s in catalog.REPLAY_SIGNALS} <= composite_ids


def test_replay_series_ids_match_composite_sql():
    by_id = {s["signal_id"]: s for s in SIGNALS}
    for s in catalog.REPLAY_SIGNALS:
        assert f"series_id = '{s['series_id']}'" in by_id[s["signal_id"]]["sql"]


def test_horizons_come_from_scorer():
    assert catalog.HORIZONS is HORIZONS


def test_benchmark_constants():
    assert catalog.BENCHMARK_SERIES == "SP500"
    assert catalog.FRED_DB == "fred.db"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_backtest_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.combiners.backtest'`.

- [ ] **Step 3: Implement**

Create empty `sources/combiners/backtest/__init__.py`, then `sources/combiners/backtest/catalog.py`:

```python
"""Replay roster for the point-in-time backtest: which composite signals
are replayed, with the score CASE imported from composite (flags cannot
drift) and horizons imported from the scorer (grading windows match)."""

from typing import Any

from sources.combiners.composite.catalog import FRED_CURVE_SCORE, FRED_HY_SPREAD_SCORE
from sources.combiners.scorer.catalog import HORIZONS

FRED_DB = "fred.db"
BENCHMARK_SERIES = "SP500"  # grading spine; unrevised index closes

REPLAY_SIGNALS: list[dict[str, Any]] = [
    {"signal_id": "fred_curve", "series_id": "T10Y2Y", "score_case": FRED_CURVE_SCORE},
    {
        "signal_id": "fred_hy_spread",
        "series_id": "BAMLH0A0HYM2",
        "score_case": FRED_HY_SPREAD_SCORE,
    },
]

__all__ = ["BENCHMARK_SERIES", "FRED_DB", "HORIZONS", "REPLAY_SIGNALS"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_backtest_catalog.py -v`
Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/__init__.py sources/combiners/backtest/catalog.py tests/test_backtest_catalog.py
git commit --no-gpg-sign -m "feat(backtest): replay catalog — composite CASEs, scorer horizons"
```

---

### Task 4: `backtest` db schema + writers + prune

**Files:**
- Create: `sources/combiners/backtest/db.py` (schema/writers only; views arrive in Tasks 5–6)
- Test: `tests/test_backtest_db_schema.py`, `tests/test_backtest_db_write.py`

**Interfaces:**
- Consumes: `catalog.REPLAY_SIGNALS`, `catalog.HORIZONS` (Task 3); `sources.combiners.scorer.db._wilson(sign: str) -> str` and `RELIABLE_MIN_N` (exist).
- Produces (used by Tasks 5–8):
  - `connect(path: str) -> sqlite3.Connection` (WAL, `uri=True`)
  - `ensure_schema(conn) -> None`
  - `write_snapshot(conn, now_iso: str) -> int`
  - `finish_snapshot(conn, sid: int, vintage_rows: int, benchmark_rows: int, sources_failed: int) -> None`
  - `insert_vintages(conn, rows) -> int` — rows of `(series_id, date, realtime_start, value)`
  - `insert_benchmark(conn, rows) -> int` — rows of `(date, close)`
  - `prune(conn, keep_days: int, now_iso: str) -> int` — snapshot headers ONLY

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest_db_schema.py`:

```python
import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_ensure_schema_is_idempotent(conn):
    db.ensure_schema(conn)  # second call must not raise


def test_expected_tables_exist(conn):
    names = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"snapshots", "signal_vintages", "benchmark_closes"} <= names
```

Create `tests/test_backtest_db_write.py`:

```python
import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_insert_vintages_upserts_last_wins(conn):
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.5)])
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.6)])
    rows = conn.execute("SELECT value FROM signal_vintages").fetchall()
    assert rows == [(0.6,)]


def test_insert_benchmark_upserts(conn):
    db.insert_benchmark(conn, [("2025-01-09", 6000.0)])
    db.insert_benchmark(conn, [("2025-01-09", 6001.0)])
    rows = conn.execute("SELECT close FROM benchmark_closes").fetchall()
    assert rows == [(6001.0,)]


def test_snapshot_header_roundtrip(conn):
    sid = db.write_snapshot(conn, "2025-01-15T00:00:00+00:00")
    db.finish_snapshot(conn, sid, 10, 20, 1)
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    assert row == (10, 20, 1)


def test_prune_deletes_only_old_headers_never_data(conn):
    old = db.write_snapshot(conn, "2024-01-01T00:00:00+00:00")
    new = db.write_snapshot(conn, "2025-01-14T00:00:00+00:00")
    db.insert_vintages(conn, [("T10Y2Y", "2020-01-09", "2020-01-09", 0.5)])
    db.insert_benchmark(conn, [("2020-01-09", 3000.0)])
    n = db.prune(conn, keep_days=30, now_iso="2025-01-15T00:00:00+00:00")
    assert n == 1
    ids = [r[0] for r in conn.execute("SELECT id FROM snapshots")]
    assert ids == [new] and old not in ids
    assert conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM benchmark_closes").fetchone() == (1,)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_backtest_db_schema.py tests/test_backtest_db_write.py -v`
Expected: FAIL with `ImportError` / `ModuleNotFoundError` on `sources.combiners.backtest.db`.

- [ ] **Step 3: Implement**

Create `sources/combiners/backtest/db.py`:

```python
"""backtest.db: point-in-time replay of composite's FRED regime signals.

Data tables are upsert-keyed history copied out of fred.db (never
snapshot-scoped); prune deletes old snapshot headers ONLY. The product is
the views (Tasks 5-6 of the plan; see the design spec): what flag
composite WOULD have emitted on each historical date using only data
knowable that day, and how the benchmark moved afterward. Manual analysis
tool — deliberately unscheduled."""

import sqlite3
from datetime import datetime, timedelta

_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,
    vintage_rows   INTEGER NOT NULL DEFAULT 0,
    benchmark_rows INTEGER NOT NULL DEFAULT 0,
    sources_failed INTEGER NOT NULL DEFAULT 0
);

-- ALFRED vintages for the replay series: one row per (observation date,
-- publication date). Copied verbatim from fred.db observation_vintages.
CREATE TABLE IF NOT EXISTS signal_vintages (
    series_id      TEXT NOT NULL,
    date           TEXT NOT NULL,
    realtime_start TEXT NOT NULL,
    value          REAL,
    PRIMARY KEY (series_id, date, realtime_start)
);

-- The grading spine: benchmark daily closes (SP500 via fred.db
-- observations; index closes are not revised).
CREATE TABLE IF NOT EXISTS benchmark_closes (
    date  TEXT PRIMARY KEY,
    close REAL NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Tables (CREATE IF NOT EXISTS), then views (DROP+CREATE)."""
    conn.executescript(_TABLES)
    conn.commit()


def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (now_iso,))
    conn.commit()  # survive a later per-source rollback
    return cur.lastrowid


def finish_snapshot(
    conn, sid: int, vintage_rows: int, benchmark_rows: int, sources_failed: int
) -> None:
    conn.execute(
        "UPDATE snapshots SET vintage_rows = ?, benchmark_rows = ?,"
        " sources_failed = ? WHERE id = ?",
        (vintage_rows, benchmark_rows, sources_failed, sid),
    )


def insert_vintages(conn, rows) -> int:
    rows = list(rows)
    conn.executemany(
        "INSERT OR REPLACE INTO signal_vintages"
        " (series_id, date, realtime_start, value) VALUES (?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_benchmark(conn, rows) -> int:
    rows = list(rows)
    conn.executemany(
        "INSERT OR REPLACE INTO benchmark_closes (date, close) VALUES (?, ?)", rows
    )
    return len(rows)


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Snapshot headers only — signal_vintages/benchmark_closes are the
    replay dataset and are never pruned."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    cur = conn.execute("DELETE FROM snapshots WHERE captured_at < ?", (cutoff,))
    conn.commit()
    return cur.rowcount
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_backtest_db_schema.py tests/test_backtest_db_write.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/db.py tests/test_backtest_db_schema.py tests/test_backtest_db_write.py
git commit --no-gpg-sign -m "feat(backtest): schema, writers, header-only prune"
```

---

### Task 5: Point-in-time views — `v_pit_signal` + `v_replay_flags`

**Files:**
- Modify: `sources/combiners/backtest/db.py`
- Test: `tests/test_backtest_db_views.py` (new)

**Interfaces:**
- Consumes: `catalog.REPLAY_SIGNALS` (Task 3), tables from Task 4.
- Produces: view `v_pit_signal(asof_date, series_id, value)` — for every benchmark date × replay series, the value as known on `asof_date`; view `v_replay_flags(asof_date, signal_id, value, score)` — the imported CASE applied to PIT values (NULL-value rows excluded). Task 6 joins `v_replay_flags` to `v_replay_returns` on `asof_date`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest_db_views.py`:

```python
import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def spine(c, rows):
    c.executemany("INSERT INTO benchmark_closes (date, close) VALUES (?, ?)", rows)


def vintage(c, series, date, realtime_start, value):
    c.execute(
        "INSERT INTO signal_vintages VALUES (?, ?, ?, ?)",
        (series, date, realtime_start, value),
    )


def pit(c, asof, series):
    return c.execute(
        "SELECT value FROM v_pit_signal WHERE asof_date = ? AND series_id = ?",
        (asof, series),
    ).fetchone()


# ---- v_pit_signal ----------------------------------------------------


def test_pit_no_lookahead_ignores_later_revision(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)  # future revision
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


def test_pit_reflects_revision_once_published(conn):
    spine(conn, [("2025-01-10", 100.0), ("2025-02-02", 101.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)
    assert pit(conn, "2025-02-02", "T10Y2Y") == (-0.7,)


def test_pit_hides_observation_published_after_asof(conn):
    # obs date is in the past but its FIRST vintage lands later: invisible.
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-15", 0.9)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (None,)


def test_pit_prefers_latest_observation_date(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-08", "2025-01-08", 0.3)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


# ---- v_replay_flags --------------------------------------------------


def test_flags_apply_composite_cases(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", -0.1)  # inverted -> -1
    vintage(conn, "BAMLH0A0HYM2", "2025-01-09", "2025-01-09", 5.5)  # >=5.0 -> -2
    rows = dict(
        conn.execute(
            "SELECT signal_id, score FROM v_replay_flags WHERE asof_date = '2025-01-10'"
        )
    )
    assert rows == {"fred_curve": -1, "fred_hy_spread": -2}


def test_flags_exclude_dates_with_no_published_value(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-15", 0.5)  # not yet published
    rows = conn.execute("SELECT * FROM v_replay_flags").fetchall()
    assert rows == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_backtest_db_views.py -v`
Expected: FAIL with `sqlite3.OperationalError: no such table: v_pit_signal` (or `no such view`).

- [ ] **Step 3: Implement**

In `sources/combiners/backtest/db.py`, add after the imports:

```python
from sources.combiners.backtest import catalog
```

Add after `_TABLES`:

```python
def _flags_select(signal: dict) -> str:
    return (
        f"SELECT asof_date, '{signal['signal_id']}' AS signal_id, value,\n"
        f"       {signal['score_case']} AS score\n"
        f"FROM v_pit_signal\n"
        f"WHERE series_id = '{signal['series_id']}' AND value IS NOT NULL"
    )


def _views() -> str:
    flags = "\nUNION ALL\n".join(_flags_select(s) for s in catalog.REPLAY_SIGNALS)
    return f"""
-- For every (benchmark trading date D, replay series): the value as KNOWN
-- on D — the latest observation date having any vintage published on or
-- before D, valued at its newest such vintage. NULL when nothing was
-- published yet (LEFT-JOIN-shaped miss, not an error).
DROP VIEW IF EXISTS v_pit_signal;
CREATE VIEW v_pit_signal AS
SELECT d.date AS asof_date, s.series_id,
       (SELECT v.value FROM signal_vintages v
         WHERE v.series_id = s.series_id
           AND v.realtime_start <= d.date
           AND v.value IS NOT NULL
         ORDER BY v.date DESC, v.realtime_start DESC
         LIMIT 1) AS value
FROM benchmark_closes d
CROSS JOIN (SELECT DISTINCT series_id FROM signal_vintages) s;

-- The flag composite WOULD have emitted on each date, via the identical
-- imported CASE expressions (see catalog.REPLAY_SIGNALS).
DROP VIEW IF EXISTS v_replay_flags;
CREATE VIEW v_replay_flags AS
{flags};
"""
```

Change `ensure_schema` to build the views too:

```python
def ensure_schema(conn) -> None:
    """Tables (CREATE IF NOT EXISTS), then views (DROP+CREATE)."""
    conn.executescript(_TABLES)
    conn.executescript(_views())
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_backtest_db_views.py tests/test_backtest_db_schema.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/db.py tests/test_backtest_db_views.py
git commit --no-gpg-sign -m "feat(backtest): point-in-time signal + flag views"
```

---

### Task 6: Grading views — `v_replay_returns` + `v_replay_efficacy`

**Files:**
- Modify: `sources/combiners/backtest/db.py`
- Test: `tests/test_backtest_db_views.py` (append)

**Interfaces:**
- Consumes: `v_replay_flags` (Task 5), `catalog.HORIZONS`, `sources.combiners.scorer.db._wilson` + `RELIABLE_MIN_N`.
- Produces: `v_replay_returns(asof_date, horizon, entry_date, entry_close, exit_date, exit_close, fwd_return)`; `v_replay_efficacy(signal_id, direction, horizon, n_days, avg_fwd_return, hit_rate, n_bench, hit_ci_lo, hit_ci_hi, reliable)`. Task 8's `run()` prints `v_replay_efficacy`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_backtest_db_views.py`:

```python
# ---- v_replay_returns ------------------------------------------------


def test_returns_entry_strictly_after_and_horizon_offsets(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    row = conn.execute(
        "SELECT entry_date, exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row[0] == "2025-01-02"  # first close STRICTLY after D
    assert row[1] == "2025-01-07"  # 5 trading rows after entry
    assert row[2] == pytest.approx(107.0 / 102.0 - 1)


def test_returns_unmatured_dates_yield_null(conn):
    spine(conn, [("2025-01-01", 100.0), ("2025-01-02", 101.0)])
    row = conn.execute(
        "SELECT exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row == (None, None)


# ---- v_replay_efficacy -----------------------------------------------


def test_efficacy_grades_bearish_flag_against_falling_benchmark(conn):
    # 30 falling closes; curve inverted from day one -> every matured
    # bearish day is a hit at every horizon.
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    row = conn.execute(
        "SELECT n_bench, hit_rate, reliable FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    # 30 spine days; asof d has entry d+1, exit d+6 -> matured for d in 1..24
    assert row[0] == 24
    assert row[1] == pytest.approx(1.0)
    assert row[2] == 0  # 24 < RELIABLE_MIN_N (30)


def test_efficacy_wilson_ci_brackets_hit_rate(conn):
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    lo, hi = conn.execute(
        "SELECT hit_ci_lo, hit_ci_hi FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    assert 0.0 < lo < 1.0  # Wilson never collapses to zero width on all-hit
    assert hi >= 1.0 or hi == pytest.approx(1.0, abs=1e-9)


def test_efficacy_neutral_rows_reported_but_ungraded(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", 0.5)  # not inverted -> 0
    row = conn.execute(
        "SELECT n_days, n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'neutral' AND horizon = 5"
    ).fetchone()
    assert row[0] > 0  # reported
    assert row[1] == 0 and row[2] is None  # excluded from grading
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_backtest_db_views.py -v`
Expected: the 5 new tests FAIL (`no such table: v_replay_returns` / `v_replay_efficacy`); Task 5's tests still PASS.

- [ ] **Step 3: Implement**

In `sources/combiners/backtest/db.py`, extend the imports:

```python
from sources.combiners.scorer.db import RELIABLE_MIN_N, _wilson
```

Extend `_views()` by appending to the returned f-string (before the closing `"""`), and add the horizons helper above it:

```python
def _horizons_union() -> str:
    return " UNION ALL ".join(f"SELECT {h} AS horizon" for h in catalog.HORIZONS)
```

```sql
-- Benchmark spine with row numbers: horizons step in TRADING days.
DROP VIEW IF EXISTS v_spine;
CREATE VIEW v_spine AS
SELECT date, close, ROW_NUMBER() OVER (ORDER BY date) AS rn
FROM benchmark_closes;

-- Forward benchmark returns per decision date x horizon. Entry is the
-- first close STRICTLY after asof_date (same no-overnight-look-ahead rule
-- as scorer's entry_for); exit is `horizon` spine rows after entry.
-- Unmatured dates yield NULL via LEFT JOIN.
DROP VIEW IF EXISTS v_replay_returns;
CREATE VIEW v_replay_returns AS
SELECT d.date AS asof_date, h.horizon,
       e.date AS entry_date, e.close AS entry_close,
       x.date AS exit_date, x.close AS exit_close,
       CASE WHEN x.close IS NOT NULL AND e.close IS NOT NULL
            THEN x.close / e.close - 1 END AS fwd_return
FROM v_spine d
CROSS JOIN ({_horizons_union()}) h
LEFT JOIN v_spine e ON e.rn = d.rn + 1
LEFT JOIN v_spine x ON x.rn = d.rn + 1 + h.horizon;

-- Hit-rate scoreboard, same column shape as scorer v_signal_efficacy:
-- hit = sign agreement between flag and forward benchmark return.
-- Neutral (score 0) days form their own direction group with NULL hits —
-- reported as base rate, excluded from grading.
DROP VIEW IF EXISTS v_replay_efficacy;
CREATE VIEW v_replay_efficacy AS
SELECT signal_id, direction, horizon,
       COUNT(*) AS n_days,
       AVG(fwd_return) AS avg_fwd_return,
       AVG(hit) AS hit_rate,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable
FROM (
    SELECT f.signal_id,
           CASE WHEN f.score < 0 THEN 'bearish'
                WHEN f.score > 0 THEN 'bullish' ELSE 'neutral' END AS direction,
           r.horizon, r.fwd_return,
           CASE WHEN f.score = 0 OR r.fwd_return IS NULL THEN NULL
                WHEN f.score < 0 AND r.fwd_return < 0 THEN 1
                WHEN f.score > 0 AND r.fwd_return > 0 THEN 1
                ELSE 0 END AS hit
    FROM v_replay_flags f
    JOIN v_replay_returns r ON r.asof_date = f.asof_date
)
GROUP BY signal_id, direction, horizon;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_backtest_db_views.py -v`
Expected: all PASS. If `test_efficacy_wilson_ci_brackets_hit_rate` fails on the `hi` assertion, print the actual value — Wilson's upper bound at p=1.0 is exactly 1.0-ish; loosen only the `hi` assertion to `hi == pytest.approx(1.0, abs=0.05)` if SQLite float noise bites.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/db.py tests/test_backtest_db_views.py
git commit --no-gpg-sign -m "feat(backtest): forward-return and Wilson-CI efficacy views"
```

---

### Task 7: `backtest` fetch (read-only copy out of fred.db)

**Files:**
- Create: `sources/combiners/backtest/fetch.py`
- Test: `tests/test_backtest_fetch.py`

**Interfaces:**
- Consumes: fred.db table shapes — `observation_vintages(series_id, date, realtime_start, value)`, `observations(series_id, date, value, ...)`.
- Produces:
  - `attach_ro(conn, db_path: str, alias: str = "src") -> None` (raises `FileNotFoundError` if missing)
  - `detach(conn, alias: str = "src") -> None`
  - `harvest_vintages(conn, series_ids) -> list` — rows `(series_id, date, realtime_start, value)`
  - `harvest_benchmark(conn, series_id: str) -> list` — rows `(date, value)`, NULL values excluded

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest_fetch.py`:

```python
import sqlite3

import pytest

from sources.combiners.backtest import fetch


@pytest.fixture
def fred_db(tmp_path):
    path = tmp_path / "fred.db"
    c = sqlite3.connect(path)
    c.execute(
        "CREATE TABLE observation_vintages"
        " (series_id TEXT, date TEXT, realtime_start TEXT, value REAL)"
    )
    c.execute("CREATE TABLE observations (series_id TEXT, date TEXT, value REAL)")
    c.executemany(
        "INSERT INTO observation_vintages VALUES (?, ?, ?, ?)",
        [
            ("T10Y2Y", "2025-01-09", "2025-01-09", 0.5),
            ("UNRELATED", "2025-01-09", "2025-01-09", 9.9),
        ],
    )
    c.executemany(
        "INSERT INTO observations VALUES (?, ?, ?)",
        [
            ("SP500", "2025-01-09", 6000.0),
            ("SP500", "2025-01-10", None),  # FRED '.' placeholder
            ("T10Y2Y", "2025-01-09", 0.5),
        ],
    )
    c.commit()
    c.close()
    return str(path)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", uri=True)
    yield c
    c.close()


def test_attach_ro_missing_file_raises(conn, tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))


def test_harvest_vintages_filters_to_requested_series(conn, fred_db):
    fetch.attach_ro(conn, fred_db)
    rows = fetch.harvest_vintages(conn, ["T10Y2Y"])
    fetch.detach(conn)
    assert rows == [("T10Y2Y", "2025-01-09", "2025-01-09", 0.5)]


def test_harvest_benchmark_filters_series_and_nulls(conn, fred_db):
    fetch.attach_ro(conn, fred_db)
    rows = fetch.harvest_benchmark(conn, "SP500")
    fetch.detach(conn)
    assert rows == [("2025-01-09", 6000.0)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_backtest_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError` on `sources.combiners.backtest.fetch`.

- [ ] **Step 3: Implement**

Create `sources/combiners/backtest/fetch.py`:

```python
"""Pure extraction against fred.db ATTACHed read-only. No network anywhere
in this package — the replay's external feed is the local data/ dir (same
convention as the composite combiner)."""

import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    """Attach a source DB read-only. The connection must have been opened
    with uri=True or the mode=ro URI is rejected by SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


def harvest_vintages(conn, series_ids) -> list:
    """Full vintage history for the replay series, verbatim."""
    ids = list(series_ids)
    qmarks = ",".join("?" * len(ids))
    return conn.execute(
        "SELECT series_id, date, realtime_start, value"
        f" FROM src.observation_vintages WHERE series_id IN ({qmarks})"
        " ORDER BY series_id, date, realtime_start",
        ids,
    ).fetchall()


def harvest_benchmark(conn, series_id: str) -> list:
    """Benchmark daily closes; index closes are unrevised so plain
    observations suffice (no vintages needed)."""
    return conn.execute(
        "SELECT date, value FROM src.observations"
        " WHERE series_id = ? AND value IS NOT NULL ORDER BY date",
        (series_id,),
    ).fetchall()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_backtest_fetch.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/fetch.py tests/test_backtest_fetch.py
git commit --no-gpg-sign -m "feat(backtest): read-only vintage/benchmark harvest from fred.db"
```

---

### Task 8: `backtest` run + registry entry

**Files:**
- Create: `sources/combiners/backtest/run.py`
- Modify: `registry.py` (import + `REGISTRY` entry)
- Test: `tests/test_backtest_run.py`, `tests/test_registry.py` (append one test)

**Interfaces:**
- Consumes: everything above.
- Produces: `run(db_path, db_dir="data", now_iso=None, keep_days=None, harvest_vintages=..., harvest_benchmark=...) -> tuple[int, int, int]` (sid, vintage rows, benchmark rows); `main(argv=None)`; `main.py backtest ...` dispatch.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backtest_run.py`:

```python
import sqlite3

import pytest

from sources.combiners.backtest import db, run


@pytest.fixture
def data_dir(tmp_path):
    """A data/ dir containing a minimal real fred.db."""
    c = sqlite3.connect(tmp_path / "fred.db")
    c.execute(
        "CREATE TABLE observation_vintages"
        " (series_id TEXT, date TEXT, realtime_start TEXT, value REAL)"
    )
    c.execute("CREATE TABLE observations (series_id TEXT, date TEXT, value REAL)")
    c.execute(
        "INSERT INTO observation_vintages VALUES ('T10Y2Y', '2025-01-01', '2025-01-01', -0.5)"
    )
    c.executemany(
        "INSERT INTO observations VALUES ('SP500', ?, ?)",
        [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)],
    )
    c.commit()
    c.close()
    return str(tmp_path)


def test_run_copies_and_reports(data_dir, tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00"
    )
    assert (n_vint, n_bench) == (1, 30)
    out = capsys.readouterr().out
    assert "fred_curve" in out and "bearish" in out
    conn = db.connect(str(tmp_path / "backtest.db"))
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    conn.close()
    assert row == (1, 30, 0)


def test_run_missing_fred_db_skips_and_counts_failure(tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"),
        db_dir=str(tmp_path),  # no fred.db here
        now_iso="2025-02-01T00:00:00+00:00",
    )
    assert (n_vint, n_bench) == (0, 0)
    assert "FileNotFoundError" in capsys.readouterr().out
    conn = db.connect(str(tmp_path / "backtest.db"))
    (failed,) = conn.execute(
        "SELECT sources_failed FROM snapshots WHERE id = ?", (sid,)
    ).fetchone()
    conn.close()
    assert failed == 1


def test_run_is_idempotent(data_dir, tmp_path):
    path = str(tmp_path / "backtest.db")
    run.run(path, db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00")
    run.run(path, db_dir=data_dir, now_iso="2025-02-02T00:00:00+00:00")
    conn = db.connect(path)
    counts = (
        conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone()[0],
        conn.execute("SELECT COUNT(*) FROM benchmark_closes").fetchone()[0],
    )
    conn.close()
    assert counts == (1, 30)
```

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_backtest():
    import registry

    assert "backtest" in registry.REGISTRY
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_backtest_run.py tests/test_registry.py -v`
Expected: backtest tests FAIL (`ModuleNotFoundError` on `run`); `test_dispatch_lists_backtest` FAILS (KeyError-shaped assert); existing registry tests PASS.

- [ ] **Step 3: Implement**

Create `sources/combiners/backtest/run.py`:

```python
"""Point-in-time replay proof: copy vintage + benchmark rows out of
fred.db, let the views grade what composite's FRED regime signals would
have said each historical day. Manual analysis tool — deliberately
unscheduled (see docs/SCHEDULE.md)."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.backtest import catalog, db, fetch


def run(
    db_path,
    db_dir="data",
    now_iso=None,
    keep_days=None,
    harvest_vintages=fetch.harvest_vintages,
    harvest_benchmark=fetch.harvest_benchmark,
):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso)
        n_vint = n_bench = failures = 0
        path = os.path.join(db_dir, catalog.FRED_DB)
        try:
            fetch.attach_ro(conn, path)
        except Exception as e:
            failures += 1
            print(f"skip {catalog.FRED_DB}: {type(e).__name__}")
        else:
            try:
                series = [s["series_id"] for s in catalog.REPLAY_SIGNALS]
                n_vint = db.insert_vintages(conn, harvest_vintages(conn, series))
                n_bench = db.insert_benchmark(
                    conn, harvest_benchmark(conn, catalog.BENCHMARK_SERIES)
                )
            except Exception as e:
                failures += 1
                conn.rollback()
                print(f"skip {catalog.FRED_DB}: {type(e).__name__}")
            finally:
                fetch.detach(conn)
        db.finish_snapshot(conn, sid, n_vint, n_bench, failures)
        conn.commit()
        for row in conn.execute(
            "SELECT signal_id, direction, horizon, n_bench, hit_rate,"
            " hit_ci_lo, hit_ci_hi, reliable FROM v_replay_efficacy"
            " ORDER BY signal_id, direction, horizon"
        ):
            sig, direction, horizon, n, hr, lo, hi, rel = row
            stats = (
                f"hit {hr:.2f} (CI {lo:.2f}-{hi:.2f}, n={n})"
                if hr is not None
                else f"ungraded (n_days incl. neutral; n={n})"
            )
            tag = " reliable" if rel else ""
            print(f"{sig} {direction} {horizon}d: {stats}{tag}")
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, n_vint, n_bench


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="backtest",
        description="Point-in-time replay of composite's FRED regime signals"
        " (reads fred.db read-only; manual tool, not scheduled)",
    )
    p.add_argument("--db", default="backtest.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, n_vint, n_bench = run(a.db, a.db_dir, keep_days=a.keep_days)
    print(f"backtest snapshot {sid}: {n_vint} vintages, {n_bench} closes, into {a.db}")


if __name__ == "__main__":
    main()
```

In `registry.py`, add the import (alphabetical, with the other combiners):

```python
from sources.combiners.backtest.run import main as backtest_main
```

and the entry after `"advisor"`:

```python
    "backtest": backtest_main,
```

- [ ] **Step 4: Run the FULL suite + gates**

Run: `uv run ruff check && uv run ruff format --check && uv run mypy && uv run pytest`
Expected: all four green (~700+ tests). Fix any ruff/mypy nits (import order, annotations) before committing.

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/backtest/run.py registry.py tests/test_backtest_run.py tests/test_registry.py
git commit --no-gpg-sign -m "feat(backtest): run orchestration + registry dispatch"
```

---

### Task 9: Schedule `--vintages` + document

**Files:**
- Modify: `deploy/launchd/install.py` (line ~68, the `"fred"` entry)
- Modify: `docs/SCHEDULE.md` (fred row ~line 32; Operations section ~line 88)

**Interfaces:**
- Produces: the nightly fred job fetches vintages; the docs record where the replay tool lives.

- [ ] **Step 1: Edit install.py**

Change:

```python
    "fred": (job("fred"), weekly(MON_FRI, 16, 40)),
```

to:

```python
    "fred": (job("fred", "--vintages"), weekly(MON_FRI, 16, 40)),
```

- [ ] **Step 2: Edit docs/SCHEDULE.md**

Replace the fred row:

```markdown
| `fred` | 4:40pm | Daily rate series finalized ~4:15pm ET. Runs `--vintages`: idempotent upsert of the full ALFRED revision history into `observation_vintages` (~31 extra API calls/run; feeds the backtest combiner's point-in-time replay). If nightly runtime ever hurts, split `--vintages` to a weekly slot — the vintage fetch is a separate call per series |
```

Append to the **Operations** section:

```markdown
- **Backtest replay** (manual, unscheduled by design):
  `uv run python main.py backtest --db data/backtest.db` — copies FRED
  vintages + SP500 closes out of `data/fred.db` (read-only) and prints
  point-in-time hit rates for the FRED regime signals. See
  `docs/superpowers/specs/2026-07-07-backtesting-foundation-design.md`.
```

- [ ] **Step 3: Verify dry-run renders**

Run: `uv run python deploy/launchd/install.py --dry-run | grep -A2 fred`
Expected: the fred plist ProgramArguments include `--vintages`.

- [ ] **Step 4: Commit**

```bash
git add deploy/launchd/install.py docs/SCHEDULE.md
git commit --no-gpg-sign -m "feat(fred): nightly --vintages; document backtest manual tool"
```

---

### Task 10: Ops — backfill, install, proof run, roadmap prune

This task runs against live data (network + launchctl); do it in the main session, not a subagent.

- [ ] **Step 1: One-shot vintage backfill (network; needs FRED_API_KEY from .env)**

```bash
set -a; source .env; set +a
uv run python main.py fred --db data/fred.db --vintages
```

Expected: per-series lines, no failures (429 backoff is automatic; rerun is idempotent if one series skips).

- [ ] **Step 2: Sanity-check the backfill**

```bash
sqlite3 data/fred.db "SELECT COUNT(DISTINCT series_id) FROM observation_vintages;"
sqlite3 data/fred.db "SELECT COUNT(*) FROM (SELECT date FROM observation_vintages WHERE series_id='PAYEMS' GROUP BY date HAVING COUNT(*) > 1);"
sqlite3 data/fred.db "SELECT COUNT(*) FROM observations WHERE series_id='SP500';"
```

Expected: 31 series; PAYEMS has many multi-vintage dates (revisions captured); SP500 has ~2500 rows (~10y of trading days).

- [ ] **Step 3: Reload the schedule**

```bash
uv run python deploy/launchd/install.py
```

Expected: plists rewritten + bootstrapped without error.

- [ ] **Step 4: The proof run**

```bash
uv run python main.py backtest --db data/backtest.db
```

Expected: `v_replay_efficacy` lines for `fred_curve` and `fred_hy_spread` (bearish/bullish/neutral × 5/10/21d) with multi-thousand `n_days` and `reliable` = 1 on well-populated buckets. Read the numbers — they are the roadmap deliverable.

- [ ] **Step 5: Prune ROADMAP + update memory**

In `docs/ROADMAP.md`: replace the whole `### 7. Backtesting foundation` section with a shipped parenthetical in the same style as items 1–6, quoting the headline hit-rate numbers from Step 4's output; under item 8 add a bullet:

```markdown
- **Bar-store build (`bars` slice)** (deferred from shipped item 7) — dedicated
  OHLCV screener with its own DB when ticker-grain replay is needed; the
  close ledger stays evidence-only. Decision + rationale:
  `docs/superpowers/specs/2026-07-07-backtesting-foundation-design.md` §4.
```

Update the memory file `fred-vintages-deferred.md` (it is no longer deferred — vintages are scheduled nightly as of 2026-07-07) and its `MEMORY.md` index line.

- [ ] **Step 6: Final commit**

```bash
git add docs/ROADMAP.md
git commit --no-gpg-sign -m "docs(roadmap): item 7 shipped — backtesting foundation"
```

---

## Self-Review (completed at write time)

- **Spec coverage:** §1 FRED → Tasks 1, 9, 10; §2 hoist → Task 2; §3 combiner → Tasks 3–8; §4 ADR → already in spec + Task 10 Step 5 roadmap pointer; §5 error handling → Tasks 7–8; §6 testing → every task's test steps; §7 ops → Tasks 9–10.
- **Type consistency:** `run()` returns `(sid, n_vint, n_bench)` in both Task 8 code and tests; writer names (`insert_vintages`/`insert_benchmark`) match across Tasks 4/8; view/column names match across Tasks 5/6/8 tests.
- **Known judgment call:** `v_pit_signal` uses a correlated subquery (~2.5k dates × 2 series) — fine at proof scale; revisit only if the roster grows.
