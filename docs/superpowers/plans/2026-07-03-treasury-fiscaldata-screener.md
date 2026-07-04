# U.S. Treasury Fiscal Data Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `treasury` screener — a liquidity & supply reader pulling curated U.S. Treasury Fiscal Data datasets (TGA cash balance, debt-to-the-penny, average interest rates, the announced-auction forward calendar, auction results) plus the official par yield curve into SQLite as per-dataset time-series/panel tables, with derived liquidity/supply/curve views.

**Architecture:** A data screener in the FRED/CFTC mould (`catalog`/`fetch`/`db`/`run` + registry) — **time-series/panel shape**, records upserted by their natural `(…, record_date)` key, history not snapshot-scoped. Reuses `screener_common.connect` (WAL), the `http_client` bounded-backoff, and the FRED-style `select_ids` + single-table prune. Two fetch modes: the key-free FiscalData JSON:API (paged) and one XML branch for the Treasury par yield-curve feed. **No credentials.**

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `xml.etree.ElementTree`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** FiscalData + the Treasury XML feed are public/key-free; `.env.example` unchanged. Descriptive UA `agentic-trading-bot ninadk.dev@gmail.com`; retry `{429, 500, 502, 503, 504}` via `http_client`.
- **`now_iso` injected, never wall-clock in logic.** `run()` accepts `now_iso=None`, defaulting to UTC now; fetchers injected so tests are network-free.
- **Panel upsert, never duplicate keys.** Each `write_<table>` upserts on the table's natural key; a revised (restated) row overwrites in place; batches dedupe by key (last wins) — the FRED `write_observations` shape.
- **Skip-and-continue** per dataset: `conn.rollback()` the failed dataset, log **only** `type(e).__name__` (never `str(e)`/`e.url`), continue. Zero successes → still `write_snapshot(…, 0, 0)` and warn; never raise.
- **Prune is FRED-style single-table** — delete old `snapshots` only; **never** cascade into the fact tables (the fiscal history is the store). Call this out in `db.py`.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest` (config in `pyproject.toml`).
- **Commits:** do NOT add a co-author line (per user global instruction).

### Live-verification action (🟡 — do before finalizing parsers)

FiscalData slugs/fields are located but not adversarially verified. The parsers below use the documented field names; **confirm each live** (the API is key-free — one `curl`/WebFetch per dataset) and, if a field is renamed, adjust the parser *and its fixture together*. Any dataset that 404s is dropped from `CATALOG` with a note. The specific names to confirm: `open_today_bal`/`close_today_bal` (dts_cash), `tot_pub_debt_out_amt`/`debt_held_public_amt`/`intragov_hold_amt` (debt_penny), `avg_interest_rate_amt` (avg_rates), `announcemt_date` (upcoming_auctions — Treasury's spelling), `high_yield_rate`/`bid_to_cover_ratio`/`offering_amt`/`total_accepted_amt` (auction_results), and the `BC_*`/`NEW_DATE` XML element names (yield curve).

---

## File Structure

**New — `treasury_screener/` package:**
- `treasury_screener/__init__.py` — empty.
- `treasury_screener/catalog.py` — `Dataset` dataclass + curated `CATALOG` + `select_ids`.
- `treasury_screener/fetch.py` — FiscalData paged JSON client + XML yield-curve branch + per-dataset pure parsers.
- `treasury_screener/db.py` — per-dataset schema + writers + 5 ELT views + single-table prune.
- `treasury_screener/run.py` — resolve datasets → fetch/parse/write each (skip-and-continue) + argparse `main`.

**Modified:**
- `registry.py` — import `treasury_screener.run.main` and register `"treasury"`.

**New tests (`tests/`):**
`test_treasury_catalog.py`, `test_treasury_fetch.py`, `test_treasury_db_schema.py`, `test_treasury_db_write.py`, `test_treasury_db_views.py`, `test_treasury_run.py`, and one assertion in `test_registry.py`.

---

## Task 1: `treasury_screener.catalog` — Dataset catalog + select_ids

**Files:**
- Create: `treasury_screener/__init__.py` (empty), `treasury_screener/catalog.py`
- Test: `tests/test_treasury_catalog.py`

**Interfaces:**
- `Dataset` frozen dataclass: `dataset_id, endpoint, table, date_field, frequency`.
- `CATALOG: list[Dataset]`.
- `select_ids(all_ids, only, exclude, add=None) -> list[str]` — FRED semantics.

- [ ] **Step 1: Write the failing test**

Create `tests/test_treasury_catalog.py`:

```python
from treasury_screener.catalog import CATALOG, Dataset, select_ids

_FREQ = {"daily", "monthly", "event"}


def test_catalog_ids_unique_and_known():
    ids = [d.dataset_id for d in CATALOG]
    assert len(ids) == len(set(ids))
    assert {"dts_cash", "debt_penny", "avg_rates", "upcoming_auctions",
            "auction_results", "yield_curve"} <= set(ids)


def test_catalog_fields_valid():
    for d in CATALOG:
        assert d.frequency in _FREQ
        assert d.endpoint and d.table and d.date_field


def test_yield_curve_uses_xml_sentinel():
    yc = next(d for d in CATALOG if d.dataset_id == "yield_curve")
    assert yc.endpoint == "xml:yield_curve"


def test_select_ids_default_only_exclude_add_dedupe():
    ids = [d.dataset_id for d in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["dts_cash", "dts_cash"], None) == ["dts_cash"]
    assert "dts_cash" not in select_ids(ids, None, ["dts_cash"])
    assert select_ids(ids, ["dts_cash"], None, add=["x", " x "]) == ["dts_cash", "x"]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `treasury_screener/__init__.py` (empty).

Create `treasury_screener/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    dataset_id: str   # local key, e.g. "dts_cash"
    endpoint: str     # FiscalData path or "xml:yield_curve" sentinel
    table: str        # target table
    date_field: str   # API record-date field
    frequency: str    # daily | monthly | event


# Curated Treasury datasets. Slugs/fields confirmed live at implementation; any
# that 404s is dropped with a note.
CATALOG: list[Dataset] = [
    Dataset("dts_cash", "v1/accounting/dts/operating_cash_balance",
            "dts_cash", "record_date", "daily"),
    Dataset("debt_penny", "v2/accounting/od/debt_to_penny",
            "debt_penny", "record_date", "daily"),
    Dataset("avg_rates", "v2/accounting/od/avg_interest_rates",
            "avg_rates", "record_date", "monthly"),
    Dataset("upcoming_auctions", "v1/accounting/od/upcoming_auctions",
            "upcoming_auctions", "auction_date", "event"),
    Dataset("auction_results", "v1/accounting/od/auctions_query",
            "auction_results", "auction_date", "event"),
    Dataset("yield_curve", "xml:yield_curve", "yield_curve", "record_date",
            "daily"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Ordered, de-duplicated dataset ids: ``only`` (or full catalog) minus
    ``exclude``, then ``add`` appended. Tokens stripped; blanks/dupes dropped.
    Identical to fred_screener.catalog.select_ids."""
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

- [ ] **Step 4: Run test to verify it passes** — expect PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add treasury_screener/__init__.py treasury_screener/catalog.py tests/test_treasury_catalog.py
git commit -m "feat(treasury): curated FiscalData dataset catalog + select_ids"
```

---

## Task 2: `treasury_screener.fetch` — paged JSON client + XML branch + parsers

**Files:**
- Create: `treasury_screener/fetch.py`
- Test: `tests/test_treasury_fetch.py`

**Interfaces:**
- `_build_url(endpoint, *, fields=None, filter_=None, sort=None, page_size=10000, page_number=1) -> str`.
- `fetch_dataset(endpoint, *, fields=None, since=None, get=_http_get) -> list[dict]` — page until `links.next` is null.
- Pure parsers: `parse_dts_cash`, `parse_debt_penny`, `parse_avg_rates`, `parse_upcoming_auctions`, `parse_auction_results`.
- `parse_yield_curve(xml_text) -> list[dict]`, `fetch_yield_curve(year, get=_http_get) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_treasury_fetch.py`:

```python
import json
import urllib.error

from treasury_screener import fetch


def test_build_url_encodes_fields_filter_sort_and_pagination():
    url = fetch._build_url("v2/accounting/od/debt_to_penny",
                           fields=["record_date", "tot_pub_debt_out_amt"],
                           filter_="record_date:gte:2026-01-01",
                           sort="record_date", page_size=500, page_number=2)
    assert "format=json" in url
    assert "page%5Bsize%5D=500" in url and "page%5Bnumber%5D=2" in url
    assert "record_date%3Agte%3A2026-01-01" in url          # filter encoded
    assert "record_date%2Ctot_pub_debt_out_amt" in url      # fields joined


def test_fetch_dataset_follows_pagination_until_next_null():
    pages = [
        {"data": [{"record_date": "2026-01-01"}], "links": {"next": "&page=2"}},
        {"data": [{"record_date": "2026-01-02"}], "links": {"next": None}},
    ]
    calls = {"n": 0}

    def get(url):
        i = calls["n"]
        calls["n"] += 1
        return json.dumps(pages[i])

    rows = fetch.fetch_dataset("v2/accounting/od/debt_to_penny", get=get)
    assert [r["record_date"] for r in rows] == ["2026-01-01", "2026-01-02"]
    assert calls["n"] == 2


def test_parse_dts_cash_coerces_and_keeps_account_type():
    rows = fetch.parse_dts_cash([
        {"record_date": "2026-01-02", "account_type": "Treasury General Account (TGA)",
         "open_today_bal": "750000", "close_today_bal": "800000"},
        {"record_date": "2026-01-02", "account_type": "Federal Reserve Account",
         "open_today_bal": "", "close_today_bal": None},
    ])
    assert rows[0]["close_balance"] == 800000.0
    assert rows[1]["open_balance"] is None      # blank -> None


def test_parse_debt_penny_and_avg_rates_and_auctions():
    d = fetch.parse_debt_penny([{"record_date": "2026-01-02",
        "tot_pub_debt_out_amt": "34000000000000",
        "debt_held_public_amt": "27000000000000",
        "intragov_hold_amt": "7000000000000"}])[0]
    assert d["tot_pub_debt_out"] == 34000000000000.0

    a = fetch.parse_avg_rates([{"record_date": "2026-01-31",
        "security_type_desc": "Marketable", "security_desc": "Treasury Notes",
        "avg_interest_rate_amt": "2.75"}])[0]
    assert a["avg_interest_rate"] == 2.75 and a["security_desc"] == "Treasury Notes"

    ua = fetch.parse_upcoming_auctions([{"cusip": "", "security_type": "Note",
        "security_term": "10-Year", "announcemt_date": "2026-01-05",
        "auction_date": "2026-01-12", "issue_date": "2026-01-15"}])[0]
    assert ua["auction_date"] == "2026-01-12" and ua["announcement_date"] == "2026-01-05"

    ar = fetch.parse_auction_results([{"cusip": "912828XX", "auction_date": "2026-01-12",
        "security_type": "Note", "security_term": "10-Year", "high_yield_rate": "4.1",
        "bid_to_cover_ratio": "2.6", "offering_amt": "39000000000",
        "total_accepted_amt": "39000000000"}])[0]
    assert ar["bid_to_cover_ratio"] == 2.6 and ar["high_yield"] == 4.1


def test_parse_yield_curve_extracts_tenors():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom"
        xmlns:m="http://x/m" xmlns:d="http://x/d"><entry><content>
        <m:properties>
          <d:NEW_DATE>2026-01-02T00:00:00</d:NEW_DATE>
          <d:BC_3MONTH>4.3</d:BC_3MONTH>
          <d:BC_2YEAR>3.8</d:BC_2YEAR>
          <d:BC_10YEAR>3.9</d:BC_10YEAR>
        </m:properties></content></entry></feed>"""
    rows = fetch.parse_yield_curve(xml)
    assert rows[0]["record_date"] == "2026-01-02"
    assert rows[0]["mo3"] == 4.3 and rows[0]["yr2"] == 3.8 and rows[0]["yr10"] == 3.9
    assert rows[0]["yr30"] is None              # absent tenor -> None


def test_parse_yield_curve_rejects_doctype_entity_bomb():
    import pytest
    bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "AAAA">]>'
            '<feed><entry></entry></feed>')
    with pytest.raises(ValueError):
        fetch.parse_yield_curve(bomb)


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_dataset_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps({"data": [], "links": {"next": None}})

    def get(url):
        return fetch._http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_dataset("v2/accounting/od/debt_to_penny", get=get)
    assert calls["n"] == 2 and slept == [1.0]
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `treasury_screener/fetch.py`:

```python
"""U.S. Treasury Fiscal Data client (paged JSON:API) + the one XML branch for the
par yield-curve feed. Pure parsers separated from HTTP so they unit-test without
network. Key-free; reuses the shared bounded-backoff client."""
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET

import http_client

API_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
YIELD_CURVE_URL = ("https://home.treasury.gov/resource-center/data-chart-center/"
                   "interest-rates/pages/xml?data=daily_treasury_yield_curve")
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _date(v):
    return (v or "")[:10] or None


def _build_url(endpoint, *, fields=None, filter_=None, sort=None,
               page_size=10000, page_number=1) -> str:
    params = {"format": "json", "page[size]": page_size,
              "page[number]": page_number}
    if fields:
        params["fields"] = ",".join(fields)
    if filter_:
        params["filter"] = filter_
    if sort:
        params["sort"] = sort
    return f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"


def fetch_dataset(endpoint, *, fields=None, since=None, get=_http_get) -> list:
    """Page through the JSON:API `data` arrays until `links.next` is null."""
    filter_ = f"record_date:gte:{since}" if since else None
    records, page = [], 1
    while True:
        url = _build_url(endpoint, fields=fields, filter_=filter_,
                         sort="record_date", page_number=page)
        payload = json.loads(get(url))
        records.extend(payload.get("data", []))
        if not (payload.get("links") or {}).get("next"):
            break
        page += 1
    return records


def parse_dts_cash(records) -> list:
    return [{"record_date": _date(r.get("record_date")),
             "account_type": r.get("account_type"),
             "open_balance": _num(r.get("open_today_bal")),
             "close_balance": _num(r.get("close_today_bal"))} for r in records]


def parse_debt_penny(records) -> list:
    return [{"record_date": _date(r.get("record_date")),
             "tot_pub_debt_out": _num(r.get("tot_pub_debt_out_amt")),
             "debt_held_public": _num(r.get("debt_held_public_amt")),
             "intragov_hold": _num(r.get("intragov_hold_amt"))} for r in records]


def parse_avg_rates(records) -> list:
    return [{"record_date": _date(r.get("record_date")),
             "security_type_desc": r.get("security_type_desc"),
             "security_desc": r.get("security_desc"),
             "avg_interest_rate": _num(r.get("avg_interest_rate_amt"))}
            for r in records]


def parse_upcoming_auctions(records) -> list:
    return [{"cusip": r.get("cusip") or None,
             "security_type": r.get("security_type"),
             "security_term": r.get("security_term"),
             "announcement_date": _date(r.get("announcemt_date")),
             "auction_date": _date(r.get("auction_date")),
             "issue_date": _date(r.get("issue_date"))} for r in records]


def parse_auction_results(records) -> list:
    return [{"cusip": r.get("cusip"), "auction_date": _date(r.get("auction_date")),
             "security_type": r.get("security_type"),
             "security_term": r.get("security_term"),
             "high_yield": _num(r.get("high_yield_rate")),
             "bid_to_cover_ratio": _num(r.get("bid_to_cover_ratio")),
             "offering_amt": _num(r.get("offering_amt")),
             "total_accepted": _num(r.get("total_accepted_amt"))} for r in records]


_TENOR = {"BC_1MONTH": "mo1", "BC_2MONTH": "mo2", "BC_3MONTH": "mo3",
          "BC_4MONTH": "mo4", "BC_6MONTH": "mo6", "BC_1YEAR": "yr1",
          "BC_2YEAR": "yr2", "BC_3YEAR": "yr3", "BC_5YEAR": "yr5",
          "BC_7YEAR": "yr7", "BC_10YEAR": "yr10", "BC_20YEAR": "yr20",
          "BC_30YEAR": "yr30"}
_YC_COLS = ["record_date"] + list(_TENOR.values())


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_yield_curve(xml_text) -> list:
    """Parse the Treasury par-curve Atom XML → one dict per business day, wide by
    tenor. Namespace-agnostic (matches on local element names).

    Hardening: stdlib xml.etree does not resolve external entities (no XXE), but
    is vulnerable to entity-expansion DoS ('billion laughs'). Those bombs live in
    a DOCTYPE/ENTITY block, which the legitimate Treasury feed never uses — so we
    reject any such declaration before parsing (defusedxml would be cleaner but
    the repo is strictly dependency-free)."""
    if xml_text and ("<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text):
        raise ValueError("refusing XML with a DOCTYPE/ENTITY declaration "
                         "(entity-expansion guard)")
    root = ET.fromstring(xml_text)
    out = []
    for el in root.iter():
        if _local(el.tag) != "properties":
            continue
        row = {c: None for c in _YC_COLS}
        for child in el.iter():
            name = _local(child.tag)
            if name == "NEW_DATE":
                row["record_date"] = _date(child.text)
            elif name in _TENOR:
                row[_TENOR[name]] = _num(child.text)
        if row["record_date"]:
            out.append(row)
    return out


def fetch_yield_curve(year, get=_http_get) -> list:
    return parse_yield_curve(get(f"{YIELD_CURVE_URL}&field_tdr_date_value={year}"))
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add treasury_screener/fetch.py tests/test_treasury_fetch.py
git commit -m "feat(treasury): FiscalData paged JSON client + XML yield-curve branch + parsers"
```

---

## Task 3: `treasury_screener.db` — per-dataset schema + writers + prune

**Files:**
- Create: `treasury_screener/db.py` (schema + writers + prune; **views in Task 4**)
- Test: `tests/test_treasury_db_schema.py`, `tests/test_treasury_db_write.py`

**Interfaces:**
- `connect` — re-export from `screener_common`.
- `ensure_schema(conn)` — 6 tables + `snapshots` (+ views from Task 4). Idempotent.
- `write_dts_cash / write_debt_penny / write_avg_rates / write_upcoming_auctions / write_auction_results / write_yield_curve(conn, rows) -> int` — upsert by natural key, dedupe (last wins).
- `write_snapshot(conn, captured_at, dataset_count, row_count) -> int`.
- `prune(conn, keep_days, now_iso) -> int` — single-table snapshots delete.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_treasury_db_schema.py`:

```python
from treasury_screener import db


def test_ensure_schema_creates_all_tables_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"snapshots", "dts_cash", "debt_penny", "avg_rates",
            "upcoming_auctions", "auction_results", "yield_curve"} <= tables
```

Create `tests/test_treasury_db_write.py`:

```python
from treasury_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_dts_cash_upsert_in_place():
    conn = _fresh()
    row = {"record_date": "2026-01-02", "account_type": "TGA",
           "open_balance": 700.0, "close_balance": 750.0}
    db.write_dts_cash(conn, [row])
    db.write_dts_cash(conn, [{**row, "close_balance": 800.0}])   # restated
    got = conn.execute("SELECT close_balance FROM dts_cash").fetchall()
    assert got == [(800.0,)]                     # updated in place, no duplicate


def test_write_dedupes_within_batch_last_wins():
    conn = _fresh()
    n = db.write_debt_penny(conn, [
        {"record_date": "2026-01-02", "tot_pub_debt_out": 1.0,
         "debt_held_public": None, "intragov_hold": None},
        {"record_date": "2026-01-02", "tot_pub_debt_out": 2.0,
         "debt_held_public": None, "intragov_hold": None},
    ])
    assert n == 1
    assert conn.execute("SELECT tot_pub_debt_out FROM debt_penny").fetchone()[0] == 2.0


def test_write_yield_curve_and_auctions_persist_null_blank():
    conn = _fresh()
    db.write_yield_curve(conn, [{"record_date": "2026-01-02", "mo1": 4.5,
        "mo2": None, "mo3": 4.3, "mo4": None, "mo6": None, "yr1": None,
        "yr2": 3.8, "yr3": None, "yr5": None, "yr7": None, "yr10": 3.9,
        "yr20": None, "yr30": None}])
    assert conn.execute("SELECT yr10, mo2 FROM yield_curve").fetchone() == (3.9, None)
    db.write_upcoming_auctions(conn, [{"cusip": None, "security_type": "Note",
        "security_term": "10-Year", "announcement_date": "2026-01-05",
        "auction_date": "2026-01-12", "issue_date": "2026-01-15"}])
    assert conn.execute("SELECT auction_date FROM upcoming_auctions").fetchone()[0] \
        == "2026-01-12"


def test_prune_deletes_old_snapshots_not_facts():
    conn = _fresh()
    db.write_debt_penny(conn, [{"record_date": "2026-01-02", "tot_pub_debt_out": 1.0,
        "debt_held_public": None, "intragov_hold": None}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `treasury_screener/db.py` (views deferred to Task 4 via `_VIEWS = ""`):

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "write_dts_cash", "write_debt_penny",
           "write_avg_rates", "write_upcoming_auctions", "write_auction_results",
           "write_yield_curve", "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,
    dataset_count INTEGER NOT NULL,
    row_count     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dts_cash (
    record_date   TEXT NOT NULL,
    account_type  TEXT NOT NULL,
    open_balance  REAL,
    close_balance REAL,
    PRIMARY KEY (record_date, account_type)
);
CREATE TABLE IF NOT EXISTS debt_penny (
    record_date      TEXT PRIMARY KEY,
    tot_pub_debt_out REAL,
    debt_held_public REAL,
    intragov_hold    REAL
);
CREATE TABLE IF NOT EXISTS avg_rates (
    record_date        TEXT NOT NULL,
    security_type_desc TEXT NOT NULL,
    security_desc      TEXT NOT NULL,
    avg_interest_rate  REAL,
    PRIMARY KEY (record_date, security_type_desc, security_desc)
);
CREATE TABLE IF NOT EXISTS yield_curve (
    record_date TEXT PRIMARY KEY,
    mo1 REAL, mo2 REAL, mo3 REAL, mo4 REAL, mo6 REAL,
    yr1 REAL, yr2 REAL, yr3 REAL, yr5 REAL, yr7 REAL,
    yr10 REAL, yr20 REAL, yr30 REAL
);
CREATE TABLE IF NOT EXISTS upcoming_auctions (
    cusip             TEXT,
    security_type     TEXT NOT NULL,
    security_term     TEXT NOT NULL,
    announcement_date TEXT,
    auction_date      TEXT NOT NULL,
    issue_date        TEXT,
    PRIMARY KEY (auction_date, security_type, security_term)
);
CREATE TABLE IF NOT EXISTS auction_results (
    cusip              TEXT NOT NULL,
    auction_date       TEXT NOT NULL,
    security_type      TEXT,
    security_term      TEXT,
    high_yield         REAL,
    bid_to_cover_ratio REAL,
    offering_amt       REAL,
    total_accepted     REAL,
    PRIMARY KEY (cusip, auction_date)
);
"""


def ensure_schema(conn) -> None:
    """Create all Treasury tables (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def _upsert(conn, table, cols, key_cols, rows) -> int:
    """Generic upsert: dedupe by key (last wins), INSERT ... ON CONFLICT(key)
    DO UPDATE the non-key columns. Rows are dicts whose keys are `cols`."""
    by_key = {tuple(r[k] for k in key_cols): r for r in rows}
    placeholders = ", ".join(f":{c}" for c in cols)
    non_key = [c for c in cols if c not in key_cols]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in non_key) or \
        f"{key_cols[0]}={key_cols[0]}"
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(key_cols)}) DO UPDATE SET {set_clause}",
        list(by_key.values()))
    conn.commit()
    return len(by_key)


def write_dts_cash(conn, rows) -> int:
    return _upsert(conn, "dts_cash",
                   ["record_date", "account_type", "open_balance", "close_balance"],
                   ["record_date", "account_type"], rows)


def write_debt_penny(conn, rows) -> int:
    return _upsert(conn, "debt_penny",
                   ["record_date", "tot_pub_debt_out", "debt_held_public",
                    "intragov_hold"], ["record_date"], rows)


def write_avg_rates(conn, rows) -> int:
    return _upsert(conn, "avg_rates",
                   ["record_date", "security_type_desc", "security_desc",
                    "avg_interest_rate"],
                   ["record_date", "security_type_desc", "security_desc"], rows)


def write_upcoming_auctions(conn, rows) -> int:
    return _upsert(conn, "upcoming_auctions",
                   ["cusip", "security_type", "security_term", "announcement_date",
                    "auction_date", "issue_date"],
                   ["auction_date", "security_type", "security_term"], rows)


def write_auction_results(conn, rows) -> int:
    return _upsert(conn, "auction_results",
                   ["cusip", "auction_date", "security_type", "security_term",
                    "high_yield", "bid_to_cover_ratio", "offering_amt",
                    "total_accepted"], ["cusip", "auction_date"], rows)


def write_yield_curve(conn, rows) -> int:
    cols = ["record_date", "mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2",
            "yr3", "yr5", "yr7", "yr10", "yr20", "yr30"]
    return _upsert(conn, "yield_curve", cols, ["record_date"], rows)


def write_snapshot(conn, captured_at, dataset_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, dataset_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, dataset_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshot provenance ONLY. The fact tables are
    the historical store and are NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})",
                 ids)
    conn.commit()
    return len(ids)


_VIEWS = ""   # filled in Task 4
```

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (1 + 4 tests).

- [ ] **Step 5: Commit**

```bash
git add treasury_screener/db.py tests/test_treasury_db_schema.py tests/test_treasury_db_write.py
git commit -m "feat(treasury): per-dataset schema + keyed upserts + single-table prune"
```

---

## Task 4: `treasury_screener.db` — ELT views

**Files:**
- Modify: `treasury_screener/db.py` (fill `_VIEWS`)
- Test: `tests/test_treasury_db_views.py`

**Views:** `v_tga_trend`, `v_debt_trend`, `v_yield_curve_latest`, `v_upcoming_auctions`, `v_auction_demand`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_treasury_db_views.py`:

```python
from treasury_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_yield_curve_latest_spread_and_inverted_flag():
    conn = _fresh()
    base = {c: None for c in ["mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2",
                              "yr3", "yr5", "yr7", "yr10", "yr20", "yr30"]}
    db.write_yield_curve(conn, [
        {**base, "record_date": "2026-01-01", "yr2": 3.0, "yr10": 4.0, "mo3": 3.5},
        {**base, "record_date": "2026-02-01", "yr2": 4.5, "yr10": 4.0, "mo3": 4.8},
    ])
    row = conn.execute("SELECT record_date, spread_2s10s, inverted "
                       "FROM v_yield_curve_latest").fetchone()
    assert row[0] == "2026-02-01"           # newest
    assert abs(row[1] - (-0.5)) < 1e-9      # 4.0 - 4.5
    assert row[2] == 1                      # inverted (spread < 0)


def test_v_upcoming_auctions_filters_future_ordered():
    conn = _fresh()
    db.write_upcoming_auctions(conn, [
        {"cusip": None, "security_type": "Bill", "security_term": "4-Week",
         "announcement_date": None, "auction_date": "2000-01-01", "issue_date": None},
        {"cusip": None, "security_type": "Note", "security_term": "10-Year",
         "announcement_date": None, "auction_date": "2099-01-01", "issue_date": None},
    ])
    dates = [r[0] for r in conn.execute(
        "SELECT auction_date FROM v_upcoming_auctions")]
    assert dates == ["2099-01-01"]          # past dropped


def test_v_debt_trend_delta_vs_prior():
    conn = _fresh()
    db.write_debt_penny(conn, [
        {"record_date": "2026-01-01", "tot_pub_debt_out": 100.0,
         "debt_held_public": None, "intragov_hold": None},
        {"record_date": "2026-01-02", "tot_pub_debt_out": 130.0,
         "debt_held_public": None, "intragov_hold": None},
    ])
    row = conn.execute("SELECT change_vs_prior FROM v_debt_trend "
                       "WHERE record_date='2026-01-02'").fetchone()
    assert row[0] == 30.0


def test_v_auction_demand_latest_per_term():
    conn = _fresh()
    for d, btc in [("2026-01-01", 2.0), ("2026-02-01", 3.0)]:
        db.write_auction_results(conn, [{"cusip": f"c{d}", "auction_date": d,
            "security_type": "Note", "security_term": "10-Year", "high_yield": 4.0,
            "bid_to_cover_ratio": btc, "offering_amt": None, "total_accepted": None}])
    row = conn.execute("SELECT auction_date, latest_btc, avg_btc FROM "
                       "v_auction_demand WHERE security_term='10-Year'").fetchone()
    assert row[0] == "2026-02-01" and row[1] == 3.0
    assert abs(row[2] - 2.5) < 1e-9         # average of 2.0 and 3.0
```

- [ ] **Step 2: Run test to verify it fails** — views don't exist yet.

- [ ] **Step 3: Write minimal implementation**

In `treasury_screener/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- TGA closing balance per date with ~week-over-week (5 business-day) change.
CREATE VIEW IF NOT EXISTS v_tga_trend AS
WITH tga AS (
    SELECT record_date, close_balance FROM dts_cash
    WHERE account_type LIKE '%TGA%'
)
SELECT record_date, close_balance,
       close_balance - LAG(close_balance, 5) OVER (ORDER BY record_date)
         AS wow_change
FROM tga ORDER BY record_date;

-- Total public debt per date with the delta vs the prior stored date.
CREATE VIEW IF NOT EXISTS v_debt_trend AS
SELECT record_date, tot_pub_debt_out,
       tot_pub_debt_out - LAG(tot_pub_debt_out) OVER (ORDER BY record_date)
         AS change_vs_prior
FROM debt_penny ORDER BY record_date;

-- Newest par curve with the 2s10s spread + inversion flag + 3m10y.
CREATE VIEW IF NOT EXISTS v_yield_curve_latest AS
WITH latest AS (SELECT * FROM yield_curve ORDER BY record_date DESC LIMIT 1)
SELECT record_date, yr2, yr10, mo3,
       yr10 - yr2 AS spread_2s10s,
       (yr10 - yr2 < 0) AS inverted,
       yr10 - mo3 AS spread_3m10y
FROM latest;

-- Forward auction calendar: announced auctions dated today or later.
CREATE VIEW IF NOT EXISTS v_upcoming_auctions AS
SELECT cusip, security_type, security_term, announcement_date, auction_date,
       issue_date
FROM upcoming_auctions
WHERE auction_date >= date('now')
ORDER BY auction_date;

-- Latest bid-to-cover per term + the term's average across stored auctions.
CREATE VIEW IF NOT EXISTS v_auction_demand AS
WITH ranked AS (
    SELECT security_term, auction_date, bid_to_cover_ratio,
           ROW_NUMBER() OVER (PARTITION BY security_term
                              ORDER BY auction_date DESC) AS rn,
           AVG(bid_to_cover_ratio) OVER (PARTITION BY security_term) AS avg_btc
    FROM auction_results WHERE bid_to_cover_ratio IS NOT NULL
)
SELECT security_term, auction_date, bid_to_cover_ratio AS latest_btc, avg_btc
FROM ranked WHERE rn = 1;
"""
```

> **Note on `v_upcoming_auctions` using `date('now')`:** this is a *screener* view (not a monitor), so — like FRED's data-relative views — it may use SQLite's `date('now')`; the test pins determinism by seeding a clearly-past (`2000-01-01`) and clearly-future (`2099-01-01`) auction so the assertion holds for decades. The event-monitor framework reads this view for the forward auction calendar.

- [ ] **Step 4: Run test to verify it passes** — expect PASS (4 tests). Run the whole db suite too.

- [ ] **Step 5: Commit**

```bash
git add treasury_screener/db.py tests/test_treasury_db_views.py
git commit -m "feat(treasury): ELT views — TGA/debt trend, 2s10s curve, auction calendar + demand"
```

---

## Task 5: `treasury_screener.run` — orchestration + CLI

**Files:**
- Create: `treasury_screener/run.py`
- Test: `tests/test_treasury_run.py`

**Interfaces:**
- `run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None, fetch_dataset=fetch.fetch_dataset, fetch_yield_curve=fetch.fetch_yield_curve, now_iso=None) -> (snapshot_id, dataset_count, row_count)`.
- `main(argv=None)` — argparse, `prog="treasury"`.

**Behavior:** resolve datasets; per dataset compute `since` (max stored `record_date`, or `--start` floor on first run; **event** datasets skip the `since` filter); dispatch to the right parser+writer (yield_curve → XML branch, year from `now_iso`); skip-and-continue + secret hygiene; all-fail → `(0,0)` snapshot + warn.

- [ ] **Step 1: Write the failing test**

Create `tests/test_treasury_run.py`:

```python
import sqlite3

from treasury_screener import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _raw_debt(dates):
    return [{"record_date": d, "tot_pub_debt_out_amt": "100",
             "debt_held_public_amt": "70", "intragov_hold_amt": "30"} for d in dates]


def test_run_happy_path_counts_rows(tmp_path):
    db_path = str(tmp_path / "t.db")

    def fetch_dataset(endpoint, *, fields=None, since=None):
        return _raw_debt(["2026-07-01", "2026-07-02"])

    def fetch_yc(year):
        return [{"record_date": f"{year}-07-01", **{c: None for c in
                 ["mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2", "yr3", "yr5",
                  "yr7", "yr10", "yr20", "yr30"]}}]

    sid, nds, nrows = runmod.run(db_path, only=["debt_penny", "yield_curve"],
                                 fetch_dataset=fetch_dataset,
                                 fetch_yield_curve=fetch_yc, now_iso=NOW)
    assert nds == 2 and nrows == 3
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 2


def test_run_skips_failing_dataset_without_leaking_secret(tmp_path, capsys):
    def fetch_dataset(endpoint, *, fields=None, since=None):
        if "debt_to_penny" in endpoint:
            raise RuntimeError("https://api?token=SECRET boom")
        return _raw_debt(["2026-07-01"])       # avg_rates path (reuses shape ok)

    sid, nds, nrows = runmod.run(str(tmp_path / "t.db"),
                                 only=["debt_penny"], fetch_dataset=fetch_dataset,
                                 now_iso=NOW)
    assert (nds, nrows) == (0, 0)              # the only dataset failed
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err


def test_run_all_fail_writes_zero_snapshot(tmp_path, capsys):
    def boom(endpoint, *, fields=None, since=None):
        raise RuntimeError("x")

    sid, nds, nrows = runmod.run(str(tmp_path / "t.db"), only=["debt_penny"],
                                 fetch_dataset=boom, now_iso=NOW)
    assert (nds, nrows) == (0, 0)
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert "warning" in capsys.readouterr().err.lower()


def test_run_incremental_second_run_upserts(tmp_path):
    db_path = str(tmp_path / "t.db")
    seen = {"since": []}

    def fetch_dataset(endpoint, *, fields=None, since=None):
        seen["since"].append(since)
        return _raw_debt(["2026-07-02"])

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset, now_iso=NOW)
    assert seen["since"][0] is None             # first run: full history
    assert seen["since"][1] == "2026-07-02"     # second run: floored at max date
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "t.db")

    def fetch_dataset(endpoint, *, fields=None, since=None):
        return _raw_debt(["2026-07-02"])

    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset,
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["debt_penny"], fetch_dataset=fetch_dataset,
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM debt_penny").fetchone()[0] == 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `treasury_screener/run.py`:

```python
import argparse
import sys
from datetime import datetime, timezone

from treasury_screener import catalog, db, fetch

# dataset_id -> (parser, writer, table). yield_curve is handled separately (XML).
_HANDLERS = {
    "dts_cash": (fetch.parse_dts_cash, db.write_dts_cash, "dts_cash"),
    "debt_penny": (fetch.parse_debt_penny, db.write_debt_penny, "debt_penny"),
    "avg_rates": (fetch.parse_avg_rates, db.write_avg_rates, "avg_rates"),
    "upcoming_auctions": (fetch.parse_upcoming_auctions,
                          db.write_upcoming_auctions, "upcoming_auctions"),
    "auction_results": (fetch.parse_auction_results, db.write_auction_results,
                        "auction_results"),
}


def _max_date(conn, table, date_col="record_date"):
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    return row[0] if row and row[0] else None


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        fetch_dataset=fetch.fetch_dataset,
        fetch_yield_curve=fetch.fetch_yield_curve, now_iso=None):
    """Fetch the selected Treasury datasets, upsert each into its table,
    snapshot the run, optionally prune. Skip-and-continue per dataset. Returns
    (snapshot_id, dataset_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    year = int(now_iso[:4])
    ids = catalog.select_ids([d.dataset_id for d in catalog.CATALOG], only,
                             exclude, add=add)
    by_id = {d.dataset_id: d for d in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for dataset_id in ids:
            ds = by_id.get(dataset_id)
            try:
                if dataset_id == "yield_curve":
                    rows = fetch_yield_curve(year)
                    n = db.write_yield_curve(conn, rows)
                elif dataset_id in _HANDLERS:
                    parser, writer, table = _HANDLERS[dataset_id]
                    # event datasets have no record_date floor; daily/monthly do
                    since = None
                    if ds and ds.frequency != "event" and start is None:
                        since = _max_date(conn, table)
                    elif start is not None:
                        since = start
                    raw = fetch_dataset(ds.endpoint if ds else dataset_id,
                                        since=since)
                    n = writer(conn, parser(raw))
                else:
                    print(f"warning: unknown dataset {dataset_id}",
                          file=sys.stderr)
                    continue
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {dataset_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no Treasury datasets fetched (0 datasets, 0 rows)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="treasury",
        description="Pull U.S. Treasury Fiscal Data datasets into SQLite")
    p.add_argument("--db", default="treasury.db")
    p.add_argument("--only", default=None, help="comma-separated dataset ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra dataset id not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="record_date floor for the first fetch (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, nds, nrows = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                        add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {nrows} rows across {nds} datasets into {a.db}")


if __name__ == "__main__":
    main()
```

> **Incremental `since` note (revision follow-up):** `since = max(record_date)` (inclusive `gte`) re-absorbs the boundary day's restatement on each run. FiscalData occasionally revises rows a few days back; a **wider trailing-window lookback** (à la the CFTC revision-lookback) is a documented follow-up. `--start` forces a full re-fetch floor for a manual backfill. Event datasets (auctions) always full-fetch and upsert.

- [ ] **Step 4: Run test to verify it passes** — expect PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add treasury_screener/run.py tests/test_treasury_run.py
git commit -m "feat(treasury): run orchestration (incremental, skip-and-continue) + CLI"
```

---

## Task 6: Register `treasury` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_treasury():
    import registry
    assert "treasury" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails** — `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import and register (near the other data screeners):

```python
from treasury_screener.run import main as treasury_main
```
```python
    "treasury": treasury_main,
```

- [ ] **Step 4: Run test to verify it passes** — `python -m pytest tests/test_registry.py -v`.

- [ ] **Step 5: Run the FULL suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(treasury): register treasury dispatcher"
```

---

## Task 7: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `treasury` to Built**

- Add a `treasury` row to the **Built ✅** table (link this plan + the spec).
- Remove the `treasury` row from **Spec'd — data screeners 📝** (New official sources table).
- In **Recommended build order**, strike through item 7 (`treasury`) as ✅ Built, mirroring items 1–6. Note the deferred wider revision-lookback follow-up and that the auction calendar ships as `v_upcoming_auctions`.

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark treasury Built; auction calendar via v_upcoming_auctions"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| `Dataset` catalog + `select_ids` (only/exclude/add) | Task 1 |
| Paged JSON:API `fetch_dataset` (follow `links.next`); `_build_url` encoding | Task 2 |
| Per-dataset pure parsers (coercion, blank→None, date normalize) | Task 2 |
| XML `parse_yield_curve` / `fetch_yield_curve` (namespace-agnostic) | Task 2 |
| 6 per-dataset tables + `snapshots`, natural-key upserts | Task 3 |
| Single-table prune, never cascade into fact tables | Task 3 |
| `v_tga_trend` / `v_debt_trend` / `v_yield_curve_latest` (2s10s+inverted) / `v_upcoming_auctions` / `v_auction_demand` | Task 4 |
| `run` incremental `since`, event-dataset full-fetch, skip-and-continue, all-fail→(0,0) | Task 5 |
| Secret hygiene (type name only) | Task 5 |
| CLI `--db/--only/--exclude/--add/--start/--keep-days` | Task 5 |
| Registry `"treasury"` | Task 6 |
| No credentials; `.env.example` unchanged; `now_iso` injected | Global Constraints |

**2. Placeholder scan:** No `TODO` in code. 🟡 field names are handled via the **live-verification action** (adjust parser + fixture together), not code placeholders. The wider revision-lookback is a documented follow-up (surfaced in the roadmap entry); v1 ships a working inclusive-floor incremental.

**3. Type consistency:** Each parser's output dict keys **exactly match** its table's column names (Task 2 ↔ Task 3), so the named-param `_upsert` binds directly. `_num` returns `float|None`; `_date` returns ISO `str|None`. `run` returns a 3-tuple `(snapshot_id, dataset_count, row_count)` used identically in every test. The yield-curve column set is identical across `parse_yield_curve` (Task 2), the `yield_curve` table (Task 3), and `write_yield_curve` (Task 3).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-treasury-fiscaldata-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
