# EIA Energy Inventories Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `eia` screener — curated weekly EIA energy-inventory series (crude incl. Cushing, gasoline, distillate, production, imports, natural-gas storage) into SQLite as a FRED-style time series, with builds/draws (week-over-week change) derived in views.

**Architecture:** A near-clone of `fred_screener`: `catalog`/`fetch`/`db`/`run` + registry, a small `series` dimension + a `(series_id, period)` observation table upserted in place, signals in views. Differences from FRED: an **`EIA_API_KEY`** (query param, never logged), a **route+facet per series**, and EIA v2's **bracket-array query params**. Reuses `screener_common.connect` (WAL), `http_client` backoff, FRED-style `select_ids` + single-table prune.

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `os`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **Requires `EIA_API_KEY`** (free). Read via `require_api_key` (verbatim the FRED pattern) — raise clearly if absent, **never echo the key**. Add `EIA_API_KEY=` to `.env.example` with a short comment.
- **Secret hygiene (key in URL):** per-series failures log **only** `type(e).__name__` — never `str(e)`/`e.url` (an EIA `HTTPError.url` embeds the key). Retry `{429, 500, 502, 503, 504}`; UA `agentic-trading-bot ninadk.dev@gmail.com`.
- **Bracket-array params:** build the query as an **ordered list of `(key, value)` tuples** → `urllib.parse.urlencode(pairs, doseq=True)` so repeated `facets[series][]` survive.
- **`now_iso` injected, never wall-clock.** `run()` accepts `now_iso=None`; `fetch_series_obs` injected so tests are network-free.
- **Upsert by `(series_id, period)`** — revisions overwrite in place; periods never duplicate.
- **Skip-and-continue** per series: `conn.rollback()`, type-name-only log, continue. Zero successes → still `write_snapshot(…,0,0)` and warn; never raise.
- **Prune is FRED-style single-table** — delete old `snapshots` only; never touch `eia_obs`. Call this out in `db.py`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest`.
- **Commits:** no co-author line; use `git commit --no-gpg-sign` (this repo's ssh/1Password signing hangs non-interactively).

### Live-verification action (🟡)

v2 routes + facet ids located but not verified. Confirm live (needs the key) and adjust the catalog + fixtures together: each series' `route` + `facet` id, the `response.data[]` shape (`period`, `value`, `units`), and the bracket-param round-trip. Drop any series that 404s with a note.

---

## File Structure

**New — `eia_screener/` package:** `__init__.py`, `catalog.py`, `fetch.py`, `db.py`, `run.py`.
**Modified:** `registry.py` — register `"eia"`; `.env.example` — add `EIA_API_KEY=`.
**New tests:** `test_eia_catalog.py`, `test_eia_fetch.py`, `test_eia_db_schema.py`, `test_eia_db_write.py`, `test_eia_db_views.py`, `test_eia_run.py`, + one `test_registry.py` assertion.

---

## Task 1: `eia_screener.catalog` — curated series + select_ids

**Files:** Create `eia_screener/__init__.py` (empty), `eia_screener/catalog.py`; Test `tests/test_eia_catalog.py`.

**Interfaces:** `Series(series_id, route, facet, label, category)`; `CATALOG`; `select_ids(all_ids, only, exclude, add=None)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eia_catalog.py`:

```python
from eia_screener.catalog import CATALOG, Series, select_ids

_CATS = {"crude", "cushing", "gasoline", "distillate", "production", "imports",
         "natgas", "custom"}


def test_catalog_ids_unique_have_route_and_facet():
    ids = [s.series_id for s in CATALOG]
    assert len(ids) == len(set(ids))
    for s in CATALOG:
        assert s.route and s.facet and s.category in _CATS


def test_catalog_covers_headline_categories():
    cats = {s.category for s in CATALOG}
    assert {"crude", "cushing", "gasoline", "natgas"} <= cats


def test_select_ids_default_only_exclude_add():
    ids = [s.series_id for s in CATALOG]
    assert select_ids(ids, None, None) == ids
    first = ids[0]
    assert select_ids(ids, [first, first], None) == [first]
    assert first not in select_ids(ids, None, [first])
    assert select_ids(ids, [first], None, add=["X", " X "]) == [first, "X"]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `eia_screener/__init__.py` (empty). Create `eia_screener/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    series_id: str   # canonical key we store (often == facet)
    route: str       # v2 route, e.g. "petroleum/stoc/wstk"
    facet: str       # EIA facets[series][] value
    label: str
    category: str    # crude|cushing|gasoline|distillate|production|imports|natgas|custom


# Curated weekly WPSR + NG-storage series. Route/facet ids 🟡 confirm live; drop
# any that 404 with a note.
CATALOG: list[Series] = [
    Series("WCESTUS1", "petroleum/stoc/wstk", "WCESTUS1",
           "Crude oil stocks (ex-SPR)", "crude"),
    Series("W_EPC0_SAX_YCUOK_MBBL", "petroleum/stoc/wstk",
           "W_EPC0_SAX_YCUOK_MBBL", "Cushing OK crude stocks", "cushing"),
    Series("WGTSTUS1", "petroleum/stoc/wstk", "WGTSTUS1",
           "Total gasoline stocks", "gasoline"),
    Series("WDISTUS1", "petroleum/stoc/wstk", "WDISTUS1",
           "Distillate stocks", "distillate"),
    Series("WCRFPUS2", "petroleum/sum/sndw", "WCRFPUS2",
           "Crude oil field production", "production"),
    Series("WCRIMUS2", "petroleum/sum/sndw", "WCRIMUS2",
           "Crude oil imports", "imports"),
    Series("NW2_EPG0_SWO_R48_BCF", "natural-gas/stor/wkly",
           "NW2_EPG0_SWO_R48_BCF", "Working gas in storage (Lower 48)", "natgas"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated series ids (FRED select_ids semantics)."""
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
- [ ] **Step 5: Commit** — `git add eia_screener/__init__.py eia_screener/catalog.py tests/test_eia_catalog.py && git commit --no-gpg-sign -m "feat(eia): curated WPSR + NG-storage series catalog + select_ids"`

---

## Task 2: `eia_screener.fetch` — v2 client (bracket params, key) + parser

**Files:** Create `eia_screener/fetch.py`; Modify `.env.example`; Test `tests/test_eia_fetch.py`.

**Interfaces:** `require_api_key(api_key)`; `_build_url(route, facet, api_key, start=None)`; `parse_response(payload) -> (rows, unit)`; `fetch_series_obs(route, facet, api_key, start=None, get=_http_get) -> (rows, unit)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eia_fetch.py`:

```python
import json
import urllib.error

import pytest

from eia_screener import fetch


def test_require_api_key_raises_without_echoing():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "EIA_API_KEY" in str(exc.value)
    assert fetch.require_api_key("KEY") == "KEY"


def test_build_url_encodes_bracket_arrays_and_key():
    url = fetch._build_url("petroleum/stoc/wstk", "WCESTUS1", "SECRET",
                           start="2026-01-01")
    assert "api_key=SECRET" in url
    assert "data%5B0%5D=value" in url                       # data[0]=value
    assert "facets%5Bseries%5D%5B%5D=WCESTUS1" in url        # facets[series][]
    assert "sort%5B0%5D%5Bcolumn%5D=period" in url
    assert "start=2026-01-01" in url
    assert url.startswith("https://api.eia.gov/v2/petroleum/stoc/wstk/data/?")


def test_parse_response_extracts_rows_and_unit():
    payload = {"response": {"data": [
        {"period": "2026-06-26", "value": "420500", "units": "MBBL"},
        {"period": "2026-06-19", "value": None, "units": "MBBL"},   # withheld
    ]}}
    rows, unit = fetch.parse_response(payload)
    assert unit == "MBBL"
    assert rows[0] == {"period": "2026-06-26", "value": 420500.0}
    assert rows[1]["value"] is None


def test_fetch_series_obs_calls_get_and_parses():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"response": {"data": [
            {"period": "2026-06-26", "value": "1.0", "units": "BCF"}]}})

    rows, unit = fetch.fetch_series_obs("natural-gas/stor/wkly", "F", "K", get=get)
    assert unit == "BCF" and rows[0]["value"] == 1.0
    assert "facets%5Bseries%5D%5B%5D=F" in seen["url"]


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

Create `eia_screener/fetch.py`:

```python
"""EIA Open Data API v2 client. Near-clone of fred_screener.fetch: an API key in
the query string (never logged), plus EIA's bracket-array params built via an
ordered (key, value) tuple list + urlencode(doseq=True) so repeated
facets[series][] survive."""
import json
import time
import urllib.parse

import http_client

API_BASE = "https://api.eia.gov/v2"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

__all__ = ["require_api_key", "parse_response", "fetch_series_obs"]


def require_api_key(api_key):
    """Return a non-empty key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError(
            "EIA_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_url(route, facet, api_key, start=None) -> str:
    """Assemble a v2 data URL. Ordered tuples + doseq so bracket-array keys
    (data[0], facets[series][], sort[0][...]) encode correctly."""
    pairs = [
        ("api_key", api_key),
        ("frequency", "weekly"),
        ("data[0]", "value"),
        ("facets[series][]", facet),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
    ]
    if start:
        pairs.append(("start", start))
    return f"{API_BASE}/{route}/data/?" + urllib.parse.urlencode(pairs, doseq=True)


def parse_response(payload) -> tuple:
    """Map response.data[] to ([{period, value}], unit). Withheld value -> None."""
    data = (payload.get("response") or {}).get("data") or []
    rows, unit = [], None
    for d in data:
        period = d.get("period")
        if not period:
            continue
        rows.append({"period": str(period)[:10], "value": _num(d.get("value"))})
        unit = unit or d.get("units") or d.get("unit")
    return rows, unit


def fetch_series_obs(route, facet, api_key, start=None, get=_http_get) -> tuple:
    """GET one series' weekly observations. Returns (rows, unit)."""
    payload = json.loads(get(_build_url(route, facet, api_key, start)))
    return parse_response(payload)
```

Also append to `.env.example` (a new line):

```
# Free key for the EIA Open Data API v2 (https://www.eia.gov/opendata/) — used by the `eia` screener
EIA_API_KEY=
```

- [ ] **Step 4: Run test to verify it passes** — PASS (5 tests).
- [ ] **Step 5: Commit** — `git add eia_screener/fetch.py tests/test_eia_fetch.py .env.example && git commit --no-gpg-sign -m "feat(eia): v2 client (bracket params, key) + response parser; .env.example key"`

---

## Task 3: `eia_screener.db` — schema + writers + prune

**Files:** Create `eia_screener/db.py` (views deferred to Task 4); Test `tests/test_eia_db_schema.py`, `tests/test_eia_db_write.py`.

**Interfaces:** `connect`; `ensure_schema`; `upsert_series(conn, metas, captured_at)`; `write_observations(conn, series_id, rows) -> int`; `write_snapshot(conn, captured_at, series_count, observation_count) -> int`; `prune(conn, keep_days, now_iso) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_eia_db_schema.py`:

```python
from eia_screener import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "series", "eia_obs"} <= tables
```

Create `tests/test_eia_db_write.py`:

```python
from eia_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _meta(sid, unit="MBBL", label="L", cat="crude"):
    return {"series_id": sid, "route": "r", "label": label, "category": cat,
            "unit": unit, "frequency": "weekly"}


def test_write_observations_upsert_in_place():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1")], "t")
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 100.0}])
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 105.0}])
    assert conn.execute("SELECT value FROM eia_obs").fetchall() == [(105.0,)]


def test_upsert_series_preserves_first_seen_refreshes_meta():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1", unit="MBBL")], "t1")
    db.upsert_series(conn, [_meta("S1", unit="MBBL2")], "t2")
    row = conn.execute(
        "SELECT unit, first_seen, last_seen FROM series WHERE series_id='S1'"
    ).fetchone()
    assert row == ("MBBL2", "t1", "t2")


def test_prune_snapshots_not_obs():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1")], "t")
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 1.0}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM eia_obs").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `eia_screener/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_series", "write_observations",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,
    series_count      INTEGER NOT NULL,
    observation_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS series (
    series_id  TEXT PRIMARY KEY,
    route      TEXT,
    label      TEXT,
    category   TEXT,
    unit       TEXT,
    frequency  TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS eia_obs (
    series_id TEXT NOT NULL REFERENCES series(series_id),
    period    TEXT NOT NULL,
    value     REAL,
    PRIMARY KEY (series_id, period)
);
CREATE INDEX IF NOT EXISTS ix_eia_obs_period ON eia_obs(period);
"""


def ensure_schema(conn) -> None:
    """Create tables + indexes (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_series(conn, metas, captured_at) -> None:
    """Upsert the series dimension: refresh route/label/category/unit/frequency +
    last_seen, preserve first_seen (FRED upsert_series shape)."""
    params = [{"series_id": m["series_id"], "route": m.get("route"),
               "label": m.get("label"), "category": m.get("category"),
               "unit": m.get("unit"), "frequency": m.get("frequency", "weekly"),
               "seen": captured_at} for m in metas]
    conn.executemany(
        """INSERT INTO series (series_id, route, label, category, unit,
                               frequency, first_seen, last_seen)
           VALUES (:series_id, :route, :label, :category, :unit, :frequency,
                   :seen, :seen)
           ON CONFLICT(series_id) DO UPDATE SET
             route=excluded.route, label=excluded.label,
             category=excluded.category, unit=excluded.unit,
             frequency=excluded.frequency, last_seen=excluded.last_seen""",
        params)
    conn.commit()


def write_observations(conn, series_id, rows) -> int:
    """Upsert observations by (series_id, period): revised values overwrite in
    place, periods never duplicate. Dedupe within batch (last wins)."""
    by_period = {r["period"]: r["value"] for r in rows}
    conn.executemany(
        """INSERT INTO eia_obs (series_id, period, value) VALUES (?, ?, ?)
           ON CONFLICT(series_id, period) DO UPDATE SET value=excluded.value""",
        [(series_id, p, v) for p, v in by_period.items()])
    conn.commit()
    return len(by_period)


def write_snapshot(conn, captured_at, series_count, observation_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) "
        "VALUES (?, ?, ?)", (captured_at, series_count, observation_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. eia_obs is the accumulated
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


_VIEWS = ""   # filled in Task 4
```

- [ ] **Step 4: Run tests to verify they pass** — PASS (1 + 3 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(eia): series/eia_obs schema + upserts + single-table prune"`

---

## Task 4: `eia_screener.db` — inventory views

**Files:** Modify `eia_screener/db.py` (fill `_VIEWS`); Test `tests/test_eia_db_views.py`.

**Views:** `v_latest`, `v_weekly_change`, `v_series_history`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eia_db_views.py`:

```python
from eia_screener import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_series(conn, [{"series_id": "CRUDE", "route": "r",
                             "label": "Crude", "category": "crude",
                             "unit": "MBBL", "frequency": "weekly"}], "t")
    return conn


def test_v_latest_picks_newest_non_null():
    conn = _seed()
    db.write_observations(conn, "CRUDE", [
        {"period": "2026-06-19", "value": 420.0},
        {"period": "2026-06-26", "value": 415.0},
        {"period": "2026-07-03", "value": None}])       # withheld -> skipped
    row = conn.execute(
        "SELECT period, value, label FROM v_latest WHERE series_id='CRUDE'"
    ).fetchone()
    assert row == ("2026-06-26", 415.0, "Crude")


def test_v_weekly_change_draw_is_negative():
    conn = _seed()
    db.write_observations(conn, "CRUDE", [
        {"period": "2026-06-19", "value": 420.0},
        {"period": "2026-06-26", "value": 415.0}])       # a 5-MBBL draw
    row = conn.execute(
        "SELECT change_abs, change_pct FROM v_weekly_change WHERE series_id='CRUDE'"
    ).fetchone()
    assert row[0] == -5.0
    assert abs(row[1] - (-5.0 / 420.0 * 100)) < 1e-9


def test_v_series_history_full_series():
    conn = _seed()
    db.write_observations(conn, "CRUDE", [
        {"period": "2026-06-19", "value": 420.0},
        {"period": "2026-06-26", "value": 415.0}])
    periods = [r[0] for r in conn.execute(
        "SELECT period FROM v_series_history WHERE series_id='CRUDE' "
        "ORDER BY period")]
    assert periods == ["2026-06-19", "2026-06-26"]
```

- [ ] **Step 2: Run test to verify it fails** — views don't exist.

- [ ] **Step 3: Write minimal implementation**

In `eia_screener/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- Most recent non-null observation per series, joined to metadata.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT o.series_id, o.period, o.value,
           ROW_NUMBER() OVER (PARTITION BY o.series_id
                              ORDER BY o.period DESC) AS rn
    FROM eia_obs o WHERE o.value IS NOT NULL
)
SELECT r.series_id, s.label, s.category, s.unit, r.period, r.value
FROM ranked r JOIN series s ON s.series_id = r.series_id
WHERE r.rn = 1;

-- Latest vs the immediately preceding non-null period: the build/draw signal.
CREATE VIEW IF NOT EXISTS v_weekly_change AS
SELECT l.series_id, l.label, l.category, l.period AS latest_period,
       l.value AS latest, p.value AS prior,
       l.value - p.value AS change_abs,
       CASE WHEN p.value IS NOT NULL AND p.value <> 0
            THEN 100.0 * (l.value - p.value) / p.value END AS change_pct
FROM v_latest l
LEFT JOIN eia_obs p ON p.series_id = l.series_id AND p.value IS NOT NULL
     AND p.period = (SELECT MAX(o2.period) FROM eia_obs o2
                     WHERE o2.series_id = l.series_id AND o2.value IS NOT NULL
                       AND o2.period < l.period);

-- Full observation history per series joined to metadata.
CREATE VIEW IF NOT EXISTS v_series_history AS
SELECT o.series_id, s.label, s.category, s.unit, o.period, o.value
FROM eia_obs o JOIN series s ON s.series_id = o.series_id
ORDER BY o.series_id, o.period;
"""
```

- [ ] **Step 4: Run test to verify it passes** — PASS (3 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(eia): views — v_latest, v_weekly_change (build/draw), v_series_history"`

---

## Task 5: `eia_screener.run` — orchestration + CLI

**Files:** Create `eia_screener/run.py`; Test `tests/test_eia_run.py`.

**Interfaces:** `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, api_key=None, now_iso=None, fetch_series_obs=fetch.fetch_series_obs) -> (snapshot_id, series_count, observation_count)`; `main(argv=None)` — `prog="eia"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_eia_run.py`:

```python
import sqlite3

from eia_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"
CATALOG_ID = "WCESTUS1"


def _obs(*periods):
    return ([{"period": p, "value": v} for p, v in periods], "MBBL")


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_series_obs(route, facet, api_key, start=None):
        return _obs(("2026-06-26", 415.0), ("2026-06-19", 420.0))

    sid, sc, oc = runmod.run(db_path, only=[CATALOG_ID], api_key="K",
                             fetch_series_obs=fetch_series_obs, now_iso=NOW)
    assert sc == 1 and oc == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT unit FROM series").fetchone()[0] == "MBBL"


def test_run_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("EIA_API_KEY", raising=False)
    try:
        runmod.run(str(tmp_path / "e.db"), now_iso=NOW)
        assert False, "expected RuntimeError for missing key"
    except RuntimeError as e:
        assert "EIA_API_KEY" in str(e)


def test_run_skips_failing_series_hides_key(tmp_path, capsys):
    def fetch_series_obs(route, facet, api_key, start=None):
        if facet == "WCESTUS1":
            raise RuntimeError("https://api.eia.gov?api_key=SECRETKEY boom")
        return _obs(("2026-06-26", 1.0))

    sid, sc, oc = runmod.run(
        str(tmp_path / "e.db"), only=["WCESTUS1", "WGTSTUS1"], api_key="K",
        fetch_series_obs=fetch_series_obs, now_iso=NOW)
    assert sc == 1                                  # first failed, second stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "SECRETKEY" not in err                   # key/message never leaked


def test_run_add_route_facet_token(tmp_path):
    seen = []

    def fetch_series_obs(route, facet, api_key, start=None):
        seen.append((route, facet))
        return _obs(("2026-06-26", 1.0))

    runmod.run(str(tmp_path / "e.db"), only=[], add=["natural-gas/stor/wkly:F1"],
               api_key="K", fetch_series_obs=fetch_series_obs, now_iso=NOW)
    assert ("natural-gas/stor/wkly", "F1") in seen
    conn = sqlite3.connect(str(tmp_path / "e.db"))
    assert conn.execute(
        "SELECT category FROM series WHERE series_id='F1'").fetchone()[0] == "custom"


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(route, facet, api_key, start=None):
        raise RuntimeError("x")

    sid, sc, oc = runmod.run(str(tmp_path / "e.db"), only=["WCESTUS1"],
                             api_key="K", fetch_series_obs=boom, now_iso=NOW)
    assert (sc, oc) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "e.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_obs(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_series_obs(route, facet, api_key, start=None):
        return _obs(("2026-06-26", 1.0))

    runmod.run(db_path, only=["WCESTUS1"], api_key="K",
               fetch_series_obs=fetch_series_obs,
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["WCESTUS1"], api_key="K",
               fetch_series_obs=fetch_series_obs, now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM eia_obs").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `eia_screener/run.py`:

```python
import argparse
import os
import sys
from datetime import datetime, timezone

from eia_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        api_key=None, now_iso=None, fetch_series_obs=fetch.fetch_series_obs):
    """Fetch selected EIA series, upsert obs, snapshot, optionally prune.
    Skip-and-continue. Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("EIA_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    ad_hoc, add_ids = {}, []
    for token in (add or []):
        route, _, facet = token.partition(":")
        if not route or not facet:
            print(f"warning: bad --add token {token} (want route:facet)",
                  file=sys.stderr)
            continue
        ad_hoc[facet] = catalog.Series(facet, route, facet, facet, "custom")
        add_ids.append(facet)

    ids = catalog.select_ids([s.series_id for s in catalog.CATALOG], only,
                             exclude, add=add_ids)
    by_id = {**{s.series_id: s for s in catalog.CATALOG}, **ad_hoc}

    conn = db.connect(db_path)
    successes, total_obs = 0, 0
    try:
        db.ensure_schema(conn)
        for sid in ids:
            s = by_id.get(sid)
            if s is None:
                continue
            try:
                rows, unit = fetch_series_obs(s.route, s.facet, api_key,
                                              start=start)
                db.upsert_series(conn, [{"series_id": s.series_id,
                    "route": s.route, "label": s.label, "category": s.category,
                    "unit": unit, "frequency": "weekly"}], now_iso)
                n = db.write_observations(conn, s.series_id, rows)
            except Exception as e:  # key rides in the URL -> type name only
                conn.rollback()
                print(f"warning: skipping {sid}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_obs += n

        if successes == 0:
            print("warning: no EIA series fetched (0 series, 0 observations)",
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
        prog="eia",
        description="Pull weekly EIA energy-inventory series into SQLite")
    p.add_argument("--db", default="eia.db")
    p.add_argument("--only", default=None, help="comma-separated series ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="ad-hoc series as route:facet (repeatable)")
    p.add_argument("--start", default=None, help="period floor (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, sc, oc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} series into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes** — PASS (6 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(eia): run orchestration (route:facet add, skip-and-continue, secret hygiene) + CLI"`

---

## Task 6: Register `eia` in the dispatcher

**Files:** Modify `registry.py`; Test `tests/test_registry.py` (+1 assertion).

- [ ] **Step 1:** Add `def test_dispatch_lists_eia():\n    import registry\n    assert "eia" in registry.REGISTRY`.
- [ ] **Step 2:** Run → `AssertionError`.
- [ ] **Step 3:** In `registry.py` add `from eia_screener.run import main as eia_main` and `"eia": eia_main,`.
- [ ] **Step 4:** Run `python -m pytest tests/test_registry.py -v` → PASS.
- [ ] **Step 5:** Run full `python -m pytest` → PASS. Commit `git commit --no-gpg-sign -m "feat(eia): register eia dispatcher"`.

---

## Task 7: Roadmap bookkeeping

- [ ] Add an `eia` row to **Built ✅** (link this plan + spec); remove `eia` from **Spec'd — data screeners**; update the tail line to drop `eia` (leaving `usda`); note the release-schedule monitor stays in the event-monitor layer. Commit `git commit --no-gpg-sign -m "docs(roadmap): mark eia Built"`.

---

## Self-Review

**1. Spec coverage:** Series catalog (route+facet) + `select_ids` (Task 1); `require_api_key` (never echoes), bracket-array `_build_url` (doseq), `parse_response`, `fetch_series_obs`, `.env.example` key (Task 2); `series`/`eia_obs` schema, upserts (revise-in-place, preserve first_seen), single-table prune (Task 3); `v_latest`/`v_weekly_change` (build/draw)/`v_series_history` (Task 4); `run` route:facet `--add`, skip-and-continue, secret hygiene (key never leaked), all-fail→(0,0) + CLI (Task 5); registry (Task 6). `now_iso` injected.

**2. Placeholder scan:** No `TODO`. 🟡 routes/facets handled via the live-verification action. `--add route:facet` is the spec's escape hatch, implemented + tested.

**3. Type consistency:** `fetch_series_obs` returns `(rows, unit)` consumed identically in `run` and tests; obs-row keys (`period, value`) match `write_observations`; series-meta dict keys match `upsert_series`. `require_api_key` gate runs before any fetch. `run` returns a 3-tuple used identically across tests.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-eia-energy-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit, `--no-gpg-sign`) per task, full `python -m pytest` before the roadmap commit.
