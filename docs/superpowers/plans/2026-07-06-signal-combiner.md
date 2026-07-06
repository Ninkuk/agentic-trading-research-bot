# Composite Signal Combiner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new `composite` source that reads the ~21 per-source SQLite DBs read-only, normalizes curated signals to −2…+2 scores, and materializes a market-regime row + per-ticker scorecard with snapshot provenance into `data/composite.db`.

**Architecture:** New third source kind `sources/combiners/composite/` with the standard four files (`catalog.py`, `fetch.py`, `db.py`, `run.py`). Two-phase run: (1) per-source sequential `ATTACH ... ?mode=ro` → extract → `DETACH` (SQLite's attach limit is 10, verified on this machine — never attach all at once); (2) combine inside `composite.db` with no source attached. Spec: `docs/superpowers/specs/2026-07-06-signal-combiner-design.md`.

**Tech Stack:** Python 3.12 stdlib only (`sqlite3`, `argparse`, `os`, `datetime`). Dev dependency: pytest via `uv run pytest`.

## Global Constraints

- **Stdlib only.** No new runtime dependencies, no exceptions.
- **No network anywhere in this package** — the combiner's external feed is the local `data/` directory.
- **Source DBs are attached read-only, always** (`file:<path>?mode=ro` URI). The composite connection MUST be opened with `sqlite3.connect(path, uri=True)` or the ATTACH fails with `OperationalError: unable to open database` (verified live; plain paths still work under `uri=True`).
- **One-clock rule:** extraction SQL binds the run's own `:today` (= `now_iso[:10]`); NEVER read source views that reference `calendar_now` (all 4 monitors' `v_upcoming`/`v_imminent`/derivatives, `treasury.v_upcoming_auctions`, `fred.v_asof`). Query base tables instead.
- **Determinism:** time enters `run()` only as injected `now_iso` (UTC `datetime.now(timezone.utc).isoformat()` — fixed-width incl. `+00:00`; prune's lexicographic compare depends on it).
- **Secret hygiene:** on per-item failure print only `type(e).__name__`, never `str(e)`/`repr(e)`.
- **Offline tests:** no network, no real `data/` DBs in tests; fixtures build miniature source DBs in `tmp_path` by calling each source's own `ensure_schema`.
- **Score semantics:** integer −2…+2, positive = bullish for the entity, contrarian interpretation applied inside the extraction SQL.
- **Commits:** `git commit --no-gpg-sign` (GPG signing hangs non-interactive sessions); no `Co-Authored-By` trailers.
- Run the suite with `uv run pytest` (repo root). Full suite must stay green after every task.

## Deviations from spec (agreed at plan time)

- `market_regime.rrp_trend TEXT` / `tga_trend TEXT` become `rrp_change REAL` / `tga_change REAL` (signed week-over-week deltas — more queryable; the sign IS the trend). Spec amended.
- The illustrative `stocks` trend-state signal (`ma50vs200`) is **omitted**: it would emit ~3k ±1 rows per run and drown `signal_values`. Revisit as a scorecard JOIN column later.
- CFTC `fx` asset class is scored but **not crosswalked** (net-long EUR ≠ net-long UUP; direction is incoherent at class level).
- `edgar_insider` and `portfolio_holding` carry `score 0` (informational: Form 4 clusters are directionless at index level; holdings are not a view). Score-0 signals are excluded from bullish/bearish counts but `edgar_insider` counts toward `total`.

## Post-review adjustments (adversarial review, 2026-07-06)

An adversarial review with full session context ran every catalog SQL against the real DBs and simulated the vote aggregation; verdict FIX-THEN-SHIP. Applied to this plan:

- **F1 (blocker):** `_mini_portfolio` fixture now supplies `position_count` (portfolio's `snapshots` requires it NOT NULL).
- **F2 (major):** `si_days_to_cover` tightened to `>= 10` floor / `>= 20` for +2 — at the old view floor (≥5) it emitted 1,599 rows, was 1,317 tickers' only signal, and skewed the composite bullish. Smoke run now checks the score distribution.
- **F3 (major):** `si_days_to_cover` + `ftd_persistent` family overlap documented in catalog (both read squeeze fuel; a flag from only these two is one phenomenon double-counted). Family-diverse flagging deferred deliberately.
- **F4 (minor):** `stocks_rsi` excludes degenerate `rsi = 0` rows (real placeholder artifacts scored +2).
- **F5 (minor):** launchd slot moved 21:00 → 21:05 to clear edgar's 15-min failure-retry window.
- **F6 (minor):** short-interest staleness budgets 20 → 25 days (FINRA bi-monthly + ~9-day publication lag).

## File Structure

- Create: `sources/combiners/__init__.py` (empty), `sources/combiners/composite/__init__.py` (empty)
- Create: `sources/combiners/composite/db.py` — composite schema, writers, combine SQL, views, prune
- Create: `sources/combiners/composite/catalog.py` — `SIGNALS`, `REGIME_FIELDS`, `CROSSWALK`, `select_ids`
- Create: `sources/combiners/composite/fetch.py` — `attach_ro`, `detach`, `staleness_days`, `extract`
- Create: `sources/combiners/composite/run.py` — `run(...)` + `main(argv)`
- Modify: `registry.py` — register `composite`
- Modify: `deploy/launchd/install.py:54-88` (JOBS dict), `docs/SCHEDULE.md`, `CLAUDE.md`
- Tests: `tests/test_composite_db_schema.py`, `tests/test_composite_db_write.py`, `tests/test_composite_db_views.py`, `tests/test_composite_catalog.py`, `tests/test_composite_fetch.py`, `tests/test_composite_run.py`, `tests/test_registry.py`

---

### Task 1: Package skeleton + schema (`db.py` part 1)

**Files:**
- Create: `sources/combiners/__init__.py`, `sources/combiners/composite/__init__.py`
- Create: `sources/combiners/composite/db.py`
- Test: `tests/test_composite_db_schema.py`

**Interfaces:**
- Produces: `db.connect(path) -> sqlite3.Connection` (URI-enabled, WAL), `db.ensure_schema(conn)`. Tables: `snapshots(id, captured_at, signals_expected, signals_ok, signals_failed)`, `signal_values`, `market_regime`, `ticker_scores` (columns exactly as in the code below).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_composite_db_schema.py
import sqlite3

from sources.combiners.composite import db


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def test_ensure_schema_creates_tables(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    assert {"snapshots", "signal_values", "market_regime",
            "ticker_scores"} <= _tables(conn)


def test_ensure_schema_is_idempotent(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise


def test_connect_uses_wal_and_uri(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    # URI mode is on: an ATTACH with ?mode=ro must parse (target must exist)
    other = tmp_path / "src.db"
    sqlite3.connect(str(other)).close()
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{other}?mode=ro",))


def test_score_check_constraint(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (captured_at, signals_expected)"
                 " VALUES ('2026-07-06T00:00:00+00:00', 1)")
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO signal_values (snapshot_id, signal_id, grain,"
            " entity, score) VALUES (1, 'x', 'ticker', 'AAPL', 3)")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources.combiners'`

- [ ] **Step 3: Write the implementation**

Create the two empty `__init__.py` files, then:

```python
# sources/combiners/composite/db.py
"""composite.db schema: snapshot-scoped signal values, one market-regime
row per run, and a per-ticker scorecard. The composite's value is its
replayable history — everything is snapshot-scoped and pruned by cascade."""
import sqlite3
from datetime import datetime, timedelta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    signals_expected INTEGER NOT NULL,
    signals_ok       INTEGER NOT NULL DEFAULT 0,
    signals_failed   INTEGER NOT NULL DEFAULT 0
);

-- Audit trail: every composite number is reconstructible from here.
CREATE TABLE IF NOT EXISTS signal_values (
    snapshot_id    INTEGER NOT NULL REFERENCES snapshots(id),
    signal_id      TEXT NOT NULL,
    grain          TEXT NOT NULL
                   CHECK (grain IN ('market', 'asset_class', 'ticker')),
    entity         TEXT NOT NULL,          -- '*' | asset class | ticker
    raw_value      REAL,
    score          INTEGER NOT NULL DEFAULT 0
                   CHECK (score BETWEEN -2 AND 2),
    obs_date       TEXT,
    staleness_days REAL,
    via_crosswalk  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, signal_id, entity)
);

CREATE TABLE IF NOT EXISTS market_regime (
    snapshot_id          INTEGER PRIMARY KEY REFERENCES snapshots(id),
    t10y2y               REAL,
    curve_inverted       INTEGER,
    hy_spread            REAL,
    vix                  REAL,
    vix_backwardation    INTEGER,
    equity_pcr_pctile    REAL,
    in_fomc_blackout     INTEGER,
    imminent_high_impact INTEGER,
    days_to_opex         INTEGER,
    rrp_change           REAL,
    tga_change           REAL,
    regime               TEXT,             -- risk_on | risk_off | mixed
    inputs_expected      INTEGER NOT NULL,
    inputs_present       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_scores (
    snapshot_id          INTEGER NOT NULL REFERENCES snapshots(id),
    symbol               TEXT NOT NULL,
    bullish              INTEGER NOT NULL DEFAULT 0,
    bearish              INTEGER NOT NULL DEFAULT 0,
    total                INTEGER NOT NULL DEFAULT 0,
    score_sum            INTEGER NOT NULL DEFAULT 0,
    coverage             REAL,
    worst_staleness_days REAL,
    in_portfolio         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, symbol)
);
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine);
    # without it the read-only attach fails outright.
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_db_schema.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add sources/combiners tests/test_composite_db_schema.py
git commit --no-gpg-sign -m "feat(composite): combiners package skeleton + composite.db schema"
```

---

### Task 2: Writers, combine functions, prune (`db.py` part 2)

**Files:**
- Modify: `sources/combiners/composite/db.py` (append)
- Test: `tests/test_composite_db_write.py`

**Interfaces:**
- Consumes: Task 1 schema.
- Produces:
  - `write_snapshot(conn, now_iso, signals_expected) -> int` (commits immediately so later rollbacks never lose the header)
  - `finish_snapshot(conn, sid, ok, failed) -> None`
  - `write_signal_values(conn, sid, rows) -> int` — rows are dicts with keys `signal_id, grain, entity, raw_value, score, obs_date, staleness_days` (and optional `via_crosswalk`); `INSERT OR IGNORE`
  - `apply_crosswalk(conn, sid, crosswalk) -> int` — fan asset-class rows out to tickers, `via_crosswalk=1`
  - `write_market_regime(conn, sid, regime_fields) -> None` — `regime_fields` maps signal_id → `market_regime` column
  - `write_ticker_scores(conn, sid) -> int`
  - `prune(conn, keep_days, now_iso) -> int` — cascades over ALL THREE child tables (the shared `screener_common.prune` handles one child, so calling it per-table would orphan the other two — the first call deletes the snapshot headers)
  - `INFORMATIONAL_SIGNALS = frozenset({"portfolio_holding"})` — excluded from vote counts entirely

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_composite_db_write.py
from sources.combiners.composite import db

NOW = "2026-07-06T21:00:00+00:00"
OLD = "2025-07-01T21:00:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    return conn


def _row(**kw):
    base = dict(signal_id="s1", grain="ticker", entity="AAPL",
                raw_value=1.0, score=1, obs_date="2026-07-03",
                staleness_days=3.0)
    base.update(kw)
    return base


def test_snapshot_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, signals_expected=5)
    db.finish_snapshot(conn, sid, ok=4, failed=1)
    got = conn.execute("SELECT captured_at, signals_expected, signals_ok,"
                       " signals_failed FROM snapshots WHERE id=?",
                       (sid,)).fetchone()
    assert got == (NOW, 5, 4, 1)


def test_write_signal_values_ignores_dupes(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    n = db.write_signal_values(conn, sid, [_row(), _row()])
    assert n == 1


def test_apply_crosswalk_fans_out(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 1)
    db.write_signal_values(conn, sid, [_row(
        signal_id="cftc_mm_extreme", grain="asset_class",
        entity="energy", score=2)])
    n = db.apply_crosswalk(conn, sid, {"energy": ["XLE", "XOM"]})
    assert n == 2
    got = conn.execute(
        "SELECT entity, score, via_crosswalk FROM signal_values"
        " WHERE snapshot_id=? AND grain='ticker' ORDER BY entity",
        (sid,)).fetchall()
    assert got == [("XLE", 2, 1), ("XOM", 2, 1)]


def test_write_ticker_scores_counts_and_portfolio(tmp_path):
    conn = _conn(tmp_path)
    sid = db.write_snapshot(conn, NOW, 4)
    db.write_signal_values(conn, sid, [
        _row(signal_id="a", entity="AAPL", score=2, staleness_days=3.0),
        _row(signal_id="b", entity="AAPL", score=-1, staleness_days=9.0),
        _row(signal_id="a", entity="XOM", score=1),
        _row(signal_id="portfolio_holding", entity="XOM", score=0),
        _row(signal_id="portfolio_holding", entity="DHR", score=0),
    ])
    db.write_ticker_scores(conn, sid)
    rows = {r[0]: r[1:] for r in conn.execute(
        "SELECT symbol, bullish, bearish, total, score_sum, coverage,"
        " worst_staleness_days, in_portfolio FROM ticker_scores"
        " WHERE snapshot_id=?", (sid,))}
    # 2 distinct non-informational ticker signals ran (a, b)
    assert rows["AAPL"] == (1, 1, 2, 1, 1.0, 9.0, 0)
    assert rows["XOM"] == (1, 0, 1, 1, 0.5, 3.0, 1)
    assert rows["DHR"] == (0, 0, 0, 0, 0.0, None, 1)  # held, no signals


def test_prune_cascades_all_children(tmp_path):
    conn = _conn(tmp_path)
    old = db.write_snapshot(conn, OLD, 1)
    db.write_signal_values(conn, old, [_row()])
    db.write_ticker_scores(conn, old)
    db.write_market_regime(conn, old, {})
    new = db.write_snapshot(conn, NOW, 1)
    assert db.prune(conn, keep_days=90, now_iso=NOW) == 1
    for t in ("signal_values", "market_regime", "ticker_scores"):
        assert conn.execute(
            f"SELECT COUNT(*) FROM {t} WHERE snapshot_id=?",
            (old,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_db_write.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'write_snapshot'`

- [ ] **Step 3: Write the implementation (append to db.py)**

```python
# Signals that inform but do not vote (score is structurally 0 and the
# signal is excluded from bullish/bearish/total and coverage).
INFORMATIONAL_SIGNALS = frozenset({"portfolio_holding"})


def write_snapshot(conn, now_iso: str, signals_expected: int) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, ?)",
        (now_iso, signals_expected))
    conn.commit()  # survive later per-signal rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid: int, ok: int, failed: int) -> None:
    conn.execute("UPDATE snapshots SET signals_ok=?, signals_failed=?"
                 " WHERE id=?", (ok, failed, sid))


def write_signal_values(conn, sid: int, rows) -> int:
    n = 0
    for r in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO signal_values (snapshot_id, signal_id,"
            " grain, entity, raw_value, score, obs_date, staleness_days,"
            " via_crosswalk) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, r["signal_id"], r["grain"], r["entity"], r["raw_value"],
             r["score"], r["obs_date"], r["staleness_days"],
             r.get("via_crosswalk", 0)))
        n += cur.rowcount
    return n


def apply_crosswalk(conn, sid: int, crosswalk: dict) -> int:
    """Fan each asset-class row out to its mapped tickers (via_crosswalk=1)."""
    n = 0
    for asset_class, tickers in crosswalk.items():
        rows = conn.execute(
            "SELECT signal_id, raw_value, score, obs_date, staleness_days"
            " FROM signal_values WHERE snapshot_id=? AND grain='asset_class'"
            " AND entity=? AND via_crosswalk=0",
            (sid, asset_class)).fetchall()
        for signal_id, raw, score, obs, stale in rows:
            for t in tickers:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO signal_values (snapshot_id,"
                    " signal_id, grain, entity, raw_value, score, obs_date,"
                    " staleness_days, via_crosswalk)"
                    " VALUES (?, ?, 'ticker', ?, ?, ?, ?, ?, 1)",
                    (sid, signal_id, t, raw, score, obs, stale))
                n += cur.rowcount
    return n


# Hand-set regime thresholds — documented judgment, not fitted. Tune here.
_REGIME_RISK_OFF_VIX = 25.0
_REGIME_RISK_ON_VIX = 20.0
_REGIME_HY_WIDE = 4.0


def _classify_regime(vals: dict) -> str:
    vix, hy = vals.get("vix"), vals.get("hy_spread")
    back = (vals.get("vix_backwardation") or 0) > 0
    if vix is None or hy is None:
        return "mixed"
    if vix >= _REGIME_RISK_OFF_VIX or (back and hy >= _REGIME_HY_WIDE):
        return "risk_off"
    if vix < _REGIME_RISK_ON_VIX and not back and hy < _REGIME_HY_WIDE:
        return "risk_on"
    return "mixed"


def write_market_regime(conn, sid: int, regime_fields: dict) -> None:
    """regime_fields: signal_id -> market_regime column; values come from
    that signal's market-grain raw_value in this snapshot."""
    vals, present = {}, 0
    for signal_id, col in regime_fields.items():
        row = conn.execute(
            "SELECT raw_value FROM signal_values WHERE snapshot_id=?"
            " AND signal_id=? AND entity='*'", (sid, signal_id)).fetchone()
        vals[col] = row[0] if row else None
        present += 1 if row else 0
    t10y2y = vals.get("t10y2y")
    back = vals.get("vix_backwardation")
    conn.execute(
        "INSERT INTO market_regime (snapshot_id, t10y2y, curve_inverted,"
        " hy_spread, vix, vix_backwardation, equity_pcr_pctile,"
        " in_fomc_blackout, imminent_high_impact, days_to_opex, rrp_change,"
        " tga_change, regime, inputs_expected, inputs_present)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, t10y2y,
         None if t10y2y is None else int(t10y2y < 0),
         vals.get("hy_spread"), vals.get("vix"),
         None if back is None else int(back > 0),
         vals.get("equity_pcr_pctile"),
         None if vals.get("in_fomc_blackout") is None
         else int(vals["in_fomc_blackout"]),
         None if vals.get("imminent_high_impact") is None
         else int(vals["imminent_high_impact"]),
         None if vals.get("days_to_opex") is None
         else int(vals["days_to_opex"]),
         vals.get("rrp_change"), vals.get("tga_change"),
         _classify_regime(vals), len(regime_fields), present))


def write_ticker_scores(conn, sid: int) -> int:
    """Counting, not weighting: bullish/bearish/total votes + score sum.
    Informational signals never vote; coverage = total / distinct voting
    ticker-grain signals present in this snapshot."""
    info = ",".join("?" * len(INFORMATIONAL_SIGNALS))
    args = (sid, *INFORMATIONAL_SIGNALS)
    applicable = conn.execute(
        f"SELECT COUNT(DISTINCT signal_id) FROM signal_values"
        f" WHERE snapshot_id=? AND grain='ticker'"
        f" AND signal_id NOT IN ({info})", args).fetchone()[0]
    conn.execute(
        f"INSERT INTO ticker_scores (snapshot_id, symbol, bullish, bearish,"
        f" total, score_sum, coverage, worst_staleness_days)"
        f" SELECT snapshot_id, entity,"
        f"  SUM(score > 0), SUM(score < 0), COUNT(*), SUM(score),"
        f"  CASE WHEN ? > 0 THEN CAST(COUNT(*) AS REAL) / ? END,"
        f"  MAX(staleness_days)"
        f" FROM signal_values WHERE snapshot_id=? AND grain='ticker'"
        f" AND signal_id NOT IN ({info}) GROUP BY entity",
        (applicable, applicable, *args))
    # Held tickers always appear, even with zero signals; then flag them.
    conn.execute(
        "INSERT OR IGNORE INTO ticker_scores (snapshot_id, symbol, coverage)"
        " SELECT snapshot_id, entity, 0.0 FROM signal_values"
        " WHERE snapshot_id=? AND signal_id='portfolio_holding'", (sid,))
    conn.execute(
        "UPDATE ticker_scores SET in_portfolio=1 WHERE snapshot_id=?"
        " AND symbol IN (SELECT entity FROM signal_values WHERE snapshot_id=?"
        " AND signal_id='portfolio_holding')", (sid, sid))
    return conn.execute("SELECT COUNT(*) FROM ticker_scores"
                        " WHERE snapshot_id=?", (sid,)).fetchone()[0]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Snapshot cascade over ALL child tables. Same fixed-width-timestamp
    caveat as screener_common.prune (which handles a single child table —
    calling it once per child would orphan the later ones, so the cascade
    is reimplemented here over the three children)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,))]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for table in ("signal_values", "market_regime", "ticker_scores"):
        conn.execute(f"DELETE FROM {table} WHERE snapshot_id IN ({qmarks})",
                     ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_db_write.py tests/test_composite_db_schema.py -v`
Expected: 9 passed. Note `test_write_ticker_scores_counts_and_portfolio` expects `write_market_regime` to accept `{}` — it does (inserts an all-NULL "mixed" row with 0/0 coverage).

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/composite/db.py tests/test_composite_db_write.py
git commit --no-gpg-sign -m "feat(composite): writers, crosswalk fan-out, combine functions, prune"
```

---

### Task 3: Views (`db.py` part 3)

**Files:**
- Modify: `sources/combiners/composite/db.py` (extend `_SCHEMA`)
- Test: `tests/test_composite_db_views.py`

**Interfaces:**
- Produces views: `v_latest_snapshot`, `v_latest_regime`, `v_latest_scorecard`, `v_flagged`, `v_score_history`, `v_signal_detail`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_composite_db_views.py
from sources.combiners.composite import db

T1 = "2026-07-05T21:00:00+00:00"
T2 = "2026-07-06T21:00:00+00:00"


def _seed(conn):
    s1 = db.write_snapshot(conn, T1, 1)
    s2 = db.write_snapshot(conn, T2, 1)
    for sid, score in ((s1, 1), (s2, 2)):
        db.write_signal_values(conn, sid, [
            dict(signal_id=f"sig{i}", grain="ticker", entity="GME",
                 raw_value=1.0, score=score, obs_date="2026-07-03",
                 staleness_days=1.0) for i in range(3)])
        db.write_signal_values(conn, sid, [
            dict(signal_id="sig0", grain="ticker", entity="AAPL",
                 raw_value=1.0, score=1, obs_date="2026-07-03",
                 staleness_days=1.0)])
        db.write_ticker_scores(conn, sid)
        db.write_market_regime(conn, sid, {})
    return s1, s2


def test_latest_views_pick_newest_snapshot(tmp_path):
    conn = db.connect(str(tmp_path / "c.db")); db.ensure_schema(conn)
    s1, s2 = _seed(conn)
    assert conn.execute("SELECT id FROM v_latest_snapshot").fetchone()[0] == s2
    assert conn.execute("SELECT COUNT(*) FROM v_latest_regime"
                        ).fetchone()[0] == 1
    assert {r[0] for r in conn.execute(
        "SELECT symbol FROM v_latest_scorecard")} == {"GME", "AAPL"}


def test_flagged_applies_both_thresholds(tmp_path):
    conn = db.connect(str(tmp_path / "c.db")); db.ensure_schema(conn)
    _seed(conn)
    # GME latest: 3 signals x score 2 -> score_sum 6, total 3 -> flagged
    # AAPL: 1 signal, score_sum 1 -> not flagged
    assert [r[0] for r in conn.execute(
        "SELECT symbol FROM v_flagged")] == ["GME"]


def test_score_history_spans_snapshots(tmp_path):
    conn = db.connect(str(tmp_path / "c.db")); db.ensure_schema(conn)
    _seed(conn)
    got = conn.execute(
        "SELECT captured_at, score_sum FROM v_score_history"
        " WHERE symbol='GME' ORDER BY captured_at").fetchall()
    assert got == [(T1, 3), (T2, 6)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_db_views.py -v`
Expected: FAIL with `sqlite3.OperationalError: no such table: v_latest_snapshot`

- [ ] **Step 3: Append to `_SCHEMA` in db.py (inside the same string, after the tables)**

```sql
CREATE VIEW IF NOT EXISTS v_latest_snapshot AS
SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1;

CREATE VIEW IF NOT EXISTS v_latest_regime AS
SELECT m.* FROM market_regime m
JOIN v_latest_snapshot l ON m.snapshot_id = l.id;

CREATE VIEW IF NOT EXISTS v_latest_scorecard AS
SELECT t.* FROM ticker_scores t
JOIN v_latest_snapshot l ON t.snapshot_id = l.id;

-- Flag thresholds are hand-set and tunable; edit here (|score_sum| >= 4
-- with at least 3 voting signals present).
CREATE VIEW IF NOT EXISTS v_flagged AS
SELECT * FROM v_latest_scorecard
WHERE ABS(score_sum) >= 4 AND total >= 3;

-- The future paper-trading dataset: composite over time.
CREATE VIEW IF NOT EXISTS v_score_history AS
SELECT s.captured_at, t.symbol, t.bullish, t.bearish, t.total,
       t.score_sum, t.coverage, t.in_portfolio
FROM ticker_scores t JOIN snapshots s ON s.id = t.snapshot_id;

CREATE VIEW IF NOT EXISTS v_signal_detail AS
SELECT v.* FROM signal_values v
JOIN v_latest_snapshot l ON v.snapshot_id = l.id;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_db_views.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/composite/db.py tests/test_composite_db_views.py
git commit --no-gpg-sign -m "feat(composite): latest/flagged/history views"
```

---

### Task 4: Signal catalog (`catalog.py`)

**Files:**
- Create: `sources/combiners/composite/catalog.py`
- Test: `tests/test_composite_catalog.py`

**Interfaces:**
- Produces: `SIGNALS` (list of dicts: `signal_id, db, grain, staleness_budget_days, sql`), `REGIME_FIELDS` (signal_id → market_regime column), `CROSSWALK` (asset class → tickers), `select_ids(only, exclude, add) -> list[dict]`.
- Every SQL runs with the source attached as `src` and MAY reference `:today`. Row shape: `(entity, raw_value, score, obs_date)`.

All table/view/column names below were live-verified against the real `data/` DBs on 2026-07-06 (EIA series ids, USDA regions, reddit `filter` values, cboe `vix_daily`/`pcr_daily`, cftc `markets` join, fomc `payload.$.window_end`, portfolio `positions.quantity`). If a source errors during the Task 8 smoke run, re-verify against that DB before changing SQL.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_composite_catalog.py
import pytest

from sources.combiners.composite import catalog

KNOWN_DBS = {
    "fred.db", "cboe_stats.db", "fomc.db", "econ_calendar.db",
    "market_calendar.db", "nyfed.db", "treasury.db", "cftc.db", "eia.db",
    "usda.db", "short_interest.db", "short_volume.db", "ftd.db",
    "reddit.db", "stocks.db", "edgar.db", "portfolio.db",
}
ASSET_CLASSES = {"ags", "rates", "energy", "softs", "metals", "fx",
                 "equity_index"}


def test_signal_ids_unique_and_wellformed():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert len(ids) == len(set(ids))
    for s in catalog.SIGNALS:
        assert s["grain"] in ("market", "asset_class", "ticker")
        assert s["db"] in KNOWN_DBS
        assert s["staleness_budget_days"] >= 0
        assert "src." in s["sql"]          # reads the attached alias
        assert "calendar_now" not in s["sql"]  # one-clock rule


def test_regime_fields_reference_market_signals():
    market_ids = {s["signal_id"] for s in catalog.SIGNALS
                  if s["grain"] == "market"}
    assert set(catalog.REGIME_FIELDS) <= market_ids


def test_crosswalk_classes_are_known():
    assert set(catalog.CROSSWALK) <= ASSET_CLASSES
    assert "fx" not in catalog.CROSSWALK   # direction incoherent; excluded


def test_select_ids():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert [s["signal_id"] for s in catalog.select_ids(None, None, None)] == ids
    only = catalog.select_ids([ids[0]], None, None)
    assert [s["signal_id"] for s in only] == [ids[0]]
    excl = catalog.select_ids(None, [ids[0]], None)
    assert ids[0] not in [s["signal_id"] for s in excl]
    with pytest.raises(ValueError):
        catalog.select_ids(["nope"], None, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` on catalog

- [ ] **Step 3: Write the catalog**

```python
# sources/combiners/composite/catalog.py
"""Curated signal catalog: which source signals feed the composite, how
each normalizes to a -2..+2 score, and how asset classes map to tickers.

Every SQL runs against ONE source DB attached read-only as `src`, with
:today (YYYY-MM-DD) bound by the run. Required row shape:
    (entity, raw_value, score, obs_date)
entity is '*' (market), an asset class, or a ticker. score is an integer
-2..+2, positive = bullish for the entity — contrarian readings (crowded
shorts, panicky put buying) are applied HERE, not by consumers.

One-clock rule: never reference a source's calendar_now-dependent views
(monitor v_upcoming/v_imminent, treasury.v_upcoming_auctions, fred.v_asof);
query base tables with :today instead.
"""

SIGNALS = [
    # ------------------------------------------------ market grain ----
    {
        "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', value,
                   CASE WHEN value < 0 THEN -1 ELSE 0 END,
                   date
            FROM src.observations
            WHERE series_id = 'T10Y2Y' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "fred_hy_spread", "db": "fred.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', value,
                   CASE WHEN value >= 5.0 THEN -2
                        WHEN value >= 4.0 THEN -1
                        WHEN value < 3.5 THEN 1 ELSE 0 END,
                   date
            FROM src.observations
            WHERE series_id = 'BAMLH0A0HYM2' AND value IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "cboe_vix", "db": "cboe_stats.db", "grain": "market",
        "staleness_budget_days": 5,
        "sql": """
            SELECT '*', close,
                   CASE WHEN close >= 30 THEN -2
                        WHEN close >= 25 THEN -1
                        WHEN close < 15 THEN 1 ELSE 0 END,
                   date
            FROM src.vix_daily WHERE close IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        "signal_id": "cboe_vix_backwardation", "db": "cboe_stats.db",
        "grain": "market", "staleness_budget_days": 5,
        "sql": """
            SELECT '*', close - vix3m,
                   CASE WHEN close > vix3m THEN -2 ELSE 0 END,
                   date
            FROM src.vix_daily
            WHERE close IS NOT NULL AND vix3m IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """,
    },
    {
        # Contrarian: panicky put buying (high PCR percentile) is bullish.
        "signal_id": "cboe_equity_pcr", "db": "cboe_stats.db",
        "grain": "market", "staleness_budget_days": 5,
        "sql": """
            WITH latest AS (
                SELECT date, equity_pcr FROM src.pcr_daily
                WHERE equity_pcr IS NOT NULL ORDER BY date DESC LIMIT 1),
            hist AS (
                SELECT equity_pcr FROM src.pcr_daily
                WHERE equity_pcr IS NOT NULL ORDER BY date DESC LIMIT 252),
            p AS (
                SELECT l.date AS date,
                       100.0 * (SELECT COUNT(*) FROM hist h
                                WHERE h.equity_pcr <= l.equity_pcr)
                             / (SELECT COUNT(*) FROM hist) AS pctile
                FROM latest l)
            SELECT '*', pctile,
                   CASE WHEN pctile >= 90 THEN 2 WHEN pctile >= 75 THEN 1
                        WHEN pctile <= 10 THEN -2 WHEN pctile <= 25 THEN -1
                        ELSE 0 END,
                   date
            FROM p
        """,
    },
    {
        # Gate, not direction: score 0; regime tier reads the raw flag.
        "signal_id": "fomc_blackout", "db": "fomc.db", "grain": "market",
        "staleness_budget_days": 0,
        "sql": """
            SELECT '*',
                   EXISTS(SELECT 1 FROM src.events e
                          WHERE e.event_type = 'fomc_blackout_start'
                            AND e.event_date <= :today
                            AND json_extract(e.payload, '$.window_end')
                                >= :today),
                   0, :today
        """,
    },
    {
        "signal_id": "econ_imminent", "db": "econ_calendar.db",
        "grain": "market", "staleness_budget_days": 0,
        "sql": """
            SELECT '*', COUNT(*), 0, :today
            FROM src.events
            WHERE event_date >= :today
              AND event_date <= date(:today, '+3 days')
        """,
    },
    {
        "signal_id": "mcal_days_to_opex", "db": "market_calendar.db",
        "grain": "market", "staleness_budget_days": 0,
        "sql": """
            SELECT '*',
                   CAST(julianday(MIN(event_date)) - julianday(:today)
                        AS INTEGER),
                   0, :today
            FROM src.events
            WHERE event_type IN ('opex', 'quad_witching')
              AND event_date >= :today
        """,
    },
    {
        # Falling RRP take-up releases liquidity into markets: bullish.
        "signal_id": "nyfed_rrp", "db": "nyfed.db", "grain": "market",
        "staleness_budget_days": 5,
        "sql": """
            SELECT '*', change_vs_prior,
                   CASE WHEN change_vs_prior < 0 THEN 1
                        WHEN change_vs_prior > 0 THEN -1 ELSE 0 END,
                   operation_date
            FROM src.v_rrp_trend
            WHERE change_vs_prior IS NOT NULL
            ORDER BY operation_date DESC LIMIT 1
        """,
    },
    {
        # Rising TGA drains liquidity from markets: bearish.
        "signal_id": "tsy_tga", "db": "treasury.db", "grain": "market",
        "staleness_budget_days": 7,
        "sql": """
            SELECT '*', wow_change,
                   CASE WHEN wow_change < 0 THEN 1
                        WHEN wow_change > 0 THEN -1 ELSE 0 END,
                   record_date
            FROM src.v_tga_trend
            WHERE wow_change IS NOT NULL
            ORDER BY record_date DESC LIMIT 1
        """,
    },
    # ------------------------------------------- asset-class grain ----
    {
        # Contrarian at extremes: washed-out managed money = bullish.
        "signal_id": "cftc_mm_extreme", "db": "cftc.db",
        "grain": "asset_class", "staleness_budget_days": 12,
        "sql": """
            SELECT m.asset_class, AVG(c.cot_index),
                   CASE WHEN AVG(c.cot_index) <= 10 THEN 2
                        WHEN AVG(c.cot_index) <= 20 THEN 1
                        WHEN AVG(c.cot_index) >= 90 THEN -2
                        WHEN AVG(c.cot_index) >= 80 THEN -1 ELSE 0 END,
                   MAX(c.report_date)
            FROM src.v_disagg_cot_index_latest c
            JOIN src.markets m ON m.code = c.code
            WHERE c.cot_index IS NOT NULL
            GROUP BY m.asset_class
        """,
    },
    {
        "signal_id": "cftc_lev_extreme", "db": "cftc.db",
        "grain": "asset_class", "staleness_budget_days": 12,
        "sql": """
            SELECT m.asset_class, AVG(c.cot_index),
                   CASE WHEN AVG(c.cot_index) <= 10 THEN 2
                        WHEN AVG(c.cot_index) <= 20 THEN 1
                        WHEN AVG(c.cot_index) >= 90 THEN -2
                        WHEN AVG(c.cot_index) >= 80 THEN -1 ELSE 0 END,
                   MAX(c.report_date)
            FROM src.v_tff_cot_index_latest c
            JOIN src.markets m ON m.code = c.code
            WHERE c.cot_index IS NOT NULL
            GROUP BY m.asset_class
        """,
    },
    {
        # Crude build = bearish energy; draw = bullish.
        "signal_id": "eia_crude_stocks", "db": "eia.db",
        "grain": "asset_class", "staleness_budget_days": 10,
        "sql": """
            SELECT 'energy', change_pct,
                   CASE WHEN change_pct <= -2.0 THEN 1
                        WHEN change_pct >= 2.0 THEN -1 ELSE 0 END,
                   latest_period
            FROM src.v_weekly_change WHERE series_id = 'WCESTUS1'
        """,
    },
    {
        "signal_id": "eia_natgas_storage", "db": "eia.db",
        "grain": "asset_class", "staleness_budget_days": 10,
        "sql": """
            SELECT 'energy', change_pct,
                   CASE WHEN change_pct <= -2.0 THEN 1
                        WHEN change_pct >= 2.0 THEN -1 ELSE 0 END,
                   latest_period
            FROM src.v_weekly_change
            WHERE series_id = 'NW2_EPG0_SWO_R48_BCF'
        """,
    },
    {
        # Tight US grain stocks-to-use = bullish ags. WASDE is monthly and
        # market-year keyed; obs_date is :today by construction (budget 35).
        "signal_id": "usda_stocks_to_use", "db": "usda.db",
        "grain": "asset_class", "staleness_budget_days": 35,
        "sql": """
            SELECT 'ags', AVG(stocks_to_use),
                   CASE WHEN AVG(stocks_to_use) < 0.10 THEN 1 ELSE 0 END,
                   :today
            FROM src.v_wasde_stocks_to_use
            WHERE region = 'United States'
              AND commodity IN ('Corn', 'Soybeans', 'Wheat')
              AND stocks_to_use IS NOT NULL
              AND market_year = (SELECT MAX(market_year)
                                 FROM src.v_wasde_stocks_to_use
                                 WHERE region = 'United States')
        """,
    },
    # ------------------------------------------------ ticker grain ----
    {
        # Crowded shorts = squeeze fuel (contrarian bullish). The source
        # view pre-filters days_to_cover >= 5 / ADV >= 100k, but at >= 5
        # this blankets ~1,600 tickers and skews the whole composite
        # bullish (measured 2026-07-06); score only genuine extremes.
        # FAMILY OVERLAP: this and ftd_persistent both read squeeze fuel —
        # a flag driven by only these two is one phenomenon double-counted.
        "signal_id": "si_days_to_cover", "db": "short_interest.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, days_to_cover,
                   CASE WHEN days_to_cover >= 20 THEN 2 ELSE 1 END,
                   settlement_date
            FROM src.v_high_days_to_cover
            WHERE days_to_cover >= 10
        """,
    },
    {
        # NEW shorting pressure (vs own 6-period base) reads as informed
        # bears arriving: bearish. Distinct from the level read above.
        "signal_id": "si_spike", "db": "short_interest.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, base_ratio,
                   CASE WHEN base_ratio >= 2.0 THEN -2 ELSE -1 END,
                   settlement_date
            FROM src.v_short_interest_spikes
            WHERE base_ratio >= 1.5
        """,
    },
    {
        "signal_id": "sv_ratio_spike", "db": "short_volume.db",
        "grain": "ticker", "staleness_budget_days": 4,
        "sql": """
            SELECT symbol, spike_ratio,
                   CASE WHEN spike_ratio >= 1.6 THEN -2 ELSE -1 END,
                   date
            FROM src.v_ratio_spikes WHERE spike_ratio >= 1.3
        """,
    },
    {
        # Persistent fails-to-deliver = delivery stress / squeeze fuel.
        # FAMILY OVERLAP with si_days_to_cover — see the note there.
        "signal_id": "ftd_persistent", "db": "ftd.db",
        "grain": "ticker", "staleness_budget_days": 25,
        "sql": """
            SELECT symbol, streak_days,
                   CASE WHEN streak_days >= 10 THEN 2 ELSE 1 END,
                   streak_end
            FROM src.v_persistent
            WHERE active = 1 AND symbol IS NOT NULL
        """,
    },
    {
        # Attention momentum: mention spikes with real volume behind them.
        "signal_id": "reddit_trending", "db": "reddit.db",
        "grain": "ticker", "staleness_budget_days": 2,
        "sql": """
            SELECT ticker, mention_pct_change,
                   CASE WHEN mention_pct_change >= 3.0 THEN 2 ELSE 1 END,
                   substr(captured_at, 1, 10)
            FROM src.v_signals
            WHERE filter = 'all-stocks' AND mentions >= 50
              AND mention_pct_change >= 1.0
        """,
    },
    {
        # Mean-reversion read on RSI extremes, liquid names only.
        "signal_id": "stocks_rsi", "db": "stocks.db",
        "grain": "ticker", "staleness_budget_days": 4,
        "sql": """
            SELECT symbol, rsi,
                   CASE WHEN rsi <= 20 THEN 2 WHEN rsi <= 30 THEN 1
                        WHEN rsi >= 80 THEN -2 ELSE -1 END,
                   priceDate
            FROM src.v_latest
            WHERE rsi IS NOT NULL AND rsi > 0
              AND (rsi <= 30 OR rsi >= 70)
              AND dollarVolume >= 10000000
        """,
    },
    {
        # Form 4 cluster = attention flag; direction unknown at index
        # level (buys and sells both file Form 4), hence score 0.
        "signal_id": "edgar_insider", "db": "edgar.db",
        "grain": "ticker", "staleness_budget_days": 5,
        "sql": """
            SELECT ticker, COUNT(*), 0, MAX(filed_date)
            FROM src.v_tickered
            WHERE bucket = 'insider' AND ticker IS NOT NULL
            GROUP BY ticker HAVING COUNT(*) >= 3
        """,
    },
    {
        # Live holdings: informational only (never votes; sets in_portfolio).
        "signal_id": "portfolio_holding", "db": "portfolio.db",
        "grain": "ticker", "staleness_budget_days": 3,
        "sql": """
            SELECT p.symbol, p.quantity, 0, substr(s.captured_at, 1, 10)
            FROM src.positions p
            JOIN src.snapshots s ON s.id = p.snapshot_id
            WHERE p.snapshot_id = (SELECT id FROM src.snapshots
                                   ORDER BY captured_at DESC, id DESC
                                   LIMIT 1)
        """,
    },
]

# market-grain signal -> market_regime column (raw_value is copied over;
# derived flags like curve_inverted are computed in db.write_market_regime).
REGIME_FIELDS = {
    "fred_curve": "t10y2y",
    "fred_hy_spread": "hy_spread",
    "cboe_vix": "vix",
    "cboe_vix_backwardation": "vix_backwardation",
    "cboe_equity_pcr": "equity_pcr_pctile",
    "fomc_blackout": "in_fomc_blackout",
    "econ_imminent": "imminent_high_impact",
    "mcal_days_to_opex": "days_to_opex",
    "nyfed_rrp": "rrp_change",
    "tsy_tga": "tga_change",
}

# Asset class -> liquid proxy tickers. Curated judgment; 'fx' is scored
# but deliberately NOT mapped (net-long EUR != net-long UUP).
CROSSWALK = {
    "energy": ["XLE", "XOM", "CVX", "USO"],
    "metals": ["GDX", "GLD", "SLV", "FCX", "COPX"],
    "ags": ["DBA", "CORN", "SOYB", "WEAT"],
    "softs": ["DBA"],
    "rates": ["TLT", "IEF"],
    "equity_index": ["SPY", "QQQ", "IWM"],
}


def select_ids(only=None, exclude=None, add=None):
    """Standard catalog selection: --only narrows, --add extends an --only
    list, --exclude removes. Returns catalog entries in catalog order."""
    ids = [s["signal_id"] for s in SIGNALS]
    sel = list(only) if only else list(ids)
    if add:
        sel += [a for a in add if a not in sel]
    if exclude:
        sel = [s for s in sel if s not in exclude]
    unknown = sorted(set(sel) - set(ids))
    if unknown:
        raise ValueError(f"unknown signal ids: {', '.join(unknown)}")
    chosen = set(sel)
    return [s for s in SIGNALS if s["signal_id"] in chosen]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_catalog.py -v`
Expected: 4 passed

- [ ] **Step 5: Live-verify every extraction SQL against the real data/ DBs**

Run this harness (reads only; composite.db not involved):

```bash
uv run python - <<'EOF'
import sqlite3
from sources.combiners.composite import catalog
today = "2026-07-06"
for s in catalog.SIGNALS:
    conn = sqlite3.connect(":memory:", uri=True)
    try:
        conn.execute("ATTACH DATABASE ? AS src",
                     (f"file:data/{s['db']}?mode=ro",))
        params = {"today": today} if ":today" in s["sql"] else {}
        rows = conn.execute(s["sql"], params).fetchall()
        print(f"{s['signal_id']:24s} {len(rows):5d} rows   e.g. {rows[:2]}")
    except Exception as e:
        print(f"{s['signal_id']:24s} ERROR {type(e).__name__}")
    finally:
        conn.close()
EOF
```

Expected: every signal prints a row count (0 rows is acceptable for spike-type signals on a quiet day; `edgar_insider` prints ERROR FileNotFoundError-equivalent `OperationalError` until the first 8:30pm edgar run creates `data/edgar.db` — that is the skip-and-continue path, acceptable). Any OTHER error: fix the SQL against that DB's actual schema before proceeding — do not paper over it.

- [ ] **Step 6: Commit**

```bash
git add sources/combiners/composite/catalog.py tests/test_composite_catalog.py
git commit --no-gpg-sign -m "feat(composite): curated signal catalog, regime fields, crosswalk"
```

---

### Task 5: Extraction (`fetch.py`)

**Files:**
- Create: `sources/combiners/composite/fetch.py`
- Test: `tests/test_composite_fetch.py`

**Interfaces:**
- Consumes: catalog entry dicts (Task 4 shape).
- Produces: `attach_ro(conn, db_path, alias="src")` (raises `FileNotFoundError` if missing), `detach(conn, alias="src")`, `staleness_days(today, obs_date) -> float|None`, `extract(conn, signal, today) -> list[dict]` (dicts ready for `db.write_signal_values`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_composite_fetch.py
import sqlite3

import pytest

from sources.combiners.composite import fetch
from sources.screeners.fred_screener import db as fred_db

SIG = {
    "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 7,
    "sql": ("SELECT '*', value, CASE WHEN value < 0 THEN -1 ELSE 0 END,"
            " date FROM src.observations WHERE series_id='T10Y2Y'"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 1"),
}


def _mini_fred(tmp_path):
    """Real fred schema via the source's own ensure_schema — combiner
    tests break loudly if the source schema drifts."""
    path = tmp_path / "fred.db"
    conn = fred_db.connect(str(path))
    fred_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO observations (series_id, date, value) VALUES (?,?,?)",
        [("T10Y2Y", "2026-07-01", 0.35), ("T10Y2Y", "2026-07-03", -0.10)])
    conn.commit()
    conn.close()
    return str(path)


def test_attach_ro_missing_file_raises(tmp_path):
    conn = sqlite3.connect(":memory:", uri=True)
    with pytest.raises(FileNotFoundError):
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))


def test_attach_is_readonly(tmp_path):
    path = _mini_fred(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO src.observations (series_id, date, value)"
                     " VALUES ('X', '2026-01-01', 1)")


def test_extract_normalizes_rows(tmp_path):
    path = _mini_fred(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    rows = fetch.extract(conn, SIG, today="2026-07-06")
    assert rows == [{
        "signal_id": "fred_curve", "grain": "market", "entity": "*",
        "raw_value": -0.10, "score": -1, "obs_date": "2026-07-03",
        "staleness_days": 3,
    }]
    fetch.detach(conn)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT 1 FROM src.observations")


def test_staleness_days():
    assert fetch.staleness_days("2026-07-06", "2026-07-03") == 3
    assert fetch.staleness_days("2026-07-06", None) is None
    assert fetch.staleness_days("2026-07-06", "not-a-date") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError` on fetch

- [ ] **Step 3: Write the implementation**

```python
# sources/combiners/composite/fetch.py
"""Pure extraction against ATTACHed source DBs. No network anywhere in
this package — the combiner's external feed is the local data/ dir."""
import os
from datetime import date


def attach_ro(conn, db_path: str, alias: str = "src") -> None:
    """Attach a source DB read-only. The connection must have been opened
    with uri=True or the mode=ro URI is rejected by SQLite."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn.execute(f"ATTACH DATABASE ? AS {alias}",
                 (f"file:{db_path}?mode=ro",))


def detach(conn, alias: str = "src") -> None:
    conn.execute(f"DETACH DATABASE {alias}")


def staleness_days(today: str, obs_date):
    try:
        return (date.fromisoformat(today)
                - date.fromisoformat(str(obs_date)[:10])).days
    except (TypeError, ValueError):
        return None


def extract(conn, signal: dict, today: str) -> list:
    """Run one catalog signal's SQL; normalize to write_signal_values rows.
    Rows with a NULL entity or score are dropped (a LEFT-JOIN-shaped miss,
    not an error)."""
    params = {"today": today} if ":today" in signal["sql"] else {}
    out = []
    for entity, raw_value, score, obs_date in conn.execute(
            signal["sql"], params):
        if entity is None or score is None:
            continue
        out.append({
            "signal_id": signal["signal_id"],
            "grain": signal["grain"],
            "entity": str(entity),
            "raw_value": raw_value,
            "score": max(-2, min(2, int(score))),
            "obs_date": obs_date,
            "staleness_days": staleness_days(today, obs_date),
        })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_fetch.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add sources/combiners/composite/fetch.py tests/test_composite_fetch.py
git commit --no-gpg-sign -m "feat(composite): read-only attach + extraction seam"
```

---

### Task 6: Orchestration (`run.py`)

**Files:**
- Create: `sources/combiners/composite/run.py`
- Test: `tests/test_composite_run.py`

**Interfaces:**
- Consumes: `catalog.select_ids/CROSSWALK/REGIME_FIELDS`, `fetch.attach_ro/detach/extract`, all `db.*` writers.
- Produces: `run(db_path, db_dir, now_iso=None, only=None, exclude=None, add=None, keep_days=None, signals=None) -> (sid, ok, failed)`; `main(argv)`. The `signals=` parameter is a test seam that bypasses the catalog.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_composite_run.py
import sqlite3

from sources.combiners.composite import db, run as run_mod
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.portfolio_screener import db as pf_db

NOW = "2026-07-06T21:00:00+00:00"

FRED_SIG = {
    "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 7,
    "sql": ("SELECT '*', value, CASE WHEN value < 0 THEN -1 ELSE 0 END,"
            " date FROM src.observations WHERE series_id='T10Y2Y'"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 1"),
}
MISSING_SIG = {
    "signal_id": "ghost", "db": "nope.db", "grain": "market",
    "staleness_budget_days": 0, "sql": "SELECT '*', 1, 0, :today",
}
BROKEN_SIG = {
    "signal_id": "broken", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 0, "sql": "SELECT nope FROM src.does_not_exist",
}
PF_SIG = {
    "signal_id": "portfolio_holding", "db": "portfolio.db",
    "grain": "ticker", "staleness_budget_days": 3,
    "sql": ("SELECT p.symbol, p.quantity, 0, substr(s.captured_at, 1, 10)"
            " FROM src.positions p JOIN src.snapshots s ON s.id ="
            " p.snapshot_id WHERE p.snapshot_id = (SELECT id FROM"
            " src.snapshots ORDER BY captured_at DESC, id DESC LIMIT 1)"),
}


def _mini_fred(dirpath):
    conn = fred_db.connect(str(dirpath / "fred.db"))
    fred_db.ensure_schema(conn)
    conn.execute("INSERT INTO observations (series_id, date, value)"
                 " VALUES ('T10Y2Y', '2026-07-03', -0.10)")
    conn.commit(); conn.close()


def _mini_portfolio(dirpath):
    conn = pf_db.connect(str(dirpath / "portfolio.db"))
    pf_db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (captured_at, position_count)"
                 " VALUES (?, 1)", (NOW,))
    conn.execute("INSERT INTO positions (snapshot_id, symbol, quantity)"
                 " VALUES (1, 'XOM', 10)")
    conn.commit(); conn.close()


def test_run_happy_path_writes_all_tiers(tmp_path, capsys):
    _mini_fred(tmp_path); _mini_portfolio(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(out, str(tmp_path), now_iso=NOW,
                                  signals=[FRED_SIG, PF_SIG])
    assert (ok, failed) == (2, 0)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT t10y2y, curve_inverted FROM v_latest_regime"
                        ).fetchone() == (-0.10, 1)
    assert conn.execute("SELECT in_portfolio FROM v_latest_scorecard"
                        " WHERE symbol='XOM'").fetchone() == (1,)


def test_run_skips_missing_db_and_broken_sql(tmp_path, capsys):
    _mini_fred(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(
        out, str(tmp_path), now_iso=NOW,
        signals=[FRED_SIG, MISSING_SIG, BROKEN_SIG])
    assert (ok, failed) == (1, 2)
    err = capsys.readouterr().out
    assert "FileNotFoundError" in err and "OperationalError" in err
    # never leak details beyond the exception type name
    assert "does_not_exist" not in err
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT signals_ok, signals_failed FROM snapshots"
                        ).fetchone() == (1, 2)


def test_run_never_writes_to_sources(tmp_path):
    _mini_fred(tmp_path)
    before = (tmp_path / "fred.db").read_bytes()
    run_mod.run(str(tmp_path / "composite.db"), str(tmp_path),
                now_iso=NOW, signals=[FRED_SIG])
    assert (tmp_path / "fred.db").read_bytes() == before


def test_main_argv_roundtrip(tmp_path, capsys):
    _mini_fred(tmp_path)
    run_mod.main(["--db", str(tmp_path / "composite.db"),
                  "--db-dir", str(tmp_path), "--only", "fred_curve"])
    out = capsys.readouterr().out
    assert "composite snapshot" in out and "1 signals ok" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_composite_run.py -v`
Expected: FAIL with `ModuleNotFoundError` on run

- [ ] **Step 3: Write the implementation**

```python
# sources/combiners/composite/run.py
"""Combine per-source signals into data/composite.db.

Two-phase: (1) per-source sequential read-only ATTACH -> extract ->
DETACH (SQLite caps attached DBs at 10, so never all-at-once); (2) build
market_regime + ticker_scores inside composite.db with nothing attached.
Time enters only as now_iso; extraction binds the run's own :today (the
one-clock rule) and never reads calendar_now-dependent source views.
Skip-and-continue per signal; failures print exception type names only."""
import argparse
import os
from datetime import datetime, timezone

from sources.combiners.composite import catalog, db, fetch


def run(db_path, db_dir, now_iso=None, only=None, exclude=None, add=None,
        keep_days=None, signals=None):
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = now_iso[:10]
    if signals is None:
        signals = catalog.select_ids(only, exclude, add)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso, len(signals))
        ok = failed = 0
        by_db = {}
        for s in signals:
            by_db.setdefault(s["db"], []).append(s)
        for db_file, sigs in by_db.items():
            path = os.path.join(db_dir, db_file)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                print(f"skip {db_file}: {type(e).__name__}")
                failed += len(sigs)
                continue
            try:
                for sig in sigs:
                    try:
                        rows = fetch.extract(conn, sig, today)
                        db.write_signal_values(conn, sid, rows)
                        conn.commit()
                        ok += 1
                    except Exception as e:
                        conn.rollback()
                        print(f"skip {sig['signal_id']}:"
                              f" {type(e).__name__}")
                        failed += 1
            finally:
                fetch.detach(conn)
        db.apply_crosswalk(conn, sid, catalog.CROSSWALK)
        db.write_market_regime(conn, sid, catalog.REGIME_FIELDS)
        db.write_ticker_scores(conn, sid)
        db.finish_snapshot(conn, sid, ok, failed)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, ok, failed


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="composite",
        description="Combine per-source signals into a market-regime row"
                    " + per-ticker scorecard (reads other data/ DBs"
                    " read-only)")
    p.add_argument("--db", default="composite.db")
    p.add_argument("--db-dir", default="data",
                   help="directory holding the source DBs")
    p.add_argument("--only", action="append")
    p.add_argument("--exclude", action="append")
    p.add_argument("--add", action="append")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, ok, failed = run(a.db, a.db_dir, only=a.only, exclude=a.exclude,
                          add=a.add, keep_days=a.keep_days)
    print(f"composite snapshot {sid}: {ok} signals ok, {failed} failed,"
          f" into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_composite_run.py -v`
Expected: 4 passed. If `test_run_never_writes_to_sources` fails on byte
comparison: the mini fred DB is WAL-mode — close it fully in the fixture
(the fixture does) and compare again; a genuinely read-only attach never
touches the file.

- [ ] **Step 5: Run the whole composite suite + full repo suite**

Run: `uv run pytest tests/test_composite_run.py tests/test_composite_fetch.py tests/test_composite_catalog.py tests/test_composite_db_schema.py tests/test_composite_db_write.py tests/test_composite_db_views.py -v && uv run pytest -q`
Expected: all composite tests pass; full suite stays green.

- [ ] **Step 6: Commit**

```bash
git add sources/combiners/composite/run.py tests/test_composite_run.py
git commit --no-gpg-sign -m "feat(composite): two-phase run with skip-and-continue"
```

---

### Task 7: Registry

**Files:**
- Modify: `registry.py` (import block + REGISTRY dict)
- Modify: `tests/test_registry.py` (append)

**Interfaces:**
- Consumes: `sources.combiners.composite.run.main`.
- Produces: `main.py composite [args...]` dispatches to it.

- [ ] **Step 1: Write the failing test (append to tests/test_registry.py)**

```python
def test_dispatch_lists_composite():
    import registry
    assert "composite" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_registry.py::test_dispatch_lists_composite -v`
Expected: FAIL with `AssertionError`

- [ ] **Step 3: Register**

In `registry.py`, after the portfolio import (line 23):

```python
from sources.combiners.composite.run import main as composite_main
```

and as the last REGISTRY entry (after `"portfolio"`):

```python
    "composite": composite_main,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: all pass, including the new one

- [ ] **Step 5: Commit**

```bash
git add registry.py tests/test_registry.py
git commit --no-gpg-sign -m "feat(composite): register composite dispatcher"
```

---

### Task 8: Smoke run on real data, schedule, docs

**Files:**
- Modify: `deploy/launchd/install.py` (JOBS dict), `docs/SCHEDULE.md`, `CLAUDE.md`
- No new tests (deploy script has none; keep parity)

**Interfaces:**
- Consumes: the shipped `composite` dispatcher.

- [ ] **Step 1: Smoke run against real data/**

```bash
uv run python main.py composite --db data/composite.db --keep-days 365
sqlite3 data/composite.db "SELECT * FROM v_latest_regime"
sqlite3 data/composite.db "SELECT COUNT(*) FROM v_latest_scorecard"
sqlite3 data/composite.db "SELECT score_sum, COUNT(*) FROM v_latest_scorecard GROUP BY score_sum ORDER BY score_sum"
sqlite3 data/composite.db "SELECT * FROM v_flagged LIMIT 10"
```

Expected: `composite snapshot 1: N signals ok, M failed` where failures are only known-absent sources (e.g. `edgar.db` before its first evening run). `v_latest_regime` shows one row with plausible values (VIX in the teens, curve positive as of 2026-07). Investigate ANY other failure before continuing — do not ship a combiner that silently half-runs.

**Sanity-check the score distribution** (the adversarial review caught the original catalog skewing structurally bullish here): the `score_sum` histogram should be roughly centered on 0 with thin tails, and the scorecard should be well under ~1,500 rows. `v_flagged` returning 0 rows on a quiet day is CORRECT — flags should be rare. If the distribution looks lopsided or a single signal dominates row counts (`SELECT signal_id, COUNT(*) FROM v_signal_detail GROUP BY signal_id`), revisit that signal's thresholds in catalog.py before installing the schedule.

- [ ] **Step 2: Add the launchd job**

In `deploy/launchd/install.py`, in the JOBS dict, insert before the `daily-summary` entry (nightly at **9:05pm** Phoenix — edgar starts 8:30pm and on failure retries after a 15-min sleep, so 9:00pm can race its retry; 9:05 clears it while leaving 10 min before the 9:15 summary. WAL keeps a concurrent read consistent regardless — worst case is same-night edgar freshness. Every day, matching daily-summary, so weekend runs pick up Friday-published weeklies):

```python
    # -- combine (after all collectors incl. edgar's retry window;
    #    before the nightly summary) --
    "composite": (job("composite", "--keep-days", "365"),
                  weekly(range(7), 21, 5)),
```

Then install and verify:

```bash
uv run python deploy/launchd/install.py --dry-run   # inspect plist output
uv run python deploy/launchd/install.py
launchctl list | grep com.tradingbot.composite
```

Expected: `com.tradingbot.composite: loaded` and the label appears in `launchctl list`.

- [ ] **Step 3: Update docs**

`docs/SCHEDULE.md`: add a row to the job table — `composite | 9:05pm daily | Combines all source DBs into data/composite.db (read-only attaches). Must stay after every collector's last daily slot INCLUDING edgar's 15-min failure retry (~8:45pm+) and before daily-summary at 9:15pm.`

`CLAUDE.md`: in the file-tree block add `└── combiners/    # 1 cross-source combiner (composite: regime + ticker scorecard)` and, in the "Architecture" prose, one sentence: combiners are the third kind — they read the other `data/` DBs ATTACHed read-only and never fetch the network; the combiner binds its own `:today` instead of reading `calendar_now`-dependent source views.

- [ ] **Step 4: Full suite green**

Run: `uv run pytest -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add deploy/launchd/install.py docs/SCHEDULE.md CLAUDE.md
git commit --no-gpg-sign -m "feat(composite): nightly launchd slot + schedule/architecture docs"
```
