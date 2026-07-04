# Market Calendar Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `market_calendar` monitor — the forward calendar of U.S. **equity + bond market holidays, early closes, and monthly OPEX / quarterly quad-witching** — into the shared `events` table, and expose the clean **trading-day helpers** (`is_trading_day`, `next_trading_day`, `next_early_close`) that the rest of the system reuses.

**Architecture:** This monitor is the mirror image of `econ_calendar`: there the API is the source and code is thin; here **code is the source**. Holidays/early closes are **seeded constants** (`catalog.py`, cited from NYSE/SIFMA) with an **optional, isolated HTML parser** (`fetch.py`) as a refresh path; OPEX/quad-witching are **pure computation** (`compute.py`) from the third-Friday rule against the holiday set. It reuses the already-built `monitor_common` framework (events/snapshots schema, `set_today`, `replace_forward_window`, `write_snapshot`, `prune`, `v_upcoming`/`v_imminent`) and the shared `http_client` bounded-backoff (opt-in refresh only). **No credentials, no new dependency.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `datetime`, `argparse`, `dataclasses`, `re`/`html.parser`); `pytest`. Reuses `monitor_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` only (via `http_client`). No new packages.
- **No credentials.** A default run is **network-free and fully deterministic**; the HTML refresh is opt-in behind `--refresh`. `.env.example` is unchanged.
- **User-Agent** (for the opt-in refresh only): `agentic-trading-bot ninadk.dev@gmail.com`; bounded backoff on retryable statuses (403/429/503 — Cloudflare/CDN pages throttle) via `http_client`.
- **Fail loudly on drift.** The HTML parser must **raise** if its target table/anchor is missing or the parsed count is zero — **never** return an empty set that would blank the calendar (a monitor reporting "no holidays coming" is dangerous). Per-item errors log **only** `type(e).__name__`.
- **`now_iso` is injected, never wall-clock in logic.** Every `run()` accepts `now_iso=None`, defaulting to `datetime.now(timezone.utc).isoformat()`. All today/upcoming/imminent logic derives from it. **Never `date('now')` in SQL.**
- **`subtype` is part of the events primary key and must NEVER be NULL** — this monitor has no natural subtype, so every row writes `''`.
- **Write via `replace_forward_window` per `event_type`** — so a corrected/removed holiday or a recomputed OPEX set replaces cleanly and stale future rows disappear; past events (`event_date < today`) are never touched.
- **Prune NEVER touches future events.** `prune` deletes old `snapshots` provenance only.
- **Every writer ends with `conn.commit()`** (repo rule; `monitor_common` helpers already do).
- **Test command:** `python -m pytest` (config in `pyproject.toml`; `pythonpath=["."]`, `testpaths=["tests"]`).
- **Commits:** do NOT add a co-author line (per user global instruction).

---

## File Structure

**New — monitor layer (`market_calendar/` package):**
- `market_calendar/__init__.py` — empty package marker.
- `market_calendar/catalog.py` — seed constants: `EQUITY_HOLIDAYS`, `EQUITY_EARLY_CLOSES`, `BOND_HOLIDAYS`, `BOND_EARLY_CLOSES` (cited from NYSE/SIFMA), and small accessors.
- `market_calendar/compute.py` — pure `third_friday`, `opex_dates` (no I/O). *(One-module deviation from the spec's 4-file layout: the spec places these in `run.py`, but the spec's own test list names `test_market_calendar_compute.py`, so a dedicated pure module is cleaner and matches the intended test surface.)*
- `market_calendar/fetch.py` — thin OPTIONAL HTML parser (`parse_nyse_calendar`, `parse_sifma_calendar`), isolated, **fails loudly**; reuses `http_client`.
- `market_calendar/db.py` — `ensure_schema` (via `monitor_common`) + calendar views + trading-day helpers.
- `market_calendar/run.py` — seed + compute → `replace_forward_window` per `event_type`; argparse `main`.

**Modified:**
- `registry.py` — import `market_calendar.run.main` and register `"market_calendar"`.

**New tests (`tests/`):**
`test_market_calendar_catalog.py`, `test_market_calendar_compute.py`, `test_market_calendar_fetch.py`, `test_market_calendar_db_schema.py`, `test_market_calendar_db_write.py`, `test_market_calendar_run.py`, and one assertion added to `test_registry.py`.

### Event-row shape (all rows this monitor writes)

`monitor_common.upsert_events` / `replace_forward_window` consume dict rows with keys
`event_type, event_date, event_time, subtype, title, status, source, payload`.

| `event_type` | `event_time` | `source` | `title` example |
|---|---|---|---|
| `market_holiday` | `None` | `nyse` | `Independence Day (observed)` |
| `early_close` | `13:00` | `nyse` | `Day After Thanksgiving (early close)` |
| `bond_holiday` | `None` | `sifma` | `Columbus Day (bond)` |
| `bond_early_close` | `14:00` | `sifma` | `Good Friday (bond early close)` |
| `opex` | `16:00` | `computed` | `August Monthly OPEX` |
| `quad_witching` | `16:00` | `computed` | `June Quad Witching` |

`subtype = ''` and `status = 'scheduled'` throughout (deterministic; no tentative lifecycle).

### Live-verification action (do before finalizing `catalog.py`)

The seed dates below are transcribed from the official pages at 🔵 confidence. Before shipping, **confirm against NYSE (`nyse.com/markets/hours-calendars`) and SIFMA (`sifma.org/.../holiday-schedule`)**. The invariant tests in Task 1 (every equity/bond holiday falls Mon–Fri; observed-date rules) catch transcription typos. The 2026 equity/federal set and Good-Friday/Easter derivations are high-confidence; the SIFMA **bond early closes** and the **2027** rows are the least certain — verify or trim those, but the module ships runnable with 2026 fully seeded.

---

## Task 1: `market_calendar.catalog` — seed constants

**Files:**
- Create: `market_calendar/__init__.py` (empty)
- Create: `market_calendar/catalog.py`
- Test: `tests/test_market_calendar_catalog.py`

**Interfaces:**
- Produces:
  - `EQUITY_HOLIDAYS: dict[str, str]` — `"YYYY-MM-DD" -> label` (NYSE full closures).
  - `EQUITY_EARLY_CLOSES: dict[str, str]` — `"YYYY-MM-DD" -> "13:00"`.
  - `BOND_HOLIDAYS: dict[str, str]` — SIFMA full closures (adds Columbus Day, Veterans Day; excludes Good Friday, which SIFMA treats as an early close).
  - `BOND_EARLY_CLOSES: dict[str, str]` — `"YYYY-MM-DD" -> "14:00"`.
  - `holiday_dates() -> set[str]` — union of equity + bond full-closure dates (used by the OPEX shift).

- [ ] **Step 1: Write the failing test**

Create `tests/test_market_calendar_catalog.py`:

```python
from datetime import date

from market_calendar import catalog


def _all_dated():
    return (list(catalog.EQUITY_HOLIDAYS) + list(catalog.EQUITY_EARLY_CLOSES)
            + list(catalog.BOND_HOLIDAYS) + list(catalog.BOND_EARLY_CLOSES))


def test_every_seed_date_is_a_weekday():
    # A U.S. market holiday/early-close never lands on a weekend (it is observed
    # on the nearest weekday). This catches transcription typos loudly.
    for d in _all_dated():
        assert date.fromisoformat(d).weekday() < 5, f"{d} is a weekend"


def test_equity_early_close_times_are_1300():
    assert set(catalog.EQUITY_EARLY_CLOSES.values()) == {"13:00"}


def test_bond_early_close_times_are_1400():
    assert set(catalog.BOND_EARLY_CLOSES.values()) == {"14:00"}


def test_2026_core_equity_holidays_present():
    for d in ("2026-01-01", "2026-05-25", "2026-07-03",
              "2026-11-26", "2026-12-25"):
        assert d in catalog.EQUITY_HOLIDAYS


def test_bond_adds_columbus_and_veterans_not_in_equities():
    # SIFMA divergence: bonds observe Columbus Day + Veterans Day; equities do not.
    assert "2026-10-12" in catalog.BOND_HOLIDAYS      # Columbus Day
    assert "2026-11-11" in catalog.BOND_HOLIDAYS      # Veterans Day
    assert "2026-10-12" not in catalog.EQUITY_HOLIDAYS
    assert "2026-11-11" not in catalog.EQUITY_HOLIDAYS


def test_holiday_dates_unions_equity_and_bond_full_closures():
    hs = catalog.holiday_dates()
    assert "2026-01-01" in hs                          # equity + bond
    assert "2026-10-12" in hs                          # bond-only Columbus Day
    # early closes are NOT full-closure dates
    assert "2026-11-27" not in hs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_calendar_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_calendar'`

- [ ] **Step 3: Write minimal implementation**

Create `market_calendar/__init__.py` (empty).

Create `market_calendar/catalog.py`:

```python
"""Seeded U.S. market calendar — the source of truth for this monitor.

Transcribed 2026-07-03 from nyse.com/markets/hours-calendars (equities) and
sifma.org/resources/guides-playbooks/holiday-schedule (bonds). Re-confirm against
those pages before extending the horizon; the invariant tests catch weekend typos.

Divergence: the bond market (SIFMA) additionally observes Columbus Day and
Veterans Day, and treats Good Friday as an early close rather than a full close."""

# --- Equities (NYSE / Nasdaq full closures) ---------------------------------
EQUITY_HOLIDAYS: dict[str, str] = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

# Half-days close 13:00 ET (options 13:15). Day after Thanksgiving; Christmas Eve
# when it is a weekday; July 3 when July 4 is a weekday (not the case in 2026/2027).
EQUITY_EARLY_CLOSES: dict[str, str] = {
    "2026-11-27": "13:00",
    "2026-12-24": "13:00",
    "2027-11-26": "13:00",
}

# --- Bonds (SIFMA recommended full closures) --------------------------------
# Equity federal holidays PLUS Columbus Day + Veterans Day; Good Friday is a bond
# EARLY close (below), not a full closure.
BOND_HOLIDAYS: dict[str, str] = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-10-12": "Columbus Day",
    "2026-11-11": "Veterans Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-10-11": "Columbus Day",
    "2027-11-11": "Veterans Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

# SIFMA recommended bond early closes, 14:00 ET (2026 set from the design spec).
BOND_EARLY_CLOSES: dict[str, str] = {
    "2026-04-03": "14:00",   # Good Friday
    "2026-05-22": "14:00",   # Friday before Memorial Day
    "2026-07-02": "14:00",   # Thursday before Independence Day (observed)
    "2026-11-27": "14:00",   # Day after Thanksgiving
    "2026-12-24": "14:00",   # Christmas Eve
    "2026-12-31": "14:00",   # New Year's Eve
}


def holiday_dates() -> set[str]:
    """Union of equity + bond FULL-closure dates. This is the holiday set the
    OPEX computation shifts against (a 3rd Friday on any market closure moves to
    the preceding Thursday). Early closes are excluded — the market is open."""
    return set(EQUITY_HOLIDAYS) | set(BOND_HOLIDAYS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market_calendar_catalog.py -v`
Expected: PASS (6 tests). If any weekend assertion fails, a date was mistranscribed — fix against the official page.

- [ ] **Step 5: Commit**

```bash
git add market_calendar/__init__.py market_calendar/catalog.py tests/test_market_calendar_catalog.py
git commit -m "feat(market_calendar): seeded NYSE/SIFMA holiday + early-close catalog"
```

---

## Task 2: `market_calendar.compute` — OPEX / quad-witching (pure)

**Files:**
- Create: `market_calendar/compute.py`
- Test: `tests/test_market_calendar_compute.py`

**Interfaces:**
- Produces:
  - `third_friday(year: int, month: int) -> datetime.date` — the 3rd Friday.
  - `opex_dates(year: int, holidays: set[str]) -> list[tuple[str, str]]` — one `(iso_date, kind)` per month; `kind` is `"quad_witching"` for Mar/Jun/Sep/Dec else `"opex"`; if the 3rd Friday is in `holidays`, shift to the **preceding Thursday**.

- [ ] **Step 1: Write the failing test**

Create `tests/test_market_calendar_compute.py`:

```python
from datetime import date

from market_calendar import compute


def test_third_friday_known_values():
    assert compute.third_friday(2026, 1) == date(2026, 1, 16)
    assert compute.third_friday(2026, 6) == date(2026, 6, 19)
    assert compute.third_friday(2026, 8) == date(2026, 8, 21)


def test_opex_dates_tags_quad_witching_months():
    got = dict(compute.opex_dates(2026, set()))
    assert got["2026-03-20"] == "quad_witching"   # March -> quad
    assert got["2026-06-19"] == "quad_witching"   # June -> quad
    assert got["2026-09-18"] == "quad_witching"
    assert got["2026-12-18"] == "quad_witching"
    assert got["2026-08-21"] == "opex"            # August -> monthly


def test_opex_dates_has_twelve_entries():
    assert len(compute.opex_dates(2026, set())) == 12


def test_opex_shifts_to_thursday_when_third_friday_is_a_holiday():
    # Synthetic: pretend Aug 21 2026 (a 3rd Friday) is a market holiday.
    got = dict(compute.opex_dates(2026, {"2026-08-21"}))
    assert "2026-08-21" not in got
    assert got["2026-08-20"] == "opex"            # shifted to preceding Thursday
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_calendar_compute.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_calendar.compute'`

- [ ] **Step 3: Write minimal implementation**

Create `market_calendar/compute.py`:

```python
"""Pure OPEX / quad-witching computation — no I/O, no wall clock.

Monthly equity/index option expiration is the 3rd Friday; quad-witching is the
3rd Friday of Mar/Jun/Sep/Dec. When that Friday is a market holiday the
expiration shifts to the preceding Thursday — deterministic once the holiday set
is known, which is why this takes `holidays` as an argument rather than fetching."""
from datetime import date, timedelta

_QUAD_MONTHS = {3, 6, 9, 12}


def third_friday(year: int, month: int) -> date:
    """The 3rd Friday of (year, month)."""
    first = date(year, month, 1)
    # weekday(): Mon=0 .. Sun=6; Friday=4. Days from the 1st to the first Friday:
    offset = (4 - first.weekday()) % 7
    return first + timedelta(days=offset + 14)


def opex_dates(year: int, holidays: set) -> list:
    """One (iso_date, kind) per month for `year`. kind='quad_witching' for
    Mar/Jun/Sep/Dec else 'opex'. A 3rd Friday that is a market holiday shifts to
    the preceding Thursday."""
    out = []
    for month in range(1, 13):
        d = third_friday(year, month)
        if d.isoformat() in holidays:
            d = d - timedelta(days=1)   # preceding Thursday
        kind = "quad_witching" if month in _QUAD_MONTHS else "opex"
        out.append((d.isoformat(), kind))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market_calendar_compute.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add market_calendar/compute.py tests/test_market_calendar_compute.py
git commit -m "feat(market_calendar): pure third_friday + holiday-aware opex_dates"
```

---

## Task 3: `market_calendar.fetch` — thin optional HTML parser (fails loudly)

**Files:**
- Create: `market_calendar/fetch.py`
- Test: `tests/test_market_calendar_fetch.py`

**Interfaces:**
- Consumes: `http_client.make_opener`, `http_client.http_get`.
- Produces:
  - `parse_nyse_calendar(html: str) -> dict[str, str]` — extract `"YYYY-MM-DD" -> label` equity closures from the NYSE page's table. **Raises `ValueError` if zero rows parsed** (schema drift / blanked calendar).
  - `parse_sifma_calendar(html: str) -> dict[str, str]` — same, for the SIFMA bond page.
  - `fetch_page(url, get=None) -> str` — bounded-backoff GET (reuses `http_client`), UA set, retry on 403/429/503. Used only by the opt-in `--refresh`.

> **Parser realism note:** the official pages render holiday tables as HTML rows of `Holiday name` + a date cell per year. A robust v1 extracts `(label, date)` pairs via a tolerant regex/`html.parser` over the rendered rows and normalizes dates to ISO. The exact selectors depend on the live markup, which the executing agent should sample via a one-off `--refresh` fetch. The **non-negotiable contract** (and what the tests pin) is: **a parse yielding zero dated rows raises**, never returns `{}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_market_calendar_fetch.py`:

```python
import pytest

from market_calendar import fetch

# Minimal fixture shaped like the parser's tolerant contract: rows pairing a
# label with an ISO (or normalizable) date. Keep in sync with the parser regex.
_NYSE_HTML = """
<table><tr><td>New Year's Day</td><td>2026-01-01</td></tr>
<tr><td>Independence Day</td><td>2026-07-03</td></tr></table>
"""
_SIFMA_HTML = """
<table><tr><td>Columbus Day</td><td>2026-10-12</td></tr></table>
"""


def test_parse_nyse_extracts_dated_rows():
    got = fetch.parse_nyse_calendar(_NYSE_HTML)
    assert got["2026-01-01"] == "New Year's Day"
    assert "2026-07-03" in got


def test_parse_sifma_extracts_dated_rows():
    got = fetch.parse_sifma_calendar(_SIFMA_HTML)
    assert got["2026-10-12"] == "Columbus Day"


def test_parse_raises_on_zero_rows_never_blanks_calendar():
    with pytest.raises(ValueError):
        fetch.parse_nyse_calendar("<html><body>no table here</body></html>")


def test_fetch_page_uses_bounded_backoff(monkeypatch):
    calls = {"n": 0}

    def get(url):                       # injected opener stand-in
        calls["n"] += 1
        return "<ok/>"

    out = fetch.fetch_page("https://example.test/cal", get=get)
    assert out == "<ok/>"
    assert calls["n"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_calendar_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_calendar.fetch'`

- [ ] **Step 3: Write minimal implementation**

Create `market_calendar/fetch.py`:

```python
"""Thin, OPTIONAL HTML refresh for the seeded calendar. Isolated and fails loudly.

A normal run never calls this — the seed in catalog.py is the source of truth.
`--refresh` uses it to re-derive the seed from the official pages. If the target
table is missing or zero dated rows parse, we RAISE: a silently-empty holiday set
would tell the bot the market is open every day, which is dangerous."""
import re

from http_client import http_get, make_opener

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY = {403, 429, 503}

# Tolerant row matcher: a text label followed (within the same row) by a date we
# can normalize to ISO. The exact markup is confirmed live at refresh time; this
# contract — <label, date> pairs, raise on none — is what the monitor depends on.
_ROW = re.compile(
    r"<td[^>]*>\s*([A-Za-z][^<]*?)\s*</td>\s*<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>",
    re.IGNORECASE | re.DOTALL,
)


def _parse(html: str) -> dict:
    out = {}
    for label, iso in _ROW.findall(html or ""):
        out[iso] = label.strip()
    if not out:
        raise ValueError("no dated calendar rows parsed — refusing to blank the "
                         "calendar (source markup likely changed)")
    return out


def parse_nyse_calendar(html: str) -> dict:
    """Equity closures from the NYSE hours-and-calendars page. Raises on drift."""
    return _parse(html)


def parse_sifma_calendar(html: str) -> dict:
    """Bond closures from the SIFMA holiday-schedule page. Raises on drift."""
    return _parse(html)


def fetch_page(url: str, get=None) -> str:
    """Bounded-backoff GET for the opt-in refresh. `get` injectable for tests."""
    opener = get or make_opener(_UA)
    return http_get(url, opener, _RETRY)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market_calendar_fetch.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add market_calendar/fetch.py tests/test_market_calendar_fetch.py
git commit -m "feat(market_calendar): optional NYSE/SIFMA HTML refresh parser (fails loudly)"
```

---

## Task 4: `market_calendar.db` — schema, calendar views, trading-day helpers

**Files:**
- Create: `market_calendar/db.py`
- Test: `tests/test_market_calendar_db_schema.py`, `tests/test_market_calendar_db_write.py`

**Interfaces:**
- Consumes: `monitor_common` (`connect`, `ensure_schema` as `_mc_ensure_schema`, `upsert_events`, `set_today`).
- Produces:
  - `connect` — re-export from `monitor_common`.
  - `ensure_schema(conn) -> None` — calls `monitor_common.ensure_schema`, then creates `v_upcoming_closures`, `v_next_opex`, `v_early_closes`. Idempotent.
  - `is_trading_day(conn, d: str) -> bool` — `d` is a weekday **and** not in `market_holiday` events.
  - `next_trading_day(conn, d: str) -> str` — the next trading day strictly after `d`.
  - `next_early_close(conn, d: str) -> str | None` — the next `early_close` on or after `d`, else `None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_market_calendar_db_schema.py`:

```python
from market_calendar import db


def test_ensure_schema_creates_events_snapshots_and_calendar_views():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"events", "snapshots", "calendar_now"} <= tables
    assert {"v_upcoming_closures", "v_next_opex", "v_early_closes"} <= views


def test_ensure_schema_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)   # must not raise
```

Create `tests/test_market_calendar_db_write.py`:

```python
import monitor_common
from market_calendar import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _evt(event_type, date, event_time=None, title="T", source="nyse"):
    return {"event_type": event_type, "event_date": date,
            "event_time": event_time, "subtype": "", "title": title,
            "status": "scheduled", "source": source, "payload": None}


def test_is_trading_day_false_on_weekend_and_holiday():
    conn = _fresh()
    monitor_common.upsert_events(conn, [_evt("market_holiday", "2026-07-03")], "t")
    assert db.is_trading_day(conn, "2026-07-03") is False   # holiday
    assert db.is_trading_day(conn, "2026-07-04") is False   # Saturday
    assert db.is_trading_day(conn, "2026-07-06") is True    # Monday, open


def test_next_trading_day_skips_weekend_and_holiday():
    conn = _fresh()
    monitor_common.upsert_events(conn, [_evt("market_holiday", "2026-07-03")], "t")
    # Thu 2026-07-02 -> Fri is a holiday, Sat/Sun weekend -> Mon 2026-07-06
    assert db.next_trading_day(conn, "2026-07-02") == "2026-07-06"


def test_next_early_close_returns_next_on_or_after():
    conn = _fresh()
    monitor_common.upsert_events(
        conn, [_evt("early_close", "2026-11-27", "13:00")], "t")
    assert db.next_early_close(conn, "2026-01-01") == "2026-11-27"
    assert db.next_early_close(conn, "2026-12-01") is None


def test_v_upcoming_closures_lists_holidays_and_early_closes_from_today():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-06-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("market_holiday", "2026-05-25"),                  # past -> out
        _evt("market_holiday", "2026-07-03"),                  # future -> in
        _evt("early_close", "2026-11-27", "13:00"),            # future -> in
    ], "t")
    dates = [r[0] for r in conn.execute(
        "SELECT event_date FROM v_upcoming_closures ORDER BY event_date")]
    assert dates == ["2026-07-03", "2026-11-27"]


def test_v_next_opex_returns_soonest_expiration():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("opex", "2026-08-21", "16:00", source="computed"),
        _evt("quad_witching", "2026-09-18", "16:00", source="computed"),
    ], "t")
    row = conn.execute(
        "SELECT event_date, event_type FROM v_next_opex").fetchone()
    assert row == ("2026-08-21", "opex")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_market_calendar_db_schema.py tests/test_market_calendar_db_write.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_calendar.db'`

- [ ] **Step 3: Write minimal implementation**

Create `market_calendar/db.py`:

```python
"""market_calendar store: the shared monitor schema plus calendar-specific views
and the trading-day helpers other modules import.

is_trading_day/next_trading_day/next_early_close are Python helpers (not views)
because 'is date D open?' needs a bound date argument, which a stored SQLite view
cannot carry. They read the events table written by run.py."""
from datetime import date, timedelta

from monitor_common import connect
from monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema", "is_trading_day", "next_trading_day",
           "next_early_close"]

_CAL_SCHEMA = """
-- What's closed or short from today onward (equity + bond).
CREATE VIEW IF NOT EXISTS v_upcoming_closures AS
SELECT e.event_type, e.event_date, e.event_time, e.title, e.source
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('market_holiday', 'early_close',
                       'bond_holiday', 'bond_early_close')
ORDER BY e.event_date, e.event_time;

-- The single soonest option expiration (monthly OPEX or quad-witching).
CREATE VIEW IF NOT EXISTS v_next_opex AS
SELECT e.event_type, e.event_date, e.event_time, e.title
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('opex', 'quad_witching')
ORDER BY e.event_date
LIMIT 1;

-- Upcoming half-days (equity + bond), with their close time.
CREATE VIEW IF NOT EXISTS v_early_closes AS
SELECT e.event_type, e.event_date, e.event_time, e.title, e.source
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('early_close', 'bond_early_close')
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + calendar views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_CAL_SCHEMA)
    conn.commit()


def is_trading_day(conn, d: str) -> bool:
    """True iff `d` (YYYY-MM-DD) is a weekday and not an equity market_holiday."""
    if date.fromisoformat(d).weekday() >= 5:            # Sat/Sun
        return False
    hit = conn.execute(
        "SELECT 1 FROM events WHERE event_type='market_holiday' "
        "AND event_date=? LIMIT 1", (d,)).fetchone()
    return hit is None


def next_trading_day(conn, d: str) -> str:
    """The next equity trading day strictly after `d`. Bounded scan (holidays
    never cluster more than a few days) so a bad DB can't loop forever."""
    cur = date.fromisoformat(d)
    for _ in range(30):
        cur += timedelta(days=1)
        if is_trading_day(conn, cur.isoformat()):
            return cur.isoformat()
    raise RuntimeError("no trading day found within 30 days")


def next_early_close(conn, d: str):
    """The next equity early_close on or after `d`, or None."""
    row = conn.execute(
        "SELECT event_date FROM events WHERE event_type='early_close' "
        "AND event_date >= ? ORDER BY event_date LIMIT 1", (d,)).fetchone()
    return row[0] if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_market_calendar_db_schema.py tests/test_market_calendar_db_write.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add market_calendar/db.py tests/test_market_calendar_db_schema.py tests/test_market_calendar_db_write.py
git commit -m "feat(market_calendar): calendar views + trading-day helpers"
```

---

## Task 5: `market_calendar.run` — orchestration + CLI

**Files:**
- Create: `market_calendar/run.py`
- Test: `tests/test_market_calendar_run.py`

**Interfaces:**
- Consumes: `market_calendar.catalog`, `market_calendar.compute`, `market_calendar.fetch`, `market_calendar.db`, `monitor_common` (`set_today`, `replace_forward_window`, `write_snapshot`, `prune`).
- Produces:
  - `run(db_path, years=2, horizon_days=7, keep_days=None, refresh=False, pages=None, now_iso=None) -> (snapshot_id, event_count)`.
  - `main(argv=None)` — argparse CLI, `prog="market_calendar"`.

**Behavior:**
1. `now_iso` default to UTC now; `today = date(now_iso)`.
2. `ensure_schema`; `set_today(now_iso, horizon_days)`.
3. Load seeds from `catalog`. If `refresh` (or `pages` injected), parse via `fetch` and **merge over** the seed (parser raising on drift aborts the run — correct).
4. Build event rows: equity holidays → `market_holiday`; equity early closes → `early_close` (`13:00`); bond holidays → `bond_holiday`; bond early closes → `bond_early_close` (`14:00`).
5. Compute `opex_dates` for `years` forward from `today`'s year against `catalog.holiday_dates()`; tag `opex` / `quad_witching` (`16:00`).
6. Write **per `event_type`** via `replace_forward_window` (each of the 6 types, so removed/shifted future rows disappear; past retained).
7. `event_count` = future events after write; `write_snapshot(now_iso, event_count, 'market_calendar')`; `prune` if `keep_days`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_market_calendar_run.py`:

```python
import sqlite3

from market_calendar import run as runmod

NOW = "2026-06-01T00:00:00+00:00"


def test_run_writes_holidays_early_closes_and_opex(tmp_path):
    db_path = str(tmp_path / "m.db")
    sid, count = runmod.run(db_path, years=1, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    types = {r[0] for r in conn.execute(
        "SELECT DISTINCT event_type FROM events")}
    assert {"market_holiday", "early_close", "bond_holiday",
            "bond_early_close", "opex", "quad_witching"} <= types
    # 12 monthly expirations for the one computed year, all future from June 1.
    n_opex = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type IN ('opex','quad_witching')"
    ).fetchone()[0]
    assert n_opex >= 7            # Jun..Dec forward at least
    assert count > 0


def test_run_is_idempotent_no_duplicates(tmp_path):
    db_path = str(tmp_path / "m.db")
    runmod.run(db_path, years=1, now_iso=NOW)
    runmod.run(db_path, years=1, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    # replace_forward_window keeps the future set stable across identical runs.
    dupes = conn.execute(
        "SELECT event_type, event_date, COUNT(*) c FROM events "
        "GROUP BY event_type, event_date HAVING c > 1").fetchall()
    assert dupes == []


def test_run_keep_days_prunes_snapshots_not_future_events(tmp_path):
    db_path = str(tmp_path / "m.db")
    runmod.run(db_path, years=1, now_iso="2026-01-01T00:00:00+00:00")   # old snap
    runmod.run(db_path, years=1, now_iso=NOW, keep_days=30)             # prunes
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0


def test_run_refresh_merges_parsed_pages_over_seed(tmp_path):
    db_path = str(tmp_path / "m.db")
    pages = {"nyse": "<td>Test Holiday</td><td>2026-06-15</td>", "sifma": None}
    runmod.run(db_path, years=1, now_iso=NOW, pages=pages)
    conn = sqlite3.connect(db_path)
    hit = conn.execute(
        "SELECT title FROM events WHERE event_date='2026-06-15' "
        "AND event_type='market_holiday'").fetchone()
    assert hit == ("Test Holiday",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_market_calendar_run.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'market_calendar.run'`

- [ ] **Step 3: Write minimal implementation**

Create `market_calendar/run.py`:

```python
import argparse
from datetime import datetime, timezone

import monitor_common
from market_calendar import catalog, compute, db, fetch

_NYSE_URL = "https://www.nyse.com/markets/hours-calendars"
_SIFMA_URL = "https://www.sifma.org/resources/guides-playbooks/holiday-schedule"


def _rows(mapping, event_type, source, event_time=None):
    """Build events rows from a {date: label-or-time} seed mapping."""
    return [{"event_type": event_type, "event_date": d,
             "event_time": event_time, "subtype": "", "title": _title(label),
             "status": "scheduled", "source": source, "payload": None}
            for d, label in mapping.items()]


def _title(label):
    return label if isinstance(label, str) and not label[:1].isdigit() else None


def run(db_path, years=2, horizon_days=7, keep_days=None, refresh=False,
        pages=None, now_iso=None):
    """Seed holidays/early closes + compute OPEX/quad-witching into the events
    calendar; write each event_type via replace_forward_window so stale future
    rows disappear. Deterministic and network-free unless refresh/pages given.
    Returns (snapshot_id, event_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()
    start_year = int(today[:4])

    eq_hol = dict(catalog.EQUITY_HOLIDAYS)
    eq_early = dict(catalog.EQUITY_EARLY_CLOSES)
    bond_hol = dict(catalog.BOND_HOLIDAYS)
    bond_early = dict(catalog.BOND_EARLY_CLOSES)

    if refresh or pages is not None:
        pages = pages or {"nyse": fetch.fetch_page(_NYSE_URL),
                          "sifma": fetch.fetch_page(_SIFMA_URL)}
        if pages.get("nyse"):
            eq_hol.update(fetch.parse_nyse_calendar(pages["nyse"]))  # raises on drift
        if pages.get("sifma"):
            bond_hol.update(fetch.parse_sifma_calendar(pages["sifma"]))

    holiday_set = set(eq_hol) | set(bond_hol)
    opex = []
    for year in range(start_year, start_year + years):
        for iso, kind in compute.opex_dates(year, holiday_set):
            opex.append({"event_type": kind, "event_date": iso,
                         "event_time": "16:00", "subtype": "",
                         "title": _opex_title(iso, kind), "status": "scheduled",
                         "source": "computed", "payload": None})

    by_type = {
        "market_holiday": _rows(eq_hol, "market_holiday", "nyse"),
        "early_close": _rows(eq_early, "early_close", "nyse", "13:00"),
        "bond_holiday": _rows(bond_hol, "bond_holiday", "sifma"),
        "bond_early_close": _rows(bond_early, "bond_early_close", "sifma", "14:00"),
        "opex": [r for r in opex if r["event_type"] == "opex"],
        "quad_witching": [r for r in opex if r["event_type"] == "quad_witching"],
    }

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days)
        for event_type, rows in by_type.items():
            monitor_common.replace_forward_window(conn, event_type, today, rows,
                                                  now_iso)
        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_date >= ?", (today,)
        ).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "market_calendar")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _opex_title(iso, kind):
    month = _MONTHS[int(iso[5:7]) - 1]
    return (f"{month} Quad Witching" if kind == "quad_witching"
            else f"{month} Monthly OPEX")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="market_calendar",
        description="Seed U.S. market holidays/early closes + compute OPEX into SQLite")
    p.add_argument("--db", default="market_calendar.db")
    p.add_argument("--years", type=int, default=2,
                   help="years of OPEX/quad-witching to compute forward")
    p.add_argument("--horizon-days", type=int, default=7,
                   help="imminence window for v_imminent")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    p.add_argument("--refresh", action="store_true",
                   help="opt-in: refresh the seed from the live NYSE/SIFMA pages")
    a = p.parse_args(argv)
    _, count = run(a.db, years=a.years, horizon_days=a.horizon_days,
                   keep_days=a.keep_days, refresh=a.refresh)
    print(f"stored {count} forward market-calendar events into {a.db}")


if __name__ == "__main__":
    main()
```

> **Note on `_title`/`_rows`:** the seed mappings carry `date -> label` for holidays but `date -> "13:00"` for early closes. `_title` returns the label for holidays and `None` for the time-valued early-close maps (their human title comes from `event_type` + date downstream; keeping `title` NULL avoids storing "13:00" as a title). The executing agent may instead give early closes explicit titles (e.g. a parallel label map) — either is acceptable as long as `event_time` is `13:00`/`14:00` and the row validates.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_market_calendar_run.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add market_calendar/run.py tests/test_market_calendar_run.py
git commit -m "feat(market_calendar): run orchestration (seed + compute, replace-forward) + CLI"
```

---

## Task 6: Register `market_calendar` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_market_calendar():
    import registry
    assert "market_calendar" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_registry.py::test_dispatch_lists_market_calendar -v`
Expected: FAIL — `AssertionError`

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import alongside the others:

```python
from market_calendar.run import main as market_calendar_main
```

And add to `REGISTRY` (after `"econ_calendar"`):

```python
    "econ_calendar": econ_calendar_main,
    "market_calendar": market_calendar_main,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green — new modules plus all existing screeners).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(market_calendar): register market_calendar dispatcher"
```

---

## Task 7: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `market_calendar` to Built and mark the plan**

In `docs/ROADMAP.md`:
- Add a `market_calendar` row to the **Built ✅** table (links to this plan + the design spec).
- Remove the `market_calendar` row from the **Spec'd — event-date monitors 📝** table.
- In **Recommended build order**, strike through item 4 (`market_calendar`) as ✅ Built, mirroring items 1–3; note it added the shared trading-day helpers other monitors/screeners reuse.

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark market_calendar Built; trading-day helpers landed"
```

---

## Self-Review

**1. Spec coverage** (market-calendar spec):

| Spec requirement | Task |
|---|---|
| `catalog.py` seeded equity + bond holidays / early closes, cited | Task 1 |
| Bond divergence (Columbus/Veterans Day; Good Friday early close) | Task 1 |
| Pure `third_friday` / `opex_dates`, quad-witching tagging, Fri→Thu holiday shift | Task 2 |
| Thin optional HTML parser, isolated, **raises on zero rows** | Task 3 |
| Bounded backoff on 403/429/503 for opt-in refresh | Task 3 |
| `db.ensure_schema` layering `monitor_common` + calendar views | Task 4 |
| `v_upcoming_closures` / `v_next_opex` / `v_early_closes` | Task 4 |
| `is_trading_day` / `next_trading_day` / `next_early_close` helpers | Task 4 |
| `run()` seed+compute, `replace_forward_window` per type, `now_iso` injected | Task 5 |
| CLI `--db/--years/--horizon-days/--keep-days/--refresh` | Task 5 |
| Registry dispatch `"market_calendar"` | Task 6 |
| No credentials; `.env.example` unchanged; network-free default | Global Constraints |
| `subtype=''`; prune snapshots-only, never events | Global Constraints / Task 4–5 |

**2. Placeholder scan:** No `TBD`/`TODO` in code steps. The one genuinely-uncertain area (SIFMA bond early closes and 2027 rows at 🔵 confidence) is handled by the **live-verification action** + the weekend-invariant test, not a code placeholder — the module ships runnable with 2026 fully seeded.

**3. Type consistency:** Event-row dict keys (`event_type, event_date, event_time, subtype, title, status, source, payload`) are identical across `_rows`/OPEX builders (Task 5), the `monitor_common` helpers, and every test helper. `event_time` is `None` for holidays, `13:00`/`14:00` for early closes, `16:00` for OPEX. `holiday_dates()` (Task 1) feeds `opex_dates(year, holidays)` (Task 2) as a `set[str]`. `is_trading_day`/`next_trading_day` take/return ISO date strings consistently (Task 4).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-market-calendar-monitor.md`. Execute task-by-task via superpowers:subagent-driven-development (recommended) or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
