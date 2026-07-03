# SEC Fails-to-Deliver (FTD) Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a sixth screener, `ftd`, that ingests the SEC's semi-monthly fails-to-deliver ZIP files into SQLite and exposes screener views (latest leaderboard, Reg SHO persistence proxy, spikes, per-security history).

**Architecture:** A new `ftd_screener/` package (`fetch.py` / `db.py` / `run.py`) mirroring `cftc_screener`, reusing `screener_common.connect` (WAL) and `http_client` bounded-backoff. Unlike CFTC's per-instrument Socrata queries, FTD is a periodic full-universe bulk dump: you ingest **time periods** (half-months), each a ZIP holding every security's fails. Fact table `fails` is keyed by `(cusip, settlement_date)` and **replaced per period** (not snapshot-scoped); `snapshots` records run provenance only.

**Tech Stack:** Python 3, stdlib only (`urllib`, `zipfile`, `io`, `calendar`, `sqlite3`, `argparse`), `pytest`. No new dependencies.

## Global Constraints

- **Python: stdlib only.** No new third-party dependencies (matches the existing screeners).
- **HTTP:** reuse `http_client.http_get` for backoff. SEC throttles with **HTTP 403** — retry set is `{403, 429, 503}`. Send `User-Agent: "agentic-trading-bot ninadk.dev@gmail.com"` (same as `edgar_screener`).
- **File URL pattern:** `https://www.sec.gov/files/data/fails-deliver-data/cnsfails{YYYYMM}{a|b}.zip` — `a` = settlement days 01–15, `b` = 16–end-of-month.
- **Leak-safe logging:** on any per-period failure, `conn.rollback()` and print only `type(e).__name__` to stderr — never `str(e)` or `e.url`.
- **Prune is single-table:** `prune()` deletes old `snapshots` rows only. **Never cascade into `fails`** — fail history is the permanent store (CFTC/FRED convention).
- **Stable key is CUSIP**, not SYMBOL. SYMBOL may be blank/reused.
- **Dates:** store `settlement_date` as `YYYY-MM-DD`. `now_iso` is a UTC `isoformat()` string, injectable for tests.
- **Design-spec reference:** `docs/superpowers/specs/2026-07-03-ftd-screener-design.md`.

---

### Task 1: `fetch.py` — pure parsing + URL/date helpers

**Files:**
- Create: `ftd_screener/__init__.py` (empty)
- Create: `ftd_screener/fetch.py`
- Test: `tests/test_ftd_fetch.py`

**Interfaces:**
- Produces:
  - `FILES_BASE: str` = `"https://www.sec.gov/files/data/fails-deliver-data"`
  - `period_url(period: str, base: str = FILES_BASE) -> str`
  - `settlement_bounds(period: str) -> tuple[str, str]` — `(start_YYYY-MM-DD, end_YYYY-MM-DD)`
  - `parse_file(text: str) -> tuple[list[dict], int | None]` — `(rows, trailer_count)`; each row dict has keys `cusip, settlement_date, symbol, quantity, price, description, dollar_value`

- [ ] **Step 1: Create the package marker**

Create `ftd_screener/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing test for parsing + helpers**

Create `tests/test_ftd_fetch.py`:

```python
# tests/test_ftd_fetch.py
import pytest

from ftd_screener.fetch import (
    parse_file, period_url, settlement_bounds,
)

SAMPLE = (
    "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n"
    "20250501|B38564108|CMBT|111|CMB.TECH NV (BEL)|9.51\n"
    "20250502|000000000|BLANKQTY||CORP|\n"          # blank quantity -> skipped
    "20250502|C00948205|AGRI|12336|AGRIFORCE|2.13\n"
    "20250505||NOCUSIP|50|NO CUSIP CO|1.00\n"        # blank cusip -> skipped
    "Trailer record count 2\n"
    "Trailer total quantity of shares 12447\n"
)


def test_parse_file_maps_and_coerces():
    rows, trailer = parse_file(SAMPLE)
    assert trailer == 2
    assert len(rows) == 2                       # blank-qty and blank-cusip skipped
    assert rows[0] == {
        "cusip": "B38564108", "settlement_date": "2025-05-01",
        "symbol": "CMBT", "quantity": 111, "price": 9.51,
        "description": "CMB.TECH NV (BEL)",
        "dollar_value": pytest.approx(111 * 9.51),
    }
    assert rows[1]["cusip"] == "C00948205"
    assert rows[1]["dollar_value"] == pytest.approx(12336 * 2.13)


def test_parse_file_blank_price_gives_none():
    rows, trailer = parse_file("20250501|X1|SYM|100|A NAME|\n")
    assert trailer is None                      # no trailer line present
    assert rows[0]["price"] is None
    assert rows[0]["dollar_value"] is None


def test_parse_file_header_row_is_dropped():
    # header's SETTLEMENT DATE is non-numeric -> filtered; QUANTITY cell non-int too
    rows, _ = parse_file(
        "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n")
    assert rows == []


def test_period_url():
    assert period_url("202505a") == (
        "https://www.sec.gov/files/data/fails-deliver-data/cnsfails202505a.zip")


def test_settlement_bounds_first_half():
    assert settlement_bounds("202505a") == ("2025-05-01", "2025-05-15")


def test_settlement_bounds_second_half_uses_month_end():
    assert settlement_bounds("202502b") == ("2025-02-16", "2025-02-28")  # non-leap
    assert settlement_bounds("202405b") == ("2024-05-16", "2024-05-31")
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_ftd_fetch.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftd_screener.fetch'`.

- [ ] **Step 4: Write the implementation**

Create `ftd_screener/fetch.py`:

```python
# ftd_screener/fetch.py
import calendar

FILES_BASE = "https://www.sec.gov/files/data/fails-deliver-data"


def period_url(period: str, base: str = FILES_BASE) -> str:
    """URL of the ZIP for a period id like '202505a'."""
    return f"{base}/cnsfails{period}.zip"


def settlement_bounds(period: str) -> tuple[str, str]:
    """(start, end) YYYY-MM-DD dates a period covers. 'a' -> 01..15,
    'b' -> 16..last-day-of-month."""
    year, month, half = int(period[:4]), int(period[4:6]), period[6]
    last = calendar.monthrange(year, month)[1]
    if half == "a":
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-15"
    return f"{year:04d}-{month:02d}-16", f"{year:04d}-{month:02d}-{last:02d}"


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


def parse_file(text: str) -> tuple[list[dict], int | None]:
    """Parse an FTD file body into (rows, trailer_count).

    Pipe-delimited: SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY|DESCRIPTION|PRICE.
    Stops at the first 'Trailer' line (capturing 'Trailer record count N').
    The header line is dropped naturally (its non-numeric date/quantity fail
    coercion). Rows missing a CUSIP, a valid date, or a valid quantity are
    skipped. dollar_value = quantity * price (None if price missing)."""
    rows: list[dict] = []
    trailer_count: int | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("Trailer"):
            if "record count" in line:
                trailer_count = _num(line.rsplit(" ", 1)[-1], int)
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue
        settle, cusip, symbol, qty, desc, price = (p.strip() for p in parts[:6])
        date = _norm_date(settle)
        quantity = _num(qty, int)
        if not cusip or date is None or quantity is None:
            continue
        p = _num(price, float)
        rows.append({
            "cusip": cusip, "settlement_date": date,
            "symbol": symbol or None, "quantity": quantity, "price": p,
            "description": desc or None,
            "dollar_value": (quantity * p) if p is not None else None,
        })
    return rows, trailer_count
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_ftd_fetch.py -q`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add ftd_screener/__init__.py ftd_screener/fetch.py tests/test_ftd_fetch.py
git commit -m "feat(ftd): FTD file parsing + URL/date helpers"
```

---

### Task 2: `fetch.py` — ZIP download + `fetch_period` (backoff, 404→None)

**Files:**
- Modify: `ftd_screener/fetch.py`
- Test: `tests/test_ftd_fetch.py` (append)

**Interfaces:**
- Consumes: `parse_file`, `period_url` (Task 1); `http_client.http_get`.
- Produces:
  - `_urlopen` — module-level bytes opener (SEC `User-Agent`)
  - `_http_get(url, opener=_urlopen, attempts=5, base_delay=1.0, sleep=time.sleep) -> bytes`
  - `fetch_period(period: str, get=_http_get, opener=None) -> tuple[list[dict], int | None] | None` — `None` on HTTP 404

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ftd_fetch.py`:

```python
import io
import urllib.error
import zipfile

from ftd_screener.fetch import _http_get, fetch_period


def _zip_bytes(member: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, text)
    return buf.getvalue()


def test_fetch_period_reads_single_member_regardless_of_name():
    blob = _zip_bytes("cnsfails202505a", SAMPLE)   # member name != inferable

    def fake_get(url, opener=None):
        assert url.endswith("cnsfails202505a.zip")
        return blob

    rows, trailer = fetch_period("202505a", get=fake_get)
    assert trailer == 2 and len(rows) == 2


def test_fetch_period_returns_none_on_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    assert fetch_period("209901a", get=fake_get) is None


def test_fetch_period_reraises_non_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 500, "err", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_period("202505a", get=fake_get)


def test_http_get_retries_on_403_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 403, "throttle", {}, None)
        return b"OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == b"OK"
    assert slept == [1.0]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_ftd_fetch.py -q`
Expected: FAIL — `ImportError: cannot import name '_http_get'` (and `fetch_period`).

- [ ] **Step 3: Write the implementation**

Add to the top imports of `ftd_screener/fetch.py`:

```python
import io
import time
import urllib.error
import urllib.request
import zipfile

import http_client
```

Append to `ftd_screener/fetch.py` (after `parse_file`):

```python
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({403, 429, 503})  # SEC throttles with 403 (like EDGAR)
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0


def _bytes_opener(headers: dict, timeout: int = 60):
    """opener(url)->bytes for binary (ZIP) downloads. Unlike
    http_client.make_opener, does NOT decode the body."""
    def opener(url: str) -> bytes:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return opener


_urlopen = _bytes_opener(_UA)


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> bytes:
    """GET raw bytes with bounded backoff, retrying SEC throttling (403/429/503)
    and transient network errors. Non-retryable HTTP errors (e.g. 404) raise at
    once, preserving fetch_period's 404 -> None handling."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_period(period: str, get=_http_get, opener=None):
    """Download + parse one period's ZIP. Returns (rows, trailer_count), or
    None on HTTP 404 (period not yet published). Reads whichever single member
    the archive contains; decodes with errors='replace'."""
    op = opener if opener is not None else _urlopen
    try:
        blob = get(period_url(period), opener=op)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        member = zf.namelist()[0]
        text = zf.read(member).decode("utf-8", "replace")
    return parse_file(text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_ftd_fetch.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add ftd_screener/fetch.py tests/test_ftd_fetch.py
git commit -m "feat(ftd): ZIP fetch_period with 403-backoff and 404->None"
```

---

### Task 3: `db.py` — schema + writers

**Files:**
- Create: `ftd_screener/db.py`
- Test: `tests/test_ftd_db_write.py`, `tests/test_ftd_db_schema.py`

**Interfaces:**
- Consumes: `screener_common.connect`.
- Produces:
  - `connect(path)` (re-exported), `ensure_schema(conn)`
  - `upsert_securities(conn, rows: list[dict]) -> None`
  - `replace_period(conn, period: str, rows: list[dict]) -> int`
  - `record_period(conn, period, bounds: tuple[str, str], fetched_at, row_count, trailer_count) -> None`
  - `write_snapshot(conn, captured_at, period_count, row_count) -> int`
  - `stored_periods(conn) -> list[str]` (sorted ascending)
  - `prune(conn, keep_days, now_iso) -> int`

- [ ] **Step 1: Write the failing schema test**

Create `tests/test_ftd_db_schema.py`:

```python
# tests/test_ftd_db_schema.py
from ftd_screener import db


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)            # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"securities", "fails", "periods", "snapshots"} <= tables
```

- [ ] **Step 2: Write the failing writer tests**

Create `tests/test_ftd_db_write.py`:

```python
# tests/test_ftd_db_write.py
from ftd_screener import db


def _rows(*specs):
    """spec tuples: (cusip, settlement_date, symbol, quantity, price)."""
    out = []
    for cusip, date, symbol, qty, price in specs:
        out.append({
            "cusip": cusip, "settlement_date": date, "symbol": symbol,
            "quantity": qty, "price": price, "description": f"{symbol} corp",
            "dollar_value": (qty * price if price is not None else None),
        })
    return out


def test_replace_period_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("A", "2025-05-01", "AA", 100, 1.0),
               ("B", "2025-05-01", "BB", 200, 2.0))
    db.upsert_securities(conn, v1)
    assert db.replace_period(conn, "202505a", v1) == 2
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 2

    # repost drops B and revises A's quantity
    v2 = _rows(("A", "2025-05-01", "AA", 150, 1.0))
    db.upsert_securities(conn, v2)
    assert db.replace_period(conn, "202505a", v2) == 1
    assert [tuple(r) for r in conn.execute(
        "SELECT cusip, quantity FROM fails")] == [("A", 150)]


def test_upsert_securities_tracks_first_last_seen_and_latest_label():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("A", "2025-05-01", "OLD", 1, None)))
    db.upsert_securities(conn, _rows(("A", "2025-05-20", "NEW", 1, None)))
    db.upsert_securities(conn, _rows(("A", "2025-04-01", "EARLY", 1, None)))
    row = conn.execute(
        "SELECT symbol, first_seen, last_seen FROM securities "
        "WHERE cusip='A'").fetchone()
    assert tuple(row) == ("NEW", "2025-04-01", "2025-05-20")


def test_stored_periods_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_period(conn, "202505a", ("2025-05-01", "2025-05-15"), "t", 10, 10)
    db.record_period(conn, "202504b", ("2025-04-16", "2025-04-30"), "t", 5, 5)
    assert db.stored_periods(conn) == ["202504b", "202505a"]


def test_prune_removes_old_snapshots_only():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("A", "2025-05-01", "AA", 1, None)))
    db.replace_period(conn, "202505a", _rows(("A", "2025-05-01", "AA", 1, None)))
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 1  # untouched
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_ftd_db_schema.py tests/test_ftd_db_write.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftd_screener.db'`.

- [ ] **Step 4: Write the implementation**

Create `ftd_screener/db.py`:

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities", "replace_period",
           "record_period", "write_snapshot", "stored_periods", "prune"]

_FAIL_COLS = ["cusip", "settlement_date", "period", "symbol", "quantity",
              "price", "dollar_value"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    cusip       TEXT PRIMARY KEY,
    symbol      TEXT,
    description TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS fails (
    cusip           TEXT NOT NULL REFERENCES securities(cusip),
    settlement_date TEXT NOT NULL,
    period          TEXT NOT NULL,
    symbol          TEXT,
    quantity        INTEGER NOT NULL,
    price           REAL,
    dollar_value    REAL,
    PRIMARY KEY (cusip, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_fails_date   ON fails(settlement_date);
CREATE INDEX IF NOT EXISTS ix_fails_period ON fails(period);
CREATE INDEX IF NOT EXISTS ix_fails_symbol ON fails(symbol);
CREATE TABLE IF NOT EXISTS periods (
    period        TEXT PRIMARY KEY,
    settle_start  TEXT NOT NULL,
    settle_end    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    trailer_count INTEGER
);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    period_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables and indexes. Idempotent. (Views added in a later task.)"""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the CUSIP dimension: extend first_seen/last_seen to the min/max
    settlement_date ever seen, and refresh symbol/description from the row whose
    date is at or after the stored last_seen (so the label reflects the newest
    appearance regardless of insert order)."""
    params = [{"cusip": r["cusip"], "symbol": r.get("symbol"),
               "description": r.get("description"), "d": r["settlement_date"]}
              for r in rows]
    conn.executemany(
        """INSERT INTO securities (cusip, symbol, description, first_seen, last_seen)
           VALUES (:cusip, :symbol, :description, :d, :d)
           ON CONFLICT(cusip) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen),
             symbol      = CASE WHEN excluded.last_seen >= securities.last_seen
                                THEN excluded.symbol ELSE securities.symbol END,
             description = CASE WHEN excluded.last_seen >= securities.last_seen
                                THEN excluded.description
                                ELSE securities.description END""",
        params,
    )
    conn.commit()


def replace_period(conn, period: str, rows: list[dict]) -> int:
    """Delete all fails for this period, then bulk-insert the given rows.
    Period-replace (not upsert) so a repost that drops a row leaves no orphan.
    Dedupes within the batch by (cusip, settlement_date); each settlement_date
    belongs to exactly one period (a=1..15, b=16..end), so no cross-period
    collision is possible. Returns rows written."""
    by_key = {(r["cusip"], r["settlement_date"]): r for r in rows}
    conn.execute("DELETE FROM fails WHERE period = ?", (period,))
    placeholders = ", ".join(":" + c for c in _FAIL_COLS)
    params = []
    for r in by_key.values():
        p = {c: r.get(c) for c in _FAIL_COLS}
        p["period"] = period
        params.append(p)
    conn.executemany(
        f"INSERT INTO fails ({', '.join(_FAIL_COLS)}) VALUES ({placeholders})",
        params,
    )
    conn.commit()
    return len(by_key)


def record_period(conn, period: str, bounds: tuple, fetched_at: str,
                  row_count: int, trailer_count) -> None:
    """Upsert one period's provenance row."""
    start, end = bounds
    conn.execute(
        """INSERT INTO periods (period, settle_start, settle_end, fetched_at,
                                row_count, trailer_count)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(period) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count,
             trailer_count=excluded.trailer_count""",
        (period, start, end, fetched_at, row_count, trailer_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, period_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, period_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, period_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_periods(conn) -> list:
    """All ingested period ids, sorted ascending (lexical == chronological
    because months are zero-padded and 'a' < 'b')."""
    return [r[0] for r in conn.execute(
        "SELECT period FROM periods ORDER BY period")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Fail history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — do NOT cascade into fails."""
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

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_ftd_db_schema.py tests/test_ftd_db_write.py -q`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add ftd_screener/db.py tests/test_ftd_db_schema.py tests/test_ftd_db_write.py
git commit -m "feat(ftd): schema + securities/fails/periods writers"
```

---

### Task 4: `db.py` — screener views

**Files:**
- Modify: `ftd_screener/db.py`
- Test: `tests/test_ftd_db_views.py`

**Interfaces:**
- Consumes: writers from Task 3.
- Produces: views `v_security_history`, `v_latest_fails`, `v_date_rank`, `v_fail_streaks`, `v_persistent`, `v_spikes`. `ensure_schema` now also creates the views.

- [ ] **Step 1: Write the failing view tests**

Create `tests/test_ftd_db_views.py`:

```python
# tests/test_ftd_db_views.py
from ftd_screener import db


def _seed(conn, cusip, series):
    """series: list of (settlement_date, quantity). Seeds one cusip under its
    own period label (replace_period deletes by period, so per-cusip labels
    keep seeds independent)."""
    rows = [{"cusip": cusip, "settlement_date": d, "symbol": cusip,
             "quantity": q, "price": 1.0, "description": cusip,
             "dollar_value": float(q)} for d, q in series]
    db.upsert_securities(conn, rows)
    db.replace_period(conn, f"seed-{cusip}", rows)


def test_v_persistent_active_streak_of_six():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    dates = ["2025-05-01", "2025-05-02", "2025-05-05",
             "2025-05-06", "2025-05-07", "2025-05-08"]
    _seed(conn, "A", [(d, 20000) for d in dates])
    row = conn.execute(
        "SELECT streak_days, active FROM v_persistent WHERE cusip='A'").fetchone()
    assert tuple(row) == (6, 1)


def test_v_fail_streaks_below_threshold_day_splits_streak():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    # 3 days >=10k, one day <10k (present but excluded), 3 more days >=10k
    _seed(conn, "A", [("2025-05-01", 20000), ("2025-05-02", 20000),
                      ("2025-05-05", 20000), ("2025-05-06", 5000),
                      ("2025-05-07", 20000), ("2025-05-08", 20000),
                      ("2025-05-09", 20000)])
    streaks = sorted(r[0] for r in conn.execute(
        "SELECT streak_days FROM v_fail_streaks WHERE cusip='A'"))
    assert streaks == [3, 3]
    assert conn.execute(
        "SELECT COUNT(*) FROM v_persistent WHERE cusip='A'").fetchone()[0] == 0


def test_v_spikes_ratio_against_trailing_average():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn, "A", [("2025-05-01", 1000), ("2025-05-02", 1000),
                      ("2025-05-05", 1000), ("2025-05-06", 1000),
                      ("2025-05-07", 5000)])
    q, base, ratio = conn.execute(
        "SELECT quantity, base, spike_ratio FROM v_spikes "
        "WHERE cusip='A'").fetchone()
    assert q == 5000
    assert base == 1000.0
    assert ratio == 5.0


def test_v_latest_fails_returns_only_max_date():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn, "A", [("2025-05-01", 100), ("2025-05-07", 200)])
    _seed(conn, "B", [("2025-05-07", 300)])
    got = {r[0]: r[1] for r in conn.execute(
        "SELECT cusip, quantity FROM v_latest_fails")}
    assert got == {"A": 200, "B": 300}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_ftd_db_views.py -q`
Expected: FAIL — `sqlite3.OperationalError: no such table: v_persistent`.

- [ ] **Step 3: Add the views and wire them into `ensure_schema`**

Add this constant after `_SCHEMA` in `ftd_screener/db.py`:

```python
_VIEWS = """
-- every fail joined to its security (convenience / per-security history)
CREATE VIEW IF NOT EXISTS v_security_history AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip;

-- (1) latest-settlement-date leaderboard; order by quantity OR dollar_value
CREATE VIEW IF NOT EXISTS v_latest_fails AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip
WHERE f.settlement_date = (SELECT MAX(settlement_date) FROM fails);

-- global dense rank of distinct settlement dates (settlement days are not
-- contiguous calendar days; this ordinal defines "consecutive")
CREATE VIEW IF NOT EXISTS v_date_rank AS
SELECT settlement_date,
       DENSE_RANK() OVER (ORDER BY settlement_date) AS drank
FROM (SELECT DISTINCT settlement_date FROM fails);

-- gaps-and-islands: one row per (cusip, unbroken run of >=10k-share days)
CREATE VIEW IF NOT EXISTS v_fail_streaks AS
WITH q AS (
  SELECT f.cusip, f.settlement_date, f.quantity, dr.drank,
         dr.drank - ROW_NUMBER() OVER (PARTITION BY f.cusip
                                       ORDER BY f.settlement_date) AS grp
  FROM fails f JOIN v_date_rank dr USING (settlement_date)
  WHERE f.quantity >= 10000)
SELECT cusip, COUNT(*) AS streak_days,
       MIN(settlement_date) AS streak_start,
       MAX(settlement_date) AS streak_end,
       MAX(quantity) AS peak_quantity
FROM q GROUP BY cusip, grp;

-- (2) Reg SHO threshold PROXY: >=5 consecutive settlement days at >=10k shares.
-- (Missing the "0.5% of shares outstanding" half by design.) active=1 when the
-- streak reaches the newest settlement date.
CREATE VIEW IF NOT EXISTS v_persistent AS
SELECT k.cusip, s.symbol, s.description, k.streak_days,
       k.streak_start, k.streak_end, k.peak_quantity,
       (k.streak_end = (SELECT MAX(settlement_date) FROM fails)) AS active
FROM v_fail_streaks k JOIN securities s ON s.cusip = k.cusip
WHERE k.streak_days >= 5;

-- (3) spikes: latest fails vs the security's own trailing 20-day average
-- (excludes the current day). spike_ratio >= 3 => notable jump.
CREATE VIEW IF NOT EXISTS v_spikes AS
WITH w AS (
  SELECT cusip, settlement_date, quantity,
         AVG(quantity) OVER (PARTITION BY cusip ORDER BY settlement_date
                             ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS base
  FROM fails)
SELECT w.cusip, s.symbol, s.description, w.settlement_date,
       w.quantity, w.base,
       CASE WHEN w.base > 0 THEN w.quantity / w.base END AS spike_ratio
FROM w JOIN securities s ON s.cusip = w.cusip
WHERE w.settlement_date = (SELECT MAX(settlement_date) FROM fails)
  AND w.base > 0;
"""
```

Then update `ensure_schema` to also run the views:

```python
def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_ftd_db_views.py tests/test_ftd_db_schema.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add ftd_screener/db.py tests/test_ftd_db_views.py
git commit -m "feat(ftd): screener views (latest/persistent/spikes/history)"
```

---

### Task 5: `run.py` — period enumeration, orchestration, CLI

**Files:**
- Create: `ftd_screener/run.py`
- Test: `tests/test_ftd_run.py`

**Interfaces:**
- Consumes: `db` (Task 3–4), `fetch.fetch_period`, `fetch.settlement_bounds` (Task 1–2).
- Produces:
  - `periods_in_range(start_month: str, end_month: str) -> list[str]` (inclusive, both halves)
  - `_default_start(now_dt, months=24) -> str` — `"YYYY-MM"`
  - `run(db_path, start=None, keep_days=None, full=False, fetch_period=fetch.fetch_period, now_iso=None) -> tuple[int, int, int]` — `(snapshot_id, period_count, row_count)`
  - `main(argv=None)`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ftd_run.py`:

```python
# tests/test_ftd_run.py
from datetime import datetime, timezone

from ftd_screener import db, run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _one_row(period):
    """One fail row whose settlement_date falls inside `period` (a=05th,
    b=20th) — keeps (cusip, date) unique across periods."""
    day = "05" if period[6] == "a" else "20"
    d = f"{period[:4]}-{period[4:6]}-{day}"
    return [{"cusip": "A", "settlement_date": d, "symbol": "A", "quantity": 10,
             "price": 1.0, "description": "A", "dollar_value": 10.0}]


def test_periods_in_range_inclusive_both_halves():
    assert run_mod.periods_in_range("2025-11", "2026-01") == [
        "202511a", "202511b", "202512a", "202512b", "202601a", "202601b"]


def test_default_start_is_24_months_back():
    now = datetime(2026, 7, 3, tzinfo=timezone.utc)
    assert run_mod._default_start(now) == "2024-07"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"202606b"}

    def fetch_period(period):
        return (_one_row(period), 1) if period in published else None

    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(dbp, start="2026-06", now_iso=NOW,
                              fetch_period=fetch_period)
    assert (pc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 1


def test_run_incremental_skips_old_stored_refetches_last_two(tmp_path):
    def make_fp(sink):
        def fetch_period(period):
            sink.append(period)
            return (_one_row(period), 1)
        return fetch_period

    dbp = str(tmp_path / "ftd.db")
    now = "2026-03-31T00:00:00+00:00"      # range 2026-01..2026-03 -> 6 periods
    first = []
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp(first))
    assert len(first) == 6                 # first run fetches all published

    second = []
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp(second))
    assert second == ["202603a", "202603b"]  # only the trailing two refetched


def test_run_full_refetches_every_period(tmp_path):
    def make_fp(sink):
        def fetch_period(period):
            sink.append(period)
            return (_one_row(period), 1)
        return fetch_period

    dbp = str(tmp_path / "ftd.db")
    now = "2026-03-31T00:00:00+00:00"
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp([]))
    second = []
    run_mod.run(dbp, start="2026-01", full=True, now_iso=now,
                fetch_period=make_fp(second))
    assert len(second) == 6


def test_run_skips_failing_period_and_continues(tmp_path, capsys):
    def fetch_period(period):
        if period == "202606a":
            raise RuntimeError("boom")
        if period == "202606b":
            return (_one_row(period), 1)
        return None

    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(dbp, start="2026-06",
                              now_iso="2026-06-30T00:00:00+00:00",
                              fetch_period=fetch_period)
    assert pc == 1
    assert "202606a" in capsys.readouterr().err


def test_run_warns_on_trailer_mismatch(tmp_path, capsys):
    def fetch_period(period):
        return (_one_row(period), 999) if period == "202606b" else None

    run_mod.run(str(tmp_path / "ftd.db"), start="2026-06",
                now_iso="2026-06-30T00:00:00+00:00", fetch_period=fetch_period)
    assert "trailer" in capsys.readouterr().err.lower()


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(dbp, start="2026-06", now_iso=NOW,
                              fetch_period=lambda period: None)
    assert (pc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT period_count, row_count FROM snapshots").fetchone()) == (0, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_ftd_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftd_screener.run'`.

- [ ] **Step 3: Write the implementation**

Create `ftd_screener/run.py`:

```python
import argparse
import sys
from datetime import datetime, timezone

from ftd_screener import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored periods so
# SEC reposts (which occasionally revise a published half-month) are re-absorbed
# by the per-period replace. --full re-ingests every period in range.
_REFETCH_PERIODS = 2
_DEFAULT_LOOKBACK_MONTHS = 24


def periods_in_range(start_month: str, end_month: str) -> list:
    """Period ids from start_month..end_month inclusive (both 'YYYY-MM'),
    each month yielding its 'a' then 'b' half."""
    y, m = int(start_month[:4]), int(start_month[5:7])
    ey, em = int(end_month[:4]), int(end_month[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}a")
        out.append(f"{y:04d}{m:02d}b")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _default_start(now_dt, months: int = _DEFAULT_LOOKBACK_MONTHS) -> str:
    """'YYYY-MM' for `months` before now_dt."""
    y, m = now_dt.year, now_dt.month - months
    while m <= 0:
        m, y = m + 12, y - 1
    return f"{y:04d}-{m:02d}"


def run(db_path, start=None, keep_days=None, full=False,
        fetch_period=fetch.fetch_period, now_iso=None):
    """Ingest FTD periods into SQLite. Enumerate half-month periods from `start`
    (default: 24 months back) through the current month; ingest new periods and
    re-fetch the trailing _REFETCH_PERIODS already-stored ones (all of them when
    full=True). A 404 (period not yet published) is skipped. Any per-period
    failure rolls back and continues. Returns (snapshot_id, period_count,
    row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_month = f"{now_dt.year:04d}-{now_dt.month:02d}"
    all_periods = periods_in_range(start, end_month)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_periods(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_PERIODS:])  # newest already-stored periods

        period_count = 0
        total_rows = 0
        for period in all_periods:
            if (not full and period in stored_set and period not in refetch):
                continue
            try:
                result = fetch_period(period)
                if result is None:          # 404 -> not yet published
                    continue
                rows, trailer_count = result
                if trailer_count is not None and trailer_count != len(rows):
                    print(f"warning: {period} trailer count {trailer_count} != "
                          f"parsed {len(rows)}", file=sys.stderr)
                db.upsert_securities(conn, rows)
                written = db.replace_period(conn, period, rows)
                db.record_period(conn, period, fetch.settlement_bounds(period),
                                 now_iso, written, trailer_count)
                total_rows += written
                period_count += 1
            except Exception as e:  # skip-and-continue on any per-period failure
                # Roll back the failed period's uncommitted writes, then log only
                # the exception class — never str(e)/e.url, which may echo the URL.
                conn.rollback()
                print(f"warning: skipping {period}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, period_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, period_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="ftd",
        description="Pull SEC fails-to-deliver data into SQLite")
    p.add_argument("--db", default="ftd.db")
    p.add_argument("--start", default=None,
                   help="earliest publication month YYYY-MM "
                        "(default: 24 months back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every period in range, ignoring the "
                        "incremental skip")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches fail history)")
    a = p.parse_args(argv)
    _, pc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} fail rows across {pc} periods into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_ftd_run.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add ftd_screener/run.py tests/test_ftd_run.py
git commit -m "feat(ftd): run orchestration + CLI (period enumeration, incremental skip)"
```

---

### Task 6: Register `ftd` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (append)

**Interfaces:**
- Consumes: `ftd_screener.run.main`.
- Produces: `REGISTRY["ftd"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_ftd():
    import registry
    assert "ftd" in registry.REGISTRY
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_registry.py::test_dispatch_lists_ftd -q`
Expected: FAIL — `KeyError`/`assert "ftd" in {...}`.

- [ ] **Step 3: Wire the screener into `registry.py`**

Add the import alongside the others (after the `fred` import line):

```python
from ftd_screener.run import main as ftd_main
```

Add the entry to `REGISTRY` (after the `"cftc"` line):

```python
    "ftd": ftd_main,
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_registry.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(ftd): register ftd screener in dispatcher"
```

---

### Task 7: Full-suite verification + live smoke test

**Files:** none (verification only).

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest -q`
Expected: PASS — all pre-existing tests plus the new `test_ftd_*` and the extended `test_registry`. No failures, no errors.

- [ ] **Step 2: Live smoke test against the real SEC endpoint (one recent period)**

Run:
```bash
python main.py ftd --db /tmp/ftd_smoke.db --start 2025-05
```
Expected: prints `stored <N> fail rows across <M> periods into /tmp/ftd_smoke.db` with `N` in the tens of thousands and `M >= 1`. (If the SEC returns 403s it will retry with backoff; a transient failure is skipped per-period, not fatal.)

- [ ] **Step 3: Spot-check the derived views**

Run:
```bash
python - <<'PY'
import sqlite3
c = sqlite3.connect("/tmp/ftd_smoke.db")
print("latest leaderboard (top 5 by $):")
for r in c.execute("SELECT symbol, quantity, dollar_value FROM v_latest_fails "
                   "ORDER BY dollar_value DESC LIMIT 5"):
    print(" ", tuple(r))
print("persistent (streak >=5), top 5:")
for r in c.execute("SELECT symbol, streak_days, active FROM v_persistent "
                   "ORDER BY streak_days DESC LIMIT 5"):
    print(" ", tuple(r))
PY
```
Expected: both queries return rows without error (leaderboard non-empty; persistent may be empty if the seeded window is short — that is acceptable, it must simply not error).

- [ ] **Step 4: Clean up the smoke-test DB**

Run: `rm -f /tmp/ftd_smoke.db /tmp/ftd_smoke.db-wal /tmp/ftd_smoke.db-shm`

---

## Self-Review Notes (spec coverage)

- **Ingestion (ZIP download, unzip, parse, trailer-validate):** Tasks 1–2 (parse + trailer), Task 5 (mismatch warning). ✓
- **Storage (securities/fails/periods/snapshots, period-replace):** Task 3. ✓
- **Views (latest / persistent proxy / spikes / history):** Task 4. ✓
- **Reg SHO shares-only proxy + documented 0.5% gap:** `v_persistent` comment (Task 4) + spec Non-goals. ✓
- **CLI ergonomics (`--start`/`--full`/`--keep-days`, 24-month default):** Task 5. ✓
- **Incremental skip + trailing re-fetch + 404→None + skip-and-continue + leak-safe logging:** Task 5. ✓
- **Prune single-table (fails never cascaded):** Task 3 + `test_prune_removes_old_snapshots_only`. ✓
- **Registry wiring:** Task 6. ✓
- **No new env/secrets:** confirmed — nothing added to `.env.example`.
