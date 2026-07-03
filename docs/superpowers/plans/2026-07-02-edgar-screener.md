# SEC EDGAR Filing-Activity Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third screener (`edgar`) that pulls the SEC EDGAR daily filing index into SQLite as a time-series and exposes filing-activity trading signals via SQL views.

**Architecture:** A self-contained `edgar_screener/` package (`fetch.py`, `db.py`, `run.py`) mirroring `reddit_screener/`. Filings are parsed from `master.{date}.idx`, classified into signal buckets by form type, joined to tickers via `company_tickers.json`, and stored as immutable snapshots. "Rich" signals are ELT SQL views. A new `screener_common.py` holds the two genuinely-shared helpers (`connect`, generic `prune`); reddit is migrated onto it without behaviour change.

**Tech Stack:** Python 3 (stdlib only — `urllib`, `sqlite3`, `json`, `argparse`), pytest. No new dependencies.

## Global Constraints

- **Dependency-free:** stdlib only (`urllib`, `sqlite3`, `json`, `datetime`, `argparse`). No new packages in `pyproject.toml`.
- **SEC User-Agent required:** every HTTP request sends header `User-Agent: agentic-trading-bot ninadk.dev@gmail.com` (a generic client gets HTTP 403).
- **Source file:** `master.{YYYYMMDD}.idx` (pipe-delimited), NOT `form.idx`. Base URL `https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{n}/`.
- **CIK→ticker map:** `https://www.sec.gov/files/company_tickers.json`.
- **ELT principle:** store raw filings; every derived signal is a `CREATE VIEW IF NOT EXISTS`.
- **Dates:** index rows use `YYYYMMDD`; stored `filed_date`/`index_date` are `YYYY-MM-DD`; `captured_at` is ISO-8601 UTC.
- **TDD:** every task is red → green → commit. Reddit's existing tests must stay green throughout.
- **No commit co-author line** (repo convention).

## File Structure

- `screener_common.py` (new) — `connect(path)`, `prune(conn, keep_days, now_iso, *, child_table, child_fk="snapshot_id")`.
- `reddit_screener/db.py` (modify) — import `connect` from common; wrap `prune` binding `child_table="observations"`.
- `edgar_screener/__init__.py` (new, empty).
- `edgar_screener/fetch.py` (new) — `classify`, `parse_master`, `index_url`, `fetch_ticker_map`, `fetch_daily_index`.
- `edgar_screener/db.py` (new) — `_SCHEMA`, `ensure_schema`, `write_snapshot`, `upsert_issuers`, re-exported `connect`, wrapped `prune`.
- `edgar_screener/run.py` (new) — `run(...)`, `main(...)`.
- `registry.py` (modify) — add `"edgar"`.
- Tests: `tests/test_screener_common.py`, `tests/test_edgar_fetch.py`, `tests/test_edgar_db_schema.py`, `tests/test_edgar_db_write.py`, `tests/test_edgar_run.py`, `tests/test_registry.py` (extend).

---

### Task 1: Shared `screener_common` + reddit migration

**Files:**
- Create: `screener_common.py`
- Create: `tests/test_screener_common.py`
- Modify: `reddit_screener/db.py:1-2,75-78,127-138` (replace `connect`/`prune`, drop now-unused import)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `connect(path: str) -> sqlite3.Connection` — opens SQLite in WAL mode.
  - `prune(conn, keep_days: int, now_iso: str, *, child_table: str, child_fk: str = "snapshot_id") -> int` — deletes `snapshots` older than `keep_days` before `now_iso`, cascading to `child_table` first; returns count of snapshots removed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_screener_common.py`:

```python
import sqlite3

from screener_common import connect, prune


def _mk(conn):
    conn.executescript(
        "CREATE TABLE snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT);"
        "CREATE TABLE kids(snapshot_id INTEGER, v INTEGER);"
    )


def test_connect_sets_wal_mode(tmp_path):
    conn = connect(str(tmp_path / "x.db"))
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_prune_deletes_old_snapshots_and_children():
    conn = sqlite3.connect(":memory:")
    _mk(conn)
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (1, '2026-06-01T00:00:00+00:00')")
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (2, '2026-07-02T00:00:00+00:00')")
    conn.execute("INSERT INTO kids VALUES (1, 10), (2, 20)")
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00",
                    child_table="kids")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM kids").fetchone()[0] == 1
    assert conn.execute("SELECT snapshot_id FROM kids").fetchone()[0] == 2


def test_prune_no_old_snapshots_returns_zero():
    conn = sqlite3.connect(":memory:")
    _mk(conn)
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (1, '2026-07-02T00:00:00+00:00')")
    assert prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00",
                 child_table="kids") == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_screener_common.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'screener_common'`.

- [ ] **Step 3: Write minimal implementation**

Create `screener_common.py`:

```python
import sqlite3
from datetime import datetime, timedelta


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def prune(conn, keep_days: int, now_iso: str, *, child_table: str,
          child_fk: str = "snapshot_id") -> int:
    """Delete snapshots older than keep_days before now_iso, cascading to
    child_table first. Returns the number of snapshots removed."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM {child_table} WHERE {child_fk} IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_screener_common.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Migrate `reddit_screener/db.py` onto the shared helpers**

In `reddit_screener/db.py`, change the top import (line 1) from:

```python
import sqlite3
from datetime import datetime, timedelta
```

to:

```python
from screener_common import connect, prune as _prune
```

Delete the old `connect` function (lines ~75-78) and the old `prune` function (lines ~127-138), and in their place add a thin wrapper at the end of the file:

```python
def prune(conn, keep_days, now_iso):
    """Prune reddit snapshots + observations. Delegates to the shared helper."""
    return _prune(conn, keep_days, now_iso, child_table="observations")
```

(Leave `_SCHEMA`, `ensure_schema`, `write_snapshot`, `_asset_type`, `upsert_tickers` unchanged.)

- [ ] **Step 6: Run the full reddit + common suite to verify no behaviour change**

Run: `.venv/bin/pytest tests/test_screener_common.py tests/test_reddit_db_write.py tests/test_reddit_db_schema.py tests/test_reddit_run.py -v`
Expected: PASS (all reddit tests still green; `connect`/`prune` imported through reddit_screener.db work unchanged).

- [ ] **Step 7: Commit**

```bash
git add screener_common.py tests/test_screener_common.py reddit_screener/db.py
git commit -m "refactor: extract shared connect/prune into screener_common"
```

---

### Task 2: EDGAR parsing + form classification (pure functions)

**Files:**
- Create: `edgar_screener/__init__.py` (empty)
- Create: `edgar_screener/fetch.py`
- Create: `tests/test_edgar_fetch.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `classify(form: str) -> str` — returns one of `insider|event|stake|offering|periodic|other`.
  - `parse_master(text: str) -> list[dict]` — each dict has keys `cik(int), company(str), form(str), filed_date("YYYY-MM-DD"), path(str), accession(str), bucket(str)`.
  - `index_url(index_date: str, base: str = ARCHIVES_BASE) -> str` — builds the `master.{YYYYMMDD}.idx` URL for a `YYYY-MM-DD` date.
  - Module constant `ARCHIVES_BASE`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_edgar_fetch.py`:

```python
from edgar_screener.fetch import classify, index_url, parse_master

MASTER = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    Jun 2, 2025
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/
 
CIK|Company Name|Form Type|Date Filed|File Name
--------------------------------------------------------------------------------
1000623|Mativ Holdings, Inc.|4|20250602|edgar/data/1000623/0001562180-25-004291.txt
1318605|Tesla, Inc.|8-K|20250602|edgar/data/1318605/0001318605-25-000123.txt
789019|MICROSOFT CORP|424B5|20250602|edgar/data/789019/0000789019-25-000045.txt
garbage_line_without_pipes
999|Missing Path Co|10-Q|20250602
"""


def test_classify_buckets():
    assert classify("4") == "insider"
    assert classify("4/A") == "insider"
    assert classify("8-K") == "event"
    assert classify("SC 13D") == "stake"
    assert classify("SC 13G/A") == "stake"
    assert classify("S-1") == "offering"
    assert classify("424B5") == "offering"   # prefix match
    assert classify("424B2") == "offering"
    assert classify("10-K") == "periodic"
    assert classify("3") == "other"


def test_parse_master_extracts_valid_rows_only():
    rows = parse_master(MASTER)
    assert len(rows) == 3          # 2 malformed lines skipped
    first = rows[0]
    assert first["cik"] == 1000623
    assert first["company"] == "Mativ Holdings, Inc."
    assert first["form"] == "4"
    assert first["bucket"] == "insider"
    assert first["filed_date"] == "2025-06-02"
    assert first["accession"] == "0001562180-25-004291"
    assert first["path"] == "edgar/data/1000623/0001562180-25-004291.txt"


def test_parse_master_classifies_each_row():
    buckets = [r["bucket"] for r in parse_master(MASTER)]
    assert buckets == ["insider", "event", "offering"]


def test_index_url_computes_quarter():
    assert index_url("2025-06-02").endswith("/2025/QTR2/master.20250602.idx")
    assert index_url("2025-01-15").endswith("/2025/QTR1/master.20250115.idx")
    assert index_url("2025-12-31").endswith("/2025/QTR4/master.20251231.idx")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_edgar_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'edgar_screener'`.

- [ ] **Step 3: Write minimal implementation**

Create `edgar_screener/__init__.py` (empty file).

Create `edgar_screener/fetch.py`:

```python
from datetime import datetime

ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/daily-index"

_FORM_BUCKETS = {
    "4": "insider", "4/A": "insider",
    "8-K": "event", "8-K/A": "event",
    "SC 13D": "stake", "SC 13D/A": "stake",
    "SC 13G": "stake", "SC 13G/A": "stake",
    "S-1": "offering", "S-1/A": "offering",
    "10-K": "periodic", "10-K/A": "periodic",
    "10-Q": "periodic", "10-Q/A": "periodic",
}


def classify(form: str) -> str:
    """Map a raw SEC form type to a signal bucket."""
    if form in _FORM_BUCKETS:
        return _FORM_BUCKETS[form]
    if form.startswith("424B"):
        return "offering"
    return "other"


def parse_master(text: str) -> list[dict]:
    """Parse a pipe-delimited master.idx into filing dicts. Skips the header
    block (through the '---' divider) and any malformed line."""
    rows = []
    started = False
    for line in text.splitlines():
        if not started:
            if line.startswith("---"):
                started = True
            continue
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        cik, company, form, filed, path = parts
        try:
            cik_i = int(cik)
        except ValueError:
            continue
        accession = path.rsplit("/", 1)[-1]
        if accession.endswith(".txt"):
            accession = accession[:-4]
        rows.append({
            "cik": cik_i,
            "company": company,
            "form": form,
            "filed_date": f"{filed[:4]}-{filed[4:6]}-{filed[6:8]}",
            "path": path,
            "accession": accession,
            "bucket": classify(form),
        })
    return rows


def index_url(index_date: str, base: str = ARCHIVES_BASE) -> str:
    """Build the master.idx URL for a YYYY-MM-DD date, computing its quarter."""
    d = datetime.fromisoformat(index_date)
    qtr = (d.month - 1) // 3 + 1
    return f"{base}/{d.year}/QTR{qtr}/master.{d.strftime('%Y%m%d')}.idx"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_edgar_fetch.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add edgar_screener/__init__.py edgar_screener/fetch.py tests/test_edgar_fetch.py
git commit -m "feat: add EDGAR master.idx parser and form classifier"
```

---

### Task 3: EDGAR HTTP fetchers (ticker map + daily index)

**Files:**
- Modify: `edgar_screener/fetch.py` (append fetchers + constants)
- Modify: `tests/test_edgar_fetch.py` (append fetcher tests)

**Interfaces:**
- Consumes: `parse_master`, `index_url` (Task 2).
- Produces:
  - `fetch_ticker_map(url: str = TICKER_MAP_URL, get=_http_get) -> dict[int, dict]` — `{cik: {"ticker": str, "title": str}}`.
  - `fetch_daily_index(index_date: str, get=_http_get) -> list[dict] | None` — parsed rows, or `None` on HTTP 404.
  - Module constants `TICKER_MAP_URL`, `_UA`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_edgar_fetch.py`:

```python
import json
import urllib.error

from edgar_screener.fetch import fetch_daily_index, fetch_ticker_map


def test_fetch_ticker_map_indexes_by_cik():
    raw = json.dumps({
        "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    })
    tmap = fetch_ticker_map(get=lambda url: raw)
    assert tmap[320193] == {"ticker": "AAPL", "title": "Apple Inc."}
    assert tmap[1045810]["ticker"] == "NVDA"


def test_fetch_daily_index_parses_when_present():
    def fake_get(url):
        assert url.endswith("/2025/QTR2/master.20250602.idx")
        return MASTER
    rows = fetch_daily_index("2025-06-02", get=fake_get)
    assert [r["bucket"] for r in rows] == ["insider", "event", "offering"]


def test_fetch_daily_index_returns_none_on_404():
    def fake_get(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
    assert fetch_daily_index("2025-06-01", get=fake_get) is None


def test_fetch_daily_index_reraises_non_404():
    def fake_get(url):
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)
    try:
        fetch_daily_index("2025-06-01", get=fake_get)
        assert False, "expected HTTPError to propagate"
    except urllib.error.HTTPError as e:
        assert e.code == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_edgar_fetch.py -k fetch -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_daily_index'`.

- [ ] **Step 3: Write minimal implementation**

Append to `edgar_screener/fetch.py` (and add the two imports at the top — `import json`, `import urllib.error`, `import urllib.request`):

```python
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_ticker_map(url: str = TICKER_MAP_URL, get=_http_get) -> dict:
    """Load company_tickers.json into {cik: {'ticker':..., 'title':...}}."""
    raw = json.loads(get(url))
    return {int(v["cik_str"]): {"ticker": v["ticker"], "title": v["title"]}
            for v in raw.values()}


def fetch_daily_index(index_date: str, get=_http_get):
    """Fetch + parse master.idx for a date. Returns rows, or None on HTTP 404."""
    try:
        text = get(index_url(index_date))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return parse_master(text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_edgar_fetch.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add edgar_screener/fetch.py tests/test_edgar_fetch.py
git commit -m "feat: add EDGAR ticker-map and daily-index fetchers"
```

---

### Task 4: EDGAR schema + ELT views

**Files:**
- Create: `edgar_screener/db.py`
- Create: `tests/test_edgar_db_schema.py`

**Interfaces:**
- Consumes: `screener_common.connect` (Task 1).
- Produces:
  - `connect` (re-exported), `ensure_schema(conn) -> None`.
  - Tables `snapshots`, `filings`, `issuers`; views `v_latest`, `v_tickered`, `v_insider_activity`, `v_events`, `v_stakes`, `v_offerings`, `v_activity_history`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_edgar_db_schema.py`:

```python
from edgar_screener.db import connect, ensure_schema

TABLES = {"snapshots", "filings", "issuers"}
VIEWS = {"v_latest", "v_tickered", "v_insider_activity", "v_events",
         "v_stakes", "v_offerings", "v_activity_history"}


def test_schema_creates_tables_and_views():
    conn = connect(":memory:")
    ensure_schema(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')").fetchall()}
    assert TABLES <= names
    assert VIEWS <= names


def test_ensure_schema_is_idempotent():
    conn = connect(":memory:")
    ensure_schema(conn)
    ensure_schema(conn)  # must not raise
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='filings'").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_edgar_db_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'edgar_screener.db'`.

- [ ] **Step 3: Write minimal implementation**

Create `edgar_screener/db.py`:

```python
from screener_common import connect, prune as _prune

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    index_date   TEXT NOT NULL,
    filing_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS filings (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    accession   TEXT NOT NULL,
    cik         INTEGER NOT NULL,
    company     TEXT,
    ticker      TEXT,
    form        TEXT NOT NULL,
    bucket      TEXT NOT NULL,
    filed_date  TEXT NOT NULL,
    path        TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, accession, cik)
);
CREATE INDEX IF NOT EXISTS ix_filings_ticker ON filings(ticker);
CREATE INDEX IF NOT EXISTS ix_filings_bucket ON filings(bucket);
CREATE TABLE IF NOT EXISTS issuers (
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,
    company    TEXT,
    first_seen TEXT,
    last_seen  TEXT
);

-- Every filing from the most recent snapshot.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH latest AS (
    SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1
)
SELECT f.* FROM filings f JOIN latest l ON f.snapshot_id = l.id;

-- Latest filings from tickered (tradeable) issuers only.
CREATE VIEW IF NOT EXISTS v_tickered AS
SELECT * FROM v_latest WHERE ticker IS NOT NULL;

-- Insider (Form 4) filing count per ticker -> cluster detection.
CREATE VIEW IF NOT EXISTS v_insider_activity AS
SELECT ticker, company, COUNT(*) AS insider_filings
FROM v_tickered WHERE bucket = 'insider'
GROUP BY ticker, company
ORDER BY insider_filings DESC;

-- Latest material-event (8-K) filings per ticker.
CREATE VIEW IF NOT EXISTS v_events AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'event';

-- Latest activist/large-stake (13D/13G) filings.
CREATE VIEW IF NOT EXISTS v_stakes AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'stake';

-- Latest IPO / offering (S-1, 424B) filings.
CREATE VIEW IF NOT EXISTS v_offerings AS
SELECT ticker, company, form, accession, filed_date, path
FROM v_tickered WHERE bucket = 'offering';

-- Filings-per-ticker across index dates, with delta vs the prior stored day.
CREATE VIEW IF NOT EXISTS v_activity_history AS
WITH per_day AS (
    SELECT f.ticker AS ticker, s.index_date AS index_date,
           COUNT(*) AS filings_count
    FROM filings f JOIN snapshots s ON s.id = f.snapshot_id
    WHERE f.ticker IS NOT NULL
    GROUP BY f.ticker, s.index_date
)
SELECT ticker, index_date, filings_count,
       filings_count - LAG(filings_count) OVER (
           PARTITION BY ticker ORDER BY index_date) AS filings_delta_since_last
FROM per_day;
"""


def ensure_schema(conn) -> None:
    """Create tables + ELT views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def prune(conn, keep_days, now_iso):
    """Prune edgar snapshots + filings. Delegates to the shared helper."""
    return _prune(conn, keep_days, now_iso, child_table="filings")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_edgar_db_schema.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add edgar_screener/db.py tests/test_edgar_db_schema.py
git commit -m "feat: add EDGAR SQLite schema and filing-signal views"
```

---

### Task 5: EDGAR snapshot write + issuer upsert

**Files:**
- Modify: `edgar_screener/db.py` (append `write_snapshot`, `upsert_issuers`)
- Create: `tests/test_edgar_db_write.py`

**Interfaces:**
- Consumes: `connect`, `ensure_schema`, `prune` (Task 4).
- Produces:
  - `write_snapshot(conn, captured_at: str, index_date: str, rows: list[dict]) -> tuple[int, int]` — returns `(snapshot_id, count)`. Each row must carry `accession, cik, company, ticker, form, bucket, filed_date, path`.
  - `upsert_issuers(conn, rows: list[dict], captured_at: str) -> None` — upsert `issuers` by `cik`, preserving `first_seen`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_edgar_db_write.py`:

```python
from edgar_screener.db import (connect, ensure_schema, prune, upsert_issuers,
                               write_snapshot)


def _rows():
    return [
        {"accession": "0001-25-001", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "4", "bucket": "insider",
         "filed_date": "2025-06-02", "path": "edgar/data/1000623/0001-25-001.txt"},
        {"accession": "0002-25-002", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "4", "bucket": "insider",
         "filed_date": "2025-06-02", "path": "edgar/data/1000623/0002-25-002.txt"},
        {"accession": "0003-25-003", "cik": 999999, "company": "Private Co",
         "ticker": None, "form": "D", "bucket": "other",
         "filed_date": "2025-06-02", "path": "edgar/data/999999/0003-25-003.txt"},
    ]


def test_write_snapshot_stores_rows_and_count():
    conn = connect(":memory:")
    ensure_schema(conn)
    sid, n = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    assert n == 3
    assert conn.execute(
        "SELECT filing_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0] == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM filings WHERE snapshot_id=? AND cik=1000623",
        (sid,)).fetchone()[0] == 2


def test_v_insider_activity_counts_clusters():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    row = conn.execute(
        "SELECT insider_filings FROM v_insider_activity WHERE ticker='MATV'").fetchone()
    assert row[0] == 2


def test_v_tickered_excludes_untickered():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    tickers = {r[0] for r in conn.execute("SELECT ticker FROM v_tickered").fetchall()}
    assert tickers == {"MATV"}   # None-ticker 'D' filing excluded


def test_upsert_issuers_preserves_first_seen():
    conn = connect(":memory:")
    ensure_schema(conn)
    upsert_issuers(conn, _rows(), "2026-07-01T00:00:00+00:00")
    upsert_issuers(conn, _rows(), "2026-07-02T00:00:00+00:00")
    row = conn.execute(
        "SELECT ticker, first_seen, last_seen FROM issuers WHERE cik=1000623").fetchone()
    assert row == ("MATV", "2026-07-01T00:00:00+00:00", "2026-07-02T00:00:00+00:00")


def test_v_activity_history_deltas():
    conn = connect(":memory:")
    ensure_schema(conn)
    # day 1: MATV has 2 insider filings
    write_snapshot(conn, "2026-07-01T00:00:00+00:00", "2025-06-02", _rows())
    # day 2: MATV has 1 filing
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-03", [
        {"accession": "0009-25-009", "cik": 1000623, "company": "Mativ",
         "ticker": "MATV", "form": "8-K", "bucket": "event",
         "filed_date": "2025-06-03", "path": "edgar/data/1000623/0009-25-009.txt"}])
    delta = conn.execute(
        "SELECT filings_delta_since_last FROM v_activity_history "
        "WHERE ticker='MATV' AND index_date='2025-06-03'").fetchone()[0]
    assert delta == -1   # 1 - 2


def test_prune_removes_old_snapshots_and_filings():
    conn = connect(":memory:")
    ensure_schema(conn)
    write_snapshot(conn, "2026-06-01T00:00:00+00:00", "2025-06-01", _rows())
    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "2025-06-02", _rows())
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM filings").fetchone()[0] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_edgar_db_write.py -v`
Expected: FAIL with `ImportError: cannot import name 'write_snapshot'`.

- [ ] **Step 3: Write minimal implementation**

Append to `edgar_screener/db.py`:

```python
def write_snapshot(conn, captured_at: str, index_date: str,
                   rows: list[dict]) -> tuple[int, int]:
    """Insert one snapshot header + its filing rows. Returns (id, count)."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, index_date, filing_count) "
        "VALUES (?, ?, ?)",
        (captured_at, index_date, len(rows)),
    )
    snapshot_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO filings
           (snapshot_id, accession, cik, company, ticker, form, bucket,
            filed_date, path)
           VALUES (:sid, :accession, :cik, :company, :ticker, :form, :bucket,
                   :filed_date, :path)""",
        [{**r, "sid": snapshot_id} for r in rows],
    )
    conn.commit()
    return snapshot_id, len(rows)


def upsert_issuers(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the issuer dimension: refresh ticker/company/last_seen, keep
    first_seen. Dedupes by CIK within the batch."""
    seen = {}
    for r in rows:
        seen[r["cik"]] = (r.get("ticker"), r["company"])
    conn.executemany(
        """INSERT INTO issuers (cik, ticker, company, first_seen, last_seen)
           VALUES (:cik, :ticker, :company, :seen, :seen)
           ON CONFLICT(cik) DO UPDATE SET
             ticker=excluded.ticker,
             company=excluded.company,
             last_seen=excluded.last_seen""",
        [{"cik": c, "ticker": t, "company": n, "seen": captured_at}
         for c, (t, n) in seen.items()],
    )
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_edgar_db_write.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add edgar_screener/db.py tests/test_edgar_db_write.py
git commit -m "feat: add EDGAR snapshot write and issuer upsert"
```

---

### Task 6: EDGAR orchestration + CLI

**Files:**
- Create: `edgar_screener/run.py`
- Create: `tests/test_edgar_run.py`

**Interfaces:**
- Consumes: `edgar_screener.db` (`connect`, `ensure_schema`, `write_snapshot`, `upsert_issuers`, `prune`), `edgar_screener.fetch` (`fetch_daily_index`, `fetch_ticker_map`).
- Produces:
  - `run(db_path, index_date=None, keep_days=None, fetch_index=fetch.fetch_daily_index, fetch_map=fetch.fetch_ticker_map, now_iso=None) -> tuple[int, int]` — returns `(snapshot_id, filing_count)`.
  - `main(argv=None) -> None` — the registered CLI entry point.

- [ ] **Step 1: Write the failing test**

Create `tests/test_edgar_run.py`:

```python
import pytest

from edgar_screener.db import connect
from edgar_screener.run import run

TMAP = {1000623: {"ticker": "MATV", "title": "Mativ"}}


def _rows(form="4"):
    return [{"accession": "a1", "cik": 1000623, "company": "Mativ", "form": form,
             "bucket": "insider", "filed_date": "2025-06-02",
             "path": "edgar/data/1000623/a1.txt"},
            {"accession": "a2", "cik": 555, "company": "Private", "form": "D",
             "bucket": "other", "filed_date": "2025-06-02",
             "path": "edgar/data/555/a2.txt"}]


def test_run_joins_tickers_and_writes(tmp_path):
    db_path = str(tmp_path / "e.db")
    sid, n = run(db_path, index_date="2025-06-02",
                 fetch_index=lambda d: _rows(), fetch_map=lambda: TMAP,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 2
    conn = connect(db_path)
    got = dict(conn.execute("SELECT cik, ticker FROM filings").fetchall())
    assert got == {1000623: "MATV", 555: None}   # untickered stays NULL


def test_run_default_date_walks_back_to_latest(tmp_path):
    db_path = str(tmp_path / "e.db")
    calls = []

    def fake_index(d):
        calls.append(d)
        return _rows() if d == "2026-06-30" else None  # only this day exists

    run(db_path, fetch_index=fake_index, fetch_map=lambda: TMAP,
        now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT index_date FROM snapshots").fetchone()[0] == "2026-06-30"
    assert calls[:3] == ["2026-07-02", "2026-07-01", "2026-06-30"]


def test_run_explicit_missing_date_raises(tmp_path):
    db_path = str(tmp_path / "e.db")
    with pytest.raises(RuntimeError, match="no EDGAR index for 2025-06-01"):
        run(db_path, index_date="2025-06-01",
            fetch_index=lambda d: None, fetch_map=lambda: TMAP,
            now_iso="2026-07-02T00:00:00+00:00")


def test_run_empty_index_warns_and_writes_zero(tmp_path, capsys):
    db_path = str(tmp_path / "e.db")
    sid, n = run(db_path, index_date="2025-06-02",
                 fetch_index=lambda d: [], fetch_map=lambda: TMAP,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 0
    assert "0 filings" in capsys.readouterr().err
    conn = connect(db_path)
    assert conn.execute("SELECT filing_count FROM snapshots").fetchone()[0] == 0


def test_run_ticker_map_failure_writes_nothing(tmp_path):
    db_path = str(tmp_path / "e.db")

    def boom():
        raise RuntimeError("map down")

    with pytest.raises(RuntimeError, match="map down"):
        run(db_path, index_date="2025-06-02",
            fetch_index=lambda d: _rows(), fetch_map=boom,
            now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_run_second_run_appends_history(tmp_path):
    db_path = str(tmp_path / "e.db")
    run(db_path, index_date="2025-06-02", fetch_index=lambda d: _rows(),
        fetch_map=lambda: TMAP, now_iso="2026-07-01T00:00:00+00:00")
    run(db_path, index_date="2025-06-03", fetch_index=lambda d: _rows(),
        fetch_map=lambda: TMAP, now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_edgar_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'edgar_screener.run'`.

- [ ] **Step 3: Write minimal implementation**

Create `edgar_screener/run.py`:

```python
import argparse
import sys
from datetime import datetime, timedelta, timezone

from edgar_screener import db, fetch

_MAX_BACK = 5


def run(db_path, index_date=None, keep_days=None,
        fetch_index=fetch.fetch_daily_index, fetch_map=fetch.fetch_ticker_map,
        now_iso=None):
    """Fetch one EDGAR daily index, join tickers, append a snapshot.
    Returns (snapshot_id, filing_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    if index_date is None:
        day = datetime.fromisoformat(now_iso).date()
        rows = None
        for _ in range(_MAX_BACK + 1):
            index_date = day.isoformat()
            rows = fetch_index(index_date)
            if rows is not None:
                break
            day -= timedelta(days=1)
        if rows is None:
            raise RuntimeError(
                f"no EDGAR daily index in the {_MAX_BACK} days before {now_iso}")
    else:
        rows = fetch_index(index_date)
        if rows is None:
            raise RuntimeError(f"no EDGAR index for {index_date}")

    # Ticker map is core to the join; a failure here must abort before any write.
    tmap = fetch_map()
    for r in rows:
        info = tmap.get(r["cik"])
        r["ticker"] = info["ticker"] if info else None

    if not rows:
        print(f"warning: EDGAR index for {index_date} has 0 filings",
              file=sys.stderr)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        snapshot_id, count = db.write_snapshot(conn, now_iso, index_date, rows)
        db.upsert_issuers(conn, rows, now_iso)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="edgar",
        description="Pull the SEC EDGAR daily filing index into SQLite")
    p.add_argument("--db", default="edgar.db")
    p.add_argument("--date", default=None,
                   help="YYYY-MM-DD filing day (default: latest available)")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    _, count = run(a.db, index_date=a.date, keep_days=a.keep_days)
    print(f"stored {count} filings into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_edgar_run.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add edgar_screener/run.py tests/test_edgar_run.py
git commit -m "feat: add EDGAR run orchestration and CLI"
```

---

### Task 7: Register `edgar` in the dispatcher

**Files:**
- Modify: `registry.py:1-9`
- Modify: `tests/test_registry.py` (extend)

**Interfaces:**
- Consumes: `edgar_screener.run.main` (Task 6).
- Produces: `REGISTRY["edgar"]` routable via `registry.dispatch`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_registry.py`:

```python
def test_dispatch_lists_edgar():
    import registry
    assert "edgar" in registry.REGISTRY


def test_registry_has_all_three_screeners():
    import registry
    assert set(registry.REGISTRY) >= {"stocks", "reddit", "edgar"}
```

And update the existing `test_registry_has_both_screeners` assertion (line 29) to include edgar:

```python
def test_registry_has_both_screeners():
    assert set(registry.REGISTRY) >= {"stocks", "reddit", "edgar"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_registry.py -v`
Expected: FAIL — `edgar` not in `REGISTRY`.

- [ ] **Step 3: Write minimal implementation**

Edit `registry.py` to import and register edgar:

```python
import sys

from edgar_screener.run import main as edgar_main
from reddit_screener.run import main as reddit_main
from stock_analysis_screener.run import main as stocks_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
    "edgar": edgar_main,
}
```

(Leave the `dispatch` function below unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add registry.py tests/test_registry.py
git commit -m "feat: register edgar screener in the CLI dispatcher"
```

---

### Task 8: Full-suite gate + live smoke test

**Files:**
- None created (verification only).

**Interfaces:**
- Consumes: the entire built system.
- Produces: confidence that the whole suite is green and the live SEC pull works end-to-end.

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/pytest -q`
Expected: PASS — all tests across `stock_analysis_screener/`, `reddit_screener/`, `edgar_screener/`, and `screener_common` green.

- [ ] **Step 2: Live smoke pull against SEC (network)**

Run:
```bash
.venv/bin/python main.py edgar --db /tmp/edgar_smoke.db
```
Expected: prints `stored <N> filings into /tmp/edgar_smoke.db` with `N > 0`.

- [ ] **Step 3: Verify the tradeable subset and insider view are populated**

Run:
```bash
.venv/bin/python -c "
from edgar_screener.db import connect
c = connect('/tmp/edgar_smoke.db')
print('filings:', c.execute('SELECT COUNT(*) FROM filings').fetchone()[0])
print('tickered:', c.execute('SELECT COUNT(*) FROM v_tickered').fetchone()[0])
print('top insiders:', c.execute('SELECT ticker, insider_filings FROM v_insider_activity LIMIT 5').fetchall())
"
```
Expected: `filings` in the thousands, `tickered` non-zero (hundreds), `top insiders` a non-empty list of `(ticker, count)` pairs.

- [ ] **Step 4: Clean up the smoke DB**

Run: `rm -f /tmp/edgar_smoke.db /tmp/edgar_smoke.db-wal /tmp/edgar_smoke.db-shm`

- [ ] **Step 5: No commit** (verification task — nothing to commit).

---

## Notes for the implementer

- **Run pytest via `.venv/bin/pytest`** (the repo uses a `uv`-managed venv). If that path differs, use `uv run pytest`.
- **The `.venv/bin/python main.py edgar` smoke test hits the live SEC** — it must send the required User-Agent (already baked into `fetch._UA`). If it 403s, the UA header regressed.
- **Do not touch `stock_analysis_screener/`** (the stocks screener) — it is a different shape and out of scope.
- **Reddit parity:** after Task 1, re-run reddit's tests any time you touch shared code; they are the guard that the `screener_common` migration stayed behaviour-preserving.
