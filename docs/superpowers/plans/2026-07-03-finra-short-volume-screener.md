# FINRA Daily Short Sale Volume Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `finra_short_volume` screener that ingests FINRA's daily consolidated short-sale-volume flat files into SQLite, with screening views for shorting pressure.

**Architecture:** A new screener package following the existing FTD layout (`fetch.py` / `db.py` / `run.py`), wired into `registry.py`. One pipe-delimited text file per trading day is downloaded (no auth), parsed into `(symbol, date)` rows with a computed `short_ratio`, and written via a per-day *replace* into a `short_volume` fact table. SQL views surface the latest leaderboard, high-ratio names, ratio spikes vs. a trailing baseline, and consecutive-day short-pressure streaks.

**Tech Stack:** Python 3.12 stdlib only (`urllib`, `sqlite3`, `argparse`, `datetime`); `pytest` for tests. Reuses in-repo `screener_common.connect` and `http_client.http_get`/`make_opener`.

## Global Constraints

- **Python ≥ 3.12**, **standard library only** — no third-party runtime dependencies (matches every existing screener).
- **Reuse shared primitives:** `screener_common.connect` for the SQLite connection; `http_client.make_opener` + `http_client.http_get` for the bounded-backoff download. Do NOT reinvent them.
- **Secret-hygiene / error rule (repo-wide):** in per-item failure handlers, `conn.rollback()` then print **only** `type(e).__name__` — never `str(e)` or `e.url`. (No secrets exist in this feed, but the pattern is mandatory for consistency.)
- **No `.env` / `.env.example` changes** — this data source requires no credentials.
- **Data source:** `https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt`, pipe-delimited `Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market`. A descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`) is required; retry HTTP 403/429/503; HTTP 404 = non-trading-day/unpublished → treated as "skip".
- **View thresholds (baked into SQL):** liquidity floor `total_volume >= 100000`; elevated-ratio threshold `short_ratio >= 0.50`.
- **Retention:** `prune` deletes snapshot-provenance rows only — it must NEVER delete `short_volume` facts.
- **Run all tests with:** `python -m pytest -q` from the repo root (pytest is configured via `pyproject.toml` with `pythonpath=["."]`).

## File Structure

- `finra_short_volume/__init__.py` — empty package marker.
- `finra_short_volume/fetch.py` — URL construction, flat-file parsing (+ `short_ratio`), one-day download with 404→None and bounded backoff.
- `finra_short_volume/db.py` — schema (tables + indexes + views), dimension/fact/provenance writes, `prune`.
- `finra_short_volume/run.py` — calendar-day enumeration, incremental orchestration, argparse CLI.
- `registry.py` — MODIFY: register `"short_volume"`.
- `tests/test_finra_shorts_fetch.py`, `tests/test_finra_shorts_db_schema.py`, `tests/test_finra_shorts_db_write.py`, `tests/test_finra_shorts_db_views.py`, `tests/test_finra_shorts_run.py` — mirror the `test_ftd_*` suite.
- `tests/test_registry.py` — MODIFY: assert `"short_volume"` registered.

---

### Task 1: Package scaffold + `fetch.py`

**Files:**
- Create: `finra_short_volume/__init__.py`
- Create: `finra_short_volume/fetch.py`
- Test: `tests/test_finra_shorts_fetch.py`

**Interfaces:**
- Consumes: `http_client.make_opener(headers)`, `http_client.http_get(url, opener, retry_status, attempts, base_delay, sleep)` (already in repo).
- Produces:
  - `FILES_BASE: str = "https://cdn.finra.org/equity/regsho/daily"`
  - `day_url(date: str, base: str = FILES_BASE) -> str` — `date` is `"YYYY-MM-DD"`.
  - `parse_file(text: str) -> list[dict]` — each dict has keys `symbol, date, short_volume, short_exempt_volume, total_volume, short_ratio, market`.
  - `fetch_day(date: str, get=_http_get, opener=None) -> list[dict] | None` — `None` on HTTP 404.
  - `_http_get(url, opener=_urlopen, attempts=5, base_delay=1.0, sleep=time.sleep) -> str`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_finra_shorts_fetch.py`:

```python
# tests/test_finra_shorts_fetch.py
import urllib.error

import pytest

from finra_short_volume.fetch import (
    _http_get, day_url, fetch_day, parse_file,
)

SAMPLE = (
    "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n"
    "20240614|AAL|900|100|1500|B,Q,N\n"
    "20240614|ZERO|0|0|0|Q\n"          # total_volume 0 -> ratio None, still kept
    "20240614||50|0|100|Q\n"           # blank symbol -> skipped
    "20240614|SHORT|5|0\n"             # too few fields -> skipped
    "Trailer|record|count|3|x|y\n"     # footer-ish: date 'Trailer' invalid -> skipped
)


def test_parse_file_maps_and_computes_ratio():
    rows = parse_file(SAMPLE)
    assert len(rows) == 2              # AAL + ZERO; blank/short/footer dropped
    assert rows[0] == {
        "symbol": "AAL", "date": "2024-06-14",
        "short_volume": 900, "short_exempt_volume": 100,
        "total_volume": 1500,
        "short_ratio": pytest.approx(900 / 1500),
        "market": "B,Q,N",
    }


def test_parse_file_zero_total_volume_gives_none_ratio():
    zero = [r for r in parse_file(SAMPLE) if r["symbol"] == "ZERO"][0]
    assert zero["total_volume"] == 0
    assert zero["short_ratio"] is None


def test_parse_file_header_row_is_dropped():
    rows = parse_file(
        "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n")
    assert rows == []


def test_day_url():
    assert day_url("2024-06-14") == (
        "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20240614.txt")


def test_fetch_day_parses_returned_text():
    def fake_get(url, opener=None):
        assert url.endswith("CNMSshvol20240614.txt")
        return SAMPLE

    rows = fetch_day("2024-06-14", get=fake_get)
    assert len(rows) == 2


def test_fetch_day_returns_none_on_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    assert fetch_day("2099-01-01", get=fake_get) is None


def test_fetch_day_reraises_non_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 500, "err", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_day("2024-06-14", get=fake_get)


def test_http_get_retries_on_403_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 403, "throttle", {}, None)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_finra_shorts_fetch.py -q`
Expected: FAIL / collection error — `ModuleNotFoundError: No module named 'finra_short_volume'`.

- [ ] **Step 3: Create the package and implement `fetch.py`**

Create empty `finra_short_volume/__init__.py` (0 bytes).

Create `finra_short_volume/fetch.py`:

```python
# finra_short_volume/fetch.py
import time
import urllib.error

import http_client

FILES_BASE = "https://cdn.finra.org/equity/regsho/daily"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family (same shape the edgar/cftc fetchers already handle).
_RETRY_STATUS = frozenset({403, 429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def day_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the consolidated-NMS short-volume file for a 'YYYY-MM-DD' date."""
    return f"{base}/CNMSshvol{date.replace('-', '')}.txt"


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


def parse_file(text: str) -> list[dict]:
    """Parse a daily CNMS short-volume file body into rows.

    Pipe-delimited: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market.
    The header line drops naturally (its non-numeric date/volume fail coercion).
    Any footer/summary or malformed line is skipped: a row with fewer than 6
    fields, or missing a symbol, a valid 8-digit date, or a valid total_volume.
    short_ratio = short_volume / total_volume (None when total_volume is 0)."""
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue
        d_raw, symbol, sv, sev, tv, market = (p.strip() for p in parts[:6])
        date = _norm_date(d_raw)
        short_volume = _num(sv, int)
        total_volume = _num(tv, int)
        if not symbol or date is None or short_volume is None or total_volume is None:
            continue
        short_ratio = (short_volume / total_volume) if total_volume else None
        rows.append({
            "symbol": symbol, "date": date,
            "short_volume": short_volume,
            "short_exempt_volume": _num(sev, int),
            "total_volume": total_volume,
            "short_ratio": short_ratio,
            "market": market or None,
        })
    return rows


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET file text with bounded backoff, retrying 403/429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 404) raise at once, so
    fetch_day can map 404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_day(date: str, get=_http_get, opener=None):
    """Download + parse one trading day's CNMS file. Returns list[dict], or
    None on HTTP 404 (weekend/holiday/not-yet-published)."""
    op = opener if opener is not None else _urlopen
    try:
        text = get(day_url(date), opener=op)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return parse_file(text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_finra_shorts_fetch.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add finra_short_volume/__init__.py finra_short_volume/fetch.py tests/test_finra_shorts_fetch.py
git commit -m "feat(short_volume): FINRA daily short-volume fetch + parse"
```

---

### Task 2: `db.py` — schema + writes

**Files:**
- Create: `finra_short_volume/db.py` (schema + writes now; views added in Task 3)
- Test: `tests/test_finra_shorts_db_schema.py`, `tests/test_finra_shorts_db_write.py`

**Interfaces:**
- Consumes: `screener_common.connect(path)`.
- Produces:
  - `connect` (re-exported), `ensure_schema(conn) -> None`
  - `upsert_securities(conn, rows: list[dict]) -> None`
  - `replace_day(conn, date: str, rows: list[dict]) -> int` (rows written)
  - `record_day(conn, date: str, fetched_at: str, row_count: int) -> None`
  - `write_snapshot(conn, captured_at: str, day_count: int, row_count: int) -> int` (snapshot id)
  - `stored_days(conn) -> list[str]` (ascending)
  - `prune(conn, keep_days: int, now_iso: str) -> int` (snapshot headers removed)
  - Row dicts use keys: `symbol, date, short_volume, short_exempt_volume, total_volume, short_ratio, market`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_finra_shorts_db_schema.py`:

```python
# tests/test_finra_shorts_db_schema.py
from finra_short_volume import db


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)            # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"securities", "short_volume", "days", "snapshots"} <= tables
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_latest", "v_high_short_ratio", "v_ratio_spikes",
            "v_short_streaks", "v_symbol_history", "v_date_rank"} <= views
```

Create `tests/test_finra_shorts_db_write.py`:

```python
# tests/test_finra_shorts_db_write.py
from finra_short_volume import db


def _rows(*specs):
    """spec tuples: (symbol, date, short_volume, total_volume)."""
    out = []
    for symbol, d, sv, tv in specs:
        out.append({"symbol": symbol, "date": d, "short_volume": sv,
                    "short_exempt_volume": 0, "total_volume": tv,
                    "short_ratio": (sv / tv if tv else None), "market": "Q"})
    return out


def test_replace_day_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("AA", "2024-06-14", 100, 200), ("BB", "2024-06-14", 300, 600))
    db.upsert_securities(conn, v1)
    assert db.replace_day(conn, "2024-06-14", v1) == 2
    assert conn.execute("SELECT COUNT(*) FROM short_volume").fetchone()[0] == 2

    # repost drops BB and revises AA's short_volume
    v2 = _rows(("AA", "2024-06-14", 150, 200))
    db.upsert_securities(conn, v2)
    assert db.replace_day(conn, "2024-06-14", v2) == 1
    assert [tuple(r) for r in conn.execute(
        "SELECT symbol, short_volume FROM short_volume")] == [("AA", 150)]


def test_upsert_securities_tracks_first_and_last_seen():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", 1, 2)))
    db.upsert_securities(conn, _rows(("AA", "2024-07-01", 1, 2)))
    db.upsert_securities(conn, _rows(("AA", "2024-05-01", 1, 2)))
    row = conn.execute(
        "SELECT first_seen, last_seen FROM securities WHERE symbol='AA'").fetchone()
    assert tuple(row) == ("2024-05-01", "2024-07-01")


def test_stored_days_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_day(conn, "2024-06-14", "t", 10)
    db.record_day(conn, "2024-05-31", "t", 5)
    db.record_day(conn, "2024-06-14", "t2", 11)   # upsert, not duplicate
    assert db.stored_days(conn) == ["2024-05-31", "2024-06-14"]


def test_prune_removes_old_snapshots_only():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", 1, 2)))
    db.replace_day(conn, "2024-06-14", _rows(("AA", "2024-06-14", 1, 2)))
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM short_volume").fetchone()[0] == 1  # untouched
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_finra_shorts_db_schema.py tests/test_finra_shorts_db_write.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'finra_short_volume.db'`.

- [ ] **Step 3: Implement `db.py`**

Create `finra_short_volume/db.py`. (The `_VIEWS` block is included now so `ensure_schema` creates the views the schema test asserts; the view *behavior* is tested in Task 3.)

```python
# finra_short_volume/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities", "replace_day",
           "record_day", "write_snapshot", "stored_days", "prune"]

_SV_COLS = ["symbol", "date", "short_volume", "short_exempt_volume",
            "total_volume", "short_ratio", "market"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    symbol     TEXT PRIMARY KEY,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS short_volume (
    symbol              TEXT NOT NULL REFERENCES securities(symbol),
    date                TEXT NOT NULL,
    short_volume        INTEGER NOT NULL,
    short_exempt_volume INTEGER,
    total_volume        INTEGER NOT NULL,
    short_ratio         REAL,
    market              TEXT,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS ix_sv_date   ON short_volume(date);
CREATE INDEX IF NOT EXISTS ix_sv_symbol ON short_volume(symbol);
CREATE TABLE IF NOT EXISTS days (
    date       TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    day_count   INTEGER NOT NULL,
    row_count   INTEGER NOT NULL
);
"""

_VIEWS = """
-- per-symbol time series (drill-down)
CREATE VIEW IF NOT EXISTS v_symbol_history AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume;

-- (1) latest-day leaderboard, liquid names only (order by short_ratio or volume)
CREATE VIEW IF NOT EXISTS v_latest AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume
WHERE date = (SELECT MAX(date) FROM short_volume)
  AND total_volume >= 100000;

-- (2) heavy short participation on the latest day
CREATE VIEW IF NOT EXISTS v_high_short_ratio AS
SELECT symbol, date, short_volume, total_volume, short_ratio, market
FROM short_volume
WHERE date = (SELECT MAX(date) FROM short_volume)
  AND total_volume >= 100000
  AND short_ratio >= 0.50;

-- (3) latest short_ratio vs the symbol's trailing 20-day average (excl. today)
CREATE VIEW IF NOT EXISTS v_ratio_spikes AS
WITH w AS (
  SELECT symbol, date, short_ratio, total_volume,
         AVG(short_ratio) OVER (PARTITION BY symbol ORDER BY date
                                ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS base
  FROM short_volume)
SELECT w.symbol, w.date, w.short_ratio, w.total_volume, w.base,
       CASE WHEN w.base > 0 THEN w.short_ratio / w.base END AS spike_ratio
FROM w
WHERE w.date = (SELECT MAX(date) FROM short_volume)
  AND w.total_volume >= 100000
  AND w.base > 0;

-- global dense rank of distinct trading days (trading days are not contiguous
-- calendar days; this ordinal defines "consecutive")
CREATE VIEW IF NOT EXISTS v_date_rank AS
SELECT date, DENSE_RANK() OVER (ORDER BY date) AS drank
FROM (SELECT DISTINCT date FROM short_volume);

-- (4) gaps-and-islands: one row per (symbol, unbroken run of elevated days)
CREATE VIEW IF NOT EXISTS v_short_streaks AS
WITH q AS (
  SELECT sv.symbol, sv.date, sv.short_ratio, dr.drank,
         dr.drank - ROW_NUMBER() OVER (PARTITION BY sv.symbol
                                       ORDER BY sv.date) AS grp
  FROM short_volume sv JOIN v_date_rank dr USING (date)
  WHERE sv.total_volume >= 100000 AND sv.short_ratio >= 0.50)
SELECT symbol, COUNT(*) AS streak_days,
       MIN(date) AS streak_start, MAX(date) AS streak_end,
       MAX(short_ratio) AS peak_ratio,
       (MAX(date) = (SELECT MAX(date) FROM short_volume)) AS active
FROM q GROUP BY symbol, grp;
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the symbol dimension: extend first_seen/last_seen to the min/max
    date ever seen for each symbol."""
    params = [{"symbol": r["symbol"], "d": r["date"]} for r in rows]
    conn.executemany(
        """INSERT INTO securities (symbol, first_seen, last_seen)
           VALUES (:symbol, :d, :d)
           ON CONFLICT(symbol) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen)""",
        params,
    )
    conn.commit()


def replace_day(conn, date: str, rows: list[dict]) -> int:
    """Delete all short_volume rows for this date, then bulk-insert the given
    rows. Replace (not upsert) so a FINRA file repost that drops a row leaves no
    orphan. Dedupes within the batch by (symbol, date). Returns rows written."""
    by_key = {(r["symbol"], r["date"]): r for r in rows}
    conn.execute("DELETE FROM short_volume WHERE date = ?", (date,))
    placeholders = ", ".join(":" + c for c in _SV_COLS)
    params = [{c: r.get(c) for c in _SV_COLS} for r in by_key.values()]
    conn.executemany(
        f"INSERT INTO short_volume ({', '.join(_SV_COLS)}) VALUES ({placeholders})",
        params,
    )
    conn.commit()
    return len(by_key)


def record_day(conn, date: str, fetched_at: str, row_count: int) -> None:
    """Upsert one day's provenance row."""
    conn.execute(
        """INSERT INTO days (date, fetched_at, row_count)
           VALUES (?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count""",
        (date, fetched_at, row_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, day_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, day_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, day_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_days(conn) -> list:
    """All ingested dates, sorted ascending (ISO dates sort chronologically)."""
    return [r[0] for r in conn.execute("SELECT date FROM days ORDER BY date")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Short-volume history is NOT snapshot-scoped, so this is a single-table delete
    of snapshot headers only — it must NOT cascade into short_volume."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_finra_shorts_db_schema.py tests/test_finra_shorts_db_write.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add finra_short_volume/db.py tests/test_finra_shorts_db_schema.py tests/test_finra_shorts_db_write.py
git commit -m "feat(short_volume): sqlite schema + dimension/fact/provenance writes"
```

---

### Task 3: `db.py` — screening views behavior

**Files:**
- Modify: none (views already created in Task 2's `_VIEWS`).
- Test: `tests/test_finra_shorts_db_views.py`

**Interfaces:**
- Consumes: the views created by `ensure_schema` — `v_latest`, `v_high_short_ratio`, `v_ratio_spikes`, `v_short_streaks` (columns `streak_days, streak_start, streak_end, peak_ratio, active`).
- Produces: no new code — this task locks in view semantics with tests. If a test fails, fix the corresponding view SQL in `db.py`'s `_VIEWS`.

**Note on seeding:** `replace_day` deletes by date, so seeding two symbols on the same date via separate calls would clobber. The view tests insert rows directly with an `_insert` helper to seed multi-symbol/multi-date panels safely.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_finra_shorts_db_views.py`:

```python
# tests/test_finra_shorts_db_views.py
import pytest

from finra_short_volume import db

_COLS = ["symbol", "date", "short_volume", "short_exempt_volume",
         "total_volume", "short_ratio", "market"]


def _rows(symbol, series):
    """series: list of (date, short_ratio, total_volume). short_volume is
    derived so the stored ratio is exact."""
    return [{"symbol": symbol, "date": d,
             "short_volume": int(round(ratio * tv)),
             "short_exempt_volume": 0, "total_volume": tv,
             "short_ratio": ratio, "market": "Q"}
            for d, ratio, tv in series]


def _insert(conn, rows):
    """Insert directly (bypassing replace_day's delete-by-date) so multiple
    symbols can share a date."""
    db.upsert_securities(conn, rows)
    conn.executemany(
        f"INSERT INTO short_volume ({','.join(_COLS)}) "
        f"VALUES ({','.join(':' + c for c in _COLS)})", rows)
    conn.commit()


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_latest_only_max_date_and_liquid():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-13", 0.4, 200000),
                              ("2024-06-14", 0.6, 200000)]))
    _insert(conn, _rows("B", [("2024-06-14", 0.9, 50000)]))   # illiquid -> excluded
    got = {r[0]: r[1] for r in conn.execute(
        "SELECT symbol, short_ratio FROM v_latest")}
    assert set(got) == {"A"}                       # B dropped, only latest date
    assert got["A"] == pytest.approx(0.6)


def test_v_high_short_ratio_threshold():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-14", 0.6, 200000)]))  # >=0.5 -> in
    _insert(conn, _rows("B", [("2024-06-14", 0.4, 200000)]))  # <0.5 -> out
    syms = {r[0] for r in conn.execute("SELECT symbol FROM v_high_short_ratio")}
    assert syms == {"A"}


def test_v_ratio_spikes_against_trailing_average():
    conn = _fresh()
    _insert(conn, _rows("A", [("2024-06-10", 0.2, 200000),
                              ("2024-06-11", 0.2, 200000),
                              ("2024-06-12", 0.2, 200000),
                              ("2024-06-13", 0.2, 200000),
                              ("2024-06-14", 0.6, 200000)]))  # latest jumps
    ratio, base, spike = conn.execute(
        "SELECT short_ratio, base, spike_ratio FROM v_ratio_spikes "
        "WHERE symbol='A'").fetchone()
    assert ratio == pytest.approx(0.6)
    assert base == pytest.approx(0.2)
    assert spike == pytest.approx(3.0)


def test_v_short_streaks_below_threshold_day_splits_run():
    conn = _fresh()
    # 3 elevated, 1 below (present but excluded -> breaks run), 3 elevated again
    _insert(conn, _rows("A", [("2024-06-10", 0.6, 200000),
                              ("2024-06-11", 0.6, 200000),
                              ("2024-06-12", 0.6, 200000),
                              ("2024-06-13", 0.3, 200000),
                              ("2024-06-14", 0.6, 200000),
                              ("2024-06-15", 0.6, 200000),
                              ("2024-06-16", 0.6, 200000)]))
    streaks = sorted((r[0], r[1]) for r in conn.execute(
        "SELECT streak_days, active FROM v_short_streaks WHERE symbol='A'"))
    # two runs of 3; the later one is active (reaches the max stored date)
    assert streaks == [(3, 0), (3, 1)]
```

- [ ] **Step 2: Run tests to verify the state**

Run: `python -m pytest tests/test_finra_shorts_db_views.py -q`
Expected: PASS if the Task 2 `_VIEWS` SQL is correct. If any assertion fails, fix the offending view in `finra_short_volume/db.py`'s `_VIEWS` and re-run until green. (This is the point of the task — the tests pin the SQL semantics.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_finra_shorts_db_views.py finra_short_volume/db.py
git commit -m "test(short_volume): pin screening-view semantics"
```

---

### Task 4: `run.py` — orchestration + CLI

**Files:**
- Create: `finra_short_volume/run.py`
- Test: `tests/test_finra_shorts_run.py`

**Interfaces:**
- Consumes: `finra_short_volume.db` (all Task 2 writers), `finra_short_volume.fetch.fetch_day`.
- Produces:
  - `days_in_range(start_date: str, end_date: str) -> list[str]` — inclusive, all calendar dates.
  - `_default_start(now_dt, days=_DEFAULT_LOOKBACK_DAYS) -> str`
  - `run(db_path, start=None, keep_days=None, full=False, fetch_day=fetch.fetch_day, now_iso=None) -> tuple[int, int, int]` → `(snapshot_id, day_count, row_count)`
  - `main(argv=None)` — CLI with `--db`, `--start`, `--full`, `--keep-days`.
  - Module constants `_REFETCH_DAYS = 2`, `_DEFAULT_LOOKBACK_DAYS = 183`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_finra_shorts_run.py`:

```python
# tests/test_finra_shorts_run.py
from datetime import datetime, timezone

from finra_short_volume import db, run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _rows(day):
    """One liquid, elevated row whose date == day (keeps (symbol, date) unique)."""
    return [{"symbol": "AAL", "date": day, "short_volume": 120,
             "short_exempt_volume": 0, "total_volume": 200,
             "short_ratio": 0.6, "market": "Q"}]


def test_days_in_range_inclusive():
    assert run_mod.days_in_range("2026-06-29", "2026-07-02") == [
        "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02"]


def test_default_start_is_about_six_months_back():
    now = datetime(2026, 7, 3, tzinfo=timezone.utc)
    assert run_mod._default_start(now, days=183) == "2026-01-01"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"2026-06-30"}

    def fetch_day(day):
        return _rows(day) if day in published else None

    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW,
                            fetch_day=fetch_day)
    assert (dc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM short_volume").fetchone()[0] == 1


def test_run_incremental_skips_old_stored_refetches_last_two(tmp_path):
    def make_fd(sink):
        def fetch_day(day):
            sink.append(day)
            return _rows(day)
        return fetch_day

    dbp = str(tmp_path / "sv.db")
    now = "2026-01-05T00:00:00+00:00"          # range 2026-01-01..2026-01-05
    first = []
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd(first))
    assert len(first) == 5                      # all five days fetched

    second = []
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd(second))
    assert second == ["2026-01-04", "2026-01-05"]  # only trailing two refetched


def test_run_full_refetches_every_day(tmp_path):
    def make_fd(sink):
        def fetch_day(day):
            sink.append(day)
            return _rows(day)
        return fetch_day

    dbp = str(tmp_path / "sv.db")
    now = "2026-01-05T00:00:00+00:00"
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd([]))
    second = []
    run_mod.run(dbp, start="2026-01-01", full=True, now_iso=now,
                fetch_day=make_fd(second))
    assert len(second) == 5


def test_run_skips_failing_day_and_continues(tmp_path, capsys):
    def fetch_day(day):
        if day == "2026-06-30":
            raise RuntimeError("boom")
        if day == "2026-07-01":
            return _rows(day)
        return None

    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW,
                            fetch_day=fetch_day)
    assert dc == 1
    assert "2026-06-30" in capsys.readouterr().err


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW,
                            fetch_day=lambda day: None)
    assert (dc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT day_count, row_count FROM snapshots").fetchone()) == (0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_finra_shorts_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'finra_short_volume.run'`.

- [ ] **Step 3: Implement `run.py`**

Create `finra_short_volume/run.py`:

```python
# finra_short_volume/run.py
import argparse
import sys
from datetime import date as date_cls, datetime, timedelta, timezone

from finra_short_volume import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored days so a
# FINRA file repost is re-absorbed by the per-day replace. --full re-ingests
# every day in range.
_REFETCH_DAYS = 2
_DEFAULT_LOOKBACK_DAYS = 183       # ~6 months


def days_in_range(start_date: str, end_date: str) -> list[str]:
    """All calendar dates start_date..end_date inclusive, each 'YYYY-MM-DD'."""
    d = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date)
    out = []
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _default_start(now_dt, days: int = _DEFAULT_LOOKBACK_DAYS) -> str:
    """'YYYY-MM-DD' for `days` before now_dt's date."""
    return (now_dt.date() - timedelta(days=days)).isoformat()


def run(db_path, start=None, keep_days=None, full=False,
        fetch_day=fetch.fetch_day, now_iso=None):
    """Ingest FINRA daily short-volume files into SQLite. Enumerate calendar days
    from `start` (default: ~6 months back) through today; ingest new days and
    re-fetch the trailing _REFETCH_DAYS already-stored ones (all of them when
    full=True). A 404 (weekend/holiday/unpublished) is skipped. Any per-day
    failure rolls back and continues. Returns (snapshot_id, day_count,
    row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_date = now_dt.date().isoformat()
    all_days = days_in_range(start, end_date)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_days(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_DAYS:])   # newest already-stored days

        day_count = 0
        total_rows = 0
        for day in all_days:
            if not full and day in stored_set and day not in refetch:
                continue
            try:
                rows = fetch_day(day)
                if rows is None:                  # 404 -> weekend/holiday/unpub
                    continue
                db.upsert_securities(conn, rows)
                written = db.replace_day(conn, day, rows)
                db.record_day(conn, day, now_iso, written)
                total_rows += written
                day_count += 1
            except Exception as e:  # skip-and-continue on any per-day failure
                # Roll back the failed day's uncommitted writes, then log only the
                # exception class — never str(e)/e.url.
                conn.rollback()
                print(f"warning: skipping {day}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, day_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, day_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="short_volume",
        description="Pull FINRA daily short sale volume into SQLite")
    p.add_argument("--db", default="short_volume.db")
    p.add_argument("--start", default=None,
                   help="earliest trading date YYYY-MM-DD "
                        "(default: ~6 months back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every day in range, ignoring the "
                        "incremental skip")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches short-volume history)")
    a = p.parse_args(argv)
    _, dc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} short-volume rows across {dc} days into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_finra_shorts_run.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add finra_short_volume/run.py tests/test_finra_shorts_run.py
git commit -m "feat(short_volume): run orchestration + CLI"
```

---

### Task 5: Register in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `finra_short_volume.run.main`.
- Produces: `"short_volume"` key in `registry.REGISTRY`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_short_volume():
    import registry
    assert "short_volume" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_registry.py::test_dispatch_lists_short_volume -q`
Expected: FAIL — `KeyError`/assert: `"short_volume"` not in `REGISTRY`.

- [ ] **Step 3: Wire the screener into `registry.py`**

Add the import alongside the others (after the `ftd_screener` import):

```python
from finra_short_volume.run import main as short_volume_main
```

Add the entry to the `REGISTRY` dict (after the `"ftd"` line):

```python
    "short_volume": short_volume_main,
```

- [ ] **Step 4: Run the full suite to verify green**

Run: `python -m pytest -q`
Expected: PASS — the whole suite, including the new `test_finra_shorts_*` files and the registry test.

- [ ] **Step 5: Commit**

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(short_volume): register short_volume screener in dispatcher"
```

---

### Task 6: Live smoke test (manual verification)

**Files:** none (verification only).

This is the one step that touches the real network — everything above is
hermetic. It confirms the file format assumptions (delimiter, header, any
footer) hold against a live file.

- [ ] **Step 1: Run against a small real window**

Run: `python main.py short_volume --db /tmp/sv_smoke.db --start 2024-06-10`
(pick a start ~4 days before a known weekday so a few files exist; adjust to a
recent date range at implementation time). Expected: prints
`stored <N> short-volume rows across <D> days into /tmp/sv_smoke.db` with N in
the hundreds-of-thousands and D ≥ 1; no tracebacks. Weekends/holidays log
nothing (silently skipped as 404).

- [ ] **Step 2: Eyeball the data and views**

Run:
```bash
sqlite3 /tmp/sv_smoke.db \
  "SELECT symbol, short_volume, total_volume, ROUND(short_ratio,3) \
   FROM v_latest ORDER BY short_ratio DESC LIMIT 10;"
```
Expected: ten liquid tickers with plausible ratios in `[0,1]`. Spot-check one
symbol against the raw file line if desired.

- [ ] **Step 3: Clean up**

Run: `rm -f /tmp/sv_smoke.db /tmp/sv_smoke.db-wal /tmp/sv_smoke.db-shm`
No commit (nothing changed in the repo).

---

## Self-Review

**Spec coverage** (spec → task):
- Data source / URL / UA / 404-skip / backoff → Task 1 (`fetch.py`). ✓
- `short_ratio` computed at parse, zero-total → None → Task 1 tests. ✓
- Schema: `securities` / `short_volume` / `days` / `snapshots` → Task 2. ✓
- Writes: `upsert_securities`, `replace_day` (repost-safe), `record_day`, `write_snapshot`, `stored_days`, `prune` (snapshot-only) → Task 2. ✓
- Five views + `v_date_rank` helper → created in Task 2, semantics pinned in Task 3. ✓
- Run: 6-month default, incremental skip + trailing refetch, `--full`, skip-and-continue, zero snapshot → Task 4. ✓
- CLI flags `--db/--start/--full/--keep-days` → Task 4. ✓
- Registry `"short_volume"` → Task 5. ✓
- Format assumptions verified live → Task 6. ✓
- Retention "never drops facts" → Task 2 `prune` + `test_prune_removes_old_snapshots_only`. ✓
- Out-of-scope items (short interest, non-CNMS segments, float joins, OAuth) → intentionally absent. ✓

**Placeholder scan:** No TBD/TODO/"add error handling"/"similar to Task N" — every code and test block is complete. ✓

**Type consistency:** Row-dict keys (`symbol, date, short_volume, short_exempt_volume, total_volume, short_ratio, market`) are identical across `fetch.parse_file`, `db._SV_COLS`, and all test fixtures. `fetch_day`/`run` signatures and the `(snapshot_id, day_count, row_count)` return tuple match between Task 4 code and its tests. View column names (`streak_days, streak_start, streak_end, peak_ratio, active`, `base`, `spike_ratio`) match between `_VIEWS` (Task 2) and the Task 3 tests. ✓
