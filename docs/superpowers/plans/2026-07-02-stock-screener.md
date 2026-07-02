# Stock Screener → SQLite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull all 310 stockanalysis.com data points for the ~5,600-stock universe via the anonymous `data-points` endpoint and store them as append-only snapshots in a wide SQLite table.

**Architecture:** A single-run CLI: fetch the SvelteKit `__data.json` catalog (for the id→name→category→proOnly dictionary), fetch every catalog id from the plain-JSON `data-points` endpoint (one request, ~38 MB), ensure/migrate a wide `metrics` table, then insert one snapshot + one row per ticker in a transaction. Five focused modules under `screener/` plus a thin `main.py`.

**Tech Stack:** Python 3.12, standard library only at runtime (`urllib.request`, `sqlite3`, `argparse`, `datetime`). `pytest` for tests (dev dependency). Managed with `uv`.

## Global Constraints

- Python `>=3.12` (from `pyproject.toml`).
- **Runtime code imports standard library only** — no third-party runtime dependencies. `pytest` is a dev-only dependency.
- Both endpoints require header `User-Agent: Mozilla/5.0`.
- Catalog endpoint: `https://stockanalysis.com/stocks/screener/__data.json`.
- Data endpoint: `https://stockanalysis.com/_api/endpoints/screener/data-points` with query `type=s&ids=<id1>+<id2>+...` (space-separated ids, URL-encoded to `+`).
- All identifiers used as SQLite column names must be double-quoted (ids like `change` are safe but quote uniformly).
- Timestamps are ISO-8601 strings; production code uses UTC, tests inject a fixed value.
- Do not add a commit co-author.

---

### Task 1: Package scaffolding + type inference (`screener/typing.py`)

**Files:**
- Create: `screener/__init__.py` (empty)
- Create: `screener/typing.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_typing.py`
- Modify: `pyproject.toml` (add pytest dev dependency + config)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `STRING_IDS: frozenset[str]` — data-point ids always stored as text.
  - `infer_affinity(values: Iterable[object]) -> str` — `"REAL"` if every non-null value is a non-bool number, else `"TEXT"` (all-null → `"TEXT"`).
  - `column_type(dp_id: str, values: Iterable[object]) -> str` — `"TEXT"` if `dp_id in STRING_IDS`, else `infer_affinity(values)`.

- [ ] **Step 1: Add pytest dev dependency and config**

Run:
```bash
cd /Users/ninkuk/Desktop/agentic-trading-bot
uv add --dev pytest
```

Then append to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty package files**

```bash
mkdir -p screener tests
touch screener/__init__.py tests/__init__.py
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_typing.py`:
```python
from screener.typing import STRING_IDS, column_type, infer_affinity


def test_infer_real_when_all_numbers():
    assert infer_affinity([1, 2.5, None]) == "REAL"


def test_infer_text_when_any_string():
    assert infer_affinity([1, "x"]) == "TEXT"


def test_infer_text_when_all_null():
    assert infer_affinity([None, None]) == "TEXT"


def test_infer_text_for_bool_values():
    assert infer_affinity([True, False]) == "TEXT"


def test_column_type_respects_string_override():
    # 'cik' is an identifier that can look numeric but must stay TEXT
    assert "cik" in STRING_IDS
    assert column_type("cik", [12345]) == "TEXT"


def test_column_type_infers_numeric():
    assert column_type("price", [10.0, 11.5]) == "REAL"


def test_column_type_date_is_text():
    assert column_type("nextEarningsDate", ["2026-10-16"]) == "TEXT"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_typing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener.typing'`

- [ ] **Step 5: Write minimal implementation**

Create `screener/typing.py`:
```python
from collections.abc import Iterable

# Data-point ids whose values are always text: categories, dates, currencies,
# identifiers, and Yes/No flags. Forces TEXT even if a sample looks numeric.
STRING_IDS: frozenset[str] = frozenset({
    "n", "marketCapCategory", "industry", "sector", "exchange", "country",
    "usState", "high52Date", "low52Date", "allTimeHighDate", "allTimeLowDate",
    "priceDate", "ipoDate", "lastReportDate", "fiscalYearEnd", "last10kFilingDate",
    "earningsDate", "nextEarningsDate", "lastEarningsDate", "earningsTime",
    "exDivDate", "paymentDate", "lastSplitDate", "lastSplitType", "isSpac",
    "optionable", "ma50vs200", "priceCurrency", "financialCurrency", "sic",
    "cik", "isin", "cusip", "website", "analystRatings", "analystRatingsTop",
    "payoutFrequency", "tag",
})


def infer_affinity(values: Iterable[object]) -> str:
    """REAL if every non-null value is a non-bool number, else TEXT (all-null -> TEXT)."""
    saw_value = False
    for v in values:
        if v is None:
            continue
        saw_value = True
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return "TEXT"
    return "REAL" if saw_value else "TEXT"


def column_type(dp_id: str, values: Iterable[object]) -> str:
    """SQLite affinity for a data-point column: STRING_IDS override, else inferred."""
    if dp_id in STRING_IDS:
        return "TEXT"
    return infer_affinity(values)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/test_typing.py -v`
Expected: PASS (7 passed)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock screener/__init__.py screener/typing.py tests/__init__.py tests/test_typing.py
git commit -m "feat: type inference for screener columns"
```

---

### Task 2: Catalog parser (`screener/catalog.py`)

**Files:**
- Create: `screener/catalog.py`
- Create: `tests/test_catalog.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass(frozen=True) DataPoint(id: str, name: str, category: str, is_pro: bool)`
  - `parse_catalog(raw: dict) -> tuple[list[DataPoint], int]` — decodes the SvelteKit index-deduplicated payload into `(data_points, universe_count)`.
  - `fetch_catalog(url: str = CATALOG_URL) -> tuple[list[DataPoint], int]` — HTTP GET + `parse_catalog`.
  - `CATALOG_URL: str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_catalog.py`:
```python
from screener.catalog import DataPoint, parse_catalog


def make_raw():
    # Minimal SvelteKit index-deduplicated payload.
    # pool[0] is the top object; every value is an index into the pool.
    pool = [
        {"count": 1, "data": 2, "dataPoints": 3},  # 0: top
        2,                                          # 1: count = 2
        [],                                         # 2: data (unused by catalog)
        [4, 5],                                     # 3: dataPoints -> defs at 4,5
        {"name": 6, "id": 7, "cat": 8},             # 4: def (no proOnly)
        {"name": 9, "id": 10, "cat": 8, "proOnly": 11},  # 5: def (proOnly)
        "Market Cap",                               # 6
        "marketCap",                                # 7
        "Valuation & Ratios",                       # 8
        "Altman Z-Score",                           # 9
        "zScore",                                   # 10
        True,                                       # 11
    ]
    return {"nodes": [
        {"type": "data", "data": ["session-node"]},
        {"type": "data", "data": pool},
    ]}


def test_parse_catalog_returns_points_and_count():
    points, count = parse_catalog(make_raw())
    assert count == 2
    assert points == [
        DataPoint("marketCap", "Market Cap", "Valuation & Ratios", False),
        DataPoint("zScore", "Altman Z-Score", "Valuation & Ratios", True),
    ]


def test_parse_catalog_raises_when_payload_missing():
    import pytest
    with pytest.raises(ValueError):
        parse_catalog({"nodes": [{"type": "data", "data": ["only-session"]}]})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener.catalog'`

- [ ] **Step 3: Write minimal implementation**

Create `screener/catalog.py`:
```python
import json
import urllib.request
from dataclasses import dataclass

CATALOG_URL = "https://stockanalysis.com/stocks/screener/__data.json"
_UA = {"User-Agent": "Mozilla/5.0"}


@dataclass(frozen=True)
class DataPoint:
    id: str
    name: str
    category: str
    is_pro: bool


def parse_catalog(raw: dict) -> tuple[list[DataPoint], int]:
    """Decode SvelteKit index-deduplicated payload -> (data_points, universe_count)."""
    pool = None
    for node in raw.get("nodes", []):
        data = node.get("data") if isinstance(node, dict) else None
        if (isinstance(data, list) and data and isinstance(data[0], dict)
                and "dataPoints" in data[0]):
            pool = data
            break
    if pool is None:
        raise ValueError("screener payload node not found in __data.json")

    top = pool[0]

    def deref(idx):
        return pool[idx]

    count = deref(top["count"])
    points: list[DataPoint] = []
    for dp_idx in deref(top["dataPoints"]):
        obj = deref(dp_idx)
        if not isinstance(obj, dict) or "id" not in obj:
            continue
        points.append(DataPoint(
            id=deref(obj["id"]),
            name=deref(obj["name"]) if "name" in obj else "",
            category=deref(obj["cat"]) if "cat" in obj else "",
            is_pro=bool(deref(obj["proOnly"])) if "proOnly" in obj else False,
        ))
    return points, count


def fetch_catalog(url: str = CATALOG_URL) -> tuple[list[DataPoint], int]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = json.load(resp)
    return parse_catalog(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_catalog.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add screener/catalog.py tests/test_catalog.py
git commit -m "feat: SvelteKit catalog parser for screener data points"
```

---

### Task 3: Data-points fetch parser (`screener/fetch.py`)

**Files:**
- Create: `screener/fetch.py`
- Create: `tests/test_fetch.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `parse_data_points(raw: dict) -> dict[str, dict]` — extracts `{ticker: {field: value}}` from `raw["data"]["data"]`.
  - `fetch_data_points(ids: list[str], type_: str = "s", url: str = DATA_URL) -> dict[str, dict]`
  - `DATA_URL: str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetch.py`:
```python
import pytest

from screener.fetch import parse_data_points


def test_parse_data_points_extracts_ticker_map():
    raw = {"status": 200, "data": {"data": {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": None, "sector": "Energy"},
    }}}
    out = parse_data_points(raw)
    assert out == {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": None, "sector": "Energy"},
    }


def test_parse_data_points_rejects_bad_shape():
    with pytest.raises(ValueError):
        parse_data_points({"status": 200, "data": {"data": []}})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener.fetch'`

- [ ] **Step 3: Write minimal implementation**

Create `screener/fetch.py`:
```python
import json
import urllib.parse
import urllib.request

DATA_URL = "https://stockanalysis.com/_api/endpoints/screener/data-points"
_UA = {"User-Agent": "Mozilla/5.0"}


def parse_data_points(raw: dict) -> dict[str, dict]:
    """Extract {ticker: {field: value}} from the data-points response."""
    data = raw.get("data", {})
    inner = data.get("data") if isinstance(data, dict) else None
    if not isinstance(inner, dict):
        raise ValueError("unexpected data-points payload shape")
    return inner


def fetch_data_points(ids: list[str], type_: str = "s",
                      url: str = DATA_URL) -> dict[str, dict]:
    query = urllib.parse.urlencode({"type": type_, "ids": " ".join(ids)})
    req = urllib.request.Request(f"{url}?{query}", headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.load(resp)
    return parse_data_points(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fetch.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add screener/fetch.py tests/test_fetch.py
git commit -m "feat: data-points fetch and parser"
```

---

### Task 4: DB schema and migration (`screener/db.py` part 1)

**Files:**
- Create: `screener/db.py`
- Create: `tests/test_db_schema.py`

**Interfaces:**
- Consumes: `screener.catalog.DataPoint`.
- Produces:
  - `connect(path: str) -> sqlite3.Connection`
  - `ensure_schema(conn, columns: dict[str, str]) -> None` — creates `snapshots`, `data_points`, `metrics`, index, `v_latest` view; adds any missing `metrics` columns (idempotent). `columns` maps data-point id → affinity.
  - `upsert_data_points(conn, data_points: Iterable[DataPoint]) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_schema.py`:
```python
from screener.catalog import DataPoint
from screener.db import connect, ensure_schema, upsert_data_points


def cols(conn):
    return {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}


def test_ensure_schema_creates_tables_and_columns():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL", "sector": "TEXT"})
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"snapshots", "data_points", "metrics"} <= tables
    assert {"snapshot_id", "symbol", "price", "sector"} <= cols(conn)


def test_ensure_schema_is_idempotent_and_adds_new_columns():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL"})
    ensure_schema(conn, {"price": "REAL", "rsi": "REAL"})  # rerun + new column
    assert "rsi" in cols(conn)


def test_upsert_data_points_inserts_and_updates():
    conn = connect(":memory:")
    ensure_schema(conn, {})
    upsert_data_points(conn, [DataPoint("zScore", "Altman Z-Score", "Tech", True)])
    upsert_data_points(conn, [DataPoint("zScore", "Z-Score", "Technical", False)])
    row = conn.execute(
        "SELECT name, category, is_pro FROM data_points WHERE id='zScore'").fetchone()
    assert row == ("Z-Score", "Technical", 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener.db'`

- [ ] **Step 3: Write minimal implementation**

Create `screener/db.py`:
```python
import sqlite3
from collections.abc import Iterable

from screener.catalog import DataPoint

_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,
    universe_count INTEGER NOT NULL,
    source         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS data_points (
    id       TEXT PRIMARY KEY,
    name     TEXT,
    category TEXT,
    is_pro   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS metrics (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    symbol      TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, symbol)
);
CREATE INDEX IF NOT EXISTS ix_metrics_symbol ON metrics(symbol);
CREATE VIEW IF NOT EXISTS v_latest AS
SELECT m.* FROM metrics m
WHERE m.snapshot_id = (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _metrics_columns(conn) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}


def ensure_schema(conn, columns: dict[str, str]) -> None:
    """Create base tables and add any missing metrics columns. Idempotent."""
    conn.executescript(_BASE_SCHEMA)
    existing = _metrics_columns(conn)
    for col, affinity in columns.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE metrics ADD COLUMN "{col}" {affinity}')
    conn.commit()


def upsert_data_points(conn, data_points: Iterable[DataPoint]) -> None:
    conn.executemany(
        """INSERT INTO data_points (id, name, category, is_pro)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, category=excluded.category, is_pro=excluded.is_pro""",
        [(d.id, d.name, d.category, int(d.is_pro)) for d in data_points],
    )
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add screener/db.py tests/test_db_schema.py
git commit -m "feat: sqlite schema and idempotent column migration"
```

---

### Task 5: Snapshot write and prune (`screener/db.py` part 2)

**Files:**
- Modify: `screener/db.py` (add `write_snapshot`, `prune`)
- Create: `tests/test_db_write.py`

**Interfaces:**
- Consumes: `connect`, `ensure_schema` from Task 4.
- Produces:
  - `write_snapshot(conn, captured_at: str, source: str, data: dict[str, dict], column_ids: list[str]) -> int` — inserts a `snapshots` row (`universe_count=len(data)`) and one `metrics` row per ticker; returns the new `snapshot_id`.
  - `prune(conn, keep_days: int, now_iso: str) -> int` — deletes snapshots (and their metrics) with `captured_at` older than `keep_days` before `now_iso`; returns count deleted.

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_write.py`:
```python
from screener.db import connect, ensure_schema, prune, write_snapshot


def setup_conn():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL", "sector": "TEXT"})
    return conn


def test_write_snapshot_stores_rows_and_returns_id():
    conn = setup_conn()
    data = {"AAA": {"price": 10.0, "sector": "Tech"},
            "BBB": {"price": 20.0}}  # BBB missing sector -> NULL
    sid = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "src", data,
                         ["price", "sector"])
    assert isinstance(sid, int)
    count = conn.execute("SELECT universe_count FROM snapshots WHERE id=?",
                         (sid,)).fetchone()[0]
    assert count == 2
    row = conn.execute(
        "SELECT price, sector FROM metrics WHERE snapshot_id=? AND symbol='BBB'",
        (sid,)).fetchone()
    assert row == (20.0, None)


def test_v_latest_returns_only_newest_snapshot():
    conn = setup_conn()
    write_snapshot(conn, "2026-07-01T00:00:00+00:00", "src",
                   {"AAA": {"price": 1.0}}, ["price", "sector"])
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "src",
                   {"AAA": {"price": 2.0}}, ["price", "sector"])
    prices = [r[0] for r in conn.execute("SELECT price FROM v_latest").fetchall()]
    assert prices == [2.0]


def test_prune_removes_old_snapshots_and_their_metrics():
    conn = setup_conn()
    old = write_snapshot(conn, "2026-06-01T00:00:00+00:00", "src",
                         {"AAA": {"price": 1.0}}, ["price", "sector"])
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "src",
                   {"AAA": {"price": 2.0}}, ["price", "sector"])
    deleted = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert deleted == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM metrics WHERE snapshot_id=?", (old,)).fetchone()[0] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db_write.py -v`
Expected: FAIL with `ImportError: cannot import name 'write_snapshot'`

- [ ] **Step 3: Write minimal implementation**

Append to `screener/db.py`:
```python
def write_snapshot(conn, captured_at: str, source: str,
                   data: dict[str, dict], column_ids: list[str]) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, ?)",
        (captured_at, len(data), source),
    )
    snapshot_id = cur.lastrowid
    cols = ["snapshot_id", "symbol"] + column_ids
    quoted = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO metrics ({quoted}) VALUES ({placeholders})"
    rows = [
        [snapshot_id, symbol] + [fields.get(cid) for cid in column_ids]
        for symbol, fields in data.items()
    ]
    conn.executemany(sql, rows)
    conn.commit()
    return snapshot_id


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete snapshots + metrics older than keep_days before now_iso. Returns count."""
    from datetime import datetime, timedelta
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM metrics WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db_write.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add screener/db.py tests/test_db_write.py
git commit -m "feat: snapshot write and retention prune"
```

---

### Task 6: CLI orchestration (`screener/run.py`, `main.py`)

**Files:**
- Create: `screener/run.py`
- Modify: `main.py` (replace hello-world with entrypoint)
- Create: `tests/test_run.py`

**Interfaces:**
- Consumes: `catalog.fetch_catalog`, `fetch.fetch_data_points`, `db.*`, `typing.column_type`.
- Produces:
  - `select_ids(all_ids: list[str], only, exclude) -> list[str]`
  - `run(db_path, keep_days=None, only=None, exclude=None, type_="s", fetch_catalog=..., fetch_data=..., now_iso=None) -> tuple[int, int]` — returns `(snapshot_id, stock_count)`. `fetch_catalog`/`fetch_data`/`now_iso` are injectable for tests.
  - `main(argv=None) -> None` — argparse CLI.

- [ ] **Step 1: Write the failing test**

Create `tests/test_run.py`:
```python
from screener.catalog import DataPoint
from screener.db import connect
from screener.run import run, select_ids


def test_select_ids_applies_only_and_exclude():
    assert select_ids(["a", "b", "c"], ["a", "b"], ["b"]) == ["a"]
    assert select_ids(["a", "b", "c"], None, ["b"]) == ["a", "c"]


def test_run_writes_snapshot_end_to_end(tmp_path):
    db_path = str(tmp_path / "s.db")
    catalog = ([
        DataPoint("price", "Stock Price", "Price & Volume", False),
        DataPoint("sector", "Sector", "Company Info", False),
    ], 2)
    data = {"AAA": {"price": 10.0, "sector": "Tech"},
            "BBB": {"price": 20.0, "sector": "Energy"}}

    def fake_catalog():
        return catalog

    def fake_data(ids, type_):
        assert ids == ["price", "sector"]
        assert type_ == "s"
        return data

    sid, n = run(db_path, fetch_catalog=fake_catalog, fetch_data=fake_data,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 2
    conn = connect(db_path)
    stored = conn.execute(
        "SELECT price, sector FROM metrics WHERE symbol='AAA'").fetchone()
    assert stored == (10.0, "Tech")
    # catalog persisted
    assert conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener.run'`

- [ ] **Step 3: Write minimal implementation**

Create `screener/run.py`:
```python
import argparse
from datetime import datetime, timezone

from screener import catalog, db, fetch
from screener.typing import column_type

SOURCE = "stockanalysis.com"


def select_ids(all_ids, only, exclude):
    ids = list(only) if only else list(all_ids)
    ex = set(exclude or ())
    return [i for i in ids if i not in ex]


def run(db_path, keep_days=None, only=None, exclude=None, type_="s",
        fetch_catalog=catalog.fetch_catalog, fetch_data=fetch.fetch_data_points,
        now_iso=None):
    data_points, _count = fetch_catalog()
    all_ids = [d.id for d in data_points]
    ids = select_ids(all_ids, only, exclude)
    data = fetch_data(ids, type_)

    columns = {cid: column_type(cid, (row.get(cid) for row in data.values()))
               for cid in ids}

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn, columns)
        db.upsert_data_points(conn, data_points)
        captured_at = now_iso or datetime.now(timezone.utc).isoformat()
        snapshot_id = db.write_snapshot(conn, captured_at, SOURCE, data, ids)
        if keep_days is not None:
            db.prune(conn, keep_days, captured_at)
    finally:
        conn.close()
    return snapshot_id, len(data)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Pull stockanalysis.com screener into SQLite")
    p.add_argument("--db", default="screener.db")
    p.add_argument("--keep-days", type=int, default=None)
    p.add_argument("--only", default=None, help="comma-separated data-point ids")
    p.add_argument("--exclude", default=None, help="comma-separated data-point ids")
    p.add_argument("--type", dest="type_", default="s")
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    snapshot_id, n = run(a.db, a.keep_days, only, exclude, a.type_)
    print(f"snapshot {snapshot_id}: stored {n} stocks into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Replace `main.py`**

Overwrite `main.py`:
```python
from screener.run import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 7: Smoke-test against the live endpoints**

Run:
```bash
uv run python main.py --db /tmp/screener_smoke.db --only price,sector,rsi,zScore
```
Expected: prints `snapshot 1: stored <~5600> stocks into /tmp/screener_smoke.db`. Verify:
```bash
uv run python -c "import sqlite3; c=sqlite3.connect('/tmp/screener_smoke.db'); print(c.execute('SELECT symbol, price, rsi FROM v_latest LIMIT 3').fetchall())"
```
Expected: three rows with a symbol, a numeric price, and a numeric rsi.

- [ ] **Step 8: Commit**

```bash
git add screener/run.py main.py tests/test_run.py
git commit -m "feat: screener CLI orchestration and entrypoint"
```

---

## Self-Review

**Spec coverage:**
- Catalog fetch + SvelteKit parser → Task 2 ✓
- data-points fetch (all ids, one request) → Task 3 + wiring in Task 6 ✓
- Wide `metrics` table, `snapshots`, `data_points`, `v_latest` view, `ix_metrics_symbol` → Task 4 ✓
- Snapshot-history append + `universe_count` → Task 5 ✓
- Retention prune (`--keep-days`) → Task 5 + CLI in Task 6 ✓
- Type inference (273 numeric / 36 string split, string-set override) → Task 1 ✓
- Config subset (`--only`/`--exclude`) → Task 6 (`select_ids`) ✓
- CLI (`--db`, `--keep-days`, `--only`, `--exclude`, `--type`) → Task 6 ✓
- Error handling: HTTP failures abort (urllib raises, `run` propagates, no snapshot written since insert follows successful fetch); missing field → NULL (Task 5 test); unknown column added on the fly (Task 4 migration) ✓
- Stdlib-only runtime → all modules import only stdlib; pytest is dev-only ✓
- Cadence is operational (external cron) — no code needed ✓

**Placeholder scan:** none — every step has concrete code/commands.

**Type consistency:** `DataPoint(id, name, category, is_pro)` used identically in Tasks 2, 4, 6. `column_type(dp_id, values)`, `ensure_schema(conn, columns: dict)`, `write_snapshot(...) -> int`, `prune(conn, keep_days, now_iso)`, `run(...) -> (snapshot_id, count)` consistent across producer/consumer blocks. `column_ids`/`ids` naming: `run` builds `ids` and passes as `write_snapshot`'s `column_ids` positional — matches.

## Out of scope (per spec)
Scheduling, ETFs/funds (`type=e`), a separate slowly-changing `stocks` dimension, and any query/screening UI.
