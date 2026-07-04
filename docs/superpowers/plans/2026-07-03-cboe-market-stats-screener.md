# CBOE Market Statistics Screener (Put/Call + VIX) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `cboe_stats` screener — market-wide options-sentiment time series (put/call ratios by product + total volume; VIX/VIX3M/VIX9D/VVIX levels) into SQLite, with contrarian/regime views (put/call extremes, VIX term structure, at-a-glance sentiment).

**Architecture:** A CSV time-series screener like FRED (`catalog`/`fetch`/`db`/`run` + registry). Two fact tables (`pcr_daily`, `vix_daily`), **upserted by `date`** with **column-merge** semantics (each vol feed owns only its columns). Shares only the CBOE-CDN UA + `http_client` backoff with `cboe_options` — no shared tables/code. FRED-style single-table prune. **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `csv`, `io`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** CBOE CDN CSVs are public; `.env.example` unchanged. UA `agentic-trading-bot ninadk.dev@gmail.com`; retry `{429, 503}`; **403/404 on a feed → skip that feed** (CBOE CDN 403s withdrawn files), not a retry.
- **`now_iso` injected, never wall-clock.** `run()` accepts `now_iso=None`; `fetch_pcr`/`fetch_vix` injected so tests are network-free. **Dates come from the CSV, never the clock.**
- **Column-merge upsert.** Each feed writes only its own columns onto the shared `date` row (`ON CONFLICT(date) DO UPDATE SET <this feed's cols>`), so a partial `--only` run never blanks a sibling column.
- **Missing/blank cells → NULL, never 0.0.**
- **Skip-and-continue** per feed: `conn.rollback()`, log **only** `type(e).__name__`, continue. Zero successes → still `write_snapshot(…,0,0)` and warn; never raise.
- **Prune is FRED-style single-table** — delete old `snapshots` only; never touch `pcr_daily`/`vix_daily`. Call this out in `db.py`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest`.
- **Commits:** no co-author line; use `git commit --no-gpg-sign` (this repo's ssh/1Password signing hangs non-interactively).

### Live-verification action (🟡)

CSV routes + headers located but not verified. Confirm live and adjust parser + fixtures together: the PCR market-statistics CSV URL + its column headers (the fixture assumes `DATE,TOTAL_PCR,EQUITY_PCR,INDEX_PCR,TOTAL_VOLUME`), and each vol-index CSV URL (`{FEED}_History.csv` on the CBOE CDN) + header (some carry a preamble line before `DATE,OPEN,HIGH,LOW,CLOSE`). Drop any feed that 403/404s with a note. The parsers are tolerant (header-search, MM/DD/YYYY-or-ISO dates, single-value fallback) so minor drift is absorbed; a header rename that yields zero rows is the failure to catch live.

---

## File Structure

**New — `cboe_stats/` package:** `__init__.py`, `catalog.py`, `fetch.py`, `db.py`, `run.py`.
**Modified:** `registry.py` — register `"cboe_stats"`.
**New tests:** `test_cboe_stats_catalog.py`, `test_cboe_stats_fetch.py`, `test_cboe_stats_db_schema.py`, `test_cboe_stats_db_write.py`, `test_cboe_stats_db_views.py`, `test_cboe_stats_run.py`, + one `test_registry.py` assertion.

---

## Task 1: `cboe_stats.catalog` — Feed catalog + select_ids

**Files:** Create `cboe_stats/__init__.py` (empty), `cboe_stats/catalog.py`; Test `tests/test_cboe_stats_catalog.py`.

**Interfaces:** `Feed(feed_id, kind)`; `CATALOG`; `select_ids(all_ids, only, exclude, add=None)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cboe_stats_catalog.py`:

```python
from cboe_stats.catalog import CATALOG, Feed, select_ids


def test_catalog_has_pcr_and_vol_indices():
    by_id = {f.feed_id: f for f in CATALOG}
    assert by_id["PCR"].kind == "pcr"
    assert {"VIX", "VIX3M", "VIX9D", "VVIX"} <= set(by_id)
    assert by_id["VIX"].kind == "vix"


def test_select_ids_default_only_exclude_add():
    ids = [f.feed_id for f in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["VIX", "VIX"], None) == ["VIX"]
    assert "VIX" not in select_ids(ids, None, ["VIX"])
    assert select_ids(ids, ["VIX"], None, add=["RVX", " RVX "]) == ["VIX", "RVX"]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `cboe_stats/__init__.py` (empty). Create `cboe_stats/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    feed_id: str   # PCR | VIX | VIX3M | VIX9D | VVIX
    kind: str      # "pcr" | "vix"


CATALOG: list[Feed] = [
    Feed("PCR", "pcr"),
    Feed("VIX", "vix"),
    Feed("VIX3M", "vix"),
    Feed("VIX9D", "vix"),
    Feed("VVIX", "vix"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated feed ids (FRED select_ids semantics)."""
    ids = list(only) if only else list(all_ids)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for i in list(ids) + list(add or ()):
        i = i.strip()
        if not i or i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out
```

- [ ] **Step 4: Run test to verify it passes** — PASS (2 tests).
- [ ] **Step 5: Commit** — `git add cboe_stats/__init__.py cboe_stats/catalog.py tests/test_cboe_stats_catalog.py && git commit --no-gpg-sign -m "feat(cboe_stats): put/call + vol-index feed catalog + select_ids"`

---

## Task 2: `cboe_stats.fetch` — CBOE CDN CSV client + parsers

**Files:** Create `cboe_stats/fetch.py`; Test `tests/test_cboe_stats_fetch.py`.

**Interfaces:** `parse_pcr_csv(text)`, `parse_vix_csv(text)`, `fetch_pcr(get=_http_get)`, `fetch_vix(feed_id, get=_http_get)` (return `None` on 403/404).

- [ ] **Step 1: Write the failing test**

Create `tests/test_cboe_stats_fetch.py`:

```python
import urllib.error

from cboe_stats import fetch

_PCR = ("DATE,TOTAL_PCR,EQUITY_PCR,INDEX_PCR,TOTAL_VOLUME\n"
        "2026-06-01,0.95,0.72,1.40,\"45,000,000\"\n"
        ",0.9,0.7,1.2,100\n")                       # blank date dropped
_VIX = ("Preamble line to skip\n"
        "DATE,OPEN,HIGH,LOW,CLOSE\n"
        "06/01/2026,14.1,15.0,13.9,14.6\n")
_VVIX = "DATE,VVIX\n2026-06-01,95.2\n"


def test_parse_pcr_csv_coerces_and_strips_commas():
    rows = fetch.parse_pcr_csv(_PCR)
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-06-01"
    assert rows[0]["equity_pcr"] == 0.72
    assert rows[0]["total_volume"] == 45000000       # comma-stripped int


def test_parse_vix_csv_skips_preamble_and_parses_mmddyyyy():
    rows = fetch.parse_vix_csv(_VIX)
    assert rows[0]["date"] == "2026-06-01"           # 06/01/2026 normalized
    assert rows[0]["close"] == 14.6 and rows[0]["open"] == 14.1


def test_parse_vix_csv_single_value_fallback_close():
    rows = fetch.parse_vix_csv(_VVIX)                 # DATE,VVIX (no CLOSE col)
    assert rows[0]["date"] == "2026-06-01" and rows[0]["close"] == 95.2


def test_fetch_vix_returns_none_on_403():
    def get(url):
        raise urllib.error.HTTPError(url, 403, "no", {}, None)

    assert fetch.fetch_vix("VIX", get=get) is None


def test_http_get_retries_503():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "e", {}, None)
        return _VVIX

    out = fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert out == _VVIX and slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `cboe_stats/fetch.py`:

```python
"""CBOE market-statistics + VIX CSV client. Shares only the CBOE-CDN UA and the
bounded-backoff helper with cboe_options — nothing else. Pure CSV parsers,
network-free-testable. Dates come from the CSV, never the wall clock."""
import csv
import io
import time
import urllib.error
from datetime import datetime

import http_client

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

# 🟡 confirm live: PCR market-statistics CSV route + the per-index CDN CSVs.
PCR_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/put_call_ratio.csv"
_VIX_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"

__all__ = ["parse_pcr_csv", "parse_vix_csv", "fetch_pcr", "fetch_vix"]


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int(v):
    f = _num(v)
    return int(f) if f is not None else None


def _norm_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_pcr_csv(text) -> list:
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        norm = {(k or "").strip().upper().replace(" ", "_").replace("/", "_"): v
                for k, v in rec.items()}
        d = _norm_date(norm.get("DATE"))
        if not d:
            continue
        rows.append({"date": d, "total_pcr": _num(norm.get("TOTAL_PCR")),
                     "equity_pcr": _num(norm.get("EQUITY_PCR")),
                     "index_pcr": _num(norm.get("INDEX_PCR")),
                     "total_volume": _int(norm.get("TOTAL_VOLUME"))})
    return rows


def parse_vix_csv(text) -> list:
    """Parse a CBOE index CSV. Skips any preamble before the DATE header.
    close = CLOSE column, or (single-series files like DATE,VVIX) the last cell."""
    rows = []
    header = None
    for parts in csv.reader(io.StringIO(text)):
        if not parts:
            continue
        upper = [p.strip().upper() for p in parts]
        if header is None:
            if "DATE" in upper:
                header = upper
            continue
        rec = dict(zip(header, parts))
        d = _norm_date(rec.get("DATE"))
        if not d:
            continue
        close = _num(rec.get("CLOSE"))
        if close is None and len(parts) > 1:
            close = _num(parts[-1])              # single-value fallback
        rows.append({"date": d, "open": _num(rec.get("OPEN")),
                     "high": _num(rec.get("HIGH")), "low": _num(rec.get("LOW")),
                     "close": close})
    return rows


def _get_csv(url, get):
    try:
        return get(url)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None                          # skip this feed
        raise


def fetch_pcr(get=_http_get):
    text = _get_csv(PCR_URL, get)
    return None if text is None else parse_pcr_csv(text)


def fetch_vix(feed_id, get=_http_get):
    text = _get_csv(f"{_VIX_BASE}/{feed_id}_History.csv", get)
    return None if text is None else parse_vix_csv(text)
```

- [ ] **Step 4: Run test to verify it passes** — PASS (5 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(cboe_stats): CBOE CDN CSV client + put/call & VIX parsers"`

---

## Task 3: `cboe_stats.db` — schema + column-merge writers + prune

**Files:** Create `cboe_stats/db.py` (views deferred to Task 4); Test `tests/test_cboe_stats_db_schema.py`, `tests/test_cboe_stats_db_write.py`.

**Interfaces:** `connect`; `ensure_schema`; `write_pcr(conn, rows)`; `write_vix(conn, feed_id, rows)`; `write_snapshot(conn, captured_at, feed_count, row_count)`; `prune(conn, keep_days, now_iso)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cboe_stats_db_schema.py`:

```python
from cboe_stats import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "pcr_daily", "vix_daily"} <= tables
```

Create `tests/test_cboe_stats_db_write.py`:

```python
from cboe_stats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_vix_column_merge_does_not_blank_siblings():
    conn = _fresh()
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 14.0, "high": 15.0,
                                "low": 13.5, "close": 14.6}])
    db.write_vix(conn, "VIX3M", [{"date": "2026-06-01", "open": None,
                                  "high": None, "low": None, "close": 16.2}])
    row = conn.execute(
        "SELECT close, vix3m FROM vix_daily WHERE date='2026-06-01'").fetchone()
    assert row == (14.6, 16.2)                   # VIX close preserved, vix3m added


def test_write_vix_reupsert_overwrites_in_place():
    conn = _fresh()
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 1, "high": 1,
                                "low": 1, "close": 14.6}])
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 1, "high": 1,
                                "low": 1, "close": 15.0}])
    assert conn.execute("SELECT close FROM vix_daily").fetchall() == [(15.0,)]


def test_write_pcr_upsert():
    conn = _fresh()
    n = db.write_pcr(conn, [{"date": "2026-06-01", "total_pcr": 0.95,
                             "equity_pcr": 0.72, "index_pcr": 1.4,
                             "total_volume": 45000000}])
    assert n == 1
    assert conn.execute("SELECT equity_pcr FROM pcr_daily").fetchone()[0] == 0.72


def test_prune_snapshots_not_facts():
    conn = _fresh()
    db.write_pcr(conn, [{"date": "2026-06-01", "total_pcr": 1.0, "equity_pcr": 1.0,
                         "index_pcr": 1.0, "total_volume": 1}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM pcr_daily").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `cboe_stats/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "write_pcr", "write_vix",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    feed_count  INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pcr_daily (
    date         TEXT PRIMARY KEY,
    total_pcr    REAL,
    equity_pcr   REAL,
    index_pcr    REAL,
    total_volume INTEGER
);
CREATE TABLE IF NOT EXISTS vix_daily (
    date  TEXT PRIMARY KEY,
    open  REAL, high REAL, low REAL, close REAL,
    vix3m REAL, vix9d REAL, vvix REAL
);
"""

# Which vix_daily columns each feed owns, and which parsed key fills them.
_VIX_MAP = {
    "VIX": {"open": "open", "high": "high", "low": "low", "close": "close"},
    "VIX3M": {"vix3m": "close"},
    "VIX9D": {"vix9d": "close"},
    "VVIX": {"vvix": "close"},
}


def ensure_schema(conn) -> None:
    """Create tables (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def write_pcr(conn, rows) -> int:
    by_date = {r["date"]: r for r in rows}
    conn.executemany(
        """INSERT INTO pcr_daily (date, total_pcr, equity_pcr, index_pcr,
                                  total_volume)
           VALUES (:date, :total_pcr, :equity_pcr, :index_pcr, :total_volume)
           ON CONFLICT(date) DO UPDATE SET
             total_pcr=excluded.total_pcr, equity_pcr=excluded.equity_pcr,
             index_pcr=excluded.index_pcr, total_volume=excluded.total_volume""",
        list(by_date.values()))
    conn.commit()
    return len(by_date)


def write_vix(conn, feed_id, rows) -> int:
    """Column-merge upsert: write only this feed's columns onto the date row, so a
    partial run never blanks a sibling column. Unknown feed (e.g. --add RVX with
    no column) is a no-op."""
    mapping = _VIX_MAP.get(feed_id)
    if not mapping:
        return 0
    cols = list(mapping)                          # vix_daily columns this feed owns
    by_date = {r["date"]: r for r in rows}
    params = [tuple([d] + [r.get(mapping[c]) for c in cols])
              for d, r in by_date.items()]
    collist = ", ".join(["date"] + cols)
    ph = ", ".join(["?"] * (1 + len(cols)))
    setc = ", ".join(f"{c}=excluded.{c}" for c in cols)
    conn.executemany(
        f"INSERT INTO vix_daily ({collist}) VALUES ({ph}) "
        f"ON CONFLICT(date) DO UPDATE SET {setc}", params)
    conn.commit()
    return len(by_date)


def write_snapshot(conn, captured_at, feed_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, feed_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, feed_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. pcr_daily/vix_daily are the
    accumulated history and are NEVER cascade-pruned (FRED prune shape)."""
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


_VIEWS = ""   # filled in Task 4
```

- [ ] **Step 4: Run tests to verify they pass** — PASS (1 + 4 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(cboe_stats): pcr/vix schema + column-merge upserts + prune"`

---

## Task 4: `cboe_stats.db` — sentiment views

**Files:** Modify `cboe_stats/db.py` (fill `_VIEWS`); Test `tests/test_cboe_stats_db_views.py`.

**Views:** `v_pcr_extremes`, `v_vix_term_structure`, `v_latest_sentiment`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cboe_stats_db_views.py`:

```python
from cboe_stats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_pcr_extremes_flags_fear_at_high_percentile():
    conn = _fresh()
    for d, e in [("2026-06-01", 0.5), ("2026-06-02", 0.6), ("2026-06-03", 0.7),
                 ("2026-06-04", 0.8), ("2026-06-05", 1.2)]:      # latest highest
        db.write_pcr(conn, [{"date": d, "total_pcr": e, "equity_pcr": e,
                             "index_pcr": None, "total_volume": None}])
    row = conn.execute("SELECT equity_pcr_pctile, equity_flag "
                       "FROM v_pcr_extremes").fetchone()
    assert row[0] == 0.8 and row[1] == "fear"    # 4/5 of history below 1.2


def test_v_vix_term_structure_backwardation_flag():
    conn = _fresh()
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": None, "high": None,
                                "low": None, "close": 20.0}])
    db.write_vix(conn, "VIX3M", [{"date": "2026-06-01", "close": 18.0,
                                  "open": None, "high": None, "low": None}])
    row = conn.execute("SELECT backwardation FROM v_vix_term_structure").fetchone()
    assert row[0] == 1                            # close 20 > vix3m 18 -> stress


def test_v_latest_sentiment_one_row():
    conn = _fresh()
    db.write_pcr(conn, [{"date": "2026-06-01", "total_pcr": 0.9, "equity_pcr": 0.7,
                         "index_pcr": None, "total_volume": None}])
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": None, "high": None,
                                "low": None, "close": 14.6}])
    rows = conn.execute("SELECT vix_close, equity_pcr FROM v_latest_sentiment"
                        ).fetchall()
    assert rows == [(14.6, 0.7)]
```

- [ ] **Step 2: Run test to verify it fails** — views don't exist.

- [ ] **Step 3: Write minimal implementation**

In `cboe_stats/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- Latest put/call vs its trailing percentile, with a contrarian flag.
CREATE VIEW IF NOT EXISTS v_pcr_extremes AS
WITH latest AS (SELECT * FROM pcr_daily ORDER BY date DESC LIMIT 1)
SELECT l.date, l.total_pcr, l.equity_pcr,
       (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
        WHERE equity_pcr IS NOT NULL) AS equity_pcr_pctile,
       CASE
         WHEN (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
               WHERE equity_pcr IS NOT NULL) >= 0.8 THEN 'fear'
         WHEN (SELECT AVG(equity_pcr < l.equity_pcr) FROM pcr_daily
               WHERE equity_pcr IS NOT NULL) <= 0.2 THEN 'complacency'
         ELSE 'neutral' END AS equity_flag
FROM latest l;

-- Latest VIX vs VIX3M term structure (backwardation = stress).
CREATE VIEW IF NOT EXISTS v_vix_term_structure AS
WITH latest AS (
    SELECT * FROM vix_daily WHERE close IS NOT NULL ORDER BY date DESC LIMIT 1
)
SELECT date, close, vix3m,
       CASE WHEN vix3m IS NOT NULL AND vix3m <> 0 THEN close / vix3m END
         AS vix_vix3m_ratio,
       CASE WHEN vix3m IS NULL THEN NULL WHEN close > vix3m THEN 1 ELSE 0 END
         AS backwardation
FROM latest;

-- One-row at-a-glance sentiment readout.
CREATE VIEW IF NOT EXISTS v_latest_sentiment AS
SELECT
  (SELECT date FROM vix_daily WHERE close IS NOT NULL
   ORDER BY date DESC LIMIT 1) AS vix_date,
  (SELECT close FROM vix_daily WHERE close IS NOT NULL
   ORDER BY date DESC LIMIT 1) AS vix_close,
  (SELECT date FROM pcr_daily ORDER BY date DESC LIMIT 1) AS pcr_date,
  (SELECT equity_pcr FROM pcr_daily ORDER BY date DESC LIMIT 1) AS equity_pcr,
  (SELECT total_pcr FROM pcr_daily ORDER BY date DESC LIMIT 1) AS total_pcr,
  (SELECT backwardation FROM v_vix_term_structure) AS backwardation;
"""
```

- [ ] **Step 4: Run test to verify it passes** — PASS (3 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(cboe_stats): sentiment views — pcr extremes, VIX term structure, latest readout"`

---

## Task 5: `cboe_stats.run` — orchestration + CLI

**Files:** Create `cboe_stats/run.py`; Test `tests/test_cboe_stats_run.py`.

**Interfaces:** `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, now_iso=None, fetch_pcr=fetch.fetch_pcr, fetch_vix=fetch.fetch_vix) -> (snapshot_id, feed_count, row_count)`; `main(argv=None)` — `prog="cboe_stats"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cboe_stats_run.py`:

```python
import sqlite3

from cboe_stats import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _pcr(d):
    return [{"date": d, "total_pcr": 0.9, "equity_pcr": 0.7, "index_pcr": None,
             "total_volume": None}]


def _vix(d, close):
    return [{"date": d, "open": None, "high": None, "low": None, "close": close}]


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "c.db")
    sid, fc, rc = runmod.run(
        db_path, only=["PCR", "VIX", "VIX3M"],
        fetch_pcr=lambda: _pcr("2026-06-01"),
        fetch_vix=lambda fid: _vix("2026-06-01", 14.6 if fid == "VIX" else 16.0),
        now_iso=NOW)
    assert fc == 3 and rc == 3
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT close, vix3m FROM vix_daily").fetchone() == (14.6, 16.0)


def test_run_skips_failing_feed_hides_secret(tmp_path, capsys):
    def fetch_vix(fid):
        if fid == "VIX":
            raise RuntimeError("https://cdn.cboe.com?k=SECRET boom")
        return _vix("2026-06-01", 16.0)

    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["VIX", "VIX3M"],
                             fetch_vix=fetch_vix, now_iso=NOW)
    assert fc == 1                                 # VIX failed, VIX3M stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_none_feed_skipped(tmp_path):
    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["VIX"],
                             fetch_vix=lambda fid: None, now_iso=NOW)
    assert fc == 0 and rc == 0                      # 403/404 -> None -> skip


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    sid, fc, rc = runmod.run(str(tmp_path / "c.db"), only=["PCR"],
                             fetch_pcr=lambda: (_ for _ in ()).throw(RuntimeError("x")),
                             now_iso=NOW)
    assert (fc, rc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "c.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "c.db")
    runmod.run(db_path, only=["PCR"], fetch_pcr=lambda: _pcr("2026-06-01"),
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["PCR"], fetch_pcr=lambda: _pcr("2026-06-01"),
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM pcr_daily").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `cboe_stats/run.py`:

```python
import argparse
import sys
from datetime import datetime, timezone

from cboe_stats import catalog, db, fetch


def _filter_start(rows, start):
    return [r for r in rows if r["date"] >= start] if start else rows


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        now_iso=None, fetch_pcr=fetch.fetch_pcr, fetch_vix=fetch.fetch_vix):
    """Fetch selected CBOE feeds, upsert into pcr_daily/vix_daily, snapshot,
    optionally prune. Skip-and-continue. Returns
    (snapshot_id, feed_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    ids = catalog.select_ids([f.feed_id for f in catalog.CATALOG], only, exclude,
                             add)
    kind_by_id = {f.feed_id: f.kind for f in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for feed_id in ids:
            kind = kind_by_id.get(feed_id, "vix")  # --add unknown -> vix
            try:
                if kind == "pcr":
                    rows = fetch_pcr()
                    if rows is None:
                        continue                    # 403/404 skip
                    n = db.write_pcr(conn, _filter_start(rows, start))
                else:
                    rows = fetch_vix(feed_id)
                    if rows is None:
                        continue
                    n = db.write_vix(conn, feed_id, _filter_start(rows, start))
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {feed_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no CBOE feeds fetched (0 feeds, 0 rows)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cboe_stats",
        description="Pull CBOE market-wide put/call + VIX sentiment into SQLite")
    p.add_argument("--db", default="cboe_stats.db")
    p.add_argument("--only", default=None, help="comma-separated feed ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra vol-index feed id (repeatable)")
    p.add_argument("--start", default=None,
                   help="filter parsed rows to date >= this (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, fc, rc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {rc} rows across {fc} feeds into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes** — PASS (5 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(cboe_stats): run orchestration (skip-and-continue) + CLI"`

---

## Task 6: Register `cboe_stats` in the dispatcher

**Files:** Modify `registry.py`; Test `tests/test_registry.py` (+1 assertion).

- [ ] **Step 1:** Add `def test_dispatch_lists_cboe_stats():\n    import registry\n    assert "cboe_stats" in registry.REGISTRY`.
- [ ] **Step 2:** Run → `AssertionError`.
- [ ] **Step 3:** In `registry.py` add `from cboe_stats.run import main as cboe_stats_main` and `"cboe_stats": cboe_stats_main,`.
- [ ] **Step 4:** Run `python -m pytest tests/test_registry.py -v` → PASS.
- [ ] **Step 5:** Run full `python -m pytest` → PASS. Commit `git commit --no-gpg-sign -m "feat(cboe_stats): register cboe_stats dispatcher"`.

---

## Task 7: Roadmap bookkeeping

- [ ] Add a `cboe_stats` row to **Built ✅** (link this plan + spec); remove `cboe_stats` from **Spec'd — data screeners**; update the tail line to drop `cboe_stats` (leaving `eia`, `usda`); note the deferred OCC cleared-volume future add. Commit `git commit --no-gpg-sign -m "docs(roadmap): mark cboe_stats Built"`.

---

## Self-Review

**1. Spec coverage:** Feed catalog + `select_ids` (Task 1); CBOE CDN CSV client, `parse_pcr_csv`/`parse_vix_csv` (preamble skip, MM/DD/YYYY, single-value fallback, comma-int), 403/404→None (Task 2); `pcr_daily`/`vix_daily` schema, **column-merge** `write_vix`, `write_pcr`, single-table prune (Task 3); `v_pcr_extremes` (percentile+flag)/`v_vix_term_structure` (backwardation)/`v_latest_sentiment` (Task 4); `run` skip-and-continue/all-fail→(0,0)/secret hygiene + CLI (Task 5); registry (Task 6). No credentials; `now_iso` injected; dates from CSV.

**2. Placeholder scan:** No `TODO`. 🟡 CSV routes/headers handled via the live-verification action + tolerant parsers. `--add` unknown vol index is a documented no-op (no schema column) — not a crash.

**3. Type consistency:** Parser output keys match table columns; `write_vix` maps parsed `close` → the sibling column via `_VIX_MAP`. `_num`→`float|None`, `_int`→`int|None`. `run` returns a 3-tuple `(snapshot_id, feed_count, row_count)` used identically in tests. `kind` routes PCR vs VIX feeds consistently between catalog and run.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-cboe-market-stats-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit, `--no-gpg-sign`) per task, full `python -m pytest` before the roadmap commit.
