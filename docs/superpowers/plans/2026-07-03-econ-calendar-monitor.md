# Economic Release Calendar Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `econ_calendar` monitor — the forward calendar of U.S. economic releases (CPI, PPI, Employment Situation, GDP, Retail Sales, …) pulled from FRED into an `events` table — and, as its foundation, the shared `monitor_common` module every future event-date monitor reuses.

**Architecture:** This plan builds two layers. **Tasks 1–3** create `monitor_common.py` (repo-root sibling of `screener_common.py`): the `events`/`snapshots` schema, insert-or-firm-up write helpers, cancellation-aware forward-window replace, snapshot-only prune, and the `:today`-parameterised `v_upcoming`/`v_imminent` views. **Tasks 4–8** build the `econ_calendar` package (`catalog`/`fetch`/`db`/`run`) on top and register it. The monitor reuses the existing `FRED_API_KEY` and the `fred_screener.fetch` HTTP scaffolding — no new credential, no new dependency.

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `argparse`, `datetime`, `dataclasses`); `pytest` for tests. Reuses `screener_common.connect`, `http_client`, and `fred_screener.fetch`.

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the two source specs.

- **Python 3.12+, dependency-free** — stdlib + `urllib` only, via the shared `http_client` / `fred_screener.fetch` scaffolding. No new packages.
- **No new credential** — reuse `FRED_API_KEY` from `.env`; `.env.example` is unchanged. `require_api_key` raises clearly if absent and **never echoes the key value**.
- **User-Agent** (inherited via `fred_screener.fetch`): `agentic-trading-bot ninadk.dev@gmail.com`.
- **Secret hygiene (repo-wide):** per-item failures log **only** `type(e).__name__` — never `str(e)` / `e.url` (a FRED `HTTPError` embeds the API key in its URL). API keys are never printed.
- **`now_iso` is injected, never wall-clock in logic.** Every `run()` accepts `now_iso=None`, defaulting to `datetime.now(timezone.utc).isoformat()`. All "today"/"upcoming"/"imminent" logic derives from it. **Never `date('now')` in SQL.**
- **`subtype` is part of the events primary key and must NEVER be NULL** — monitors with no natural subtype write the empty string `''` (SQLite treats every NULL as distinct, which would break the natural key).
- **Prune NEVER touches future events.** `prune` is a single-table delete of old `snapshots` provenance rows only.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest` (config in `pyproject.toml`; `pythonpath=["."]`, `testpaths=["tests"]`).
- **Commits:** do NOT add a co-author line (per user global instruction).

---

## File Structure

**New — framework layer (repo root):**
- `monitor_common.py` — `connect` (re-export), `events`/`snapshots`/`calendar_now` schema, `ensure_schema`, `set_today`, `upsert_events`, `replace_forward_window`, `write_snapshot`, `v_upcoming`/`v_imminent` views, `prune`.

**New — monitor layer (`econ_calendar/` package):**
- `econ_calendar/__init__.py` — empty package marker.
- `econ_calendar/catalog.py` — `Release` dataclass, curated `CATALOG`, `select_ids`.
- `econ_calendar/fetch.py` — FRED `releases/dates` + `release/dates` fetchers (reuse `fred_screener.fetch`) and the pure `parse_release_dates`.
- `econ_calendar/db.py` — `ensure_schema` (calls `monitor_common.ensure_schema`, adds a `release_catalog` table synced from `catalog.CATALOG`, and the three econ views).
- `econ_calendar/run.py` — orchestration + argparse `main`.

**Modified:**
- `registry.py` — import `econ_calendar.run.main` and register `"econ_calendar"`.

**New tests (`tests/`):**
`test_monitor_common_schema.py`, `test_monitor_common_write.py`, `test_monitor_common_views.py`, `test_econ_calendar_catalog.py`, `test_econ_calendar_fetch.py`, `test_econ_calendar_db_schema.py`, `test_econ_calendar_db_write.py`, `test_econ_calendar_run.py`, and additions to `test_registry.py`.

### Key design decision: the `calendar_now` params table

The framework spec says the monitor views are "parameterised on `:today`" bound from the injected `now_iso`, and forbids `date('now')`. But **a SQLite `CREATE VIEW` body cannot carry a bind parameter** — you can't put `:today` inside the stored view — yet the spec's tests assert the named views *exist* and are `SELECT`-able. The reconciliation used throughout this plan: `ensure_schema` creates a **single-row `calendar_now(today, horizon_days)` table**; `run()` populates it from `now_iso` via `set_today()`; the real views read `(SELECT today FROM calendar_now)`. This keeps genuine named views *and* full determinism (tests call `set_today(now_iso)` — no wall clock, no `date('now')`).

---

## Task 1: `monitor_common` — schema + `set_today`

**Files:**
- Create: `monitor_common.py`
- Test: `tests/test_monitor_common_schema.py`

**Interfaces:**
- Consumes: `screener_common.connect`.
- Produces:
  - `connect(path: str) -> sqlite3.Connection` (re-export)
  - `ensure_schema(conn) -> None` — creates `events`, `snapshots`, `calendar_now` + indexes; idempotent.
  - `set_today(conn, now_iso: str, horizon_days: int = 7) -> str` — writes `date(now_iso)` + horizon into the singleton `calendar_now` row; returns the `YYYY-MM-DD` today.

- [ ] **Step 1: Write the failing test**

Create `tests/test_monitor_common_schema.py`:

```python
from monitor_common import connect, ensure_schema, set_today


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def test_ensure_schema_creates_tables():
    conn = _fresh()
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"events", "snapshots", "calendar_now"} <= names


def test_ensure_schema_idempotent_keeps_singleton():
    conn = _fresh()
    ensure_schema(conn)  # second call must not raise
    n = conn.execute("SELECT COUNT(*) FROM calendar_now").fetchone()[0]
    assert n == 1


def test_set_today_writes_date_and_horizon():
    conn = _fresh()
    today = set_today(conn, "2026-07-03T12:00:00+00:00", horizon_days=5)
    assert today == "2026-07-03"
    row = conn.execute(
        "SELECT today, horizon_days FROM calendar_now WHERE id=0").fetchone()
    assert row == ("2026-07-03", 5)


def test_subtype_defaults_to_empty_string_not_null():
    conn = _fresh()
    conn.execute("INSERT INTO events (event_type, event_date, source, fetched_at) "
                 "VALUES ('x', '2026-07-03', 'fred', 't')")
    conn.commit()
    assert conn.execute("SELECT subtype FROM events").fetchone()[0] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_monitor_common_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'monitor_common'`

- [ ] **Step 3: Write minimal implementation**

Create `monitor_common.py`:

```python
"""Shared store for event-date monitors — the forward-calendar analogue of
screener_common. Monitors (econ_calendar, fomc_calendar, market_calendar, ...)
reuse this for the events schema, write semantics, shared views, and prune.

Views are parameterised on 'today' via the single-row calendar_now table (a
SQLite view body cannot bind :today); callers set it from the injected now_iso
with set_today() — never date('now'), so tests are deterministic."""
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "set_today", "upsert_events",
           "replace_forward_window", "write_snapshot", "prune"]

_EVENT_COLS = ("event_type", "event_date", "event_time", "subtype", "title",
               "status", "source", "payload")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,               -- YYYY-MM-DD
    event_time TEXT,                        -- 'HH:MM' ET if known else NULL
    subtype    TEXT NOT NULL DEFAULT '',    -- part of the natural key; '' not NULL
    title      TEXT,
    status     TEXT,                        -- tentative|scheduled|confirmed|released
    source     TEXT NOT NULL,
    payload    TEXT,                         -- optional JSON extras
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (event_type, event_date, subtype)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT,
    event_count INTEGER,
    source      TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);

-- Single-row params table so real named views can filter on an injected 'today'.
CREATE TABLE IF NOT EXISTS calendar_now (
    id           INTEGER PRIMARY KEY CHECK (id = 0),
    today        TEXT NOT NULL DEFAULT '',
    horizon_days INTEGER NOT NULL DEFAULT 7
);
INSERT OR IGNORE INTO calendar_now (id, today, horizon_days) VALUES (0, '', 7);

-- Forward calendar: everything from today onward.
CREATE VIEW IF NOT EXISTS v_upcoming AS
SELECT e.* FROM events e, calendar_now p
WHERE e.event_date >= p.today
ORDER BY e.event_date, e.event_time;

-- Near-term watch list: today .. today + horizon_days.
CREATE VIEW IF NOT EXISTS v_imminent AS
SELECT e.* FROM events e, calendar_now p
WHERE e.event_date BETWEEN p.today
      AND date(p.today, '+' || p.horizon_days || ' days')
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Create the events/snapshots/calendar_now schema + shared views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def set_today(conn, now_iso: str, horizon_days: int = 7) -> str:
    """Set the calendar_now singleton from the injected now_iso. Returns today
    as YYYY-MM-DD. Every view's :today derives from here — never date('now')."""
    today = datetime.fromisoformat(now_iso).date().isoformat()
    conn.execute("UPDATE calendar_now SET today=?, horizon_days=? WHERE id=0",
                 (today, horizon_days))
    conn.commit()
    return today
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_monitor_common_schema.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add monitor_common.py tests/test_monitor_common_schema.py
git commit -m "feat(monitor_common): events/snapshots schema + calendar_now params + set_today"
```

---

## Task 2: `monitor_common` — write semantics

**Files:**
- Modify: `monitor_common.py` (append `upsert_events`, `replace_forward_window`, `write_snapshot`)
- Test: `tests/test_monitor_common_write.py`

**Interfaces:**
- Consumes: the `events`/`snapshots` schema from Task 1; `_EVENT_COLS`.
- Produces:
  - `upsert_events(conn, rows: list[dict], fetched_at: str) -> int` — insert-or-firm-up by `(event_type, event_date, subtype)`; dedupes within the batch (last wins); returns distinct rows written.
  - `replace_forward_window(conn, event_type: str, today: str, rows: list[dict], fetched_at: str) -> int` — delete `event_date >= today` for that `event_type`, insert `rows`; past untouched; returns rows inserted.
  - `write_snapshot(conn, captured_at: str, event_count: int, source: str) -> int` — one run header; returns snapshot id.
  - Each `dict` row carries keys: `event_type, event_date, event_time, subtype, title, status, source, payload` (`subtype`/`payload` may be `""`/`None`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_monitor_common_write.py`:

```python
from monitor_common import (connect, ensure_schema, upsert_events,
                            replace_forward_window, write_snapshot)


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def _row(event_type, date, subtype="", status="scheduled",
         time="08:30", title="T"):
    return {"event_type": event_type, "event_date": date, "event_time": time,
            "subtype": subtype, "title": title, "status": status,
            "source": "fred", "payload": None}


def test_upsert_inserts_then_firms_up_in_place():
    conn = _fresh()
    upsert_events(conn, [_row("cpi_release", "2026-08-12", "10",
                              status="tentative")], "t1")
    upsert_events(conn, [_row("cpi_release", "2026-08-12", "10",
                              status="confirmed")], "t2")
    rows = conn.execute("SELECT status, fetched_at FROM events").fetchall()
    assert rows == [("confirmed", "t2")]        # one row, updated in place


def test_upsert_dedupes_within_batch_last_wins():
    conn = _fresh()
    n = upsert_events(conn, [
        _row("cpi_release", "2026-08-12", "10", status="tentative"),
        _row("cpi_release", "2026-08-12", "10", status="confirmed"),
    ], "t")
    assert n == 1
    assert conn.execute("SELECT status FROM events").fetchone()[0] == "confirmed"


def test_replace_forward_window_drops_old_future_keeps_past():
    conn = _fresh()
    upsert_events(conn, [_row("opex", "2026-06-19"),      # past vs today
                         _row("opex", "2026-09-18")], "t")  # stale future
    n = replace_forward_window(conn, "opex", "2026-07-03",
                               [_row("opex", "2026-08-21")], "t2")
    assert n == 1
    dates = [r[0] for r in conn.execute(
        "SELECT event_date FROM events ORDER BY event_date")]
    assert dates == ["2026-06-19", "2026-08-21"]  # past kept, old future gone


def test_write_snapshot_returns_id_and_stores_source_and_count():
    conn = _fresh()
    sid = write_snapshot(conn, "2026-07-03T00:00:00+00:00", 7, "fred")
    got = conn.execute("SELECT event_count, source FROM snapshots WHERE id=?",
                       (sid,)).fetchone()
    assert got == (7, "fred")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_monitor_common_write.py -v`
Expected: FAIL — `ImportError: cannot import name 'upsert_events'`

- [ ] **Step 3: Write minimal implementation**

Append to `monitor_common.py`:

```python
def upsert_events(conn, rows: list[dict], fetched_at: str) -> int:
    """Insert-or-firm-up events by (event_type, event_date, subtype). A date that
    firms up (tentative -> confirmed) or gains a time updates in place; no
    duplicate row. Dedupes within the batch (last wins). Returns distinct rows."""
    by_key = {(r["event_type"], r["event_date"], r.get("subtype") or ""): r
              for r in rows}
    params = [(r["event_type"], r["event_date"], r.get("event_time"),
               r.get("subtype") or "", r.get("title"), r.get("status"),
               r["source"], r.get("payload"), fetched_at)
              for r in by_key.values()]
    conn.executemany(
        f"""INSERT INTO events ({", ".join(_EVENT_COLS)}, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_type, event_date, subtype) DO UPDATE SET
              event_time=excluded.event_time, title=excluded.title,
              status=excluded.status, source=excluded.source,
              payload=excluded.payload, fetched_at=excluded.fetched_at""",
        params,
    )
    conn.commit()
    return len(params)


def replace_forward_window(conn, event_type: str, today: str,
                           rows: list[dict], fetched_at: str) -> int:
    """Cancellation-aware path for one event_type: delete future rows
    (event_date >= today) then insert the freshly-fetched set, so a source that
    stops listing a future event lets that row disappear. Past events
    (event_date < today) are NEVER touched. Returns rows inserted."""
    conn.execute("DELETE FROM events WHERE event_type=? AND event_date >= ?",
                 (event_type, today))
    n = upsert_events(conn, rows, fetched_at)  # commits
    return n


def write_snapshot(conn, captured_at: str, event_count: int, source: str) -> int:
    """Insert one run-provenance header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, event_count, source) VALUES (?, ?, ?)",
        (captured_at, event_count, source),
    )
    conn.commit()
    return cur.lastrowid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_monitor_common_write.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add monitor_common.py tests/test_monitor_common_write.py
git commit -m "feat(monitor_common): upsert_events, replace_forward_window, write_snapshot"
```

---

## Task 3: `monitor_common` — prune + shared-view behavior

**Files:**
- Modify: `monitor_common.py` (append `prune`)
- Test: `tests/test_monitor_common_views.py`

**Interfaces:**
- Consumes: `set_today` (Task 1), `upsert_events`/`write_snapshot` (Task 2), the `v_upcoming`/`v_imminent` views (Task 1).
- Produces:
  - `prune(conn, keep_days: int, now_iso: str) -> int` — delete `snapshots` older than `keep_days` before `now_iso`; **never** touches `events`; returns snapshots removed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_monitor_common_views.py`:

```python
from monitor_common import (connect, ensure_schema, upsert_events,
                            write_snapshot, set_today, prune)


def _fresh():
    conn = connect(":memory:")
    ensure_schema(conn)
    return conn


def _row(date):
    return {"event_type": "a", "event_date": date, "event_time": "08:30",
            "subtype": "", "title": "T", "status": "scheduled",
            "source": "fred", "payload": None}


def test_v_upcoming_includes_today_excludes_past():
    conn = _fresh()
    set_today(conn, "2026-07-03T00:00:00+00:00")
    upsert_events(conn, [_row("2026-06-01"), _row("2026-07-03"),
                         _row("2026-08-01")], "t")
    dates = [r[0] for r in conn.execute("SELECT event_date FROM v_upcoming")]
    assert dates == ["2026-07-03", "2026-08-01"]


def test_v_imminent_respects_horizon_boundary():
    conn = _fresh()
    set_today(conn, "2026-07-03T00:00:00+00:00", horizon_days=7)
    upsert_events(conn, [_row("2026-07-05"),   # 2 days out -> in
                         _row("2026-07-10"),   # 7 days out -> in (inclusive)
                         _row("2026-07-20")], "t")  # 17 days out -> out
    dates = [r[0] for r in conn.execute("SELECT event_date FROM v_imminent")]
    assert dates == ["2026-07-05", "2026-07-10"]


def test_prune_deletes_old_snapshots_but_never_events():
    conn = _fresh()
    set_today(conn, "2026-07-03T00:00:00+00:00")
    upsert_events(conn, [_row("2026-12-31")], "t")            # far-future event
    write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, "fred")  # old header
    write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, "fred")  # recent header
    removed = prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_monitor_common_views.py -v`
Expected: FAIL — `ImportError: cannot import name 'prune'`

- [ ] **Step 3: Write minimal implementation**

Append to `monitor_common.py`:

```python
def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.

    Single-table delete of snapshot headers only, exactly like
    fred_screener.db.prune. It must NEVER prune events: the whole point of a
    monitor is the forward calendar. Compares captured_at to a UTC isoformat
    cutoff as a plain string (fixed-width, so lexicographic '<' is correct)."""
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

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_monitor_common_views.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the whole monitor_common suite and commit**

Run: `python -m pytest tests/test_monitor_common_schema.py tests/test_monitor_common_write.py tests/test_monitor_common_views.py -v`
Expected: PASS (11 tests) — `monitor_common` is now a complete, reusable framework.

```bash
git add monitor_common.py tests/test_monitor_common_views.py
git commit -m "feat(monitor_common): snapshot-only prune + shared upcoming/imminent views"
```

---

## Task 4: `econ_calendar.catalog` — curated release catalog

**Files:**
- Create: `econ_calendar/__init__.py` (empty)
- Create: `econ_calendar/catalog.py`
- Test: `tests/test_econ_calendar_catalog.py`

**Interfaces:**
- Produces:
  - `Release` frozen dataclass: `release_id: int, event_type: str, label: str, impact: str, category: str, release_time: str`.
  - `CATALOG: list[Release]`.
  - `select_ids(only=None, exclude=None) -> list[int]` — ordered, de-duplicated release_ids; `only`/`exclude` are optional iterables of stringy ints; blanks/dupes dropped.

> **Live-verification action (do this before finalizing the catalog):** confirm each `release_id` against `GET https://api.stlouisfed.org/fred/releases?api_key=KEY&file_type=json`. Drop any id that 404s (leave a comment), and resolve the ids the spec left open — Retail Sales (`~99`), PCE / Personal Income & Outlays, JOLTS — adding a `Release` row for each once its id is confirmed. The starting set below is the spec's numbered, higher-confidence ids; it yields a working monitor immediately.

- [ ] **Step 1: Write the failing test**

Create `tests/test_econ_calendar_catalog.py`:

```python
from econ_calendar.catalog import CATALOG, Release, select_ids

_VALID_IMPACT = {"high", "med"}
_VALID_CATEGORY = {"inflation", "labor", "growth", "consumer"}


def test_catalog_release_ids_unique():
    ids = [r.release_id for r in CATALOG]
    assert len(ids) == len(set(ids))


def test_catalog_fields_valid_and_every_release_has_a_time():
    for r in CATALOG:
        assert r.impact in _VALID_IMPACT
        assert r.category in _VALID_CATEGORY
        assert r.release_time and ":" in r.release_time


def test_catalog_has_the_high_impact_core():
    types = {r.event_type for r in CATALOG}
    assert {"cpi_release", "employment_situation", "ppi_release",
            "gdp_release"} <= types


def test_select_ids_defaults_to_full_catalog():
    assert select_ids() == [r.release_id for r in CATALOG]


def test_select_ids_only_keeps_order():
    assert select_ids(only=["10", "46"]) == [10, 46]


def test_select_ids_exclude_removes():
    got = select_ids(exclude=["10"])
    assert 10 not in got and 46 in got


def test_select_ids_strips_and_dedupes():
    assert select_ids(only=[" 10 ", "10", "46"]) == [10, 46]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_econ_calendar_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'econ_calendar'`

- [ ] **Step 3: Write minimal implementation**

Create `econ_calendar/__init__.py` (empty file):

```python
```

Create `econ_calendar/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Release:
    release_id: int      # FRED release id
    event_type: str      # stable per-release slug, e.g. 'cpi_release'
    label: str           # human name, e.g. 'Consumer Price Index'
    impact: str          # 'high' | 'med'
    category: str        # 'inflation' | 'labor' | 'growth' | 'consumer'
    release_time: str    # 'HH:MM' ET known time; sole source of events.event_time


# Curated high/med-impact U.S. macro releases. Ids are the spec's numbered set;
# confirm each live against /fred/releases before shipping and drop any that
# 404. Most U.S. macro data prints at 08:30 ET (BLS/BEA/Census).
CATALOG: list[Release] = [
    Release(10, "cpi_release", "Consumer Price Index", "high", "inflation", "08:30"),
    Release(50, "employment_situation", "Employment Situation", "high", "labor", "08:30"),
    Release(46, "ppi_release", "Producer Price Index", "high", "inflation", "08:30"),
    Release(53, "gdp_release", "Gross Domestic Product", "high", "growth", "08:30"),
    Release(99, "retail_sales_release", "Advance Retail Sales", "high", "consumer", "08:30"),
]


def select_ids(only=None, exclude=None) -> list[int]:
    """Resolve the ordered, de-duplicated release_ids to pull: ``only`` (or the
    full catalog) minus ``exclude``. Tokens may be str or int; blanks and
    duplicates are dropped."""
    ids = _coerce(only) if only else [r.release_id for r in CATALOG]
    ex = set(_coerce(exclude))
    out, seen = [], set()
    for i in ids:
        if i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out


def _coerce(values: Iterable) -> list[int]:
    """Turn an iterable of str/int tokens into ints, dropping blanks."""
    out = []
    for v in values or ():
        s = str(v).strip()
        if s:
            out.append(int(s))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_econ_calendar_catalog.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add econ_calendar/__init__.py econ_calendar/catalog.py tests/test_econ_calendar_catalog.py
git commit -m "feat(econ_calendar): curated FRED release catalog + select_ids"
```

---

## Task 5: `econ_calendar.fetch` — FRED calendar fetchers + pure parse

**Files:**
- Create: `econ_calendar/fetch.py`
- Test: `tests/test_econ_calendar_fetch.py`

**Interfaces:**
- Consumes: `fred_screener.fetch` (`_http_get`, `_build_url`, `require_api_key`); `econ_calendar.catalog.Release`.
- Produces:
  - `require_api_key` / `_http_get` — re-exported from `fred_screener.fetch` (written once).
  - `fetch_all_release_dates(api_key, today, get=_http_get) -> list[dict]` — the backbone `releases/dates` call; raw `{release_id, release_name, date}` rows.
  - `fetch_release_dates(release_id, api_key, today, get=_http_get) -> list[dict]` — the per-release `release/dates` variant.
  - `parse_release_dates(rows: list[dict], by_id: dict[int, Release]) -> list[dict]` — **pure**: filter to catalog ids, map each to an `events` row (`event_type, event_date, event_time, subtype, title, status, source, payload`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_econ_calendar_fetch.py`:

```python
import json
import urllib.error

import pytest

from econ_calendar import fetch
from econ_calendar.catalog import Release

REL = {10: Release(10, "cpi_release", "Consumer Price Index",
                   "high", "inflation", "08:30")}
PAYLOAD = {"release_dates": [
    {"release_id": 10, "release_name": "Consumer Price Index", "date": "2026-08-12"},
    {"release_id": 999, "release_name": "Not In Catalog", "date": "2026-08-13"},
]}


def test_parse_filters_to_catalog_and_maps_fields():
    rows = fetch.parse_release_dates(PAYLOAD["release_dates"], REL)
    assert len(rows) == 1                       # 999 dropped
    r = rows[0]
    assert r["event_type"] == "cpi_release"
    assert r["event_date"] == "2026-08-12"
    assert r["event_time"] == "08:30"           # from the catalog known-time
    assert r["subtype"] == "10"                 # str(release_id)
    assert r["status"] == "scheduled"
    assert r["source"] == "fred"


def test_fetch_all_url_has_no_data_flag_and_realtime_start():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps(PAYLOAD)

    out = fetch.fetch_all_release_dates("SECRET", "2026-07-03", get=get)
    assert out == PAYLOAD["release_dates"]
    assert "include_release_dates_with_no_data=true" in seen["url"]
    assert "realtime_start=2026-07-03" in seen["url"]


def test_fetch_release_dates_url_includes_release_id_and_flag():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps(PAYLOAD)

    fetch.fetch_release_dates(10, "SECRET", "2026-07-03", get=get)
    assert "release_id=10" in seen["url"]
    assert "include_release_dates_with_no_data=true" in seen["url"]
    assert "realtime_start=2026-07-03" in seen["url"]


def test_require_api_key_raises_without_echoing_key():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "FRED_API_KEY" in str(exc.value)


def _http_error(code):
    return urllib.error.HTTPError("http://x?api_key=SECRET", code, "e", {}, None)


def test_http_get_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps(PAYLOAD)

    out = fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert json.loads(out) == PAYLOAD
    assert slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_econ_calendar_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'econ_calendar.fetch'`

- [ ] **Step 3: Write minimal implementation**

Create `econ_calendar/fetch.py`:

```python
import json

# Reuse the FRED client written once in fred_screener.fetch: same host, same key,
# same bounded backoff (429/5xx), same require_api_key (never echoes the key).
from fred_screener.fetch import _build_url, _http_get, require_api_key

__all__ = ["require_api_key", "_http_get", "fetch_all_release_dates",
           "fetch_release_dates", "parse_release_dates"]

# The key parameter: default (false) strips future dates, making the endpoint
# backward-looking and useless for a monitor. 'true' surfaces the forward calendar.
_NO_DATA = "true"


def fetch_all_release_dates(api_key, today, get=_http_get) -> list[dict]:
    """Backbone call: all upcoming release dates from today forward."""
    url = _build_url("releases/dates", {
        "include_release_dates_with_no_data": _NO_DATA,
        "sort_order": "asc",
        "order_by": "release_date",
        "realtime_start": today,
    }, api_key)
    return json.loads(get(url)).get("release_dates", [])


def fetch_release_dates(release_id, api_key, today, get=_http_get) -> list[dict]:
    """Per-release variant: one release's upcoming dates from today forward."""
    url = _build_url("release/dates", {
        "release_id": release_id,
        "include_release_dates_with_no_data": _NO_DATA,
        "realtime_start": today,
        "sort_order": "asc",
    }, api_key)
    return json.loads(get(url)).get("release_dates", [])


def parse_release_dates(rows: list[dict], by_id: dict) -> list[dict]:
    """Pure: filter raw FRED release-date rows to catalog ids and map each to an
    events row. event_time comes from the catalog's known-time (FRED gives the
    date only). Status is 'scheduled' for v1 — FRED carries no verified
    provisional flag; firm-up to 'tentative'/'confirmed' is a documented follow-up."""
    out = []
    for raw in rows:
        release = by_id.get(raw.get("release_id"))
        if release is None:
            continue
        out.append({
            "event_type": release.event_type,
            "event_date": raw["date"],
            "event_time": release.release_time,
            "subtype": str(release.release_id),
            "title": raw.get("release_name") or release.label,
            "status": "scheduled",
            "source": "fred",
            "payload": json.dumps({"release_id": release.release_id}),
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_econ_calendar_fetch.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add econ_calendar/fetch.py tests/test_econ_calendar_fetch.py
git commit -m "feat(econ_calendar): FRED releases/dates fetchers + pure parse_release_dates"
```

---

## Task 6: `econ_calendar.db` — schema + econ views

**Files:**
- Create: `econ_calendar/db.py`
- Test: `tests/test_econ_calendar_db_schema.py`, `tests/test_econ_calendar_db_write.py`

**Interfaces:**
- Consumes: `monitor_common` (`connect`, `ensure_schema` as `_mc_ensure_schema`, `upsert_events`, `set_today`); `econ_calendar.catalog.CATALOG`.
- Produces:
  - `connect` — re-export from `monitor_common`.
  - `ensure_schema(conn) -> None` — calls `monitor_common.ensure_schema`, creates+syncs a `release_catalog` table from `CATALOG`, and creates `v_upcoming_releases`, `v_imminent_high_impact`, `v_this_week`. Idempotent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_econ_calendar_db_schema.py`:

```python
from econ_calendar import db
from econ_calendar.catalog import CATALOG


def test_ensure_schema_creates_events_snapshots_catalog_and_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "release_catalog"} <= tables
    assert {"v_upcoming_releases", "v_imminent_high_impact",
            "v_this_week"} <= views


def test_ensure_schema_idempotent_and_syncs_full_catalog():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise or duplicate rows
    n = conn.execute("SELECT COUNT(*) FROM release_catalog").fetchone()[0]
    assert n == len(CATALOG)
```

Create `tests/test_econ_calendar_db_write.py`:

```python
import monitor_common
from econ_calendar import db
from econ_calendar.catalog import CATALOG

CPI = next(r for r in CATALOG if r.event_type == "cpi_release")


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _evt(event_type, date, subtype, status="scheduled"):
    return {"event_type": event_type, "event_date": date, "event_time": "08:30",
            "subtype": subtype, "title": "T", "status": status,
            "source": "fred", "payload": None}


def test_upsert_firms_up_no_duplicate():
    conn = _fresh()
    sub = str(CPI.release_id)
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", sub, "tentative")], "t1")
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", sub, "confirmed")], "t2")
    assert conn.execute("SELECT status FROM events").fetchall() == [("confirmed",)]


def test_v_imminent_high_impact_filters_high_within_horizon():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00", horizon_days=14)
    sub = str(CPI.release_id)
    monitor_common.upsert_events(conn, [
        _evt("cpi_release", "2026-08-12", sub),   # high, 11 days out -> in
        _evt("cpi_release", "2026-09-30", sub),   # high, outside horizon -> out
    ], "t")
    got = [r[0] for r in conn.execute(
        "SELECT event_date FROM v_imminent_high_impact")]
    assert got == ["2026-08-12"]


def test_v_upcoming_releases_joins_catalog_impact_and_label():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00")
    monitor_common.upsert_events(
        conn, [_evt("cpi_release", "2026-08-12", str(CPI.release_id))], "t")
    row = conn.execute(
        "SELECT event_type, impact, label FROM v_upcoming_releases").fetchone()
    assert row == ("cpi_release", CPI.impact, CPI.label)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_econ_calendar_db_schema.py tests/test_econ_calendar_db_write.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'econ_calendar.db'`

- [ ] **Step 3: Write minimal implementation**

Create `econ_calendar/db.py`:

```python
from monitor_common import connect
from monitor_common import ensure_schema as _mc_ensure_schema

from econ_calendar.catalog import CATALOG

__all__ = ["connect", "ensure_schema"]

# release_catalog materializes the Python catalog so the views can JOIN impact /
# label / category in SQL. v_this_week runs today .. the coming Sunday
# (weekday 0), for a weekly planning glance.
_ECON_SCHEMA = """
CREATE TABLE IF NOT EXISTS release_catalog (
    event_type   TEXT PRIMARY KEY,
    release_id   INTEGER NOT NULL,
    label        TEXT NOT NULL,
    impact       TEXT NOT NULL,
    category     TEXT NOT NULL,
    release_time TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_upcoming_releases AS
SELECT u.event_type, u.event_date, u.event_time, u.subtype, u.title, u.status,
       c.label, c.impact, c.category
FROM v_upcoming u
JOIN release_catalog c ON c.event_type = u.event_type
ORDER BY u.event_date, u.event_time;

CREATE VIEW IF NOT EXISTS v_imminent_high_impact AS
SELECT i.event_type, i.event_date, i.event_time, i.subtype, i.title, i.status,
       c.label, c.impact, c.category
FROM v_imminent i
JOIN release_catalog c ON c.event_type = i.event_type
WHERE c.impact = 'high'
ORDER BY i.event_date, i.event_time;

CREATE VIEW IF NOT EXISTS v_this_week AS
SELECT u.event_type, u.event_date, u.event_time, u.subtype, u.title, u.status,
       c.label, c.impact, c.category
FROM v_upcoming u
JOIN release_catalog c ON c.event_type = u.event_type,
     calendar_now p
WHERE u.event_date <= date(p.today, 'weekday 0')
ORDER BY u.event_date, u.event_time;
"""


def ensure_schema(conn) -> None:
    """Create the shared monitor schema + econ-specific catalog table and views,
    then sync release_catalog from CATALOG. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_ECON_SCHEMA)
    conn.executemany(
        """INSERT INTO release_catalog
           (event_type, release_id, label, impact, category, release_time)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(event_type) DO UPDATE SET
             release_id=excluded.release_id, label=excluded.label,
             impact=excluded.impact, category=excluded.category,
             release_time=excluded.release_time""",
        [(r.event_type, r.release_id, r.label, r.impact, r.category,
          r.release_time) for r in CATALOG],
    )
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_econ_calendar_db_schema.py tests/test_econ_calendar_db_write.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add econ_calendar/db.py tests/test_econ_calendar_db_schema.py tests/test_econ_calendar_db_write.py
git commit -m "feat(econ_calendar): db schema, release_catalog sync, upcoming/imminent/this-week views"
```

---

## Task 7: `econ_calendar.run` — orchestration + CLI

**Files:**
- Create: `econ_calendar/run.py`
- Test: `tests/test_econ_calendar_run.py`

**Interfaces:**
- Consumes: `econ_calendar.catalog` (`CATALOG`, `select_ids`), `econ_calendar.db` (`connect`, `ensure_schema`), `econ_calendar.fetch` (`require_api_key`, `fetch_release_dates`, `parse_release_dates`), `monitor_common` (`set_today`, `upsert_events`, `write_snapshot`, `prune`).
- Produces:
  - `run(db_path, only=None, exclude=None, horizon_days=7, keep_days=None, api_key=None, fetch_one=fetch.fetch_release_dates, now_iso=None) -> (snapshot_id, event_count)`.
  - `main(argv=None)` — argparse CLI, `prog="econ_calendar"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_econ_calendar_run.py`:

```python
import sqlite3

from econ_calendar import run as runmod

NOW = "2026-08-01T00:00:00+00:00"


def _raw(release_id, dates):
    return [{"release_id": release_id, "release_name": "X", "date": d}
            for d in dates]


def test_run_happy_path_counts_and_writes(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-08-12"])

    sid, count = runmod.run(db_path, only=["10"], api_key="K",
                            fetch_one=fetch_one, now_iso=NOW)
    assert count == 1
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_skips_release_that_raises_without_leaking_secret(tmp_path, capsys):
    def fetch_one(release_id, api_key, today):
        if release_id == 10:
            raise RuntimeError("http://api?api_key=SECRET boom")
        return _raw(release_id, ["2026-08-12"])

    sid, count = runmod.run(str(tmp_path / "e.db"), only=["10", "46"],
                            api_key="K", fetch_one=fetch_one, now_iso=NOW)
    assert count == 1                      # 10 skipped, 46 written
    err = capsys.readouterr().err
    assert "skipping 10" in err
    assert "SECRET" not in err             # secret hygiene: only the type name


def test_run_only_and_exclude_select_ids(tmp_path):
    seen = []

    def fetch_one(release_id, api_key, today):
        seen.append(release_id)
        return _raw(release_id, ["2026-08-12"])

    runmod.run(str(tmp_path / "e.db"), only=["10", "46"], exclude=["46"],
               api_key="K", fetch_one=fetch_one, now_iso=NOW)
    assert seen == [10]


def test_run_second_run_firms_up_not_duplicated(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-08-12"])

    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW)
    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_keep_days_prunes_snapshots_not_future_events(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-12-31"])   # far-future event

    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one,
               now_iso="2026-01-01T00:00:00+00:00")             # old snapshot
    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one,
               now_iso=NOW, keep_days=30)                       # prunes old
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_econ_calendar_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'econ_calendar.run'`

- [ ] **Step 3: Write minimal implementation**

Create `econ_calendar/run.py`:

```python
import argparse
import os
import sys
from datetime import datetime, timezone

import monitor_common
from econ_calendar import catalog, db, fetch


def run(db_path, only=None, exclude=None, horizon_days=7, keep_days=None,
        api_key=None, fetch_one=fetch.fetch_release_dates, now_iso=None):
    """Fetch upcoming release dates for the selected FRED releases, upsert them
    into the events calendar, snapshot the run, and optionally prune old
    snapshots. Returns (snapshot_id, event_count).

    Per-release fetch is skip-and-continue: one release failing never aborts the
    run, and only type(e).__name__ is logged (a FRED URL embeds the api_key)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("FRED_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()

    ids = catalog.select_ids(only, exclude)
    by_id = {r.release_id: r for r in catalog.CATALOG}

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days)
        rows = []
        for release_id in ids:
            try:
                raw = fetch_one(release_id, api_key, today)
                rows.extend(fetch.parse_release_dates(raw, {release_id:
                                                            by_id[release_id]}))
            except Exception as e:  # skip-and-continue; never echo str(e)/e.url
                conn.rollback()
                print(f"warning: skipping {release_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
        count = monitor_common.upsert_events(conn, rows, now_iso)
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count, "fred")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="econ_calendar",
        description="Pull the FRED forward economic-release calendar into SQLite")
    p.add_argument("--db", default="econ_calendar.db")
    p.add_argument("--only", default=None,
                   help="comma-separated release_ids to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated release_ids to skip")
    p.add_argument("--horizon-days", type=int, default=7,
                   help="imminence window for v_imminent_high_impact")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, count = run(a.db, only=only, exclude=exclude,
                   horizon_days=a.horizon_days, keep_days=a.keep_days)
    print(f"stored {count} scheduled releases into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_econ_calendar_run.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add econ_calendar/run.py tests/test_econ_calendar_run.py
git commit -m "feat(econ_calendar): run orchestration (skip-and-continue) + argparse CLI"
```

---

## Task 8: Register `econ_calendar` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

**Interfaces:**
- Consumes: `econ_calendar.run.main`.
- Produces: `"econ_calendar"` key in `registry.REGISTRY`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py` (append at end):

```python
def test_dispatch_lists_econ_calendar():
    import registry
    assert "econ_calendar" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_registry.py::test_dispatch_lists_econ_calendar -v`
Expected: FAIL — `AssertionError` (`econ_calendar` not in REGISTRY)

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import alongside the others:

```python
from econ_calendar.run import main as econ_calendar_main
```

And add the entry to the `REGISTRY` dict (after `"options"`):

```python
    "options": options_main,
    "econ_calendar": econ_calendar_main,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_registry.py -v`
Expected: PASS (all registry tests, including the new one)

- [ ] **Step 5: Run the full suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green — the new modules plus all existing screeners)

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(econ_calendar): register econ_calendar dispatcher"
```

---

## Task 9: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `econ_calendar` to Built and mark the plan**

In `docs/ROADMAP.md`:
- Add an `econ_calendar` row to the **Built ✅** table (with links to this plan and the two specs), following the existing row format.
- Remove the `econ_calendar` row from the **Spec'd — event-date monitors 📝** table.
- In **Recommended build order**, strike through item 3 (`econ_calendar`) as ✅ Built, mirroring how items 1–2 are struck through, and note that `monitor_common` shipped as its foundation.
- Under **Architecture**, note that `monitor_common.py` now exists (the framework spec's `monitor_common` is realized).

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark econ_calendar Built; monitor_common framework landed"
```

---

## Self-Review

**1. Spec coverage** (econ-calendar spec + framework spec):

| Spec requirement | Task |
|---|---|
| `monitor_common` events/snapshots schema, `subtype` NOT NULL `''`, indexes | Task 1 |
| `now_iso` injection / `set_today` (never `date('now')`) | Task 1 (+ used in 3, 6, 7) |
| `upsert_events` firm-up-in-place + batch dedupe | Task 2 |
| `replace_forward_window` (cancellation-aware, past retained) | Task 2 |
| `write_snapshot` provenance | Task 2 |
| `v_upcoming` / `v_imminent` shared views | Task 1 (behavior tested Task 3) |
| `prune` snapshots-only, never events | Task 3 |
| `Release` dataclass + curated catalog + known-time (`release_time`) | Task 4 |
| `select_ids` only/exclude/strip/dedupe | Task 4 |
| `require_api_key` before any call, never echoes key | Task 5 |
| `fetch_all_release_dates` / `fetch_release_dates` with `include_release_dates_with_no_data=true` + `realtime_start` | Task 5 |
| `parse_release_dates` pure (catalog filter, event_time from lookup, status/source) | Task 5 |
| Bounded backoff on 429/5xx (reused) | Task 5 |
| econ `db.ensure_schema` layering `monitor_common` + 3 econ views | Task 6 |
| `v_upcoming_releases` / `v_imminent_high_impact` / `v_this_week` | Task 6 |
| `run()` orchestration, skip-and-continue, secret hygiene | Task 7 |
| CLI `--db/--only/--exclude/--horizon-days/--keep-days` | Task 7 |
| Registry dispatch `"econ_calendar"` | Task 8 |
| Reuse `FRED_API_KEY`, `.env.example` unchanged | Global Constraints / Task 5 (no new key touched) |

Every spec section maps to a task. The spec's own test list (`test_econ_calendar_fetch/catalog/db_schema/db_write/run` + registry) is covered by Tasks 4–8.

**2. Placeholder scan:** No `TBD`/`TODO`/"add error handling"/"similar to Task N" in code steps. The one open item the *spec itself* leaves unresolved (Retail Sales/PCE/JOLTS release_ids the spec marked `~99`/`tbd`) is handled as an explicit **live-verification action** in Task 4, not a code placeholder — the shipped catalog is complete and runnable with the four numbered high-confidence ids plus Retail Sales.

**3. Type consistency:** `event_time` sourced from `Release.release_time` throughout (Task 4 field → Task 5 parse → Task 6 view). `subtype` is `str(release_id)` in parse (Task 5) and in tests (Task 6/7). Event-row dict keys are identical across `upsert_events` (Task 2), `parse_release_dates` (Task 5), and every test helper. `run()` injects `fetch_one` matching `fetch_release_dates(release_id, api_key, today)` (Task 5 signature). `set_today`/`upsert_events`/`write_snapshot`/`prune` signatures are used identically in Tasks 3, 6, 7.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-03-econ-calendar-monitor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
