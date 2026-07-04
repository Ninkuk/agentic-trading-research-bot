# FINRA OTC / ATS (Dark Pool) Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `ats` screener — FINRA's weekly OTC/ATS (dark-pool) transparency data (per security, per ATS MPID, per week: trade counts + share quantities) into SQLite as a weekly per-venue panel, with microstructure views (off-exchange leaders, top dark pools, per-symbol venue history).

**Architecture:** A FINRA screener like `short_interest`, but POSTing to the `api.finra.org` query API instead of a CDN GET. It reuses the `http_client` bounded-backoff **unchanged** — `http_get(url, opener)` only calls `opener(url)`, so a closure that captures the JSON `compareFilters` body and issues a POST drops straight in. New **three-way panel** shape `(week_start, symbol, mpid)`; history is not snapshot-scoped; `replace_week` (delete-then-insert) absorbs FINRA re-posts; FRED-style single-table prune. No `catalog.py` (full-universe feed). **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `csv`, `io`, `datetime`, `argparse`); `pytest`. Reuses `screener_common.connect`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** The FINRA query API is anonymous; `.env.example` unchanged. Descriptive UA `agentic-trading-bot ninadk.dev@gmail.com`; retry `{429, 503}`; `403/404 → None` (week not yet published / absent).
- **`now_iso` injected, never wall-clock in logic.** `run()` accepts `now_iso=None`, defaulting to UTC now; `fetch_week` injected so tests are network-free.
- **Delay-aware:** the newest fetched week is floored ~2 weeks back (`_PUBLICATION_LAG_DAYS = 14`) so the runner doesn't chase structurally-unpublished weeks; any that slip through 404 → `None` → skipped.
- **Replace-by-week, never orphan.** `replace_week` deletes the week's `ats_volume` rows then bulk-inserts; dedupe within the batch by `(week_start, symbol, mpid)`.
- **Skip-and-continue** per week: `conn.rollback()`, log **only** `type(e).__name__` (never `str(e)`/`e.url`), continue.
- **Prune is FRED-style single-table** — delete old `snapshots` only; never touch `ats_volume`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest` (config in `pyproject.toml`).
- **Commits:** do NOT add a co-author line (per user global instruction).

### Live-verification action (🟡)

The program + POST mechanics are 🟢-verified, but the exact weekly-ATS dataset `name` slug and JSON field names are 🟡. Confirm live (anonymous POST) and adjust the parser + fixtures together: the record fields the fixture assumes are `weekStartDate`, `issueSymbolIdentifier`, `MPID`, `ATSName`, `totalWeeklyTradeCount`, `totalWeeklyShareQuantity`, `tierIdentifier`, and the dataset slug `_DATASET`. Non-attributed de-minimis rows (blank MPID) map to the sentinel `"NON_ATS_DEMINIMIS"` so the PK holds.

---

## File Structure

**New — `finra_ats/` package:**
- `finra_ats/__init__.py` — empty.
- `finra_ats/fetch.py` — `week_body`, `parse_rows` (JSON+CSV), `_post_opener`, `fetch_week`.
- `finra_ats/db.py` — schema (`venues`/`ats_volume`/`weeks`/`snapshots`) + writers + 3 views + prune.
- `finra_ats/run.py` — `weeks_in_range` + delay-aware incremental orchestration + argparse `main`.

**Modified:**
- `registry.py` — import `finra_ats.run.main` and register `"ats"`.

**New tests (`tests/`):**
`test_finra_ats_fetch.py`, `test_finra_ats_db_schema.py`, `test_finra_ats_db_write.py`, `test_finra_ats_db_views.py`, `test_finra_ats_run.py`, and one assertion in `test_registry.py`.

### Fact-row shape (parser → writers)

`{week_start, symbol, mpid, ats_name, trade_count, share_quantity, tier}`.

---

## Task 1: `finra_ats.fetch` — POST query client + parsers

**Files:**
- Create: `finra_ats/__init__.py` (empty), `finra_ats/fetch.py`
- Test: `tests/test_finra_ats_fetch.py`

**Interfaces:**
- `week_body(week_start, limit=10000) -> dict`.
- `parse_rows(text, fmt) -> list[dict]` — `fmt in {"json","csv"}`.
- `fetch_week(week_start, get=_http_get, opener=None) -> list[dict] | None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finra_ats_fetch.py`:

```python
import json
import urllib.error

from finra_ats import fetch

_JSON = json.dumps([
    {"weekStartDate": "2026-06-08", "issueSymbolIdentifier": "AAPL",
     "MPID": "UBSA", "ATSName": "UBS ATS", "totalWeeklyTradeCount": "1234",
     "totalWeeklyShareQuantity": "567890", "tierIdentifier": "T1"},
    {"weekStartDate": "2026-06-08", "issueSymbolIdentifier": "AAPL",
     "MPID": "", "ATSName": "", "totalWeeklyTradeCount": "5",
     "totalWeeklyShareQuantity": "", "tierIdentifier": "T1"},   # de-minimis
    {"weekStartDate": "2026-06-08", "issueSymbolIdentifier": "",   # no symbol
     "MPID": "X", "totalWeeklyTradeCount": "1"},
])


def test_week_body_selects_the_week():
    body = fetch.week_body("2026-06-08")
    dumped = json.dumps(body)
    assert "weekStartDate" in dumped and "2026-06-08" in dumped


def test_parse_rows_json_coerces_and_sentinels_deminimis():
    rows = fetch.parse_rows(_JSON, "json")
    assert len(rows) == 2                            # symbol-less row dropped
    assert rows[0]["mpid"] == "UBSA" and rows[0]["share_quantity"] == 567890
    assert rows[0]["trade_count"] == 1234 and rows[0]["tier"] == "T1"
    assert rows[1]["mpid"] == "NON_ATS_DEMINIMIS"    # blank MPID -> sentinel
    assert rows[1]["share_quantity"] is None         # blank -> None


def test_parse_rows_csv():
    csv_text = ("weekStartDate,issueSymbolIdentifier,MPID,ATSName,"
                "totalWeeklyTradeCount,totalWeeklyShareQuantity,tierIdentifier\n"
                "2026-06-08,MSFT,CDEL,Citadel Connect,10,2000,T1\n")
    rows = fetch.parse_rows(csv_text, "csv")
    assert rows == [{"week_start": "2026-06-08", "symbol": "MSFT",
                     "mpid": "CDEL", "ats_name": "Citadel Connect",
                     "trade_count": 10, "share_quantity": 2000, "tier": "T1"}]


def test_fetch_week_posts_and_parses(monkeypatch):
    seen = {}

    def opener(url):
        seen["url"] = url
        return _JSON

    rows = fetch.fetch_week("2026-06-08", opener=opener)
    assert len(rows) == 2
    assert "otcMarket" in seen["url"]


def test_fetch_week_returns_none_on_403_404():
    def opener(url):
        raise urllib.error.HTTPError(url, 404, "no", {}, None)

    assert fetch.fetch_week("2026-06-08", opener=opener) is None
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `finra_ats/__init__.py` (empty).

Create `finra_ats/fetch.py`:

```python
"""FINRA OTC/ATS (dark-pool) transparency via the anonymous api.finra.org query
API. POSTs a compareFilters body but reuses http_client's backoff unchanged: the
loop only calls opener(url), so a body-capturing POST closure drops straight in."""
import csv
import io
import json
import time
import urllib.error
import urllib.request

import http_client

_DATASET = "weeklySummary"   # 🟡 confirm the weekly-ATS dataset slug live
API_URL = f"https://api.finra.org/data/group/otcMarket/name/{_DATASET}"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_DEMINIMIS = "NON_ATS_DEMINIMIS"

__all__ = ["week_body", "parse_rows", "fetch_week"]


def week_body(week_start: str, limit: int = 10000) -> dict:
    """compareFilters JSON body selecting one week (weekStartDate EQUAL date)."""
    return {"compareFilters": [{"compareType": "EQUAL",
                                "fieldName": "weekStartDate",
                                "fieldValue": week_start}],
            "limit": limit}


def _to_int(raw):
    raw = ("" if raw is None else str(raw)).strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _records(text, fmt):
    if fmt == "csv":
        return list(csv.DictReader(io.StringIO(text)))
    data = json.loads(text)
    if isinstance(data, list):
        return data
    return data.get("data") or data.get("results") or []


def parse_rows(text: str, fmt: str) -> list:
    """Map API records to the curated fact-row shape. Rows missing symbol or week
    are skipped; blank MPID -> the de-minimis sentinel so the PK holds."""
    out = []
    for r in _records(text, fmt):
        symbol = (r.get("issueSymbolIdentifier") or r.get("symbol") or "").strip()
        week = (r.get("weekStartDate") or "").strip()
        if not symbol or not week:
            continue
        mpid = (r.get("MPID") or "").strip() or _DEMINIMIS
        ats_name = (r.get("ATSName") or "").strip() or None
        out.append({
            "week_start": week, "symbol": symbol, "mpid": mpid,
            "ats_name": ats_name,
            "trade_count": _to_int(r.get("totalWeeklyTradeCount")),
            "share_quantity": _to_int(r.get("totalWeeklyShareQuantity")),
            "tier": (r.get("tierIdentifier") or "").strip() or None,
        })
    return out


def _post_opener(body: dict):
    """opener(url)->text that POSTs the JSON body. Captures the body so
    http_client.http_get's opener(url) call issues the POST unchanged."""
    data = json.dumps(body).encode("utf-8")
    headers = {**_UA, "Content-Type": "application/json",
               "Accept": "application/json"}

    def opener(url):
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", "replace")
    return opener


def _http_get(url, opener, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def fetch_week(week_start, get=_http_get, opener=None):
    """POST + parse one week. Returns rows, or None on HTTP 403/404 (not yet
    published / absent). 429/503 + transient errors retried by the backoff."""
    op = opener if opener is not None else _post_opener(week_body(week_start))
    try:
        text = get(API_URL, opener=op)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise
    return parse_rows(text, "json")
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add finra_ats/__init__.py finra_ats/fetch.py tests/test_finra_ats_fetch.py
git commit -m "feat(ats): FINRA otcMarket POST query client + CSV/JSON parsers"
```

---

## Task 2: `finra_ats.db` — schema + writers + prune

**Files:**
- Create: `finra_ats/db.py` (schema + writers + prune; **views in Task 3**)
- Test: `tests/test_finra_ats_db_schema.py`, `tests/test_finra_ats_db_write.py`

**Interfaces:**
- `connect` — re-export from `screener_common`.
- `ensure_schema(conn)` — `venues`/`ats_volume`/`weeks`/`snapshots` + indexes (+ views Task 3). Idempotent.
- `upsert_venues(conn, rows)` — mpid dimension; newest `ats_name`, min/max week → first/last_seen.
- `replace_week(conn, week_start, rows) -> int` — delete week then bulk-insert; dedupe by `(week_start, symbol, mpid)`.
- `record_week(conn, week_start, fetched_at, row_count)`.
- `write_snapshot(conn, captured_at, week_count, row_count) -> int`.
- `stored_weeks(conn) -> list[str]` — ascending.
- `prune(conn, keep_days, now_iso) -> int` — single-table snapshots delete.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_finra_ats_db_schema.py`:

```python
from finra_ats import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"venues", "ats_volume", "weeks", "snapshots"} <= tables
```

Create `tests/test_finra_ats_db_write.py`:

```python
from finra_ats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _row(week, symbol, mpid, shares=100, ats_name="ATS", tc=5, tier="T1"):
    return {"week_start": week, "symbol": symbol, "mpid": mpid,
            "ats_name": ats_name, "trade_count": tc, "share_quantity": shares,
            "tier": tier}


def test_upsert_venues_refreshes_name_and_extends_seen_window():
    conn = _fresh()
    db.upsert_venues(conn, [_row("2026-06-08", "A", "UBSA", ats_name="UBS ATS")])
    db.upsert_venues(conn, [_row("2026-06-15", "A", "UBSA", ats_name="UBS ATS v2")])
    row = conn.execute(
        "SELECT ats_name, first_seen, last_seen FROM venues WHERE mpid='UBSA'"
    ).fetchone()
    assert row == ("UBS ATS v2", "2026-06-08", "2026-06-15")


def test_replace_week_replaces_and_dedupes():
    conn = _fresh()
    db.upsert_venues(conn, [_row("2026-06-08", "A", "M1")])
    db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1", shares=100),
                                         _row("2026-06-08", "A", "M2", shares=50)])
    # a re-post that drops M2 leaves no orphan
    n = db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1", shares=200)])
    assert n == 1
    rows = conn.execute("SELECT mpid, share_quantity FROM ats_volume "
                        "ORDER BY mpid").fetchall()
    assert rows == [("M1", 200)]                 # M2 gone, M1 replaced


def test_record_week_stored_weeks_and_prune():
    conn = _fresh()
    db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1")])
    db.record_week(conn, "2026-06-08", "t", 1)
    db.record_week(conn, "2026-06-01", "t", 1)
    assert db.stored_weeks(conn) == ["2026-06-01", "2026-06-08"]
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM ats_volume").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `finra_ats/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_venues", "replace_week",
           "record_week", "write_snapshot", "stored_weeks", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS venues (
    mpid       TEXT PRIMARY KEY,
    ats_name   TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS ats_volume (
    week_start     TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    mpid           TEXT NOT NULL REFERENCES venues(mpid),
    trade_count    INTEGER,
    share_quantity INTEGER,
    tier           TEXT,
    PRIMARY KEY (week_start, symbol, mpid)
);
CREATE INDEX IF NOT EXISTS ix_ats_week   ON ats_volume(week_start);
CREATE INDEX IF NOT EXISTS ix_ats_symbol ON ats_volume(symbol);
CREATE TABLE IF NOT EXISTS weeks (
    week_start TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    week_count  INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables/indexes (+ views from Task 3). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_venues(conn, rows) -> None:
    """Upsert the mpid dimension: newest ats_name, widen first/last_seen."""
    agg = {}
    for r in rows:
        mp, w = r["mpid"], r["week_start"]
        cur = agg.get(mp)
        if cur is None:
            agg[mp] = {"mpid": mp, "ats_name": r.get("ats_name"),
                       "first": w, "last": w}
        else:
            if r.get("ats_name"):
                cur["ats_name"] = r["ats_name"]
            cur["first"] = min(cur["first"], w)
            cur["last"] = max(cur["last"], w)
    conn.executemany(
        """INSERT INTO venues (mpid, ats_name, first_seen, last_seen)
           VALUES (:mpid, :ats_name, :first, :last)
           ON CONFLICT(mpid) DO UPDATE SET
             ats_name=COALESCE(excluded.ats_name, venues.ats_name),
             first_seen=min(venues.first_seen, excluded.first_seen),
             last_seen=max(venues.last_seen, excluded.last_seen)""",
        list(agg.values()))
    conn.commit()


def replace_week(conn, week_start, rows) -> int:
    """Delete the week's rows then bulk-insert (dedupe by full key). A re-post
    that drops a venue leaves no orphan."""
    by_key = {(r["week_start"], r["symbol"], r["mpid"]): r for r in rows}
    conn.execute("DELETE FROM ats_volume WHERE week_start=?", (week_start,))
    conn.executemany(
        """INSERT INTO ats_volume
           (week_start, symbol, mpid, trade_count, share_quantity, tier)
           VALUES (:week_start, :symbol, :mpid, :trade_count, :share_quantity,
                   :tier)""", list(by_key.values()))
    conn.commit()
    return len(by_key)


def record_week(conn, week_start, fetched_at, row_count) -> None:
    conn.execute(
        """INSERT INTO weeks (week_start, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(week_start) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (week_start, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at, week_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, week_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, week_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_weeks(conn) -> list:
    return [r[0] for r in conn.execute(
        "SELECT week_start FROM weeks ORDER BY week_start")]


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots only. ats_volume is the store and is
    NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})",
                 ids)
    conn.commit()
    return len(ids)


_VIEWS = ""   # filled in Task 3
```

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (1 + 3 tests).

- [ ] **Step 5: Commit**

```bash
git add finra_ats/db.py tests/test_finra_ats_db_schema.py tests/test_finra_ats_db_write.py
git commit -m "feat(ats): venues/ats_volume/weeks schema + replace-week writes + prune"
```

---

## Task 3: `finra_ats.db` — microstructure views

**Files:**
- Modify: `finra_ats/db.py` (fill `_VIEWS`)
- Test: `tests/test_finra_ats_db_views.py`

**Views:** `v_latest_off_exchange`, `v_top_dark_pools`, `v_symbol_venue_history`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finra_ats_db_views.py`:

```python
from finra_ats import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    rows = [
        {"week_start": "2026-06-01", "symbol": "A", "mpid": "M1",
         "ats_name": "Pool One", "trade_count": 3, "share_quantity": 100, "tier": "T1"},
        {"week_start": "2026-06-08", "symbol": "A", "mpid": "M1",
         "ats_name": "Pool One", "trade_count": 5, "share_quantity": 300, "tier": "T1"},
        {"week_start": "2026-06-08", "symbol": "A", "mpid": "M2",
         "ats_name": "Pool Two", "trade_count": 2, "share_quantity": 50, "tier": "T1"},
        {"week_start": "2026-06-08", "symbol": "B", "mpid": "M1",
         "ats_name": "Pool One", "trade_count": 1, "share_quantity": 400, "tier": "T1"},
    ]
    db.upsert_venues(conn, rows)
    for w in ("2026-06-01", "2026-06-08"):
        db.replace_week(conn, w, [r for r in rows if r["week_start"] == w])
    return conn


def test_v_latest_off_exchange_aggregates_newest_week_by_symbol():
    conn = _seed()
    rows = conn.execute("SELECT symbol, total_shares FROM v_latest_off_exchange"
                        ).fetchall()
    # newest week 2026-06-08: B=400, A=300+50=350 -> B first
    assert rows == [("B", 400), ("A", 350)]


def test_v_top_dark_pools_ranks_venues_with_name():
    conn = _seed()
    rows = conn.execute(
        "SELECT mpid, ats_name, total_shares FROM v_top_dark_pools").fetchall()
    # newest week: M1 = 300+400 = 700, M2 = 50
    assert rows[0] == ("M1", "Pool One", 700)
    assert rows[1] == ("M2", "Pool Two", 50)


def test_v_symbol_venue_history_series():
    conn = _seed()
    rows = conn.execute(
        "SELECT week_start, share_quantity FROM v_symbol_venue_history "
        "WHERE symbol='A' AND mpid='M1' ORDER BY week_start").fetchall()
    assert rows == [("2026-06-01", 100), ("2026-06-08", 300)]
```

- [ ] **Step 2: Run test to verify it fails** — views don't exist yet.

- [ ] **Step 3: Write minimal implementation**

In `finra_ats/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- Off-exchange totals per symbol for the newest stored week.
CREATE VIEW IF NOT EXISTS v_latest_off_exchange AS
SELECT a.symbol,
       SUM(a.share_quantity) AS total_shares,
       SUM(a.trade_count)    AS total_trades,
       COUNT(DISTINCT a.mpid) AS venue_count
FROM ats_volume a
WHERE a.week_start = (SELECT MAX(week_start) FROM ats_volume)
GROUP BY a.symbol
ORDER BY total_shares DESC;

-- Biggest dark pools this (newest) week, with the ATS name.
CREATE VIEW IF NOT EXISTS v_top_dark_pools AS
SELECT a.mpid, v.ats_name,
       SUM(a.share_quantity) AS total_shares,
       SUM(a.trade_count)    AS total_trades
FROM ats_volume a
LEFT JOIN venues v ON v.mpid = a.mpid
WHERE a.week_start = (SELECT MAX(week_start) FROM ats_volume)
GROUP BY a.mpid, v.ats_name
ORDER BY total_shares DESC;

-- Per-(symbol, venue) weekly time series.
CREATE VIEW IF NOT EXISTS v_symbol_venue_history AS
SELECT a.symbol, a.mpid, v.ats_name, a.week_start, a.trade_count,
       a.share_quantity
FROM ats_volume a
LEFT JOIN venues v ON v.mpid = a.mpid
ORDER BY a.symbol, a.mpid, a.week_start;
"""
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add finra_ats/db.py tests/test_finra_ats_db_views.py
git commit -m "feat(ats): microstructure views — off-exchange leaders, top dark pools, venue history"
```

---

## Task 4: `finra_ats.run` — delay-aware week orchestration + CLI

**Files:**
- Create: `finra_ats/run.py`
- Test: `tests/test_finra_ats_run.py`

**Interfaces:**
- `weeks_in_range(start, end) -> list[str]` — Monday-anchored week-starts.
- `run(db_path, start=None, keep_days=None, full=False, fetch_week=fetch.fetch_week, now_iso=None) -> (snapshot_id, week_count, row_count)`.
- `main(argv=None)` — argparse, `prog="ats"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finra_ats_run.py`:

```python
import sqlite3

from finra_ats import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _row(week, symbol="A", mpid="M1"):
    return {"week_start": week, "symbol": symbol, "mpid": mpid,
            "ats_name": "ATS", "trade_count": 1, "share_quantity": 100,
            "tier": "T1"}


def test_weeks_in_range_monday_anchored():
    wks = runmod.weeks_in_range("2026-06-10", "2026-06-24")   # Wed .. Wed
    assert wks == ["2026-06-08", "2026-06-15", "2026-06-22"]  # Mondays


def test_run_delay_aware_end_and_counts(tmp_path):
    db_path = str(tmp_path / "a.db")
    fetched = []

    def fetch_week(week_start):
        fetched.append(week_start)
        return [_row(week_start)]

    sid, wc, rc = runmod.run(db_path, start="2026-06-01",
                             fetch_week=fetch_week, now_iso=NOW)
    # newest week must be floored ~2 weeks before 2026-07-03 -> no 2026-06-29+
    assert all(w <= "2026-06-22" for w in fetched)
    assert wc == len(fetched) and rc == wc


def test_run_incremental_skips_stored_but_refetches_trailing(tmp_path):
    db_path = str(tmp_path / "a.db")
    runmod.run(db_path, start="2026-06-01",
               fetch_week=lambda w: [_row(w)], now_iso=NOW)
    second = []

    def fetch_week(week_start):
        second.append(week_start)
        return [_row(week_start)]

    runmod.run(db_path, start="2026-06-01", fetch_week=fetch_week, now_iso=NOW)
    # only the trailing 2 stored weeks are re-fetched on the second run
    assert len(second) == 2


def test_run_none_week_skipped_and_failure_hides_secret(tmp_path, capsys):
    db_path = str(tmp_path / "a.db")

    def fetch_week(week_start):
        if week_start == "2026-06-08":
            return None                          # not published -> skip
        if week_start == "2026-06-15":
            raise RuntimeError("https://api.finra.org?x=SECRET boom")
        return [_row(week_start)]

    sid, wc, rc = runmod.run(db_path, start="2026-06-01",
                             fetch_week=fetch_week, now_iso=NOW)
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
    conn = sqlite3.connect(db_path)
    stored = {r[0] for r in conn.execute("SELECT week_start FROM weeks")}
    assert "2026-06-08" not in stored and "2026-06-15" not in stored


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "a.db")
    runmod.run(db_path, start="2026-06-01", fetch_week=lambda w: [_row(w)],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, start="2026-06-01", fetch_week=lambda w: [_row(w)],
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM ats_volume").fetchone()[0] >= 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `finra_ats/run.py`:

```python
import argparse
import sys
from datetime import date, datetime, timedelta, timezone

from finra_ats import db, fetch

_PUBLICATION_LAG_DAYS = 14      # newest fetchable week floored ~2 weeks back
_DEFAULT_LOOKBACK_DAYS = 182    # ~6 months
_REFETCH_WEEKS = 2              # re-absorb FINRA re-posts of the trailing weeks


def weeks_in_range(start: str, end: str) -> list:
    """Monday-anchored week-start dates from the Monday on/before start through
    end, inclusive."""
    s = date.fromisoformat(start)
    s -= timedelta(days=s.weekday())            # back to Monday
    e = date.fromisoformat(end)
    out = []
    while s <= e:
        out.append(s.isoformat())
        s += timedelta(days=7)
    return out


def _default_start(today: date) -> str:
    return (today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)).isoformat()


def run(db_path, start=None, keep_days=None, full=False,
        fetch_week=fetch.fetch_week, now_iso=None):
    """Enumerate delay-aware weeks, fetch new (and the trailing few) with
    replace-week writes, snapshot, optionally prune. Returns
    (snapshot_id, week_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = date.fromisoformat(now_iso[:10])
    end = (today - timedelta(days=_PUBLICATION_LAG_DAYS)).isoformat()
    start = start or _default_start(today)
    weeks = weeks_in_range(start, end)

    conn = db.connect(db_path)
    week_count, row_count = 0, 0
    try:
        db.ensure_schema(conn)
        stored = set(db.stored_weeks(conn))
        refetch = set() if full else set(sorted(stored)[-_REFETCH_WEEKS:])
        for w in weeks:
            if not full and w in stored and w not in refetch:
                continue
            try:
                rows = fetch_week(w)
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {w}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            if rows is None:                     # not published / absent
                continue
            db.upsert_venues(conn, rows)
            n = db.replace_week(conn, w, rows)
            db.record_week(conn, w, now_iso, n)
            week_count += 1
            row_count += n
        snapshot_id = db.write_snapshot(conn, now_iso, week_count, row_count)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, week_count, row_count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="ats",
        description="Pull FINRA weekly OTC/ATS (dark-pool) volume into SQLite")
    p.add_argument("--db", default="finra_ats.db")
    p.add_argument("--start", default=None,
                   help="earliest week to ingest (YYYY-MM-DD; default ~6mo back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every week in range")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, wc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} rows across {wc} weeks into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add finra_ats/run.py tests/test_finra_ats_run.py
git commit -m "feat(ats): delay-aware week orchestration (incremental + trailing refetch) + CLI"
```

---

## Task 5: Register `ats` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_ats():
    import registry
    assert "ats" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails** — `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import and register:

```python
from finra_ats.run import main as ats_main
```
```python
    "ats": ats_main,
```

- [ ] **Step 4: Run test to verify it passes** — `python -m pytest tests/test_registry.py -v`.

- [ ] **Step 5: Run the FULL suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(ats): register ats dispatcher"
```

---

## Task 6: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `ats` to Built**

- Add an `ats` row to the **Built ✅** table (link this plan + the spec).
- Remove the `ats` row from **Spec'd — data screeners 📝** (Deepen-publishers table).
- Update the "lower-priority tail" line to drop `ats` (leaving `nyfed`, `cboe_stats`, `eia`, `usda`). Note the deferred monthly non-ATS series follow-up.

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark ats Built"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| `week_body` compareFilters; `parse_rows` JSON+CSV, coercion, de-minimis sentinel, symbol/week guards | Task 1 |
| POST reuse of `http_client` backoff (body-capturing opener closure) | Task 1 |
| `fetch_week` 403/404 → None; 429/503 retried | Task 1 |
| `venues`/`ats_volume`/`weeks`/`snapshots` schema, `(week_start, symbol, mpid)` PK | Task 2 |
| `upsert_venues` (newest name, min/max seen); `replace_week` (delete+insert, no orphan); `record_week`; `stored_weeks`; single-table prune | Task 2 |
| `v_latest_off_exchange` / `v_top_dark_pools` / `v_symbol_venue_history` | Task 3 |
| `weeks_in_range` Monday-anchored; delay-aware end; incremental skip + trailing refetch + `--full`; skip-and-continue; secret hygiene | Task 4 |
| CLI `--db/--start/--full/--keep-days` | Task 4 |
| Registry `"ats"` | Task 5 |
| No credentials; `.env.example` unchanged; `now_iso` injected; no `catalog.py` | Global Constraints |

**2. Placeholder scan:** No `TODO` in code. 🟡 dataset slug/field names handled via the live-verification action (adjust parser + fixture together). Monthly non-ATS series is an explicit spec Non-goal, surfaced in the roadmap entry.

**3. Type consistency:** The fact-row keys (`week_start, symbol, mpid, ats_name, trade_count, share_quantity, tier`) are identical across `parse_rows` (Task 1), `upsert_venues`/`replace_week` named-param binds (Task 2), and every test helper. Counts are `int|None` via `_to_int`. `run` returns a 3-tuple `(snapshot_id, week_count, row_count)` used identically in tests. `stored_weeks` returns ascending ISO strings feeding the trailing-refetch slice.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-finra-ats-dark-pool-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
