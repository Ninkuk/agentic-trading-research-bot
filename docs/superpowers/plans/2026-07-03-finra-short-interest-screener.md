# FINRA Equity Short Interest Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `short_interest` screener that pulls FINRA's bi-monthly settled equity short-interest files into SQLite, exposing a squeeze / days-to-cover reader.

**Architecture:** Clone the `finra_short_volume` module template (`fetch.py` → `db.py` → `run.py`, registered in `registry.py`) over a **bi-monthly settlement file** instead of a daily one. Same CDN, same pipe parser, same descriptive-`User-Agent`, same FRED-style single-table prune. The only new machinery is a **settlement-date schedule generator** (the ~15th + month-end of each month, rolled back to a business day) that replaces calendar-day enumeration.

**Tech Stack:** Python 3 standard library only (`sqlite3`, `urllib`, `argparse`, `datetime`), reusing the repo's `http_client` (bounded backoff) and `screener_common.connect` (WAL). Tests: `pytest`. No new dependencies.

## Global Constraints

Every task's requirements implicitly include this section. Values copied verbatim from the spec.

- **No new dependencies, no new env vars.** The CDN bulk file needs no credentials; `.env.example` is unchanged.
- **Data source (primary):** `https://cdn.finra.org/equity/otcmarket/biweekly/shrt{YYYYMMDD}.csv`, where `{YYYYMMDD}` is the **settlement date**, not the publication date.
- **Pipe-delimited despite the `.csv` extension** — split on `|`, drop the header by coercion failure, skip short/malformed lines.
- **Descriptive User-Agent required** (CDN behind Cloudflare): `agentic-trading-bot ninadk.dev@gmail.com`.
- **403 and 404 both mean "no file for this settlement" → skip** (return `None`). Only `429`/`503` and transient network errors are retryable.
- **Secret-hygiene rule (repo-wide):** on a per-settlement failure, log **only `type(e).__name__`** to stderr — never `str(e)` / `e.url`.
- **Replace-by-settlement writes:** delete the settlement's rows, then bulk-insert, so a FINRA repost that drops a symbol leaves no orphan.
- **Retention:** keep **all** short-interest history; `--keep-days` prunes **only** run-provenance snapshots, never facts.
- **View thresholds baked into SQL:** liquidity floor `avg_daily_volume >= 100000`; squeeze threshold `days_to_cover >= 5.0`.
- **Coverage cutoff (documentation only, not enforced):** consolidated exchange-listed short interest exists only from **June 2021 onward**; a `--start` earlier than 2021-06 yields OTC-only universes.
- **Column order (🟡 confirm live at build time before wiring the parser):**
  `accountingYearMonthNumber | symbolCode | issueName | marketClassCode | currentShortPositionQuantity | previousShortPositionQuantity | changePercent | averageDailyVolumeQuantity | daysToCoverQuantity | revisionFlag | stockSplitFlag | newIssueFlag | settlementDate`

---

## File Structure

| Path | Responsibility |
|---|---|
| `finra_short_interest/__init__.py` | Package marker (empty). |
| `finra_short_interest/fetch.py` | CDN download + pipe parse: `settlement_url`, `parse_file`, `fetch_settlement`. |
| `finra_short_interest/db.py` | SQLite schema + writes + squeeze views + FRED-style prune. |
| `finra_short_interest/run.py` | Settlement-date enumeration + incremental orchestration + argparse CLI. |
| `registry.py` | Register `"short_interest"` dispatcher (modify). |
| `tests/test_finra_short_interest_fetch.py` | Parser / URL / 403-404 tests (network never hit). |
| `tests/test_finra_short_interest_db_schema.py` | Schema idempotency; tables + views exist. |
| `tests/test_finra_short_interest_db_write.py` | `upsert_securities`, `replace_settlement`, `record_settlement`, `stored_settlements`, `prune`. |
| `tests/test_finra_short_interest_db_views.py` | `v_latest`, `v_high_days_to_cover`, `v_short_interest_spikes` semantics. |
| `tests/test_finra_short_interest_run.py` | Settlement enumeration + incremental skip + trailing-refetch + `--full` + secret hygiene. |
| `tests/test_registry.py` | Assert `"short_interest"` dispatches (modify). |
| `docs/ROADMAP.md` | Mark `short_interest` Built (modify). |

---

### Task 1: `fetch.py` — download + pipe parse

**Files:**
- Create: `finra_short_interest/__init__.py`
- Create: `finra_short_interest/fetch.py`
- Test: `tests/test_finra_short_interest_fetch.py`

**Interfaces:**
- Consumes: `http_client.make_opener`, `http_client.http_get` (repo root).
- Produces:
  - `settlement_url(date: str, base: str = FILES_BASE) -> str`
  - `parse_file(text: str) -> list[dict]` — each dict has keys `symbol, issue_name, settlement_date, current_short_qty, previous_short_qty, avg_daily_volume, days_to_cover, change_pct, revision_flag, market_class`.
  - `fetch_settlement(date: str, get=_http_get, opener=None) -> list[dict] | None` (None on 403/404).

- [ ] **Step 1: Create the empty package marker**

Create `finra_short_interest/__init__.py` as an empty file (zero bytes).

- [ ] **Step 2: Write the failing fetch test**

Create `tests/test_finra_short_interest_fetch.py`:

```python
# tests/test_finra_short_interest_fetch.py
import urllib.error

import pytest

from finra_short_interest.fetch import (
    _http_get, fetch_settlement, parse_file, settlement_url,
)

# Pipe-delimited despite .csv. Header + 3 keepable rows + 3 droppable rows.
SAMPLE = (
    "accountingYearMonthNumber|symbolCode|issueName|marketClassCode|"
    "currentShortPositionQuantity|previousShortPositionQuantity|changePercent|"
    "averageDailyVolumeQuantity|daysToCoverQuantity|revisionFlag|"
    "stockSplitFlag|newIssueFlag|settlementDate\n"
    "202406|AAL|AMERICAN AIRLINES|NNM|1500000|1200000|25.0|500000|3.0|A||N|20240614\n"
    "202406|ILLQ|ILLIQUID CORP|OTC|900000|900000|0.0|1000|900.0|||N|20240614\n"
    "202406|BLNK|BLANK NUMS|NNM|5000|||500||X||N|20240614\n"   # blank prev/chg/dtc -> None
    "202406||NO SYMBOL|NNM|100|100|0|500|1|||N|20240614\n"     # blank symbol -> skipped
    "202406|SHORT|TOO FEW FIELDS|NNM|100\n"                    # < 13 fields -> skipped
    "Trailer|rec|count|x|y|z|w|v|u|t|s|r|qq\n"                 # bad date/qty -> skipped
)


def test_parse_file_maps_columns_and_keeps_three_rows():
    rows = parse_file(SAMPLE)
    assert len(rows) == 3                      # AAL + ILLQ + BLNK
    assert rows[0] == {
        "symbol": "AAL", "issue_name": "AMERICAN AIRLINES",
        "settlement_date": "2024-06-14",
        "current_short_qty": 1500000, "previous_short_qty": 1200000,
        "avg_daily_volume": 500000, "days_to_cover": pytest.approx(3.0),
        "change_pct": pytest.approx(25.0), "revision_flag": "A",
        "market_class": "NNM",
    }


def test_parse_file_blank_numerics_and_flags_become_none():
    blnk = [r for r in parse_file(SAMPLE) if r["symbol"] == "BLNK"][0]
    assert blnk["previous_short_qty"] is None
    assert blnk["change_pct"] is None
    assert blnk["days_to_cover"] is None
    assert blnk["revision_flag"] is None


def test_parse_file_header_row_is_dropped():
    header_only = SAMPLE.splitlines()[0] + "\n"
    assert parse_file(header_only) == []


def test_settlement_url_formats_settlement_date():
    assert settlement_url("2024-06-14") == (
        "https://cdn.finra.org/equity/otcmarket/biweekly/shrt20240614.csv")


def test_fetch_settlement_parses_returned_text():
    def fake_get(url, opener=None):
        assert url.endswith("shrt20240614.csv")
        return SAMPLE

    rows = fetch_settlement("2024-06-14", get=fake_get)
    assert len(rows) == 3


def test_fetch_settlement_returns_none_on_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    assert fetch_settlement("2099-01-15", get=fake_get) is None


def test_fetch_settlement_returns_none_on_403():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)

    assert fetch_settlement("2099-01-15", get=fake_get) is None


def test_fetch_settlement_reraises_non_404_non_403():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 500, "err", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_settlement("2024-06-14", get=fake_get)


def test_http_get_retries_on_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_fetch.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'finra_short_interest.fetch'` (or import error).

- [ ] **Step 4: Write `fetch.py`**

Create `finra_short_interest/fetch.py`:

```python
# finra_short_interest/fetch.py
import time
import urllib.error

import http_client

FILES_BASE = "https://cdn.finra.org/equity/otcmarket/biweekly"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family only. 403 is NOT retryable here: like the short-volume
# CDN, it signals "no file for this settlement date".
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_MIN_FIELDS = 13

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def settlement_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the FINRA equity short-interest file for a 'YYYY-MM-DD' settlement
    date. Named by settlement date: shrt{YYYYMMDD}.csv (pipe-delimited body)."""
    return f"{base}/shrt{date.replace('-', '')}.csv"


def _norm_date(raw) -> str | None:
    """YYYYMMDD -> YYYY-MM-DD; None if not exactly 8 digits."""
    raw = (raw or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _num(raw, cast):
    """Coerce a stripped string via cast; blank/unparseable -> None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def _to_int(raw):
    """Integer, tolerant of a trailing '.0' FINRA may emit for share quantities.
    The header row's non-numeric value fails float() -> None -> line dropped."""
    return _num(raw, lambda v: int(float(v)))


def _to_float(raw):
    return _num(raw, float)


def parse_file(text: str) -> list[dict]:
    """Parse a FINRA equity short-interest file body into rows.

    Pipe-delimited despite the .csv extension. Column order:
      accountingYearMonthNumber | symbolCode | issueName | marketClassCode |
      currentShortPositionQuantity | previousShortPositionQuantity |
      changePercent | averageDailyVolumeQuantity | daysToCoverQuantity |
      revisionFlag | stockSplitFlag | newIssueFlag | settlementDate
    The header line drops naturally (its non-numeric quantity fails coercion).
    Any trailer/short/malformed line is skipped: fewer than 13 fields, or
    missing symbolCode, a valid 8-digit settlementDate, or a parseable
    currentShortPositionQuantity. days_to_cover / change_pct are FINRA-computed
    and stored as-is (blank -> None); they are never re-derived."""
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < _MIN_FIELDS:
            continue
        (_aym, symbol, issue, mclass, cur, prev, chg,
         adv, dtc, rev, _split, _new, sdate) = (p.strip() for p in parts[:13])
        settlement_date = _norm_date(sdate)
        current_short_qty = _to_int(cur)
        if not symbol or settlement_date is None or current_short_qty is None:
            continue
        rows.append({
            "symbol": symbol,
            "issue_name": issue or None,
            "settlement_date": settlement_date,
            "current_short_qty": current_short_qty,
            "previous_short_qty": _to_int(prev),
            "avg_daily_volume": _to_int(adv),
            "days_to_cover": _to_float(dtc),
            "change_pct": _to_float(chg),
            "revision_flag": rev or None,
            "market_class": mclass or None,
        })
    return rows


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET file text with bounded backoff, retrying 429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
    fetch_settlement can map 403/404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_settlement(date: str, get=_http_get, opener=None):
    """Download + parse one settlement's file. Returns list[dict], or None on
    HTTP 403/404 (absent / not-yet-published settlement)."""
    op = opener if opener is not None else _urlopen
    try:
        text = get(settlement_url(date), opener=op)
    except urllib.error.HTTPError as e:
        # CDN returns 403 (not 404) for dates with no file; both mean skip.
        if e.code in (403, 404):
            return None
        raise
    return parse_file(text)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_fetch.py -q`
Expected: PASS (9 passed).

- [ ] **Step 6: Commit**

```bash
git add finra_short_interest/__init__.py finra_short_interest/fetch.py tests/test_finra_short_interest_fetch.py
git commit -m "feat(short_interest): CDN download + pipe parser"
```

---

### Task 2: `db.py` — schema + writes

**Files:**
- Create: `finra_short_interest/db.py`
- Test: `tests/test_finra_short_interest_db_schema.py`
- Test: `tests/test_finra_short_interest_db_write.py`

**Interfaces:**
- Consumes: `screener_common.connect`; the row-dict shape produced by `parse_file` (Task 1).
- Produces:
  - `ensure_schema(conn) -> None`
  - `upsert_securities(conn, rows: list[dict]) -> None`
  - `replace_settlement(conn, settlement_date: str, rows: list[dict]) -> int`
  - `record_settlement(conn, settlement_date: str, fetched_at: str, row_count: int) -> None`
  - `write_snapshot(conn, captured_at: str, settlement_count: int, row_count: int) -> int`
  - `stored_settlements(conn) -> list[str]`
  - `prune(conn, keep_days: int, now_iso: str) -> int`
  - Re-exports `connect`.

- [ ] **Step 1: Write the failing schema test**

Create `tests/test_finra_short_interest_db_schema.py`:

```python
# tests/test_finra_short_interest_db_schema.py
from finra_short_interest import db


def test_ensure_schema_is_idempotent_and_creates_tables():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)            # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"securities", "short_interest", "settlements", "snapshots"} <= tables
```

- [ ] **Step 2: Write the failing write test**

Create `tests/test_finra_short_interest_db_write.py`:

```python
# tests/test_finra_short_interest_db_write.py
from finra_short_interest import db


def _rows(*specs):
    """spec tuples: (symbol, settlement_date, issue_name, current_short_qty)."""
    out = []
    for symbol, sdate, issue, cur in specs:
        out.append({
            "symbol": symbol, "issue_name": issue, "settlement_date": sdate,
            "current_short_qty": cur, "previous_short_qty": None,
            "avg_daily_volume": 200000, "days_to_cover": 1.0,
            "change_pct": 0.0, "revision_flag": None, "market_class": "NNM",
        })
    return out


def test_replace_settlement_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("AA", "2024-06-14", "ALPHA", 100),
               ("BB", "2024-06-14", "BETA", 300))
    db.upsert_securities(conn, v1)
    assert db.replace_settlement(conn, "2024-06-14", v1) == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM short_interest").fetchone()[0] == 2

    # repost drops BB and revises AA's current_short_qty
    v2 = _rows(("AA", "2024-06-14", "ALPHA", 150))
    db.upsert_securities(conn, v2)
    assert db.replace_settlement(conn, "2024-06-14", v2) == 1
    assert [tuple(r) for r in conn.execute(
        "SELECT symbol, current_short_qty FROM short_interest")] == [("AA", 150)]


def test_upsert_securities_refreshes_issue_name_to_newest_and_tracks_seen():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", "OLD CO", 1)))
    db.upsert_securities(conn, _rows(("AA", "2024-07-15", "NEW CO", 1)))
    db.upsert_securities(conn, _rows(("AA", "2024-05-15", "ANCIENT CO", 1)))
    issue, first, last = conn.execute(
        "SELECT issue_name, first_seen, last_seen FROM securities "
        "WHERE symbol='AA'").fetchone()
    assert issue == "NEW CO"                   # newest settlement wins
    assert (first, last) == ("2024-05-15", "2024-07-15")


def test_stored_settlements_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_settlement(conn, "2024-06-28", "t", 10)
    db.record_settlement(conn, "2024-06-14", "t", 5)
    db.record_settlement(conn, "2024-06-28", "t2", 11)   # upsert, not duplicate
    assert db.stored_settlements(conn) == ["2024-06-14", "2024-06-28"]


def test_prune_removes_old_snapshots_only_and_keeps_facts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    facts = _rows(("AA", "2024-06-14", "ALPHA", 1))
    db.upsert_securities(conn, facts)
    db.replace_settlement(conn, "2024-06-14", facts)
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM short_interest").fetchone()[0] == 1  # untouched
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_db_schema.py tests/test_finra_short_interest_db_write.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'finra_short_interest.db'`.

- [ ] **Step 4: Write `db.py` (schema + writes; views added in Task 3)**

Create `finra_short_interest/db.py`:

```python
# finra_short_interest/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities",
           "replace_settlement", "record_settlement", "write_snapshot",
           "stored_settlements", "prune"]

_SI_COLS = ["symbol", "settlement_date", "current_short_qty",
            "previous_short_qty", "avg_daily_volume", "days_to_cover",
            "change_pct", "revision_flag", "market_class"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    symbol     TEXT PRIMARY KEY,
    issue_name TEXT,                       -- newest issueName seen
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS short_interest (
    symbol             TEXT NOT NULL REFERENCES securities(symbol),
    settlement_date    TEXT NOT NULL,      -- YYYY-MM-DD
    current_short_qty  INTEGER NOT NULL,
    previous_short_qty INTEGER,
    avg_daily_volume   INTEGER,
    days_to_cover      REAL,               -- FINRA-computed daysToCoverQuantity
    change_pct         REAL,               -- FINRA-computed changePercent
    revision_flag      TEXT,
    market_class       TEXT,               -- marketClassCode (NNM/OTC/etc.)
    PRIMARY KEY (symbol, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_si_settlement ON short_interest(settlement_date);
CREATE INDEX IF NOT EXISTS ix_si_symbol     ON short_interest(symbol);
CREATE TABLE IF NOT EXISTS settlements (
    settlement_date TEXT PRIMARY KEY,
    fetched_at      TEXT NOT NULL,
    row_count       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    settlement_count INTEGER NOT NULL,
    row_count        INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables and indexes. Idempotent. (Views are added in Task 3.)"""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the symbol dimension: extend first_seen/last_seen to the min/max
    settlement date seen, and refresh issue_name to the newest (largest
    settlement_date) name observed."""
    params = [{"symbol": r["symbol"], "issue": r.get("issue_name"),
               "d": r["settlement_date"]} for r in rows]
    conn.executemany(
        """INSERT INTO securities (symbol, issue_name, first_seen, last_seen)
           VALUES (:symbol, :issue, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen),
             issue_name = CASE WHEN excluded.last_seen >= securities.last_seen
                               THEN excluded.issue_name
                               ELSE securities.issue_name END""",
        params,
    )
    conn.commit()


def replace_settlement(conn, settlement_date: str, rows: list[dict]) -> int:
    """Delete all short_interest rows for this settlement, then bulk-insert the
    given rows. Replace (not upsert) so a FINRA repost that drops a symbol
    leaves no orphan. Dedupes within the batch by (symbol, settlement_date).
    Returns rows written."""
    by_key = {(r["symbol"], r["settlement_date"]): r for r in rows}
    conn.execute("DELETE FROM short_interest WHERE settlement_date = ?",
                 (settlement_date,))
    placeholders = ", ".join(":" + c for c in _SI_COLS)
    params = [{c: r.get(c) for c in _SI_COLS} for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO short_interest ({', '.join(_SI_COLS)}) "
        f"VALUES ({placeholders})", params)
    conn.commit()
    return len(by_key)


def record_settlement(conn, settlement_date: str, fetched_at: str,
                      row_count: int) -> None:
    """Upsert one settlement's provenance row."""
    conn.execute(
        """INSERT INTO settlements (settlement_date, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(settlement_date) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (settlement_date, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, settlement_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, settlement_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, settlement_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_settlements(conn) -> list:
    """All ingested settlement dates, sorted ascending (ISO dates sort
    chronologically)."""
    return [r[0] for r in conn.execute(
        "SELECT settlement_date FROM settlements ORDER BY settlement_date")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Short-interest history is NOT snapshot-scoped, so this is a single-table
    delete of snapshot headers only — it must NOT cascade into short_interest."""
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

- [ ] **Step 5: Run both tests to verify they pass**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_db_schema.py tests/test_finra_short_interest_db_write.py -q`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add finra_short_interest/db.py tests/test_finra_short_interest_db_schema.py tests/test_finra_short_interest_db_write.py
git commit -m "feat(short_interest): SQLite schema + replace-by-settlement writes"
```

---

### Task 3: `db.py` — squeeze views

**Files:**
- Modify: `finra_short_interest/db.py` (add `_VIEWS`; extend `ensure_schema`)
- Test: `tests/test_finra_short_interest_db_views.py`
- Modify: `tests/test_finra_short_interest_db_schema.py` (assert views exist)

**Interfaces:**
- Consumes: the `short_interest` table (Task 2).
- Produces (SQLite views): `v_latest`, `v_high_days_to_cover`, `v_short_interest_spikes`, `v_symbol_history`.

- [ ] **Step 1: Write the failing views test**

Create `tests/test_finra_short_interest_db_views.py`:

```python
# tests/test_finra_short_interest_db_views.py
import pytest

from finra_short_interest import db

_COLS = ["symbol", "settlement_date", "current_short_qty", "previous_short_qty",
         "avg_daily_volume", "days_to_cover", "change_pct", "revision_flag",
         "market_class"]


def _row(symbol, sdate, cur, adv=200000, dtc=1.0, prev=None):
    return {"symbol": symbol, "settlement_date": sdate,
            "current_short_qty": cur, "previous_short_qty": prev,
            "avg_daily_volume": adv, "days_to_cover": dtc, "change_pct": 0.0,
            "revision_flag": None, "market_class": "NNM"}


def _insert(conn, rows):
    """Insert directly (bypassing replace_settlement's delete-by-date) so
    multiple symbols can share a settlement date."""
    db.upsert_securities(conn, [dict(r, issue_name="X") for r in rows])
    conn.executemany(
        f"INSERT INTO short_interest ({','.join(_COLS)}) "
        f"VALUES ({','.join(':' + c for c in _COLS)})", rows)
    conn.commit()


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_latest_only_max_settlement_and_liquid():
    conn = _fresh()
    _insert(conn, [_row("A", "2024-06-14", 100, adv=200000),
                   _row("A", "2024-06-28", 120, adv=200000)])
    _insert(conn, [_row("B", "2024-06-28", 999, adv=50000)])   # illiquid -> out
    rows = conn.execute(
        "SELECT symbol, settlement_date, current_short_qty FROM v_latest"
    ).fetchall()
    assert len(rows) == 1
    assert tuple(rows[0]) == ("A", "2024-06-28", 120)


def test_v_high_days_to_cover_threshold_and_liquidity():
    conn = _fresh()
    _insert(conn, [_row("A", "2024-06-28", 100, adv=200000, dtc=6.0)])  # in
    _insert(conn, [_row("B", "2024-06-28", 100, adv=200000, dtc=4.0)])  # dtc<5 out
    _insert(conn, [_row("C", "2024-06-28", 100, adv=50000, dtc=9.0)])   # illiquid out
    syms = {r[0] for r in conn.execute(
        "SELECT symbol FROM v_high_days_to_cover")}
    assert syms == {"A"}


def test_v_short_interest_spikes_prior_and_trailing_average():
    conn = _fresh()
    # four trailing settlements at 100000, latest jumps to 300000, prev=150000
    _insert(conn, [
        _row("A", "2024-04-15", 100000, adv=200000),
        _row("A", "2024-04-30", 100000, adv=200000),
        _row("A", "2024-05-15", 100000, adv=200000),
        _row("A", "2024-05-31", 100000, adv=200000),
        _row("A", "2024-06-14", 300000, adv=200000, prev=150000),
    ])
    cur, prev, si_change, base, base_ratio = conn.execute(
        "SELECT current_short_qty, previous_short_qty, si_change, base, "
        "base_ratio FROM v_short_interest_spikes WHERE symbol='A'").fetchone()
    assert (cur, prev) == (300000, 150000)
    assert si_change == pytest.approx(2.0)     # 300000 / 150000 (file's prior)
    assert base == pytest.approx(100000.0)     # trailing settlement average
    assert base_ratio == pytest.approx(3.0)    # 300000 / 100000


def test_v_symbol_history_returns_full_series():
    conn = _fresh()
    _insert(conn, [_row("A", "2024-06-14", 100), _row("A", "2024-06-28", 120)])
    dates = [r[0] for r in conn.execute(
        "SELECT settlement_date FROM v_symbol_history WHERE symbol='A' "
        "ORDER BY settlement_date")]
    assert dates == ["2024-06-14", "2024-06-28"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_db_views.py -q`
Expected: FAIL with `sqlite3.OperationalError: no such table: v_latest` (view not yet created).

- [ ] **Step 3: Add the `_VIEWS` constant to `db.py`**

In `finra_short_interest/db.py`, add this constant immediately after the `_SCHEMA = """..."""` block:

```python
_VIEWS = """
-- per-symbol time series (drill-down)
CREATE VIEW IF NOT EXISTS v_symbol_history AS
SELECT symbol, settlement_date, current_short_qty, avg_daily_volume,
       days_to_cover, change_pct
FROM short_interest;

-- (1) latest-settlement leaderboard, liquid names only
--     (order by current_short_qty or days_to_cover). The liquidity floor
--     mirrors short_volume's v_latest; illiquid names remain in v_symbol_history.
CREATE VIEW IF NOT EXISTS v_latest AS
SELECT symbol, settlement_date, current_short_qty, avg_daily_volume,
       days_to_cover, change_pct, market_class
FROM short_interest
WHERE settlement_date = (SELECT MAX(settlement_date) FROM short_interest)
  AND avg_daily_volume >= 100000;

-- (2) squeeze shortlist: high open short AND thin liquidity to buy it back
CREATE VIEW IF NOT EXISTS v_high_days_to_cover AS
SELECT symbol, settlement_date, current_short_qty, avg_daily_volume,
       days_to_cover, change_pct, market_class
FROM short_interest
WHERE settlement_date = (SELECT MAX(settlement_date) FROM short_interest)
  AND avg_daily_volume >= 100000
  AND days_to_cover >= 5.0;

-- (3) building short interest on the latest settlement, measured BOTH against
--     the file's own previous_short_qty AND the symbol's trailing settlement
--     average (~prior quarter: the 6 settlements before this one).
CREATE VIEW IF NOT EXISTS v_short_interest_spikes AS
WITH w AS (
  SELECT symbol, settlement_date, current_short_qty, previous_short_qty,
         avg_daily_volume,
         AVG(current_short_qty) OVER (
           PARTITION BY symbol ORDER BY settlement_date
           ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING) AS base
  FROM short_interest)
SELECT w.symbol, w.settlement_date, w.current_short_qty, w.previous_short_qty,
       CAST(w.current_short_qty AS REAL)
         / NULLIF(w.previous_short_qty, 0) AS si_change,
       w.base,
       CASE WHEN w.base > 0
            THEN CAST(w.current_short_qty AS REAL) / w.base END AS base_ratio
FROM w
WHERE w.settlement_date = (SELECT MAX(settlement_date) FROM short_interest)
  AND w.avg_daily_volume >= 100000;
"""
```

- [ ] **Step 4: Extend `ensure_schema` to build the views**

In `finra_short_interest/db.py`, replace the `ensure_schema` function with:

```python
def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()
```

- [ ] **Step 5: Extend the schema test to assert views exist**

In `tests/test_finra_short_interest_db_schema.py`, append to the end of `test_ensure_schema_is_idempotent_and_creates_tables` (after the tables assertion):

```python
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_latest", "v_high_days_to_cover", "v_short_interest_spikes",
            "v_symbol_history"} <= views
```

- [ ] **Step 6: Run the views + schema tests to verify they pass**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_db_views.py tests/test_finra_short_interest_db_schema.py -q`
Expected: PASS (5 passed).

- [ ] **Step 7: Commit**

```bash
git add finra_short_interest/db.py tests/test_finra_short_interest_db_views.py tests/test_finra_short_interest_db_schema.py
git commit -m "feat(short_interest): squeeze / days-to-cover views"
```

---

### Task 4: `run.py` — settlement enumeration + orchestration + CLI

**Files:**
- Create: `finra_short_interest/run.py`
- Test: `tests/test_finra_short_interest_run.py`

**Interfaces:**
- Consumes: `db` (Task 2/3), `fetch.fetch_settlement` (Task 1).
- Produces:
  - `settlement_dates(start: str, end: str) -> list[str]`
  - `_default_start(now_dt, days=_DEFAULT_LOOKBACK_DAYS) -> str`
  - `run(db_path, start=None, keep_days=None, full=False, fetch_settlement=fetch.fetch_settlement, now_iso=None) -> tuple[int, int, int]` (snapshot_id, settlement_count, row_count)
  - `main(argv=None)` — CLI `prog="short_interest"`.

- [ ] **Step 1: Write the failing run test**

Create `tests/test_finra_short_interest_run.py`:

```python
# tests/test_finra_short_interest_run.py
from datetime import datetime, timezone

from finra_short_interest import db, run as run_mod

NOW = "2024-08-15T00:00:00+00:00"


def _rows(s):
    """One liquid row whose settlement_date == s."""
    return [{"symbol": "AAL", "issue_name": "AMERICAN AIRLINES",
             "settlement_date": s, "current_short_qty": 1500000,
             "previous_short_qty": 1200000, "avg_daily_volume": 500000,
             "days_to_cover": 3.0, "change_pct": 25.0,
             "revision_flag": None, "market_class": "NNM"}]


def test_settlement_dates_rolls_weekend_back_to_friday():
    # 2024-06-15 is Saturday -> 06-14; 2024-06-30 is Sunday -> 06-28;
    # 2024-07-15 Mon, 2024-07-31 Wed -> unchanged.
    assert run_mod.settlement_dates("2024-06-01", "2024-07-31") == [
        "2024-06-14", "2024-06-28", "2024-07-15", "2024-07-31"]


def test_settlement_dates_bounds_are_inclusive_and_clipped():
    # start after the 15th drops that month's mid-month settlement.
    assert run_mod.settlement_dates("2024-06-20", "2024-07-16") == [
        "2024-06-28", "2024-07-15"]


def test_default_start_is_about_twelve_months_back():
    now = datetime(2026, 7, 3, tzinfo=timezone.utc)
    assert run_mod._default_start(now, days=365) == "2025-07-03"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"2024-06-14"}

    def fetch_settlement(s):
        return _rows(s) if s in published else None

    dbp = str(tmp_path / "si.db")
    _, sc, rc = run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                            fetch_settlement=fetch_settlement)
    assert (sc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT COUNT(*) FROM short_interest").fetchone()[0] == 1


def test_run_incremental_skips_stored_refetches_last_two(tmp_path):
    # range 2024-06-01..2024-08-15 -> settlements:
    #   06-14, 06-28, 07-15, 07-31, 08-15  (five)
    def make_fs(sink):
        def fetch_settlement(s):
            sink.append(s)
            return _rows(s)
        return fetch_settlement

    dbp = str(tmp_path / "si.db")
    first = []
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                fetch_settlement=make_fs(first))
    assert len(first) == 5

    second = []
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                fetch_settlement=make_fs(second))
    assert second == ["2024-07-31", "2024-08-15"]   # only trailing two refetched


def test_run_full_refetches_every_settlement(tmp_path):
    def make_fs(sink):
        def fetch_settlement(s):
            sink.append(s)
            return _rows(s)
        return fetch_settlement

    dbp = str(tmp_path / "si.db")
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW, fetch_settlement=make_fs([]))
    second = []
    run_mod.run(dbp, start="2024-06-01", full=True, now_iso=NOW,
                fetch_settlement=make_fs(second))
    assert len(second) == 5


def test_run_skips_failing_settlement_and_logs_class_only(tmp_path, capsys):
    def fetch_settlement(s):
        if s == "2024-06-14":
            raise RuntimeError("boom-secret")
        if s == "2024-06-28":
            return _rows(s)
        return None

    dbp = str(tmp_path / "si.db")
    _, sc, _ = run_mod.run(dbp, start="2024-06-01",
                           now_iso="2024-07-01T00:00:00+00:00",
                           fetch_settlement=fetch_settlement)
    assert sc == 1
    err = capsys.readouterr().err
    assert "2024-06-14" in err
    assert "RuntimeError" in err
    assert "boom-secret" not in err          # secret-hygiene: no str(e)


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "si.db")
    _, sc, rc = run_mod.run(dbp, start="2024-06-01",
                            now_iso="2024-06-20T00:00:00+00:00",
                            fetch_settlement=lambda s: None)
    assert (sc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT settlement_count, row_count FROM snapshots").fetchone()) == (0, 0)


def test_run_keep_days_prunes_old_snapshots(tmp_path):
    dbp = str(tmp_path / "si.db")
    run_mod.run(dbp, start="2024-06-01",
                now_iso="2024-06-20T00:00:00+00:00",
                fetch_settlement=lambda s: None)
    conn = db.connect(dbp)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 0, 0)
    conn.close()
    run_mod.run(dbp, start="2024-06-01",
                now_iso="2024-06-20T00:00:00+00:00", keep_days=30,
                fetch_settlement=lambda s: None)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE captured_at < '2020-01-01'"
    ).fetchone()[0] == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_run.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'finra_short_interest.run'`.

- [ ] **Step 3: Write `run.py`**

Create `finra_short_interest/run.py`:

```python
# finra_short_interest/run.py
import argparse
import sys
from datetime import date as date_cls, datetime, timedelta, timezone

from finra_short_interest import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored settlements
# so a FINRA repost/revision is re-absorbed by replace_settlement. --full
# re-ingests every settlement in range.
_REFETCH_SETTLEMENTS = 2
_DEFAULT_LOOKBACK_DAYS = 365       # ~12 months (~24 settlements)


def _last_day_of_month(year: int, month: int) -> date_cls:
    if month == 12:
        return date_cls(year, 12, 31)
    return date_cls(year, month + 1, 1) - timedelta(days=1)


def _roll_back_to_weekday(d: date_cls) -> date_cls:
    """FINRA settlement dates fall on business days; a nominal 15th / month-end
    landing on a weekend rolls back to the prior Friday. Holiday shifts are not
    modeled — a wrong guess simply 404s and is skipped (and, being unstored, is
    retried on every later run until it publishes)."""
    wd = d.weekday()                # Mon=0 .. Sun=6
    if wd == 5:                     # Saturday -> Friday
        return d - timedelta(days=1)
    if wd == 6:                     # Sunday -> Friday
        return d - timedelta(days=2)
    return d


def settlement_dates(start: str, end: str) -> list[str]:
    """The FINRA bi-monthly settlement schedule in [start, end] inclusive: the
    mid-month (15th) and month-end of every month, each rolled back to the prior
    weekday. Returns 'YYYY-MM-DD' strings, ascending and de-duplicated."""
    s = date_cls.fromisoformat(start)
    e = date_cls.fromisoformat(end)
    out: list[str] = []
    year, month = s.year, s.month
    while date_cls(year, month, 1) <= e:
        mid = _roll_back_to_weekday(date_cls(year, month, 15))
        eom = _roll_back_to_weekday(_last_day_of_month(year, month))
        for d in (mid, eom):
            if s <= d <= e:
                out.append(d.isoformat())
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return sorted(set(out))


def _default_start(now_dt, days: int = _DEFAULT_LOOKBACK_DAYS) -> str:
    """'YYYY-MM-DD' for `days` before now_dt's date."""
    return (now_dt.date() - timedelta(days=days)).isoformat()


def run(db_path, start=None, keep_days=None, full=False,
        fetch_settlement=fetch.fetch_settlement,
        now_iso=None) -> tuple[int, int, int]:
    """Ingest FINRA bi-monthly short-interest files into SQLite. Enumerate
    settlement dates from `start` (default: ~12 months back) through today;
    ingest new settlements and re-fetch the trailing _REFETCH_SETTLEMENTS
    already-stored ones (all of them when full=True). A 403/404 (absent /
    not-yet-published settlement) is skipped. Any per-settlement failure rolls
    back and continues. Returns (snapshot_id, settlement_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_date = now_dt.date().isoformat()
    all_settlements = settlement_dates(start, end_date)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_settlements(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_SETTLEMENTS:])   # newest stored settlements

        settlement_count = 0
        total_rows = 0
        for s in all_settlements:
            if not full and s in stored_set and s not in refetch:
                continue
            try:
                rows = fetch_settlement(s)
                if rows is None:                  # 403/404 -> absent/unpublished
                    continue
                db.upsert_securities(conn, rows)
                written = db.replace_settlement(conn, s, rows)
                db.record_settlement(conn, s, now_iso, written)
                total_rows += written
                settlement_count += 1
            except Exception as e:  # skip-and-continue on any per-settlement failure
                # Roll back this settlement's uncommitted writes, then log ONLY
                # the exception class — never str(e)/e.url.
                conn.rollback()
                print(f"warning: skipping {s}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, settlement_count,
                                        total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, settlement_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="short_interest",
        description="Pull FINRA bi-monthly equity short interest into SQLite")
    p.add_argument("--db", default="short_interest.db")
    p.add_argument("--start", default=None,
                   help="earliest settlement date YYYY-MM-DD "
                        "(default: ~12 months back; listed coverage starts "
                        "2021-06, earlier is OTC-only)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every settlement in range, ignoring the "
                        "incremental skip")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches short-interest history)")
    a = p.parse_args(argv)
    _, sc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} short-interest rows across {sc} settlements into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_finra_short_interest_run.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add finra_short_interest/run.py tests/test_finra_short_interest_run.py
git commit -m "feat(short_interest): settlement enumeration, orchestration, CLI"
```

---

### Task 5: Register the screener + update docs

**Files:**
- Modify: `registry.py`
- Modify: `tests/test_registry.py`
- Modify: `docs/ROADMAP.md`

**Interfaces:**
- Consumes: `finra_short_interest.run.main` (Task 4).
- Produces: `registry.REGISTRY["short_interest"]` dispatch entry.

- [ ] **Step 1: Write the failing registry test**

In `tests/test_registry.py`, add at the end of the file:

```python
def test_dispatch_lists_short_interest():
    import registry
    assert "short_interest" in registry.REGISTRY
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_registry.py::test_dispatch_lists_short_interest -q`
Expected: FAIL with `AssertionError` (`"short_interest"` not in REGISTRY).

- [ ] **Step 3: Register the screener**

In `registry.py`, add the import alongside the other screener imports (after the `short_volume` import line):

```python
from finra_short_interest.run import main as short_interest_main
```

And add the entry to the `REGISTRY` dict (after the `"short_volume"` line):

```python
    "short_interest": short_interest_main,
```

- [ ] **Step 4: Run the registry test to verify it passes**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest tests/test_registry.py -q`
Expected: PASS (all registry tests pass).

- [ ] **Step 5: Update `docs/ROADMAP.md`**

Make these edits in `docs/ROADMAP.md`:

**(a)** In the **Built ✅** table, add a row after the `short_volume` row:

```markdown
| `short_interest` | FINRA Equity Short Interest | Settled short position / days-to-cover / squeeze | [spec](superpowers/specs/2026-07-03-finra-short-interest-screener-design.md) | [plan](superpowers/plans/2026-07-03-finra-short-interest-screener.md) |
```

**(b)** In the **Spec'd — data screeners 📝** "Deepen publishers already wired in" table, **delete** the `short_interest` row:

```markdown
| 🟢 | `short_interest` | FINRA Equity Short Interest | Settled short interest, days-to-cover, squeeze | [spec](superpowers/specs/2026-07-03-finra-short-interest-screener-design.md) |
```

**(c)** In the **Recommended build order** list, replace item 2:

```markdown
2. ~~**`short_interest`**~~ — ✅ **Built** (see Built table). Cloned the `short_volume` CDN pattern; adds squeeze/days-to-cover. [plan](superpowers/plans/2026-07-03-finra-short-interest-screener.md)
```

- [ ] **Step 6: Run the full test suite (regression gate)**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -m pytest -q`
Expected: PASS — the entire suite green, including all `test_finra_short_interest_*` and `test_registry`.

- [ ] **Step 7: Smoke-test the CLI end to end**

Run: `cd /Users/ninkuk/Desktop/agentic-trading-bot && python -c "import registry; print('short_interest' in registry.REGISTRY)" && python -m finra_short_interest.run --help`
Expected: prints `True`, then the argparse help for `prog=short_interest` listing `--db`, `--start`, `--full`, `--keep-days`.

> **Optional live confirmation (network, do once at build time — Global Constraint 🟡):** run `python -m finra_short_interest.run --db /tmp/si_smoke.db --start 2024-06-01` and confirm rows land, then spot-check the parser against a real file. If the live column order or `settlementDate` format differs from the documented layout, fix `parse_file`'s positional unpack and re-run the Task 1 tests before proceeding.

- [ ] **Step 8: Commit**

```bash
git add registry.py tests/test_registry.py docs/ROADMAP.md
git commit -m "feat(short_interest): register screener + mark Built in roadmap"
```

---

## Self-Review

**1. Spec coverage:**

| Spec item | Task |
|---|---|
| CDN bulk file primary, pipe-delimited, descriptive UA | Task 1 (`fetch.py`) |
| `settlement_url`, `parse_file`, `fetch_settlement` (403/404 → None) | Task 1 |
| Reuse `_norm_date` / `_num`; keep `days_to_cover` / `change_pct` as stored | Task 1 |
| `securities` (with `issue_name`), `short_interest`, `settlements`, `snapshots` schema + indexes | Task 2 |
| `upsert_securities` (issue-name refresh + first/last_seen), `replace_settlement`, `record_settlement`, `write_snapshot`, `stored_settlements`, `prune` (snapshots only) | Task 2 |
| Views `v_latest`, `v_high_days_to_cover`, `v_short_interest_spikes`, `v_symbol_history`; thresholds baked in | Task 3 |
| Settlement-date enumeration (~15th + month-end), `_default_start` ~12 mo, `_REFETCH_SETTLEMENTS=2`, `--full`, incremental skip, secret-hygiene logging | Task 4 |
| CLI `prog="short_interest"`, `--db`/`--start`/`--full`/`--keep-days` | Task 4 |
| Register `"short_interest"`; no `.env.example` change | Task 5 |
| Coverage-cutoff / publication-delay documentation | Global Constraints + `main` help text + Task 4 docstrings |
| Test files mirroring `test_finra_shorts_*` + registry test | Tasks 1–5 |

Non-goals (POST API, float joins, pre-2021 backfill, merging with `short_volume`, OAuth2) are correctly **not** implemented.

**2. Placeholder scan:** No TBD/TODO/"add error handling"/"similar to Task N" — every step shows complete code or an exact command with expected output.

**3. Type consistency:** Row-dict keys (`symbol, issue_name, settlement_date, current_short_qty, previous_short_qty, avg_daily_volume, days_to_cover, change_pct, revision_flag, market_class`) are identical across `parse_file` (Task 1), `_SI_COLS` (Task 2), the view columns (Task 3), and the run-test `_rows` fixtures (Task 4). Function names (`settlement_url`, `fetch_settlement`, `replace_settlement`, `record_settlement`, `stored_settlements`, `settlement_dates`) are used consistently everywhere.

**One deliberate divergence from the spec, flagged for the reviewer:** the spec's `settlement_dates` says "the ~15th and month-end"; this plan generates the literal 15th and last calendar day **rolled back to the prior weekday** (Sat→Fri, Sun→Fri), because FINRA settlement files are named by a business day (e.g. 2024-06-15 was a Saturday → the real file is `shrt20240614.csv`). Holiday shifts are **not** modeled — a wrong guess 404s and, being unstored, is retried on every later run until it publishes. This is documented in the `_roll_back_to_weekday` docstring and is the safe failure mode the spec's 403/404-skip design already assumes.
