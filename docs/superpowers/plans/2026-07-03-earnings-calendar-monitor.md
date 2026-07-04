# Earnings Calendar Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `earnings` monitor — a forward earnings calendar for watched names (when each reports, before/after the bell) sourced from stockanalysis.com and **confirmed** by EDGAR 8-K Item 2.02 — into the shared `events` table, with four earnings views.

**Architecture:** An event-date monitor on `monitor_common` (like `fomc`/`market_calendar`). The **forward dates come from stockanalysis.com** (the approved trusted-source exception — see the standing project note; decode via the *existing* `stock_analysis_screener.probe.page_data`, do NOT write a second decoder). **Official confirmation** comes from EDGAR: an 8-K carrying Item `2.02` near a scheduled date flips it `scheduled → confirmed`, `source='edgar'` (reuse `edgar_screener.fetch`'s ticker map + bounded-backoff client). Reuses `monitor_common` (`events`/`snapshots`/`calendar_now`, `set_today`, `replace_forward_window`, `write_snapshot`, `prune`). **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `json`, `datetime`, `argparse`); `pytest`. Reuses `monitor_common`, `stock_analysis_screener.probe`, `edgar_screener.fetch`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + the existing decoders/clients. No new packages.
- **No credentials.** stockanalysis.com needs no key (approved exception); EDGAR uses the descriptive UA already in `edgar_screener`. `.env.example` unchanged.
- **Reuse, don't reimplement.** Forward decode via `stock_analysis_screener.probe.page_data`; SEC access via `edgar_screener.fetch` (`fetch_ticker_map`, `_http_get`, `_UA`, `_RETRY_STATUS`).
- **Fail loudly on forward-feed drift.** `fetch_forward` raises `EarningsFeedError` if a non-empty payload yields zero rows / a row is missing its ticker — never returns `[]` (a silent empty earnings calendar is dangerous). Whole-payload drift aborts the run; a transient network failure logs a **type-name-only** warning and preserves the last-good calendar.
- **Licensed data is internal-use only.** Never republish stockanalysis rows; they power decisions only.
- **`now_iso` injected, never wall-clock in logic.** `run()` accepts `now_iso=None`, defaulting to UTC now; `fetch_forward` and `confirm` are injected so tests are network-free.
- **`subtype` is part of the events PK and NEVER NULL** — earnings uses `subtype = ticker`.
- **Write via `replace_forward_window`** for `event_type='earnings'` — a shifted report date moves cleanly; a moved-away future date disappears; past events retained.
- **Prune NEVER touches future events** — snapshots provenance only.
- **Secret hygiene:** per-ticker EDGAR errors log **only** `type(e).__name__`, never `str(e)`/`e.url`.
- **Every writer ends with `conn.commit()`** (the `monitor_common` helpers already do).
- **Test command:** `python -m pytest` (config in `pyproject.toml`).
- **Commits:** do NOT add a co-author line (per user global instruction).

---

## File Structure

**New — `earnings_calendar/` package:**
- `earnings_calendar/__init__.py` — empty.
- `earnings_calendar/fetch.py` — `EarningsFeedError`, `fetch_forward` (decode+flatten), `timing_to_time`, `confirm_via_edgar` (+ helpers).
- `earnings_calendar/db.py` — `ensure_schema` (delegates to `monitor_common`) + 4 earnings views.
- `earnings_calendar/run.py` — `build_events` + `run` + argparse `main`.

**Modified:**
- `registry.py` — import `earnings_calendar.run.main` and register `"earnings"`.

**New tests (`tests/`):**
`test_earnings_fetch.py`, `test_earnings_db_schema.py`, `test_earnings_db_views.py`, `test_earnings_db_write.py`, `test_earnings_run.py`, and one assertion in `test_registry.py`.

### Event-row mapping (`build_events`)

| column | value |
|---|---|
| `event_type` | `'earnings'` |
| `event_date` | report date `YYYY-MM-DD` |
| `event_time` | `'before open'` / `'after close'` / `None` (from `t`) |
| `subtype` | ticker (`s`) |
| `title` | company name (`n`) |
| `status` | `'scheduled'` (→ `'confirmed'` on EDGAR match) |
| `source` | `'stockanalysis'` (→ `'edgar'` on confirmation) |
| `payload` | JSON `{eps_est, rev_est, mktcap, timing}` |

> **Live-verify (🔵):** confirm the decoded day-block shape (the fixture below assumes `{"data": [{"date", "rows": [{"s","n","t","e","r","m",…}]}]}`) and the EDGAR `filings.recent` `form`/`items`/`filingDate` arrays against one live decode/submissions call; adjust the parser + fixture together if the live shape differs. The raise-on-empty guard is the safety net.

---

## Task 1: `earnings_calendar.fetch` — forward decode + EDGAR confirm

**Files:**
- Create: `earnings_calendar/__init__.py` (empty), `earnings_calendar/fetch.py`
- Test: `tests/test_earnings_fetch.py`

**Interfaces:**
- `EarningsFeedError(Exception)`.
- `fetch_forward(get=probe.page_data) -> list[dict]` — normalized `{ticker, name, date, timing, eps_est, eps_growth, rev_est, rev_growth, mktcap}`; raises on drift.
- `timing_to_time(t) -> str | None`.
- `confirm_via_edgar(tickers, scheduled_by_ticker, get=edgar.\_http_get, tmap=edgar.fetch_ticker_map) -> set[(ticker, date)]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_earnings_fetch.py`:

```python
import json

import pytest

from earnings_calendar import fetch

# Decoded fixture shaped per the catalog: day-blocks each with a date + symbol
# rows (s/n/t/e/eg/r/rg/m). Confirm vs a live decode at implementation.
DECODED = {"data": [
    {"date": "2026-07-06", "day": "Monday", "count": 2, "rows": [
        {"s": "AAPL", "n": "Apple Inc.", "t": "amc", "e": 1.5, "eg": 10,
         "r": 9e10, "rg": 5, "m": 3e12},
        {"s": "MSFT", "n": "Microsoft Corp.", "t": "bmo", "e": 2.9, "eg": 8,
         "r": 6e10, "rg": 12, "m": 2.5e12},
    ]},
]}


def test_fetch_forward_flattens_and_normalizes():
    rows = fetch.fetch_forward(get=lambda path: DECODED)
    assert len(rows) == 2
    aapl = next(r for r in rows if r["ticker"] == "AAPL")
    assert aapl["date"] == "2026-07-06" and aapl["timing"] == "amc"
    assert aapl["name"] == "Apple Inc." and aapl["mktcap"] == 3e12
    assert aapl["eps_est"] == 1.5


def test_fetch_forward_raises_on_zero_rows_from_nonempty():
    with pytest.raises(fetch.EarningsFeedError):
        fetch.fetch_forward(get=lambda path: {"data": [{"date": "2026-07-06",
                                                        "rows": []}]})


def test_timing_to_time_mapping():
    assert fetch.timing_to_time("bmo") == "before open"
    assert fetch.timing_to_time("amc") == "after close"
    assert fetch.timing_to_time("") is None


def test_confirm_via_edgar_matches_item_202_near_date():
    subs = {"filings": {"recent": {
        "form": ["8-K", "10-Q", "8-K"],
        "items": ["2.02,9.01", "", "5.02"],       # only the first is earnings
        "filingDate": ["2026-07-07", "2026-05-01", "2026-06-01"],
    }}}

    def get(url):
        return json.dumps(subs)

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    confirmed = fetch.confirm_via_edgar(
        ["AAPL"], {"AAPL": ["2026-07-06"]}, get=get, tmap=tmap)
    assert ("AAPL", "2026-07-06") in confirmed     # 8-K 2.02 filed 07-07 (±3d)


def test_confirm_skips_unmapped_ticker_and_non_202():
    subs = {"filings": {"recent": {"form": ["8-K"], "items": ["5.02"],
                                   "filingDate": ["2026-07-07"]}}}

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    # MSFT unmapped -> skipped; AAPL has no 2.02 near date -> not confirmed
    confirmed = fetch.confirm_via_edgar(
        ["AAPL", "MSFT"], {"AAPL": ["2026-07-06"], "MSFT": ["2026-07-06"]},
        get=lambda url: json.dumps(subs), tmap=tmap)
    assert confirmed == set()


def test_confirm_per_ticker_error_is_skipped_not_fatal(capsys):
    def get(url):
        raise RuntimeError("https://data.sec.gov?x=SECRET boom")

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    confirmed = fetch.confirm_via_edgar(
        ["AAPL"], {"AAPL": ["2026-07-06"]}, get=get, tmap=tmap)
    assert confirmed == set()
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `earnings_calendar/__init__.py` (empty).

Create `earnings_calendar/fetch.py`:

```python
"""Forward earnings feed (stockanalysis.com, approved trusted exception) + EDGAR
8-K Item 2.02 confirmation.

Forward dates are decoded via the EXISTING stock_analysis_screener.probe decoder
(do not write a second devalue decoder). EDGAR only *confirms* a date after the
filing posts — it is never the forward source. Licensed data is internal-use only."""
import json
import sys
from datetime import date

from edgar_screener import fetch as _edgar
from stock_analysis_screener import probe

EARNINGS_ROUTE = "/stocks/earnings-calendar/"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

__all__ = ["EarningsFeedError", "fetch_forward", "timing_to_time",
           "confirm_via_edgar"]


class EarningsFeedError(Exception):
    """Raised when the forward feed yields zero rows from a non-empty payload."""


def _day_blocks(payload):
    if isinstance(payload, dict):
        return payload.get("data") or []
    if isinstance(payload, list):
        return payload
    return []


def _norm_date(v):
    return (v or "")[:10] or None


def fetch_forward(get=probe.page_data) -> list:
    """Decode the earnings-calendar payload and flatten day-blocks into normalized
    rows. `get(route)` returns the decoded page data (injected in tests). Fails
    loudly on drift."""
    payload = get(EARNINGS_ROUTE)
    rows = []
    for block in _day_blocks(payload):
        d = _norm_date(block.get("date"))
        for sym in block.get("rows", []):
            ticker = sym.get("s")
            if not ticker or not d:
                continue
            rows.append({
                "ticker": ticker, "name": sym.get("n"), "date": d,
                "timing": sym.get("t"), "eps_est": sym.get("e"),
                "eps_growth": sym.get("eg"), "rev_est": sym.get("r"),
                "rev_growth": sym.get("rg"), "mktcap": sym.get("m"),
            })
    if payload and not rows:
        raise EarningsFeedError(
            "no earnings rows decoded from non-empty payload (schema drift?)")
    return rows


def timing_to_time(t):
    """Map the stockanalysis timing code to a human event_time."""
    return {"bmo": "before open", "amc": "after close"}.get(t)


def _item_202_dates(payload) -> list:
    """Filing dates of 8-Ks carrying Item 2.02 (earnings) from a submissions
    payload's filings.recent parallel arrays."""
    recent = (payload.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    items = recent.get("items") or []
    dates = recent.get("filingDate") or []
    out = []
    for i, form in enumerate(forms):
        item = items[i] if i < len(items) else ""
        if form == "8-K" and "2.02" in (item or ""):
            if i < len(dates):
                out.append(dates[i])
    return out


def _near(scheduled, dates, window=3) -> bool:
    """True if any filing date is within +/-window days of the scheduled date."""
    try:
        s = date.fromisoformat(scheduled)
    except ValueError:
        return False
    for d in dates:
        try:
            if abs((date.fromisoformat(str(d)[:10]) - s).days) <= window:
                return True
        except ValueError:
            continue
    return False


def confirm_via_edgar(tickers, scheduled_by_ticker, get=_edgar._http_get,
                      tmap=_edgar.fetch_ticker_map) -> set:
    """For each watched ticker, resolve its CIK and look for an 8-K Item 2.02
    near a scheduled date -> confirm that (ticker, date). Per-ticker failures are
    skipped (type-name-only log); an unmapped ticker is skipped. Returns the set
    of confirmed (ticker, date) pairs."""
    cik_by_ticker = {v["ticker"]: k for k, v in tmap().items()}
    confirmed = set()
    for ticker in tickers:
        cik = cik_by_ticker.get(ticker)
        if cik is None:
            continue
        try:
            payload = json.loads(get(SUBMISSIONS_URL.format(cik=cik)))
        except Exception as e:  # skip-and-continue; never echo str(e)/url
            print(f"warning: EDGAR confirm {ticker}: {type(e).__name__}",
                  file=sys.stderr)
            continue
        filed = _item_202_dates(payload)
        for scheduled in scheduled_by_ticker.get(ticker, []):
            if _near(scheduled, filed):
                confirmed.add((ticker, scheduled))
    return confirmed
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add earnings_calendar/__init__.py earnings_calendar/fetch.py tests/test_earnings_fetch.py
git commit -m "feat(earnings): stockanalysis forward decode (reuses probe) + EDGAR Item-2.02 confirm"
```

---

## Task 2: `earnings_calendar.db` — schema delegation + earnings views

**Files:**
- Create: `earnings_calendar/db.py`
- Test: `tests/test_earnings_db_schema.py`, `tests/test_earnings_db_views.py`

**Interfaces:**
- `connect` — re-export from `monitor_common`.
- `ensure_schema(conn)` — `monitor_common.ensure_schema` + `v_upcoming_earnings`, `v_imminent_earnings`, `v_this_week_earnings`, `v_earnings_confirmed`. Idempotent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_earnings_db_schema.py`:

```python
from earnings_calendar import db


def test_ensure_schema_creates_tables_and_four_earnings_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "calendar_now"} <= tables
    assert {"v_upcoming_earnings", "v_imminent_earnings",
            "v_this_week_earnings", "v_earnings_confirmed"} <= views


def test_ensure_schema_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)   # must not raise
```

Create `tests/test_earnings_db_views.py`:

```python
import json

import monitor_common
from earnings_calendar import db


def _fresh(now, horizon=7):
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    monitor_common.set_today(conn, now, horizon)
    return conn


def _evt(ticker, event_date, status="scheduled", source="stockanalysis",
         mktcap=1e9, timing="amc"):
    return {"event_type": "earnings", "event_date": event_date,
            "event_time": "after close", "subtype": ticker, "title": ticker,
            "status": status, "source": source,
            "payload": json.dumps({"mktcap": mktcap, "timing": timing})}


def test_v_upcoming_earnings_filters_future_orders_by_date_then_mktcap():
    conn = _fresh("2026-07-06T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("OLD", "2026-06-01"),                       # past -> out
        _evt("SM", "2026-07-08", mktcap=1e9),
        _evt("BIG", "2026-07-08", mktcap=9e11),          # same day, bigger first
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_upcoming_earnings")]
    assert rows == ["BIG", "SM"]


def test_v_imminent_earnings_respects_horizon():
    conn = _fresh("2026-07-06T00:00:00+00:00", horizon=7)
    monitor_common.upsert_events(conn, [
        _evt("A", "2026-07-09"),      # in
        _evt("B", "2026-07-20"),      # out (14 days)
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_imminent_earnings")]
    assert rows == ["A"]


def test_v_this_week_earnings_mon_to_fri():
    conn = _fresh("2026-07-06T00:00:00+00:00")   # Monday
    monitor_common.upsert_events(conn, [
        _evt("MON", "2026-07-06"), _evt("FRI", "2026-07-10"),
        _evt("NEXTMON", "2026-07-13"),          # next week -> out
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_this_week_earnings")]
    assert rows == ["MON", "FRI"]


def test_v_earnings_confirmed_only_edgar_verified():
    conn = _fresh("2026-07-06T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("A", "2026-07-08", status="scheduled", source="stockanalysis"),
        _evt("B", "2026-07-09", status="confirmed", source="edgar"),
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_earnings_confirmed")]
    assert rows == ["B"]
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `earnings_calendar/db.py`:

```python
"""earnings_calendar store: the shared monitor schema plus four earnings views.
The events/snapshots/calendar_now DDL lives in monitor_common; this only adds
views. Scope is by ingest (--only watchlist), so the views need no watchlist
table — they filter event_type='earnings' against the injected :today."""
from monitor_common import connect
from monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema"]

_EARNINGS_VIEWS = """
-- All upcoming earnings, biggest names first within a day.
CREATE VIEW IF NOT EXISTS v_upcoming_earnings AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status,
       e.source, json_extract(e.payload, '$.mktcap') AS mktcap,
       json_extract(e.payload, '$.eps_est') AS eps_est
FROM events e, calendar_now p
WHERE e.event_type = 'earnings' AND e.event_date >= p.today
ORDER BY e.event_date, json_extract(e.payload, '$.mktcap') DESC;

-- Reporting within the horizon window (drives sizing / IV-crush decisions).
CREATE VIEW IF NOT EXISTS v_imminent_earnings AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status
FROM events e, calendar_now p
WHERE e.event_type = 'earnings'
  AND e.event_date BETWEEN p.today
      AND date(p.today, '+' || p.horizon_days || ' days')
ORDER BY e.event_date;

-- Current Mon-Fri week ("who prints this week").
CREATE VIEW IF NOT EXISTS v_this_week_earnings AS
WITH wk AS (
    SELECT date(today, '-' ||
               ((CAST(strftime('%w', today) AS INTEGER) + 6) % 7) || ' days')
           AS mon
    FROM calendar_now
)
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status
FROM events e, wk
WHERE e.event_type = 'earnings'
  AND e.event_date >= wk.mon AND e.event_date <= date(wk.mon, '+4 days')
ORDER BY e.event_date;

-- EDGAR-verified subset: a firm print vs an aggregator estimate.
CREATE VIEW IF NOT EXISTS v_earnings_confirmed AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status,
       e.source
FROM events e
WHERE e.event_type = 'earnings'
  AND e.status IN ('confirmed', 'released') AND e.source = 'edgar'
ORDER BY e.event_date;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + earnings views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_EARNINGS_VIEWS)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (2 + 4 tests).

- [ ] **Step 5: Commit**

```bash
git add earnings_calendar/db.py tests/test_earnings_db_schema.py tests/test_earnings_db_views.py
git commit -m "feat(earnings): schema delegation + upcoming/imminent/this-week/confirmed views"
```

---

## Task 3: `earnings_calendar.run` — build_events + orchestration + CLI

**Files:**
- Create: `earnings_calendar/run.py`
- Test: `tests/test_earnings_db_write.py`, `tests/test_earnings_run.py`

**Interfaces:**
- `build_events(rows, now_iso) -> list[dict]`.
- `run(db_path, horizon_days=None, keep_days=None, only=None, fetch_forward=fetch.fetch_forward, confirm=fetch.confirm_via_edgar, now_iso=None) -> (snapshot_id, event_count)`.
- `main(argv=None)` — argparse, `prog="earnings"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_earnings_db_write.py`:

```python
import json

from earnings_calendar import run as runmod

NOW = "2026-07-06T00:00:00+00:00"


def _row(ticker, date, timing="amc", name="X"):
    return {"ticker": ticker, "name": name, "date": date, "timing": timing,
            "eps_est": 1.0, "eps_growth": None, "rev_est": 2.0, "rev_growth": None,
            "mktcap": 5e9}


def test_build_events_maps_subtype_time_and_payload():
    ev = runmod.build_events([_row("AAPL", "2026-07-08", "bmo")], NOW)[0]
    assert ev["event_type"] == "earnings" and ev["subtype"] == "AAPL"
    assert ev["event_date"] == "2026-07-08"
    assert ev["event_time"] == "before open"
    assert ev["status"] == "scheduled" and ev["source"] == "stockanalysis"
    assert json.loads(ev["payload"])["eps_est"] == 1.0


def test_run_shifted_date_updates_in_place_no_duplicate(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("AAPL", "2026-07-08")],
               now_iso=NOW)
    runmod.run(db_path, fetch_forward=lambda: [_row("AAPL", "2026-07-09")],
               now_iso=NOW)                       # date moved
    conn = sqlite3.connect(db_path)
    dates = [r[0] for r in conn.execute(
        "SELECT event_date FROM events WHERE subtype='AAPL'")]
    assert dates == ["2026-07-09"]                # old future date replaced


def test_run_edgar_confirm_flips_status_and_source(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "e.db")

    def confirm(tickers, scheduled_by_ticker, **kw):
        return {("AAPL", "2026-07-08")}

    runmod.run(db_path, only=["AAPL"],
               fetch_forward=lambda: [_row("AAPL", "2026-07-08")],
               confirm=confirm, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status, source FROM events WHERE subtype='AAPL'").fetchone()
    assert row == ("confirmed", "edgar")
```

Create `tests/test_earnings_run.py`:

```python
import sqlite3

from earnings_calendar import run as runmod

NOW = "2026-07-06T00:00:00+00:00"


def _row(ticker, date):
    return {"ticker": ticker, "name": ticker, "date": date, "timing": "amc",
            "eps_est": None, "eps_growth": None, "rev_est": None,
            "rev_growth": None, "mktcap": 1e9}


def test_run_end_to_end_counts_and_snapshots(tmp_path):
    db_path = str(tmp_path / "e.db")
    sid, count = runmod.run(
        db_path, fetch_forward=lambda: [_row("A", "2026-07-08"),
                                        _row("B", "2026-07-09")], now_iso=NOW)
    assert count == 2
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_only_filters_to_watchlist(tmp_path):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, only=["A"],
               fetch_forward=lambda: [_row("A", "2026-07-08"),
                                      _row("B", "2026-07-09")],
               confirm=lambda *a, **k: set(), now_iso=NOW)
    conn = sqlite3.connect(db_path)
    tickers = {r[0] for r in conn.execute("SELECT subtype FROM events")}
    assert tickers == {"A"}


def test_run_transient_feed_failure_preserves_calendar_hides_secret(
        tmp_path, capsys):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso=NOW)

    def boom():
        raise RuntimeError("https://stockanalysis?k=SECRET boom")

    runmod.run(db_path, fetch_forward=boom, now_iso=NOW)
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_keep_days_prunes_snapshots_not_events(tmp_path):
    db_path = str(tmp_path / "e.db")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, fetch_forward=lambda: [_row("A", "2026-07-08")],
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `earnings_calendar/run.py`:

```python
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone

import monitor_common
from earnings_calendar import db, fetch


def build_events(rows, now_iso) -> list:
    """Map normalized forward rows to earnings events (subtype=ticker)."""
    out = []
    for r in rows:
        out.append({
            "event_type": "earnings", "event_date": r["date"],
            "event_time": fetch.timing_to_time(r.get("timing")),
            "subtype": r["ticker"], "title": r.get("name"),
            "status": "scheduled", "source": "stockanalysis",
            "payload": json.dumps({"eps_est": r.get("eps_est"),
                                   "rev_est": r.get("rev_est"),
                                   "mktcap": r.get("mktcap"),
                                   "timing": r.get("timing")}),
        })
    return out


def run(db_path, horizon_days=None, keep_days=None, only=None,
        fetch_forward=fetch.fetch_forward, confirm=fetch.confirm_via_edgar,
        now_iso=None):
    """Decode the forward earnings feed, replace the forward window, optionally
    confirm watched tickers via EDGAR, snapshot, and optionally prune. Returns
    (snapshot_id, event_count). Feed drift aborts loudly; a transient feed
    failure preserves the last-good calendar."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()
    watch = {t.strip().upper() for t in only} if only else None

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days or 7)

        try:
            rows = fetch_forward()
        except fetch.EarningsFeedError:
            raise                                   # abort loudly on schema drift
        except Exception as e:                      # transient: keep last-good
            print(f"warning: earnings feed failed: {type(e).__name__}",
                  file=sys.stderr)
            rows = None

        if rows is not None:
            if watch is not None:
                rows = [r for r in rows if r["ticker"].upper() in watch]
            if horizon_days is not None:
                cutoff = (date.fromisoformat(today)
                          + timedelta(days=horizon_days)).isoformat()
                rows = [r for r in rows if r["date"] <= cutoff]
            events = build_events(rows, now_iso)
            monitor_common.replace_forward_window(conn, "earnings", today,
                                                  events, now_iso)

            if watch is not None and rows:
                scheduled_by_ticker = {}
                for r in rows:
                    scheduled_by_ticker.setdefault(r["ticker"], []).append(
                        r["date"])
                try:
                    confirmed = confirm(list(scheduled_by_ticker),
                                        scheduled_by_ticker)
                except Exception as e:
                    print(f"warning: earnings confirm failed: "
                          f"{type(e).__name__}", file=sys.stderr)
                    confirmed = set()
                for ticker, when in confirmed:
                    conn.execute(
                        "UPDATE events SET status='confirmed', source='edgar' "
                        "WHERE event_type='earnings' AND subtype=? "
                        "AND event_date=?", (ticker, when))
                conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='earnings' "
            "AND event_date >= ?", (today,)).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "stockanalysis")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="earnings",
        description="Pull the forward earnings calendar (stockanalysis + EDGAR confirm)")
    p.add_argument("--db", default="earnings.db")
    p.add_argument("--horizon-days", type=int, default=None,
                   help="cap how far forward to store")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    p.add_argument("--only", nargs="+", default=None,
                   help="restrict to these tickers (default: the watchlist)")
    a = p.parse_args(argv)
    _, count = run(a.db, horizon_days=a.horizon_days, keep_days=a.keep_days,
                   only=a.only)
    print(f"stored {count} forward earnings events into {a.db}")


if __name__ == "__main__":
    main()
```

> **EDGAR confirm runs only with `--only`:** confirmation is scoped to watched CIKs (a handful of ≤10 req/s calls). Without a watchlist there's nothing to confirm against the whole market, so the confirm pass is skipped. `replace_forward_window` resets future rows to `scheduled` each run and the confirm pass re-flips matched ones — idempotent.

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (3 + 4 tests).

- [ ] **Step 5: Commit**

```bash
git add earnings_calendar/run.py tests/test_earnings_db_write.py tests/test_earnings_run.py
git commit -m "feat(earnings): build_events + run (replace-forward, EDGAR confirm, transient-safe) + CLI"
```

---

## Task 4: Register `earnings` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_earnings():
    import registry
    assert "earnings" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails** — `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import and register (after the other monitors, e.g. `"fomc"`):

```python
from earnings_calendar.run import main as earnings_main
```
```python
    "earnings": earnings_main,
```

- [ ] **Step 4: Run test to verify it passes** — `python -m pytest tests/test_registry.py -v`.

- [ ] **Step 5: Run the FULL suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(earnings): register earnings dispatcher"
```

---

## Task 5: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `earnings` to Built**

- Add an `earnings` row to the **Built ✅** table (link this plan + the spec).
- Remove the `earnings` row from **Spec'd — event-date monitors 📝** (the table is now empty — note that, or leave a "nothing pending" line).
- In **Recommended build order**, strike through item 8 (`earnings`) as ✅ Built, mirroring items 1–7. Note that this completes the ranked build order; the remaining `ats`/`nyfed`/`cboe_stats`/`eia`/`usda` are the lower-priority tail. Note the deferred cadence-based estimation (EDGAR historical Item-2.02 spacing) as a follow-up.

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark earnings Built; ranked build order complete"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| `fetch_forward` via existing `probe.page_data`, flatten day-blocks, fail loudly | Task 1 |
| `timing_to_time` (bmo/amc/other) | Task 1 |
| `confirm_via_edgar` — CIK resolve, 8-K Item 2.02 near date, skip unmapped/errors | Task 1 |
| `db.ensure_schema` delegates to `monitor_common` + 4 earnings views | Task 2 |
| `v_upcoming_earnings` / `v_imminent_earnings` / `v_this_week_earnings` / `v_earnings_confirmed` | Task 2 |
| `build_events` (subtype=ticker, event_time from timing, payload JSON) | Task 3 |
| `run` replace-forward, `--only` watchlist scope, EDGAR confirm flips status/source | Task 3 |
| Transient feed failure preserves calendar; drift aborts; secret hygiene | Task 3 |
| CLI `--db/--horizon-days/--keep-days/--only` | Task 3 |
| Registry `"earnings"` | Task 4 |
| No credentials; `.env.example` unchanged; `now_iso` injected; licensed data internal-only | Global Constraints |

**2. Placeholder scan:** No `TODO` in code. The cadence-based *estimation* (job b — projecting a next date from EDGAR Item-2.02 spacing when the forward feed lacks a name) is a documented follow-up surfaced in the roadmap entry; v1 ships the forward feed + EDGAR *confirmation* (job a) fully. The decoded-shape assumption is flagged for live confirmation with the raise-on-empty guard as the safety net.

**3. Type consistency:** The normalized forward-row keys (`ticker, name, date, timing, eps_est, eps_growth, rev_est, rev_growth, mktcap`) flow from `fetch_forward` (Task 1) into `build_events` (Task 3) identically. Event-row dict keys match `monitor_common` and every test helper. `payload` is always a JSON string so the views' `json_extract` works. `confirm_via_edgar` returns a `set[(ticker, date)]` consumed identically in `run` and the tests. `subtype` is always the ticker — never NULL.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-earnings-calendar-monitor.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
