# USDA WASDE / NASS Commodity Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `usda` screener — USDA crop supply/demand & ending-stocks data (corn, soybeans, wheat) from the NASS Quick Stats API into SQLite as a `(commodity, metric, period)` panel, with the **stocks-to-use ratio** and balance-sheet views derived in SQL.

**Architecture:** A panel screener like `eia`: `catalog`/`fetch`/`db`/`run` + registry, one `usda_obs` fact table upserted by `(commodity, metric, period)`, signals in views. Needs a **`NASS_API_KEY`** (query param, never logged). The catalog carries a **NASS query dict per `(commodity, metric)` target**. Reuses `screener_common.connect` (WAL), `http_client` backoff, FRED-style `select_ids` + single-table prune. **The last screener in the roadmap.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `os`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **Requires `NASS_API_KEY`** (free). Read via `require_api_key` (FRED pattern) — raise clearly if absent, **never echo the key**. Add `NASS_API_KEY=` to `.env.example` with a short comment.
- **Secret hygiene (key in URL):** per-target failures log **only** `type(e).__name__` — never `str(e)`/`e.url`. Retry `{429, 500, 502, 503, 504}`; UA `agentic-trading-bot ninadk.dev@gmail.com`.
- **`now_iso` injected, never wall-clock.** `run()` accepts `now_iso=None`; `fetch_target` injected so tests are network-free.
- **Upsert by `(commodity, metric, period)`** — revisions overwrite in place; periods never duplicate.
- **Withheld/blank NASS values → NULL, never 0.0** (`(D)`/`(Z)`/`(NA)` markers).
- **Skip-and-continue** per target: `conn.rollback()`, type-name-only log, continue. Zero successes → still `write_snapshot(…,0,0)` and warn; never raise.
- **Prune is FRED-style single-table** — delete old `snapshots` only; never touch `usda_obs`. Call this out in `db.py`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest`.
- **Commits:** no co-author line; use `git commit --no-gpg-sign` (this repo's ssh/1Password signing hangs non-interactively).

### Live-verification action (🟡)

Quick Stats params + `short_desc` values located but not verified, and full WASDE-native balance sheets live in OCE/ESMIS (not Quick Stats). Confirm live (needs the key) and adjust the catalog + fixtures together: each target's `short_desc`/`statisticcat_desc`, that each query stays under NASS's **50,000-row cap** (narrow to `agg_level_desc=NATIONAL` + annual + a specific `short_desc`), and the `data[]`/`Value`/`unit_desc` field names. v1 sources what Quick Stats exposes (production, stocks, use); WASDE-native ingestion is a documented confirm-then-wire follow-up.

---

## File Structure

**New — `usda_screener/` package:** `__init__.py`, `catalog.py`, `fetch.py`, `db.py`, `run.py`.
**Modified:** `registry.py` — register `"usda"`; `.env.example` — add `NASS_API_KEY=`.
**New tests:** `test_usda_catalog.py`, `test_usda_fetch.py`, `test_usda_db_schema.py`, `test_usda_db_write.py`, `test_usda_run.py`, + one `test_registry.py` assertion.

---

## Task 1: `usda_screener.catalog` — (commodity, metric) targets + select_ids

**Files:** Create `usda_screener/__init__.py` (empty), `usda_screener/catalog.py`; Test `tests/test_usda_catalog.py`.

**Interfaces:** `Series(commodity, metric, query)` with an `.id` property (`"COMMODITY:METRIC"`); `CATALOG`; `select_ids(all_ids, only, exclude, add=None)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_usda_catalog.py`:

```python
from usda_screener.catalog import CATALOG, Series, select_ids


def test_catalog_ids_unique_and_have_query():
    ids = [s.id for s in CATALOG]
    assert len(ids) == len(set(ids))
    for s in CATALOG:
        assert isinstance(s.query, dict) and s.query
        assert ":" in s.id


def test_catalog_covers_corn_soy_wheat_balance():
    ids = {s.id for s in CATALOG}
    assert {"CORN:ENDING_STOCKS", "CORN:TOTAL_USE", "SOYBEANS:ENDING_STOCKS",
            "WHEAT:ENDING_STOCKS"} <= ids


def test_select_ids_default_only_exclude_add():
    ids = [s.id for s in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["CORN:ENDING_STOCKS", "CORN:ENDING_STOCKS"], None) \
        == ["CORN:ENDING_STOCKS"]
    assert "CORN:ENDING_STOCKS" not in select_ids(ids, None, ["CORN:ENDING_STOCKS"])
    assert select_ids(ids, ["CORN:TOTAL_USE"], None,
                      add=["WHEAT:TOTAL_USE", " WHEAT:TOTAL_USE "]) \
        == ["CORN:TOTAL_USE", "WHEAT:TOTAL_USE"]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `usda_screener/__init__.py` (empty). Create `usda_screener/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    commodity: str   # CORN | SOYBEANS | WHEAT
    metric: str      # PRODUCTION | ENDING_STOCKS | TOTAL_USE  (our label)
    query: dict      # NASS Quick Stats filter (short_desc, statisticcat_desc, ...)

    @property
    def id(self) -> str:
        return f"{self.commodity}:{self.metric}"


def _q(commodity, statcat, short_desc):
    return {"commodity_desc": commodity, "statisticcat_desc": statcat,
            "agg_level_desc": "NATIONAL", "short_desc": short_desc,
            "year__GE": "2000"}


# Curated corn/soy/wheat balance-sheet targets. short_desc / statisticcat_desc
# ids are 🟡 — confirm live under NASS's 50k-row cap; drop any that error.
CATALOG: list[Series] = [
    Series("CORN", "PRODUCTION", _q("CORN", "PRODUCTION",
           "CORN, GRAIN - PRODUCTION, MEASURED IN BU")),
    Series("CORN", "ENDING_STOCKS", _q("CORN", "STOCKS",
           "CORN, GRAIN - STOCKS, MEASURED IN BU")),
    Series("CORN", "TOTAL_USE", _q("CORN", "USE",
           "CORN, GRAIN - USE, TOTAL, MEASURED IN BU")),
    Series("SOYBEANS", "PRODUCTION", _q("SOYBEANS", "PRODUCTION",
           "SOYBEANS - PRODUCTION, MEASURED IN BU")),
    Series("SOYBEANS", "ENDING_STOCKS", _q("SOYBEANS", "STOCKS",
           "SOYBEANS - STOCKS, MEASURED IN BU")),
    Series("SOYBEANS", "TOTAL_USE", _q("SOYBEANS", "USE",
           "SOYBEANS - USE, TOTAL, MEASURED IN BU")),
    Series("WHEAT", "PRODUCTION", _q("WHEAT", "PRODUCTION",
           "WHEAT - PRODUCTION, MEASURED IN BU")),
    Series("WHEAT", "ENDING_STOCKS", _q("WHEAT", "STOCKS",
           "WHEAT - STOCKS, MEASURED IN BU")),
    Series("WHEAT", "TOTAL_USE", _q("WHEAT", "USE",
           "WHEAT - USE, TOTAL, MEASURED IN BU")),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated composite ids (FRED select_ids semantics)."""
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

- [ ] **Step 4: Run test to verify it passes** — PASS (3 tests).
- [ ] **Step 5: Commit** — `git add usda_screener/__init__.py usda_screener/catalog.py tests/test_usda_catalog.py && git commit --no-gpg-sign -m "feat(usda): curated corn/soy/wheat balance-sheet catalog + select_ids"`

---

## Task 2: `usda_screener.fetch` — Quick Stats client + parser

**Files:** Create `usda_screener/fetch.py`; Modify `.env.example`; Test `tests/test_usda_fetch.py`.

**Interfaces:** `require_api_key(api_key)`; `_build_url(query, api_key)`; `parse_response(payload) -> list[dict]`; `fetch_target(query, api_key, get=_http_get) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_usda_fetch.py`:

```python
import json
import urllib.error

import pytest

from usda_screener import fetch


def test_require_api_key_raises_without_echoing():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "NASS_API_KEY" in str(exc.value)
    assert fetch.require_api_key("KEY") == "KEY"


def test_build_url_includes_key_format_and_filters():
    url = fetch._build_url({"commodity_desc": "CORN",
                            "statisticcat_desc": "STOCKS"}, "SECRET")
    assert url.startswith("https://quickstats.nass.usda.gov/api/api_GET/?")
    assert "key=SECRET" in url and "format=JSON" in url
    assert "commodity_desc=CORN" in url and "statisticcat_desc=STOCKS" in url


def test_parse_response_coerces_and_withheld_to_none():
    payload = {"data": [
        {"year": 2025, "Value": "1,875,000,000", "unit_desc": "BU"},
        {"year": 2024, "Value": "(D)", "unit_desc": "BU"},        # withheld
        {"Value": "5", "unit_desc": "BU"},                         # no year -> drop
    ]}
    rows = fetch.parse_response(payload)
    assert len(rows) == 2
    assert rows[0] == {"period": "2025", "value": 1875000000.0, "unit": "BU"}
    assert rows[1]["value"] is None


def test_fetch_target_calls_get_and_parses():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"data": [{"year": 2025, "Value": "10",
                                     "unit_desc": "BU"}]})

    rows = fetch.fetch_target({"commodity_desc": "WHEAT"}, "K", get=get)
    assert rows[0]["value"] == 10.0 and "commodity_desc=WHEAT" in seen["url"]


def test_http_get_retries_503():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "e", {}, None)
        return "{}"

    fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert calls["n"] == 2 and slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `usda_screener/fetch.py`:

```python
"""USDA NASS Quick Stats API client. Near-clone of eia_screener.fetch: an API key
in the query string (never logged) + a pure parser. Withheld markers ((D)/(Z)/
(NA)) and blanks map to None."""
import json
import time
import urllib.parse

import http_client

API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

__all__ = ["require_api_key", "parse_response", "fetch_target"]


def require_api_key(api_key):
    """Return a non-empty key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError(
            "NASS_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    """Comma-stripped float; withheld ((D)/(Z)/(NA)) or blank -> None."""
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v or v.startswith("("):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _build_url(query, api_key) -> str:
    pairs = [("key", api_key), ("format", "JSON")] + sorted(query.items())
    return API_URL + "?" + urllib.parse.urlencode(pairs)


def parse_response(payload) -> list:
    """Map NASS data[] to [{period, value, unit}]. period is the year; rows with
    no year are dropped."""
    rows = []
    for d in payload.get("data") or []:
        year = d.get("year")
        if year in (None, ""):
            continue
        rows.append({"period": str(year), "value": _num(d.get("Value")),
                     "unit": d.get("unit_desc")})
    return rows


def fetch_target(query, api_key, get=_http_get) -> list:
    """GET one (commodity, metric) target's rows via its NASS query dict."""
    return parse_response(json.loads(get(_build_url(query, api_key))))
```

Also append to `.env.example`:

```
# Free key for the USDA NASS Quick Stats API (https://quickstats.nass.usda.gov/api/) — used by the `usda` screener
NASS_API_KEY=
```

- [ ] **Step 4: Run test to verify it passes** — PASS (5 tests).
- [ ] **Step 5: Commit** — `git add usda_screener/fetch.py tests/test_usda_fetch.py .env.example && git commit --no-gpg-sign -m "feat(usda): NASS Quick Stats client (key) + response parser; .env.example key"`

---

## Task 3: `usda_screener.db` — schema + writer + views + prune

**Files:** Create `usda_screener/db.py`; Test `tests/test_usda_db_schema.py`, `tests/test_usda_db_write.py`.

*(Views are small here; created with the schema — no staging needed. The write test exercises `v_stocks_to_use`.)*

**Interfaces:** `connect`; `ensure_schema`; `write_observations(conn, commodity, metric, rows) -> int`; `write_snapshot(conn, captured_at, series_count, observation_count) -> int`; `prune(conn, keep_days, now_iso) -> int`. Views: `v_latest_balance`, `v_stocks_to_use`, `v_series_history`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_usda_db_schema.py`:

```python
from usda_screener import db


def test_ensure_schema_creates_table_and_views_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"snapshots", "usda_obs"} <= tables
    assert {"v_latest_balance", "v_stocks_to_use", "v_series_history"} <= views
```

Create `tests/test_usda_db_write.py`:

```python
from usda_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_observations_upsert_in_place():
    conn = _fresh()
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 1800.0, "unit": "BU"}])
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 1875.0, "unit": "BU"}])
    assert conn.execute("SELECT value FROM usda_obs").fetchall() == [(1875.0,)]


def test_v_stocks_to_use_ratio():
    conn = _fresh()
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 2000.0, "unit": "BU"}])
    db.write_observations(conn, "CORN", "TOTAL_USE",
                          [{"period": "2025", "value": 14000.0, "unit": "BU"}])
    row = conn.execute("SELECT ending_stocks, total_use, stocks_to_use "
                       "FROM v_stocks_to_use WHERE commodity='CORN'").fetchone()
    assert row[0] == 2000.0 and row[1] == 14000.0
    assert abs(row[2] - (2000.0 / 14000.0)) < 1e-9


def test_v_stocks_to_use_null_when_total_use_absent():
    conn = _fresh()
    db.write_observations(conn, "WHEAT", "ENDING_STOCKS",
                          [{"period": "2025", "value": 800.0, "unit": "BU"}])
    row = conn.execute("SELECT total_use, stocks_to_use FROM v_stocks_to_use "
                       "WHERE commodity='WHEAT'").fetchone()
    assert row == (None, None)                    # partial selection -> NULL


def test_prune_snapshots_not_obs():
    conn = _fresh()
    db.write_observations(conn, "CORN", "PRODUCTION",
                          [{"period": "2025", "value": 15000.0, "unit": "BU"}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `usda_screener/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "write_observations", "write_snapshot",
           "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,
    series_count      INTEGER NOT NULL,
    observation_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usda_obs (
    commodity TEXT NOT NULL,
    metric    TEXT NOT NULL,
    period    TEXT NOT NULL,
    value     REAL,
    unit      TEXT,
    PRIMARY KEY (commodity, metric, period)
);
CREATE INDEX IF NOT EXISTS ix_usda_obs_period ON usda_obs(period);

-- Latest period per (commodity, metric): current balance-sheet lines.
CREATE VIEW IF NOT EXISTS v_latest_balance AS
WITH ranked AS (
    SELECT commodity, metric, period, value, unit,
           ROW_NUMBER() OVER (PARTITION BY commodity, metric
                              ORDER BY period DESC) AS rn
    FROM usda_obs WHERE value IS NOT NULL
)
SELECT commodity, metric, period, value, unit FROM ranked WHERE rn = 1;

-- The key gauge: ending_stocks / total_use per commodity per period.
CREATE VIEW IF NOT EXISTS v_stocks_to_use AS
SELECT es.commodity, es.period, es.value AS ending_stocks,
       tu.value AS total_use,
       CASE WHEN tu.value IS NOT NULL AND tu.value <> 0
            THEN es.value / tu.value END AS stocks_to_use
FROM usda_obs es
LEFT JOIN usda_obs tu ON tu.commodity = es.commodity
     AND tu.period = es.period AND tu.metric = 'TOTAL_USE'
WHERE es.metric = 'ENDING_STOCKS';

-- Full history per (commodity, metric).
CREATE VIEW IF NOT EXISTS v_series_history AS
SELECT commodity, metric, period, value, unit FROM usda_obs
ORDER BY commodity, metric, period;
"""


def ensure_schema(conn) -> None:
    """Create the fact table + views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def write_observations(conn, commodity, metric, rows) -> int:
    """Upsert obs by (commodity, metric, period): revisions overwrite in place,
    periods never duplicate. Dedupe within batch (last wins)."""
    by_period = {r["period"]: r for r in rows}
    conn.executemany(
        """INSERT INTO usda_obs (commodity, metric, period, value, unit)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(commodity, metric, period) DO UPDATE SET
             value=excluded.value, unit=excluded.unit""",
        [(commodity, metric, p, r["value"], r.get("unit"))
         for p, r in by_period.items()])
    conn.commit()
    return len(by_period)


def write_snapshot(conn, captured_at, series_count, observation_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) "
        "VALUES (?, ?, ?)", (captured_at, series_count, observation_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. usda_obs is the accumulated
    history and is NEVER cascade-pruned (FRED prune shape)."""
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
```

- [ ] **Step 4: Run tests to verify they pass** — PASS (1 + 4 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(usda): usda_obs schema + upsert writer + stocks-to-use views + prune"`

---

## Task 4: `usda_screener.run` — orchestration + CLI

**Files:** Create `usda_screener/run.py`; Test `tests/test_usda_run.py`.

**Interfaces:** `run(db_path, only=None, exclude=None, add=None, keep_days=None, api_key=None, now_iso=None, fetch_target=fetch.fetch_target) -> (snapshot_id, series_count, observation_count)`; `main(argv=None)` — `prog="usda"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_usda_run.py`:

```python
import sqlite3

from usda_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _rows(*pairs):
    return [{"period": p, "value": v, "unit": "BU"} for p, v in pairs]


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "u.db")

    def fetch_target(query, api_key):
        return _rows(("2025", 2000.0), ("2024", 1900.0))

    sid, sc, oc = runmod.run(db_path, only=["CORN:ENDING_STOCKS"], api_key="K",
                             fetch_target=fetch_target, now_iso=NOW)
    assert sc == 1 and oc == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 2


def test_run_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NASS_API_KEY", raising=False)
    try:
        runmod.run(str(tmp_path / "u.db"), now_iso=NOW)
        assert False, "expected RuntimeError for missing key"
    except RuntimeError as e:
        assert "NASS_API_KEY" in str(e)


def test_run_skips_failing_target_hides_key(tmp_path, capsys):
    def fetch_target(query, api_key):
        if query["commodity_desc"] == "CORN":
            raise RuntimeError("https://quickstats?key=SECRETKEY boom")
        return _rows(("2025", 1.0))

    sid, sc, oc = runmod.run(
        str(tmp_path / "u.db"),
        only=["CORN:ENDING_STOCKS", "SOYBEANS:ENDING_STOCKS"], api_key="K",
        fetch_target=fetch_target, now_iso=NOW)
    assert sc == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRETKEY" not in err


def test_run_add_known_pair(tmp_path):
    seen = []

    def fetch_target(query, api_key):
        seen.append(query["commodity_desc"])
        return _rows(("2025", 1.0))

    runmod.run(str(tmp_path / "u.db"), only=[], add=["WHEAT:PRODUCTION"],
               api_key="K", fetch_target=fetch_target, now_iso=NOW)
    assert "WHEAT" in seen


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(query, api_key):
        raise RuntimeError("x")

    sid, sc, oc = runmod.run(str(tmp_path / "u.db"), only=["CORN:PRODUCTION"],
                             api_key="K", fetch_target=boom, now_iso=NOW)
    assert (sc, oc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "u.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_obs(tmp_path):
    db_path = str(tmp_path / "u.db")

    def fetch_target(query, api_key):
        return _rows(("2025", 1.0))

    runmod.run(db_path, only=["CORN:PRODUCTION"], api_key="K",
               fetch_target=fetch_target, now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["CORN:PRODUCTION"], api_key="K",
               fetch_target=fetch_target, now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `usda_screener/run.py`:

```python
import argparse
import os
import sys
from datetime import datetime, timezone

from usda_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, keep_days=None, api_key=None,
        now_iso=None, fetch_target=fetch.fetch_target):
    """Fetch selected USDA targets, upsert obs, snapshot, optionally prune.
    Skip-and-continue. Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("NASS_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    by_id = {s.id: s for s in catalog.CATALOG}
    ids = catalog.select_ids([s.id for s in catalog.CATALOG], only, exclude,
                             add=add)

    conn = db.connect(db_path)
    successes, total_obs = 0, 0
    try:
        db.ensure_schema(conn)
        for cid in ids:
            s = by_id.get(cid)
            if s is None:
                print(f"warning: unknown target {cid}", file=sys.stderr)
                continue
            try:
                rows = fetch_target(s.query, api_key)
                n = db.write_observations(conn, s.commodity, s.metric, rows)
            except Exception as e:  # key rides in the URL -> type name only
                conn.rollback()
                print(f"warning: skipping {cid}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_obs += n

        if successes == 0:
            print("warning: no USDA targets fetched (0 series, 0 observations)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_obs)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_obs


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="usda",
        description="Pull USDA crop supply/demand balance-sheet data into SQLite")
    p.add_argument("--db", default="usda.db")
    p.add_argument("--only", default=None, help="comma-separated COMMODITY:METRIC")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra catalog-known COMMODITY:METRIC (repeatable)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, sc, oc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} targets into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes** — PASS (6 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(usda): run orchestration (skip-and-continue, secret hygiene) + CLI"`

---

## Task 5: Register `usda` in the dispatcher

**Files:** Modify `registry.py`; Test `tests/test_registry.py` (+1 assertion).

- [ ] **Step 1:** Add `def test_dispatch_lists_usda():\n    import registry\n    assert "usda" in registry.REGISTRY`.
- [ ] **Step 2:** Run → `AssertionError`.
- [ ] **Step 3:** In `registry.py` add `from usda_screener.run import main as usda_main` and `"usda": usda_main,`.
- [ ] **Step 4:** Run `python -m pytest tests/test_registry.py -v` → PASS.
- [ ] **Step 5:** Run full `python -m pytest` → PASS. Commit `git commit --no-gpg-sign -m "feat(usda): register usda dispatcher"`.

---

## Task 6: Roadmap bookkeeping — **completes the roadmap**

- [ ] Add a `usda` row to **Built ✅** (link this plan + spec); remove `usda` from **Spec'd — data screeners** (the table's "New official sources" section is now empty — note that). Update the build-order tail line to mark `usda` ✅ Built and state that **the entire roadmap is now complete** (no screeners/monitors remain in any Spec'd/Planned state). Commit `git commit --no-gpg-sign -m "docs(roadmap): mark usda Built — roadmap complete"`.

---

## Self-Review

**1. Spec coverage:** `(commodity, metric)` catalog with NASS query dicts + composite-id `select_ids` (Task 1); `require_api_key` (never echoes), `_build_url` (key + format + filters), `parse_response` (comma-strip, `(D)`→None, year→period), `.env.example` key (Task 2); `usda_obs` schema, upsert by `(commodity, metric, period)`, `v_latest_balance`/`v_stocks_to_use` (self-join ratio, NULL-safe)/`v_series_history`, single-table prune (Task 3); `run` skip-and-continue, secret hygiene (key never leaked), `--add COMMODITY:METRIC`, all-fail→(0,0) + CLI (Task 4); registry (Task 5). `now_iso` injected.

**2. Placeholder scan:** No `TODO`. 🟡 `short_desc`/params handled via the live-verification action; WASDE-native balance sheet (OCE/ESMIS) is a documented confirm-then-wire follow-up (v1 sources Quick Stats production/stocks/use). `--add` is catalog-known-pairs only, as the spec requires.

**3. Type consistency:** `fetch_target(query, api_key)` returns `[{period, value, unit}]` consumed identically in `run` and tests; obs-row keys match `write_observations`. `require_api_key` gate runs before any fetch. `Series.id` (`"COMMODITY:METRIC"`) is the select/lookup key throughout. `run` returns a 3-tuple used identically across tests.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-usda-wasde-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit, `--no-gpg-sign`) per task, full `python -m pytest` before the roadmap commit. **This is the final screener — the roadmap is complete after it merges.**
