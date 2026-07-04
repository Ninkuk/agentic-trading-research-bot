# FOMC Calendar Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `fomc` monitor — a forward-looking macro-event feed of FOMC **meetings**, computed **minutes** (+21d), **communication blackout** windows, and **SEP / dot-plot** meetings — into the shared `events` table, with three FOMC views (`v_next_fomc`, `v_in_blackout`, `v_upcoming_fomc_events`).

**Architecture:** An event-date monitor in the mould of `market_calendar` / `econ_calendar`. Only **meeting dates are parsed** (the one fragile function, isolated in `fetch.py`, raising `FomcCalendarParseError` on schema drift); everything else is **pure computation** from each meeting's start/end. It reuses the built `monitor_common` framework (`events`/`snapshots`/`calendar_now` schema, `set_today`, `replace_forward_window`, `write_snapshot`, `prune`, `v_upcoming`/`v_imminent`) and the `http_client` bounded-backoff. **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `re`, `json`, `datetime`, `argparse`); `pytest`. Reuses `monitor_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** A single public HTML GET with the descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`); `.env.example` unchanged.
- **Fail loudly on whole-page drift.** `parse_calendar` raises `FomcCalendarParseError` if non-empty HTML yields zero meetings — never returns `[]` (a silent empty calendar is the dangerous failure). A `FomcCalendarParseError` aborts the run loudly. A *transient* fetch/network failure logs a **type-name-only** warning and **preserves the last-good calendar** (no replace-forward).
- **`now_iso` injected, never wall-clock in logic.** `run()` accepts `now_iso=None`, defaulting to UTC now; `fetch_calendar` is injected so tests are network-free.
- **`subtype` is part of the events PK and NEVER NULL.** The meeting row uses `''`; every derived event uses the **parent meeting's decision date** as `subtype` (pins minutes/SEP/blackout to their meeting; keeps the UPSERT idempotent).
- **Write via `replace_forward_window` per `event_type`** — a firmed status updates in place; a cancelled/rescheduled future meeting disappears; past events (`event_date < today`) are never touched.
- **Prune NEVER touches future events** — snapshots provenance only.
- **Secret hygiene:** per-item / fetch errors log **only** `type(e).__name__`, never `str(e)`/`e.url`.
- **Every writer ends with `conn.commit()`** (the `monitor_common` helpers already do).
- **Test command:** `python -m pytest` (config in `pyproject.toml`).
- **Commits:** do NOT add a co-author line (per user global instruction).

---

## File Structure

**New — `fomc_calendar/` package:**
- `fomc_calendar/__init__.py` — empty.
- `fomc_calendar/fetch.py` — `FomcCalendarParseError`, `parse_calendar` (the fragile parser), `fetch_calendar`, pure derivations `minutes_date`/`blackout_window`/`is_sep_meeting`.
- `fomc_calendar/db.py` — `ensure_schema` (delegates to `monitor_common`) + the 3 FOMC views.
- `fomc_calendar/run.py` — `build_events` + `run` + argparse `main`.

**Modified:**
- `registry.py` — import `fomc_calendar.run.main` and register `"fomc"`.

**New tests (`tests/`):**
`test_fomc_fetch.py`, `test_fomc_db_schema.py`, `test_fomc_db_views.py`, `test_fomc_db_write.py`, `test_fomc_run.py`, and one assertion in `test_registry.py`.

### Event-row vocabulary (produced by `build_events`, consumed by `monitor_common`)

Dict keys: `event_type, event_date, event_time, subtype, title, status, source, payload` (`payload` is a JSON string).

| `event_type` | `event_date` | `event_time` | `subtype` | payload |
|---|---|---|---|---|
| `fomc_meeting` | decision day (end) | `14:00` | `''` | `{start, end, has_press_conference, has_sep}` |
| `fomc_sep` | decision day | `14:00` | decision day | `{}` (only Mar/Jun/Sep/Dec) |
| `fomc_minutes` | end + 21d | `14:00` | decision day | `{}` |
| `fomc_blackout_start` | 2nd Sat before start | `None` | decision day | `{window_end}` |
| `fomc_blackout_end` | end + 1d | `None` | decision day | `{window_start}` |

`status` starts `tentative`, becomes `confirmed` when the parsed marker firms; `source='federalreserve'`.

---

## Task 1: `fomc_calendar.fetch` — parser + pure derivations

**Files:**
- Create: `fomc_calendar/__init__.py` (empty), `fomc_calendar/fetch.py`
- Test: `tests/test_fomc_fetch.py`

**Interfaces:**
- `FomcCalendarParseError(Exception)`.
- `parse_calendar(html) -> list[dict]` — `{start_date, end_date, status, has_press_conference}` per meeting; raises on zero-from-nonempty.
- `fetch_calendar(get=_http_get) -> list[dict]`.
- `minutes_date(end_date) -> str` — `+21d`.
- `blackout_window(start_date, end_date) -> (start_iso, end_iso)`.
- `is_sep_meeting(decision_date) -> bool` — month ∈ {3,6,9,12}.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fomc_fetch.py`:

```python
import pytest

from fomc_calendar import fetch

# Fixture shaped like the real page: per-year panels ("YYYY FOMC Meetings"),
# each meeting a __month + __date block. '*' on the date = press conference;
# "(tentative)" in the year heading = tentative year. Confirm/adjust the regex
# against the live markup at implementation — the raise-on-zero guard is the net.
_HTML = """
<div class="panel"><div class="panel-heading">2026 FOMC Meetings</div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">January</div>
    <div class="fomc-meeting__date">27-28*</div></div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">April/May</div>
    <div class="fomc-meeting__date">28-1</div></div>
</div>
<div class="panel"><div class="panel-heading">2027 FOMC Meetings (tentative)</div>
  <div class="fomc-meeting"><div class="fomc-meeting__month">January</div>
    <div class="fomc-meeting__date">26-27</div></div>
</div>
"""


def test_parse_calendar_extracts_meetings_and_dates():
    meetings = fetch.parse_calendar(_HTML)
    assert len(meetings) == 3
    jan = meetings[0]
    assert jan["start_date"] == "2026-01-27" and jan["end_date"] == "2026-01-28"
    assert jan["status"] == "confirmed"
    assert jan["has_press_conference"] is True


def test_parse_calendar_handles_cross_month_range():
    meetings = fetch.parse_calendar(_HTML)
    apr = meetings[1]
    assert apr["start_date"] == "2026-04-28" and apr["end_date"] == "2026-05-01"
    assert apr["has_press_conference"] is False


def test_parse_calendar_marks_tentative_year():
    meetings = fetch.parse_calendar(_HTML)
    assert meetings[2]["status"] == "tentative"       # 2027 panel


def test_parse_calendar_raises_on_zero_from_nonempty():
    with pytest.raises(fetch.FomcCalendarParseError):
        fetch.parse_calendar("<html><body>no meetings here</body></html>")


def test_minutes_date_is_end_plus_21_days():
    assert fetch.minutes_date("2026-01-28") == "2026-02-18"


def test_blackout_window_second_saturday_before_and_end_plus_one():
    # Jan 27-28 2026 (start is a Tuesday): nearest preceding Saturday = Jan 24,
    # second preceding = Jan 17; blackout ends end+1 = Jan 29.
    start, end = fetch.blackout_window("2026-01-27", "2026-01-28")
    assert start == "2026-01-17"
    assert end == "2026-01-29"


def test_blackout_window_when_start_is_saturday_walks_back_a_full_week():
    # If the meeting start is itself a Saturday, "preceding Saturday" is strictly
    # before it (a week back), then one more week => 14 days before.
    start, _ = fetch.blackout_window("2026-01-17", "2026-01-18")  # Jan 17 = Sat
    assert start == "2026-01-03"


def test_is_sep_meeting_true_only_for_quarter_months():
    assert fetch.is_sep_meeting("2026-03-18") is True
    assert fetch.is_sep_meeting("2026-06-17") is True
    assert fetch.is_sep_meeting("2026-01-28") is False
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `fomc_calendar/__init__.py` (empty).

Create `fomc_calendar/fetch.py`:

```python
"""FOMC calendar fetch + the one fragile HTML parser, isolated here.

Only meeting dates are parsed; minutes/blackout/SEP are computed elsewhere. The
parser fails loudly (FomcCalendarParseError) rather than emit an empty calendar —
a silent 'no meetings coming' is the dangerous failure mode for a macro monitor."""
import re
from datetime import date, timedelta

from http_client import http_get, make_opener

CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({403, 429, 503})

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

_YEAR = re.compile(r"(\d{4})\s+FOMC\s+Meetings([^<]*)", re.IGNORECASE)
# month (opt /second-month) ... date "d-d" (opt trailing '*') — confirm vs live markup.
_MEETING = re.compile(
    r"fomc-meeting__month[^>]*>\s*([A-Za-z]+)(?:\s*/\s*([A-Za-z]+))?\s*<"
    r"[\s\S]*?fomc-meeting__date[^>]*>\s*(\d+)\s*-\s*(\d+)\s*(\*?)",
    re.IGNORECASE)


class FomcCalendarParseError(Exception):
    """Raised when the FOMC page yields zero meetings from non-empty HTML."""


def _norm_date(year: int, month_name: str, day: str) -> str:
    mo = _MONTHS[month_name.strip().lower()[:3]]
    return date(int(year), mo, int(day)).isoformat()


def parse_calendar(html: str) -> list:
    """Extract meetings from the FOMC calendars page. Raises on drift."""
    if not html or not html.strip():
        raise FomcCalendarParseError("empty FOMC calendar HTML")
    meetings = []
    # split into per-year panels (chunk starts at each 'YYYY FOMC Meetings')
    for chunk in re.split(r"(?=\d{4}\s+FOMC\s+Meetings)", html):
        ym = _YEAR.search(chunk)
        if not ym:
            continue
        year, heading = int(ym.group(1)), ym.group(2)
        tentative = "tentative" in heading.lower()
        for m1, m2, d1, d2, star in _MEETING.findall(chunk):
            start = _norm_date(year, m1, d1)
            end = _norm_date(year, m2 or m1, d2)
            meetings.append({
                "start_date": start, "end_date": end,
                "status": "tentative" if tentative else "confirmed",
                "has_press_conference": bool(star),
            })
    if not meetings:
        raise FomcCalendarParseError(
            "no meetings parsed from non-empty HTML (page structure changed?)")
    return meetings


_urlopen = make_opener(_UA)


def _http_get(url: str) -> str:
    return http_get(url, _urlopen, _RETRY_STATUS)


def fetch_calendar(get=_http_get) -> list:
    """GET the FOMC calendars page and parse it."""
    return parse_calendar(get(CALENDAR_URL))


def minutes_date(end_date: str) -> str:
    """Minutes release = meeting end + 3 weeks (21 days)."""
    return (date.fromisoformat(end_date) + timedelta(days=21)).isoformat()


def blackout_window(start_date: str, end_date: str):
    """(blackout_start, blackout_end): the second Saturday preceding the meeting
    start, and the day after the meeting end. Saturday is weekday 5."""
    start = date.fromisoformat(start_date)
    days_back = (start.weekday() - 5) % 7 or 7    # strictly-preceding Saturday
    first_sat = start - timedelta(days=days_back)
    blackout_start = first_sat - timedelta(days=7)
    blackout_end = date.fromisoformat(end_date) + timedelta(days=1)
    return blackout_start.isoformat(), blackout_end.isoformat()


def is_sep_meeting(decision_date: str) -> bool:
    """SEP / dot-plot meetings are roughly quarterly: Mar/Jun/Sep/Dec."""
    return date.fromisoformat(decision_date).month in {3, 6, 9, 12}
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (8 tests). If a date/weekday assertion fails, check `_norm_date`/`blackout_window` against the documented rule (do not change the expected values without recomputing).

- [ ] **Step 5: Commit**

```bash
git add fomc_calendar/__init__.py fomc_calendar/fetch.py tests/test_fomc_fetch.py
git commit -m "feat(fomc): isolated FOMC HTML parser (fails loudly) + minutes/blackout/SEP derivations"
```

---

## Task 2: `fomc_calendar.db` — schema delegation + FOMC views

**Files:**
- Create: `fomc_calendar/db.py`
- Test: `tests/test_fomc_db_schema.py`, `tests/test_fomc_db_views.py`

**Interfaces:**
- `connect` — re-export from `monitor_common`.
- `ensure_schema(conn)` — `monitor_common.ensure_schema` + `v_next_fomc`, `v_in_blackout`, `v_upcoming_fomc_events`. Idempotent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fomc_db_schema.py`:

```python
from fomc_calendar import db


def test_ensure_schema_creates_shared_tables_and_fomc_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "calendar_now"} <= tables
    assert {"v_next_fomc", "v_in_blackout", "v_upcoming_fomc_events"} <= views


def test_ensure_schema_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)   # must not raise
```

Create `tests/test_fomc_db_views.py`:

```python
import json

import monitor_common
from fomc_calendar import db


def _fresh(now):
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    monitor_common.set_today(conn, now)
    return conn


def _evt(event_type, event_date, subtype="", event_time="14:00",
         status="confirmed", payload=None):
    return {"event_type": event_type, "event_date": event_date,
            "event_time": event_time, "subtype": subtype, "title": "T",
            "status": status, "source": "federalreserve",
            "payload": json.dumps(payload or {})}


def test_v_next_fomc_picks_next_meeting_with_days_until_and_has_sep():
    conn = _fresh("2026-03-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("fomc_meeting", "2026-01-28", payload={"has_sep": False}),  # past
        _evt("fomc_meeting", "2026-03-18", payload={"has_sep": True}),   # next
    ], "t")
    row = conn.execute(
        "SELECT event_date, days_until, has_sep FROM v_next_fomc").fetchone()
    assert row[0] == "2026-03-18"
    assert row[1] == 17                     # 2026-03-18 minus 2026-03-01
    assert row[2] in (1, True)              # json true -> 1


def test_v_in_blackout_true_inside_window_false_outside():
    conn = _fresh("2026-03-14T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("fomc_blackout_start", "2026-03-07", subtype="2026-03-18",
             event_time=None, payload={"window_end": "2026-03-19"}),
    ], "t")
    assert conn.execute("SELECT in_blackout FROM v_in_blackout").fetchone()[0] == 1
    monitor_common.set_today(conn, "2026-03-25T00:00:00+00:00")   # after window
    assert conn.execute("SELECT in_blackout FROM v_in_blackout").fetchone()[0] == 0


def test_v_upcoming_fomc_events_orders_and_labels():
    conn = _fresh("2026-03-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("fomc_minutes", "2026-04-08", subtype="2026-03-18"),
        _evt("fomc_meeting", "2026-03-18"),
    ], "t")
    rows = conn.execute(
        "SELECT event_type, label FROM v_upcoming_fomc_events").fetchall()
    assert rows[0][0] == "fomc_meeting"          # earliest first
    assert "Decision" in rows[0][1] or "Meeting" in rows[0][1]
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `fomc_calendar/db.py`:

```python
"""fomc_calendar store: the shared monitor schema plus three FOMC views. The
events/snapshots/calendar_now DDL lives in monitor_common; this only adds views."""
from monitor_common import connect
from monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema"]

_FOMC_VIEWS = """
-- The single next rate decision, with days_until and the dot-plot flag.
CREATE VIEW IF NOT EXISTS v_next_fomc AS
SELECT e.event_date, e.event_time, e.status,
       CAST(julianday(e.event_date) - julianday(p.today) AS INTEGER) AS days_until,
       json_extract(e.payload, '$.has_sep') AS has_sep
FROM events e, calendar_now p
WHERE e.event_type = 'fomc_meeting' AND e.event_date >= p.today
ORDER BY e.event_date
LIMIT 1;

-- Boolean helper other modules query: is today inside a blackout window?
CREATE VIEW IF NOT EXISTS v_in_blackout AS
SELECT EXISTS(
    SELECT 1 FROM events e, calendar_now p
    WHERE e.event_type = 'fomc_blackout_start'
      AND e.event_date <= p.today
      AND json_extract(e.payload, '$.window_end') >= p.today
) AS in_blackout;

-- The full forward FOMC agenda with a human label per event type.
CREATE VIEW IF NOT EXISTS v_upcoming_fomc_events AS
SELECT e.event_type, e.event_date, e.event_time, e.status, e.title,
       CASE e.event_type
         WHEN 'fomc_meeting'         THEN 'FOMC Rate Decision'
         WHEN 'fomc_sep'             THEN 'Summary of Economic Projections'
         WHEN 'fomc_minutes'         THEN 'FOMC Minutes'
         WHEN 'fomc_blackout_start'  THEN 'Communication Blackout Begins'
         WHEN 'fomc_blackout_end'    THEN 'Communication Blackout Ends'
         ELSE e.event_type END AS label
FROM events e, calendar_now p
WHERE e.event_type LIKE 'fomc\\_%' ESCAPE '\\' AND e.event_date >= p.today
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + FOMC views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_FOMC_VIEWS)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (2 + 3 tests). Note the `LIKE 'fomc\_%' ESCAPE '\'` so the `_` is a literal underscore, not a wildcard.

- [ ] **Step 5: Commit**

```bash
git add fomc_calendar/db.py tests/test_fomc_db_schema.py tests/test_fomc_db_views.py
git commit -m "feat(fomc): schema delegation + v_next_fomc / v_in_blackout / v_upcoming_fomc_events"
```

---

## Task 3: `fomc_calendar.run` — build_events + orchestration + CLI

**Files:**
- Create: `fomc_calendar/run.py`
- Test: `tests/test_fomc_db_write.py`, `tests/test_fomc_run.py`

**Interfaces:**
- `build_events(meetings, now_iso) -> list[dict]` — expand each meeting into its 4–5 event rows.
- `run(db_path, horizon_days=None, keep_days=None, fetch_calendar=fetch.fetch_calendar, now_iso=None) -> (snapshot_id, event_count)`.
- `main(argv=None)` — argparse, `prog="fomc"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fomc_db_write.py`:

```python
import json

from fomc_calendar import run as runmod

NOW = "2026-01-01T00:00:00+00:00"
MEETING = {"start_date": "2026-03-17", "end_date": "2026-03-18",
           "status": "tentative", "has_press_conference": True}
JAN = {"start_date": "2026-01-27", "end_date": "2026-01-28",
       "status": "confirmed", "has_press_conference": True}


def test_build_events_expands_all_types_with_subtype_convention():
    evs = runmod.build_events([MEETING], NOW)
    by_type = {e["event_type"]: e for e in evs}
    assert set(by_type) == {"fomc_meeting", "fomc_sep", "fomc_minutes",
                            "fomc_blackout_start", "fomc_blackout_end"}
    # meeting subtype is '' ; derived events pin to the decision date (end)
    assert by_type["fomc_meeting"]["subtype"] == ""
    assert by_type["fomc_minutes"]["subtype"] == "2026-03-18"
    # SEP only appears for a quarter-month meeting (March)
    assert json.loads(by_type["fomc_meeting"]["payload"])["has_sep"] is True
    assert by_type["fomc_minutes"]["event_date"] == "2026-04-08"     # +21d
    assert by_type["fomc_blackout_end"]["event_date"] == "2026-03-19"  # end+1


def test_build_events_no_sep_for_january_meeting():
    types = {e["event_type"] for e in runmod.build_events([JAN], NOW)}
    assert "fomc_sep" not in types


def test_run_upserts_then_firms_status_in_place(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)
    firmed = {**MEETING, "status": "confirmed"}
    runmod.run(db_path, fetch_calendar=lambda: [firmed], now_iso=NOW)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT status FROM events WHERE event_type='fomc_meeting'").fetchall()
    assert rows == [("confirmed",)]           # in place, no duplicate


def test_run_replace_forward_drops_cancelled_future_meeting(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [JAN, MEETING], now_iso=NOW)
    # next run no longer lists the March meeting -> its future rows disappear
    runmod.run(db_path, fetch_calendar=lambda: [JAN], now_iso=NOW)
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM events "
                     "WHERE event_date >= '2026-03-01'").fetchone()[0]
    assert n == 0
```

Create `tests/test_fomc_run.py`:

```python
import sqlite3

from fomc_calendar import fetch
from fomc_calendar import run as runmod

NOW = "2026-01-01T00:00:00+00:00"
MEETING = {"start_date": "2026-03-17", "end_date": "2026-03-18",
           "status": "tentative", "has_press_conference": True}


def test_run_end_to_end_counts_and_snapshots(tmp_path):
    db_path = str(tmp_path / "fomc.db")
    sid, count = runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)
    assert count == 5                          # meeting+sep+minutes+2 blackout
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_parse_error_aborts_loudly(tmp_path):
    def boom():
        raise fetch.FomcCalendarParseError("page structure changed")

    try:
        runmod.run(str(tmp_path / "fomc.db"), fetch_calendar=boom, now_iso=NOW)
        assert False, "expected FomcCalendarParseError to propagate"
    except fetch.FomcCalendarParseError:
        pass


def test_run_transient_fetch_failure_preserves_calendar_and_hides_secret(
        tmp_path, capsys):
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)  # seed

    def boom():
        raise RuntimeError("https://fed?token=SECRET boom")

    runmod.run(db_path, fetch_calendar=boom, now_iso=NOW)
    err = capsys.readouterr().err
    assert "SECRET" not in err and "RuntimeError" in err
    conn = sqlite3.connect(db_path)                # calendar preserved
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 5


def test_run_keep_days_prunes_snapshots_not_events(tmp_path):
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING],
               now_iso="2026-06-01T00:00:00+00:00", keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `fomc_calendar/run.py`:

```python
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone

import monitor_common
from fomc_calendar import db, fetch

_EVENT_TYPES = ("fomc_meeting", "fomc_sep", "fomc_minutes",
                "fomc_blackout_start", "fomc_blackout_end")


def _evt(event_type, event_date, event_time, subtype, title, status, payload):
    return {"event_type": event_type, "event_date": event_date,
            "event_time": event_time, "subtype": subtype, "title": title,
            "status": status, "source": "federalreserve",
            "payload": json.dumps(payload)}


def build_events(meetings, now_iso) -> list:
    """Expand each parsed meeting into its events rows. The meeting uses
    subtype='' ; every derived event pins to the meeting's decision date."""
    out = []
    for m in meetings:
        decision = m["end_date"]                 # day 2 = decision day
        status = m["status"]
        has_sep = fetch.is_sep_meeting(decision)
        out.append(_evt("fomc_meeting", decision, "14:00", "", "FOMC Meeting",
                        status, {"start": m["start_date"], "end": m["end_date"],
                                 "has_press_conference": m["has_press_conference"],
                                 "has_sep": has_sep}))
        if has_sep:
            out.append(_evt("fomc_sep", decision, "14:00", decision,
                            "FOMC SEP (dot plot)", status, {}))
        out.append(_evt("fomc_minutes", fetch.minutes_date(m["end_date"]),
                        "14:00", decision, "FOMC Minutes", status, {}))
        bo_start, bo_end = fetch.blackout_window(m["start_date"], m["end_date"])
        out.append(_evt("fomc_blackout_start", bo_start, None, decision,
                        "FOMC Blackout Begins", status, {"window_end": bo_end}))
        out.append(_evt("fomc_blackout_end", bo_end, None, decision,
                        "FOMC Blackout Ends", status, {"window_start": bo_start}))
    return out


def run(db_path, horizon_days=None, keep_days=None,
        fetch_calendar=fetch.fetch_calendar, now_iso=None):
    """Parse the FOMC calendar, derive minutes/blackout/SEP, replace the forward
    window per event_type, snapshot, and optionally prune. Returns
    (snapshot_id, event_count). A whole-page parse error aborts loudly; a
    transient fetch failure preserves the last-good calendar."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days or 7)

        try:
            meetings = fetch_calendar()
        except fetch.FomcCalendarParseError:
            raise                                # abort loudly on structural drift
        except Exception as e:                   # transient: keep last-good calendar
            print(f"warning: FOMC fetch failed: {type(e).__name__}",
                  file=sys.stderr)
            meetings = []

        if meetings:
            events = build_events(meetings, now_iso)
            if horizon_days is not None:
                cutoff = (date.fromisoformat(today)
                          + timedelta(days=horizon_days)).isoformat()
                events = [e for e in events if e["event_date"] <= cutoff]
            by_type = {}
            for e in events:
                by_type.setdefault(e["event_type"], []).append(e)
            for et in _EVENT_TYPES:
                monitor_common.replace_forward_window(conn, et, today,
                                                      by_type.get(et, []), now_iso)

        count = conn.execute("SELECT COUNT(*) FROM events WHERE event_date >= ?",
                             (today,)).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "federalreserve")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fomc",
        description="Pull the FOMC forward calendar (meetings/minutes/blackout/SEP)")
    p.add_argument("--db", default="fomc.db")
    p.add_argument("--horizon-days", type=int, default=None,
                   help="cap how far forward to store (default: keep all parsed)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    a = p.parse_args(argv)
    _, count = run(a.db, horizon_days=a.horizon_days, keep_days=a.keep_days)
    print(f"stored {count} forward FOMC events into {a.db}")


if __name__ == "__main__":
    main()
```

> **Note on `count` with `horizon_days`:** `count` re-queries `event_date >= today` (all forward events), while `horizon_days` caps which events get *written*. The end-to-end test uses `horizon_days=None`, so `count == 5`. This matches `market_calendar`'s counting convention (snapshot reflects the stored forward calendar size).

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (4 + 4 tests).

- [ ] **Step 5: Commit**

```bash
git add fomc_calendar/run.py tests/test_fomc_db_write.py tests/test_fomc_run.py
git commit -m "feat(fomc): build_events + run (replace-forward, drift-aborts, transient-safe) + CLI"
```

---

## Task 4: Register `fomc` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_fomc():
    import registry
    assert "fomc" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails** — `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import and register (after `"market_calendar"` if present, else after `"econ_calendar"`):

```python
from fomc_calendar.run import main as fomc_main
```
```python
    "fomc": fomc_main,
```

- [ ] **Step 4: Run test to verify it passes** — `python -m pytest tests/test_registry.py -v`.

- [ ] **Step 5: Run the FULL suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(fomc): register fomc dispatcher"
```

---

## Task 5: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `fomc` to Built**

- Add a `fomc` row to the **Built ✅** table (link this plan + the spec).
- Remove the `fomc` row from **Spec'd — event-date monitors 📝**.
- In **Recommended build order**, strike through item 6 (`fomc`) as ✅ Built, mirroring items 1–5. Optionally note the deferred Phase-1.5 RSS `status → released` flip (spec Non-goal).

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark fomc Built"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| Isolated `parse_calendar`, fails loudly (`FomcCalendarParseError`) on zero-from-nonempty | Task 1 |
| Pure `minutes_date` (+21d), `blackout_window` (2nd-Sat-before / end+1), `is_sep_meeting` (Mar/Jun/Sep/Dec) | Task 1 |
| `fetch_calendar` via `http_client` backoff + UA | Task 1 |
| `db.ensure_schema` delegates to `monitor_common` + 3 FOMC views | Task 2 |
| `v_next_fomc` (days_until + has_sep) / `v_in_blackout` (boolean) / `v_upcoming_fomc_events` (labels) | Task 2 |
| `build_events` 4–5 event types, subtype convention (`''` meeting, decision-date derived) | Task 3 |
| UPSERT firms status in place; replace-forward drops cancelled future meeting | Task 3 |
| `run` skip/abort semantics: parse-error aborts, transient preserves calendar, secret hygiene | Task 3 |
| CLI `--db/--horizon-days/--keep-days` | Task 3 |
| Registry `"fomc"` | Task 4 |
| No credentials; `.env.example` unchanged; `now_iso` injected | Global Constraints |

**2. Placeholder scan:** No `TODO` in code. The Phase-1.5 RSS `status→released` flip is a spec **Non-goal for v1** (noted in the roadmap entry), not a placeholder. The HTML parser regex is explicitly flagged for live confirmation with the raise-on-zero guard as the safety net — same discipline as `market_calendar.fetch`.

**3. Type consistency:** Event-row dict keys (`event_type, event_date, event_time, subtype, title, status, source, payload`) are identical across `_evt`/`build_events` (Task 3), the `monitor_common` helpers, and every test helper. `payload` is always a JSON **string** (`json.dumps`), so `json_extract` in the views works. Dates are ISO strings end-to-end; `blackout_window`/`minutes_date` take and return ISO strings. `subtype` is `''` for meetings, decision-date for derived — never NULL.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-fomc-calendar-monitor.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
