# FRED Macro / Regime Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `fred_screener/` package that pulls a curated set of macroeconomic time series from the FRED API into SQLite as an upserted observation history, with ELT regime-signal views, wired into the existing `registry.py` dispatcher.

**Architecture:** Follows the established screener package shape (`catalog.py` / `fetch.py` / `db.py` / `run.py`), reusing `screener_common.connect`. Unlike the other screeners, the fact table (`observations`) is upserted by `(series_id, date)` rather than snapshot-scoped, because FRED revises history. `snapshots` records fetch-run provenance only. Per-series fetch failures are skip-and-continue.

**Tech Stack:** Python 3.12, stdlib only (`urllib`, `sqlite3`, `json`, `os`), `pytest` (run via `.venv/bin/pytest`).

**Spec:** `docs/superpowers/specs/2026-07-02-fred-screener-design.md`

## Global Constraints

- **Dependency-free:** stdlib only (`urllib`, `sqlite3`, `json`, `os`, `datetime`). No new packages.
- **API base:** `https://api.stlouisfed.org/fred/`. Auth via `api_key` query param; always send `file_type=json`.
- **API key source:** `FRED_API_KEY` env var (loaded from `.env`). **Never** include the key or full request URL in any raised message, log, or stderr line.
- **Missing observations:** FRED sends missing values as the literal string `"."` → store as SQL `NULL`.
- **Per-series failure policy:** skip-and-continue (warn to stderr, run proceeds). Zero successes → write a `(0, 0)` snapshot, warn loudly, return normally (do not raise).
- **Observations are NOT snapshot-scoped:** upsert by `(series_id, date)`; pruning must never delete observations.
- **Test runner:** `.venv/bin/pytest` with `pythonpath=["."]` (already configured in `pyproject.toml`).
- **Follow existing patterns:** dependency-inject fetchers and `now_iso` into `run()` for network-free tests, exactly like `edgar_screener/run.py`.

---

## File Structure

- `fred_screener/__init__.py` — empty package marker (Task 1).
- `fred_screener/catalog.py` — `Series` dataclass, `CATALOG` list, `select_ids()` (Task 1).
- `fred_screener/fetch.py` — HTTP client: `_http_get` backoff, `_build_url`, `parse_observations`, `fetch_series`, `fetch_observations` (Task 2).
- `fred_screener/db.py` — schema + views, `ensure_schema`, `upsert_series`, `write_observations`, `write_snapshot`, `prune` (Task 3).
- `fred_screener/run.py` — `run()` orchestration + `main()` CLI (Task 4).
- `registry.py` — add `"fred"` route (Task 5).
- Tests: `tests/test_fred_catalog.py`, `tests/test_fred_fetch.py`, `tests/test_fred_db_schema.py`, `tests/test_fred_db_write.py`, `tests/test_fred_run.py`, and additions to `tests/test_registry.py`.

---

## Task 1: Catalog + series selection

**Files:**
- Create: `fred_screener/__init__.py`
- Create: `fred_screener/catalog.py`
- Test: `tests/test_fred_catalog.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Series` frozen dataclass: `series_id: str`, `theme: str`.
  - `CATALOG: list[Series]` — the curated macro series.
  - `select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]` — resolve the ordered, de-duplicated series ids to fetch.

- [ ] **Step 1: Create the package marker**

Create `fred_screener/__init__.py` as an empty file:

```python
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_fred_catalog.py`:

```python
from fred_screener.catalog import CATALOG, Series, select_ids

VALID_THEMES = {"growth", "inflation", "rates", "labor", "credit",
                "housing", "sentiment"}


def test_catalog_ids_are_unique():
    ids = [s.series_id for s in CATALOG]
    assert len(ids) == len(set(ids))


def test_catalog_entries_have_valid_themes():
    assert CATALOG, "catalog must not be empty"
    for s in CATALOG:
        assert isinstance(s, Series)
        assert s.theme in VALID_THEMES, f"{s.series_id} has bad theme {s.theme}"


def test_select_ids_defaults_to_full_catalog():
    all_ids = [s.series_id for s in CATALOG]
    assert select_ids(all_ids, only=None, exclude=None) == all_ids


def test_select_ids_only_subsets_and_preserves_order():
    out = select_ids(["A", "B", "C"], only=["C", "A"], exclude=None)
    assert out == ["C", "A"]


def test_select_ids_excludes():
    out = select_ids(["A", "B", "C"], only=None, exclude=["B"])
    assert out == ["A", "C"]


def test_select_ids_strips_dedupes_and_drops_blanks():
    out = select_ids(["A"], only=["B", " B ", "", "C", "C"], exclude=None)
    assert out == ["B", "C"]


def test_select_ids_appends_add_after_selection():
    out = select_ids(["A", "B"], only=None, exclude=None, add=["Z", "A"])
    # add is appended; duplicates against the existing selection are dropped
    assert out == ["A", "B", "Z"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_fred_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fred_screener.catalog'`

- [ ] **Step 4: Write minimal implementation**

Create `fred_screener/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    series_id: str
    theme: str  # growth|inflation|rates|labor|credit|housing|sentiment


# Curated macro/regime reader. Ids verified live against the FRED API on
# 2026-07-02; any that 404 at implementation time should be dropped here.
CATALOG: list[Series] = [
    # growth
    Series("GDPC1", "growth"),
    Series("INDPRO", "growth"),
    Series("PAYEMS", "growth"),
    Series("RSAFS", "growth"),
    # inflation
    Series("CPIAUCSL", "inflation"),
    Series("CPILFESL", "inflation"),
    Series("PCEPILFE", "inflation"),
    Series("T5YIE", "inflation"),
    Series("T10YIE", "inflation"),
    # rates
    Series("DFF", "rates"),
    Series("DGS2", "rates"),
    Series("DGS10", "rates"),
    Series("DGS30", "rates"),
    Series("T10Y2Y", "rates"),
    Series("T10Y3M", "rates"),
    # labor
    Series("UNRATE", "labor"),
    Series("ICSA", "labor"),
    Series("CIVPART", "labor"),
    Series("JTSJOL", "labor"),
    # credit
    Series("BAMLH0A0HYM2", "credit"),
    Series("BAMLC0A0CM", "credit"),
    Series("DRSFRMACBS", "credit"),
    # housing
    Series("HOUST", "housing"),
    Series("PERMIT", "housing"),
    Series("CSUSHPINSA", "housing"),
    Series("MORTGAGE30US", "housing"),
    # sentiment
    Series("UMCSENT", "sentiment"),
    Series("VIXCLS", "sentiment"),
    Series("STLFSI4", "sentiment"),
    Series("NFCI", "sentiment"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated series ids to fetch: ``only`` (or the
    full catalog) minus ``exclude``, then any ``add`` ids appended. Tokens are
    stripped; blanks and duplicates are dropped."""
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

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_fred_catalog.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Verify catalog ids are live (drop any dead ids)**

Run this one-off probe (uses the real key; drops any id that isn't a valid series):

```bash
set -a; source .env; set +a
for id in $(.venv/bin/python -c "from fred_screener.catalog import CATALOG; print(' '.join(s.series_id for s in CATALOG))"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://api.stlouisfed.org/fred/series?series_id=$id&api_key=$FRED_API_KEY&file_type=json")
  [ "$code" != "200" ] && echo "DROP $id (HTTP $code)"
done; echo "probe done"
```
Expected: `probe done` with no `DROP` lines. If any id prints `DROP`, remove that `Series(...)` line from `CATALOG` and re-run Step 5.

- [ ] **Step 7: Commit**

```bash
git add fred_screener/__init__.py fred_screener/catalog.py tests/test_fred_catalog.py
git commit -m "feat(fred): curated macro series catalog + select_ids"
```

---

## Task 2: FRED HTTP client (`fetch.py`)

**Files:**
- Create: `fred_screener/fetch.py`
- Test: `tests/test_fred_fetch.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `parse_observations(payload: dict) -> list[dict]` → `[{"date": str, "value": float|None}, ...]` (`"."` → `None`).
  - `_build_url(path: str, params: dict, api_key: str) -> str`.
  - `_http_get(url, opener=..., attempts=5, base_delay=1.0, sleep=time.sleep) -> str` — bounded exponential backoff; retries `429`/`500`/`502`/`503`/`504` + transient network errors; honors numeric `Retry-After`.
  - `fetch_series(series_id: str, api_key: str, get=_http_get) -> dict` → metadata dict (`seriess[0]`).
  - `fetch_observations(series_id: str, api_key: str, start=None, get=_http_get) -> list[dict]`.
  - `require_api_key(api_key: str | None) -> str` — return the key or raise `RuntimeError` (never echoing the key).

> **Backoff note (rule of three):** this is the second HTTP screener with retry/backoff (EDGAR was the first). We deliberately copy a small self-contained `_http_get` here rather than import EDGAR's — FRED's retryable set differs (no `403`) and copying keeps the working EDGAR path untouched. If a *third* HTTP screener appears, extract the helper into `screener_common` then. This matches the rule-of-three reasoning in the EDGAR spec.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fred_fetch.py`:

```python
import urllib.error

import pytest

from fred_screener.fetch import (
    _build_url, _http_get, fetch_observations, fetch_series,
    parse_observations, require_api_key,
)

OBS_PAYLOAD = {
    "observations": [
        {"date": "2026-04-01", "value": "4.3"},
        {"date": "2026-05-01", "value": "."},      # missing marker
        {"date": "2026-06-01", "value": "4.2"},
    ]
}
SERIES_PAYLOAD = {
    "seriess": [{"id": "UNRATE", "title": "Unemployment Rate",
                 "frequency": "Monthly", "units": "Percent"}]
}


def test_parse_observations_maps_values_and_missing():
    rows = parse_observations(OBS_PAYLOAD)
    assert rows == [
        {"date": "2026-04-01", "value": 4.3},
        {"date": "2026-05-01", "value": None},
        {"date": "2026-06-01", "value": 4.2},
    ]


def test_build_url_includes_key_and_json_type():
    url = _build_url("series", {"series_id": "UNRATE"}, api_key="SECRET")
    assert url.startswith("https://api.stlouisfed.org/fred/series?")
    assert "series_id=UNRATE" in url
    assert "api_key=SECRET" in url
    assert "file_type=json" in url


def test_require_api_key_raises_without_echoing_key():
    with pytest.raises(RuntimeError) as exc:
        require_api_key("")
    assert "FRED_API_KEY" in str(exc.value)


def test_require_api_key_returns_present_key():
    assert require_api_key("abc123") == "abc123"


def test_fetch_series_returns_first_seriess_entry():
    got = fetch_series("UNRATE", api_key="K",
                       get=lambda url: __import__("json").dumps(SERIES_PAYLOAD))
    assert got["id"] == "UNRATE"
    assert got["title"] == "Unemployment Rate"


def test_fetch_observations_parses_and_passes_start():
    seen = {}

    def fake_get(url):
        seen["url"] = url
        return __import__("json").dumps(OBS_PAYLOAD)

    rows = fetch_observations("UNRATE", api_key="K", start="2020-01-01",
                              get=fake_get)
    assert rows[0] == {"date": "2026-04-01", "value": 4.3}
    assert "observation_start=2020-01-01" in seen["url"]


def _http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


def test_http_get_retries_on_429_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http_error(429)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0, 2.0]


def test_http_get_does_not_retry_400():
    def opener(url):
        raise _http_error(400)

    with pytest.raises(urllib.error.HTTPError) as exc:
        _http_get("http://x", opener=opener, sleep=lambda s: None)
    assert exc.value.code == 400


def test_http_get_retries_on_urlerror_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.URLError("connection reset")
        return "OK"

    assert _http_get("http://x", opener=opener, sleep=slept.append) == "OK"
    assert slept == [1.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_fred_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fred_screener.fetch'`

- [ ] **Step 3: Write minimal implementation**

Create `fred_screener/fetch.py`:

```python
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.stlouisfed.org/fred"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # FRED throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0


def require_api_key(api_key):
    """Return a non-empty API key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _build_url(path: str, params: dict, api_key: str) -> str:
    """Assemble a FRED API URL with api_key + file_type=json + caller params."""
    query = {**params, "api_key": api_key, "file_type": "json"}
    return f"{API_BASE}/{path}?{urllib.parse.urlencode(query)}"


def _urlopen(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def _retry_delay(err, attempt: int, base_delay: float) -> float:
    """Honor a numeric Retry-After header if present, else exponential backoff."""
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET a URL as text with bounded exponential backoff. Retryable: FRED
    throttling (429), transient 5xx, and transient network errors. Other HTTP
    errors (e.g. 400 bad request) raise immediately."""
    for attempt in range(1, attempts + 1):
        try:
            return opener(url)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_STATUS or attempt == attempts:
                raise
            sleep(_retry_delay(e, attempt, base_delay))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == attempts:
                raise
            sleep(_retry_delay(e, attempt, base_delay))
    raise AssertionError("unreachable")  # pragma: no cover


def parse_observations(payload: dict) -> list[dict]:
    """Map a /series/observations payload to [{date, value}], turning FRED's
    '.' missing marker into None and numeric strings into floats."""
    rows = []
    for o in payload.get("observations", []):
        raw = o.get("value")
        value = None if raw in (None, ".") else float(raw)
        rows.append({"date": o["date"], "value": value})
    return rows


def fetch_series(series_id: str, api_key: str, get=_http_get) -> dict:
    """GET /fred/series metadata; return the single seriess[0] dict."""
    url = _build_url("series", {"series_id": series_id}, api_key)
    payload = json.loads(get(url))
    seriess = payload.get("seriess") or []
    if not seriess:
        raise ValueError(f"no series metadata for {series_id}")
    return seriess[0]


def fetch_observations(series_id: str, api_key: str, start=None,
                       get=_http_get) -> list[dict]:
    """GET /fred/series/observations; return parsed [{date, value}] rows."""
    params = {"series_id": series_id}
    if start:
        params["observation_start"] = start
    url = _build_url("series/observations", params, api_key)
    return parse_observations(json.loads(get(url)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fred_fetch.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add fred_screener/fetch.py tests/test_fred_fetch.py
git commit -m "feat(fred): FRED HTTP client with backoff, series + observations"
```

---

## Task 3: Schema, upserts, views, prune (`db.py`)

**Files:**
- Create: `fred_screener/db.py`
- Test: `tests/test_fred_db_schema.py`, `tests/test_fred_db_write.py`

**Interfaces:**
- Consumes: `screener_common.connect`.
- Produces:
  - `ensure_schema(conn) -> None`.
  - `upsert_series(conn, meta_rows: list[dict], captured_at: str) -> None` — each `meta_row` is a FRED metadata dict plus a `"theme"` key.
  - `write_observations(conn, series_id: str, obs_rows: list[dict]) -> int`.
  - `write_snapshot(conn, captured_at: str, series_count: int, observation_count: int) -> int`.
  - `prune(conn, keep_days: int, now_iso: str) -> int` — deletes stale `snapshots` only.
  - `connect` re-exported from `screener_common`.

- [ ] **Step 1: Write the failing schema test**

Create `tests/test_fred_db_schema.py`:

```python
from fred_screener import db


def _tables_and_views(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
    ).fetchall()
    return {r[0] for r in rows}


def test_ensure_schema_creates_tables_and_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    names = _tables_and_views(conn)
    assert {"snapshots", "series", "observations"} <= names
    assert {"v_latest", "v_yoy_change", "v_zscore", "v_regime_signals"} <= names


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise
    assert "observations" in _tables_and_views(conn)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_fred_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fred_screener.db'`

- [ ] **Step 3: Write minimal implementation**

Create `fred_screener/db.py`:

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
    series_id                 TEXT PRIMARY KEY,
    theme                     TEXT,
    title                     TEXT,
    frequency                 TEXT,
    frequency_short           TEXT,
    units                     TEXT,
    units_short               TEXT,
    seasonal_adjustment_short TEXT,
    observation_start         TEXT,
    observation_end           TEXT,
    last_updated              TEXT,
    popularity                INTEGER,
    notes                     TEXT,
    first_seen                TEXT,
    last_seen                 TEXT
);
CREATE TABLE IF NOT EXISTS observations (
    series_id TEXT NOT NULL REFERENCES series(series_id),
    date      TEXT NOT NULL,
    value     REAL,
    PRIMARY KEY (series_id, date)
);
CREATE INDEX IF NOT EXISTS ix_observations_date ON observations(date);

-- Latest non-null observation per series, joined to metadata.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT o.series_id, o.date, o.value,
           ROW_NUMBER() OVER (PARTITION BY o.series_id
                              ORDER BY o.date DESC) AS rn
    FROM observations o
    WHERE o.value IS NOT NULL
)
SELECT r.series_id, s.theme, s.title, s.units_short, s.frequency_short,
       r.date, r.value
FROM ranked r JOIN series s ON s.series_id = r.series_id
WHERE r.rn = 1;

-- Latest value vs. the nearest observation on/before ~1 year earlier.
CREATE VIEW IF NOT EXISTS v_yoy_change AS
SELECT l.series_id, l.theme, l.title, l.date AS latest_date, l.value AS latest,
       p.value AS year_ago,
       l.value - p.value AS change_abs,
       CASE WHEN p.value IS NOT NULL AND p.value <> 0
            THEN 100.0 * (l.value - p.value) / p.value END AS change_pct
FROM v_latest l
LEFT JOIN observations p ON p.series_id = l.series_id
     AND p.value IS NOT NULL
     AND p.date = (
        SELECT MAX(o2.date) FROM observations o2
        WHERE o2.series_id = l.series_id AND o2.value IS NOT NULL
          AND o2.date <= date(l.date, '-1 year'));

-- Latest value as a z-score over the series' full stored history.
CREATE VIEW IF NOT EXISTS v_zscore AS
WITH stats AS (
    SELECT series_id, AVG(value) AS mean,
           -- population stddev; SQLite has no STDDEV, compute from moments
           CASE WHEN COUNT(value) > 1
                THEN SQRT(AVG(value*value) - AVG(value)*AVG(value)) END AS sd
    FROM observations WHERE value IS NOT NULL GROUP BY series_id
)
SELECT l.series_id, l.theme, l.title, l.value AS latest, st.mean, st.sd,
       CASE WHEN st.sd IS NOT NULL AND st.sd <> 0
            THEN (l.value - st.mean) / st.sd END AS zscore
FROM v_latest l JOIN stats st ON st.series_id = l.series_id;

-- Curated macro regime flags from the latest values (LEFT JOINs so a
-- partial --only run yields NULLs instead of erroring on missing series).
CREATE VIEW IF NOT EXISTS v_regime_signals AS
SELECT
    curve.value        AS t10y2y,
    (curve.value < 0)  AS yield_curve_inverted,
    hy.value           AS hy_spread,
    ff.value           AS fed_funds,
    unrate.value       AS unemployment
FROM (SELECT 1) base
LEFT JOIN v_latest curve  ON curve.series_id  = 'T10Y2Y'
LEFT JOIN v_latest hy     ON hy.series_id     = 'BAMLH0A0HYM2'
LEFT JOIN v_latest ff     ON ff.series_id     = 'DFF'
LEFT JOIN v_latest unrate ON unrate.series_id = 'UNRATE';
"""

_SERIES_FIELDS = ("frequency", "frequency_short", "units", "units_short",
                  "seasonal_adjustment_short", "observation_start",
                  "observation_end", "last_updated", "popularity", "notes")


def ensure_schema(conn) -> None:
    """Create tables + ELT views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_series(conn, meta_rows: list[dict], captured_at: str) -> None:
    """Upsert the series dimension: refresh metadata + last_seen, preserve
    first_seen. Each meta_row is a FRED series dict plus a 'theme' key."""
    params = []
    for m in meta_rows:
        row = {"series_id": m["id"], "theme": m.get("theme"),
               "title": m.get("title"), "seen": captured_at}
        for f in _SERIES_FIELDS:
            row[f] = m.get(f)
        params.append(row)
    conn.executemany(
        f"""INSERT INTO series
            (series_id, theme, title, {", ".join(_SERIES_FIELDS)},
             first_seen, last_seen)
            VALUES (:series_id, :theme, :title,
                    {", ".join(":" + f for f in _SERIES_FIELDS)},
                    :seen, :seen)
            ON CONFLICT(series_id) DO UPDATE SET
              theme=excluded.theme, title=excluded.title,
              {", ".join(f"{f}=excluded.{f}" for f in _SERIES_FIELDS)},
              last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_observations(conn, series_id: str, obs_rows: list[dict]) -> int:
    """Upsert observations by (series_id, date): revised values overwrite in
    place, dates are never duplicated. Dedupes within the batch (last wins)."""
    by_date = {r["date"]: r["value"] for r in obs_rows}
    conn.executemany(
        """INSERT INTO observations (series_id, date, value)
           VALUES (?, ?, ?)
           ON CONFLICT(series_id, date) DO UPDATE SET value=excluded.value""",
        [(series_id, d, v) for d, v in by_date.items()],
    )
    conn.commit()
    return len(by_date)


def write_snapshot(conn, captured_at: str, series_count: int,
                   observation_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) "
        "VALUES (?, ?, ?)",
        (captured_at, series_count, observation_count),
    )
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.

    NOTE: unlike the other screeners, observations are NOT snapshot-scoped
    (they are upserted by (series_id, date) and are the historical store), so
    this is a plain single-table delete of old snapshot headers, NOT the shared
    cascade prune in screener_common. Do not wire observations into a cascade."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run schema test to verify it passes**

Run: `.venv/bin/pytest tests/test_fred_db_schema.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Write the failing write/upsert/view tests**

Create `tests/test_fred_db_write.py`:

```python
from fred_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _meta(series_id, theme="rates", title="T", **extra):
    base = {"id": series_id, "theme": theme, "title": title}
    base.update(extra)
    return base


def test_write_observations_upserts_by_series_and_date():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")

    n1 = db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 1.0},
        {"date": "2026-02-01", "value": 2.0},
    ])
    assert n1 == 2

    # Re-run with a REVISED value for an existing date + one new date.
    n2 = db.write_observations(conn, "X", [
        {"date": "2026-02-01", "value": 2.5},   # revision
        {"date": "2026-03-01", "value": 3.0},   # new
    ])
    assert n2 == 2

    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id='X' ORDER BY date"
    ).fetchall()
    assert rows == [("2026-01-01", 1.0), ("2026-02-01", 2.5), ("2026-03-01", 3.0)]


def test_write_observations_stores_none_as_null():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [{"date": "2026-01-01", "value": None}])
    got = conn.execute(
        "SELECT value FROM observations WHERE series_id='X'").fetchone()
    assert got[0] is None


def test_upsert_series_preserves_first_seen():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X", title="Old")], "2026-01-01T00:00:00+00:00")
    db.upsert_series(conn, [_meta("X", title="New")], "2026-07-02T00:00:00+00:00")
    first_seen, last_seen, title = conn.execute(
        "SELECT first_seen, last_seen, title FROM series WHERE series_id='X'"
    ).fetchone()
    assert first_seen == "2026-01-01T00:00:00+00:00"
    assert last_seen == "2026-07-02T00:00:00+00:00"
    assert title == "New"


def test_v_latest_picks_latest_non_null():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 1.0},
        {"date": "2026-02-01", "value": 2.0},
        {"date": "2026-03-01", "value": None},   # trailing gap must be skipped
    ])
    row = conn.execute(
        "SELECT date, value FROM v_latest WHERE series_id='X'").fetchone()
    assert row == ("2026-02-01", 2.0)


def test_v_zscore_sign_on_known_distribution():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    # values 0,0,0,0,10 -> latest 10 is well above the mean -> positive z
    db.write_observations(conn, "X", [
        {"date": "2026-01-01", "value": 0.0},
        {"date": "2026-02-01", "value": 0.0},
        {"date": "2026-03-01", "value": 0.0},
        {"date": "2026-04-01", "value": 0.0},
        {"date": "2026-05-01", "value": 10.0},
    ])
    z = conn.execute(
        "SELECT zscore FROM v_zscore WHERE series_id='X'").fetchone()[0]
    assert z > 0


def test_v_yoy_change_computes_delta():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [
        {"date": "2025-06-01", "value": 100.0},
        {"date": "2026-06-01", "value": 110.0},
    ])
    row = conn.execute(
        "SELECT latest, year_ago, change_abs, change_pct "
        "FROM v_yoy_change WHERE series_id='X'").fetchone()
    assert row[0] == 110.0
    assert row[1] == 100.0
    assert row[2] == 10.0
    assert abs(row[3] - 10.0) < 1e-9


def test_prune_deletes_old_snapshots_but_not_observations():
    conn = _fresh()
    db.upsert_series(conn, [_meta("X")], "2026-07-02T00:00:00+00:00")
    db.write_observations(conn, "X", [{"date": "2020-01-01", "value": 1.0}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, "2026-07-01T00:00:00+00:00", 1, 1)  # recent

    removed = db.prune(conn, keep_days=30, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    snaps = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    assert snaps == 1      # old snapshot gone
    assert obs == 1        # observation preserved
```

- [ ] **Step 6: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_fred_db_write.py -v`
Expected: PASS (7 tests). If `v_zscore` errors on `SQRT`, note SQLite ships `sqrt` via the math functions built in from 3.35+ (Python 3.12 bundles a new-enough SQLite); if unavailable, the test will surface it here.

- [ ] **Step 7: Commit**

```bash
git add fred_screener/db.py tests/test_fred_db_schema.py tests/test_fred_db_write.py
git commit -m "feat(fred): sqlite schema, upserts, regime views, snapshot prune"
```

---

## Task 4: Orchestration + CLI (`run.py`)

**Files:**
- Create: `fred_screener/run.py`
- Test: `tests/test_fred_run.py`

**Interfaces:**
- Consumes: `catalog.CATALOG`, `catalog.select_ids`, `catalog.Series`; `fetch.fetch_series`, `fetch.fetch_observations`, `fetch.require_api_key`; `db.connect`, `db.ensure_schema`, `db.upsert_series`, `db.write_observations`, `db.write_snapshot`, `db.prune`.
- Produces:
  - `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, api_key=None, fetch_series=..., fetch_obs=..., now_iso=None) -> tuple[int, int, int]` returning `(snapshot_id, series_count, observation_count)`.
  - `main(argv=None)` CLI entry (registered as `fred_main`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fred_run.py`:

```python
from fred_screener import db, run as run_mod
from fred_screener.catalog import Series


def _theme_lookup(series_id):
    return "rates"


def _ok_series(series_id, api_key, get=None):
    return {"id": series_id, "title": f"title-{series_id}",
            "frequency": "Monthly"}


def _ok_obs(series_id, api_key, start=None, get=None):
    return [{"date": "2026-01-01", "value": 1.0},
            {"date": "2026-02-01", "value": 2.0}]


NOW = "2026-07-02T00:00:00+00:00"


def test_run_happy_path_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Series("A", "rates"), Series("B", "growth")])
    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(dbp, api_key="K", now_iso=NOW,
                              fetch_series=_ok_series, fetch_obs=_ok_obs)
    assert sc == 2
    assert oc == 4  # 2 series * 2 obs
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 2


def test_run_skips_failing_series_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Series("GOOD", "rates"), Series("BAD", "rates")])

    def flaky_series(series_id, api_key, get=None):
        if series_id == "BAD":
            raise RuntimeError("boom")
        return _ok_series(series_id, api_key)

    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(dbp, api_key="K", now_iso=NOW,
                              fetch_series=flaky_series, fetch_obs=_ok_obs)
    assert sc == 1          # only GOOD stored
    assert "BAD" in capsys.readouterr().err
    conn = db.connect(dbp)
    ids = [r[0] for r in conn.execute("SELECT series_id FROM series")]
    assert ids == ["GOOD"]


def test_run_all_fail_writes_zero_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("BAD", "rates")])

    def boom(series_id, api_key, get=None):
        raise RuntimeError("nope")

    dbp = str(tmp_path / "fred.db")
    sid, sc, oc = run_mod.run(dbp, api_key="K", now_iso=NOW,
                              fetch_series=boom, fetch_obs=_ok_obs)
    assert (sc, oc) == (0, 0)
    conn = db.connect(dbp)
    snap = conn.execute(
        "SELECT series_count, observation_count FROM snapshots").fetchone()
    assert snap == (0, 0)


def test_run_only_selects_subset(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Series("A", "rates"), Series("B", "rates")])
    dbp = str(tmp_path / "fred.db")
    _, sc, _ = run_mod.run(dbp, only=["B"], api_key="K", now_iso=NOW,
                           fetch_series=_ok_series, fetch_obs=_ok_obs)
    assert sc == 1
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT series_id FROM series")] == ["B"]


def test_run_second_run_upserts_revised_value(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Series("A", "rates")])
    dbp = str(tmp_path / "fred.db")

    def obs_v1(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.0}]

    def obs_v2(series_id, api_key, start=None, get=None):
        return [{"date": "2026-01-01", "value": 1.5}]  # revised

    run_mod.run(dbp, api_key="K", now_iso=NOW,
                fetch_series=_ok_series, fetch_obs=obs_v1)
    run_mod.run(dbp, api_key="K", now_iso=NOW,
                fetch_series=_ok_series, fetch_obs=obs_v2)

    conn = db.connect(dbp)
    rows = conn.execute("SELECT value FROM observations WHERE series_id='A'").fetchall()
    assert rows == [(1.5,)]   # single row, revised in place


def test_run_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with __import__("pytest").raises(RuntimeError) as exc:
        run_mod.run(str(tmp_path / "x.db"), api_key=None, now_iso=NOW,
                    fetch_series=_ok_series, fetch_obs=_ok_obs)
    assert "FRED_API_KEY" in str(exc.value)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_fred_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fred_screener.run'`

- [ ] **Step 3: Write minimal implementation**

Create `fred_screener/run.py`:

```python
import argparse
import os
import sys
from datetime import datetime, timezone

from fred_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        api_key=None, fetch_series=fetch.fetch_series,
        fetch_obs=fetch.fetch_observations, now_iso=None):
    """Fetch selected FRED series into SQLite, upserting observation history.
    Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("FRED_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    themes = {s.series_id: s.theme for s in catalog.CATALOG}
    all_ids = [s.series_id for s in catalog.CATALOG]
    ids = catalog.select_ids(all_ids, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_obs = 0
        for series_id in ids:
            try:
                meta = fetch_series(series_id, api_key)
                obs = fetch_obs(series_id, api_key, start=start)
            except Exception as e:  # skip-and-continue on any per-series failure
                print(f"warning: skipping {series_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            meta = {**meta, "theme": themes.get(series_id, "custom")}
            db.upsert_series(conn, [meta], now_iso)
            total_obs += db.write_observations(conn, series_id, obs)
            successes += 1

        if successes == 0:
            print("warning: no FRED series fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_obs)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_obs


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fred",
        description="Pull curated FRED macro series into SQLite")
    p.add_argument("--db", default="fred.db")
    p.add_argument("--only", default=None,
                   help="comma-separated series ids to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated series ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra series id not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="observation_start YYYY-MM-DD (default: full history)")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, sc, oc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} series into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/pytest tests/test_fred_run.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add fred_screener/run.py tests/test_fred_run.py
git commit -m "feat(fred): run orchestration + CLI with skip-and-continue"
```

---

## Task 5: Register in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `fred_screener.run.main`.
- Produces: `"fred"` entry in `registry.REGISTRY`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_fred_run.py` a registry check (kept with fred tests), or extend `tests/test_registry.py`. Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_fred():
    import registry
    assert "fred" in registry.REGISTRY
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/pytest tests/test_registry.py::test_dispatch_lists_fred -v`
Expected: FAIL with `AssertionError` (fred not in REGISTRY)

- [ ] **Step 3: Wire it in**

Modify `registry.py` — add the import and registry entry:

```python
import sys

from edgar_screener.run import main as edgar_main
from fred_screener.run import main as fred_main
from reddit_screener.run import main as reddit_main
from stock_analysis_screener.run import main as stocks_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
    "edgar": edgar_main,
    "fred": fred_main,
}
```

(Leave `dispatch()` unchanged.)

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/test_registry.py -v`
Expected: PASS (all registry tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(fred): register fred screener in dispatcher"
```

---

## Task 6: Full suite + live smoke test

**Files:** none (verification only).

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/pytest -q`
Expected: all tests PASS (existing screeners + the new fred tests), no failures.

- [ ] **Step 2: Live smoke test against the real API**

Run (small subset to stay fast; uses the real key from `.env`):

```bash
set -a; source .env; set +a
.venv/bin/python -c "
from fred_screener.run import run
from fred_screener import db
sid, sc, oc = run('/tmp/fred_smoke.db', only=['UNRATE','T10Y2Y','DFF','BAMLH0A0HYM2'])
print('snapshot', sid, 'series', sc, 'observations', oc)
conn = db.connect('/tmp/fred_smoke.db')
print('v_latest rows:', conn.execute('SELECT COUNT(*) FROM v_latest').fetchone()[0])
print('regime:', conn.execute('SELECT t10y2y, yield_curve_inverted, hy_spread, fed_funds, unemployment FROM v_regime_signals').fetchone())
"
rm -f /tmp/fred_smoke.db /tmp/fred_smoke.db-wal /tmp/fred_smoke.db-shm
```
Expected: `series 4`, a non-zero observation count (thousands), `v_latest rows: 4`, and a populated `regime:` tuple with real numbers.

- [ ] **Step 3: Final commit (if any smoke fixups were needed)**

```bash
git add -A && git commit -m "test(fred): verify live smoke run" || echo "nothing to commit"
```

---

## Self-Review Notes (author checklist — completed)

- **Spec coverage:** catalog+select (Task 1), HTTP client+backoff+`"."`→NULL+key guard (Task 2), schema+upsert-by-(series_id,date)+4 views+single-table prune (Task 3), skip-and-continue orchestration+CLI+zero-snapshot (Task 4), registry (Task 5), suite+live smoke (Task 6). All spec sections map to a task.
- **Key never logged:** `require_api_key` message + per-series warning print only the series id / class name, never the URL or key. ✓
- **Observations not pruned:** `db.prune` is single-table; a test asserts observations survive. ✓
- **Type consistency:** `fetch_series(series_id, api_key, get=...)` / `fetch_observations(series_id, api_key, start=..., get=...)` signatures match between `fetch.py`, `run.py`, and the test doubles; `run()` injects them as `fetch_series=` / `fetch_obs=`. ✓
```
