# CFTC Disaggregated + TFF COT Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing `cftc` screener from the single Legacy COT report to two additional CFTC trader-classification families — **Disaggregated** (managed-money speculator gauge) and **TFF** (leveraged-funds speculator gauge) — behind one new `--family` flag, defaulting to `legacy` so every existing invocation is byte-for-byte unchanged.

**Architecture:** Add a `Family(name, dataset_id, catalog, fact_table, field_map)` bundle. The Socrata fetch/backoff/token machinery, the 10-week revision lookback, the `markets` dimension, and the run orchestration are all shared verbatim — a family just selects *which dataset id, which trader columns, and which fact table* to route through. Each family gets its own fact table (`cot`, `cot_disagg`, `cot_tff`) and its own COT-Index view chain over that family's key speculator net.

**Tech Stack:** Python 3 standard library only (`urllib`, `sqlite3`, `argparse`), the repo's shared `http_client` (bounded backoff) and `screener_common.connect` (WAL SQLite), pytest.

## Global Constraints

Copied verbatim from the design spec; every task's requirements implicitly include these.

- **Standard library only** — no new third-party dependencies; no new `.env` variables (the optional `CFTC_APP_TOKEN` already covers all families).
- **Dispatcher stays `cftc`** — one `registry.py` entry, unchanged. The only new surface is `--family {legacy,disaggregated,tff}`, **default `legacy`**.
- **Byte-for-byte back-compat** — the 41 existing `test_cftc_*` tests must keep passing. Every generalized function keeps its legacy call form working via defaults.
- **Datasets, same host** `https://publicreporting.cftc.gov/resource/{dataset_id}.json`: Legacy `6dca-aqww`, Disaggregated `72hh-3qpy`, TFF `gpe5-46if`. **Futures-only** for all families.
- **User-Agent** header is exactly `agentic-trading-bot ninadk.dev@gmail.com`.
- **Secret hygiene** — on a per-market failure log only `type(e).__name__` to stderr; **never** `str(e)` or `e.url` (they may echo the request URL or app token).
- **Socrata query** — `$limit` max `50000`; order by `report_date_as_yyyy_mm_dd` ascending; stable key `cftc_contract_market_code`.
- **COT-Index** — a 0–100 percentile of the family's key speculator net within its trailing **156-week window** (`ROWS BETWEEN 155 PRECEDING AND CURRENT ROW`); `NULL` when `hi = lo`; extremes at `>= 90` or `<= 10`.
- **Every fact table** keeps `PRIMARY KEY (code, report_date)`, `REFERENCES markets(code)`, and `CREATE INDEX ... ON <table>(report_date)`.
- **`prune` deletes snapshot provenance only** — it must never cascade into any `cot*` fact table (positioning history is the store).
- **Supplemental family is out of scope** (non-goal): its dataset id and columns are unconfirmed 🟡. Do **not** register a non-functional `supplemental` family; leave a TODO comment only.
- **🟡 Field-name verification:** the Disaggregated/TFF socrata field names below follow CFTC's published Socrata schema but must be confirmed against the live dataset at implementation time (see Task 1, Step 8). The `run` skip-and-continue already tolerates a bad code/column gracefully.

---

## File Structure

All changes extend `cftc_screener/` in place — no new package, no new dispatcher.

- `cftc_screener/fetch.py` — **owns the field maps** (socrata field names + coercion). Add `LEGACY_FIELDS`, `DISAGG_FIELDS`, `TFF_FIELDS` triple-lists; parametrize `_build_url`, `parse_rows`, `fetch_market_rows` by `dataset_id` + `field_map` (legacy defaults). *(Task 1)*
- `cftc_screener/catalog.py` — add the `Family` dataclass, `DISAGG_CATALOG` / `TFF_CATALOG` (derived from the legacy catalog by asset class), and the `FAMILIES` registry (imports the field maps from `fetch`). *(Task 2)*
- `cftc_screener/db.py` — add `cot_disagg` + `cot_tff` tables and their view chains; refactor the upsert into a shared `_upsert_facts`; add `write_family`; generalize `max_report_date` by an optional `fact_table`. *(Task 3)*
- `cftc_screener/run.py` — add the `family="legacy"` param and `--family` CLI flag; resolve the family once and thread `dataset_id` / `field_map` / `fact_table` through. *(Task 4)*
- `tests/test_cftc_*.py` — extend each with a family axis. *(interleaved per task)*
- `docs/ROADMAP.md` — move the Disaggregated/TFF row from *Spec'd* to *Planned* with a link to this plan. *(Task 5)*

**Import layering (no cycle):** `fetch` imports only `http_client`; `catalog` imports `fetch`; `db` imports `screener_common`; `run` imports `catalog`, `db`, `fetch`. `catalog → fetch` is one-directional.

---

### Task 1: Parametrize `fetch.py` by dataset + field map

**Files:**
- Modify: `cftc_screener/fetch.py`
- Test: `tests/test_cftc_fetch.py`

**Interfaces:**
- Consumes: `http_client.make_opener`, `http_client.http_get` (unchanged).
- Produces (relied on by Tasks 2–4):
  - `LEGACY_FIELDS`, `DISAGG_FIELDS`, `TFF_FIELDS: list[tuple[str, str, type]]` — `(db_column, socrata_field, cast)` where `cast` is `int` or `float`.
  - `_LEGACY_DATASET: str = "6dca-aqww"`.
  - `_build_url(code, dataset_id=_LEGACY_DATASET, since=None, start=None, limit=_LIMIT) -> str`.
  - `parse_rows(records, field_map=LEGACY_FIELDS) -> list[dict]`.
  - `fetch_market_rows(code, dataset_id=_LEGACY_DATASET, field_map=LEGACY_FIELDS, app_token=None, since=None, start=None, get=_http_get, opener=None) -> list[dict]`.
  - Unchanged & still exported: `_headers`, `_make_opener`, `_http_get`, `_urlopen`, `_num`, `API_URL`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_cftc_fetch.py`)

```python
# --- family extension ---
from cftc_screener.fetch import DISAGG_FIELDS, LEGACY_FIELDS, TFF_FIELDS

# A Disaggregated Socrata record (subset), values as strings.
DISAGG_REC = {
    "cftc_contract_market_code": "088691",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-06-23T00:00:00.000",
    "open_interest_all": "500000",
    "m_money_positions_long_all": "120000",
    "m_money_positions_short_all": "40000",
    "swap_positions_long_all": "30000",
    "pct_of_oi_m_money_long_all": "24.0",
    "conc_net_le_4_tdr_long_all": "18.2",
}


def test_field_maps_are_disjoint_triples():
    for fmap in (LEGACY_FIELDS, DISAGG_FIELDS, TFF_FIELDS):
        assert fmap, "field map must be non-empty"
        for col, api, cast in fmap:              # unpack proves 3-tuple shape
            assert isinstance(col, str) and isinstance(api, str)
            assert cast in (int, float)
        cols = [c for c, _a, _cast in fmap]
        assert len(cols) == len(set(cols)), "db columns must be unique"


def test_build_url_targets_family_dataset():
    url = _build_url("088691", dataset_id="72hh-3qpy")
    assert url.startswith(
        "https://publicreporting.cftc.gov/resource/72hh-3qpy.json?")
    assert "cftc_contract_market_code%3D%27088691%27" in url


def test_build_url_defaults_to_legacy_dataset():
    assert _build_url("088691").startswith(
        "https://publicreporting.cftc.gov/resource/6dca-aqww.json?")


def test_parse_rows_with_disagg_field_map():
    [row] = parse_rows([DISAGG_REC], DISAGG_FIELDS)
    assert row["code"] == "088691"
    assert row["report_date"] == "2026-06-23"          # timestamp truncated
    assert row["name"] == "GOLD - COMMODITY EXCHANGE INC."
    assert row["mm_long"] == 120000                    # int coercion
    assert row["mm_short"] == 40000
    assert row["pct_oi_mm_long"] == 24.0               # float coercion
    assert row["conc_net_4_long"] == 18.2
    assert row["mm_spread"] is None                    # absent -> None


def test_fetch_market_rows_threads_dataset_and_field_map():
    seen = {}

    def fake_get(url, opener=None):
        seen["url"] = url
        return json.dumps([DISAGG_REC])

    rows = fetch_market_rows("088691", dataset_id="72hh-3qpy",
                             field_map=DISAGG_FIELDS, get=fake_get)
    assert "72hh-3qpy.json" in seen["url"]
    assert rows[0]["mm_long"] == 120000
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cftc_fetch.py -q`
Expected: FAIL with `ImportError: cannot import name 'DISAGG_FIELDS'`.

- [ ] **Step 3: Add the dataset constant and the three field maps**

In `cftc_screener/fetch.py`, replace the hardcoded `API_URL` line with a host template + legacy dataset id, and keep `API_URL` for back-compat:

```python
_HOST = "https://publicreporting.cftc.gov/resource/{}.json"
_LEGACY_DATASET = "6dca-aqww"
API_URL = _HOST.format(_LEGACY_DATASET)  # legacy default; back-compat
```

Keep the existing `_INT_FIELDS` and `_FLOAT_FIELDS` lists exactly as they are, then build the legacy triple-map from them (DRY — single source for legacy field names):

```python
# Unified (db_column, socrata_field, cast) triples. Legacy is assembled from the
# existing int/float lists so its field names live in exactly one place.
LEGACY_FIELDS = ([(c, api, int) for c, api in _INT_FIELDS] +
                 [(c, api, float) for c, api in _FLOAT_FIELDS])

# Disaggregated Futures-Only (72hh-3qpy). Producer/Merchant + Swap Dealers
# (hedgers); Managed Money + Other Reportables (speculators); Nonreportable.
# 🟡 socrata field names follow CFTC's published Disaggregated schema — confirm
# live (Step 8).
DISAGG_FIELDS = [
    ("open_interest", "open_interest_all", int),
    ("prod_merc_long", "prod_merc_positions_long_all", int),
    ("prod_merc_short", "prod_merc_positions_short_all", int),
    ("swap_long", "swap_positions_long_all", int),
    ("swap_short", "swap_positions_short_all", int),
    ("swap_spread", "swap_positions_spread_all", int),
    ("mm_long", "m_money_positions_long_all", int),
    ("mm_short", "m_money_positions_short_all", int),
    ("mm_spread", "m_money_positions_spread_all", int),
    ("other_rept_long", "other_rept_positions_long_all", int),
    ("other_rept_short", "other_rept_positions_short_all", int),
    ("other_rept_spread", "other_rept_positions_spread_all", int),
    ("nonrept_long", "nonrept_positions_long_all", int),
    ("nonrept_short", "nonrept_positions_short_all", int),
    ("chg_oi", "change_in_open_interest_all", int),
    ("chg_mm_long", "change_in_m_money_long_all", int),
    ("chg_mm_short", "change_in_m_money_short_all", int),
    ("chg_swap_long", "change_in_swap_long_all", int),
    ("chg_swap_short", "change_in_swap_short_all", int),
    ("pct_oi_mm_long", "pct_of_oi_m_money_long_all", float),
    ("pct_oi_mm_short", "pct_of_oi_m_money_short_all", float),
    ("pct_oi_swap_long", "pct_of_oi_swap_long_all", float),
    ("pct_oi_swap_short", "pct_of_oi_swap_short_all", float),
    ("traders_total", "traders_tot_all", int),
    ("traders_mm_long", "traders_m_money_long_all", int),
    ("traders_mm_short", "traders_m_money_short_all", int),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all", float),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all", float),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all", float),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all", float),
]

# Traders in Financial Futures (gpe5-46if). Dealer/Intermediary (sell-side);
# Asset Manager/Institutional; Leveraged Funds (the key gauge); Other
# Reportables; Nonreportable. 🟡 confirm field names live (Step 8).
TFF_FIELDS = [
    ("open_interest", "open_interest_all", int),
    ("dealer_long", "dealer_positions_long_all", int),
    ("dealer_short", "dealer_positions_short_all", int),
    ("dealer_spread", "dealer_positions_spread_all", int),
    ("asset_mgr_long", "asset_mgr_positions_long_all", int),
    ("asset_mgr_short", "asset_mgr_positions_short_all", int),
    ("asset_mgr_spread", "asset_mgr_positions_spread_all", int),
    ("lev_long", "lev_money_positions_long_all", int),
    ("lev_short", "lev_money_positions_short_all", int),
    ("lev_spread", "lev_money_positions_spread_all", int),
    ("other_rept_long", "other_rept_positions_long_all", int),
    ("other_rept_short", "other_rept_positions_short_all", int),
    ("other_rept_spread", "other_rept_positions_spread_all", int),
    ("nonrept_long", "nonrept_positions_long_all", int),
    ("nonrept_short", "nonrept_positions_short_all", int),
    ("chg_oi", "change_in_open_interest_all", int),
    ("chg_lev_long", "change_in_lev_money_long_all", int),
    ("chg_lev_short", "change_in_lev_money_short_all", int),
    ("chg_asset_mgr_long", "change_in_asset_mgr_long_all", int),
    ("chg_asset_mgr_short", "change_in_asset_mgr_short_all", int),
    ("pct_oi_lev_long", "pct_of_oi_lev_money_long_all", float),
    ("pct_oi_lev_short", "pct_of_oi_lev_money_short_all", float),
    ("pct_oi_asset_mgr_long", "pct_of_oi_asset_mgr_long_all", float),
    ("pct_oi_asset_mgr_short", "pct_of_oi_asset_mgr_short_all", float),
    ("traders_total", "traders_tot_all", int),
    ("traders_lev_long", "traders_lev_money_long_all", int),
    ("traders_lev_short", "traders_lev_money_short_all", int),
    ("conc_net_4_long", "conc_net_le_4_tdr_long_all", float),
    ("conc_net_8_long", "conc_net_le_8_tdr_long_all", float),
    ("conc_net_4_short", "conc_net_le_4_tdr_short_all", float),
    ("conc_net_8_short", "conc_net_le_8_tdr_short_all", float),
]
```

- [ ] **Step 4: Generalize `_build_url`, `parse_rows`, `fetch_market_rows`**

Replace the three function bodies in `cftc_screener/fetch.py`:

```python
def _build_url(code: str, dataset_id: str = _LEGACY_DATASET,
               since=None, start=None, limit: int = _LIMIT) -> str:
    """Socrata SODA query for one market on ``dataset_id``, ordered by report date
    ascending. ``since`` (YYYY-MM-DD) fetches strictly newer weeks; else ``start``
    sets an inclusive floor; else full history."""
    clauses = [f"cftc_contract_market_code='{code}'"]
    if since:
        clauses.append(f"report_date_as_yyyy_mm_dd > '{since}T00:00:00'")
    elif start:
        clauses.append(f"report_date_as_yyyy_mm_dd >= '{start}T00:00:00'")
    params = {"$where": " AND ".join(clauses),
              "$order": "report_date_as_yyyy_mm_dd",
              "$limit": limit}
    return f"{_HOST.format(dataset_id)}?{urllib.parse.urlencode(params)}"


def parse_rows(records: list, field_map=LEGACY_FIELDS) -> list[dict]:
    """Map Socrata records to curated rows using ``field_map`` — a list of
    (db_column, socrata_field, cast) triples. Coerce numeric strings, absent
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
        for col, api, cast in field_map:
            row[col] = _num(rec.get(api), cast)
        out.append(row)
    return out


def fetch_market_rows(code: str, dataset_id: str = _LEGACY_DATASET,
                      field_map=LEGACY_FIELDS, app_token=None, since=None,
                      start=None, get=_http_get, opener=None) -> list[dict]:
    """Fetch one market's COT rows from ``dataset_id`` using ``field_map``
    (incremental when ``since`` given)."""
    op = opener if opener is not None else _make_opener(app_token)
    url = _build_url(code, dataset_id, since=since, start=start)
    return parse_rows(json.loads(get(url, opener=op)), field_map)
```

Delete the now-unused module-level `parse_rows`/`_build_url` originals (you are replacing them in place). Leave `_INT_FIELDS`, `_FLOAT_FIELDS`, `_num`, `_headers`, `_make_opener`, `_http_get`, `_urlopen` untouched.

- [ ] **Step 5: Run the new + existing fetch tests**

Run: `python -m pytest tests/test_cftc_fetch.py -q`
Expected: PASS (all — the legacy `test_parse_rows_*` and `test_build_url_*` still pass because the new params default to legacy).

- [ ] **Step 6: Commit**

```bash
git add cftc_screener/fetch.py tests/test_cftc_fetch.py
git commit -m "feat(cftc): parametrize fetch by dataset id + field map (Disaggregated/TFF field maps)"
```

- [ ] **Step 7 (verification, no code):** Run the full CFTC suite to confirm nothing regressed.

Run: `python -m pytest tests/ -q -k cftc`
Expected: PASS.

- [ ] **Step 8 (🟡 live field-name confirmation — do once, before Task 4's real run):** With network available, confirm the Disaggregated/TFF socrata field names against one live row each:

```bash
curl -s "https://publicreporting.cftc.gov/resource/72hh-3qpy.json?\$limit=1" | python -m json.tool | grep -Ei "m_money|swap_positions|prod_merc"
curl -s "https://publicreporting.cftc.gov/resource/gpe5-46if.json?\$limit=1" | python -m json.tool | grep -Ei "lev_money|asset_mgr|dealer_positions"
```
If any socrata field name differs from `DISAGG_FIELDS`/`TFF_FIELDS`, correct the `api` (second) element of the affected triple and re-run Step 5. The `db_column` (first) elements are fixed by the schema in Task 3 — do not rename them.

---

### Task 2: Add the `Family` dataclass, per-family catalogs, and registry

**Files:**
- Modify: `cftc_screener/catalog.py`
- Test: `tests/test_cftc_catalog.py`

**Interfaces:**
- Consumes: `fetch.LEGACY_FIELDS`, `fetch.DISAGG_FIELDS`, `fetch.TFF_FIELDS`, `fetch._LEGACY_DATASET` (Task 1); the existing `CATALOG`, `Market`.
- Produces (relied on by Tasks 3–4):
  - `Family(name: str, dataset_id: str, catalog: list[Market], fact_table: str, field_map: list)` — frozen dataclass.
  - `DISAGG_CATALOG`, `TFF_CATALOG: list[Market]`.
  - `FAMILIES: dict[str, Family]` with keys `"legacy"`, `"disaggregated"`, `"tff"`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_cftc_catalog.py`)

```python
# --- family extension ---
from cftc_screener.catalog import DISAGG_CATALOG, FAMILIES, Family, TFF_CATALOG

_PHYSICAL = {"metals", "energy", "ags", "softs"}
_FINANCIAL = {"equity_index", "rates", "fx"}


def test_families_registry_resolves_three_names():
    assert set(FAMILIES) == {"legacy", "disaggregated", "tff"}
    for fam in FAMILIES.values():
        assert isinstance(fam, Family)
        assert fam.catalog, f"{fam.name} catalog must be non-empty"
        assert fam.dataset_id and fam.fact_table and fam.field_map


def test_family_fact_tables_are_distinct():
    tables = {f.fact_table for f in FAMILIES.values()}
    assert tables == {"cot", "cot_disagg", "cot_tff"}


def test_disagg_catalog_is_physical_commodities_only():
    assert DISAGG_CATALOG
    assert all(m.asset_class in _PHYSICAL for m in DISAGG_CATALOG)


def test_tff_catalog_is_financials_only():
    assert TFF_CATALOG
    assert all(m.asset_class in _FINANCIAL for m in TFF_CATALOG)


def test_family_catalogs_partition_the_legacy_catalog():
    # Disaggregated + TFF together cover exactly the legacy catalog, no overlap.
    disagg = {m.code for m in DISAGG_CATALOG}
    tff = {m.code for m in TFF_CATALOG}
    legacy = {m.code for m in FAMILIES["legacy"].catalog}
    assert disagg.isdisjoint(tff)
    assert disagg | tff == legacy
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_cftc_catalog.py -q`
Expected: FAIL with `ImportError: cannot import name 'FAMILIES'`.

- [ ] **Step 3: Add the dataclass, per-family catalogs, and registry** (append to `cftc_screener/catalog.py`)

```python
from cftc_screener import fetch

# The legacy catalog cleanly partitions by asset class: physical commodities are
# reported under Disaggregated, financial futures under TFF. Deriving the
# per-family catalogs from CATALOG keeps the verified contract codes in one place.
_PHYSICAL = {"metals", "energy", "ags", "softs"}
_FINANCIAL = {"equity_index", "rates", "fx"}
DISAGG_CATALOG: list[Market] = [m for m in CATALOG if m.asset_class in _PHYSICAL]
TFF_CATALOG:    list[Market] = [m for m in CATALOG if m.asset_class in _FINANCIAL]


@dataclass(frozen=True)
class Family:
    name: str            # legacy | disaggregated | tff
    dataset_id: str      # Socrata resource id
    catalog: list        # list[Market] the family reports
    fact_table: str      # cot | cot_disagg | cot_tff
    field_map: list      # (db_column, socrata_field, cast) triples for this family


LEGACY = Family("legacy", fetch._LEGACY_DATASET, CATALOG, "cot", fetch.LEGACY_FIELDS)
DISAGG = Family("disaggregated", "72hh-3qpy", DISAGG_CATALOG, "cot_disagg",
                fetch.DISAGG_FIELDS)
TFF = Family("tff", "gpe5-46if", TFF_CATALOG, "cot_tff", fetch.TFF_FIELDS)

# SUPPLEMENTAL (Commodity Index Traders, 13 ag markets, combined F&O) is a
# non-goal for this cut: its dataset id and columns are unconfirmed. Add a fourth
# Family here (and a `cot_supp` table + views in db.py) once verified live.
FAMILIES: dict[str, Family] = {f.name: f for f in (LEGACY, DISAGG, TFF)}
```

- [ ] **Step 4: Run the new + existing catalog tests**

Run: `python -m pytest tests/test_cftc_catalog.py -q`
Expected: PASS (all — the legacy `test_catalog_*` and `test_select_ids_*` are untouched).

- [ ] **Step 5: Commit**

```bash
git add cftc_screener/catalog.py tests/test_cftc_catalog.py
git commit -m "feat(cftc): add Family dataclass + Disaggregated/TFF catalogs + FAMILIES registry"
```

---

### Task 3: Add `cot_disagg` / `cot_tff` tables, views, and family-aware writers

**Files:**
- Modify: `cftc_screener/db.py`
- Test: `tests/test_cftc_db_schema.py`, `tests/test_cftc_db_write.py`, `tests/test_cftc_db_views.py`

**Interfaces:**
- Consumes: `catalog.DISAGG`, `catalog.TFF` (Task 2) in tests; `screener_common.connect` (unchanged).
- Produces (relied on by Task 4):
  - `write_family(conn, family, code, rows) -> int` — upsert by `(code, report_date)` into `family.fact_table` over columns derived from `family.field_map`. Dedupes within batch (last wins).
  - `max_report_date(conn, code, fact_table="cot")` — `MAX(report_date)` over `fact_table` for `code`, or `None`. **Legacy 2-arg call `max_report_date(conn, code)` still works.**
  - Tables `cot_disagg`, `cot_tff`; views `v_disagg_*`, `v_managed_money_extremes`, `v_tff_*`, `v_leveraged_funds_positioning`, `v_leveraged_funds_extremes`.
  - Unchanged & still exported: `write_cot`, `upsert_markets`, `write_snapshot`, `prune`, `ensure_schema`, `connect`.

- [ ] **Step 1: Write the failing schema tests** (append to `tests/test_cftc_db_schema.py`)

```python
# --- family extension ---
def test_family_tables_and_legacy_coexist():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"markets", "cot", "cot_disagg", "cot_tff", "snapshots"} <= tables


def test_cot_disagg_has_managed_money_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot_disagg)")}
    assert {"code", "report_date", "open_interest",
            "mm_long", "mm_short", "mm_spread", "swap_spread",
            "pct_oi_mm_long", "chg_mm_long"} <= cols


def test_cot_tff_has_leveraged_funds_columns():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cot_tff)")}
    assert {"code", "report_date", "open_interest",
            "lev_long", "lev_short", "lev_spread", "dealer_spread",
            "pct_oi_lev_long", "chg_lev_long"} <= cols


def test_family_views_exist():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_disagg_net", "v_disagg_cot_index_latest", "v_disagg_positioning",
            "v_managed_money_extremes", "v_tff_net", "v_tff_cot_index_latest",
            "v_leveraged_funds_positioning", "v_leveraged_funds_extremes"} <= views
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_cftc_db_schema.py -q`
Expected: FAIL (`no such table: cot_disagg`).

- [ ] **Step 3: Add the two fact tables to `_SCHEMA`**

In `cftc_screener/db.py`, extend the `_SCHEMA` string (before the `snapshots` table is fine; order only matters for the FK reference to `markets`, which stays first) with:

```sql
CREATE TABLE IF NOT EXISTS cot_disagg (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    prod_merc_long INTEGER, prod_merc_short INTEGER,
    swap_long INTEGER, swap_short INTEGER, swap_spread INTEGER,
    mm_long INTEGER, mm_short INTEGER, mm_spread INTEGER,
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    chg_oi INTEGER, chg_mm_long INTEGER, chg_mm_short INTEGER,
    chg_swap_long INTEGER, chg_swap_short INTEGER,
    pct_oi_mm_long REAL, pct_oi_mm_short REAL,
    pct_oi_swap_long REAL, pct_oi_swap_short REAL,
    traders_total INTEGER, traders_mm_long INTEGER, traders_mm_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_disagg_date ON cot_disagg(report_date);

CREATE TABLE IF NOT EXISTS cot_tff (
    code          TEXT NOT NULL REFERENCES markets(code),
    report_date   TEXT NOT NULL,
    open_interest INTEGER,
    dealer_long INTEGER, dealer_short INTEGER, dealer_spread INTEGER,
    asset_mgr_long INTEGER, asset_mgr_short INTEGER, asset_mgr_spread INTEGER,
    lev_long INTEGER, lev_short INTEGER, lev_spread INTEGER,
    other_rept_long INTEGER, other_rept_short INTEGER, other_rept_spread INTEGER,
    nonrept_long INTEGER, nonrept_short INTEGER,
    chg_oi INTEGER, chg_lev_long INTEGER, chg_lev_short INTEGER,
    chg_asset_mgr_long INTEGER, chg_asset_mgr_short INTEGER,
    pct_oi_lev_long REAL, pct_oi_lev_short REAL,
    pct_oi_asset_mgr_long REAL, pct_oi_asset_mgr_short REAL,
    traders_total INTEGER, traders_lev_long INTEGER, traders_lev_short INTEGER,
    conc_net_4_long REAL, conc_net_8_long REAL,
    conc_net_4_short REAL, conc_net_8_short REAL,
    PRIMARY KEY (code, report_date)
);
CREATE INDEX IF NOT EXISTS ix_cot_tff_date ON cot_tff(report_date);
```

> **Column-parity check:** each table's data columns must exactly equal the `db_column` (first) elements of the matching field map in `fetch.py` (`DISAGG_FIELDS` → `cot_disagg`, `TFF_FIELDS` → `cot_tff`), because `write_family` derives its INSERT column list from the field map. Task 3 Step 7 asserts this automatically.

- [ ] **Step 4: Add the family view chains**

In `cftc_screener/db.py`, add two new view scripts and execute them in `ensure_schema`. Append after the existing `_VIEWS` definition:

```python
_DISAGG_VIEWS = """
CREATE VIEW IF NOT EXISTS v_disagg_net AS
SELECT code, report_date, open_interest,
       mm_long - mm_short                 AS net_mm,        -- managed money (spec gauge)
       swap_long - swap_short             AS net_swap,
       prod_merc_long - prod_merc_short   AS net_prod_merc,
       other_rept_long - other_rept_short AS net_other
FROM cot_disagg;

CREATE VIEW IF NOT EXISTS v_disagg_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_disagg_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_mm, r.net_swap, r.net_prod_merc, r.net_other
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

CREATE VIEW IF NOT EXISTS v_disagg_cot_index AS
WITH w AS (
    SELECT code, report_date, net_mm,
           MIN(net_mm) OVER win AS lo,
           MAX(net_mm) OVER win AS hi
    FROM v_disagg_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_mm, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_mm - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_disagg_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_mm, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_disagg_cot_index)
SELECT code, report_date, net_mm, cot_index FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_disagg_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_mm, l.net_swap, l.net_prod_merc, l.net_other,
       ci.cot_index,
       c.pct_oi_mm_long, c.pct_oi_mm_short,
       c.chg_oi, c.chg_mm_long, c.chg_mm_short
FROM v_disagg_latest l
JOIN v_disagg_cot_index_latest ci
  ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot_disagg c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_managed_money_extremes AS
SELECT * FROM v_disagg_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""

_TFF_VIEWS = """
CREATE VIEW IF NOT EXISTS v_tff_net AS
SELECT code, report_date, open_interest,
       lev_long - lev_short               AS net_lev,       -- leveraged funds (spec gauge)
       asset_mgr_long - asset_mgr_short   AS net_asset_mgr,
       dealer_long - dealer_short         AS net_dealer,
       other_rept_long - other_rept_short AS net_other
FROM cot_tff;

CREATE VIEW IF NOT EXISTS v_tff_latest AS
WITH ranked AS (
    SELECT n.*, ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_tff_net n)
SELECT r.code, m.name, m.asset_class, r.report_date, r.open_interest,
       r.net_lev, r.net_asset_mgr, r.net_dealer, r.net_other
FROM ranked r JOIN markets m ON m.code = r.code
WHERE r.rn = 1;

CREATE VIEW IF NOT EXISTS v_tff_cot_index AS
WITH w AS (
    SELECT code, report_date, net_lev,
           MIN(net_lev) OVER win AS lo,
           MAX(net_lev) OVER win AS hi
    FROM v_tff_net
    WINDOW win AS (PARTITION BY code ORDER BY report_date
                   ROWS BETWEEN 155 PRECEDING AND CURRENT ROW))
SELECT code, report_date, net_lev, lo, hi,
       CASE WHEN hi <> lo
            THEN 100.0 * (net_lev - lo) / (hi - lo) END AS cot_index
FROM w;

CREATE VIEW IF NOT EXISTS v_tff_cot_index_latest AS
WITH ranked AS (
    SELECT code, report_date, net_lev, cot_index,
           ROW_NUMBER() OVER (PARTITION BY code ORDER BY report_date DESC) rn
    FROM v_tff_cot_index)
SELECT code, report_date, net_lev, cot_index FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_leveraged_funds_positioning AS
SELECT l.code, l.name, l.asset_class, l.report_date, l.open_interest,
       l.net_lev, l.net_asset_mgr, l.net_dealer, l.net_other,
       ci.cot_index,
       c.pct_oi_lev_long, c.pct_oi_lev_short,
       c.chg_oi, c.chg_lev_long, c.chg_lev_short
FROM v_tff_latest l
JOIN v_tff_cot_index_latest ci
  ON ci.code = l.code AND ci.report_date = l.report_date
JOIN cot_tff c ON c.code = l.code AND c.report_date = l.report_date;

CREATE VIEW IF NOT EXISTS v_leveraged_funds_extremes AS
SELECT * FROM v_leveraged_funds_positioning WHERE cot_index >= 90 OR cot_index <= 10;
"""
```

Update `ensure_schema` to run the new scripts:

```python
def ensure_schema(conn) -> None:
    """Create tables, indexes, and derived-signal views for every family.
    Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.executescript(_DISAGG_VIEWS)
    conn.executescript(_TFF_VIEWS)
    conn.commit()
```

- [ ] **Step 5: Run the schema tests**

Run: `python -m pytest tests/test_cftc_db_schema.py -q`
Expected: PASS.

- [ ] **Step 6: Refactor the writer and generalize `max_report_date`**

In `cftc_screener/db.py`, add `write_family` to `__all__`, factor the upsert into a shared helper, and keep `write_cot` as a thin legacy wrapper. Replace the existing `write_cot` and `max_report_date` definitions with:

```python
def _upsert_facts(conn, table: str, cols: list, code: str, rows: list) -> int:
    """Upsert rows into ``table`` by (code, report_date) over ``cols``. Revised
    weeks overwrite in place; dates never duplicated. Dedupes within the batch
    (last wins). ``table`` is a trusted internal name (a family fact table)."""
    by_date = {r["report_date"]: r for r in rows}
    allcols = ["code", "report_date"] + cols
    placeholders = ", ".join(":" + c for c in allcols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    params = []
    for date, r in by_date.items():
        p = {"code": code, "report_date": date}
        for c in cols:
            p[c] = r.get(c)
        params.append(p)
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(allcols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(code, report_date) DO UPDATE SET {updates}",
        params,
    )
    conn.commit()
    return len(by_date)


def write_cot(conn, code: str, rows: list[dict]) -> int:
    """Upsert legacy COT rows into `cot`. Back-compat wrapper over _upsert_facts."""
    return _upsert_facts(conn, "cot", _COT_COLS, code, rows)


def write_family(conn, family, code: str, rows: list[dict]) -> int:
    """Upsert one market's rows into ``family.fact_table``, over the db columns
    derived from ``family.field_map``. Same (code, report_date) upsert semantics
    as write_cot."""
    cols = [c for c, _api, _cast in family.field_map]
    return _upsert_facts(conn, family.fact_table, cols, code, rows)


def max_report_date(conn, code: str, fact_table: str = "cot"):
    """Latest stored report_date for a market in ``fact_table``, or None. The
    optional ``fact_table`` keeps the legacy 2-arg call working."""
    row = conn.execute(
        f"SELECT MAX(report_date) FROM {fact_table} WHERE code=?",
        (code,)).fetchone()
    return row[0] if row and row[0] else None
```

Update the `__all__` list to include `write_family`:

```python
__all__ = ["connect", "ensure_schema", "upsert_markets", "write_cot",
           "write_family", "max_report_date", "write_snapshot", "prune"]
```

- [ ] **Step 7: Write the failing write tests** (append to `tests/test_cftc_db_write.py`)

```python
# --- family extension ---
from cftc_screener import catalog

NOW = "2026-07-03T00:00:00+00:00"


def _seed_market(conn, code="088691"):
    db.upsert_markets(conn, [{"code": code, "name": "GOLD",
                              "asset_class": "metals"}], NOW)


def test_write_family_derived_columns_match_table():
    # write_family derives its INSERT columns from field_map; they must all be
    # real columns of the fact table (else sqlite raises "no column named ...").
    conn = _fresh()
    for fam in (catalog.DISAGG, catalog.TFF):
        tbl_cols = {r[1] for r in conn.execute(
            f"PRAGMA table_info({fam.fact_table})")}
        map_cols = {c for c, _a, _cast in fam.field_map}
        assert map_cols <= tbl_cols, f"{fam.name} field_map ⊄ {fam.fact_table}"


def test_write_family_upserts_disagg_by_date():
    conn = _fresh()
    _seed_market(conn)
    n1 = db.write_family(conn, catalog.DISAGG, "088691", [
        {"code": "088691", "report_date": "2026-06-16",
         "mm_long": 10, "mm_short": 2, "open_interest": 100},
        {"code": "088691", "report_date": "2026-06-23",
         "mm_long": 20, "mm_short": 3, "open_interest": 200},
    ])
    assert n1 == 2
    n2 = db.write_family(conn, catalog.DISAGG, "088691", [
        {"code": "088691", "report_date": "2026-06-23",
         "mm_long": 25, "mm_short": 3, "open_interest": 250},   # revision
    ])
    assert n2 == 1
    rows = conn.execute(
        "SELECT report_date, mm_long, open_interest FROM cot_disagg "
        "WHERE code='088691' ORDER BY report_date").fetchall()
    assert rows == [("2026-06-16", 10, 100), ("2026-06-23", 25, 250)]


def test_max_report_date_reads_family_table():
    conn = _fresh()
    _seed_market(conn)
    assert db.max_report_date(conn, "088691", "cot_disagg") is None
    db.write_family(conn, catalog.TFF, "088691", [
        {"code": "088691", "report_date": "2026-06-23", "lev_long": 5}])
    # legacy cot is still empty for this code; family table has the row
    assert db.max_report_date(conn, "088691") is None            # 2-arg legacy
    assert db.max_report_date(conn, "088691", "cot_tff") == "2026-06-23"


def test_prune_leaves_family_tables_intact():
    conn = _fresh()
    _seed_market(conn)
    db.write_family(conn, catalog.DISAGG, "088691", [
        {"code": "088691", "report_date": "2020-01-07", "mm_long": 1}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)   # old
    removed = db.prune(conn, keep_days=30, now_iso=NOW)
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM cot_disagg").fetchone()[0] == 1
```

- [ ] **Step 8: Run the write tests**

Run: `python -m pytest tests/test_cftc_db_write.py -q`
Expected: PASS (new + the legacy `test_write_cot_*`, `test_max_report_date_*`, `test_prune_*`).

- [ ] **Step 9: Write the failing view tests** (append to `tests/test_cftc_db_views.py`)

```python
# --- family extension ---
from cftc_screener import catalog


def _seed_disagg(conn, code, series, asset_class="metals"):
    """series: list of (report_date, mm_long, mm_short)."""
    db.upsert_markets(conn, [{"code": code, "name": "M",
                              "asset_class": asset_class}],
                      "2026-07-03T00:00:00+00:00")
    rows = [{"code": code, "report_date": d,
             "mm_long": lo, "mm_short": sh, "open_interest": 1000}
            for (d, lo, sh) in series]
    db.write_family(conn, catalog.DISAGG, code, rows)


def _seed_tff(conn, code, series, asset_class="equity_index"):
    """series: list of (report_date, lev_long, lev_short)."""
    db.upsert_markets(conn, [{"code": code, "name": "M",
                              "asset_class": asset_class}],
                      "2026-07-03T00:00:00+00:00")
    rows = [{"code": code, "report_date": d,
             "lev_long": lo, "lev_short": sh, "open_interest": 1000}
            for (d, lo, sh) in series]
    db.write_family(conn, catalog.TFF, code, rows)


def test_disagg_cot_index_is_percentile_of_managed_money_net():
    conn = _fresh()
    # net_mm walks 0, 100, then 50 (latest) -> lo=0, hi=100 -> index 50.
    _seed_disagg(conn, "G", [("2026-06-09", 0, 0), ("2026-06-16", 100, 0),
                             ("2026-06-23", 50, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_disagg_cot_index_latest WHERE code='G'"
    ).fetchone()[0]
    assert abs(idx - 50.0) < 1e-9


def test_managed_money_extremes_flags_crowded_only():
    conn = _fresh()
    _seed_disagg(conn, "HOT", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])  # index 100
    _seed_disagg(conn, "MILD", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0),
                                ("2026-06-30", 50, 0)])                        # index 50
    codes = {r[0] for r in conn.execute(
        "SELECT code FROM v_managed_money_extremes")}
    assert "HOT" in codes and "MILD" not in codes


def test_tff_cot_index_is_100_at_leveraged_max():
    conn = _fresh()
    _seed_tff(conn, "S", [("2026-06-16", 0, 0), ("2026-06-23", 100, 0)])
    idx = conn.execute(
        "SELECT cot_index FROM v_tff_cot_index_latest WHERE code='S'"
    ).fetchone()[0]
    assert idx == 100.0


def test_leveraged_funds_extremes_flags_crowded_short():
    conn = _fresh()
    # net_lev walks 100 then 0 (latest) -> lo=0, hi=100, latest=lo -> index 0.
    _seed_tff(conn, "SH", [("2026-06-16", 100, 0), ("2026-06-23", 0, 0)])
    codes = {r[0] for r in conn.execute(
        "SELECT code FROM v_leveraged_funds_extremes")}
    assert "SH" in codes
```

- [ ] **Step 10: Run the view tests**

Run: `python -m pytest tests/test_cftc_db_views.py -q`
Expected: PASS (new + all legacy `v_*` tests).

- [ ] **Step 11: Commit**

```bash
git add cftc_screener/db.py tests/test_cftc_db_schema.py tests/test_cftc_db_write.py tests/test_cftc_db_views.py
git commit -m "feat(cftc): add cot_disagg/cot_tff tables, family view chains, write_family"
```

---

### Task 4: Add the `--family` flag and route it through `run.py`

**Files:**
- Modify: `cftc_screener/run.py`
- Test: `tests/test_cftc_run.py`

**Interfaces:**
- Consumes: `catalog.FAMILIES` (Task 2), `db.write_family`, `db.max_report_date(conn, code, fact_table)` (Task 3), `fetch.fetch_market_rows(code, dataset_id, field_map, ...)` (Task 1).
- Produces: `run(db_path, ..., family="legacy", ...)`; CLI `--family {legacy,disaggregated,tff}` (default `legacy`).

- [ ] **Step 1: Update the existing run-test fakes to the new fetch signature**

`run` now calls `fetch_rows(code, dataset_id=..., field_map=..., app_token=..., start=...)`. Every injected fake in `tests/test_cftc_run.py` must accept the two new keyword params. In each existing test, change the fake signature from:

```python
def fake_fetch(code, app_token=None, since=None, start=None):
```
to:
```python
def fake_fetch(code, dataset_id=None, field_map=None, app_token=None,
               since=None, start=None):
```

Apply the same edit to every fake in the file: `fake_fetch`, `flaky`, and `boom` (the `_rows(...)` bodies are unchanged). Also update `test_run_skips_failing_write_and_continues`: `run` now writes via `write_family`, so patch that instead of `write_cot`:

```python
    orig_write = run_mod.db.write_family

    def flaky_write(conn, family, code, rows):
        if code == "BADW":
            raise RuntimeError("disk full")
        return orig_write(conn, family, code, rows)

    monkeypatch.setattr(run_mod.db, "write_family", flaky_write)
```

- [ ] **Step 2: Write the failing family tests** (append to `tests/test_cftc_run.py`)

```python
# --- family extension ---
from cftc_screener.catalog import Family


def _disagg_family(codes):
    return Family("disaggregated", "72hh-3qpy",
                  [Market(c, f"name-{c}", "metals") for c in codes],
                  "cot_disagg",
                  [("open_interest", "open_interest_all", int),
                   ("mm_long", "m_money_positions_long_all", int),
                   ("mm_short", "m_money_positions_short_all", int)])


def test_run_family_routes_dataset_and_writes_family_table(tmp_path, monkeypatch):
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "disaggregated",
                        _disagg_family(["A"]))
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None,
                   since=None, start=None):
        seen["dataset_id"] = dataset_id
        return [{"code": code, "report_date": "2026-06-23", "name": "name-A",
                 "open_interest": 100, "mm_long": 20, "mm_short": 5}]

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    assert seen["dataset_id"] == "72hh-3qpy"
    conn = db.connect(dbp)
    assert conn.execute("SELECT mm_long FROM cot_disagg WHERE code='A'"
                        ).fetchone()[0] == 20
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 0  # legacy untouched


def test_run_default_family_is_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod.catalog, "CATALOG",
                        [Market("A", "Alpha", "metals")])
    # Re-point the LEGACY family's catalog at the patched CATALOG for this test.
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "legacy",
                        Family("legacy", "6dca-aqww",
                               [Market("A", "Alpha", "metals")], "cot",
                               run_mod.fetch.LEGACY_FIELDS))

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None,
                   since=None, start=None):
        return _rows(code, [("2026-06-23", 7)])

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=fake_fetch)     # no family kwarg
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM cot").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM cot_disagg").fetchone()[0] == 0


def test_run_family_lookback_floor_uses_family_table(tmp_path, monkeypatch):
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "disaggregated",
                        _disagg_family(["A"]))
    seen = {}

    def fake_fetch(code, dataset_id=None, field_map=None, app_token=None,
                   since=None, start=None):
        seen.setdefault("start", []).append(start)
        return [{"code": code, "report_date": "2026-06-23",
                 "mm_long": 1, "mm_short": 0, "open_interest": 10}]

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    run_mod.run(dbp, family="disaggregated", now_iso=NOW, fetch_rows=fake_fetch)
    # 2026-06-23 minus 10 weeks (70 days) = 2026-04-14, read from cot_disagg
    assert seen["start"] == [None, "2026-04-14"]


def test_run_never_logs_exception_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_mod.catalog, "CATALOG", [Market("A", "Alpha", "metals")])
    monkeypatch.setitem(run_mod.catalog.FAMILIES, "legacy",
                        Family("legacy", "6dca-aqww",
                               [Market("A", "Alpha", "metals")], "cot",
                               run_mod.fetch.LEGACY_FIELDS))

    def boom(code, dataset_id=None, field_map=None, app_token=None,
             since=None, start=None):
        raise RuntimeError("SECRET-TOKEN-abc123")   # message must NOT leak

    dbp = str(tmp_path / "cftc.db")
    run_mod.run(dbp, now_iso=NOW, fetch_rows=boom)
    err = capsys.readouterr().err
    assert "A" in err                                # code is logged
    assert "SECRET-TOKEN-abc123" not in err          # message is not
    assert "RuntimeError" in err                     # class is
```

- [ ] **Step 3: Run to verify the new tests fail**

Run: `python -m pytest tests/test_cftc_run.py -q`
Expected: FAIL (`run() got an unexpected keyword argument 'family'`), and the updated `test_run_skips_failing_write_and_continues` fails on the `write_family` patch until Step 4 lands.

- [ ] **Step 4: Thread the family through `run.py`**

In `cftc_screener/run.py`, change `_fetch_floor` to take a `fact_table`, add `family="legacy"` to `run`, resolve the family, and route dataset/field_map/table:

```python
def _fetch_floor(conn, fact_table, code, start, full):
    """Inclusive report-date floor to fetch from for one market in ``fact_table``.
    A full re-pull (or a first-ever pull with no stored data) uses the caller's
    ``start`` (None = full history). Otherwise re-fetch a recent lookback window
    ending at the latest stored week."""
    if full:
        return start
    last = db.max_report_date(conn, code, fact_table)
    if last is None:
        return start
    return (datetime.fromisoformat(last)
            - timedelta(weeks=_LOOKBACK_WEEKS)).date().isoformat()


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        app_token=None, full=False, family="legacy",
        fetch_rows=fetch.fetch_market_rows, now_iso=None):
    """Fetch selected CFTC markets for one report ``family`` into SQLite,
    upserting weekly COT history into that family's fact table. Incremental runs
    re-fetch the last _LOOKBACK_WEEKS weeks per market to catch revisions;
    full=True re-pulls from ``start`` (or full history).
    Returns (snapshot_id, market_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    app_token = app_token or os.environ.get("CFTC_APP_TOKEN")  # optional; may be None

    fam = catalog.FAMILIES[family]
    asset = {m.code: m.asset_class for m in fam.catalog}
    all_codes = [m.code for m in fam.catalog]
    codes = catalog.select_ids(all_codes, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_rows = 0
        for code in codes:
            try:
                floor = _fetch_floor(conn, fam.fact_table, code, start, full)
                rows = fetch_rows(code, dataset_id=fam.dataset_id,
                                  field_map=fam.field_map,
                                  app_token=app_token, start=floor)
                if rows:
                    name = rows[-1].get("name")  # ordered ascending -> newest last
                    db.upsert_markets(conn, [{"code": code, "name": name,
                                              "asset_class": asset.get(code, "custom")}],
                                      now_iso)
                    total_rows += db.write_family(conn, fam, code, rows)
                successes += 1
            except Exception as e:  # skip-and-continue on any per-market failure
                # Roll back the failed market's uncommitted writes, then log only
                # the exception class — never str(e)/e.url, which may echo the
                # request URL or token.
                conn.rollback()
                print(f"warning: skipping {code}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        if successes == 0:
            print("warning: no CFTC markets fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows
```

Add the `--family` argument in `main` and pass it to `run`:

```python
    p.add_argument("--family", default="legacy",
                   choices=["legacy", "disaggregated", "tff"],
                   help="COT report family (default: legacy)")
```

and thread it into the `run(...)` call:

```python
    _, mc, rc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days, full=a.full, family=a.family)
    print(f"stored {rc} weekly rows across {mc} markets "
          f"({a.family}) into {a.db}")
```

- [ ] **Step 5: Run the run tests**

Run: `python -m pytest tests/test_cftc_run.py -q`
Expected: PASS (new + updated legacy tests).

- [ ] **Step 6: Run the full CFTC suite**

Run: `python -m pytest tests/ -q -k cftc`
Expected: PASS (every `test_cftc_*` green).

- [ ] **Step 7: Smoke-test the CLI end-to-end (real network, tiny slice)**

Confirm the new flag actually pulls and stores a Disaggregated market. This is the runtime observation that tests (which inject fakes) cannot give.

Run:
```bash
python main.py cftc --family disaggregated --only 088691 --db /tmp/cot_smoke.db
sqlite3 /tmp/cot_smoke.db "SELECT report_date, mm_long, mm_short FROM cot_disagg ORDER BY report_date DESC LIMIT 3;"
sqlite3 /tmp/cot_smoke.db "SELECT code, cot_index FROM v_managed_money_extremes;"
```
Expected: several weekly Gold rows with non-null `mm_long`/`mm_short`; the extremes view runs without error (may be empty). If `cot_disagg` is empty, a socrata field name is wrong → revisit Task 1 Step 8. Then `rm /tmp/cot_smoke.db`.

- [ ] **Step 8: Commit**

```bash
git add cftc_screener/run.py tests/test_cftc_run.py
git commit -m "feat(cftc): add --family flag routing legacy/disaggregated/tff through run"
```

---

### Task 5: Update the roadmap

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Move the Disaggregated/TFF row to Planned**

In `docs/ROADMAP.md`, delete this row from the **Spec'd — data screeners** table:

```markdown
| 🟢 | `cftc` (`--family`) | CFTC Disaggregated + TFF COT | Swap-dealer / managed-money / leveraged-fund positioning | [spec](superpowers/specs/2026-07-03-cot-disaggregated-tff-screener-design.md) |
```

and add it to the **Planned 📐** table (which already has a Plan column):

```markdown
| `cftc` (`--family`) | CFTC Disaggregated + TFF COT | Swap-dealer / managed-money / leveraged-fund positioning | [spec](superpowers/specs/2026-07-03-cot-disaggregated-tff-screener-design.md) | [plan](superpowers/plans/2026-07-03-cot-disaggregated-tff-screener.md) |
```

- [ ] **Step 2: Note completion in the build order**

In the **Recommended build order** section, update item 1 to point at the plan:

```markdown
1. **`cftc --family` (Disaggregated/TFF)** — clones the existing CFTC Socrata pipeline. → [plan](superpowers/plans/2026-07-03-cot-disaggregated-tff-screener.md)
```

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): move CFTC Disaggregated/TFF from Spec'd to Planned"
```

---

## Self-Review

**1. Spec coverage** (each spec section → task):
- `report_family` dimension / `--family` flag, default legacy → Task 4.
- Shared fetch/backoff/token, parametrized by `(dataset_id, field_map)` → Task 1.
- Per-family curated catalogs + `Family`/`FAMILIES` registry → Task 2.
- One fact table per family (`cot_disagg`, `cot_tff`), same shape, `PK (code, report_date)`, index, `REFERENCES markets(code)` → Task 3 Step 3.
- `write_family`, family-aware `max_report_date`; `prune`/`upsert_markets`/`write_snapshot` unchanged and non-cascading → Task 3 Steps 6–8, 11.
- Per-family view chains with speculator column swapped (managed-money / leveraged-funds), 156-week COT-Index, 90/10 extremes → Task 3 Step 4.
- 10-week revision lookback + `--full` inherited per family → Task 4 Step 4, `test_run_family_lookback_floor_uses_family_table`.
- Secret hygiene (class-only logging) → Task 4 `test_run_never_logs_exception_message`.
- Testing mirror (`test_cftc_catalog/fetch/db_schema/db_write/db_views/run`) → Tasks 1–4.
- Supplemental deferred (non-goal) → Task 2 Step 3 TODO comment; no registry entry.
- No new env vars / dispatcher unchanged → nothing to change (verified: `registry.py` still maps `"cftc": cftc_main`).

**2. Placeholder scan:** every code step carries complete code; the only "confirm live" item (socrata field names, 🟡 in the spec) is an explicit executable verification step (Task 1 Step 8, Task 4 Step 7) with concrete `curl` commands and a concrete fallback — not a TODO in the shipped code.

**3. Type consistency:** `field_map` is a `(db_column, socrata_field, cast)` triple everywhere (`fetch.py` maps, `parse_rows` unpack, `write_family`'s `[c for c, _a, _cast in ...]`, Task 3 Step 7 parity test). `Family(name, dataset_id, catalog, fact_table, field_map)` field order is identical in the dataclass (Task 2), the registry construction (Task 2), and every test constructor (Tasks 3–4). `max_report_date(conn, code, fact_table="cot")` and `write_family(conn, family, code, rows)` signatures match between definition (Task 3) and all call sites (Task 4). `_fetch_floor(conn, fact_table, code, start, full)` argument order matches its single call site in `run`.
