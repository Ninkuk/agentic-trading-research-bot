# NY Fed Markets Data Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `nyfed` screener — a funding & liquidity reader pulling curated NY Fed Markets datasets (reference rates SOFR/EFFR/OBFR/BGCR/TGCR, repo + reverse-repo operations, SOMA holdings) into per-domain SQLite tables with derived funding-stress / QT-pace views. Primary-dealer stats are wired but disabled (phase 2).

**Architecture:** A data screener structurally identical to `treasury` (domain `catalog`/`fetch`/`db`/`run` + registry). **Time-series/panel shape**, records upserted by natural `(…, date)` key, history not snapshot-scoped. Reuses `screener_common.connect` (WAL), the `http_client` bounded-backoff, and the FRED-style `select_ids` + single-table prune. Key-free JSON. **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** The NY Fed Markets API is public/key-free; `.env.example` unchanged. Descriptive UA `agentic-trading-bot ninadk.dev@gmail.com`; retry `{429, 500, 502, 503, 504}`.
- **`now_iso` injected, never wall-clock in logic.** `run()` accepts `now_iso=None`, defaulting to UTC now; `fetch_domain` injected so tests are network-free.
- **Panel upsert, never duplicate keys.** Each `write_<table>` upserts on the natural key; a restated operation/rate overwrites in place; batches dedupe by key (last wins) — the FRED `write_observations` shape.
- **Skip-and-continue** per domain: `conn.rollback()`, log **only** `type(e).__name__` (never `str(e)`/`e.url`), continue. Zero successes → still `write_snapshot(…, 0, 0)` and warn; never raise.
- **Prune is FRED-style single-table** — delete old `snapshots` only; never cascade into fact tables. Call this out in `db.py`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest` (config in `pyproject.toml`).
- **Commits:** do NOT add a co-author line. Use `git commit --no-gpg-sign` (this repo's ssh/1Password signing hangs non-interactively).

### Live-verification action (🟡)

Endpoints located but not adversarially verified. Confirm live (key-free GET) and adjust parser + fixtures together: the domain history paths, the JSON **envelope keys** (the records list may be nested under `refRates`/`repo`/`soma`), and field names (`effectiveDate`, `percentRate`, `volumeInBillions`, percentile fields; `operationId`/`operationDate`/`totalAmtAccepted`/`totalAmtSubmitted`; `asOfDate`/`securityType`/`parValue`). Any path that 404s is dropped from `CATALOG` with a note. `_first_list` (below) extracts the records list regardless of the exact envelope key, so envelope drift is tolerated.

---

## File Structure

**New — `nyfed_screener/` package:** `__init__.py`, `catalog.py`, `fetch.py`, `db.py`, `run.py`.
**Modified:** `registry.py` — register `"nyfed"`.
**New tests:** `test_nyfed_catalog.py`, `test_nyfed_fetch.py`, `test_nyfed_db_schema.py`, `test_nyfed_db_write.py`, `test_nyfed_db_views.py`, `test_nyfed_run.py`, + one `test_registry.py` assertion.

---

## Task 1: `nyfed_screener.catalog` — Domain catalog + select_ids

**Files:** Create `nyfed_screener/__init__.py` (empty), `nyfed_screener/catalog.py`; Test `tests/test_nyfed_catalog.py`.

**Interfaces:** `Domain(domain_id, endpoint, table, date_field)`; `CATALOG`; `enabled_ids()`; `select_ids(all_ids, only, exclude, add=None)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_nyfed_catalog.py`:

```python
from nyfed_screener.catalog import CATALOG, Domain, enabled_ids, select_ids


def test_catalog_ids_unique_and_v1_present():
    ids = [d.domain_id for d in CATALOG]
    assert len(ids) == len(set(ids))
    assert {"reference_rates", "rrp", "repo", "soma"} <= set(ids)


def test_primary_dealer_defined_but_disabled_by_default():
    assert "primary_dealer" in {d.domain_id for d in CATALOG}
    assert "primary_dealer" not in enabled_ids()


def test_select_ids_default_only_exclude_add():
    e = enabled_ids()
    assert select_ids(e, None, None) == e
    assert select_ids(e, ["repo", "repo"], None) == ["repo"]
    assert "repo" not in select_ids(e, None, ["repo"])
    assert select_ids(e, ["soma"], None, add=["primary_dealer"]) == \
        ["soma", "primary_dealer"]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `nyfed_screener/__init__.py` (empty). Create `nyfed_screener/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    domain_id: str    # reference_rates | rrp | repo | soma | primary_dealer
    endpoint: str     # NY Fed history path
    table: str        # target table
    date_field: str   # API date field


CATALOG: list[Domain] = [
    Domain("reference_rates", "/rates/all/search.json", "reference_rates",
           "effectiveDate"),
    Domain("rrp", "/rp/reverserepo/propositions/search.json", "repo_ops",
           "operationDate"),
    Domain("repo", "/rp/repo/all/results/search.json", "repo_ops",
           "operationDate"),
    Domain("soma", "/soma/summary.json", "soma_holdings", "asOfDate"),
    Domain("primary_dealer", "/pd/get/all/timeseries.json",
           "primary_dealer_stats", "asOfDate"),
]

# primary_dealer is phase 2: defined but off by default (opt-in via --only/--add).
_ENABLED = {"reference_rates", "rrp", "repo", "soma"}


def enabled_ids() -> list:
    return [d.domain_id for d in CATALOG if d.domain_id in _ENABLED]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated domain ids (FRED select_ids semantics)."""
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
- [ ] **Step 5: Commit** — `git add nyfed_screener/__init__.py nyfed_screener/catalog.py tests/test_nyfed_catalog.py && git commit --no-gpg-sign -m "feat(nyfed): curated Markets-domain catalog + select_ids"`

---

## Task 2: `nyfed_screener.fetch` — JSON client + per-domain parsers

**Files:** Create `nyfed_screener/fetch.py`; Test `tests/test_nyfed_fetch.py`.

**Interfaces:** `_build_url`, `fetch_domain(endpoint, *, start=None, end=None, get=_http_get)`, `parse_reference_rates`, `parse_repo_ops(records, operation_type)`, `parse_soma_holdings`, `parse_primary_dealer`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_nyfed_fetch.py`:

```python
import json
import urllib.error

from nyfed_screener import fetch


def test_build_url_encodes_dates():
    url = fetch._build_url("/rates/all/search.json",
                           {"startDate": "2026-01-01", "endDate": "2026-02-01"})
    assert "startDate=2026-01-01" in url and "endDate=2026-02-01" in url


def test_fetch_domain_extracts_records_from_envelope():
    payload = {"refRates": [{"effectiveDate": "2026-06-01", "type": "SOFR",
                             "percentRate": "5.31"}]}

    def get(url):
        return json.dumps(payload)

    recs = fetch.fetch_domain("/rates/all/search.json", get=get)
    assert recs and recs[0]["type"] == "SOFR"


def test_parse_reference_rates_coerces():
    rows = fetch.parse_reference_rates([
        {"effectiveDate": "2026-06-01", "type": "SOFR", "percentRate": "5.31",
         "volumeInBillions": "2100"},
        {"effectiveDate": "", "type": "SOFR", "percentRate": "5.0"},   # no date
    ])
    assert len(rows) == 1
    assert rows[0]["rate_type"] == "SOFR" and rows[0]["percent_rate"] == 5.31
    assert rows[0]["volume_bn"] == 2100.0


def test_parse_repo_ops_tags_operation_type():
    rows = fetch.parse_repo_ops([
        {"operationId": "RP1", "operationDate": "2026-06-01",
         "totalAmtSubmitted": "100", "totalAmtAccepted": "90"}], "reverse_repo")
    assert rows[0]["operation_type"] == "reverse_repo"
    assert rows[0]["operation_id"] == "RP1" and rows[0]["total_accepted"] == 90.0


def test_parse_soma_holdings():
    rows = fetch.parse_soma_holdings([
        {"asOfDate": "2026-06-03", "securityType": "total", "parValue": "7.2e12"}])
    assert rows[0]["as_of_date"] == "2026-06-03"
    assert rows[0]["security_type"] == "total" and rows[0]["par_value"] == 7.2e12


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_domain_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps({"refRates": []})

    def get(url):
        return fetch._http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_domain("/rates/all/search.json", get=get)
    assert calls["n"] == 2 and slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `nyfed_screener/fetch.py`:

```python
"""NY Fed Markets API client (key-free JSON) + per-domain pure parsers.
Envelope-agnostic: _first_list pulls the records array whatever the wrapper key."""
import json
import time
import urllib.parse

import http_client

API_BASE = "https://markets.newyorkfed.org/api"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)


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


def _date(v):
    return (v or "")[:10] or None


def _build_url(endpoint, params=None) -> str:
    url = f"{API_BASE}{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def _first_list(obj):
    """Return the first list found anywhere in the JSON envelope, else []."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            r = _first_list(v)
            if r is not None:
                return r
    return None


def fetch_domain(endpoint, *, start=None, end=None, get=_http_get) -> list:
    """GET a domain history endpoint (windowed when start given); return records."""
    params = {}
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end
    payload = json.loads(get(_build_url(endpoint, params or None)))
    return _first_list(payload) or []


def parse_reference_rates(records) -> list:
    out = []
    for r in records:
        rt = r.get("type") or r.get("rateType")
        d = _date(r.get("effectiveDate"))
        if not rt or not d:
            continue
        out.append({"rate_type": rt, "effective_date": d,
                    "percent_rate": _num(r.get("percentRate")),
                    "volume_bn": _num(r.get("volumeInBillions")),
                    "pct_1": _num(r.get("percentPercentile1")),
                    "pct_25": _num(r.get("percentPercentile25")),
                    "pct_75": _num(r.get("percentPercentile75")),
                    "pct_99": _num(r.get("percentPercentile99"))})
    return out


def parse_repo_ops(records, operation_type) -> list:
    out = []
    for r in records:
        oid = r.get("operationId")
        d = _date(r.get("operationDate"))
        if not oid or not d:
            continue
        out.append({"operation_id": str(oid), "operation_date": d,
                    "operation_type": operation_type,
                    "total_submitted": _num(r.get("totalAmtSubmitted")),
                    "total_accepted": _num(r.get("totalAmtAccepted")),
                    "award_rate": _num(r.get("awardRate")
                                       or r.get("percentAwardRate"))})
    return out


def parse_soma_holdings(records) -> list:
    out = []
    for r in records:
        d = _date(r.get("asOfDate"))
        if not d:
            continue
        out.append({"as_of_date": d,
                    "security_type": r.get("securityType") or "total",
                    "par_value": _num(r.get("parValue") or r.get("total"))})
    return out


def parse_primary_dealer(records) -> list:
    """Phase-2, tolerant: one row per (asOfDate, series key). 🟡 confirm shape."""
    out = []
    for r in records:
        d = _date(r.get("asOfDate"))
        key = r.get("keyId") or r.get("seriesBreakId") or r.get("series")
        if not d or not key:
            continue
        out.append({"as_of_date": d, "series_key": str(key),
                    "value": _num(r.get("value"))})
    return out
```

- [ ] **Step 4: Run test to verify it passes** — PASS (6 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(nyfed): Markets API client (envelope-agnostic) + per-domain parsers"`

---

## Task 3: `nyfed_screener.db` — schema + writers + prune

**Files:** Create `nyfed_screener/db.py` (views deferred to Task 4); Test `tests/test_nyfed_db_schema.py`, `tests/test_nyfed_db_write.py`.

**Interfaces:** `connect`; `ensure_schema`; `write_reference_rates`/`write_repo_ops`/`write_soma_holdings`/`write_primary_dealer(conn, rows) -> int`; `write_snapshot(conn, captured_at, domain_count, row_count) -> int`; `prune(conn, keep_days, now_iso) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_nyfed_db_schema.py`:

```python
from nyfed_screener import db


def test_ensure_schema_creates_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "reference_rates", "repo_ops", "soma_holdings",
            "primary_dealer_stats", "iorb"} <= tables
```

Create `tests/test_nyfed_db_write.py`:

```python
from nyfed_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_reference_rates_upsert_in_place():
    conn = _fresh()
    row = {"rate_type": "SOFR", "effective_date": "2026-06-01",
           "percent_rate": 5.31, "volume_bn": 2100.0, "pct_1": None,
           "pct_25": None, "pct_75": None, "pct_99": None}
    db.write_reference_rates(conn, [row])
    db.write_reference_rates(conn, [{**row, "percent_rate": 5.35}])  # restated
    got = conn.execute("SELECT percent_rate FROM reference_rates").fetchall()
    assert got == [(5.35,)]


def test_write_repo_ops_dedupe_and_null_blank():
    conn = _fresh()
    n = db.write_repo_ops(conn, [
        {"operation_id": "R1", "operation_date": "2026-06-01",
         "operation_type": "repo", "total_submitted": 100.0,
         "total_accepted": None, "award_rate": None},
        {"operation_id": "R1", "operation_date": "2026-06-01",
         "operation_type": "repo", "total_submitted": 200.0,
         "total_accepted": None, "award_rate": None},
    ])
    assert n == 1
    assert conn.execute("SELECT total_submitted FROM repo_ops").fetchone()[0] == 200.0
    assert conn.execute("SELECT total_accepted FROM repo_ops").fetchone()[0] is None


def test_prune_deletes_snapshots_not_facts():
    conn = _fresh()
    db.write_soma_holdings(conn, [{"as_of_date": "2026-06-03",
                                   "security_type": "total", "par_value": 7e12}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM soma_holdings").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `nyfed_screener/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "write_reference_rates",
           "write_repo_ops", "write_soma_holdings", "write_primary_dealer",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    domain_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reference_rates (
    rate_type      TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    percent_rate   REAL,
    volume_bn      REAL,
    pct_1 REAL, pct_25 REAL, pct_75 REAL, pct_99 REAL,
    PRIMARY KEY (rate_type, effective_date)
);
CREATE TABLE IF NOT EXISTS repo_ops (
    operation_id    TEXT PRIMARY KEY,
    operation_date  TEXT NOT NULL,
    operation_type  TEXT NOT NULL,
    total_submitted REAL,
    total_accepted  REAL,
    award_rate      REAL
);
CREATE INDEX IF NOT EXISTS ix_repo_ops_date ON repo_ops(operation_date);
CREATE TABLE IF NOT EXISTS soma_holdings (
    as_of_date    TEXT NOT NULL,
    security_type TEXT NOT NULL,
    par_value     REAL,
    PRIMARY KEY (as_of_date, security_type)
);
CREATE TABLE IF NOT EXISTS primary_dealer_stats (
    as_of_date TEXT NOT NULL,
    series_key TEXT NOT NULL,
    value      REAL,
    PRIMARY KEY (as_of_date, series_key)
);
-- IORB is a Fed administered rate NOT on the NY Fed API; this table lets
-- v_sofr_latest LEFT JOIN a spread (empty by default -> spread NULL). Populate
-- from FRED 'IORB' out-of-band.
CREATE TABLE IF NOT EXISTS iorb (
    effective_date TEXT PRIMARY KEY,
    percent_rate   REAL
);
"""


def ensure_schema(conn) -> None:
    """Create all NY Fed tables (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def _upsert(conn, table, cols, key_cols, rows) -> int:
    by_key = {tuple(r[k] for k in key_cols): r for r in rows}
    placeholders = ", ".join(f":{c}" for c in cols)
    non_key = [c for c in cols if c not in key_cols]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in non_key) or \
        f"{key_cols[0]}={key_cols[0]}"
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(key_cols)}) DO UPDATE SET {set_clause}",
        list(by_key.values()))
    conn.commit()
    return len(by_key)


def write_reference_rates(conn, rows) -> int:
    return _upsert(conn, "reference_rates",
                   ["rate_type", "effective_date", "percent_rate", "volume_bn",
                    "pct_1", "pct_25", "pct_75", "pct_99"],
                   ["rate_type", "effective_date"], rows)


def write_repo_ops(conn, rows) -> int:
    return _upsert(conn, "repo_ops",
                   ["operation_id", "operation_date", "operation_type",
                    "total_submitted", "total_accepted", "award_rate"],
                   ["operation_id"], rows)


def write_soma_holdings(conn, rows) -> int:
    return _upsert(conn, "soma_holdings",
                   ["as_of_date", "security_type", "par_value"],
                   ["as_of_date", "security_type"], rows)


def write_primary_dealer(conn, rows) -> int:
    return _upsert(conn, "primary_dealer_stats",
                   ["as_of_date", "series_key", "value"],
                   ["as_of_date", "series_key"], rows)


def write_snapshot(conn, captured_at, domain_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, domain_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, domain_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. Fact tables are the store and
    are NEVER cascade-pruned (FRED prune shape)."""
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
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(nyfed): per-domain schema + keyed upserts + single-table prune"`

---

## Task 4: `nyfed_screener.db` — funding/liquidity views

**Files:** Modify `nyfed_screener/db.py` (fill `_VIEWS`); Test `tests/test_nyfed_db_views.py`.

**Views:** `v_rrp_trend`, `v_sofr_latest`, `v_soma_runoff`, `v_dealer_positioning`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_nyfed_db_views.py`:

```python
from nyfed_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _rate(rate_type, d, rate):
    return {"rate_type": rate_type, "effective_date": d, "percent_rate": rate,
            "volume_bn": None, "pct_1": None, "pct_25": None, "pct_75": None,
            "pct_99": None}


def test_v_sofr_latest_spread_null_then_computed():
    conn = _fresh()
    db.write_reference_rates(conn, [_rate("SOFR", "2026-06-01", 5.30),
                                    _rate("SOFR", "2026-06-02", 5.31)])
    row = conn.execute(
        "SELECT effective_date, sofr_iorb_spread FROM v_sofr_latest").fetchone()
    assert row[0] == "2026-06-02" and row[1] is None       # no IORB -> NULL
    conn.execute("INSERT INTO iorb VALUES ('2026-06-01', 5.15)")
    conn.commit()
    row = conn.execute("SELECT sofr_iorb_spread FROM v_sofr_latest").fetchone()
    assert abs(row[0] - 0.16) < 1e-9                        # 5.31 - 5.15


def test_v_rrp_trend_take_up_and_change():
    conn = _fresh()
    db.write_repo_ops(conn, [
        {"operation_id": "A", "operation_date": "2026-06-01",
         "operation_type": "reverse_repo", "total_submitted": None,
         "total_accepted": 400.0, "award_rate": None},
        {"operation_id": "B", "operation_date": "2026-06-02",
         "operation_type": "reverse_repo", "total_submitted": None,
         "total_accepted": 500.0, "award_rate": None},
    ])
    row = conn.execute("SELECT change_vs_prior FROM v_rrp_trend "
                       "WHERE operation_date='2026-06-02'").fetchone()
    assert row[0] == 100.0


def test_v_soma_runoff_wow_change():
    conn = _fresh()
    db.write_soma_holdings(conn, [
        {"as_of_date": "2026-05-28", "security_type": "total", "par_value": 7.2e12},
        {"as_of_date": "2026-06-04", "security_type": "total", "par_value": 7.15e12},
    ])
    row = conn.execute("SELECT wow_change FROM v_soma_runoff "
                       "WHERE as_of_date='2026-06-04'").fetchone()
    assert abs(row[0] - (-5e10)) < 1e6                      # runoff (negative)
```

- [ ] **Step 2: Run test to verify it fails** — views don't exist.

- [ ] **Step 3: Write minimal implementation**

In `nyfed_screener/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- ON-RRP daily take-up + day-over-day change (excess-liquidity gauge).
CREATE VIEW IF NOT EXISTS v_rrp_trend AS
WITH daily AS (
    SELECT operation_date, SUM(total_accepted) AS take_up
    FROM repo_ops WHERE operation_type = 'reverse_repo'
    GROUP BY operation_date
)
SELECT operation_date, take_up,
       take_up - LAG(take_up) OVER (ORDER BY operation_date) AS change_vs_prior
FROM daily ORDER BY operation_date;

-- Latest SOFR + SOFR-vs-IORB spread (NULL until an iorb row exists).
CREATE VIEW IF NOT EXISTS v_sofr_latest AS
WITH latest AS (
    SELECT * FROM reference_rates WHERE rate_type = 'SOFR'
    ORDER BY effective_date DESC LIMIT 1
)
SELECT l.effective_date, l.percent_rate, l.volume_bn,
       (SELECT percent_rate FROM iorb WHERE effective_date <= l.effective_date
        ORDER BY effective_date DESC LIMIT 1) AS iorb,
       l.percent_rate - (SELECT percent_rate FROM iorb
                         WHERE effective_date <= l.effective_date
                         ORDER BY effective_date DESC LIMIT 1) AS sofr_iorb_spread
FROM latest l;

-- SOMA total par per as-of date + week-over-week change (QT/QE pace).
CREATE VIEW IF NOT EXISTS v_soma_runoff AS
WITH tot AS (
    SELECT as_of_date, par_value FROM soma_holdings
    WHERE security_type = 'total'
)
SELECT as_of_date, par_value,
       par_value - LAG(par_value) OVER (ORDER BY as_of_date) AS wow_change
FROM tot ORDER BY as_of_date;

-- Latest primary-dealer value per series (populated only once phase 2 lands).
CREATE VIEW IF NOT EXISTS v_dealer_positioning AS
WITH ranked AS (
    SELECT series_key, as_of_date, value,
           ROW_NUMBER() OVER (PARTITION BY series_key
                              ORDER BY as_of_date DESC) AS rn
    FROM primary_dealer_stats
)
SELECT series_key, as_of_date, value FROM ranked WHERE rn = 1;
"""
```

- [ ] **Step 4: Run test to verify it passes** — PASS (3 tests). Run the whole db suite too.
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(nyfed): funding/liquidity views — RRP trend, SOFR-IORB spread, SOMA runoff, dealers"`

---

## Task 5: `nyfed_screener.run` — orchestration + CLI

**Files:** Create `nyfed_screener/run.py`; Test `tests/test_nyfed_run.py`.

**Interfaces:** `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, fetch_domain=fetch.fetch_domain, now_iso=None) -> (snapshot_id, domain_count, row_count)`; `main(argv=None)` — `prog="nyfed"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_nyfed_run.py`:

```python
import sqlite3

from nyfed_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def test_run_happy_path_counts(tmp_path):
    db_path = str(tmp_path / "n.db")

    def fetch_domain(endpoint, *, start=None, end=None):
        if "rates" in endpoint:
            return [{"effectiveDate": "2026-06-01", "type": "SOFR",
                     "percentRate": "5.3"}]
        if "reverserepo" in endpoint:
            return [{"operationId": "R1", "operationDate": "2026-06-01",
                     "totalAmtAccepted": "400"}]
        return []

    sid, nd, nr = runmod.run(db_path, only=["reference_rates", "rrp"],
                             fetch_domain=fetch_domain, now_iso=NOW)
    assert nd == 2 and nr == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM reference_rates").fetchone()[0] == 1


def test_run_skips_failing_domain_hides_secret(tmp_path, capsys):
    def fetch_domain(endpoint, *, start=None, end=None):
        if "rates" in endpoint:
            raise RuntimeError("https://markets?t=SECRET boom")
        return [{"asOfDate": "2026-06-03", "securityType": "total",
                 "parValue": "7e12"}]

    sid, nd, nr = runmod.run(str(tmp_path / "n.db"),
                             only=["reference_rates", "soma"],
                             fetch_domain=fetch_domain, now_iso=NOW)
    assert nd == 1 and nr == 1                    # rates failed, soma stored
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_all_fail_zero_snapshot(tmp_path, capsys):
    def boom(endpoint, *, start=None, end=None):
        raise RuntimeError("x")

    sid, nd, nr = runmod.run(str(tmp_path / "n.db"), only=["reference_rates"],
                             fetch_domain=boom, now_iso=NOW)
    assert (nd, nr) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "n.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_incremental_floors_start_at_max_date(tmp_path):
    db_path = str(tmp_path / "n.db")
    seen = {"start": []}

    def fetch_domain(endpoint, *, start=None, end=None):
        seen["start"].append(start)
        return [{"effectiveDate": "2026-06-02", "type": "SOFR",
                 "percentRate": "5.3"}]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW)
    assert seen["start"][0] is None              # first run: full history
    assert seen["start"][1] == "2026-06-02"      # second: floored at max date


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "n.db")

    def fetch_domain(endpoint, *, start=None, end=None):
        return [{"effectiveDate": "2026-06-02", "type": "SOFR",
                 "percentRate": "5.3"}]

    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["reference_rates"], fetch_domain=fetch_domain,
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM reference_rates").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `nyfed_screener/run.py`:

```python
import argparse
import sys
from datetime import datetime, timezone

from nyfed_screener import catalog, db, fetch

_DATE_COL = {"reference_rates": "effective_date", "repo_ops": "operation_date",
             "soma_holdings": "as_of_date", "primary_dealer_stats": "as_of_date"}
_WRITER = {"reference_rates": db.write_reference_rates, "rrp": db.write_repo_ops,
           "repo": db.write_repo_ops, "soma": db.write_soma_holdings,
           "primary_dealer": db.write_primary_dealer}


def _parse(domain_id, records):
    if domain_id == "reference_rates":
        return fetch.parse_reference_rates(records)
    if domain_id == "rrp":
        return fetch.parse_repo_ops(records, "reverse_repo")
    if domain_id == "repo":
        return fetch.parse_repo_ops(records, "repo")
    if domain_id == "soma":
        return fetch.parse_soma_holdings(records)
    if domain_id == "primary_dealer":
        return fetch.parse_primary_dealer(records)
    return []


def _max_date(conn, table, date_col):
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    return row[0] if row and row[0] else None


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        fetch_domain=fetch.fetch_domain, now_iso=None):
    """Fetch selected NY Fed domains, upsert into per-domain tables, snapshot,
    optionally prune. Skip-and-continue. Returns
    (snapshot_id, domain_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    ids = catalog.select_ids(catalog.enabled_ids(), only, exclude, add=add)
    by_id = {d.domain_id: d for d in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for domain_id in ids:
            ds = by_id.get(domain_id)
            if ds is None:
                print(f"warning: unknown domain {domain_id}", file=sys.stderr)
                continue
            try:
                since = start if start is not None else _max_date(
                    conn, ds.table, _DATE_COL[ds.table])
                records = fetch_domain(ds.endpoint, start=since)
                n = _WRITER[domain_id](conn, _parse(domain_id, records))
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {domain_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no NY Fed domains fetched (0 domains, 0 rows)",
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
        prog="nyfed",
        description="Pull NY Fed Markets data (rates/repo/SOMA) into SQLite")
    p.add_argument("--db", default="nyfed.db")
    p.add_argument("--only", default=None, help="comma-separated domain ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra domain id e.g. primary_dealer (repeatable)")
    p.add_argument("--start", default=None,
                   help="date floor for the first fetch (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, nd, nr = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {nr} rows across {nd} domains into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes** — PASS (5 tests).
- [ ] **Step 5: Commit** — `git commit --no-gpg-sign -m "feat(nyfed): run orchestration (incremental, skip-and-continue) + CLI"`

---

## Task 6: Register `nyfed` in the dispatcher

**Files:** Modify `registry.py`; Test `tests/test_registry.py` (+1 assertion).

- [ ] **Step 1:** Add to `tests/test_registry.py`: `def test_dispatch_lists_nyfed():\n    import registry\n    assert "nyfed" in registry.REGISTRY`.
- [ ] **Step 2:** Run → `AssertionError`.
- [ ] **Step 3:** In `registry.py` add `from nyfed_screener.run import main as nyfed_main` and `"nyfed": nyfed_main,`.
- [ ] **Step 4:** Run `python -m pytest tests/test_registry.py -v` → PASS.
- [ ] **Step 5:** Run full `python -m pytest` → PASS. Commit `git commit --no-gpg-sign -m "feat(nyfed): register nyfed dispatcher"`.

---

## Task 7: Roadmap bookkeeping

- [ ] Add a `nyfed` row to **Built ✅** (link this plan + spec); remove `nyfed` from **Spec'd — data screeners**; update the tail line to drop `nyfed` (leaving `cboe_stats`, `eia`, `usda`); note the deferred primary-dealer phase-2. Commit `git commit --no-gpg-sign -m "docs(roadmap): mark nyfed Built"`.

---

## Self-Review

**1. Spec coverage:** Domain catalog + `select_ids`, `primary_dealer` disabled (Task 1); `_build_url`, envelope-agnostic `fetch_domain`, per-domain parsers (Task 2); per-domain tables + upserts + single-table prune + the `iorb` join table (Task 3); `v_rrp_trend`/`v_sofr_latest` (IORB spread NULL-safe)/`v_soma_runoff`/`v_dealer_positioning` (Task 4); `run` incremental/skip-and-continue/all-fail→(0,0)/secret hygiene + CLI (Task 5); registry (Task 6). No credentials; `now_iso` injected.

**2. Placeholder scan:** No `TODO`. 🟡 paths/fields/envelope keys handled via the live-verification action + `_first_list` tolerance. `primary_dealer` is spec-defined phase-2, wired but disabled — a minimal parser/writer ships so `--add primary_dealer` doesn't crash.

**3. Type consistency:** Each parser's output dict keys exactly match its table columns (Task 2 ↔ Task 3), so the named-param `_upsert` binds directly. `_num`→`float|None`, `_date`→ISO `str|None`. `run` returns a 3-tuple used identically in tests. `_DATE_COL`/`_WRITER`/`_parse` are keyed consistently by table/domain id.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-nyfed-markets-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, full `python -m pytest` before the roadmap commit.
