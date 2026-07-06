# Composite Scorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `scorer` combiner that materializes forward returns for matured composite scores into `data/scorer.db` — the permanent efficacy dataset for ticker buckets, individual signals, and regime tags.

**Architecture:** Fourth four-file package at `sources/combiners/scorer/`. Nightly three-step run, every step idempotent: (1) **harvest** `(symbol, price_date, close)` from `stocks.db` + `etfs.db` (attached read-only, one at a time) into a local `prices` ledger; (2) **register** pending outcome rows for unregistered composite snapshots with the entry side captured immediately (kills the 30-day source-prune race); (3) **mature** pending rows via pure local SQL when the Nth trading day's price exists. Spec: `docs/superpowers/specs/2026-07-06-composite-scorer-design.md`.

**Tech Stack:** Python 3.12 stdlib only; pytest via `uv run pytest`.

## Global Constraints

- **Stdlib only; no network in the package.** The scorer's feeds are `data/composite.db`, `data/stocks.db`, `data/etfs.db`.
- **Sources attached strictly read-only** (`file:<path>?mode=ro`; scorer's own connection opened `sqlite3.connect(path, uri=True)`), **one at a time**.
- **Determinism:** time enters `run()` only as injected `now_iso` (UTC isoformat, fixed width); trading-day arithmetic uses ledger `price_date`s only — no calendar math, no `date('now')`.
- **Secret hygiene:** failure paths print only `type(e).__name__`.
- **Outcome tables are NEVER pruned** — they are the experiment. `prune` touches only `snapshots` (run headers) and `prices` older than `PRICE_KEEP_DAYS = 90` (must stay > 21 trading days ≈ 31 calendar days, with margin).
- **The scorer never influences the composite** — no imports from scorer into composite, no writes to any other DB.
- **Registration is all-or-nothing per composite snapshot** (single transaction incl. the `registered_snapshots` marker row). Only composite snapshots **having a `market_regime` row** are registered (phase-2-failed snapshots are not opinions).
- **Entry staleness guard:** a row registers only if its entry `price_date >= date(composite_date, '-7 days')` (`ENTRY_MAX_AGE_DAYS = 7`); stale/no-price symbols are counted as skipped, not silently dropped.
- **Score-0 signal rows are not registered** (informational signals — `portfolio_holding`, `edgar_insider` — have no direction to grade).
- **Scoring convention (documented optimism):** entry = close of last trading day ≤ composite date; exit = close of the Nth distinct ledger `price_date` after entry; benchmark (SPY) measured on the SAME entry/exit dates as the symbol; bench columns NULL rather than failing when SPY lacks a date.
- Offline tests only; miniature source DBs built via each source's own `ensure_schema` (stocks/etfs need `ensure_schema(conn, {"priceDate": "TEXT", "close": "REAL"})` — the metrics table's data columns are dynamic).
- Commits: `git commit --no-gpg-sign`, no Co-Authored-By. Full suite green after every task (`uv run pytest -q`; note a pre-commit hook re-runs format/typecheck/suite).

## File Structure

- Create: `sources/combiners/scorer/__init__.py` (empty), `catalog.py`, `fetch.py`, `db.py`, `run.py`
- Modify: `registry.py`, `deploy/launchd/install.py`, `docs/SCHEDULE.md`, `CLAUDE.md`
- Tests: `tests/test_scorer_catalog.py`, `tests/test_scorer_db_schema.py`, `tests/test_scorer_db_write.py`, `tests/test_scorer_db_views.py`, `tests/test_scorer_fetch.py`, `tests/test_scorer_run.py`, `tests/test_registry.py` (append)

---

### Task 1: Skeleton, catalog constants, schema

**Files:**
- Create: `sources/combiners/scorer/__init__.py`, `sources/combiners/scorer/catalog.py`, `sources/combiners/scorer/db.py`
- Test: `tests/test_scorer_catalog.py`, `tests/test_scorer_db_schema.py`

**Interfaces:**
- Produces: `catalog.HORIZONS = (5, 10, 21)`, `catalog.BENCHMARK = "SPY"`, `catalog.PRICE_DBS = ("stocks.db", "etfs.db")`, `catalog.COMPOSITE_DB = "composite.db"`, `catalog.ENTRY_MAX_AGE_DAYS = 7`; `db.connect(path)` (uri=True, WAL), `db.ensure_schema(conn)`, `db.PRICE_KEEP_DAYS = 90`. Tables: `snapshots(id, captured_at, harvested, registered, matured, skipped)`, `prices(symbol, price_date, close, PK(symbol, price_date))`, `registered_snapshots(composite_snapshot_id PK, composite_date, registered_at, ticker_rows, signal_rows, skipped)`, `ticker_outcomes`, `signal_outcomes`, `regime_outcomes` exactly as in the spec's Schema section (PKs: `(composite_snapshot_id, symbol, horizon)` / `(composite_snapshot_id, signal_id, entity, horizon)` / `(composite_snapshot_id, horizon)`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer_catalog.py
from sources.combiners.scorer import catalog


def test_constants_wellformed():
    assert catalog.HORIZONS == (5, 10, 21)
    assert catalog.BENCHMARK == "SPY"
    assert catalog.PRICE_DBS == ("stocks.db", "etfs.db")
    assert catalog.COMPOSITE_DB == "composite.db"
    assert catalog.ENTRY_MAX_AGE_DAYS >= 5
```

```python
# tests/test_scorer_db_schema.py
import sqlite3

import pytest

from sources.combiners.scorer import db


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def test_schema_tables(tmp_path):
    conn = _conn(tmp_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "prices", "registered_snapshots", "ticker_outcomes",
            "signal_outcomes", "regime_outcomes"} <= tables
    db.ensure_schema(conn)  # idempotent


def test_connect_wal_uri(tmp_path):
    conn = _conn(tmp_path)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    other = tmp_path / "src.db"
    sqlite3.connect(str(other)).close()
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{other}?mode=ro",))


def test_outcome_pk_prevents_dupes(tmp_path):
    conn = _conn(tmp_path)
    row = (1, "2026-07-06", "AAPL", 3, 3, 3, 0, 0, 5,
           "2026-07-02", 200.0, 600.0)
    ins = ("INSERT INTO ticker_outcomes (composite_snapshot_id,"
           " composite_date, symbol, score_sum, total, bullish, bearish,"
           " in_portfolio, horizon, entry_date, entry_close,"
           " bench_entry_close) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
    conn.execute(ins, row)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, row)
    assert conn.execute("INSERT OR IGNORE INTO prices VALUES ('A','2026-07-02',1.0)").rowcount == 1
    assert conn.execute("INSERT OR IGNORE INTO prices VALUES ('A','2026-07-02',1.0)").rowcount == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_catalog.py tests/test_scorer_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.combiners.scorer'`

- [ ] **Step 3: Write the implementation**

Create empty `sources/combiners/scorer/__init__.py`, then:

```python
# sources/combiners/scorer/catalog.py
"""Scorer configuration. The scorer grades composite opinions against
forward returns; it never feeds anything back into the composite."""

HORIZONS = (5, 10, 21)          # trading days (ledger price_date steps)
BENCHMARK = "SPY"               # lives in etfs.db
PRICE_DBS = ("stocks.db", "etfs.db")
COMPOSITE_DB = "composite.db"
# A row registers only if its entry price is at most this many calendar
# days older than the composite snapshot (halted/delisted-symbol guard).
ENTRY_MAX_AGE_DAYS = 7
```

```python
# sources/combiners/scorer/db.py
"""scorer.db: the permanent efficacy dataset. prices is a rolling ledger;
outcome tables are never pruned — they ARE the experiment."""
import sqlite3
from datetime import datetime, timedelta

PRICE_KEEP_DAYS = 90  # must stay > 21 trading days (~31 calendar) + margin

_SCHEMA = """
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


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_catalog.py tests/test_scorer_db_schema.py -v`
Expected: 5 passed

- [ ] **Step 5: Full suite, commit**

Run: `uv run pytest -q` → green.

```bash
git add sources/combiners/scorer tests/test_scorer_catalog.py tests/test_scorer_db_schema.py
git commit --no-gpg-sign -m "feat(scorer): scorer package skeleton, catalog constants, scorer.db schema"
```

---

### Task 2: Writers — ledger, registration, maturation, prune (`db.py` part 2)

**Files:**
- Modify: `sources/combiners/scorer/db.py` (append)
- Test: `tests/test_scorer_db_write.py`

**Interfaces:**
- Consumes: Task 1 schema + catalog constants (passed in as args — db.py does NOT import catalog).
- Produces:
  - `write_snapshot(conn, now_iso) -> int` (commits immediately), `finish_snapshot(conn, sid, harvested, registered, matured, skipped)`
  - `insert_prices(conn, rows) -> int` — rows of `(symbol, price_date, close)`, `INSERT OR IGNORE`, returns inserted count
  - `entry_for(conn, symbol, composite_date, max_age_days) -> (price_date, close) | None` — newest ledger row ≤ composite_date, None if absent or older than the guard
  - `register_snapshot(conn, csid, composite_date, ticker_rows, signal_rows, regime, horizons, benchmark, max_age_days, now_iso) -> (registered_rows, skipped)` — single transaction: marker + ticker/signal/regime outcome rows; entry via `entry_for`; bench entry = benchmark close ON the symbol's entry_date (NULL if absent); regime rows use the benchmark's own entry and are skipped (counted) if the benchmark has no usable entry; signal rows with score 0 are the CALLER's job to exclude (register writes what it is given)
  - `mature(conn, now_iso) -> int` — fills exit/return columns for every pending row across all three tables where the Nth distinct `price_date` after entry exists in the ledger; benchmark exit may be NULL while the row still matures
  - `registered_ids(conn) -> set[int]`
  - `prune(conn, keep_days, now_iso) -> int` — deletes old run headers AND `prices` rows with `price_date <` (now − PRICE_KEEP_DAYS); NEVER touches outcome tables

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer_db_write.py
from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _ledger(conn, symbol, dates, start=100.0, step=1.0):
    """Insert a run of closes: dates[i] -> start + i*step."""
    db.insert_prices(conn, [(symbol, d, start + i * step)
                            for i, d in enumerate(dates)])


# 8 trading days around the 2026-07-04 holiday weekend (Jul 3 closed).
DAYS = ["2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30",
        "2026-07-01", "2026-07-02", "2026-07-06", "2026-07-07"]


def test_insert_prices_dedupes(tmp_path):
    conn = _conn(tmp_path)
    assert db.insert_prices(conn, [("A", "2026-07-02", 1.0)] * 2) == 1


def test_entry_for_respects_guard(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    # weekend composite date -> Friday 07-02 close
    assert db.entry_for(conn, "AAPL", "2026-07-05", 7) == ("2026-07-02", 105.0)
    # stale: newest price 07-07, composite date 30 days later
    assert db.entry_for(conn, "AAPL", "2026-08-15", 7) is None
    assert db.entry_for(conn, "GHOST", "2026-07-05", 7) is None


def test_register_and_mature_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)                       # 100..107
    _ledger(conn, "SPY", DAYS, start=500.0)           # 500..507
    reg, skipped = db.register_snapshot(
        conn, csid=1, composite_date="2026-07-01",
        ticker_rows=[dict(symbol="AAPL", score_sum=3, total=3, bullish=3,
                          bearish=0, in_portfolio=0)],
        signal_rows=[dict(signal_id="si_days_to_cover", entity="AAPL",
                          score=2, via_crosswalk=0)],
        regime="risk_on", horizons=(2,), benchmark="SPY",
        max_age_days=7, now_iso=NOW)
    assert (reg, skipped) == (3, 0)   # 1 ticker + 1 signal + 1 regime
    # entry was 07-01 (close 104 / 504); +2 trading days = 07-06
    assert db.mature(conn, NOW) == 3
    t = conn.execute("SELECT entry_date, entry_close, exit_date, exit_close,"
                     " fwd_return, bench_fwd_return FROM ticker_outcomes"
                     ).fetchone()
    assert t[0] == "2026-07-01" and t[1] == 104.0
    assert t[2] == "2026-07-06" and t[3] == 106.0
    assert abs(t[4] - (106.0 / 104.0 - 1)) < 1e-9
    assert abs(t[5] - (506.0 / 504.0 - 1)) < 1e-9
    r = conn.execute("SELECT regime, bench_fwd_return FROM regime_outcomes"
                     ).fetchone()
    assert r[0] == "risk_on" and abs(r[1] - (506.0 / 504.0 - 1)) < 1e-9


def test_pending_without_data_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", 
                         [dict(symbol="AAPL", score_sum=2, total=2,
                               bullish=2, bearish=0, in_portfolio=0)],
                         [], "mixed", (5,), "SPY", 7, NOW)
    assert db.mature(conn, NOW) == 0   # only 1 day past entry exists
    assert conn.execute("SELECT exit_close FROM ticker_outcomes"
                        ).fetchone()[0] is None


def test_register_skips_stale_and_missing_symbols(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-06",
        [dict(symbol="GHOST", score_sum=2, total=2, bullish=2, bearish=0,
              in_portfolio=0)],
        [], "risk_on", (5,), "SPY", 7, NOW)
    assert skipped == 1                       # GHOST has no prices
    assert reg == 1                           # regime row still registered
    assert 1 in db.registered_ids(conn)


def test_register_is_atomic_and_once(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                         (5,), "SPY", 7, NOW)
    import pytest, sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                             (5,), "SPY", 7, NOW)


def test_bench_missing_registers_null_bench(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-01",
        [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0,
              in_portfolio=0)],
        [], "risk_on", (2,), "SPY", 7, NOW)
    assert conn.execute("SELECT bench_entry_close FROM ticker_outcomes"
                        ).fetchone()[0] is None
    # regime needs the benchmark; skipped, but ticker row registered
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes"
                        ).fetchone()[0] == 0
    db.mature(conn, NOW)                      # matures with NULL bench
    row = conn.execute("SELECT fwd_return, bench_fwd_return"
                       " FROM ticker_outcomes").fetchone()
    assert row[0] is not None and row[1] is None


def test_prune_never_touches_outcomes(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", ["2026-01-02"])     # ancient ledger row
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                         (5,), "SPY", 7, NOW)
    old_header = db.write_snapshot(conn, "2025-01-01T00:00:00+00:00")
    db.prune(conn, keep_days=90, now_iso=NOW)
    assert conn.execute("SELECT COUNT(*) FROM prices WHERE symbol='AAPL'"
                        ).fetchone()[0] == 0  # ancient price pruned
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes"
                        ).fetchone()[0] == 1  # outcomes untouched
    assert conn.execute("SELECT COUNT(*) FROM snapshots WHERE id=?",
                        (old_header,)).fetchone()[0] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_db_write.py -v`
Expected: FAIL with `AttributeError` on `insert_prices`

- [ ] **Step 3: Write the implementation (append to db.py)**

```python
def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)",
                       (now_iso,))
    conn.commit()  # survive later rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid, harvested, registered, matured, skipped):
    conn.execute("UPDATE snapshots SET harvested=?, registered=?,"
                 " matured=?, skipped=? WHERE id=?",
                 (harvested, registered, matured, skipped, sid))


def insert_prices(conn, rows) -> int:
    n = 0
    for symbol, price_date, close in rows:
        if symbol is None or price_date is None or close is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, price_date, close)"
            " VALUES (?, ?, ?)", (symbol, price_date, close))
        n += cur.rowcount
    return n


def entry_for(conn, symbol, composite_date, max_age_days):
    """Newest ledger close on/before composite_date, unless staler than the
    guard (halted/delisted symbols must not register garbage windows)."""
    row = conn.execute(
        "SELECT price_date, close FROM prices WHERE symbol=?"
        " AND price_date <= ? AND price_date >= date(?, ?)"
        " ORDER BY price_date DESC LIMIT 1",
        (symbol, composite_date, composite_date,
         f"-{int(max_age_days)} days")).fetchone()
    return (row[0], row[1]) if row else None


def _bench_close(conn, benchmark, price_date):
    row = conn.execute("SELECT close FROM prices WHERE symbol=?"
                       " AND price_date=?", (benchmark, price_date)).fetchone()
    return row[0] if row else None


def register_snapshot(conn, csid, composite_date, ticker_rows, signal_rows,
                      regime, horizons, benchmark, max_age_days,
                      now_iso) -> tuple:
    """All-or-nothing registration of one composite snapshot: the marker row
    and every outcome row commit together. Returns (registered, skipped)."""
    registered = skipped = 0
    with conn:  # transaction
        conn.execute(
            "INSERT INTO registered_snapshots (composite_snapshot_id,"
            " composite_date, registered_at, ticker_rows, signal_rows,"
            " skipped) VALUES (?, ?, ?, 0, 0, 0)",
            (csid, composite_date, now_iso))
        for r in ticker_rows:
            entry = entry_for(conn, r["symbol"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO ticker_outcomes"
                    " (composite_snapshot_id, composite_date, symbol,"
                    "  score_sum, total, bullish, bearish, in_portfolio,"
                    "  horizon, entry_date, entry_close, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (csid, composite_date, r["symbol"], r["score_sum"],
                     r["total"], r["bullish"], r["bearish"],
                     r["in_portfolio"], h, entry[0], entry[1], bench))
                registered += 1
        for r in signal_rows:
            entry = entry_for(conn, r["entity"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO signal_outcomes"
                    " (composite_snapshot_id, composite_date, signal_id,"
                    "  entity, score, via_crosswalk, horizon, entry_date,"
                    "  entry_close, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (csid, composite_date, r["signal_id"], r["entity"],
                     r["score"], r["via_crosswalk"], h, entry[0], entry[1],
                     bench))
                registered += 1
        bench_entry = entry_for(conn, benchmark, composite_date, max_age_days)
        if bench_entry is None:
            skipped += 1
        else:
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO regime_outcomes"
                    " (composite_snapshot_id, composite_date, regime,"
                    "  horizon, entry_date, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?)",
                    (csid, composite_date, regime, h,
                     bench_entry[0], bench_entry[1]))
                registered += 1
        conn.execute(
            "UPDATE registered_snapshots SET ticker_rows=?, signal_rows=?,"
            " skipped=? WHERE composite_snapshot_id=?",
            (len(ticker_rows), len(signal_rows), skipped, csid))
    return registered, skipped


def registered_ids(conn):
    return {r[0] for r in conn.execute(
        "SELECT composite_snapshot_id FROM registered_snapshots")}


# Maturation: the Nth distinct ledger date after entry, per symbol. The
# correlated OFFSET subquery is the whole trading-day calendar.
_MATURE_SYMBOL = """
UPDATE {table} SET
  exit_date = x.xdate,
  exit_close = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate),
  fwd_return = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate)
               / entry_close - 1,
  bench_fwd_return = CASE WHEN bench_entry_close IS NOT NULL THEN
      (SELECT close FROM prices
       WHERE symbol = :bench AND price_date = x.xdate)
      / bench_entry_close - 1 END,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = t.{sym} AND p.price_date > t.entry_date
              ORDER BY p.price_date LIMIT 1 OFFSET t.horizon - 1) AS xdate
      FROM {table} t WHERE t.exit_date IS NULL) AS x
WHERE {table}.rowid = x.rid AND x.xdate IS NOT NULL
"""

_MATURE_REGIME = """
UPDATE regime_outcomes SET
  exit_date = x.xdate,
  bench_exit_close = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate),
  bench_fwd_return = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate)
                     / bench_entry_close - 1,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = :bench AND p.price_date > t.entry_date
              ORDER BY p.price_date LIMIT 1 OFFSET t.horizon - 1) AS xdate
      FROM regime_outcomes t WHERE t.exit_date IS NULL) AS x
WHERE regime_outcomes.rowid = x.rid AND x.xdate IS NOT NULL
"""


def mature(conn, now_iso, benchmark="SPY") -> int:
    n = 0
    params = {"now": now_iso, "bench": benchmark}
    for table, sym in (("ticker_outcomes", "symbol"),
                       ("signal_outcomes", "entity")):
        cur = conn.execute(_MATURE_SYMBOL.format(table=table, sym=sym),
                           params)
        n += cur.rowcount
    n += conn.execute(_MATURE_REGIME, params).rowcount
    conn.commit()
    return n


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Run headers + old ledger rows only. Outcome tables are the permanent
    experiment record and are NEVER pruned."""
    header_cutoff = (datetime.fromisoformat(now_iso)
                     - timedelta(days=keep_days)).isoformat()
    price_cutoff = (datetime.fromisoformat(now_iso)
                    - timedelta(days=PRICE_KEEP_DAYS)).date().isoformat()
    n = conn.execute("DELETE FROM snapshots WHERE captured_at < ?",
                     (header_cutoff,)).rowcount
    conn.execute("DELETE FROM prices WHERE price_date < ?", (price_cutoff,))
    conn.commit()
    return n
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_write.py tests/test_scorer_db_schema.py -v`
Expected: all pass. The maturation UPDATE ... FROM syntax needs SQLite ≥ 3.33 — Python 3.12 bundles ≥ 3.40; if it errors, check `sqlite3.sqlite_version` before rewriting anything.

- [ ] **Step 5: Full suite, commit**

```bash
git add sources/combiners/scorer/db.py tests/test_scorer_db_write.py
git commit --no-gpg-sign -m "feat(scorer): ledger, atomic registration, ledger-calendar maturation, prune"
```

---

### Task 3: Views (`db.py` part 3)

**Files:**
- Modify: `sources/combiners/scorer/db.py` (extend `_SCHEMA`)
- Test: `tests/test_scorer_db_views.py`

**Interfaces:**
- Produces views: `v_bucket_performance`, `v_signal_efficacy`, `v_regime_performance`, `v_pending`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer_db_views.py
from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"
DAYS = ["2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30",
        "2026-07-01", "2026-07-02", "2026-07-06", "2026-07-07"]


def _seed(tmp_path):
    conn = db.connect(str(tmp_path / "s.db")); db.ensure_schema(conn)
    # WIN rises faster than SPY; LOSE falls; SPY drifts up
    db.insert_prices(conn, [("WIN", d, 100 + 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("LOSE", d, 100 - 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("SPY", d, 500 + i) for i, d in enumerate(DAYS)])
    db.register_snapshot(
        conn, 1, "2026-07-01",
        [dict(symbol="WIN", score_sum=4, total=3, bullish=3, bearish=0,
              in_portfolio=0),
         dict(symbol="LOSE", score_sum=-4, total=3, bullish=0, bearish=3,
              in_portfolio=0),
         dict(symbol="SPY", score_sum=1, total=1, bullish=1, bearish=0,
              in_portfolio=0)],
        [dict(signal_id="si_days_to_cover", entity="WIN", score=2,
              via_crosswalk=0),
         dict(signal_id="sv_ratio_spike", entity="LOSE", score=-2,
              via_crosswalk=0)],
        "risk_on", (2,), "SPY", 7, NOW)
    db.mature(conn, NOW)
    return conn


def test_bucket_performance(tmp_path):
    conn = _seed(tmp_path)
    rows = {r[0]: r for r in conn.execute(
        "SELECT bucket, horizon, n_matured, avg_excess, hit_rate"
        " FROM v_bucket_performance")}
    assert rows["strong_bull"][2] == 1 and rows["strong_bull"][3] > 0
    assert rows["strong_bull"][4] == 1.0        # WIN beat SPY
    assert rows["strong_bear"][2] == 1
    assert rows["strong_bear"][4] == 1.0        # LOSE lagged SPY = bear hit
    assert rows["thin"][2] == 1                 # single-signal SPY row


def test_signal_efficacy_direction_adjusted(tmp_path):
    conn = _seed(tmp_path)
    rows = {r[0]: r for r in conn.execute(
        "SELECT signal_id, n_matured, avg_directional_excess, hit_rate"
        " FROM v_signal_efficacy")}
    # both signals called their direction correctly -> positive adj excess
    assert rows["si_days_to_cover"][2] > 0
    assert rows["sv_ratio_spike"][2] > 0
    assert rows["sv_ratio_spike"][3] == 1.0


def test_regime_and_pending(tmp_path):
    conn = _seed(tmp_path)
    r = conn.execute("SELECT regime, n_matured, avg_bench_return"
                     " FROM v_regime_performance").fetchone()
    assert r[0] == "risk_on" and r[1] == 1 and r[2] > 0
    # register something unmaturable -> shows in v_pending
    db.register_snapshot(conn, 2, "2026-07-07", [], [], "mixed", (21,),
                         "SPY", 7, NOW)
    assert conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_db_views.py -v`
Expected: FAIL with `no such table: v_bucket_performance`

- [ ] **Step 3: Append to `_SCHEMA` (after the tables)**

```sql
-- Bucketing lives in views (ELT): stored rows keep raw score_sum/total.
-- Buckets: strong_bull >= +4, bull +2..+3, neutral -1..+1, bear -3..-2,
-- strong_bear <= -4; rows with total < 2 bucket as 'thin' regardless.
-- hit = excess in the score's direction (bull: excess > 0; bear: < 0).
CREATE VIEW IF NOT EXISTS v_bucket_performance AS
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

-- Per-signal grade, direction-adjusted: excess * sign(score). Crosswalked
-- evidence is split out so mapped scores are graded separately.
CREATE VIEW IF NOT EXISTS v_signal_efficacy AS
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

CREATE VIEW IF NOT EXISTS v_regime_performance AS
SELECT regime, horizon, COUNT(*) AS n_matured,
       AVG(bench_fwd_return) AS avg_bench_return,
       MIN(bench_fwd_return) AS min_bench_return,
       MAX(bench_fwd_return) AS max_bench_return
FROM regime_outcomes WHERE matured_at IS NOT NULL
GROUP BY regime, horizon;

-- Registered but not yet matured: what's cooking and roughly when.
CREATE VIEW IF NOT EXISTS v_pending AS
SELECT 'ticker' AS kind, composite_date, symbol AS entity, horizon,
       entry_date FROM ticker_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'signal', composite_date, signal_id || ':' || entity, horizon,
       entry_date FROM signal_outcomes WHERE matured_at IS NULL
UNION ALL
SELECT 'regime', composite_date, COALESCE(regime, '?'), horizon,
       entry_date FROM regime_outcomes WHERE matured_at IS NULL;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_db_views.py -v`
Expected: 3 passed

- [ ] **Step 5: Full suite, commit**

```bash
git add sources/combiners/scorer/db.py tests/test_scorer_db_views.py
git commit --no-gpg-sign -m "feat(scorer): bucket/signal/regime efficacy views + pending"
```

---

### Task 4: Extraction (`fetch.py`)

**Files:**
- Create: `sources/combiners/scorer/fetch.py`
- Test: `tests/test_scorer_fetch.py`

**Interfaces:**
- Consumes: attached read-only sources (aliased `src`).
- Produces:
  - `attach_ro(conn, db_path, alias="src")` / `detach(conn, alias="src")` — same semantics as composite's fetch (FileNotFoundError on missing path; `mode=ro` URI)
  - `harvest_prices(conn) -> list[(symbol, price_date, close)]` — from `src.metrics` across ALL retained snapshots (`SELECT DISTINCT symbol, priceDate, close FROM src.metrics WHERE priceDate IS NOT NULL AND close IS NOT NULL`) — all-snapshot harvest backfills ledger gaps every night
  - `read_snapshots(conn) -> list[(id, composite_date)]` — composite snapshots HAVING a market_regime row (phase-2-failed snapshots are not opinions), date = `substr(captured_at, 1, 10)`
  - `read_ticker_scores(conn, csid) -> list[dict]` (symbol, score_sum, total, bullish, bearish, in_portfolio)
  - `read_signal_rows(conn, csid) -> list[dict]` (signal_id, entity, score, via_crosswalk) — ticker-grain only, **score != 0 only**
  - `read_regime(conn, csid) -> str | None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer_fetch.py
import sqlite3

import pytest

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import fetch
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-06T21:05:00+00:00"
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL"}


def _mini_stocks(tmp_path):
    path = tmp_path / "stocks.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute("INSERT INTO snapshots (captured_at, universe_count,"
                 " source) VALUES (?, 2, 's')", (NOW,))
    conn.executemany(
        'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close")'
        " VALUES (1, ?, ?, ?)",
        [("AAPL", "2026-07-02", 200.0), ("XOM", "2026-07-02", 100.0),
         ("NULLED", None, None)])
    conn.commit(); conn.close()
    return str(path)


def _mini_composite(tmp_path):
    path = tmp_path / "composite.db"
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, NOW, 2)
    composite_db.write_signal_values(conn, sid, [
        dict(signal_id="si_days_to_cover", grain="ticker", entity="AAPL",
             raw_value=12.0, score=2, obs_date="2026-06-15",
             staleness_days=21.0),
        dict(signal_id="portfolio_holding", grain="ticker", entity="XOM",
             raw_value=10.0, score=0, obs_date="2026-07-06",
             staleness_days=0.0),
        dict(signal_id="fred_curve", grain="market", entity="*",
             raw_value=0.35, score=0, obs_date="2026-07-02",
             staleness_days=4.0)])
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    # a phase-2-failed snapshot: header but no regime row
    composite_db.write_snapshot(conn, "2026-07-07T21:05:00+00:00", 2)
    conn.commit(); conn.close()
    return str(path), sid


def test_harvest_prices_skips_nulls(tmp_path):
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, _mini_stocks(tmp_path))
    rows = sorted(fetch.harvest_prices(conn))
    assert rows == [("AAPL", "2026-07-02", 200.0),
                    ("XOM", "2026-07-02", 100.0)]


def test_reads_composite_only_regimed_snapshots(tmp_path):
    path, sid = _mini_composite(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    assert fetch.read_snapshots(conn) == [(sid, "2026-07-06")]
    tickers = fetch.read_ticker_scores(conn, sid)
    assert {t["symbol"] for t in tickers} == {"AAPL", "XOM"}
    sigs = fetch.read_signal_rows(conn, sid)
    assert [s["signal_id"] for s in sigs] == ["si_days_to_cover"]  # no score-0
    assert fetch.read_regime(conn, sid) == "mixed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError` on scorer fetch. (Fixture columns `universe_count`/`source` were verified against `stock_analysis_screener/db.py` at plan time.)

- [ ] **Step 3: Write the implementation**

```python
# sources/combiners/scorer/fetch.py
"""Read-only extraction from stocks/etfs (prices) and composite (scores).
No network anywhere in this package."""
import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}",
                 (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots —
    INSERT OR IGNORE downstream dedupes, and re-harvesting nightly
    self-heals ledger gaps within the source's retention window."""
    return conn.execute(
        'SELECT DISTINCT symbol, "priceDate", "close" FROM src.metrics'
        ' WHERE "priceDate" IS NOT NULL AND "close" IS NOT NULL').fetchall()


def read_snapshots(conn) -> list:
    """Composite snapshots that state an opinion (have a regime row)."""
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT s.id, substr(s.captured_at, 1, 10) FROM src.snapshots s"
        " JOIN src.market_regime m ON m.snapshot_id = s.id"
        " ORDER BY s.id")]


def read_ticker_scores(conn, csid) -> list:
    return [dict(symbol=r[0], score_sum=r[1], total=r[2], bullish=r[3],
                 bearish=r[4], in_portfolio=r[5])
            for r in conn.execute(
                "SELECT symbol, score_sum, total, bullish, bearish,"
                " in_portfolio FROM src.ticker_scores"
                " WHERE snapshot_id = ?", (csid,))]


def read_signal_rows(conn, csid) -> list:
    """Ticker-grain, direction-bearing rows only (score 0 has no direction
    to grade — portfolio_holding / edgar_insider are informational)."""
    return [dict(signal_id=r[0], entity=r[1], score=r[2], via_crosswalk=r[3])
            for r in conn.execute(
                "SELECT signal_id, entity, score, via_crosswalk"
                " FROM src.signal_values WHERE snapshot_id = ?"
                " AND grain = 'ticker' AND score != 0", (csid,))]


def read_regime(conn, csid):
    row = conn.execute("SELECT regime FROM src.market_regime"
                       " WHERE snapshot_id = ?", (csid,)).fetchone()
    return row[0] if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_fetch.py -v`
Expected: 2 passed

- [ ] **Step 5: Full suite, commit**

```bash
git add sources/combiners/scorer/fetch.py tests/test_scorer_fetch.py
git commit --no-gpg-sign -m "feat(scorer): read-only price harvest + composite readers"
```

---

### Task 5: Orchestration (`run.py`)

**Files:**
- Create: `sources/combiners/scorer/run.py`
- Test: `tests/test_scorer_run.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `run(db_path, db_dir, now_iso=None, keep_days=None) -> (sid, harvested, registered, matured, skipped)`; `main(argv)` with `--db` (default `scorer.db`), `--db-dir` (default `data`), `--keep-days`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer_run.py
import sqlite3

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import run as run_mod
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-06T21:10:00+00:00"
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL"}
DAYS = ["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-06"]


def _mini_prices(path, symbols_start):
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    for i, d in enumerate(DAYS):
        conn.execute("INSERT INTO snapshots (captured_at, universe_count,"
                     " source) VALUES (?, 1, 's')", (f"{d}T11:00:00+00:00",))
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for sym, start in symbols_start.items():
            conn.execute('INSERT INTO metrics (snapshot_id, symbol,'
                         ' "priceDate", "close") VALUES (?, ?, ?, ?)',
                         (sid, sym, d, start + i))
    conn.commit(); conn.close()


def _mini_composite(dirpath, date="2026-07-01"):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, f"{date}T21:05:00+00:00", 1)
    composite_db.write_signal_values(conn, sid, [
        dict(signal_id="stocks_rsi", grain="ticker", entity="AAPL",
             raw_value=25.0, score=1, obs_date=date, staleness_days=0.0)])
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit(); conn.close()


def test_full_cycle(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    out = str(tmp_path / "scorer.db")
    sid, harvested, registered, matured, skipped = run_mod.run(
        out, str(tmp_path), now_iso=NOW)
    assert harvested == 10          # 5 dates x 2 symbols
    assert registered > 0 and skipped == 0
    conn = sqlite3.connect(out)
    # entry 07-01 (close 102); +5/+10/+21 pending (only 2 fwd days), so
    # nothing matured yet
    assert matured == 0
    assert conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0] > 0
    # header records honest counts
    assert conn.execute("SELECT harvested, registered FROM snapshots"
                        ).fetchone() == (10, registered)


def test_rerun_is_idempotent(tmp_path):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    out = str(tmp_path / "scorer.db")
    run_mod.run(out, str(tmp_path), now_iso=NOW)
    sid2, harvested2, registered2, matured2, skipped2 = run_mod.run(
        out, str(tmp_path), now_iso=NOW)
    assert (harvested2, registered2) == (0, 0)   # nothing new
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM registered_snapshots"
                        ).fetchone()[0] == 1


def test_missing_source_skip_and_continue(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    # no etfs.db, no composite.db
    out = str(tmp_path / "scorer.db")
    sid, harvested, registered, matured, skipped = run_mod.run(
        out, str(tmp_path), now_iso=NOW)
    assert harvested == 5 and registered == 0
    err = capsys.readouterr().out
    # two missing sources -> two skip lines, type names only, no traceback
    assert err.count("FileNotFoundError") == 2
    assert "Traceback" not in err


def test_main_argv(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    run_mod.main(["--db", str(tmp_path / "scorer.db"),
                  "--db-dir", str(tmp_path)])
    assert "scorer snapshot" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_scorer_run.py -v`
Expected: FAIL with `ModuleNotFoundError` on scorer run

- [ ] **Step 3: Write the implementation**

```python
# sources/combiners/scorer/run.py
"""Nightly grade of composite opinions: harvest -> register -> mature.
Every step idempotent; missed nights self-heal. Sources attached read-only
one at a time. The scorer never writes anything back into the composite."""
import argparse
import os
from datetime import datetime, timezone

from sources.combiners.scorer import catalog, db, fetch


def run(db_path, db_dir, now_iso=None, keep_days=None):
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso)
        harvested = registered = matured = skipped = 0
        # 1) harvest
        for src_db in catalog.PRICE_DBS:
            path = os.path.join(db_dir, src_db)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                print(f"skip {src_db}: {type(e).__name__}")
                continue
            try:
                harvested += db.insert_prices(conn, fetch.harvest_prices(conn))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"skip {src_db}: {type(e).__name__}")
            finally:
                fetch.detach(conn)
        # 2) register
        path = os.path.join(db_dir, catalog.COMPOSITE_DB)
        try:
            fetch.attach_ro(conn, path)
        except Exception as e:
            print(f"skip {catalog.COMPOSITE_DB}: {type(e).__name__}")
        else:
            try:
                done = db.registered_ids(conn)
                for csid, cdate in fetch.read_snapshots(conn):
                    if csid in done:
                        continue
                    reg, skip = db.register_snapshot(
                        conn, csid, cdate,
                        fetch.read_ticker_scores(conn, csid),
                        fetch.read_signal_rows(conn, csid),
                        fetch.read_regime(conn, csid),
                        catalog.HORIZONS, catalog.BENCHMARK,
                        catalog.ENTRY_MAX_AGE_DAYS, now_iso)
                    registered += reg
                    skipped += skip
            except Exception as e:
                conn.rollback()
                print(f"skip registration: {type(e).__name__}")
            finally:
                fetch.detach(conn)
        # 3) mature (local only)
        matured = db.mature(conn, now_iso, catalog.BENCHMARK)
        db.finish_snapshot(conn, sid, harvested, registered, matured, skipped)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, harvested, registered, matured, skipped


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="scorer",
        description="Grade composite opinions against forward returns"
                    " (reads composite/stocks/etfs read-only)")
    p.add_argument("--db", default="scorer.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, harvested, registered, matured, skipped = run(
        a.db, a.db_dir, keep_days=a.keep_days)
    print(f"scorer snapshot {sid}: {harvested} prices, {registered}"
          f" registered, {matured} matured, {skipped} skipped, into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_scorer_run.py -v`
Expected: 4 passed

- [ ] **Step 5: Full suite, commit**

```bash
git add sources/combiners/scorer/run.py tests/test_scorer_run.py
git commit --no-gpg-sign -m "feat(scorer): harvest/register/mature orchestration"
```

---

### Task 6: Registry

**Files:**
- Modify: `registry.py`, `tests/test_registry.py` (append)

**Interfaces:**
- Produces: `main.py scorer [args...]`.

- [ ] **Step 1: Failing test (append):**

```python
def test_dispatch_lists_scorer():
    import registry
    assert "scorer" in registry.REGISTRY
```

- [ ] **Step 2:** Run `uv run pytest tests/test_registry.py::test_dispatch_lists_scorer -v` → FAIL (AssertionError)

- [ ] **Step 3:** In `registry.py`: `from sources.combiners.scorer.run import main as scorer_main` (after the composite import) and `"scorer": scorer_main,` as the last REGISTRY entry (after `"composite"`).

- [ ] **Step 4:** `uv run pytest tests/test_registry.py -v` → all pass.

- [ ] **Step 5:**

```bash
git add registry.py tests/test_registry.py
git commit --no-gpg-sign -m "feat(scorer): register scorer dispatcher"
```

---

### Task 7: Smoke run, launchd slot, docs

**Files:**
- Modify: `deploy/launchd/install.py`, `docs/SCHEDULE.md`, `CLAUDE.md`

- [ ] **Step 1: Smoke run against real data/**

```bash
uv run python main.py scorer --db data/scorer.db --keep-days 365
sqlite3 data/scorer.db "SELECT * FROM snapshots"
sqlite3 data/scorer.db "SELECT COUNT(*), MIN(price_date), MAX(price_date) FROM prices"
sqlite3 data/scorer.db "SELECT kind, horizon, COUNT(*) FROM v_pending GROUP BY kind, horizon"
sqlite3 data/scorer.db "SELECT COUNT(*) FROM registered_snapshots"
```

Expected: harvested in the thousands (full stocks+etfs universes across their retained snapshots); every composite snapshot with a regime row registered; `matured = 0` (no horizon can mature yet — the ledger only has a few days of history); `v_pending` populated across kinds and horizons; skipped counts small and explainable (symbols without price rows). ANY unexplained skip explosion or a source error other than a known-absent DB: stop and investigate. NEVER write to other data/*.db files.

- [ ] **Step 2: launchd slot**

In `deploy/launchd/install.py` JOBS, directly after the `"composite"` entry:

```python
    "scorer": (job("scorer", "--keep-days", "365"),
               weekly(range(7), 21, 10)),
```

Then `uv run python deploy/launchd/install.py` and verify `launchctl list | grep com.tradingbot.scorer` shows the label (29 agents total).

- [ ] **Step 3: Docs**

`docs/SCHEDULE.md`: agent count 28 → 29; new row after composite's — `| scorer | every day 9:10pm | Grades composite opinions: harvests closes into data/scorer.db, registers pending outcomes, matures forward returns. Must stay after composite 9:05pm. Outcome tables are permanent (never pruned) |`.
`CLAUDE.md`: in the file tree, `combiners/` comment becomes `# 2 cross-source combiners (composite: opinions; scorer: grades them)`; add one sentence to the combiners paragraph: the scorer grades composite opinions against forward returns and never feeds back — re-weighting the catalog is a human decision made by reading `v_signal_efficacy`/`v_bucket_performance`.

- [ ] **Step 4:** `uv run pytest -q` → green.

- [ ] **Step 5:**

```bash
git add deploy/launchd/install.py docs/SCHEDULE.md CLAUDE.md
git commit --no-gpg-sign -m "feat(scorer): nightly 9:10pm launchd slot + schedule/architecture docs"
```
