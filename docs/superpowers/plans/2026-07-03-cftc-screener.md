# CFTC COT Positioning Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `cftc` screener that pulls weekly CFTC Commitments of Traders (Legacy Futures-Only) positioning for a curated set of futures markets into SQLite, with views that expose the COT Index and net-positioning signals.

**Architecture:** Mirrors `fred_screener` module-for-module (`catalog`/`fetch`/`db`/`run`). Data is a *panel* — many markets × weekly report dates × ~25 positioning columns — stored in a `cot` fact table keyed by `(code, report_date)` and upserted (CFTC revises prior weeks). A `markets` dimension and a `snapshots` provenance table round it out. Derived signals live in SQL views. Fetch hits the Socrata SODA API, one incremental request per market.

**Tech Stack:** Python 3 standard library only (`urllib`, `sqlite3`, `argparse`, `json`), `pytest` for tests. Reuses `screener_common.connect`. No new dependencies.

## Global Constraints

- **Stdlib only** — no new third-party dependencies (match FRED/EDGAR).
- **Data source:** `https://publicreporting.cftc.gov/resource/6dca-aqww.json` (Legacy Futures-Only). No API key required.
- **Optional auth:** `CFTC_APP_TOKEN` from `.env`, sent as the `X-App-Token` **request header** (never a query param, never logged). Absent token → proceed anonymously.
- **Stable market key** is `cftc_contract_market_code` (alphanumeric string, e.g. `088691`), NOT the market name.
- **`report_date`** is stored as `YYYY-MM-DD` (the API returns a full timestamp `...T00:00:00.000` — truncate to the first 10 chars).
- **Fact table `cot` is upserted** by `(code, report_date)` — revised weeks overwrite in place; dates never duplicated. It is NOT snapshot-scoped.
- **Prune** deletes old `snapshots` rows only (FRED-style single-table); it must NEVER cascade into `cot`.
- **Skip-and-continue:** any per-market fetch error is logged as `type(e).__name__` only (never `str(e)`/URL) and the run proceeds.
- Reuse `screener_common.connect` (WAL). Register the screener as `"cftc"` in `registry.py`.

---

### Task 1: Package scaffold + curated market catalog

**Files:**
- Create: `cftc_screener/__init__.py` (empty)
- Create: `cftc_screener/catalog.py`
- Test: `tests/test_cftc_catalog.py`

**Interfaces:**
- Produces: `Market(code: str, name: str, asset_class: str)` frozen dataclass; `CATALOG: list[Market]`; `select_ids(all_codes, only, exclude, add=None) -> list[str]`.
- Consumes: nothing.

**Note on `select_ids`:** identical logic to `fred_screener.catalog.select_ids` (ordered, de-duplicated, blank/exclude-aware, `add` appended after selection). Reproduced in full below.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cftc_catalog.py
from cftc_screener.catalog import CATALOG, Market, select_ids

VALID_CLASSES = {"equity_index", "rates", "fx", "metals", "energy", "ags", "softs"}


def test_catalog_codes_are_unique():
    codes = [m.code for m in CATALOG]
    assert len(codes) == len(set(codes))


def test_catalog_entries_have_valid_asset_classes():
    assert CATALOG, "catalog must not be empty"
    for m in CATALOG:
        assert isinstance(m, Market)
        assert m.asset_class in VALID_CLASSES, f"{m.code} bad class {m.asset_class}"


def test_select_ids_defaults_to_full_catalog():
    all_codes = [m.code for m in CATALOG]
    assert select_ids(all_codes, only=None, exclude=None) == all_codes


def test_select_ids_only_subsets_and_preserves_order():
    assert select_ids(["A", "B", "C"], only=["C", "A"], exclude=None) == ["C", "A"]


def test_select_ids_excludes():
    assert select_ids(["A", "B", "C"], only=None, exclude=["B"]) == ["A", "C"]


def test_select_ids_strips_dedupes_and_drops_blanks():
    assert select_ids(["A"], only=["B", " B ", "", "C", "C"], exclude=None) == ["B", "C"]


def test_select_ids_appends_add_after_selection():
    assert select_ids(["A", "B"], only=None, exclude=None, add=["Z", "A"]) == ["A", "B", "Z"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cftc_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cftc_screener'`

- [ ] **Step 3: Create the empty package init**

```python
# cftc_screener/__init__.py
```
(empty file)

- [ ] **Step 4: Verify the catalog codes live, then write the catalog**

First confirm each code returns rows (drop any that return `[]`). Run this probe for the codes below and keep only those with a non-empty result:

```bash
for c in 13874A 20974 239742 12460P 042601 043602 044601 020601 099741 097741 096742 092741 090741 099741 098662 088691 084691 085692 076651 067651 023651 111659 022651 002602 005602 001602 007601 057642 054642 083731 080732 033661 073732; do
  n=$(curl -s -G "https://publicreporting.cftc.gov/resource/6dca-aqww.json" \
        --data-urlencode "\$where=cftc_contract_market_code='$c'" \
        --data-urlencode "\$select=count(*)" | python3 -c "import sys,json;print(json.load(sys.stdin)[0].get('count','0'))");
  echo "$c -> $n";
done
```

Then write the catalog. The codes below are a starting set — **replace any that returned 0** with the correct code found by name (query `market_and_exchange_names like '%NAME%'` as in the design doc). Verified-live codes (keep as-is): `13874A` E-mini S&P 500, `099741` Euro FX, `088691` Gold, `067651` WTI Crude (NYMEX).

```python
# cftc_screener/catalog.py
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    code: str          # cftc_contract_market_code — the stable key
    name: str          # human label (canonical name refreshed from newest row at write time)
    asset_class: str   # equity_index|rates|fx|metals|energy|ags|softs


# Curated COT reader. Codes verified live against the Socrata API on
# 2026-07-03; any that return no rows at implementation time are dropped or
# corrected here (see Task 1 Step 4).
CATALOG: list[Market] = [
    # equity_index
    Market("13874A", "E-Mini S&P 500", "equity_index"),
    Market("209742", "E-Mini Nasdaq-100", "equity_index"),
    Market("239742", "E-Mini Russell 2000", "equity_index"),
    Market("124603", "E-Mini Dow ($5)", "equity_index"),
    Market("1170E1", "VIX Futures", "equity_index"),
    # rates
    Market("042601", "2-Year T-Note", "rates"),
    Market("044601", "5-Year T-Note", "rates"),
    Market("043602", "10-Year T-Note", "rates"),
    Market("020601", "U.S. Treasury Bond", "rates"),
    Market("045601", "30-Day Fed Funds", "rates"),
    # fx
    Market("099741", "Euro FX", "fx"),
    Market("097741", "Japanese Yen", "fx"),
    Market("096742", "British Pound", "fx"),
    Market("092741", "Swiss Franc", "fx"),
    Market("090741", "Canadian Dollar", "fx"),
    Market("232741", "Australian Dollar", "fx"),
    Market("098662", "U.S. Dollar Index", "fx"),
    # metals
    Market("088691", "Gold", "metals"),
    Market("084691", "Silver", "metals"),
    Market("085692", "Copper", "metals"),
    Market("076651", "Platinum", "metals"),
    # energy
    Market("067651", "WTI Crude Oil", "energy"),
    Market("023651", "Natural Gas (Henry Hub)", "energy"),
    Market("111659", "RBOB Gasoline", "energy"),
    Market("022651", "NY Harbor ULSD", "energy"),
    # ags
    Market("002602", "Corn", "ags"),
    Market("005602", "Soybeans", "ags"),
    Market("001602", "Chicago Wheat (SRW)", "ags"),
    Market("007601", "Soybean Oil", "ags"),
    Market("057642", "Live Cattle", "ags"),
    Market("054642", "Lean Hogs", "ags"),
    # softs
    Market("080732", "Sugar No. 11", "softs"),
    Market("083731", "Coffee C", "softs"),
    Market("033661", "Cotton No. 2", "softs"),
    Market("073732", "Cocoa", "softs"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated codes to fetch: ``only`` (or the full
    catalog) minus ``exclude``, then any ``add`` codes appended. Tokens are
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

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_catalog.py -v`
Expected: PASS (all 7 tests). If `test_catalog_codes_are_unique` fails, a code was duplicated during verification — fix the catalog.

- [ ] **Step 6: Commit**

```bash
git add cftc_screener/__init__.py cftc_screener/catalog.py tests/test_cftc_catalog.py
git commit -m "feat(cftc): curated COT market catalog + select_ids"
```

---

### Task 2: Socrata fetch client

**Files:**
- Create: `cftc_screener/fetch.py`
- Test: `tests/test_cftc_fetch.py`

**Interfaces:**
- Consumes: nothing (self-contained HTTP client).
- Produces:
  - `_build_url(code, since=None, start=None, limit=50000) -> str`
  - `_make_opener(app_token=None) -> callable` (returns `opener(url) -> str`)
  - `_http_get(url, opener=_urlopen, attempts=5, base_delay=1.0, sleep=time.sleep) -> str`
  - `parse_rows(records: list[dict]) -> list[dict]` — each output row has keys `code`, `report_date`, `name`, plus the 25 data columns (see `_INT_FIELDS`/`_FLOAT_FIELDS`).
  - `fetch_market_rows(code, app_token=None, since=None, start=None, get=_http_get, opener=None) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cftc_fetch.py
import json
import urllib.error

import pytest

from cftc_screener.fetch import (
    _build_url, _http_get, _make_opener, fetch_market_rows, parse_rows,
)

# One realistic Socrata record (subset of the 133 fields), values as strings.
REC = {
    "cftc_contract_market_code": "088691",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-06-23T00:00:00.000",
    "open_interest_all": "352167",
    "noncomm_positions_long_all": "217028",
    "noncomm_positions_short_all": "35689",
    "noncomm_positions_spread": "31295",          # NOTE: no _all suffix
    "comm_positions_long_all": "64579",
    "comm_positions_short_all": "269983",
    "nonrept_positions_long_all": "39265",
    "nonrept_positions_short_all": "15200",
    "change_in_open_interest_all": "12837",
    "change_in_noncomm_long_all": "5901",
    "change_in_noncomm_short_all": "4782",
    "change_in_comm_long_all": "6359",
    "change_in_comm_short_all": "4200",
    "pct_of_oi_noncomm_long_all": "61.6",
    "pct_of_oi_noncomm_short_all": "10.1",
    "pct_of_oi_comm_long_all": "18.3",
    "pct_of_oi_comm_short_all": "76.7",
    "traders_tot_all": "282",
    "traders_noncomm_long_all": "152",
    "traders_noncomm_short_all": "61",
    "traders_comm_long_all": "45",
    "traders_comm_short_all": "46",
    "conc_net_le_4_tdr_long_all": "20.2",
    "conc_net_le_8_tdr_long_all": "28.4",
    "conc_net_le_4_tdr_short_all": "35.5",
    "conc_net_le_8_tdr_short_all": "51.1",
}


def test_parse_rows_maps_and_coerces():
    [row] = parse_rows([REC])
    assert row["code"] == "088691"
    assert row["report_date"] == "2026-06-23"          # timestamp truncated
    assert row["name"] == "GOLD - COMMODITY EXCHANGE INC."
    assert row["open_interest"] == 352167              # int
    assert row["noncomm_long"] == 217028
    assert row["noncomm_spread"] == 31295              # sourced from _spread (no _all)
    assert row["pct_oi_noncomm_long"] == 61.6          # float
    assert row["conc_net_8_short"] == 51.1
    assert row["traders_total"] == 282


def test_parse_rows_missing_fields_become_none():
    [row] = parse_rows([{"cftc_contract_market_code": "X",
                         "report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000"}])
    assert row["open_interest"] is None
    assert row["pct_oi_comm_long"] is None


def test_parse_rows_skips_records_without_code_or_date():
    assert parse_rows([{"report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000"}]) == []
    assert parse_rows([{"cftc_contract_market_code": "X"}]) == []


def test_build_url_full_history():
    url = _build_url("088691")
    assert url.startswith("https://publicreporting.cftc.gov/resource/6dca-aqww.json?")
    assert "cftc_contract_market_code%3D%27088691%27" in url  # code='088691' urlencoded
    assert "report_date_as_yyyy_mm_dd" in url and "order" in url


def test_build_url_incremental_uses_since():
    url = _build_url("088691", since="2026-06-23")
    assert "2026-06-23T00%3A00%3A00" in url  # > 'since T00:00:00'


def test_make_opener_attaches_app_token_header():
    seen = {}

    class FakeResp:
        def read(self): return b"[]"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        seen["headers"] = req.headers
        return FakeResp()

    import cftc_screener.fetch as f
    opener = _make_opener("TOKEN123")
    orig = f.urllib.request.urlopen
    f.urllib.request.urlopen = fake_urlopen
    try:
        opener("http://x")
    finally:
        f.urllib.request.urlopen = orig
    # urllib capitalizes header keys: "X-app-token"
    assert seen["headers"].get("X-app-token") == "TOKEN123"


def test_make_opener_without_token_is_default():
    assert _make_opener(None).__name__ == "_urlopen"


def test_fetch_market_rows_parses_and_passes_since():
    seen = {}

    def fake_get(url, opener=None):
        seen["url"] = url
        return json.dumps([REC])

    rows = fetch_market_rows("088691", since="2026-06-16", get=fake_get)
    assert rows[0]["code"] == "088691"
    assert "2026-06-16T00%3A00%3A00" in seen["url"]


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cftc_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cftc_screener.fetch'`

- [ ] **Step 3: Write the fetch client**

```python
# cftc_screener/fetch.py
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # Socrata throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_LIMIT = 50000  # Socrata max; > full weekly history for any market

# (db_column, socrata_field) for integer-valued columns. All "_all" (all
# contracts) except the spread field, which the API names WITHOUT the suffix.
_INT_FIELDS = [
    ("open_interest", "open_interest_all"),
    ("noncomm_long", "noncomm_positions_long_all"),
    ("noncomm_short", "noncomm_positions_short_all"),
    ("noncomm_spread", "noncomm_positions_spread"),
    ("comm_long", "comm_positions_long_all"),
    ("comm_short", "comm_positions_short_all"),
    ("nonrept_long", "nonrept_positions_long_all"),
    ("nonrept_short", "nonrept_positions_short_all"),
    ("chg_oi", "change_in_open_interest_all"),
    ("chg_noncomm_long", "change_in_noncomm_long_all"),
    ("chg_noncomm_short", "change_in_noncomm_short_all"),
    ("chg_comm_long", "change_in_comm_long_all"),
    ("chg_comm_short", "change_in_comm_short_all"),
    ("traders_total", "traders_tot_all"),
    ("traders_noncomm_long", "traders_noncomm_long_all"),
    ("traders_noncomm_short", "traders_noncomm_short_all"),
    ("traders_comm_long", "traders_comm_long_all"),
    ("traders_comm_short", "traders_comm_short_all"),
]
_FLOAT_FIELDS = [
    ("pct_oi_noncomm_long", "pct_of_oi_noncomm_long_all"),
    ("pct_oi_noncomm_short", "pct_of_oi_noncomm_short_all"),
    ("pct_oi_comm_long", "pct_of_oi_comm_long_all"),
    ("pct_oi_comm_short", "pct_of_oi_comm_short_all"),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all"),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all"),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all"),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all"),
]


def _build_url(code: str, since=None, start=None, limit: int = _LIMIT) -> str:
    """Socrata SODA query for one market, ordered by report date ascending.
    ``since`` (YYYY-MM-DD) fetches strictly newer weeks; else ``start`` sets an
    inclusive floor; else full history."""
    clauses = [f"cftc_contract_market_code='{code}'"]
    if since:
        clauses.append(f"report_date_as_yyyy_mm_dd > '{since}T00:00:00'")
    elif start:
        clauses.append(f"report_date_as_yyyy_mm_dd >= '{start}T00:00:00'")
    params = {"$where": " AND ".join(clauses),
              "$order": "report_date_as_yyyy_mm_dd",
              "$limit": limit}
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


def _urlopen(url: str) -> str:  # default opener, no app token
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def _make_opener(app_token=None):
    """Return an opener(url)->str. With a token, attach X-App-Token; else the
    plain default opener."""
    if not app_token:
        return _urlopen
    headers = {**_UA, "X-App-Token": app_token}

    def opener(url: str) -> str:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", "replace")
    return opener


def _retry_delay(err, attempt: int, base_delay: float) -> float:
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET a URL as text with bounded exponential backoff. Retryable: Socrata
    throttling (429), transient 5xx, and transient network errors. Other HTTP
    errors raise immediately."""
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


def _num(raw, cast):
    if raw is None or raw == "":
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def parse_rows(records: list) -> list[dict]:
    """Map Socrata records to curated rows. Coerce numeric strings, absent
    cells to None, and truncate the report timestamp to YYYY-MM-DD. Records
    missing a code or report date are skipped."""
    out = []
    for rec in records:
        code = rec.get("cftc_contract_market_code")
        raw_date = rec.get("report_date_as_yyyy_mm_dd")
        if not code or not raw_date:
            continue
        row = {"code": code, "report_date": raw_date[:10],
               "name": rec.get("market_and_exchange_names")}
        for col, api in _INT_FIELDS:
            row[col] = _num(rec.get(api), int)
        for col, api in _FLOAT_FIELDS:
            row[col] = _num(rec.get(api), float)
        out.append(row)
    return out


def fetch_market_rows(code: str, app_token=None, since=None, start=None,
                      get=_http_get, opener=None) -> list[dict]:
    """Fetch one market's COT rows (incremental when ``since`` given)."""
    op = opener if opener is not None else _make_opener(app_token)
    url = _build_url(code, since=since, start=start)
    return parse_rows(json.loads(get(url, opener=op)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_fetch.py -v`
Expected: PASS (all tests). If `test_make_opener_attaches_app_token_header` fails on the header key case, print `seen["headers"]` — urllib title-cases header names to `X-app-token`.

- [ ] **Step 5: Commit**

```bash
git add cftc_screener/fetch.py tests/test_cftc_fetch.py
git commit -m "feat(cftc): Socrata fetch client with backoff, app-token header, row parsing"
```

---

### Task 3: SQLite storage layer (schema tables + writers)

**Files:**
- Create: `cftc_screener/db.py`
- Test: `tests/test_cftc_db_schema.py`, `tests/test_cftc_db_write.py`

**Interfaces:**
- Consumes: `screener_common.connect`.
- Produces:
  - `connect(path)` (re-exported), `ensure_schema(conn)`
  - `upsert_markets(conn, rows: list[dict], captured_at: str)` — each row `{code, name, asset_class}`
  - `write_cot(conn, code: str, rows: list[dict]) -> int` — rows are `parse_rows` output
  - `max_report_date(conn, code: str) -> str | None`
  - `write_snapshot(conn, captured_at, market_count, row_count) -> int`
  - `prune(conn, keep_days: int, now_iso: str) -> int`
  - `_COT_COLS: list[str]` (the 25 data-column names, shared with Task 4)

Views are added in Task 4; this task's `ensure_schema` creates tables only.

- [ ] **Step 1: Write the failing schema test**

```python
# tests/test_cftc_db_schema.py
from cftc_screener import db


def test_ensure_schema_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # second call must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"markets", "cot", "snapshots"} <= tables


def test_cot_has_expected_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot)")}
    assert {"code", "report_date", "open_interest", "noncomm_long",
            "noncomm_spread", "pct_oi_comm_short", "conc_net_8_short"} <= cols
```

- [ ] **Step 2: Write the failing writer test**

```python
# tests/test_cftc_db_write.py
from cftc_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _market(code="088691", name="GOLD", asset_class="metals"):
    return {"code": code, "name": name, "asset_class": asset_class}


def _cot_row(code, date, **vals):
    row = {"code": code, "report_date": date}
    row.update(vals)
    return row


def test_upsert_markets_preserves_first_seen_and_refreshes_name():
    conn = _fresh()
    db.upsert_markets(conn, [_market(name="OLD NAME")], "2026-01-01T00:00:00+00:00")
    db.upsert_markets(conn, [_market(name="NEW NAME")], "2026-07-03T00:00:00+00:00")
    first_seen, last_seen, name = conn.execute(
        "SELECT first_seen, last_seen, name FROM markets WHERE code='088691'"
    ).fetchone()
    assert first_seen == "2026-01-01T00:00:00+00:00"
    assert last_seen == "2026-07-03T00:00:00+00:00"
    assert name == "NEW NAME"


def test_write_cot_upserts_by_code_and_date():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    n1 = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-16", open_interest=100, noncomm_long=10),
        _cot_row("088691", "2026-06-23", open_interest=200, noncomm_long=20),
    ])
    assert n1 == 2
    # Revised prior week + one new week
    n2 = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-23", open_interest=250, noncomm_long=25),  # revision
        _cot_row("088691", "2026-06-30", open_interest=300, noncomm_long=30),  # new
    ])
    assert n2 == 2
    rows = conn.execute(
        "SELECT report_date, open_interest FROM cot WHERE code='088691' "
        "ORDER BY report_date").fetchall()
    assert rows == [("2026-06-16", 100), ("2026-06-23", 250), ("2026-06-30", 300)]


def test_write_cot_dedupes_within_batch_last_wins():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    n = db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-23", open_interest=1),
        _cot_row("088691", "2026-06-23", open_interest=9),  # same date, later wins
    ])
    assert n == 1
    val = conn.execute(
        "SELECT open_interest FROM cot WHERE code='088691'").fetchone()[0]
    assert val == 9


def test_max_report_date_returns_none_when_empty_then_latest():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    assert db.max_report_date(conn, "088691") is None
    db.write_cot(conn, "088691", [
        _cot_row("088691", "2026-06-16", open_interest=1),
        _cot_row("088691", "2026-06-23", open_interest=2),
    ])
    assert db.max_report_date(conn, "088691") == "2026-06-23"


def test_prune_deletes_old_snapshots_but_not_cot():
    conn = _fresh()
    db.upsert_markets(conn, [_market()], "2026-07-03T00:00:00+00:00")
    db.write_cot(conn, "088691", [_cot_row("088691", "2020-01-07", open_interest=1)])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)  # old
    db.write_snapshot(conn, "2026-07-01T00:00:00+00:00", 1, 1)  # recent
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 1  # preserved
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_cftc_db_schema.py tests/test_cftc_db_write.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cftc_screener.db'`

- [ ] **Step 4: Write the storage layer**

```python
# cftc_screener/db.py
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_markets", "write_cot",
           "max_report_date", "write_snapshot", "prune"]

# The 25 curated data columns of `cot` (order matters for INSERT/UPDATE reuse).
_COT_COLS = [
    "open_interest",
    "noncomm_long", "noncomm_short", "noncomm_spread",
    "comm_long", "comm_short",
    "nonrept_long", "nonrept_short",
    "chg_oi", "chg_noncomm_long", "chg_noncomm_short",
    "chg_comm_long", "chg_comm_short",
    "pct_oi_noncomm_long", "pct_oi_noncomm_short",
    "pct_oi_comm_long", "pct_oi_comm_short",
    "traders_total", "traders_noncomm_long", "traders_noncomm_short",
    "traders_comm_long", "traders_comm_short",
    "conc_net_4_long", "conc_net_8_long", "conc_net_4_short", "conc_net_8_short",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    code        TEXT PRIMARY KEY,
    name        TEXT,
    asset_class TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS cot (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    noncomm_long  INTEGER, noncomm_short INTEGER, noncomm_spread INTEGER,
    comm_long     INTEGER, comm_short    INTEGER,
    nonrept_long  INTEGER, nonrept_short INTEGER,
    chg_oi        INTEGER,
    chg_noncomm_long INTEGER, chg_noncomm_short INTEGER,
    chg_comm_long INTEGER, chg_comm_short INTEGER,
    pct_oi_noncomm_long REAL, pct_oi_noncomm_short REAL,
    pct_oi_comm_long REAL, pct_oi_comm_short REAL,
    traders_total INTEGER,
    traders_noncomm_long INTEGER, traders_noncomm_short INTEGER,
    traders_comm_long INTEGER, traders_comm_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_date ON cot(report_date);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    market_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""


def ensure_schema(conn) -> None:
    """Create tables + indexes. Idempotent. (Views added in cftc db views.)"""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_markets(conn, rows: list[dict], captured_at: str) -> None:
    """Upsert the market dimension: refresh name/asset_class/last_seen, preserve
    first_seen."""
    params = [{"code": r["code"], "name": r.get("name"),
               "asset_class": r.get("asset_class"), "seen": captured_at}
              for r in rows]
    conn.executemany(
        """INSERT INTO markets (code, name, asset_class, first_seen, last_seen)
           VALUES (:code, :name, :asset_class, :seen, :seen)
           ON CONFLICT(code) DO UPDATE SET
             name=excluded.name, asset_class=excluded.asset_class,
             last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_cot(conn, code: str, rows: list[dict]) -> int:
    """Upsert COT rows by (code, report_date). Revised weeks overwrite in place;
    dates never duplicated. Dedupes within the batch (last wins)."""
    by_date = {r["report_date"]: r for r in rows}
    cols = ["code", "report_date"] + _COT_COLS
    placeholders = ", ".join(":" + c for c in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _COT_COLS)
    params = []
    for date, r in by_date.items():
        p = {"code": code, "report_date": date}
        for c in _COT_COLS:
            p[c] = r.get(c)
        params.append(p)
    conn.executemany(
        f"INSERT INTO cot ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(code, report_date) DO UPDATE SET {updates}",
        params,
    )
    conn.commit()
    return len(by_date)


def max_report_date(conn, code: str):
    """Latest stored report_date for a market, or None if it has no rows."""
    row = conn.execute(
        "SELECT MAX(report_date) FROM cot WHERE code=?", (code,)).fetchone()
    return row[0] if row and row[0] else None


def write_snapshot(conn, captured_at: str, market_count: int,
                   row_count: int) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, market_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, market_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    COT history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — do NOT cascade into cot."""
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

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_db_schema.py tests/test_cftc_db_write.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add cftc_screener/db.py tests/test_cftc_db_schema.py tests/test_cftc_db_write.py
git commit -m "feat(cftc): sqlite schema, market/cot upserts, snapshot prune"
```

---

### Task 4: Derived signal views (COT Index, positioning, extremes)

**Files:**
- Modify: `cftc_screener/db.py` (add `_VIEWS`, run it in `ensure_schema`)
- Test: `tests/test_cftc_db_views.py`

**Interfaces:**
- Consumes: the tables + `write_cot`/`upsert_markets` from Task 3.
- Produces views: `v_net`, `v_latest`, `v_cot_index`, `v_cot_index_latest`, `v_positioning`, `v_extremes`.

- [ ] **Step 1: Write the failing view test**

```python
# tests/test_cftc_db_views.py
from cftc_screener import db


def _seed(conn, code, series, name="M", asset_class="metals"):
    """series: list of (report_date, noncomm_long, noncomm_short)."""
    db.upsert_markets(conn, [{"code": code, "name": name,
                              "asset_class": asset_class}],
                      "2026-07-03T00:00:00+00:00")
    rows = [{"code": code, "report_date": d,
             "noncomm_long": lo, "noncomm_short": sh, "open_interest": 1000}
            for (d, lo, sh) in series]
    db.write_cot(conn, code, rows)


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_net_computes_net_positions():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-23", 217028, 35689)])
    net = conn.execute(
        "SELECT net_noncomm FROM v_net WHERE code='G'").fetchone()[0]
    assert net == 217028 - 35689


def test_v_latest_picks_most_recent_week():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-09", 10, 0), ("2026-06-23", 50, 0),
                      ("2026-06-16", 20, 0)])
    row = conn.execute(
        "SELECT report_date, net_noncomm FROM v_latest WHERE code='G'").fetchone()
    assert row == ("2026-06-23", 50)


def test_cot_index_is_percentile_within_range():
    conn = _fresh()
    # net walks 0, 100, then 50 (latest). Window covers all 3: lo=0, hi=100.
    _seed(conn, "G", [("2026-06-09", 0, 0), ("2026-06-16", 100, 0),
                      ("2026-06-23", 50, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='G'").fetchone()[0]
    assert abs(idx - 50.0) < 1e-9


def test_cot_index_is_100_at_max():
    conn = _fresh()
    _seed(conn, "G", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_cot_index_latest WHERE code='G'").fetchone()[0]
    assert idx == 100.0


def test_v_extremes_flags_crowded_market_only():
    conn = _fresh()
    _seed(conn, "HOT", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])   # index 100
    # net walks 0, 100, then 50 (latest) -> lo=0, hi=100 -> index 50 (mid-range)
    _seed(conn, "MILD", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0),
                         ("2026-06-30", 50, 0)])                          # index 50
    codes = {r[0] for r in conn.execute("SELECT code FROM v_extremes")}
    assert "HOT" in codes
    assert "MILD" not in codes
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cftc_db_views.py -v`
Expected: FAIL — `sqlite3.OperationalError: no such table: v_net` (views not created yet).

- [ ] **Step 3: Add the views to `db.py`**

Add this constant after `_SCHEMA`:

```python
_VIEWS = """
CREATE VIEW IF NOT EXISTS v_net AS
SELECT code, report_date, open_interest,
       noncomm_long - noncomm_short AS net_noncomm,
       comm_long    - comm_short    AS net_comm,
       nonrept_long - nonrept_short AS net_nonrept
FROM cot;

CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_noncomm, r.net_comm, r.net_nonrept
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

-- COT Index: net non-commercial position as a 0-100 percentile within its own
-- trailing 156-week (3-year) range. 90+/10- = crowded long/short.
CREATE VIEW IF NOT EXISTS v_cot_index AS
WITH w AS (
    SELECT code, report_date, net_noncomm,
           MIN(net_noncomm) OVER win AS lo,
           MAX(net_noncomm) OVER win AS hi
    FROM v_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_noncomm, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_noncomm - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_noncomm, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_cot_index)
SELECT code, report_date, net_noncomm, cot_index FROM ranked WHERE rn = 1;

-- Positioning board: latest net positions, COT index, %OI, and WoW changes.
CREATE VIEW IF NOT EXISTS v_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_noncomm, l.net_comm, l.net_nonrept,
       ci.cot_index,
       c.pct_oi_noncomm_long, c.pct_oi_noncomm_short,
       c.chg_oi, c.chg_noncomm_long, c.chg_noncomm_short
FROM v_latest l
JOIN v_cot_index_latest ci ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_extremes AS
SELECT * FROM v_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""
```

Then update `ensure_schema` to create views after tables:

```python
def ensure_schema(conn) -> None:
    """Create tables, indexes, and derived-signal views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_db_views.py tests/test_cftc_db_schema.py -v`
Expected: PASS (views tests + schema idempotency still green).

- [ ] **Step 5: Commit**

```bash
git add cftc_screener/db.py tests/test_cftc_db_views.py
git commit -m "feat(cftc): COT index + positioning + extremes views"
```

---

### Task 5: Run orchestration + CLI

**Files:**
- Create: `cftc_screener/run.py`
- Test: `tests/test_cftc_run.py`

**Interfaces:**
- Consumes: `catalog.CATALOG`/`select_ids`, `db.*`, `fetch.fetch_market_rows`.
- Produces:
  - `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, app_token=None, fetch_rows=fetch.fetch_market_rows, now_iso=None) -> (snapshot_id, market_count, row_count)`
  - `main(argv=None)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cftc_run.py
from cftc_screener import db, run as run_mod
from cftc_screener.catalog import Market

NOW = "2026-07-03T00:00:00+00:00"


def _rows(code, series):
    """series: list of (date, noncomm_long). Newest last (fetch orders ascending)."""
    return [{"code": code, "report_date": d, "name": f"name-{code}",
             "noncomm_long": lo, "noncomm_short": 0, "open_interest": 1000}
            for (d, lo) in series]


def test_run_happy_path_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("A", "Alpha", "metals"),
                         Market("B", "Beta", "energy")])

    def fake_fetch(code, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-16", 10), ("2026-06-23", 20)])

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)
    assert mc == 2
    assert rc == 4  # 2 markets * 2 weeks
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0] == 2
    # market name comes from the newest fetched row
    assert conn.execute("SELECT name FROM markets WHERE code='A'").fetchone()[0] == "name-A"


def test_run_skips_failing_market_and_continues(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("GOOD", "G", "metals"),
                         Market("BAD", "B", "metals")])

    def flaky(code, app_token=None, since=None, start=None):
        if code == "BAD":
            raise RuntimeError("boom")
        return _rows(code, [("2026-06-23", 5)])

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=flaky)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["GOOD"]
    assert "BAD" in capsys.readouterr().err


def test_run_passes_since_from_max_stored_date(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    seen = {}

    def fake_fetch(code, app_token=None, since=None, start=None):
        seen.setdefault("since", []).append(since)
        # First call: full history; second call would be incremental.
        return _rows(code, [("2026-06-16", 1), ("2026-06-23", 2)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # since=None (empty db)
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)   # since=latest stored
    assert seen["since"] == [None, "2026-06-23"]


def test_run_all_fail_writes_zero_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("BAD", "B", "metals")])

    def boom(code, app_token=None, since=None, start=None):
        raise RuntimeError("nope")

    dbp = str(tmp_path / "cftc.db")
    sid, mc, rc = run_mod.run(dbp, now_iso=NOW, fetch_rows=boom)
    assert (mc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT market_count, row_count FROM snapshots").fetchone() == (0, 0)


def test_run_only_selects_subset(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("A", "Alpha", "metals"),
                         Market("B", "Beta", "metals")])

    def fake_fetch(code, app_token=None, since=None, start=None):
        return _rows(code, [("2026-06-23", 1)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, only=["B"], now_iso=NOW, fetch_rows=fake_fetch)
    conn = db.connect(dbp)
    assert [r[0] for r in conn.execute("SELECT code FROM markets")] == ["B"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cftc_run.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cftc_screener.run'`

- [ ] **Step 3: Write the orchestration + CLI**

```python
# cftc_screener/run.py
import argparse
import os
import sys
from datetime import datetime, timezone

from cftc_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        app_token=None, fetch_rows=fetch.fetch_market_rows, now_iso=None):
    """Fetch selected CFTC markets into SQLite, upserting weekly COT history.
    Returns (snapshot_id, market_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    app_token = app_token or os.environ.get("CFTC_APP_TOKEN")  # optional; may be None

    asset = {m.code: m.asset_class for m in catalog.CATALOG}
    all_codes = [m.code for m in catalog.CATALOG]
    codes = catalog.select_ids(all_codes, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_rows = 0
        for code in codes:
            try:
                since = db.max_report_date(conn, code)
                rows = fetch_rows(code, app_token=app_token, since=since,
                                  start=start)
            except Exception as e:  # skip-and-continue on any per-market failure
                # Log only the exception class — never str(e)/e.url, which may
                # echo the request URL or token.
                print(f"warning: skipping {code}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            if rows:
                name = rows[-1].get("name")  # ordered ascending -> newest last
                db.upsert_markets(conn, [{"code": code, "name": name,
                                          "asset_class": asset.get(code, "custom")}],
                                  now_iso)
                total_rows += db.write_cot(conn, code, rows)
            successes += 1

        if successes == 0:
            print("warning: no CFTC markets fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cftc",
        description="Pull curated CFTC COT positioning into SQLite")
    p.add_argument("--db", default="cftc.db")
    p.add_argument("--only", default=None,
                   help="comma-separated contract codes to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated contract codes to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra contract code not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="earliest report date YYYY-MM-DD (default: full history)")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, mc, rc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days)
    print(f"stored {rc} weekly rows across {mc} markets into {a.db}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cftc_run.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add cftc_screener/run.py tests/test_cftc_run.py
git commit -m "feat(cftc): run orchestration + CLI with incremental fetch and skip-and-continue"
```

---

### Task 6: Register in dispatcher + document env var

**Files:**
- Modify: `registry.py:1-13`
- Modify: `.env.example`
- Modify: `tests/test_registry.py`

**Interfaces:**
- Consumes: `cftc_screener.run.main`.
- Produces: `"cftc"` entry in `registry.REGISTRY`.

- [ ] **Step 1: Extend the registry test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_cftc():
    import registry
    assert "cftc" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_registry.py::test_dispatch_lists_cftc -v`
Expected: FAIL with `AssertionError` (cftc not registered).

- [ ] **Step 3: Register the screener**

Edit `registry.py` — add the import and the registry entry:

```python
import sys

from cftc_screener.run import main as cftc_main
from edgar_screener.run import main as edgar_main
from fred_screener.run import main as fred_main
from reddit_screener.run import main as reddit_main
from stock_analysis_screener.run import main as stocks_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
    "edgar": edgar_main,
    "fred": fred_main,
    "cftc": cftc_main,
}
```

- [ ] **Step 4: Document the optional env var**

Append to `.env.example` (leave existing lines intact):

```
CFTC_APP_TOKEN= # optional Socrata app token (lifts rate limits; not required)
```

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: PASS — the whole suite green, including all `test_cftc_*` and the extended registry test.

- [ ] **Step 6: Smoke-test against the live API (one market, tiny pull)**

```bash
python main.py cftc --db /tmp/cftc_smoke.db --only 088691 --start 2026-01-01
```
Expected: prints `stored N weekly rows across 1 markets into /tmp/cftc_smoke.db` (N ≈ 20–26). Then verify the signal view:
```bash
python3 -c "import sqlite3; c=sqlite3.connect('/tmp/cftc_smoke.db'); print(c.execute('SELECT code, report_date, net_noncomm, cot_index FROM v_cot_index_latest').fetchall())"
```
Expected: one row for `088691` with a numeric `net_noncomm` and a `cot_index` between 0 and 100. Clean up: `rm /tmp/cftc_smoke.db*`.

- [ ] **Step 7: Commit**

```bash
git add registry.py .env.example tests/test_registry.py
git commit -m "feat(cftc): register cftc screener + document optional app token"
```

---

## Notes for the implementer

- **Catalog codes are the one live-data dependency.** Task 1 Step 4 is not optional — a wrong/renamed code silently fetches nothing (the run logs no error because an empty result is valid). Verify every code returns rows before trusting the catalog.
- **Why `noncomm_spread` has no `_all`:** confirmed against a live Gold record — the API names the all-contracts spread field `noncomm_positions_spread` (the `_1` variant is the "old crop" split). This is the single field that breaks the otherwise-uniform `*_all` naming.
- **COT Index needs history to be meaningful.** With `--start` set recently (as in the smoke test), the 3-year window is short, so `cot_index` reflects only the pulled range. Full-history runs (no `--start`) give the real 156-week percentile.
- **Do not enable `PRAGMA foreign_keys`** — `screener_common.connect` doesn't, and the code upserts markets before COT rows regardless.
