# Sizing / Risk Advisor Combiner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A third combiner (`advisor`) that joins the composite scorecard against real holdings: whole-book ATR heat, holdings the composite disagrees with, and vol-scaled size caps for flagged tickers — written to `data/advisor.db`.

**Architecture:** Standard four-file combiner package (`sources/combiners/advisor/`) modeled on `sources/combiners/scorer/`. `fetch.py` has no network — it ATTACHes composite.db / portfolio.db / stocks.db / etfs.db / scorer.db read-only, one at a time. Heat and cap math are pure Python builders in `db.py`; storage is snapshot-scoped with `v_latest_*` views. Spec: `docs/superpowers/specs/2026-07-07-sizing-risk-advisor-design.md`.

**Tech Stack:** Python 3.12 stdlib only (`sqlite3`, `argparse`, `datetime`, `os`). Dev tooling: `uv`, `pytest`, `ruff`, `mypy`.

## Global Constraints

- **Zero runtime third-party dependencies** — stdlib only, no `uv add`.
- **No network in tests** — all fixtures are local SQLite files in `tmp_path`.
- **No wall-clock in the hot path** — time enters as injected `now_iso` (UTC `isoformat()`); the advisor binds its own `today = now_iso[:10]` and never reads any `calendar_now`-dependent view (one-clock rule).
- **Secret hygiene on per-item failure** — `conn.rollback()` then print only `type(e).__name__`; never `str(e)` / `repr(e)`.
- **Fixed-width timestamps** — every stored timestamp is a UTC `isoformat()` string (prune compares lexicographically).
- **Never write SQL against portfolio.db** — read its `v_latest_*` views only. Combiners never write back into any DB they read.
- **Read-only attaches** — `ATTACH DATABASE 'file:<path>?mode=ro'` on a connection opened with `uri=True`, one source at a time.
- **Every commit must pass the pre-commit hook** (`ruff check`, `ruff format --check`, `mypy`, `pytest` — runs automatically on `git commit`).
- **Run `uv run ruff format` (in place) after writing code, before every commit** — the plan's code blocks are semantically exact but not always formatter-canonical; the reformat is mechanical and required to pass the hook's `ruff format --check`.
- **Commit flags** — use `--no-gpg-sign` (signing hangs non-interactive sessions). Do NOT add a co-author line.
- Match house code style: minimal type annotations (annotate like `def prune(conn, keep_days: int, now_iso: str) -> int`), module docstrings stating invariants, ≤ 99-char lines.

---

### Task 1: Advisor catalog (constants + ticker groups)

**Files:**
- Create: `sources/combiners/advisor/__init__.py` (empty)
- Create: `sources/combiners/advisor/catalog.py`
- Test: `tests/test_advisor_catalog.py`

**Interfaces:**
- Consumes: `sources.combiners.composite.catalog.CROSSWALK` (dict `group -> [tickers]`).
- Produces: `RISK_BUDGET: float`, `ATR_MAX_AGE_DAYS: int`, `COMPOSITE_DB`, `PORTFOLIO_DB`, `SCORER_DB`, `PRICE_DBS: tuple`, `TICKER_GROUP: dict[str, str]` — all imported by Tasks 3 and 6 as `catalog.<NAME>`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_advisor_catalog.py`:

```python
from sources.combiners.advisor import catalog
from sources.combiners.composite.catalog import CROSSWALK


def test_risk_budget_default():
    # 1% of equity per position per 1-ATR adverse day (user-set 2026-07-07).
    assert catalog.RISK_BUDGET == 0.01


def test_ticker_group_covers_every_crosswalk_ticker():
    for _group, syms in CROSSWALK.items():  # _group: ruff B007 (unused)
        for sym in syms:
            assert catalog.TICKER_GROUP[sym] in CROSSWALK


def test_ticker_group_first_group_wins():
    # DBA appears under both ags and softs; first (ags) wins so DBA shares
    # a bet with CORN/SOYB/WEAT rather than being its own group.
    assert catalog.TICKER_GROUP["DBA"] == "ags"


def test_price_db_order_stocks_first():
    # stocks.db is attached first and wins symbol collisions.
    assert catalog.PRICE_DBS == ("stocks.db", "etfs.db")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_advisor_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.combiners.advisor'`

- [ ] **Step 3: Write minimal implementation**

Create empty `sources/combiners/advisor/__init__.py`, then `sources/combiners/advisor/catalog.py`:

```python
"""Advisor configuration. The advisor joins the composite scorecard against
real holdings; decision support only — it never places or sizes orders, and
it never writes back into anything it reads."""

from sources.combiners.composite.catalog import CROSSWALK

# Fraction of account equity a single position may put at risk per one-ATR
# adverse day (user-chosen default, 2026-07-07). Caps invert this:
# cap_shares = floor(max(0, RISK_BUDGET*equity - existing_group_heat) / ATR).
RISK_BUDGET = 0.01

# priceDate older than this many days vs the run's :today -> atr_stale = 1
# (5 covers a weekend plus a holiday).
ATR_MAX_AGE_DAYS = 5

COMPOSITE_DB = "composite.db"
PORTFOLIO_DB = "portfolio.db"
SCORER_DB = "scorer.db"
PRICE_DBS = ("stocks.db", "etfs.db")  # stocks first: it wins symbol collisions

# symbol -> crosswalk group, derived from composite's CROSSWALK at import
# time (a catalog test pins consistency). First group wins: DBA sits under
# both ags and softs, and grouping it with CORN/SOYB/WEAT (ags) keeps one
# bet per underlying exposure. Ungrouped symbols resolve to None downstream
# and count as their own single-member bet.
TICKER_GROUP: dict[str, str] = {}
for _group, _symbols in CROSSWALK.items():
    for _symbol in _symbols:
        TICKER_GROUP.setdefault(_symbol, _group)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_advisor_catalog.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/advisor/__init__.py sources/combiners/advisor/catalog.py tests/test_advisor_catalog.py
git commit --no-gpg-sign -m "feat(advisor): catalog — risk budget, ticker groups from CROSSWALK"
```

---

### Task 2: advisor.db schema, views, prune

**Files:**
- Create: `sources/combiners/advisor/db.py`
- Test: `tests/test_advisor_db_schema.py`

**Interfaces:**
- Produces: `connect(path) -> sqlite3.Connection` (WAL + `uri=True`), `ensure_schema(conn)`, `prune(conn, keep_days: int, now_iso: str) -> int`, module constants `STRONG_MIN_ABS_SCORE = 4`, `STRONG_MIN_TOTAL = 3`. Tables `snapshots`, `position_heat`, `size_caps`; views `v_latest_snapshot`, `v_latest_heat`, `v_book_heat`, `v_group_heat`, `v_disagreements`, `v_latest_caps`. Tasks 3–6 build on these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_advisor_db_schema.py`:

```python
from sources.combiners.advisor import db


def test_schema_idempotent(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # re-running must not error (views DROP+CREATE)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "position_heat", "size_caps"} <= tables
    views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {
        "v_latest_snapshot",
        "v_latest_heat",
        "v_book_heat",
        "v_group_heat",
        "v_disagreements",
        "v_latest_caps",
    } <= views


def test_wal_mode(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_strong_thresholds_pinned_to_composite_flag_view():
    # v_disagreements' `strong` must drift together with composite v_flagged
    # (same pin trick as scorer's FLAG_MIN_* constants).
    from sources.combiners.composite.db import _SCHEMA

    assert f"ABS(score_sum) >= {db.STRONG_MIN_ABS_SCORE}" in _SCHEMA
    assert f"total >= {db.STRONG_MIN_TOTAL}" in _SCHEMA


def test_prune_cascades_children(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (id, captured_at) VALUES (1, '2026-01-01T00:00:00+00:00')")
    conn.execute("INSERT INTO snapshots (id, captured_at) VALUES (2, '2026-07-07T00:00:00+00:00')")
    conn.execute(
        "INSERT INTO position_heat (snapshot_id, symbol, quantity) VALUES (1, 'AAPL', 1.0)"
    )
    conn.execute("INSERT INTO size_caps (snapshot_id, symbol) VALUES (1, 'NVDA')")
    conn.commit()
    assert db.prune(conn, keep_days=30, now_iso="2026-07-07T21:12:00+00:00") == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_heat").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM size_caps").fetchone()[0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_advisor_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError` (no `sources.combiners.advisor.db`)

- [ ] **Step 3: Write minimal implementation**

Create `sources/combiners/advisor/db.py`:

```python
"""advisor.db: snapshot-scoped sizing/risk advice — per-position ATR heat,
composite disagreements, and vol-scaled size caps. Everything cascades on
prune; the permanent record lives upstream (scorer.db), not here.

Heat/cap math is pure Python (build_* helpers) because it joins data already
fetched from four source DBs; views only scope and aggregate."""

import sqlite3
from datetime import datetime, timedelta

# Strong-disagreement thresholds, mirroring composite v_flagged
# (|score_sum| >= 4 AND total >= 3). A schema test pins these to
# composite.db's view text so the two drift together.
STRONG_MIN_ABS_SCORE = 4
STRONG_MIN_TOTAL = 3

_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at           TEXT NOT NULL,
    equity                REAL,
    cash                  REAL,
    buying_power          REAL,
    portfolio_captured_at TEXT,
    composite_captured_at TEXT,
    regime                TEXT,
    sources_failed        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS position_heat (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    group_name   TEXT,
    quantity     REAL NOT NULL,
    market_value REAL,
    atr          REAL,
    price        REAL,
    price_date   TEXT,
    heat_dollars REAL,
    heat_pct     REAL,
    weight_pct   REAL,
    score_sum    INTEGER,
    bullish      INTEGER,
    bearish      INTEGER,
    total        INTEGER,
    atr_stale    INTEGER,
    PRIMARY KEY (snapshot_id, symbol)
);

CREATE TABLE IF NOT EXISTS size_caps (
    snapshot_id          INTEGER NOT NULL REFERENCES snapshots(id),
    symbol               TEXT NOT NULL,
    direction            TEXT CHECK (direction IN ('bullish', 'bearish')),
    score_sum            INTEGER,
    atr                  REAL,
    price                REAL,
    cap_shares           REAL,
    cap_dollars          REAL,
    group_name           TEXT,
    group_heat_pct       REAL,
    reliable_signals     INTEGER,
    total_signals        INTEGER,
    exceeds_buying_power INTEGER NOT NULL DEFAULT 0,
    already_held         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, symbol)
);
"""

# Views are DROP+CREATEd every run (scorer pattern) so edits deploy nightly.
_VIEWS = f"""
DROP VIEW IF EXISTS v_latest_snapshot;
CREATE VIEW v_latest_snapshot AS
SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1;

DROP VIEW IF EXISTS v_latest_heat;
CREATE VIEW v_latest_heat AS
SELECT p.* FROM position_heat p
JOIN v_latest_snapshot l ON p.snapshot_id = l.id;

-- One row of book totals. heat_coverage = share of book market value with
-- a usable ATR, so missing metrics can never silently understate heat.
-- LEFT JOIN so an empty book still yields a row (0 positions, NULL heat).
-- sources_failed rides along: 0 positions is only believable when 0 failed.
DROP VIEW IF EXISTS v_book_heat;
CREATE VIEW v_book_heat AS
SELECT s.id AS snapshot_id, s.captured_at, s.equity, s.sources_failed,
       COUNT(p.symbol) AS positions,
       SUM(p.heat_dollars) AS heat_dollars,
       SUM(p.heat_pct) AS heat_pct,
       CASE WHEN SUM(p.market_value) > 0 THEN
            SUM(CASE WHEN p.atr IS NOT NULL THEN p.market_value ELSE 0 END)
            * 1.0 / SUM(p.market_value) END AS heat_coverage
FROM snapshots s LEFT JOIN position_heat p ON p.snapshot_id = s.id
WHERE s.id IN (SELECT id FROM v_latest_snapshot)
GROUP BY s.id, s.captured_at, s.equity, s.sources_failed;

-- CROSSWALK groups collapsed to one bet; ungrouped symbols are their own
-- single-member bet (exposure adds within a group).
DROP VIEW IF EXISTS v_group_heat;
CREATE VIEW v_group_heat AS
SELECT snapshot_id,
       COALESCE(group_name, symbol) AS bet,
       group_name,
       COUNT(*) AS members,
       GROUP_CONCAT(symbol) AS symbols,
       SUM(heat_dollars) AS heat_dollars,
       SUM(heat_pct) AS heat_pct
FROM v_latest_heat
GROUP BY snapshot_id, COALESCE(group_name, symbol);

-- Holdings today's composite scores negative (long book: bearish evidence
-- against something held). strong mirrors composite v_flagged thresholds.
DROP VIEW IF EXISTS v_disagreements;
CREATE VIEW v_disagreements AS
SELECT *, (score_sum <= -{STRONG_MIN_ABS_SCORE} AND total >= {STRONG_MIN_TOTAL}) AS strong
FROM v_latest_heat
WHERE score_sum < 0;

DROP VIEW IF EXISTS v_latest_caps;
CREATE VIEW v_latest_caps AS
SELECT c.* FROM size_caps c
JOIN v_latest_snapshot l ON c.snapshot_id = l.id;
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Tables (CREATE IF NOT EXISTS), then views (DROP+CREATE)."""
    conn.executescript(_TABLES)
    conn.executescript(_VIEWS)
    conn.commit()


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Cascade position_heat + size_caps then snapshot headers (fully
    snapshot-scoped, same pattern as portfolio.db)."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [
        r[0]
        for r in conn.execute("SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,))
    ]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("position_heat", "size_caps"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_advisor_db_schema.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/advisor/db.py tests/test_advisor_db_schema.py
git commit --no-gpg-sign -m "feat(advisor): advisor.db schema, latest-scoped views, snapshot prune"
```

---

### Task 3: Pure heat/cap builders + writers

**Files:**
- Modify: `sources/combiners/advisor/db.py` (append after `prune`)
- Test: `tests/test_advisor_db_write.py`

**Interfaces:**
- Consumes: Task 2's schema; `catalog.TICKER_GROUP` / `catalog.RISK_BUDGET` shapes.
- Produces (Task 6 calls all of these):
  - `write_snapshot(conn, now_iso: str) -> int`
  - `finish_snapshot(conn, sid, account, composite, sources_failed=0) -> None` — `account` is `{"equity","cash","buying_power","captured_at"}` or None; `composite` is `{"snapshot_id","captured_at","regime"}` or None; `sources_failed` is the count of upstream DBs that could not be read this run.
  - `build_position_heat(positions, scorecard, metrics, equity, today, ticker_group, atr_max_age_days) -> list[dict]` — `positions` = `[{"symbol","quantity","market_value"}]`; `scorecard` = `{symbol: {"score_sum","bullish","bearish","total"}}`; `metrics` = `{symbol: {"atr","close","price_date"}}`.
  - `build_size_caps(flagged, scorecard, metrics, heat_rows, equity, buying_power, risk_budget, ticker_group, flag_signals, reliable_ids) -> list[dict]` — `flagged` = `[symbol]`; `heat_rows` = output of `build_position_heat`; `flag_signals` = `{symbol: set((signal_id, via_crosswalk))}`; `reliable_ids` = `set((signal_id, via_crosswalk))` — pair keys throughout, never bare signal ids.
  - `write_position_heat(conn, sid, rows) -> int`, `write_size_caps(conn, sid, rows) -> int`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_advisor_db_write.py`:

```python
from sources.combiners.advisor import db

TODAY = "2026-07-07"


def _pos(symbol, quantity, market_value):
    return {"symbol": symbol, "quantity": quantity, "market_value": market_value}


def _metric(atr, close, price_date=TODAY):
    return {"atr": atr, "close": close, "price_date": price_date}


def _score(score_sum, total=3, bullish=None, bearish=None):
    if bullish is None:
        bullish = total if score_sum > 0 else 0
    if bearish is None:
        bearish = total if score_sum < 0 else 0
    return {"score_sum": score_sum, "bullish": bullish, "bearish": bearish, "total": total}


GROUPS = {"XLE": "energy", "XOM": "energy"}


def test_position_heat_computes_heat_and_weight():
    rows = db.build_position_heat(
        [_pos("AAPL", 10.0, 1000.0)],
        {"AAPL": _score(-1, total=1)},
        {"AAPL": _metric(atr=2.0, close=100.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    (r,) = rows
    assert r["heat_dollars"] == 20.0  # 10 shares x 2.0 ATR
    assert r["heat_pct"] == 0.002  # 20 / 10000
    assert r["weight_pct"] == 0.1
    assert r["group_name"] is None  # AAPL is not crosswalked
    assert r["score_sum"] == -1 and r["atr_stale"] == 0


def test_position_heat_missing_atr_is_null_not_skipped():
    rows = db.build_position_heat(
        [_pos("OBSCURE", 5.0, 500.0)],
        {},
        {},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    (r,) = rows
    assert r["heat_dollars"] is None and r["heat_pct"] is None
    assert r["atr_stale"] is None and r["score_sum"] is None
    assert r["weight_pct"] == 0.05  # weight still computable


def test_position_heat_stale_atr_flagged():
    rows = db.build_position_heat(
        [_pos("AAPL", 1.0, 100.0)],
        {},
        {"AAPL": _metric(atr=2.0, close=100.0, price_date="2026-06-20")},
        equity=10000.0,
        today=TODAY,  # 17 days later > 5
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    assert rows[0]["atr_stale"] == 1


def test_size_cap_inverts_risk_budget():
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=[],
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={"NVDA": {("sig_a", 0), ("sig_b", 0), ("sig_c", 0)}},
        reliable_ids={("sig_a", 0)},
    )
    (c,) = caps
    assert c["cap_shares"] == 25.0  # 0.01*10000 / 4.0 (fractional, no floor)
    assert c["cap_dollars"] == 2500.0
    assert c["direction"] == "bullish"
    assert c["exceeds_buying_power"] == 1  # 2500 > 1000
    assert c["already_held"] == 0
    assert (c["reliable_signals"], c["total_signals"]) == (1, 3)


def test_size_cap_is_fractional_on_small_accounts():
    # $200 account: budget $2, ATR 4.0 -> 0.5 shares. Flooring to int would
    # zero every cap the advisor ever emits at this equity.
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=[],
        equity=200.0,
        buying_power=500.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["cap_shares"] == 0.5
    assert c["cap_dollars"] == 50.0


def test_bearish_flag_never_gets_a_buy_cap():
    # Long-only book: a bearish flag's row IS the advice; caps stay NULL
    # even with ATR and equity known — a buy size on an avoid signal is
    # wrong advice.
    caps = db.build_size_caps(
        ["SHORTY"],
        {"SHORTY": _score(-4)},
        {"SHORTY": _metric(atr=2.0, close=50.0)},
        heat_rows=[],
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["direction"] == "bearish"
    assert c["cap_shares"] is None and c["cap_dollars"] is None
    assert c["exceeds_buying_power"] == 0


def test_size_cap_shrinks_by_existing_group_heat():
    heat_rows = db.build_position_heat(
        [_pos("XOM", 5.0, 400.0)],
        {},
        {"XOM": _metric(atr=4.0, close=80.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    caps = db.build_size_caps(
        ["XLE"],
        {"XLE": _score(4)},
        {"XLE": _metric(atr=2.0, close=50.0)},
        heat_rows=heat_rows,
        equity=10000.0,
        buying_power=99999.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    # budget 100 - existing energy heat 20 (XOM 5x4) = 80 -> 80/2 = 40.0
    assert c["cap_shares"] == 40.0
    assert c["group_name"] == "energy"
    assert c["group_heat_pct"] == 0.002


def test_size_cap_missing_atr_is_null_row():
    # Bullish so this exercises the missing-ATR path, not the bearish one.
    caps = db.build_size_caps(
        ["MYSTERY"],
        {"MYSTERY": _score(4)},
        {},
        heat_rows=[],
        equity=10000.0,
        buying_power=None,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["cap_shares"] is None and c["cap_dollars"] is None
    assert c["direction"] == "bullish"
    assert c["exceeds_buying_power"] == 0


def test_writers_roundtrip_and_header_finish(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    sid = db.write_snapshot(conn, "2026-07-07T21:12:00+00:00")
    heat = db.build_position_heat(
        [_pos("AAPL", 10.0, 1000.0)],
        {"AAPL": _score(1, total=1)},
        {"AAPL": _metric(atr=2.0, close=100.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=heat,
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    assert db.write_position_heat(conn, sid, heat) == 1
    assert db.write_size_caps(conn, sid, caps) == 1
    db.finish_snapshot(
        conn,
        sid,
        {"equity": 10000.0, "cash": 2000.0, "buying_power": 1000.0,
         "captured_at": "2026-07-07T14:30:00+00:00"},
        {"snapshot_id": 9, "captured_at": "2026-07-06T21:05:00+00:00", "regime": "risk_on"},
    )
    conn.commit()
    row = conn.execute(
        "SELECT equity, buying_power, portfolio_captured_at, composite_captured_at, regime"
        " FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    assert row == (
        10000.0,
        1000.0,
        "2026-07-07T14:30:00+00:00",
        "2026-07-06T21:05:00+00:00",
        "risk_on",
    )


def test_finish_snapshot_tolerates_missing_upstream(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    sid = db.write_snapshot(conn, "2026-07-07T21:12:00+00:00")
    db.finish_snapshot(conn, sid, None, None, sources_failed=3)
    conn.commit()
    assert conn.execute(
        "SELECT equity, regime, sources_failed FROM snapshots WHERE id=?", (sid,)
    ).fetchone() == (None, None, 3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_advisor_db_write.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'build_position_heat'`

- [ ] **Step 3: Write minimal implementation**

First change the import line at the top of `sources/combiners/advisor/db.py` to:

```python
from datetime import date, datetime, timedelta
```

(`date` is used by `_age_days` below.) Then append after `prune`:

```python
def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (now_iso,))
    conn.commit()  # survive later per-source rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid, account, composite, sources_failed=0) -> None:
    """Freeze account scalars + upstream provenance into the header (every
    derived number depends on them). Either upstream may be None.
    sources_failed distinguishes a genuinely empty book from a night where
    a source read failed and left the tables empty."""
    a, c = account or {}, composite or {}
    conn.execute(
        "UPDATE snapshots SET equity=?, cash=?, buying_power=?,"
        " portfolio_captured_at=?, composite_captured_at=?, regime=?,"
        " sources_failed=? WHERE id=?",
        (
            a.get("equity"),
            a.get("cash"),
            a.get("buying_power"),
            a.get("captured_at"),
            c.get("captured_at"),
            c.get("regime"),
            sources_failed,
            sid,
        ),
    )


def _age_days(today: str, obs_date: str) -> int:
    return (date.fromisoformat(today) - date.fromisoformat(obs_date)).days


def build_position_heat(
    positions, scorecard, metrics, equity, today, ticker_group, atr_max_age_days
) -> list:
    """One row per held position. heat = quantity x ATR (dollars lost on a
    one-ATR adverse day); NULL heat when the symbol has no metrics row —
    visible, never silently dropped (v_book_heat.heat_coverage counts it)."""
    rows = []
    for p in positions:
        sym = p["symbol"]
        m = metrics.get(sym, {})
        atr, close, pdate = m.get("atr"), m.get("close"), m.get("price_date")
        heat_dollars = p["quantity"] * atr if atr is not None else None
        heat_pct = heat_dollars / equity if heat_dollars is not None and equity else None
        weight_pct = (
            p["market_value"] / equity if p["market_value"] is not None and equity else None
        )
        sc = scorecard.get(sym, {})
        atr_stale = None
        if pdate is not None:
            atr_stale = 1 if _age_days(today, pdate) > atr_max_age_days else 0
        rows.append(
            {
                "symbol": sym,
                "group_name": ticker_group.get(sym),
                "quantity": p["quantity"],
                "market_value": p["market_value"],
                "atr": atr,
                "price": close,
                "price_date": pdate,
                "heat_dollars": heat_dollars,
                "heat_pct": heat_pct,
                "weight_pct": weight_pct,
                "score_sum": sc.get("score_sum"),
                "bullish": sc.get("bullish"),
                "bearish": sc.get("bearish"),
                "total": sc.get("total"),
                "atr_stale": atr_stale,
            }
        )
    return rows


def build_size_caps(
    flagged,
    scorecard,
    metrics,
    heat_rows,
    equity,
    buying_power,
    risk_budget,
    ticker_group,
    flag_signals,
    reliable_ids,
) -> list:
    """One row per flagged ticker. The cap inverts the risk budget and
    shrinks by heat already carried through the same crosswalk group (a
    group is one bet): allowed = max(0, budget*equity - group_heat), then
    cap_shares = allowed / ATR — FRACTIONAL, matching Robinhood fractional
    sizing (flooring to whole shares would zero every cap on a small
    account). Bearish flags carry NULL caps: the book is long-only, so the
    row itself (direction, score, group) is the advice, never a buy size.
    Same-group sibling caps each see the same remaining budget —
    alternatives, not a shopping list. exceeds_buying_power and the
    reliable-evidence counts are annotations, never gates (reliable = the
    scorer's n_bench >= 30 sample floor, not proof a signal works);
    flag_signals/reliable_ids intersect on (signal_id, via_crosswalk)
    pairs so crosswalk-only reliability never cites as direct evidence."""
    group_heat: dict = {}
    held = set()
    for r in heat_rows:
        held.add(r["symbol"])
        if r["heat_dollars"] is not None:
            bet = r["group_name"] or r["symbol"]
            group_heat[bet] = group_heat.get(bet, 0.0) + r["heat_dollars"]
    rows = []
    for sym in flagged:
        sc = scorecard.get(sym, {})
        m = metrics.get(sym, {})
        atr, close = m.get("atr"), m.get("close")
        existing = group_heat.get(ticker_group.get(sym) or sym, 0.0)
        score_sum = sc.get("score_sum")
        direction = "bullish" if (score_sum or 0) > 0 else "bearish"
        cap_shares = cap_dollars = None
        if direction == "bullish" and atr and equity:
            allowed = max(0.0, risk_budget * equity - existing)
            cap_shares = allowed / atr
            if close is not None:
                cap_dollars = cap_shares * close
        sigs = flag_signals.get(sym, set())
        rows.append(
            {
                "symbol": sym,
                "direction": direction,
                "score_sum": score_sum,
                "atr": atr,
                "price": close,
                "cap_shares": cap_shares,
                "cap_dollars": cap_dollars,
                "group_name": ticker_group.get(sym),
                "group_heat_pct": existing / equity if equity else None,
                "reliable_signals": len(sigs & reliable_ids),
                "total_signals": len(sigs),
                "exceeds_buying_power": 1
                if cap_dollars is not None and buying_power is not None and cap_dollars > buying_power
                else 0,
                "already_held": 1 if sym in held else 0,
            }
        )
    return rows


def write_position_heat(conn, sid, rows) -> int:
    conn.executemany(
        "INSERT INTO position_heat (snapshot_id, symbol, group_name, quantity,"
        " market_value, atr, price, price_date, heat_dollars, heat_pct,"
        " weight_pct, score_sum, bullish, bearish, total, atr_stale)"
        " VALUES (:sid, :symbol, :group_name, :quantity, :market_value, :atr,"
        " :price, :price_date, :heat_dollars, :heat_pct, :weight_pct,"
        " :score_sum, :bullish, :bearish, :total, :atr_stale)",
        [{**r, "sid": sid} for r in rows],
    )
    return len(rows)


def write_size_caps(conn, sid, rows) -> int:
    conn.executemany(
        "INSERT INTO size_caps (snapshot_id, symbol, direction, score_sum,"
        " atr, price, cap_shares, cap_dollars, group_name, group_heat_pct,"
        " reliable_signals, total_signals, exceeds_buying_power, already_held)"
        " VALUES (:sid, :symbol, :direction, :score_sum, :atr, :price,"
        " :cap_shares, :cap_dollars, :group_name, :group_heat_pct,"
        " :reliable_signals, :total_signals, :exceeds_buying_power,"
        " :already_held)",
        [{**r, "sid": sid} for r in rows],
    )
    return len(rows)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_advisor_db_write.py tests/test_advisor_db_schema.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/advisor/db.py tests/test_advisor_db_write.py
git commit --no-gpg-sign -m "feat(advisor): heat/cap builders and snapshot writers"
```

---

### Task 4: View behavior (book heat, group heat, disagreements)

**Files:**
- Test: `tests/test_advisor_db_views.py` (no source changes expected — this task proves Task 2's views against Task 3's writers; fix views here if a test exposes a defect)

**Interfaces:**
- Consumes: everything from Tasks 2–3.
- Produces: nothing new — the executable contract for the views.

- [ ] **Step 1: Write the tests**

Create `tests/test_advisor_db_views.py`:

```python
from sources.combiners.advisor import db


def _row(**kw):
    base = {
        "symbol": "AAPL",
        "group_name": None,
        "quantity": 1.0,
        "market_value": 100.0,
        "atr": 1.0,
        "price": 100.0,
        "price_date": "2026-07-07",
        "heat_dollars": 1.0,
        "heat_pct": 0.0001,
        "weight_pct": 0.01,
        "score_sum": 0,
        "bullish": 0,
        "bearish": 0,
        "total": 0,
        "atr_stale": 0,
    }
    base.update(kw)
    return base


def _seed(conn, captured_at, heat_rows, cap_rows=()):
    sid = db.write_snapshot(conn, captured_at)
    db.write_position_heat(conn, sid, list(heat_rows))
    db.write_size_caps(conn, sid, list(cap_rows))
    db.finish_snapshot(
        conn,
        sid,
        {"equity": 10000.0, "cash": 0.0, "buying_power": 0.0, "captured_at": captured_at},
        {"snapshot_id": 1, "captured_at": captured_at, "regime": "risk_on"},
    )
    conn.commit()
    return sid


def _fresh(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    return conn


def test_latest_views_scope_to_newest_snapshot(tmp_path):
    conn = _fresh(tmp_path)
    _seed(conn, "2026-07-06T21:12:00+00:00", [_row(symbol="OLD")])
    _seed(conn, "2026-07-07T21:12:00+00:00", [_row(symbol="NEW")])
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_latest_heat")] == ["NEW"]


def test_book_heat_totals_and_coverage(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="AAPL", market_value=1000.0, atr=2.0, heat_dollars=20.0, heat_pct=0.002),
            _row(
                symbol="NOATR",
                market_value=1000.0,
                atr=None,
                heat_dollars=None,
                heat_pct=None,
                atr_stale=None,
            ),
        ],
    )
    row = conn.execute(
        "SELECT positions, heat_dollars, heat_pct, heat_coverage FROM v_book_heat"
    ).fetchone()
    assert row == (2, 20.0, 0.002, 0.5)  # half the book's value has an ATR


def test_book_heat_empty_book_yields_a_row(tmp_path):
    conn = _fresh(tmp_path)
    _seed(conn, "2026-07-07T21:12:00+00:00", [])
    row = conn.execute("SELECT positions, heat_dollars, heat_coverage FROM v_book_heat").fetchone()
    assert row == (0, None, None)


def test_group_heat_collapses_crosswalk_groups(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="XOM", group_name="energy", heat_dollars=20.0, heat_pct=0.002),
            _row(symbol="XLE", group_name="energy", heat_dollars=10.0, heat_pct=0.001),
            _row(symbol="AAPL", group_name=None, heat_dollars=5.0, heat_pct=0.0005),
        ],
    )
    rows = {
        r[0]: (r[1], r[2])
        for r in conn.execute("SELECT bet, members, heat_dollars FROM v_group_heat")
    }
    assert rows["energy"] == (2, 30.0)
    assert rows["AAPL"] == (1, 5.0)


def test_disagreements_only_negative_scores_with_strong_flag(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="LIKED", score_sum=3, total=3),
            _row(symbol="MILD", score_sum=-1, total=2),
            _row(symbol="BAD", score_sum=-4, total=3),
        ],
    )
    rows = {r[0]: r[1] for r in conn.execute("SELECT symbol, strong FROM v_disagreements")}
    assert rows == {"MILD": 0, "BAD": 1}


def test_latest_caps_scope(tmp_path):
    conn = _fresh(tmp_path)
    cap = {
        "symbol": "NVDA",
        "direction": "bullish",
        "score_sum": 4,
        "atr": 4.0,
        "price": 100.0,
        "cap_shares": 25,
        "cap_dollars": 2500.0,
        "group_name": None,
        "group_heat_pct": 0.0,
        "reliable_signals": 1,
        "total_signals": 3,
        "exceeds_buying_power": 1,
        "already_held": 0,
    }
    _seed(conn, "2026-07-06T21:12:00+00:00", [], [dict(cap, symbol="STALE")])
    _seed(conn, "2026-07-07T21:12:00+00:00", [], [cap])
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_latest_caps")] == ["NVDA"]
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/test_advisor_db_views.py -v`
Expected: all PASS (Tasks 2–3 already implemented the behavior). If any FAIL, fix the view SQL in `sources/combiners/advisor/db.py` — the test is the contract.

- [ ] **Step 3: Commit**

```bash
git add tests/test_advisor_db_views.py
git commit --no-gpg-sign -m "test(advisor): view contracts — book heat, group bets, disagreements"
```

---

### Task 5: fetch.py — read-only extraction from the four upstreams

**Files:**
- Create: `sources/combiners/advisor/fetch.py`
- Test: `tests/test_advisor_fetch.py`

**Interfaces:**
- Consumes: composite.db views (`v_latest_scorecard`, `v_flagged`, `v_signal_detail`), portfolio.db views (`v_latest_account`, `v_latest_positions`), stocks/etfs `v_latest` (columns `atr`, `close`, `priceDate` — quote them, they're case-sensitive camelCase), scorer.db `v_signal_efficacy`.
- Produces (Task 6 calls all of these; each expects the source attached as `src`):
  - `attach_ro(conn, db_path, alias="src")`, `detach(conn, alias="src")`
  - `read_composite_header(conn) -> dict | None` — `{"snapshot_id", "captured_at", "regime"}`
  - `read_scorecard(conn) -> dict` — `{symbol: {"score_sum","bullish","bearish","total"}}`
  - `read_flagged(conn) -> list` — symbols, sorted
  - `read_flag_signals(conn) -> dict` — `{symbol: set((signal_id, via_crosswalk))}` (voting ticker-grain evidence pairs)
  - `read_account(conn) -> dict | None` — `{"equity","cash","buying_power","captured_at"}`
  - `read_positions(conn) -> list` — `[{"symbol","quantity","market_value"}]`
  - `read_metrics(conn, symbols) -> dict` — `{symbol: {"atr","close","price_date"}}`
  - `read_reliable_signals(conn) -> set` — `(signal_id, via_crosswalk)` pairs with any `reliable = 1` efficacy row

- [ ] **Step 1: Write the failing test**

Create `tests/test_advisor_fetch.py`:

```python
from sources.combiners.advisor import db as advisor_db
from sources.combiners.advisor import fetch
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db
from sources.screeners.portfolio_screener import db as portfolio_db
from sources.screeners.stock_analysis_screener import db as stocks_db

PRICE_COLS = {"priceDate": "TEXT", "close": "REAL", "atr": "REAL"}


def _advisor_conn(tmp_path):
    """A real advisor.db connection — its own `snapshots` table must never
    shadow an attached DB's inside that DB's views."""
    conn = advisor_db.connect(str(tmp_path / "advisor.db"))
    advisor_db.ensure_schema(conn)
    return conn


def _mini_composite(dirpath, signals):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, "2026-07-06T21:05:00+00:00", len(signals))
    composite_db.write_signal_values(conn, sid, signals)
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()


def _sig(signal_id, entity, score):
    return dict(
        signal_id=signal_id,
        grain="ticker",
        entity=entity,
        raw_value=1.0,
        score=score,
        obs_date="2026-07-06",
        staleness_days=0.0,
    )


def _mini_portfolio(dirpath):
    conn = portfolio_db.connect(str(dirpath / "portfolio.db"))
    portfolio_db.ensure_schema(conn)
    portfolio_db.write_snapshot(
        conn,
        "2026-07-07T21:30:00+00:00",
        {"equity": 10000.0, "cash": 2000.0, "buying_power": 1000.0},
        [
            {"symbol": "AAPL", "quantity": 10.0, "avg_cost": 90.0, "market_value": 1000.0},
            {"symbol": "XOM", "quantity": 5.0, "avg_cost": 70.0, "market_value": 400.0},
        ],
    )
    conn.close()


def _mini_prices(path, rows):
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, 's')",
        ("2026-07-07T11:00:00+00:00", len(rows)),
    )
    sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
    for sym, close, atr in rows:
        conn.execute(
            'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "atr")'
            " VALUES (?, ?, ?, ?, ?)",
            (sid, sym, "2026-07-07", close, atr),
        )
    conn.commit()
    conn.close()


def _mini_scorer(dirpath, reliable_signal="sig_a"):
    conn = scorer_db.connect(str(dirpath / "scorer.db"))
    scorer_db.ensure_schema(conn)
    # 30 matured, benchmarked rows for one (signal_id, horizon) group ->
    # n_bench = 30 -> reliable = 1 in v_signal_efficacy.
    conn.executemany(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                i, "2026-06-01", reliable_signal, f"T{i}", 1, 0, 5, "2026-06-02",
                100.0, "SPY", 500.0, "2026-06-09", 110.0, 0.10, 0.01,
                "2026-06-09T21:10:00+00:00",
            )
            for i in range(1, 31)
        ],
    )
    conn.commit()
    conn.close()


def test_composite_readers_resolve_views_in_attached_schema(tmp_path):
    # NVDA: three voting signals summing to +4 -> flagged. AAPL: one -1 vote.
    _mini_composite(
        tmp_path,
        [_sig("sig_a", "NVDA", 2), _sig("sig_b", "NVDA", 1), _sig("sig_c", "NVDA", 1),
         _sig("stocks_rsi", "AAPL", -1)],
    )
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "composite.db"))
    header = fetch.read_composite_header(conn)
    assert header["captured_at"] == "2026-07-06T21:05:00+00:00"
    expected_regime = conn.execute("SELECT regime FROM src.market_regime").fetchone()[0]
    assert header["regime"] == expected_regime
    scorecard = fetch.read_scorecard(conn)
    assert scorecard["NVDA"]["score_sum"] == 4 and scorecard["NVDA"]["total"] == 3
    assert scorecard["AAPL"]["score_sum"] == -1
    assert fetch.read_flagged(conn) == ["NVDA"]
    assert fetch.read_flag_signals(conn)["NVDA"] == {("sig_a", 0), ("sig_b", 0), ("sig_c", 0)}
    fetch.detach(conn)


def test_portfolio_readers(tmp_path):
    _mini_portfolio(tmp_path)
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "portfolio.db"))
    account = fetch.read_account(conn)
    assert account == {
        "equity": 10000.0,
        "cash": 2000.0,
        "buying_power": 1000.0,
        "captured_at": "2026-07-07T21:30:00+00:00",
    }
    positions = fetch.read_positions(conn)
    assert {p["symbol"] for p in positions} == {"AAPL", "XOM"}
    fetch.detach(conn)


def test_read_metrics_filters_to_requested_symbols(tmp_path):
    _mini_prices(tmp_path / "stocks.db", [("AAPL", 100.0, 2.0), ("OTHER", 50.0, 1.0)])
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "stocks.db"))
    metrics = fetch.read_metrics(conn, {"AAPL", "MISSING"})
    assert metrics == {"AAPL": {"atr": 2.0, "close": 100.0, "price_date": "2026-07-07"}}
    assert fetch.read_metrics(conn, set()) == {}
    fetch.detach(conn)


def test_read_reliable_signals(tmp_path):
    _mini_scorer(tmp_path, reliable_signal="sig_a")
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "scorer.db"))
    assert fetch.read_reliable_signals(conn) == {("sig_a", 0)}
    fetch.detach(conn)


def test_attach_ro_missing_file_raises(tmp_path):
    conn = _advisor_conn(tmp_path)
    try:
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_advisor_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError` (no `fetch` module)

- [ ] **Step 3: Write minimal implementation**

Create `sources/combiners/advisor/fetch.py`:

```python
"""Read-only extraction from composite (scorecard), portfolio (holdings),
stocks/etfs (ATR + close), and scorer (efficacy). No network anywhere in
this package. Every reader expects its source attached as `src`."""

import os


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}", (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


def read_composite_header(conn):
    """Latest composite snapshot (captured_at + regime); None when empty."""
    row = conn.execute(
        "SELECT s.id, s.captured_at, m.regime FROM src.snapshots s"
        " LEFT JOIN src.market_regime m ON m.snapshot_id = s.id"
        " ORDER BY s.captured_at DESC, s.id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return {"snapshot_id": row[0], "captured_at": row[1], "regime": row[2]}


def read_scorecard(conn) -> dict:
    """symbol -> latest composite score row. SQLite resolves an attached
    view's internals in the view's own schema, so src.v_latest_scorecard is
    safe even though advisor.db has its own `snapshots` table."""
    return {
        r[0]: {"score_sum": r[1], "bullish": r[2], "bearish": r[3], "total": r[4]}
        for r in conn.execute(
            "SELECT symbol, score_sum, bullish, bearish, total FROM src.v_latest_scorecard"
        )
    }


def read_flagged(conn) -> list:
    """Symbols composite currently flags. Reading src.v_flagged keeps the
    flag threshold on composite's side — the advisor never re-states it."""
    return [r[0] for r in conn.execute("SELECT symbol FROM src.v_flagged ORDER BY symbol")]


def read_flag_signals(conn) -> dict:
    """symbol -> contributing voting evidence as (signal_id, via_crosswalk)
    pairs (latest snapshot; score-0 rows are informational and excluded).
    Pairs, not bare ids: the scorer grades the direct and crosswalked
    splits separately, so citations must not collapse them."""
    out: dict = {}
    for sym, sig, via in conn.execute(
        "SELECT entity, signal_id, via_crosswalk FROM src.v_signal_detail"
        " WHERE grain = 'ticker' AND score != 0"
    ):
        out.setdefault(sym, set()).add((sig, via))
    return out


def read_account(conn):
    """Latest account scalars + that snapshot's captured_at; None when
    portfolio.db has no snapshot yet."""
    row = conn.execute(
        "SELECT a.equity, a.cash, a.buying_power, s.captured_at"
        " FROM src.v_latest_account a JOIN src.snapshots s ON s.id = a.snapshot_id"
    ).fetchone()
    if row is None:
        return None
    return {"equity": row[0], "cash": row[1], "buying_power": row[2], "captured_at": row[3]}


def read_positions(conn) -> list:
    return [
        {"symbol": r[0], "quantity": r[1], "market_value": r[2]}
        for r in conn.execute(
            "SELECT symbol, quantity, market_value FROM src.v_latest_positions"
        )
    ]


def read_metrics(conn, symbols) -> dict:
    """symbol -> {atr, close, price_date} from a price DB's v_latest.
    Column names are stockanalysis.com camelCase — keep them quoted."""
    syms = sorted(symbols)
    if not syms:
        return {}
    qmarks = ",".join("?" * len(syms))
    return {
        r[0]: {"atr": r[1], "close": r[2], "price_date": r[3]}
        for r in conn.execute(
            f'SELECT symbol, "atr", "close", "priceDate" FROM src.v_latest'
            f" WHERE symbol IN ({qmarks})",
            syms,
        )
    }


def read_reliable_signals(conn) -> set:
    """(signal_id, via_crosswalk) pairs with a reliable efficacy row at any
    horizon — annotation input for size_caps. reliable is the scorer's
    sample-size floor (n_bench >= 30), not proof the signal works."""
    return {
        (r[0], r[1])
        for r in conn.execute(
            "SELECT DISTINCT signal_id, via_crosswalk FROM src.v_signal_efficacy"
            " WHERE reliable = 1"
        )
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_advisor_fetch.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/advisor/fetch.py tests/test_advisor_fetch.py
git commit --no-gpg-sign -m "feat(advisor): read-only fetch from composite/portfolio/prices/scorer"
```

---

### Task 6: run.py orchestration + registry entry

**Files:**
- Create: `sources/combiners/advisor/run.py`
- Modify: `registry.py` (one import + one dict entry)
- Modify: `tests/test_registry.py` (append one test)
- Test: `tests/test_advisor_run.py`

**Interfaces:**
- Consumes: everything from Tasks 1, 3, 5.
- Produces: `run(db_path, db_dir, now_iso=None, keep_days=None) -> tuple[int, int, int]` (`(sid, n_heat_rows, n_cap_rows)`) and `main(argv=None)`; registry name `"advisor"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_advisor_run.py` (fixture helpers duplicated from the fetch test on purpose — each test file in this repo is self-contained):

```python
import sqlite3

from sources.combiners.advisor import run as run_mod
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db
from sources.screeners.portfolio_screener import db as portfolio_db
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-07T21:12:00+00:00"
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL", "atr": "REAL"}


def _sig(signal_id, entity, score):
    return dict(
        signal_id=signal_id,
        grain="ticker",
        entity=entity,
        raw_value=1.0,
        score=score,
        obs_date="2026-07-06",
        staleness_days=0.0,
    )


def _mini_composite(dirpath):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    signals = [
        _sig("sig_a", "NVDA", 2),
        _sig("sig_b", "NVDA", 1),
        _sig("sig_c", "NVDA", 1),  # NVDA: +4 over 3 votes -> flagged
        _sig("stocks_rsi", "AAPL", -1),  # AAPL: held + negative -> disagreement
    ]
    sid = composite_db.write_snapshot(conn, "2026-07-06T21:05:00+00:00", len(signals))
    composite_db.write_signal_values(conn, sid, signals)
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()


def _mini_portfolio(dirpath):
    conn = portfolio_db.connect(str(dirpath / "portfolio.db"))
    portfolio_db.ensure_schema(conn)
    portfolio_db.write_snapshot(
        conn,
        "2026-07-07T21:30:00+00:00",
        {"equity": 10000.0, "cash": 2000.0, "buying_power": 1000.0},
        [
            {"symbol": "AAPL", "quantity": 10.0, "avg_cost": 90.0, "market_value": 1000.0},
            {"symbol": "XOM", "quantity": 5.0, "avg_cost": 70.0, "market_value": 400.0},
        ],
    )
    conn.close()


def _mini_prices(path, rows):
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, 's')",
        ("2026-07-07T11:00:00+00:00", len(rows)),
    )
    sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
    for sym, close, atr in rows:
        conn.execute(
            'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "atr")'
            " VALUES (?, ?, ?, ?, ?)",
            (sid, sym, "2026-07-07", close, atr),
        )
    conn.commit()
    conn.close()


def _mini_scorer(dirpath):
    conn = scorer_db.connect(str(dirpath / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                i, "2026-06-01", "sig_a", f"T{i}", 1, 0, 5, "2026-06-02",
                100.0, "SPY", 500.0, "2026-06-09", 110.0, 0.10, 0.01,
                "2026-06-09T21:10:00+00:00",
            )
            for i in range(1, 31)
        ],
    )
    conn.commit()
    conn.close()


def _full_fixture(tmp_path):
    _mini_composite(tmp_path)
    _mini_portfolio(tmp_path)
    _mini_prices(tmp_path / "stocks.db", [("AAPL", 100.0, 2.0), ("NVDA", 100.0, 4.0)])
    _mini_prices(tmp_path / "etfs.db", [("XOM", 80.0, 4.0)])
    _mini_scorer(tmp_path)


def test_full_cycle(tmp_path):
    _full_fixture(tmp_path)
    out = str(tmp_path / "advisor.db")
    sid, n_heat, n_caps = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert (n_heat, n_caps) == (2, 1)  # AAPL + XOM held; NVDA flagged
    conn = sqlite3.connect(out)
    # header provenance frozen in
    assert conn.execute(
        "SELECT equity, buying_power, portfolio_captured_at, composite_captured_at,"
        " sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone() == (
        10000.0,
        1000.0,
        "2026-07-07T21:30:00+00:00",
        "2026-07-06T21:05:00+00:00",
        0,
    )
    # heat: AAPL 10x2=20 (from stocks.db), XOM 5x4=20 (from etfs.db fallback)
    heat = dict(conn.execute("SELECT symbol, heat_dollars FROM v_latest_heat"))
    assert heat == {"AAPL": 20.0, "XOM": 20.0}
    # NVDA cap: floor(0.01*10000/4)=25 shares = $2500 > $1000 buying power
    cap = conn.execute(
        "SELECT cap_shares, cap_dollars, exceeds_buying_power, direction,"
        " reliable_signals, total_signals, already_held FROM v_latest_caps"
    ).fetchone()
    assert cap == (25.0, 2500.0, 1, "bullish", 1, 3, 0)
    # AAPL is a (weak) disagreement
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_disagreements")] == ["AAPL"]


def test_missing_sources_skip_and_continue(tmp_path, capsys):
    out = str(tmp_path / "advisor.db")
    sid, n_heat, n_caps = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert (n_heat, n_caps) == (0, 0)
    err = capsys.readouterr().out
    # composite, portfolio, scorer missing -> 3 skips; price DBs are never
    # attached because there are no symbols to look up. Type names only.
    assert err.count("FileNotFoundError") == 3
    assert "Traceback" not in err
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    # the header owns the distinction between "empty book" and "failed reads"
    assert conn.execute("SELECT positions, sources_failed FROM v_book_heat").fetchone() == (0, 3)


def test_prune_via_keep_days(tmp_path):
    _full_fixture(tmp_path)
    out = str(tmp_path / "advisor.db")
    run_mod.run(out, str(tmp_path), now_iso="2026-01-01T21:12:00+00:00")
    run_mod.run(out, str(tmp_path), now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_main_argv(tmp_path, capsys):
    _full_fixture(tmp_path)
    run_mod.main(["--db", str(tmp_path / "advisor.db"), "--db-dir", str(tmp_path)])
    assert "advisor snapshot" in capsys.readouterr().out
```

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_advisor():
    import registry

    assert "advisor" in registry.REGISTRY
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_advisor_run.py tests/test_registry.py -v`
Expected: advisor tests FAIL with `ModuleNotFoundError` (no `run` module); `test_dispatch_lists_advisor` FAILs with KeyError-style assert.

- [ ] **Step 3: Write the implementation**

Create `sources/combiners/advisor/run.py`:

```python
"""Nightly sizing/risk advice: joins the composite scorecard against real
holdings (book heat, disagreements, size caps). Sources attached read-only
one at a time; the advisor writes only advisor.db — decision support,
never order generation."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.advisor import catalog, db, fetch


def run(db_path, db_dir, now_iso=None, keep_days=None):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    today = now_iso[:10]  # one-clock rule: all staleness is judged on this
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso)
        composite = None
        account = None
        scorecard: dict = {}
        flag_signals: dict = {}
        flagged: list = []
        positions: list = []
        metrics: dict = {}
        reliable: set = set()

        failures = 0

        def read_source(db_name, reader):
            """Attach one source read-only, run reader(), skip-and-continue
            printing only the exception type (secret hygiene). Failures are
            counted into the header so a partial night is visible."""
            nonlocal failures
            path = os.path.join(db_dir, db_name)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                failures += 1
                print(f"skip {db_name}: {type(e).__name__}")
                return
            try:
                reader()
            except Exception as e:
                failures += 1
                conn.rollback()
                print(f"skip {db_name}: {type(e).__name__}")
            finally:
                fetch.detach(conn)

        # Readers assign their nonlocals only after EVERY read in the source
        # succeeds — a failure mid-source must not apply half a source (real
        # equity + zero positions would masquerade as an empty book).
        def read_composite():
            nonlocal composite, scorecard, flagged, flag_signals
            header = fetch.read_composite_header(conn)
            cards = fetch.read_scorecard(conn)
            flags = fetch.read_flagged(conn)
            sigs = fetch.read_flag_signals(conn)
            composite, scorecard, flagged, flag_signals = header, cards, flags, sigs

        def read_portfolio():
            nonlocal account, positions
            acct = fetch.read_account(conn)
            pos = fetch.read_positions(conn)
            account, positions = acct, pos

        def read_prices():
            for sym, m in fetch.read_metrics(conn, symbols).items():
                metrics.setdefault(sym, m)  # first DB (stocks) wins

        def read_scorer():
            nonlocal reliable
            reliable = fetch.read_reliable_signals(conn)

        read_source(catalog.COMPOSITE_DB, read_composite)
        read_source(catalog.PORTFOLIO_DB, read_portfolio)
        symbols = {p["symbol"] for p in positions} | set(flagged)
        if symbols:
            for price_db in catalog.PRICE_DBS:
                read_source(price_db, read_prices)
        read_source(catalog.SCORER_DB, read_scorer)

        equity = account["equity"] if account else None
        buying_power = account["buying_power"] if account else None
        heat_rows = db.build_position_heat(
            positions, scorecard, metrics, equity, today,
            catalog.TICKER_GROUP, catalog.ATR_MAX_AGE_DAYS,
        )
        cap_rows = db.build_size_caps(
            flagged, scorecard, metrics, heat_rows, equity, buying_power,
            catalog.RISK_BUDGET, catalog.TICKER_GROUP, flag_signals, reliable,
        )
        db.write_position_heat(conn, sid, heat_rows)
        db.write_size_caps(conn, sid, cap_rows)
        db.finish_snapshot(conn, sid, account, composite, failures)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, len(heat_rows), len(cap_rows)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="advisor",
        description="Sizing/risk advice: book heat, disagreements, size caps"
        " (reads composite/portfolio/stocks/etfs/scorer read-only)",
    )
    p.add_argument("--db", default="advisor.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, n_heat, n_caps = run(a.db, a.db_dir, keep_days=a.keep_days)
    print(f"advisor snapshot {sid}: {n_heat} positions, {n_caps} caps, into {a.db}")


if __name__ == "__main__":
    main()
```

Modify `registry.py` — add the import (alphabetical, before the composite import):

```python
from sources.combiners.advisor.run import main as advisor_main
```

and the dict entry (after `"journal": journal_main,` at the end of the combiner block):

```python
    "advisor": advisor_main,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_advisor_run.py tests/test_registry.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full suite + gates**

Run: `uv run pytest && uv run ruff check && uv run ruff format --check && uv run mypy`
Expected: all green (the pre-commit hook re-runs these anyway)

- [ ] **Step 6: Commit**

```bash
git add sources/combiners/advisor/run.py registry.py tests/test_advisor_run.py tests/test_registry.py
git commit --no-gpg-sign -m "feat(advisor): run orchestration + registry dispatch"
```

---

### Task 7: Schedule slot + docs (ship it)

**Files:**
- Modify: `deploy/launchd/install.py` (one JOBS entry)
- Modify: `docs/SCHEDULE.md` (agent count + one table row)
- Modify: `CLAUDE.md` (combiner count + one sentence)
- Modify: `docs/ROADMAP.md` (prune item 6 to a shipped note)

**Interfaces:**
- Consumes: registry name `"advisor"` from Task 6.
- Produces: the deployed nightly slot. No code.

- [ ] **Step 1: Add the launchd job**

In `deploy/launchd/install.py`, in the `JOBS` dict's combine block, insert between the `"scorer"` and `"daily-summary"` entries:

```python
    "advisor": (job("advisor", "--keep-days", "365"), weekly(range(7), 21, 12)),
```

- [ ] **Step 2: Update docs/SCHEDULE.md**

Two edits:

1. Header count: change `30 \`com.tradingbot.*\` LaunchAgents` to `31 \`com.tradingbot.*\` LaunchAgents`.
2. In the Monthly table, insert this row between the `scorer` and `daily-summary` rows:

```markdown
| `advisor` | every day 9:12pm | Sizing/risk advice into `data/advisor.db`: joins the composite scorecard against portfolio holdings + stocks/etfs ATR + scorer efficacy (all attached read-only). Book heat (`v_book_heat`/`v_group_heat`, crosswalk groups = one bet), holdings composite disagrees with (`v_disagreements`), and 1%-risk-budget size caps (`v_latest_caps`). Must stay after scorer 9:10pm, before daily-summary 9:15pm. Weekend runs size against Friday's 2:30pm portfolio snapshot — `portfolio_captured_at` in the header makes that auditable |
```

- [ ] **Step 3: Update CLAUDE.md**

Read `CLAUDE.md` first, then two edits:

1. File-tree line: change `└── combiners/    # 2 cross-source combiners (composite: opinions; scorer: grades them)` to `└── combiners/    # 3 cross-source combiners (composite: opinions; scorer: grades; advisor: sizes)` (match the file's exact current spacing).
2. In the "Combiners are the third source kind" paragraph, after the sentence about the scorer's decision journal, append:

```
The `advisor` combiner joins the latest scorecard against real holdings
(portfolio.db read via `v_latest_*` only) plus stocks/etfs ATR and scorer
efficacy: book heat, disagreements, and vol-scaled size caps — decision
support only, never order generation.
```

- [ ] **Step 4: Prune ROADMAP.md item 6**

Replace the entire `### 6. Sizing / risk advisor combiner` section (heading through its `**Size.** L. **Depends on.** ...` line) with:

```markdown
*(Item 6, sizing/risk advisor: `advisor` combiner joins the composite
scorecard against real holdings — `v_book_heat`/`v_group_heat` (ATR heat,
crosswalk groups count as one bet), `v_disagreements`, and 1%-risk-budget
size caps in `v_latest_caps`, annotated with scorer `reliable` signal
counts. Shipped 2026-07-07; 9:12pm daily slot between scorer and
daily-summary.)*
```

- [ ] **Step 5: Verify**

Run: `uv run python deploy/launchd/install.py --dry-run` — expect a plist generated for `com.tradingbot.advisor` with `Hour 21 / Minute 12`, no errors.
Run: `uv run pytest` — full suite green.

- [ ] **Step 6: Commit**

```bash
git add deploy/launchd/install.py docs/SCHEDULE.md CLAUDE.md docs/ROADMAP.md
git commit --no-gpg-sign -m "feat(advisor): 9:12pm launchd slot; docs + roadmap prune"
```

- [ ] **Step 7: Deployment note (surface to the user, not a code step)**

The new slot loads only when the user runs `uv run python deploy/launchd/install.py` (regenerates + reloads plists) on the always-on machine. First real run happens at 9:12pm; sensible manual smoke test first:
`uv run python main.py advisor --db data/advisor.db --keep-days 365` then inspect `v_book_heat` / `v_latest_caps`.
