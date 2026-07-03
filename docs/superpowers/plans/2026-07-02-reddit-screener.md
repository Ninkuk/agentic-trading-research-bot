# Reddit Sentiment Screener (ApeWisdom) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull ApeWisdom Reddit/4chan mention data into SQLite as an immutable time-series, with derived-signal SQL views, exposed through a shared multi-screener CLI dispatcher.

**Architecture:** Store raw snapshots as the source of truth (ELT); all "rich" signals are SQL views computed over them. A new self-contained `reddit_screener/` package mirrors the proven `stock_analysis_screener/` patterns (snapshot + prune, dependency-injected `run()`, TDD) but uses a **static** schema — no dynamic columns. A tiny top-level `registry.py` + `main.py` dispatcher routes `python main.py <name> ...` to each screener, so future screeners plug in with one registry line.

**Tech Stack:** Python 3.12, stdlib only (`sqlite3`, `urllib`, `json`, `html`, `argparse`), pytest.

## Global Constraints

- **Python:** `>=3.12` (per `pyproject.toml`). SQLite window functions (`ROW_NUMBER`, `LAG`) require SQLite ≥ 3.25 — satisfied by the Python 3.12 bundled SQLite.
- **No new dependencies.** stdlib only, matching the existing `stock_analysis_screener/` package.
- **No commit co-authors** (per user global instruction) — plain commit messages, no `Co-Authored-By` trailer.
- **API base:** `https://apewisdom.io/api/v1.0/filter/{filter}/page/{n}`; 100 results/page; response `{count, pages, current_page, results:[...]}`.
- **Row fields:** `rank, ticker, name, mentions, upvotes, rank_24h_ago, mentions_24h_ago`. Numeric fields may arrive as `int` OR string OR null; coerce to `int`/`None`. `name` may contain HTML entities; `html.unescape` it.
- **Default filters:** `all-stocks,4chan`.
- **Existing `stock_analysis_screener/` behaviour must not change** — the `stocks` subcommand forwards to `stock_analysis_screener.run.main` unchanged.

---

### Task 1: Fetch layer — paginated pull, type coercion, name unescape

**Files:**
- Create: `reddit_screener/__init__.py` (empty)
- Create: `reddit_screener/fetch.py`
- Test: `tests/test_reddit_fetch.py`

**Interfaces:**
- Consumes: nothing (leaf module).
- Produces:
  - `parse_page(raw: dict) -> tuple[list[dict], int]` — returns `(rows, total_pages)`. Each row is a normalized dict with keys `ticker, name, rank, mentions, upvotes, rank_24h_ago, mentions_24h_ago` (numerics `int`/`None`, `name` unescaped). Raises `ValueError` on missing/invalid `results`.
  - `fetch_filter(filter_: str, get_page=_http_get_page) -> list[dict]` — accumulates all pages via the injectable `get_page(filter_, page) -> dict`.
  - `_http_get_page(filter_: str, page: int, base: str = API_BASE) -> dict` — the real HTTP getter.
  - `API_BASE = "https://apewisdom.io/api/v1.0/filter"`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reddit_fetch.py`:

```python
import pytest

from reddit_screener.fetch import fetch_filter, parse_page


def test_parse_page_coerces_types_and_unescapes_name():
    raw = {"count": 2, "pages": 1, "current_page": 1, "results": [
        {"rank": "1", "ticker": "MU", "name": "Micron",
         "mentions": "1147", "upvotes": "5135",
         "rank_24h_ago": "1", "mentions_24h_ago": "951"},
        {"rank": 2, "ticker": "SPY", "name": "SPDR S&amp;P 500 ETF",
         "mentions": 334, "upvotes": 1044,
         "rank_24h_ago": 3, "mentions_24h_ago": 302},
    ]}
    rows, pages = parse_page(raw)
    assert pages == 1
    assert rows[0] == {"ticker": "MU", "name": "Micron", "rank": 1,
                       "mentions": 1147, "upvotes": 5135,
                       "rank_24h_ago": 1, "mentions_24h_ago": 951}
    # HTML entity decoded, and string numerics coerced to int
    assert rows[1]["name"] == "SPDR S&P 500 ETF"
    assert rows[1]["rank"] == 2


def test_parse_page_tolerates_null_24h_fields():
    raw = {"pages": 1, "results": [
        {"rank": 5, "ticker": "NEW", "name": "New Co",
         "mentions": 3, "upvotes": 4,
         "rank_24h_ago": None, "mentions_24h_ago": None},
    ]}
    rows, _ = parse_page(raw)
    assert rows[0]["rank_24h_ago"] is None
    assert rows[0]["mentions_24h_ago"] is None


def test_parse_page_rejects_missing_results():
    with pytest.raises(ValueError):
        parse_page({"pages": 1})


def test_fetch_filter_accumulates_all_pages():
    pages = {
        1: {"pages": 2, "results": [
            {"rank": 1, "ticker": "AAA", "name": "A",
             "mentions": 10, "upvotes": 20,
             "rank_24h_ago": 2, "mentions_24h_ago": 5}]},
        2: {"pages": 2, "results": [
            {"rank": 2, "ticker": "BBB", "name": "B",
             "mentions": 8, "upvotes": 9,
             "rank_24h_ago": 1, "mentions_24h_ago": 12}]},
    }

    def fake_get_page(filter_, page):
        assert filter_ == "all-stocks"
        return pages[page]

    rows = fetch_filter("all-stocks", get_page=fake_get_page)
    assert [r["ticker"] for r in rows] == ["AAA", "BBB"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reddit_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reddit_screener'`.

- [ ] **Step 3: Create the package and fetch module**

Create empty `reddit_screener/__init__.py` (0 bytes).

Create `reddit_screener/fetch.py`:

```python
import html
import json
import urllib.request

API_BASE = "https://apewisdom.io/api/v1.0/filter"
_UA = {"User-Agent": "Mozilla/5.0"}

_NUMERIC_FIELDS = ("rank", "mentions", "upvotes", "rank_24h_ago", "mentions_24h_ago")


def _to_int(value):
    """Coerce API numerics to int; None/'' -> None (new-entrant 24h fields)."""
    if value is None or value == "":
        return None
    return int(value)


def _normalize(row: dict) -> dict:
    out = {"ticker": row["ticker"], "name": html.unescape(row.get("name") or "")}
    for field in _NUMERIC_FIELDS:
        out[field] = _to_int(row.get(field))
    return out


def parse_page(raw: dict) -> tuple[list[dict], int]:
    """Normalize one ApeWisdom page -> (rows, total_pages). Raises on bad shape."""
    results = raw.get("results")
    if not isinstance(results, list):
        raise ValueError("unexpected ApeWisdom payload: missing 'results' list")
    pages = _to_int(raw.get("pages")) or 1
    return [_normalize(r) for r in results], pages


def _http_get_page(filter_: str, page: int, base: str = API_BASE) -> dict:
    req = urllib.request.Request(f"{base}/{filter_}/page/{page}", headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_filter(filter_: str, get_page=_http_get_page) -> list[dict]:
    """Fetch every page of a filter and return the accumulated normalized rows."""
    rows, pages = parse_page(get_page(filter_, 1))
    for page in range(2, pages + 1):
        more, _ = parse_page(get_page(filter_, page))
        rows.extend(more)
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reddit_fetch.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add reddit_screener/__init__.py reddit_screener/fetch.py tests/test_reddit_fetch.py
git commit -m "feat: add ApeWisdom fetch layer with pagination and type coercion"
```

---

### Task 2: DB schema and derived-signal views

**Files:**
- Create: `reddit_screener/db.py` (schema portion)
- Test: `tests/test_reddit_db_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `connect(path: str) -> sqlite3.Connection`
  - `ensure_schema(conn) -> None` — idempotent; creates tables `snapshots`, `observations`, `tickers` and views `v_latest`, `v_signals`, `v_trending`, `v_history`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reddit_db_schema.py`:

```python
from reddit_screener.db import connect, ensure_schema


def objects(conn, kind):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type=?", (kind,)).fetchall()}


def test_ensure_schema_creates_tables_and_views():
    conn = connect(":memory:")
    ensure_schema(conn)
    assert {"snapshots", "observations", "tickers"} <= objects(conn, "table")
    assert {"v_latest", "v_signals", "v_trending", "v_history"} <= objects(conn, "view")


def test_ensure_schema_is_idempotent():
    conn = connect(":memory:")
    ensure_schema(conn)
    ensure_schema(conn)  # second run must not raise
    assert {"snapshots", "observations", "tickers"} <= objects(conn, "table")


def test_observations_columns():
    conn = connect(":memory:")
    ensure_schema(conn)
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(observations)").fetchall()}
    assert cols == {"snapshot_id", "ticker", "name", "rank", "mentions",
                    "upvotes", "rank_24h_ago", "mentions_24h_ago"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reddit_db_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reddit_screener.db'`.

- [ ] **Step 3: Write the schema module**

Create `reddit_screener/db.py`:

```python
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    filter       TEXT NOT NULL,
    ticker_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
    snapshot_id      INTEGER NOT NULL REFERENCES snapshots(id),
    ticker           TEXT NOT NULL,
    name             TEXT,
    rank             INTEGER,
    mentions         INTEGER,
    upvotes          INTEGER,
    rank_24h_ago     INTEGER,
    mentions_24h_ago INTEGER,
    PRIMARY KEY (snapshot_id, ticker)
);
CREATE INDEX IF NOT EXISTS ix_observations_ticker ON observations(ticker);
CREATE TABLE IF NOT EXISTS tickers (
    ticker     TEXT PRIMARY KEY,
    name       TEXT,
    asset_type TEXT,
    first_seen TEXT,
    last_seen  TEXT
);

-- Most recent snapshot per filter, joined to its observations.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT id, filter, captured_at,
           ROW_NUMBER() OVER (PARTITION BY filter
                              ORDER BY captured_at DESC, id DESC) AS rn
    FROM snapshots
)
SELECT r.filter, r.captured_at, o.ticker, o.name, o.rank, o.mentions,
       o.upvotes, o.rank_24h_ago, o.mentions_24h_ago
FROM ranked r
JOIN observations o ON o.snapshot_id = r.id
WHERE r.rn = 1;

-- Latest rows enriched with derived signals (NULL-guarded denominators).
CREATE VIEW IF NOT EXISTS v_signals AS
SELECT *,
    mentions - mentions_24h_ago AS mention_delta,
    CASE WHEN mentions_24h_ago IS NULL OR mentions_24h_ago = 0 THEN NULL
         ELSE (mentions - mentions_24h_ago) * 1.0 / mentions_24h_ago END
        AS mention_pct_change,
    rank_24h_ago - rank AS rank_delta,
    CASE WHEN mentions IS NULL OR mentions = 0 THEN NULL
         ELSE upvotes * 1.0 / mentions END AS upvote_ratio
FROM v_latest;

-- Biggest mention movers first.
CREATE VIEW IF NOT EXISTS v_trending AS
SELECT * FROM v_signals
WHERE mention_pct_change IS NOT NULL
ORDER BY mention_pct_change DESC;

-- Per-ticker time-series with deltas between consecutive stored snapshots.
CREATE VIEW IF NOT EXISTS v_history AS
SELECT o.ticker, s.filter, s.captured_at, o.rank, o.mentions, o.upvotes,
    o.mentions - LAG(o.mentions) OVER w AS mention_delta_since_last,
    LAG(o.rank) OVER w - o.rank AS rank_delta_since_last
FROM observations o
JOIN snapshots s ON s.id = o.snapshot_id
WINDOW w AS (PARTITION BY o.ticker, s.filter
             ORDER BY s.captured_at, o.snapshot_id);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Create tables and derived-signal views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reddit_db_schema.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add reddit_screener/db.py tests/test_reddit_db_schema.py
git commit -m "feat: add Reddit screener SQLite schema and derived-signal views"
```

---

### Task 3: DB writes — snapshot, ticker upsert, prune, view math

**Files:**
- Modify: `reddit_screener/db.py` (append write functions)
- Test: `tests/test_reddit_db_write.py`

**Interfaces:**
- Consumes: `connect`, `ensure_schema` from Task 2.
- Produces:
  - `write_snapshot(conn, captured_at: str, filter_: str, rows: list[dict]) -> tuple[int, int]` — returns `(snapshot_id, ticker_count)`.
  - `upsert_tickers(conn, rows: list[dict], captured_at: str) -> None` — sets `asset_type` from `.X` suffix, updates `last_seen`, preserves `first_seen`.
  - `prune(conn, keep_days: int, now_iso: str) -> int` — deletes observations+snapshots older than cutoff; returns snapshot count removed.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reddit_db_write.py`:

```python
from reddit_screener.db import (connect, ensure_schema, prune, upsert_tickers,
                                write_snapshot)


def _rows():
    return [
        {"ticker": "MU", "name": "Micron", "rank": 1, "mentions": 1147,
         "upvotes": 5135, "rank_24h_ago": 1, "mentions_24h_ago": 951},
        {"ticker": "BTC.X", "name": "Bitcoin", "rank": 2, "mentions": 100,
         "upvotes": 400, "rank_24h_ago": None, "mentions_24h_ago": None},
    ]


def test_write_snapshot_stores_rows_and_count():
    conn = connect(":memory:")
    ensure_schema(conn)
    sid, n = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", _rows())
    assert n == 2
    assert conn.execute(
        "SELECT ticker_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 2
    got = conn.execute(
        "SELECT mentions, upvotes FROM observations "
        "WHERE snapshot_id=? AND ticker='MU'", (sid,)).fetchone()
    assert got == (1147, 5135)


def test_upsert_tickers_classifies_and_tracks_seen():
    conn = connect(":memory:")
    ensure_schema(conn)
    upsert_tickers(conn, _rows(), "2026-07-01T00:00:00+00:00")
    upsert_tickers(conn, _rows(), "2026-07-02T00:00:00+00:00")  # second sighting
    mu = conn.execute(
        "SELECT asset_type, first_seen, last_seen FROM tickers "
        "WHERE ticker='MU'").fetchone()
    assert mu == ("stock", "2026-07-01T00:00:00+00:00", "2026-07-02T00:00:00+00:00")
    btc_type = conn.execute(
        "SELECT asset_type FROM tickers WHERE ticker='BTC.X'").fetchone()[0]
    assert btc_type == "crypto"


def test_v_signals_math_and_null_guards():
    conn = connect(":memory:")
    ensure_schema(conn)
    rows = [
        {"ticker": "MU", "name": "Micron", "rank": 1, "mentions": 1147,
         "upvotes": 5135, "rank_24h_ago": 3, "mentions_24h_ago": 951},
        # mentions_24h_ago = 0 -> pct_change must be NULL, not a divide error
        {"ticker": "NEW", "name": "New Co", "rank": 5, "mentions": 10,
         "upvotes": 20, "rank_24h_ago": None, "mentions_24h_ago": 0},
    ]
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", rows)
    mu = conn.execute(
        "SELECT mention_delta, rank_delta, upvote_ratio FROM v_signals "
        "WHERE ticker='MU'").fetchone()
    assert mu == (196, 2, 5135 / 1147)
    new_pct = conn.execute(
        "SELECT mention_pct_change FROM v_signals WHERE ticker='NEW'").fetchone()[0]
    assert new_pct is None


def test_prune_removes_old_snapshots():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-06-01T00:00:00+00:00", "all-stocks", _rows())
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "all-stocks", _rows())
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reddit_db_write.py -v`
Expected: FAIL — `ImportError: cannot import name 'write_snapshot'`.

- [ ] **Step 3: Append write functions to `reddit_screener/db.py`**

Add these imports at the top of `reddit_screener/db.py` (below the existing `import sqlite3`):

```python
from datetime import datetime, timedelta
```

Append to the end of `reddit_screener/db.py`:

```python
def write_snapshot(conn, captured_at: str, filter_: str,
                   rows: list[dict]) -> tuple[int, int]:
    """Insert one snapshot header + its observation rows. Returns (id, count)."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, filter, ticker_count) VALUES (?, ?, ?)",
        (captured_at, filter_, len(rows)),
    )
    snapshot_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO observations
           (snapshot_id, ticker, name, rank, mentions, upvotes,
            rank_24h_ago, mentions_24h_ago)
           VALUES (:sid, :ticker, :name, :rank, :mentions, :upvotes,
                   :rank_24h_ago, :mentions_24h_ago)""",
        [{**r, "sid": snapshot_id} for r in rows],
    )
    conn.commit()
    return snapshot_id, len(rows)


def _asset_type(ticker: str) -> str:
    return "crypto" if ticker.endswith(".X") else "stock"


def upsert_tickers(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the ticker dimension: refresh name/last_seen, preserve first_seen."""
    conn.executemany(
        """INSERT INTO tickers (ticker, name, asset_type, first_seen, last_seen)
           VALUES (:ticker, :name, :asset_type, :seen, :seen)
           ON CONFLICT(ticker) DO UPDATE SET
             name=excluded.name,
             asset_type=excluded.asset_type,
             last_seen=excluded.last_seen""",
        [{"ticker": r["ticker"], "name": r["name"],
          "asset_type": _asset_type(r["ticker"]), "seen": captured_at}
         for r in rows],
    )
    conn.commit()


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete snapshots + observations older than keep_days before now_iso."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM observations WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reddit_db_write.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add reddit_screener/db.py tests/test_reddit_db_write.py
git commit -m "feat: add snapshot write, ticker upsert, and prune for Reddit screener"
```

---

### Task 4: Orchestration — `run()` and module CLI

**Files:**
- Create: `reddit_screener/run.py`
- Test: `tests/test_reddit_run.py`

**Interfaces:**
- Consumes: `db.connect/ensure_schema/write_snapshot/upsert_tickers/prune` (Tasks 2–3); `fetch.fetch_filter` (Task 1).
- Produces:
  - `DEFAULT_FILTERS = ["all-stocks", "4chan"]`
  - `run(db_path, filters=None, keep_days=None, fetch_filter=fetch.fetch_filter, now_iso=None) -> list[tuple[int, int]]` — one `(snapshot_id, count)` per filter, in order.
  - `main(argv=None) -> None` — argparse CLI (`--db`, `--filters`, `--keep-days`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reddit_run.py`:

```python
import pytest

from reddit_screener.db import connect
from reddit_screener.run import run


def _mkrows(ticker, mentions):
    return [{"ticker": ticker, "name": ticker, "rank": 1, "mentions": mentions,
             "upvotes": mentions * 2, "rank_24h_ago": 1,
             "mentions_24h_ago": mentions}]


def test_run_writes_one_snapshot_per_filter_sharing_capture(tmp_path):
    db_path = str(tmp_path / "r.db")

    def fake_fetch(filter_):
        return _mkrows("MU" if filter_ == "all-stocks" else "AAA", 5)

    results = run(db_path, filters=["all-stocks", "4chan"],
                  fetch_filter=fake_fetch, now_iso="2026-07-02T00:00:00+00:00")
    assert len(results) == 2
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT filter, captured_at FROM snapshots ORDER BY id").fetchall()
    assert rows == [("all-stocks", "2026-07-02T00:00:00+00:00"),
                    ("4chan", "2026-07-02T00:00:00+00:00")]


def test_run_warns_on_empty_filter_but_still_writes_snapshot(tmp_path, capsys):
    db_path = str(tmp_path / "r.db")

    def fake_fetch(filter_):
        return []

    run(db_path, filters=["all-stocks"], fetch_filter=fake_fetch,
        now_iso="2026-07-02T00:00:00+00:00")
    assert "warning" in capsys.readouterr().err.lower()
    conn = connect(db_path)
    assert conn.execute(
        "SELECT ticker_count FROM snapshots").fetchone()[0] == 0


def test_run_second_run_appends_history(tmp_path):
    db_path = str(tmp_path / "r.db")

    run(db_path, filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 10),
        now_iso="2026-07-01T00:00:00+00:00")
    run(db_path, filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 20),
        now_iso="2026-07-02T00:00:00+00:00")

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
    latest = conn.execute(
        "SELECT mentions FROM v_latest WHERE ticker='MU'").fetchone()[0]
    assert latest == 20


def test_run_keep_days_prunes_through_run(tmp_path):
    db_path = str(tmp_path / "r.db")
    run(db_path, filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 10),
        now_iso="2026-06-01T00:00:00+00:00")
    run(db_path, filters=["all-stocks"], keep_days=7,
        fetch_filter=lambda f: _mkrows("MU", 20),
        now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_first_filter_failure_writes_no_snapshot(tmp_path):
    db_path = str(tmp_path / "r.db")

    def failing_fetch(filter_):
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        run(db_path, filters=["all-stocks"], fetch_filter=failing_fetch,
            now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_run_partial_failure_keeps_earlier_filter(tmp_path):
    db_path = str(tmp_path / "r.db")

    def fetch(filter_):
        if filter_ == "4chan":
            raise RuntimeError("boom")
        return _mkrows("MU", 5)

    with pytest.raises(RuntimeError):
        run(db_path, filters=["all-stocks", "4chan"], fetch_filter=fetch,
            now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    filters = [r[0] for r in conn.execute("SELECT filter FROM snapshots").fetchall()]
    assert filters == ["all-stocks"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reddit_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reddit_screener.run'`.

- [ ] **Step 3: Write the orchestration module**

Create `reddit_screener/run.py`:

```python
import argparse
import sys
from datetime import datetime, timezone

from reddit_screener import db, fetch

DEFAULT_FILTERS = ["all-stocks", "4chan"]


def run(db_path, filters=None, keep_days=None,
        fetch_filter=fetch.fetch_filter, now_iso=None):
    """Fetch each filter and append a snapshot. Returns [(snapshot_id, count)]."""
    filters = filters or DEFAULT_FILTERS
    captured_at = now_iso or datetime.now(timezone.utc).isoformat()
    conn = db.connect(db_path)
    results = []
    try:
        db.ensure_schema(conn)
        for filter_ in filters:
            rows = fetch_filter(filter_)
            if not rows:
                print(f"warning: filter '{filter_}' returned 0 tickers",
                      file=sys.stderr)
            snapshot_id, count = db.write_snapshot(conn, captured_at, filter_, rows)
            db.upsert_tickers(conn, rows, captured_at)
            results.append((snapshot_id, count))
        if keep_days is not None:
            db.prune(conn, keep_days, captured_at)
    finally:
        conn.close()
    return results


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="reddit", description="Pull ApeWisdom Reddit sentiment into SQLite")
    p.add_argument("--db", default="reddit.db")
    p.add_argument("--filters", default="all-stocks,4chan",
                   help="comma-separated ApeWisdom filters")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    filters = [f.strip() for f in a.filters.split(",") if f.strip()]
    results = run(a.db, filters, a.keep_days)
    total = sum(n for _, n in results)
    print(f"stored {total} rows across {len(results)} filter(s) into {a.db}")


if __name__ == "__main__":
    main()
```

**Note on failure semantics:** `write_snapshot` runs only after a successful
`fetch_filter`, and each filter commits independently. A first-filter failure
therefore leaves zero snapshots; a later-filter failure leaves the earlier
filters' snapshots committed (the two failure tests pin both cases).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reddit_run.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add reddit_screener/run.py tests/test_reddit_run.py
git commit -m "feat: add Reddit screener run orchestration and CLI"
```

---

### Task 5: Shared multi-screener dispatcher

**Files:**
- Create: `registry.py`
- Modify: `main.py` (replace its 2-line body)
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `stock_analysis_screener.run.main` (existing), `reddit_screener.run.main` (Task 4).
- Produces:
  - `REGISTRY: dict[str, callable]` — `{"stocks": ..., "reddit": ...}`; each value is a `main(argv)` callable.
  - `dispatch(argv=None) -> None` — routes `argv[0]` to the matching screener, forwarding the rest; `--list`/`-l`/empty prints names; unknown name exits with code 2.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_registry.py`:

```python
import pytest

import registry


def test_dispatch_lists_registered_screeners(capsys):
    registry.dispatch(["--list"])
    out = capsys.readouterr().out
    assert "stocks" in out
    assert "reddit" in out


def test_dispatch_routes_and_forwards_argv(monkeypatch):
    seen = {}
    monkeypatch.setitem(registry.REGISTRY, "reddit",
                        lambda argv: seen.setdefault("argv", argv))
    registry.dispatch(["reddit", "--db", "x.db"])
    assert seen["argv"] == ["--db", "x.db"]


def test_dispatch_unknown_name_exits_nonzero(capsys):
    with pytest.raises(SystemExit) as exc:
        registry.dispatch(["nope"])
    assert exc.value.code != 0
    assert "nope" in capsys.readouterr().err


def test_registry_has_both_screeners():
    assert set(registry.REGISTRY) >= {"stocks", "reddit"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'registry'`.

- [ ] **Step 3: Write the registry and rewire `main.py`**

Create `registry.py`:

```python
import sys

from reddit_screener.run import main as reddit_main
from stock_analysis_screener.run import main as stocks_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
}


def dispatch(argv=None):
    """Route `<name> [args...]` to a registered screener. `--list` prints names."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--list", "-l", "list"):
        for name in REGISTRY:
            print(name)
        return
    name, rest = argv[0], argv[1:]
    if name not in REGISTRY:
        print(f"unknown screener: {name}; choose from {', '.join(REGISTRY)}",
              file=sys.stderr)
        raise SystemExit(2)
    REGISTRY[name](rest)
```

Replace the entire body of `main.py` with:

```python
from registry import dispatch

if __name__ == "__main__":
    dispatch()
```

- [ ] **Step 4: Run the full suite to verify nothing regressed**

Run: `pytest -v`
Expected: PASS — all existing `screener` tests + the new `reddit_screener`/`registry` tests green.

Also verify the dispatcher wiring manually:

Run: `python main.py --list`
Expected output:
```
stocks
reddit
```

- [ ] **Step 5: Commit**

```bash
git add registry.py main.py tests/test_registry.py
git commit -m "feat: add multi-screener CLI dispatcher with stocks and reddit"
```

---

### Task 6: Live smoke test (manual verification)

**Files:** none (verification only).

- [ ] **Step 1: Run a real pull into a temp DB**

Run:
```bash
python main.py reddit --db /tmp/reddit_smoke.db --filters all-stocks,4chan
```
Expected: prints `stored <N> rows across 2 filter(s) into /tmp/reddit_smoke.db` with N in the low thousands (roughly ~1000 all-stocks + a few hundred 4chan).

- [ ] **Step 2: Verify derived signals are populated**

Run:
```bash
python -c "
import sqlite3
c = sqlite3.connect('/tmp/reddit_smoke.db')
print('snapshots:', c.execute('SELECT filter, ticker_count FROM snapshots').fetchall())
print('top trending:', c.execute(
    'SELECT ticker, mentions, mention_pct_change FROM v_trending LIMIT 5').fetchall())
print('crypto tickers:', c.execute(
    \"SELECT COUNT(*) FROM tickers WHERE asset_type='crypto'\").fetchone()[0])
"
```
Expected: non-empty snapshots with sensible counts, a trending list with numeric `mention_pct_change`, and `v_signals`/`v_trending` returning rows without error.

- [ ] **Step 3: Clean up**

Run: `rm -f /tmp/reddit_smoke.db /tmp/reddit_smoke.db-wal /tmp/reddit_smoke.db-shm`

(No commit — verification only.)

---

## Self-Review

**1. Spec coverage:**
- Store-raw-derive-in-views → Tasks 2 (views) + 3 (raw writes). ✓
- Static schema, no dynamic columns → Task 2. ✓
- Tables `snapshots`/`observations`/`tickers` → Task 2. ✓
- Views `v_latest`/`v_signals`/`v_trending`/`v_history` → Task 2, math pinned in Task 3. ✓
- Type coercion, null 24h fields, HTML unescape, `.X` classification → Task 1 (coerce/unescape) + Task 3 (`.X`). ✓
- Multi-board dimension + default `all-stocks,4chan` → Task 4. ✓
- Registry/dispatcher, `stocks` unchanged, `--list` → Task 5. ✓
- Error handling: empty-filter warning + zero-count snapshot, partial-run semantics → Task 4 tests. ✓
- Retention/prune → Task 3 (fn) + Task 4 (through-run). ✓
- Live smoke → Task 6. ✓

**2. Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step has full code. ✓

**3. Type consistency:** `fetch_filter(filter_, get_page=...)` used identically in Task 1 and injected in Task 4. `write_snapshot(conn, captured_at, filter_, rows) -> (id, count)` consistent across Tasks 3–4. `run(...) -> list[(id, count)]` consistent Tasks 4–5. Row dict keys identical across fetch (Task 1), write (Task 3), and run test helpers (Task 4). ✓

No gaps found.
