# SEC XBRL Fundamentals Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `sec_fundamentals` screener — primary-source company fundamentals (the XBRL facts registrants tag into 10-K/10-Q filings: revenue, net income, assets, equity, EPS, shares) pulled from `data.sec.gov` into SQLite as an auditable, point-in-time **panel** keyed `(cik, tag, period_end, form)`, with ratios derived in SQL views.

**Architecture:** A panel screener in the FRED/CFTC mould (`catalog`/`fetch`/`db`/`run` + registry). It is adjacent to `edgar`: both key on CIK and share the SEC `User-Agent` + bounded backoff. It **reuses `edgar_screener.fetch.fetch_ticker_map` and `_http_get` verbatim** (same `_UA`, same `_RETRY_STATUS = {403,429,503}`, same `http_client` backoff), the FRED-style `select_ids`, and FRED's **single-table** prune (fundamentals history is NOT snapshot-scoped). Two keyless access modes: `frames` (one metric across all filers for a period → the cross-sectional screen) and `companyfacts` (full depth per watchlist ticker); an optional `--bulk` quarterly-ZIP backfill.

**Tech Stack:** Python 3.12+ stdlib only (`sqlite3`, `urllib`, `json`, `zipfile`, `csv`, `io`, `datetime`, `argparse`, `dataclasses`); `pytest`. Reuses `screener_common.connect` (WAL), `edgar_screener.fetch`, `http_client`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.12+, dependency-free** — stdlib + `urllib` via `http_client`. No new packages.
- **No credentials.** No API key for either mode; `.env.example` unchanged. The mandatory pieces are *policy*: a descriptive `User-Agent` (`agentic-trading-bot ninadk.dev@gmail.com`, reused from `edgar_screener`) — SEC `403`s without it — and the ≤10 req/s fair-access cap.
- **Reuse EDGAR's SEC scaffolding** — import `fetch_ticker_map` and `_http_get` from `edgar_screener.fetch`; do not re-implement the opener, UA, or backoff.
- **`now_iso` injected, never wall-clock in logic.** Every `run()` accepts `now_iso=None`, defaulting to `datetime.now(timezone.utc).isoformat()`. Fetchers are injected too (`fetch_frame`/`fetch_facts`/`fetch_map`) so tests are network-free.
- **Skip-and-continue** on any per-item fetch/parse error: `conn.rollback()` the failed item, log **only** `type(e).__name__` (never `str(e)`/`e.url`), continue. Zero successes → still `write_snapshot(…, 0, 0)` and warn; never raise.
- **Panel upsert, never duplicate keys.** `write_facts` upserts by `(cik, tag, period_end, form)`; a revised value overwrites in place; a different `form` for the same period is a new row (feeds `v_revisions`).
- **Prune is FRED-style single-table** — delete old `snapshots` only; **never** cascade into `facts`. The reported history is the store.
- **Every writer ends with `conn.commit()`** (repo rule).
- **Test command:** `python -m pytest` (config in `pyproject.toml`; `pythonpath=["."]`, `testpaths=["tests"]`).
- **Commits:** do NOT add a co-author line (per user global instruction).

## Deferred (documented non-goals for this plan, not silent drops)

- **Shared ≤10 req/s throttle in `http_client`** (the spec's recommendation): a cross-cutting token-bucket affecting `edgar`/`ftd`/`fundamentals` alike. Out of scope here to keep this screener self-contained; EDGAR's existing backoff already absorbs SEC 403s. **Follow-up noted in the roadmap.**
- **Financial Statement *and Notes* datasets, pre-2009 depth, 13F/N-PORT, extension/custom tags, cross-screener joins** — per spec Non-goals.

---

## File Structure

**New — `sec_fundamentals/` package:**
- `sec_fundamentals/__init__.py` — empty.
- `sec_fundamentals/catalog.py` — `Concept` dataclass + curated `CATALOG` + `select_ids`.
- `sec_fundamentals/fetch.py` — `data.sec.gov` client (frames/companyfacts/submissions), CIK zero-pad, unit-path encoding, pure parsers, ticker-map reuse, optional `parse_bulk`.
- `sec_fundamentals/db.py` — schema (`companies`/`facts`/`snapshots`) + upserts + 4 ELT views + single-table prune.
- `sec_fundamentals/run.py` — skip-and-continue orchestration + argparse `main`.

**Modified:**
- `registry.py` — import `sec_fundamentals.run.main` and register `"fundamentals"`.

**New tests (`tests/`):**
`test_sec_fundamentals_catalog.py`, `test_sec_fundamentals_fetch.py`, `test_sec_fundamentals_db_schema.py`, `test_sec_fundamentals_db_write.py`, `test_sec_fundamentals_db_views.py`, `test_sec_fundamentals_run.py`, and one assertion in `test_registry.py`.

### Fact-row shape (produced by parsers, consumed by `write_facts`)

`{tag, uom, period_end, fiscal_year, fiscal_period, value, form, filed, accession}`.
`companyfacts` entries use JSON keys `val/accn/end/fy/fp/form/filed`; `frames` entries carry `cik/val/end/accn` only (no `form/fy/fp/filed`) → those map to `None`, and the run substitutes `form='FRAME'` before writing (keeps the non-null PK, marks provenance).

---

## Task 1: `sec_fundamentals.catalog` — curated concepts + select_ids

**Files:**
- Create: `sec_fundamentals/__init__.py` (empty), `sec_fundamentals/catalog.py`
- Test: `tests/test_sec_fundamentals_catalog.py`

**Interfaces:**
- `Concept` frozen dataclass: `tag, taxonomy, unit, kind, group`.
- `CATALOG: list[Concept]`.
- `select_ids(all_ids, only, exclude, add=None) -> list[str]` — identical semantics to `fred_screener.catalog.select_ids`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sec_fundamentals_catalog.py`:

```python
from sec_fundamentals.catalog import CATALOG, Concept, select_ids

_KINDS = {"instant", "duration"}
_GROUPS = {"income", "balance", "cashflow", "shares", "per_share"}
_UNIT_BY_GROUP = {"income": "USD", "balance": "USD", "cashflow": "USD",
                  "shares": "shares", "per_share": "USD/shares"}


def test_catalog_tags_unique():
    tags = [c.tag for c in CATALOG]
    assert len(tags) == len(set(tags))


def test_catalog_fields_valid_and_unit_matches_group():
    for c in CATALOG:
        assert c.kind in _KINDS
        assert c.group in _GROUPS
        assert c.taxonomy in {"us-gaap", "ifrs-full", "dei", "srt"}
        assert c.unit == _UNIT_BY_GROUP[c.group]


def test_catalog_has_headline_concepts():
    tags = {c.tag for c in CATALOG}
    assert {"Revenues", "NetIncomeLoss", "Assets", "StockholdersEquity",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"} <= tags


def test_balance_tags_are_instant_income_are_duration():
    by_tag = {c.tag: c for c in CATALOG}
    assert by_tag["Assets"].kind == "instant"
    assert by_tag["NetIncomeLoss"].kind == "duration"
    assert by_tag["CommonStockSharesOutstanding"].kind == "instant"


def test_select_ids_defaults_to_full_catalog():
    tags = [c.tag for c in CATALOG]
    assert select_ids(tags, None, None) == tags


def test_select_ids_only_exclude_add_dedupe_and_strip():
    tags = [c.tag for c in CATALOG]
    assert select_ids(tags, ["Assets", "Assets"], None) == ["Assets"]
    assert "Assets" not in select_ids(tags, None, ["Assets"])
    assert select_ids(tags, ["Assets"], None, add=["Foo", " Foo "]) == ["Assets", "Foo"]
```

- [ ] **Step 2: Run test to verify it fails** — `python -m pytest tests/test_sec_fundamentals_catalog.py -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `sec_fundamentals/__init__.py` (empty).

Create `sec_fundamentals/catalog.py`:

```python
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    tag: str          # us-gaap tag, the stable key, e.g. "NetIncomeLoss"
    taxonomy: str     # us-gaap | ifrs-full | dei | srt
    unit: str         # USD | shares | USD/shares
    kind: str         # "instant" (balance-sheet stock) | "duration" (flow)
    group: str        # income | balance | cashflow | shares | per_share


# Curated headline concepts. Tags verified live against data.sec.gov at
# implementation; any tag returning no frames is dropped with a note. The `kind`
# drives the frames period suffix (instant -> trailing 'I'); the wrong suffix
# yields an empty frame.
CATALOG: list[Concept] = [
    # income (duration)
    Concept("Revenues", "us-gaap", "USD", "duration", "income"),
    Concept("RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap", "USD", "duration", "income"),
    Concept("OperatingIncomeLoss", "us-gaap", "USD", "duration", "income"),
    Concept("NetIncomeLoss", "us-gaap", "USD", "duration", "income"),
    # balance (instant)
    Concept("Assets", "us-gaap", "USD", "instant", "balance"),
    Concept("Liabilities", "us-gaap", "USD", "instant", "balance"),
    Concept("StockholdersEquity", "us-gaap", "USD", "instant", "balance"),
    Concept("CashAndCashEquivalentsAtCarryingValue",
            "us-gaap", "USD", "instant", "balance"),
    # per-share / shares
    Concept("EarningsPerShareDiluted", "us-gaap", "USD/shares", "duration",
            "per_share"),
    Concept("CommonStockSharesOutstanding", "us-gaap", "shares", "instant",
            "shares"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated tags to fetch: ``only`` (or the full
    catalog) minus ``exclude``, then any ``add`` appended. Tokens stripped;
    blanks and duplicates dropped. Identical to fred_screener.catalog.select_ids."""
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

- [ ] **Step 4: Run test to verify it passes** — expect PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add sec_fundamentals/__init__.py sec_fundamentals/catalog.py tests/test_sec_fundamentals_catalog.py
git commit -m "feat(fundamentals): curated XBRL concept catalog + select_ids"
```

---

## Task 2: `sec_fundamentals.fetch` — data.sec.gov client + pure parsers

**Files:**
- Create: `sec_fundamentals/fetch.py`
- Test: `tests/test_sec_fundamentals_fetch.py`

**Interfaces:**
- `cik_str(cik: int) -> str` — `f"CIK{cik:010d}"`.
- `fetch_ticker_map` — re-export `edgar_screener.fetch.fetch_ticker_map`.
- `parse_frame(payload) -> list[dict]` — pure; `data[]` → fact rows (`form/fy/fp/filed` → `None`).
- `fetch_frame(tag, unit, period, taxonomy="us-gaap", get=_http_get) -> list[dict]`.
- `parse_company_facts(payload, tags) -> list[dict]` — pure; curated tags only.
- `fetch_company_facts(cik, get=_http_get) -> dict` — raw payload (run parses).
- `fetch_submissions(cik, get=_http_get) -> dict`.
- `parse_bulk(zip_bytes, tags) -> list[dict]` — optional `--bulk`; `num.tsv` ⋈ `sub.tsv`, curated tags, skip empty `2009q1`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sec_fundamentals_fetch.py`:

```python
import io
import json
import urllib.error
import zipfile

import pytest

from sec_fundamentals import fetch


def test_cik_str_zero_pads_to_ten_digits():
    assert fetch.cik_str(320193) == "CIK0000320193"


def test_parse_frame_maps_and_coerces():
    payload = {"data": [
        {"cik": 320193, "entityName": "APPLE INC", "end": "2024-09-28",
         "val": "391035000000", "accn": "0000320193-24-000123"},
        {"cik": 789019, "entityName": "MSFT", "end": "2024-06-30",
         "val": 245122000000, "accn": "x"},
    ]}
    rows = fetch.parse_frame(payload)
    assert rows[0]["cik"] == 320193
    assert rows[0]["value"] == 391035000000.0     # numeric string coerced
    assert rows[0]["period_end"] == "2024-09-28"
    assert rows[0]["accession"] == "0000320193-24-000123"
    assert rows[0]["form"] is None                # frames carry no form
    assert rows[1]["value"] == 245122000000.0


def test_fetch_frame_builds_url_with_unit_path_and_period(monkeypatch):
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"data": []})

    fetch.fetch_frame("EarningsPerShareDiluted", "USD/shares", "CY2024Q3",
                      get=get)
    assert "/us-gaap/EarningsPerShareDiluted/USD-per-shares/CY2024Q3.json" in seen["url"]


def test_parse_company_facts_filters_curated_tags_and_coerces():
    payload = {"facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": [
            {"end": "2024-09-28", "val": 93736000000, "fy": 2024, "fp": "FY",
             "form": "10-K", "filed": "2024-11-01", "accn": "a1"},
        ]}},
        "SomeExtensionTag": {"units": {"USD": [
            {"end": "2024-09-28", "val": 1, "form": "10-K", "accn": "a2"}]}},
    }}}
    rows = fetch.parse_company_facts(payload, {"NetIncomeLoss"})
    assert len(rows) == 1                          # extension tag ignored
    r = rows[0]
    assert r["tag"] == "NetIncomeLoss" and r["form"] == "10-K"
    assert r["value"] == 93736000000.0 and r["period_end"] == "2024-09-28"
    assert r["fiscal_year"] == 2024 and r["accession"] == "a1"


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_frame_retries_403_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(403)
        return json.dumps({"data": []})

    # inject the opener into the shared bounded-backoff via a get closure
    def get(url):
        from edgar_screener.fetch import _http_get
        return _http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_frame("Assets", "USD", "CY2024Q3I", get=get)
    assert calls["n"] == 2 and slept == [1.0]


def test_parse_bulk_joins_num_and_sub_filters_tags_skips_empty():
    sub = "adsh\tcik\tname\tsic\tform\tperiod\tfy\tfp\tfiled\n" \
          "acc1\t320193\tAPPLE INC\t3571\t10-K\t20240928\t2024\tFY\t20241101\n"
    num = "adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n" \
          "acc1\tNetIncomeLoss\tus-gaap/2024\t20240928\t4\tUSD\t93736000000\n" \
          "acc1\tIgnoredTag\tus-gaap/2024\t20240928\t4\tUSD\t1\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("sub.tsv", sub)
        z.writestr("num.tsv", num)
    rows = fetch.parse_bulk(buf.getvalue(), {"NetIncomeLoss"})
    assert len(rows) == 1
    assert rows[0]["cik"] == 320193 and rows[0]["form"] == "10-K"
    assert rows[0]["value"] == 93736000000.0
    assert rows[0]["period_end"] == "2024-09-28"   # ddate normalized to ISO
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `sec_fundamentals/fetch.py`:

```python
"""data.sec.gov XBRL client + pure parsers. Reuses edgar_screener's SEC
scaffolding (UA, bounded backoff over 403/429/503) verbatim — see the note in
[[edgar-sec-rate-limit-followup]] on SEC fingerprint-blocking bare urllib."""
import csv
import io
import json
import zipfile

from edgar_screener.fetch import _http_get, fetch_ticker_map  # reuse UA+backoff

__all__ = ["cik_str", "fetch_ticker_map", "parse_frame", "fetch_frame",
           "parse_company_facts", "fetch_company_facts", "fetch_submissions",
           "parse_bulk"]

_FRAMES = "https://data.sec.gov/api/xbrl/frames"
_FACTS = "https://data.sec.gov/api/xbrl/companyfacts"
_SUBS = "https://data.sec.gov/submissions"


def cik_str(cik: int) -> str:
    """10-digit zero-padded CIK path segment, e.g. 320193 -> 'CIK0000320193'."""
    return f"CIK{int(cik):010d}"


def _num(v):
    """Coerce a numeric string/number to float; blanks/None -> None."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unit_path(unit: str) -> str:
    """Frames URL unit segment: 'USD/shares' -> 'USD-per-shares'."""
    return unit.replace("/", "-per-")


def parse_frame(payload: dict) -> list:
    """Pure: a frames payload's data[] -> fact rows. Frames carry no
    form/fy/fp/filed, so those are None (the run substitutes form='FRAME')."""
    out = []
    for e in payload.get("data", []):
        out.append({
            "cik": e.get("cik"), "tag": None, "uom": None,
            "period_end": e.get("end"),
            "fiscal_year": e.get("fy"), "fiscal_period": e.get("fp"),
            "value": _num(e.get("val")),
            "form": e.get("form"), "filed": e.get("filed"),
            "accession": e.get("accn"),
        })
    return out


def fetch_frame(tag: str, unit: str, period: str, taxonomy: str = "us-gaap",
                get=_http_get) -> list:
    """GET a frames endpoint for (tag, unit, period). Caller supplies the
    correctly-suffixed period ('...QnI' instant vs '...Qn' duration)."""
    url = f"{_FRAMES}/{taxonomy}/{tag}/{_unit_path(unit)}/{period}.json"
    rows = parse_frame(json.loads(get(url)))
    for r in rows:                                  # stamp the requested tag/uom
        r["tag"], r["uom"] = tag, unit
    return rows


def parse_company_facts(payload: dict, tags) -> list:
    """Pure: walk facts[taxonomy][tag][units][uom][] for the curated tags only.
    Extension/non-curated tags ignored. companyfacts uses val/accn keys."""
    out = []
    for _taxonomy, tagmap in payload.get("facts", {}).items():
        for tag, body in tagmap.items():
            if tag not in tags:
                continue
            for uom, entries in body.get("units", {}).items():
                for e in entries:
                    out.append({
                        "tag": tag, "uom": uom, "period_end": e.get("end"),
                        "fiscal_year": e.get("fy"), "fiscal_period": e.get("fp"),
                        "value": _num(e.get("val")), "form": e.get("form"),
                        "filed": e.get("filed"), "accession": e.get("accn"),
                    })
    return out


def fetch_company_facts(cik: int, get=_http_get) -> dict:
    """GET companyfacts for one CIK. Returns the raw payload (run parses it)."""
    return json.loads(get(f"{_FACTS}/{cik_str(cik)}.json"))


def fetch_submissions(cik: int, get=_http_get) -> dict:
    """GET the submissions (filing history) payload for one CIK."""
    return json.loads(get(f"{_SUBS}/{cik_str(cik)}.json"))


def _iso(ddate: str) -> str:
    """SEC bulk ddate 'YYYYMMDD' -> 'YYYY-MM-DD'."""
    s = str(ddate)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s


def parse_bulk(zip_bytes: bytes, tags) -> list:
    """Optional --bulk: num.tsv joined to sub.tsv inside a quarterly ZIP,
    filtered to curated tags, emitting the same fact-row shape. The 2009q1 ZIP is
    a header-only placeholder (sub/num present but no fact rows) -> yields []."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        subs = {}
        with z.open("sub.tsv") as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t"):
                subs[row["adsh"]] = row
        out = []
        with z.open("num.tsv") as fh:
            for row in csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t"):
                if row.get("tag") not in tags:
                    continue
                sub = subs.get(row["adsh"])
                if sub is None:
                    continue
                out.append({
                    "cik": int(sub["cik"]), "tag": row["tag"],
                    "uom": row.get("uom"), "period_end": _iso(row.get("ddate")),
                    "fiscal_year": _int(sub.get("fy")),
                    "fiscal_period": sub.get("fp"), "value": _num(row.get("value")),
                    "form": sub.get("form"), "filed": _iso(sub.get("filed")),
                    "accession": row["adsh"], "name": sub.get("name"),
                    "sic": sub.get("sic"),
                })
    return out


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add sec_fundamentals/fetch.py tests/test_sec_fundamentals_fetch.py
git commit -m "feat(fundamentals): data.sec.gov frames/companyfacts client + pure parsers + bulk"
```

---

## Task 3: `sec_fundamentals.db` — schema, writers, prune

**Files:**
- Create: `sec_fundamentals/db.py` (schema + writers + prune; **views added in Task 4**)
- Test: `tests/test_sec_fundamentals_db_schema.py`, `tests/test_sec_fundamentals_db_write.py`

**Interfaces:**
- `connect` — re-export from `screener_common`.
- `ensure_schema(conn)` — `companies`/`facts`/`snapshots` + indexes + views (views land in Task 4). Idempotent.
- `upsert_companies(conn, rows, captured_at)` — refresh ticker/name/sic/last_seen, preserve first_seen.
- `write_facts(conn, cik, rows) -> int` — upsert by `(cik, tag, period_end, form)`; dedupe batch (last wins).
- `write_snapshot(conn, captured_at, company_count, fact_count) -> int`.
- `prune(conn, keep_days, now_iso) -> int` — single-table snapshots delete.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sec_fundamentals_db_schema.py`:

```python
from sec_fundamentals import db


def test_ensure_schema_creates_tables_and_is_idempotent():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"companies", "facts", "snapshots"} <= tables


def test_facts_primary_key_includes_form():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(facts)")]
    assert {"cik", "tag", "period_end", "form", "value", "filed",
            "accession"} <= set(cols)
```

Create `tests/test_sec_fundamentals_db_write.py`:

```python
from sec_fundamentals import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _co(cik, ticker="AAPL", name="APPLE INC", sic="3571"):
    return {"cik": cik, "ticker": ticker, "name": name, "sic": sic}


def _fact(tag, period_end, form, value, filed="2024-11-01", accn="a1"):
    return {"tag": tag, "uom": "USD", "period_end": period_end,
            "fiscal_year": 2024, "fiscal_period": "FY", "value": value,
            "form": form, "filed": filed, "accession": accn}


def test_write_facts_upsert_overwrites_value_in_place():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(conn, 320193, [_fact("NetIncomeLoss", "2024-09-28", "10-Q", 90)])
    db.write_facts(conn, 320193, [_fact("NetIncomeLoss", "2024-09-28", "10-Q", 95)])
    rows = conn.execute("SELECT value FROM facts").fetchall()
    assert rows == [(95.0,)]                    # revised in place, no duplicate


def test_write_facts_different_form_is_a_new_row():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(conn, 320193, [
        _fact("NetIncomeLoss", "2024-09-28", "10-Q", 90),
        _fact("NetIncomeLoss", "2024-09-28", "10-K", 92),   # restatement
    ])
    n = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    assert n == 2                                # both kept -> feeds v_revisions


def test_write_facts_dedupes_within_batch_last_wins():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    n = db.write_facts(conn, 320193, [
        _fact("Assets", "2024-09-28", "10-K", 100),
        _fact("Assets", "2024-09-28", "10-K", 200),
    ])
    assert n == 1
    assert conn.execute("SELECT value FROM facts").fetchone()[0] == 200.0


def test_upsert_companies_preserves_first_seen_refreshes_label():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193, ticker="AAPL")], "t1")
    db.upsert_companies(conn, [_co(320193, ticker="APPL2")], "t2")
    row = conn.execute(
        "SELECT ticker, first_seen, last_seen FROM companies").fetchone()
    assert row == ("APPL2", "t1", "t2")


def test_prune_deletes_old_snapshots_not_facts():
    conn = _fresh()
    db.upsert_companies(conn, [_co(320193)], "t1")
    db.write_facts(conn, 320193, [_fact("Assets", "2024-09-28", "10-K", 100)])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)   # old
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)   # recent
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests to verify they fail** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `sec_fundamentals/db.py` (schema WITHOUT views for now — views appended in Task 4):

```python
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_companies", "write_facts",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,
    company_count INTEGER NOT NULL,
    fact_count    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS companies (
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,
    name       TEXT,
    sic        TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS facts (
    cik           INTEGER NOT NULL REFERENCES companies(cik),
    tag           TEXT    NOT NULL,
    uom           TEXT,
    period_end    TEXT    NOT NULL,
    fiscal_year   INTEGER,
    fiscal_period TEXT,
    value         REAL,
    form          TEXT    NOT NULL,
    filed         TEXT,
    accession     TEXT,
    PRIMARY KEY (cik, tag, period_end, form)
);
CREATE INDEX IF NOT EXISTS ix_facts_tag_period ON facts(tag, period_end);
CREATE INDEX IF NOT EXISTS ix_facts_cik        ON facts(cik);
"""

_FACT_COLS = ("tag", "uom", "period_end", "fiscal_year", "fiscal_period",
              "value", "form", "filed", "accession")


def ensure_schema(conn) -> None:
    """Create companies/facts/snapshots + indexes (+ views from _VIEWS). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_companies(conn, rows: list, captured_at: str) -> None:
    """Upsert the company dimension: refresh ticker/name/sic/last_seen, preserve
    first_seen (FRED upsert_series shape)."""
    params = [{"cik": r["cik"], "ticker": r.get("ticker"), "name": r.get("name"),
               "sic": r.get("sic"), "seen": captured_at} for r in rows]
    conn.executemany(
        """INSERT INTO companies (cik, ticker, name, sic, first_seen, last_seen)
           VALUES (:cik, :ticker, :name, :sic, :seen, :seen)
           ON CONFLICT(cik) DO UPDATE SET
             ticker=excluded.ticker, name=excluded.name, sic=excluded.sic,
             last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_facts(conn, cik: int, rows: list) -> int:
    """Upsert facts by (cik, tag, period_end, form): a revised value overwrites
    in place; a different form for the same period is a new row (v_revisions).
    Dedupes within the batch (last wins). Returns distinct rows written."""
    by_key = {(r["tag"], r["period_end"], r["form"]): r for r in rows}
    params = [(cik, r["tag"], r.get("uom"), r["period_end"], r.get("fiscal_year"),
               r.get("fiscal_period"), r.get("value"), r["form"], r.get("filed"),
               r.get("accession")) for r in by_key.values()]
    conn.executemany(
        f"""INSERT INTO facts (cik, {", ".join(_FACT_COLS)})
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cik, tag, period_end, form) DO UPDATE SET
              uom=excluded.uom, fiscal_year=excluded.fiscal_year,
              fiscal_period=excluded.fiscal_period, value=excluded.value,
              filed=excluded.filed, accession=excluded.accession""",
        params,
    )
    conn.commit()
    return len(params)


def write_snapshot(conn, captured_at: str, company_count: int,
                   fact_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, company_count, fact_count) "
        "VALUES (?, ?, ?)", (captured_at, company_count, fact_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Single-table delete only — facts are the historical store and are NEVER
    cascade-pruned (FRED prune shape, NOT the screener_common cascade)."""
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


# Views are defined in Task 4; start with an empty string so ensure_schema works
# now and gains the views when Task 4 fills this in.
_VIEWS = ""
```

- [ ] **Step 4: Run tests to verify they pass** — expect PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add sec_fundamentals/db.py tests/test_sec_fundamentals_db_schema.py tests/test_sec_fundamentals_db_write.py
git commit -m "feat(fundamentals): companies/facts/snapshots schema + panel upserts + single-table prune"
```

---

## Task 4: `sec_fundamentals.db` — ELT views (ratios derived in SQL)

**Files:**
- Modify: `sec_fundamentals/db.py` (fill `_VIEWS`)
- Test: `tests/test_sec_fundamentals_db_views.py`

**Interfaces (views, all `CREATE VIEW IF NOT EXISTS`):**
- `v_latest_fundamentals` — newest `value` per `(cik, tag)` joined to `companies`.
- `v_frame_cross_section` — all filers for one tag+period (caller filters).
- `v_screener` — pivoted key metrics per CIK + ratios (net margin, ROE, debt-to-equity) derived in SQL.
- `v_revisions` — same `(cik, tag, period_end)` under different `form` → restatements with value delta.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sec_fundamentals_db_views.py`:

```python
from sec_fundamentals import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_companies(conn, [{"cik": 1, "ticker": "AAA", "name": "Alpha",
                                "sic": "1"}], "t")
    return conn


def _f(tag, period_end, form, value, filed):
    return {"tag": tag, "uom": "USD", "period_end": period_end,
            "fiscal_year": int(period_end[:4]), "fiscal_period": "FY",
            "value": value, "form": form, "filed": filed, "accession": form}


def test_v_latest_fundamentals_picks_newest_period():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("Assets", "2023-12-31", "10-K", 100, "2024-02-01"),
        _f("Assets", "2024-12-31", "10-K", 150, "2025-02-01"),
    ])
    row = conn.execute("SELECT value FROM v_latest_fundamentals "
                       "WHERE tag='Assets'").fetchone()
    assert row == (150.0,)


def test_v_screener_derives_ratios():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("Revenues", "2024-12-31", "10-K", 1000, "2025-02-01"),
        _f("NetIncomeLoss", "2024-12-31", "10-K", 200, "2025-02-01"),
        _f("Liabilities", "2024-12-31", "10-K", 400, "2025-02-01"),
        _f("StockholdersEquity", "2024-12-31", "10-K", 800, "2025-02-01"),
    ])
    r = conn.execute(
        "SELECT net_margin, roe, debt_to_equity FROM v_screener "
        "WHERE cik=1").fetchone()
    assert abs(r[0] - 0.20) < 1e-9      # 200/1000
    assert abs(r[1] - 0.25) < 1e-9      # 200/800
    assert abs(r[2] - 0.50) < 1e-9      # 400/800


def test_v_screener_null_ratio_when_denominator_absent():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("NetIncomeLoss", "2024-12-31", "10-K", 200, "2025-02-01")])
    r = conn.execute("SELECT net_margin FROM v_screener WHERE cik=1").fetchone()
    assert r[0] is None                 # no Revenues -> NULL, not an error


def test_v_frame_cross_section_returns_all_filers_for_tag_period():
    conn = _seed()
    db.upsert_companies(conn, [{"cik": 2, "ticker": "BBB", "name": "Beta",
                                "sic": "1"}], "t")
    db.write_facts(conn, 1, [_f("Assets", "2024-12-31", "10-K", 10, "2025-02-01")])
    db.write_facts(conn, 2, [_f("Assets", "2024-12-31", "10-K", 20, "2025-02-01")])
    rows = conn.execute(
        "SELECT ticker, value FROM v_frame_cross_section "
        "WHERE tag='Assets' AND period_end='2024-12-31' ORDER BY value").fetchall()
    assert rows == [("AAA", 10.0), ("BBB", 20.0)]


def test_v_revisions_surfaces_restatement_with_delta():
    conn = _seed()
    db.write_facts(conn, 1, [
        _f("NetIncomeLoss", "2024-09-30", "10-Q", 90, "2024-11-01"),
        _f("NetIncomeLoss", "2024-09-30", "10-K", 100, "2025-02-01"),  # restated
    ])
    rows = conn.execute(
        "SELECT form, value, value_delta FROM v_revisions "
        "WHERE tag='NetIncomeLoss' ORDER BY filed").fetchall()
    assert rows[0] == ("10-Q", 90.0, None)         # first filing, no prior
    assert rows[1] == ("10-K", 100.0, 10.0)        # +10 restatement
```

- [ ] **Step 2: Run test to verify it fails** — the views don't exist yet → `OperationalError: no such table: v_latest_fundamentals` (or empty `_VIEWS`).

- [ ] **Step 3: Write minimal implementation**

In `sec_fundamentals/db.py`, replace `_VIEWS = ""` with:

```python
_VIEWS = """
-- Newest reported value per (cik, tag), joined to the company label.
CREATE VIEW IF NOT EXISTS v_latest_fundamentals AS
WITH ranked AS (
    SELECT f.*, ROW_NUMBER() OVER (
               PARTITION BY f.cik, f.tag
               ORDER BY f.period_end DESC, f.filed DESC) AS rn
    FROM facts f
)
SELECT r.cik, c.ticker, c.name, r.tag, r.uom, r.period_end,
       r.fiscal_year, r.fiscal_period, r.value, r.form, r.filed
FROM ranked r JOIN companies c ON c.cik = r.cik
WHERE r.rn = 1;

-- All filers' values for one tag+period (caller filters tag/period_end).
CREATE VIEW IF NOT EXISTS v_frame_cross_section AS
SELECT f.tag, f.period_end, f.cik, c.ticker, c.name, f.uom, f.value,
       f.fiscal_year, f.fiscal_period, f.form, f.filed
FROM facts f JOIN companies c ON c.cik = f.cik
ORDER BY f.tag, f.period_end, f.value DESC;

-- Pivoted headline metrics per company + ratios derived live from raw facts.
CREATE VIEW IF NOT EXISTS v_screener AS
WITH pivoted AS (
    SELECT l.cik, MAX(l.ticker) AS ticker, MAX(l.name) AS name,
      MAX(CASE WHEN l.tag IN ('Revenues',
             'RevenueFromContractWithCustomerExcludingAssessedTax')
          THEN l.value END) AS revenues,
      MAX(CASE WHEN l.tag='NetIncomeLoss' THEN l.value END) AS net_income,
      MAX(CASE WHEN l.tag='Assets' THEN l.value END) AS assets,
      MAX(CASE WHEN l.tag='Liabilities' THEN l.value END) AS liabilities,
      MAX(CASE WHEN l.tag='StockholdersEquity' THEN l.value END) AS equity,
      MAX(CASE WHEN l.tag='CommonStockSharesOutstanding' THEN l.value END) AS shares,
      MAX(CASE WHEN l.tag='EarningsPerShareDiluted' THEN l.value END) AS eps_diluted
    FROM v_latest_fundamentals l GROUP BY l.cik
)
SELECT p.cik, p.ticker, p.name, p.revenues, p.net_income, p.assets,
       p.liabilities, p.equity, p.shares, p.eps_diluted,
       CASE WHEN p.revenues IS NOT NULL AND p.revenues <> 0
            THEN p.net_income / p.revenues END AS net_margin,
       CASE WHEN p.equity IS NOT NULL AND p.equity <> 0
            THEN p.net_income / p.equity END AS roe,
       CASE WHEN p.equity IS NOT NULL AND p.equity <> 0
            THEN p.liabilities / p.equity END AS debt_to_equity
FROM pivoted p;

-- Restatements: a (cik, tag, period_end) reported under >1 form, with the delta.
CREATE VIEW IF NOT EXISTS v_revisions AS
WITH multi AS (
    SELECT cik, tag, period_end FROM facts
    GROUP BY cik, tag, period_end HAVING COUNT(*) > 1
),
seq AS (
    SELECT f.cik, f.tag, f.period_end, f.form, f.filed, f.value,
           f.value - LAG(f.value) OVER (
               PARTITION BY f.cik, f.tag, f.period_end
               ORDER BY f.filed) AS value_delta
    FROM facts f JOIN multi m
      ON m.cik=f.cik AND m.tag=f.tag AND m.period_end=f.period_end
)
SELECT s.cik, c.ticker, s.tag, s.period_end, s.form, s.filed, s.value,
       s.value_delta
FROM seq s JOIN companies c ON c.cik = s.cik
ORDER BY s.cik, s.tag, s.period_end, s.filed;
"""
```

- [ ] **Step 4: Run test to verify it passes** — expect PASS (5 tests). Run the whole db suite: `python -m pytest tests/test_sec_fundamentals_db_schema.py tests/test_sec_fundamentals_db_write.py tests/test_sec_fundamentals_db_views.py -v`.

- [ ] **Step 5: Commit**

```bash
git add sec_fundamentals/db.py tests/test_sec_fundamentals_db_views.py
git commit -m "feat(fundamentals): ELT views — latest, cross-section, screener ratios, revisions"
```

---

## Task 5: `sec_fundamentals.run` — orchestration + CLI

**Files:**
- Create: `sec_fundamentals/run.py`
- Test: `tests/test_sec_fundamentals_run.py`

**Interfaces:**
- `run(db_path, only=None, exclude=None, add=None, tickers=None, periods=None, bulk=False, keep_days=None, fetch_frame=fetch.fetch_frame, fetch_facts=fetch.fetch_company_facts, fetch_map=fetch.fetch_ticker_map, now_iso=None) -> (snapshot_id, company_count, fact_count)`.
- `main(argv=None)` — argparse, `prog="fundamentals"`.

**Behavior:** default period = most recent completed calendar quarter (from `now_iso`); instant concepts get the trailing `I`. Frames path: per `(concept, period)` → `fetch_frame` → per filer `upsert_companies` (ticker from `fetch_map`) + `write_facts` with `form='FRAME'`. Watchlist depth: per ticker CIK → `fetch_facts` → `parse_company_facts(payload, tags)` → write. Skip-and-continue + secret hygiene. All-fail → `(0,0)` snapshot + warning.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sec_fundamentals_run.py`:

```python
import sqlite3

from sec_fundamentals import run as runmod

NOW = "2026-05-01T00:00:00+00:00"      # most recent completed quarter: CY2026Q1
MAP = {1: {"ticker": "AAA", "title": "Alpha"},
       2: {"ticker": "BBB", "title": "Beta"}}


def _frame_rows(cik, value):
    return [{"cik": cik, "tag": None, "uom": None, "period_end": "2026-03-31",
             "fiscal_year": None, "fiscal_period": None, "value": value,
             "form": None, "filed": None, "accession": "acc"}]


def test_run_frames_path_writes_companies_and_facts(tmp_path):
    db_path = str(tmp_path / "f.db")

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        return _frame_rows(1, 100) + _frame_rows(2, 200)

    sid, ncomp, nfact = runmod.run(
        db_path, only=["Assets"], fetch_frame=fetch_frame,
        fetch_map=lambda: MAP, now_iso=NOW)
    assert ncomp == 2 and nfact == 2
    conn = sqlite3.connect(db_path)
    # frames facts carry the FRAME provenance marker
    forms = {r[0] for r in conn.execute("SELECT DISTINCT form FROM facts")}
    assert forms == {"FRAME"}
    assert conn.execute("SELECT ticker FROM companies WHERE cik=1").fetchone() \
        == ("AAA",)


def test_run_instant_concept_requests_I_suffixed_period():
    seen = {}

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        seen[tag] = period
        return []

    runmod.run(":memory:", only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: {}, now_iso=NOW)
    assert seen["Assets"].endswith("I")        # instant -> trailing I


def test_run_skips_failing_item_without_leaking_secret(tmp_path, capsys):
    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        if tag == "Assets":
            raise RuntimeError("http://data.sec.gov/secret boom")
        return _frame_rows(1, 5)

    sid, ncomp, nfact = runmod.run(
        str(tmp_path / "f.db"), only=["Assets", "Liabilities"],
        fetch_frame=fetch_frame, fetch_map=lambda: MAP, now_iso=NOW)
    assert nfact == 1                          # Assets skipped, Liabilities kept
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert "boom" not in err                   # secret hygiene: type name only


def test_run_watchlist_depth_uses_companyfacts(tmp_path):
    db_path = str(tmp_path / "f.db")
    payload = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        {"end": "2025-12-31", "val": 7, "fy": 2025, "fp": "FY",
         "form": "10-K", "filed": "2026-02-01", "accn": "a"}]}}}}}

    def fetch_facts(cik):
        return payload

    sid, ncomp, nfact = runmod.run(
        db_path, only=["NetIncomeLoss"], tickers=["AAA"],
        fetch_frame=lambda *a, **k: [], fetch_facts=fetch_facts,
        fetch_map=lambda: MAP, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT form, value FROM facts").fetchone()
    assert row == ("10-K", 7.0)                # real form from companyfacts


def test_run_all_fail_writes_zero_snapshot(tmp_path, capsys):
    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        raise RuntimeError("boom")

    sid, ncomp, nfact = runmod.run(
        str(tmp_path / "f.db"), only=["Assets"], fetch_frame=fetch_frame,
        fetch_map=lambda: {}, now_iso=NOW)
    assert (ncomp, nfact) == (0, 0)
    assert "warning" in capsys.readouterr().err.lower()


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "f.db")

    def fetch_frame(tag, unit, period, taxonomy="us-gaap"):
        return _frame_rows(1, 100)

    runmod.run(db_path, only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: MAP, now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, only=["Assets"], fetch_frame=fetch_frame,
               fetch_map=lambda: MAP, now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] >= 1
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `sec_fundamentals/run.py`:

```python
import argparse
import sys
from datetime import date, datetime, timezone

from sec_fundamentals import catalog, db, fetch


def _default_period(now_iso: str) -> str:
    """Most recent COMPLETED calendar quarter as 'CYyyyyQq' (no I suffix)."""
    d = date.fromisoformat(now_iso[:10])
    q = (d.month - 1) // 3 + 1 - 1        # previous quarter
    y = d.year
    if q == 0:
        q, y = 4, y - 1
    return f"CY{y}Q{q}"


def _period_for(concept, period: str) -> str:
    """Instant concepts take the trailing 'I'; durations do not."""
    return period + "I" if concept.kind == "instant" else period


def run(db_path, only=None, exclude=None, add=None, tickers=None, periods=None,
        bulk=False, keep_days=None, fetch_frame=fetch.fetch_frame,
        fetch_facts=fetch.fetch_company_facts, fetch_map=fetch.fetch_ticker_map,
        now_iso=None):
    """Pull curated XBRL concepts (frames cross-section + optional companyfacts
    watchlist depth) into the facts panel. Skip-and-continue; returns
    (snapshot_id, company_count, fact_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    tags = catalog.select_ids([c.tag for c in catalog.CATALOG], only, exclude,
                              add=add)
    tag_set = set(tags)
    by_tag = {c.tag: c for c in catalog.CATALOG}
    concepts = [by_tag[t] for t in tags if t in by_tag]
    periods = periods or [_default_period(now_iso)]

    ticker_map = {}
    try:
        ticker_map = fetch_map()
    except Exception as e:  # non-fatal: unmapped CIKs get ticker=NULL
        print(f"warning: ticker map unavailable: {type(e).__name__}",
              file=sys.stderr)
    cik_by_ticker = {v["ticker"]: k for k, v in ticker_map.items()}

    conn = db.connect(db_path)
    ciks_touched, fact_total = set(), 0
    try:
        db.ensure_schema(conn)

        # --- frames cross-section (primary) ---
        for concept in concepts:
            for period in periods:
                try:
                    rows = fetch_frame(concept.tag, concept.unit,
                                       _period_for(concept, period),
                                       concept.taxonomy)
                except Exception as e:
                    conn.rollback()
                    print(f"warning: skipping frame {concept.tag}@{period}: "
                          f"{type(e).__name__}", file=sys.stderr)
                    continue
                for r in rows:
                    cik = r.get("cik")
                    if cik is None:
                        continue
                    label = ticker_map.get(cik, {})
                    db.upsert_companies(conn, [{"cik": cik,
                        "ticker": label.get("ticker"), "name": label.get("title"),
                        "sic": None}], now_iso)
                    r = {**r, "form": r.get("form") or "FRAME"}
                    fact_total += db.write_facts(conn, cik, [r])
                    ciks_touched.add(cik)

        # --- companyfacts watchlist depth (optional) ---
        for sym in (tickers or []):
            cik = cik_by_ticker.get(sym)
            if cik is None:
                print(f"warning: unmapped ticker {sym}", file=sys.stderr)
                continue
            try:
                payload = fetch_facts(cik)
                rows = fetch.parse_company_facts(payload, tag_set)
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping companyfacts {sym}: "
                      f"{type(e).__name__}", file=sys.stderr)
                continue
            label = ticker_map.get(cik, {})
            name = payload.get("entityName") or label.get("title")
            db.upsert_companies(conn, [{"cik": cik, "ticker": sym, "name": name,
                                        "sic": None}], now_iso)
            fact_total += db.write_facts(conn, cik, rows)
            ciks_touched.add(cik)

        company_count = len(ciks_touched)
        if company_count == 0 and fact_total == 0:
            print("warning: no fundamentals fetched (0 companies, 0 facts)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, company_count, fact_total)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, company_count, fact_total


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fundamentals",
        description="Pull SEC XBRL company fundamentals into a SQLite panel")
    p.add_argument("--db", default="fundamentals.db")
    p.add_argument("--only", default=None, help="comma-separated concept tags")
    p.add_argument("--exclude", default=None, help="comma-separated tags to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra tag not in the catalog (repeatable)")
    p.add_argument("--tickers", default=None,
                   help="watchlist for companyfacts depth (comma-separated)")
    p.add_argument("--period", action="append", default=None,
                   help="calendar period(s) e.g. CY2024Q3 (repeatable)")
    p.add_argument("--bulk", action="store_true",
                   help="backfill from the quarterly ZIP instead of the APIs")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, ncomp, nfact = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                          add=a.add, tickers=_split(a.tickers), periods=a.period,
                          bulk=a.bulk, keep_days=a.keep_days)
    print(f"stored {nfact} facts across {ncomp} companies into {a.db}")


if __name__ == "__main__":
    main()
```

> **`--bulk` note:** the CLI wires `--bulk` through to `run(bulk=True)`; `fetch.parse_bulk` is implemented and unit-tested (Task 2). Wiring the ZIP *download + per-quarter loop* into `run`'s body is a documented follow-up — the primary API path (frames + companyfacts) is the default and fully covered. Keep the flag accepted (no crash) even though v1's `run` does not yet execute the ZIP loop; note this in the roadmap entry.

- [ ] **Step 4: Run test to verify it passes** — expect PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add sec_fundamentals/run.py tests/test_sec_fundamentals_run.py
git commit -m "feat(fundamentals): run orchestration (frames + watchlist depth, skip-and-continue) + CLI"
```

---

## Task 6: Register `fundamentals` in the dispatcher

**Files:**
- Modify: `registry.py`
- Test: `tests/test_registry.py` (add one assertion)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_registry.py`:

```python
def test_dispatch_lists_fundamentals():
    import registry
    assert "fundamentals" in registry.REGISTRY
```

- [ ] **Step 2: Run test to verify it fails** — `AssertionError`.

- [ ] **Step 3: Write minimal implementation**

In `registry.py`, add the import and register (place near the other screeners, e.g. after `options_main`):

```python
from sec_fundamentals.run import main as fundamentals_main
```
```python
    "options": options_main,
    "fundamentals": fundamentals_main,
```

- [ ] **Step 4: Run test to verify it passes** — `python -m pytest tests/test_registry.py -v`.

- [ ] **Step 5: Run the FULL suite and commit**

Run: `python -m pytest`
Expected: PASS (entire suite green — new modules plus all existing screeners).

```bash
git add registry.py tests/test_registry.py
git commit -m "feat(fundamentals): register fundamentals dispatcher"
```

---

## Task 7: Roadmap bookkeeping

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move `fundamentals` to Built**

- Add a `fundamentals` row to the **Built ✅** table (link to this plan + the spec).
- Remove the `fundamentals` row from **Spec'd — data screeners 📝**.
- In **Recommended build order**, strike through item 5 (`fundamentals`) as ✅ Built, mirroring items 1–4; note the deferred **shared SEC throttle** and **`--bulk` run-loop** follow-ups.

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): mark fundamentals Built; note SEC-throttle + bulk follow-ups"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| `Concept` dataclass + curated CATALOG + `select_ids` (only/exclude/add) | Task 1 |
| CIK zero-pad; reuse `edgar` ticker map + UA/backoff | Task 2 |
| `parse_frame` / `parse_company_facts` pure, curated-tag filter, coercion | Task 2 |
| `fetch_frame` correct `I`/no-`I` period from `kind` | Task 2 (`_period_for` in Task 5) |
| Optional `parse_bulk` (num⋈sub, skip 2009q1 placeholder) | Task 2 |
| `companies`/`facts`/`snapshots` schema, `(cik,tag,period_end,form)` PK | Task 3 |
| `upsert_companies` preserve first_seen; `write_facts` upsert + revision row | Task 3 |
| Single-table prune, never cascade into facts | Task 3 |
| `v_latest_fundamentals` / `v_frame_cross_section` / `v_screener` (ratios) / `v_revisions` | Task 4 |
| `run` frames + watchlist depth, skip-and-continue, all-fail → (0,0) | Task 5 |
| Secret hygiene (type name only, never message) | Task 5 |
| CLI `--db/--only/--exclude/--add/--tickers/--period/--bulk/--keep-days` | Task 5 |
| Registry `"fundamentals"` | Task 6 |
| No credentials; `.env.example` unchanged | Global Constraints |

**2. Placeholder scan:** No `TODO` in code. Two spec items are **explicitly deferred with rationale** (shared SEC throttle; `--bulk` run-loop) — both surfaced in the roadmap entry, not silently dropped; the module ships fully functional on the default API path. `parse_bulk` itself is implemented and tested.

**3. Type consistency:** The fact-row dict keys (`tag, uom, period_end, fiscal_year, fiscal_period, value, form, filed, accession`) are identical across `parse_frame`/`parse_company_facts`/`parse_bulk` (Task 2), `write_facts`/`_FACT_COLS` (Task 3), and every test helper. `cik` is an `int` end-to-end (ticker map keys, `write_facts(conn, cik, …)`, PK). `form` is guaranteed non-null before `write_facts` (companyfacts carries it; frames path substitutes `'FRAME'`). Ratios in `v_screener` reference only the pivoted CTE aliases (Task 4).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-sec-fundamentals-screener.md`. Execute task-by-task via superpowers:subagent-driven-development or executing-plans, TDD (red → green → commit) per task, then run the full `python -m pytest` suite before the roadmap-bookkeeping commit.
