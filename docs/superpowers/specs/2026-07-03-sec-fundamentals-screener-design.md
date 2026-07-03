# SEC XBRL Fundamentals Screener — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [SEC XBRL financial-statement data](https://www.sec.gov/dera/data/financial-statement-data-sets.html)
(bulk quarterly ZIPs) + [data.sec.gov structured-data APIs](https://www.sec.gov/edgar/sec-api-documentation)
(`companyfacts` / `companyconcept` / `frames` / `submissions`) — the SEC's own
XBRL numbers extracted from every registrant's filings. No API key; a descriptive
`User-Agent` is mandatory (bare requests get `403`) and the ≤10 requests/second
fair-access cap applies.
**Confidence:** 🟢 verified (endpoints live-checked 2026-07-03).

## Goal

Pull **primary-source company fundamentals** — the XBRL facts SEC registrants
tag into their 10-K/10-Q filings (revenue, net income, assets, equity, EPS,
share counts…) — into SQLite, so the trading bot has an **auditable
fundamentals reader**: full reported history per company, straight from the
filings, with no vendor in the loop.

This is the **ninth** screener in the family (`stocks`, `reddit`, `edgar`,
`fred`, `cftc`, `ftd`, `short_volume`, `options`, and now `fundamentals`). It
reuses `screener_common`, the `http_client` bounded-backoff, and the
**FRED/CFTC panel layout**, and it is adjacent to `edgar` — both key on CIK and
share the SEC `User-Agent` + backoff.

## Positioning: a complement to `stocks`, not a replacement

The existing `stocks` screener (stockanalysis.com) is a **trusted aggregator**
the user keeps — it is fast, wide, and ships pre-computed ratios. `fundamentals`
does **not** replace it. It is the **official primary-source feed** underneath
it:

- **Auditable / primary-source.** Every number traces to a specific accession
  and filing date — you can point at the 10-Q it came from. No vendor
  normalization sits between the filing and the DB.
- **Full reported history + point-in-time.** XBRL carries both the original and
  the restated value (different `filed`/`accession` for the same `period_end`),
  so restatements are visible rather than silently overwritten by a vendor.
- **No vendor dependency.** If stockanalysis.com changes, breaks, or disagrees,
  this is the ground truth to **cross-check and backfill** against.

So the two coexist: `stocks` for breadth and convenience, `fundamentals` for
provenance and reconciliation. Deliberately **not** a goal to reproduce a
vendor's exact computed ratios (see Non-goals).

## Two access modes (both keyless, both require a UA)

Neither mode needs an API key. **Both** require a descriptive `User-Agent`
(`agentic-trading-bot ninadk.dev@gmail.com`) — SEC returns `403` without one —
and both obey the SEC's **10 requests/second** fair-access cap. This is the same
posture the `edgar` screener already uses; reuse its `_UA`, its
`http_client.make_opener`, and the bounded backoff over `_RETRY_STATUS =
{403, 429, 503}`. (Recall the EDGAR history: SEC not only 403s a bare client but
*fingerprint-blocks* plain `urllib` — already handled by `http_client`, whose
opener sends a real UA and whose backoff absorbs the 403s. See
[[edgar-sec-rate-limit-followup]].)

> **Recommendation: one shared ≤10 req/s throttle across all SEC screeners.**
> `edgar`, `ftd`, and `fundamentals` all hit `*.sec.gov` and the cap is
> **per-source, not per-screener** — running them back-to-back can exceed 10
> req/s in aggregate. A small shared rate-limiter (token-bucket keyed on the SEC
> host) belongs in `http_client` / `screener_common` so every SEC fetcher pays
> into the same budget. Called out here because this is the third SEC screener
> and the first with a per-entity call fan-out large enough to matter.

### A) Bulk quarterly ZIPs — full-universe backfill

`https://www.sec.gov/files/dera/data/financial-statement-data-sets/{YYYY}q{Q}.zip`

- **Coverage 2009Q1 → present**, live-verified 2026-07-03: HTTP 200 for **every**
  quarter `2009q1` … `2026q1`; `2026q2`+ correctly `404` (not yet published).
- Each ZIP is a set of flattened, tab-separated tables:
  - **`sub.tsv`** — submissions: `adsh, cik, name, sic, form, period, fy, fp,
    filed, …` (one row per filing).
  - **`tag.tsv`** — the tag dictionary (tag, version, custom flag, label…).
  - **`num.tsv`** — the numbers: `adsh, tag, version, ddate, qtrs, uom, value, …`
    (one row per reported fact).
  - **`pre.tsv`** — the presentation linkbase (statement/line ordering).
- **Gotchas:** `2009q1.zip` is a **header-only empty placeholder** (present but
  no facts — skip gracefully); XBRL as filed is **unaudited**; **custom/extension
  tags** proliferate and complicate normalization; the data is **keyed by CIK,
  not ticker**.
- **Best for:** cross-sectional full-universe screening and one-shot bulk
  backfill (all filers, all tags, one download per quarter).

> Heavier supplement, **non-goal for v1:** the **Financial Statement AND Notes
> Data Sets** —
> `https://www.sec.gov/files/dera/data/financial-statement-notes-data-sets/YYYY_MM_notes.zip`
> (recent periods = **monthly** files; older periods folded into quarterly
> `YYYYqQ_notes.zip`). SEC keeps only ~1 year of monthly files, so mid-range
> monthly URLs **legitimately 404** — not an error. These add a `txt.tsv` of
> note text (deep-disclosure detail). Bulkier; deferred.

### B) `data.sec.gov` JSON REST APIs — near-real-time, per-entity

All keyless, all UA-gated, all 10-digit zero-padded CIK:

- **companyfacts** —
  `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
  All XBRL concepts for one CIK (every tag × unit × period the company ever
  filed). Live-verified: Apple returned **~503 `us-gaap` concepts** in one call.
  → watchlist **depth**.
- **companyconcept** —
  `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/{Tag}.json`
  One company + one tag time series. → targeted single-metric pulls.
- **frames** —
  `https://data.sec.gov/api/xbrl/frames/us-gaap/{Tag}/USD/CY2019Q1I.json`
  **One fact across ALL filers for a calendar period** — the ideal
  cross-sectional screen without downloading a ZIP. **Period-format nuance
  (load-bearing):** `CY2019Q1I` = **instantaneous** (balance-sheet *stocks*:
  Assets, Liabilities, equity, shares outstanding); `CY2019Q1` (no trailing `I`)
  = **duration** (income/cash-flow *flows*: Revenues, NetIncomeLoss). The
  trailing **`I` matters** — request the wrong shape and the frame is empty.
- **submissions** —
  `https://data.sec.gov/submissions/CIK##########.json`
  Filing history for a CIK (used to resolve the newest `form`/`filed` and to seed
  `companies`).
- **Taxonomies:** non-custom only — **`us-gaap`, `ifrs-full`, `dei`, `srt`**.
  Company extension tags are out of scope for the curated concept list.

### Ticker ↔ CIK mapping

`https://www.sec.gov/files/company_tickers.json` → `{cik_str, ticker, title}`.
The `data.sec.gov` APIs need the **10-digit zero-padded** CIK
(`f"CIK{cik:010d}"`). The `edgar` screener already loads this exact map
(`fetch_ticker_map`) — **reuse it verbatim** rather than re-implement. Caveats to
carry into the design: **ticker reuse** (a symbol can be reassigned to a
different CIK over time), **symbol changes** (one CIK, many tickers historically),
and **multi-class share structures** (one CIK, several tickers) — so the
`cik → ticker` relation is not 1:1. We store CIK as the key and ticker as a
refreshable label.

## Data-shape classification: a *panel* (the FRED/CFTC shape)

- `stocks`/`reddit`/`edgar` are **cross-sectional** (snapshot-scoped state).
- `fred` is **time-series** (few series × dated observations).
- `cftc` is a **panel** keyed `(code, report_date)`, queried one instrument at a
  time.
- `fundamentals` is a **panel** too: **entity × concept × period** — many
  companies × curated tags × reporting periods. The fact is keyed
  `(cik, tag, period_end, form)` and **upserted**: a re-run overwrites a revised
  value in place and never duplicates the key, exactly like FRED's
  `write_observations` and CFTC's `write_cot`. As with those two, the fact
  history is **not snapshot-scoped** — `snapshots` records fetch-run provenance
  only, and the fundamentals history persists across pruning (FRED-style
  **single-table** prune of old `snapshots`, **never** a cascade into `facts`).

The `form` component of the key is deliberate: the same `period_end` can be
reported first in a 10-Q and later restated in a 10-K (or an amendment), and both
are worth keeping — that is precisely the point-in-time provenance `stocks`
cannot give us. (Restatements surface in `v_revisions`.)

## Recommended v1 design

Track a **curated `catalog.py` of financial concepts** (the tags the bot cares
about) against a **watchlist of tickers** (or `"all"`), mirroring
`fred_screener.catalog` / `cftc_screener.catalog`.

```python
@dataclass(frozen=True)
class Concept:
    tag: str          # us-gaap tag, the stable key, e.g. "NetIncomeLoss"
    taxonomy: str     # us-gaap | ifrs-full | dei | srt
    unit: str         # USD | shares | USD/shares
    kind: str         # "instant" (balance-sheet stock) | "duration" (flow)
    group: str        # income | balance | cashflow | shares | per_share
```

`CATALOG: list[Concept]` — a small, opinionated set of headline concepts:

- **income (duration):** `Revenues`,
  `RevenueFromContractWithCustomerExcludingAssessedTax`, `OperatingIncomeLoss`,
  `NetIncomeLoss`.
- **balance (instant):** `Assets`, `Liabilities`, `StockholdersEquity`,
  `CashAndCashEquivalentsAtCarryingValue`.
- **per-share / shares:** `EarningsPerShareDiluted` (`USD/shares`, duration),
  `CommonStockSharesOutstanding` (`shares`, instant).

`select_ids(all_tags, only, exclude, add=None)` — the **identical** ordered /
de-duped / blank-aware logic as `fred_screener.catalog.select_ids` and
`cftc_screener.catalog.select_ids`, so `--only/--exclude/--add` behave the same
across screeners. Concept tags are verified live at implementation time (like the
FRED catalog); any tag that returns no frames is dropped with a note.

**Primary v1 path — `frames` per `(tag, period)`** for cross-sectional screening
(one call yields every filer for one metric+period → the whole screen), **plus
`companyfacts` per watchlist ticker** for full depth. The quarterly-ZIP path is
an **optional `--bulk` backfill mode**, not the default (a first-run backfill of
all quarters is many hundred MB and rarely needed for a watchlist).

## Module layout

Mirrors `fred_screener` / `cftc_screener` module-for-module — the package triad
plus a catalog.

```
sec_fundamentals/
    __init__.py
    catalog.py   # Concept dataclass + curated CATALOG + select_ids()
    fetch.py     # data.sec.gov client (companyfacts/frames/submissions),
                 #   CIK zero-pad, ticker-map reuse, bulk-ZIP parse (--bulk)
    db.py        # schema (companies/facts/snapshots) + upserts + ELT views + prune
    run.py       # skip-and-continue orchestration + argparse main
```

Registered in `registry.py` as `"fundamentals": fundamentals_main` (alongside
`stocks`, `reddit`, `edgar`, `fred`, `cftc`, `ftd`, `short_volume`, `options`).
DB via `from screener_common import connect` (WAL). Prune is FRED-style
single-table (fundamentals history is NOT snapshot-scoped — it must **not** use
the `screener_common` cascade prune).

### Fetch (`sec_fundamentals/fetch.py`)

Pure parsers separated from HTTP so they unit-test against fixtures without
network. Reuses `edgar_screener`'s SEC scaffolding: the same `_UA`, the same
`http_client.make_opener` + bounded backoff, `_RETRY_STATUS = {403, 429, 503}`,
5 attempts, `Retry-After` honored.

- `cik_str(cik: int) -> str` — `f"CIK{cik:010d}"` (10-digit zero-pad).
- `fetch_ticker_map(...)` — **reuse** `edgar_screener.fetch.fetch_ticker_map`
  (`company_tickers.json` → `{cik: {ticker, title}}`); do not duplicate.
- `parse_frame(payload) -> list[dict]` — pure: map a `frames` payload's `data[]`
  to `{cik, value, end, fy, fp, form, filed, accession}`, coercing numeric
  strings and dropping absent cells to `None`.
- `fetch_frame(tag, unit, period, taxonomy="us-gaap", get=_http_get)` — GET the
  `frames` URL for `(tag, unit, period)`; **caller supplies the correctly-suffixed
  period** (`…Q1I` for `kind="instant"`, `…Q1` for `kind="duration"`) — the
  catalog `kind` drives the suffix so a flow is never requested as an instant.
- `parse_company_facts(payload) -> list[dict]` — pure: walk
  `facts[taxonomy][tag]["units"][unit][]` for the curated tags only, emitting one
  row per `{tag, uom, end, fy, fp, value, form, filed, accession}`; extension/
  non-curated tags ignored.
- `fetch_company_facts(cik, get=_http_get)` — GET `companyfacts/CIK##########.json`.
- `fetch_submissions(cik, get=_http_get)` — GET `submissions/CIK##########.json`
  for the `name`/`sic` and newest filing metadata seeding `companies`.
- `parse_bulk(zip_bytes, tags) -> list[dict]` *(optional `--bulk`)* — read
  `num.tsv` joined to `sub.tsv` inside the quarterly ZIP, filter to the curated
  tags, emit the same fact-row shape. **Skip `2009q1.zip`** (header-only
  placeholder).

## Schema (`sec_fundamentals/db.py`)

```sql
CREATE TABLE IF NOT EXISTS snapshots (   -- one row per fetch run (provenance)
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,         -- ISO-8601 UTC: when the run executed
    company_count INTEGER NOT NULL,      -- companies touched this run
    fact_count    INTEGER NOT NULL       -- fact rows upserted this run
);

CREATE TABLE IF NOT EXISTS companies (   -- dimension, upserted each run
    cik        INTEGER PRIMARY KEY,
    ticker     TEXT,                      -- from company_tickers.json; NULL if unmapped
    name       TEXT,                      -- newest entityName / sub.name seen
    sic        TEXT,
    first_seen TEXT,                      -- ISO capture of first time stored
    last_seen  TEXT                       -- ISO capture of most recent run touching it
);

CREATE TABLE IF NOT EXISTS facts (       -- panel fact table, upserted by key
    cik           INTEGER NOT NULL REFERENCES companies(cik),
    tag           TEXT    NOT NULL,       -- us-gaap tag, e.g. 'NetIncomeLoss'
    uom           TEXT,                   -- USD | shares | USD/shares
    period_end    TEXT    NOT NULL,       -- reporting period end, YYYY-MM-DD (ddate/end)
    fiscal_year   INTEGER,                -- fy
    fiscal_period TEXT,                   -- fp: FY|Q1|Q2|Q3
    value         REAL,
    form          TEXT    NOT NULL,       -- 10-K | 10-Q | 10-K/A ... (part of the key)
    filed         TEXT,                   -- filing date, YYYY-MM-DD (point-in-time)
    accession     TEXT,                   -- adsh, ties the fact to its filing
    PRIMARY KEY (cik, tag, period_end, form)
);
CREATE INDEX IF NOT EXISTS ix_facts_tag_period ON facts(tag, period_end);
CREATE INDEX IF NOT EXISTS ix_facts_cik        ON facts(cik);
```

Writers (shapes copied from FRED/CFTC):

- `upsert_companies(conn, rows, captured_at)` — refresh `ticker`/`name`/`sic`/
  `last_seen`, **preserve `first_seen`** (`ON CONFLICT(cik) DO UPDATE`, FRED
  `upsert_series` shape).
- `write_facts(conn, cik, rows) -> int` — `INSERT … ON CONFLICT(cik, tag,
  period_end, form) DO UPDATE SET value=excluded.value, filed=excluded.filed,
  accession=excluded.accession, …`; dedupe within the batch (last wins); revised
  values overwrite in place, keys never duplicated (FRED `write_observations` /
  CFTC `write_cot` shape). Returns rows written. **Ends with `conn.commit()`.**
- `write_snapshot(conn, captured_at, company_count, fact_count) -> id`.
- `prune(conn, keep_days, now_iso)` — FRED-style **single-table** delete of old
  `snapshots` only, with the same docstring warning: **do NOT cascade into
  `facts`** (the reported history is the store, not snapshot-scoped).

## Views (the derived signals — no pre-computed ratios exist upstream)

All `CREATE VIEW IF NOT EXISTS`, created with the schema. XBRL ships **no ratios**
— we derive them in SQL, degrading gracefully (LEFT JOINs → NULLs) when a
`--only` run omits a concept.

- **`v_latest_fundamentals`** — newest reported `value` per `(cik, tag)` (window
  `ROW_NUMBER() OVER (PARTITION BY cik, tag ORDER BY period_end DESC, filed
  DESC)`), joined to `companies` (`ticker`, `name`). The "current fundamentals"
  board.
- **`v_frame_cross_section`** — all companies' values for **one tag + one
  period** (`tag`, `period_end` filterable) joined to `companies` — the
  cross-sectional **screen** (the SQL analogue of a `frames` call).
- **`v_screener`** — **pivoted** key metrics per company (one row per CIK:
  revenue, net income, assets, equity, shares, EPS from the latest period), with
  **ratios derived in SQL** — e.g. net margin (`NetIncomeLoss / Revenues`), ROE
  (`NetIncomeLoss / StockholdersEquity`), debt-to-equity (`Liabilities /
  StockholdersEquity`). This is the row a bot ranks on, computed live from raw
  facts.
- **`v_revisions`** — same `(cik, tag, period_end)` appearing with **different
  `filed`/`accession`** (i.e. different `form`) → **restatements**, ordered by
  `filed`, with the value delta. This is the provenance signal `stocks` cannot
  give: which numbers were revised, when, and by how much.

## Orchestration & CLI (`sec_fundamentals/run.py`)

`run(db_path, only=None, exclude=None, add=None, tickers=None, periods=None,
bulk=False, keep_days=None, fetch_frame=fetch.fetch_frame,
fetch_facts=fetch.fetch_company_facts, fetch_map=fetch.fetch_ticker_map,
now_iso=None) -> (snapshot_id, company_count, fact_count)`:

1. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`.
2. Resolve concepts: `catalog.select_ids([c.tag for c in CATALOG], only, exclude,
   add=add)`; resolve the watchlist (`tickers` or `"all"`) to CIKs via
   `fetch_map()`.
3. `conn = connect(db_path); db.ensure_schema(conn)`.
4. **Primary path** — for each `(concept, period)`: `fetch_frame(...)` → for each
   filer row `upsert_companies` + `write_facts`. **Watchlist depth** — for each
   watchlist CIK: `fetch_facts(cik)` → filter to curated tags → write.
   **Skip-and-continue** on any per-item error, logging only `type(e).__name__`
   (never `str(e)`/`e.url` — the SEC URL is not secret but the discipline is
   uniform across screeners and future auth headers must never leak).
   `conn.rollback()` the failed item before continuing.
5. If **zero** items succeeded: still `write_snapshot(…, 0, 0)` and warn loudly
   (mirrors the other screeners' zero-count behaviour; does not raise).
6. `write_snapshot(now_iso, company_count, fact_count)`.
7. If `keep_days is not None`: `db.prune(conn, keep_days, now_iso)` (single-table).
8. Return `(snapshot_id, company_count, fact_count)`.

Fetchers + `now_iso` injected for deterministic, network-free tests (mirrors
every other screener's DI).

CLI (`main`, invoked via the dispatcher — `python main.py fundamentals`):

```
--db fundamentals.db
--only TAGS         comma-separated concept tags (default: catalog)
--exclude TAGS      comma-separated tags to skip
--add TAG           extra tag not in the catalog (repeatable)
--tickers SYMS      watchlist for companyfacts depth (default/"all" = frames only)
--period CYYYYYQ    calendar period(s) for the frames screen (repeatable)
--bulk              backfill from the quarterly ZIP instead of the APIs
--keep-days N       prune snapshot provenance older than N days (default: keep all)
```

## Defaults

- **No `--only/--exclude/--add`** → the full curated concept catalog.
- **No `--tickers`** → frames-only cross-sectional screen (no per-company depth).
- **No `--period`** → the most recent completed calendar quarter (instant tags
  get the `I` suffix from the catalog `kind`; duration tags do not).
- **No `--bulk`** → API path (frames + companyfacts), not the ZIP.
- **No `--keep-days`** → keep all provenance (the point of a history store).

## Effort / gotchas (call these out for the implementer)

- **CIK mapping is not 1:1** — reuse the `edgar` ticker map; store CIK as the key,
  ticker as a refreshable label; expect unmapped CIKs (`ticker = NULL`), ticker
  reuse, and multi-class tickers.
- **XBRL tag normalization** — different companies tag the same economic concept
  with different or **extension** tags (e.g. `Revenues` vs
  `RevenueFromContractWithCustomerExcludingAssessedTax`); v1 tracks a curated
  non-custom set and accepts coverage gaps rather than guessing mappings.
- **Point-in-time vs restated** — `(ddate/period_end, filed)` distinguishes the
  originally-reported value from a later restatement; the `form` in the PK keeps
  both. Do not collapse them.
- **No pre-computed ratios** — XBRL has none; every ratio is derived in a view
  (`v_screener`). Do not fabricate a `ratios` table.
- **Shared 10 req/s throttle + mandatory UA** — the whole SEC family shares one
  budget; a per-host throttle in `http_client` is the recommended home.
- **frames period `I` suffix** — instant vs duration; wrong suffix → empty frame.
  The catalog `kind` is the single source of truth for the suffix.
- **`2009q1.zip` is an empty placeholder** and the notes monthly files 404 by
  design past ~1 year — neither is an error.

## Testing (TDD, mirrors existing `tests/`)

Named to match the family: `test_sec_fundamentals_fetch.py`,
`test_sec_fundamentals_catalog.py`, `test_sec_fundamentals_db_schema.py`,
`test_sec_fundamentals_db_write.py`, `test_sec_fundamentals_db_views.py`,
`test_sec_fundamentals_run.py`. Fetchers and `now_iso` injected; no network.

- **fetch** — `cik_str` zero-pads to 10 digits; `parse_frame` /
  `parse_company_facts` coercion (numeric strings, missing → `None`, curated-tag
  filter, extension tags ignored); `fetch_frame` builds the **correct `I`/no-`I`
  period** from `kind`; backoff retries on `403/429/503` via a fake opener +
  injected `sleep` (like EDGAR); `2009q1` bulk placeholder yields no rows.
- **catalog** — `select_ids` only/exclude/add/dedupe/blank-drop; catalog
  integrity (unique tags, every `kind ∈ {instant, duration}`, `unit` valid per
  `group`).
- **db_schema** — `ensure_schema` idempotent; tables + all four views exist;
  re-run is a no-op.
- **db_write** — `write_facts` upsert keyed by `(cik, tag, period_end, form)`:
  a revised value **overwrites in place** (no duplicate key), a **different
  `form`** for the same period is a **new row** (feeds `v_revisions`);
  `upsert_companies` preserves `first_seen`, refreshes `ticker`/`name`.
- **db_views** — seed synthetic facts and assert `v_latest_fundamentals` picks
  the newest period, `v_frame_cross_section` returns all filers for one
  tag+period, `v_screener` derives net margin / ROE / D-E correctly (incl. NULL
  when a denominator concept is absent), `v_revisions` surfaces a restated period
  with the right delta.
- **run** — happy-path counts; **skip-and-continue** on a failing item (others
  still stored, failure warned); all-fail → `(0,0)` snapshot + loud warning;
  `--only/--exclude/--add`/`--tickers`/`--period` selection; second-run upsert
  (history grows, revised value overwrites); `keep_days` prunes `snapshots` but
  **not** `facts`.
- **secret-hygiene assertion** (as in `test_finra_shorts_run.py`): a per-item
  failure logs the **class name** (`assert "RuntimeError" in err`) but **never**
  the raised message text (`assert "boom" not in err`), guaranteeing no
  URL/header ever reaches stderr.
- `test_registry.py` — extend to assert `"fundamentals"` dispatches and appears
  in `--list`; existing screener paths unchanged.

Live smoke (manual, like the others): pull the curated concept catalog for one
recent period + a 2-ticker watchlist into a temp DB; assert non-zero `companies`,
non-zero `facts`, a populated `v_screener` row, and a sane
`v_frame_cross_section`.

## Non-goals (YAGNI)

- **13F / N-PORT holdings** — a different filing family (positions, not
  fundamentals); separate future screener.
- **The Financial Statement *and Notes* datasets** (`…_notes.zip` / `txt.tsv`
  note text) — bulkier deep-disclosure supplement; deferred.
- **Pre-2009 depth** — XBRL structured data starts 2009Q1; earlier filings are
  unstructured and out of scope.
- **Reproducing a vendor's exact computed ratios** — `v_screener` derives ratios
  transparently from raw facts; matching stockanalysis.com's numbers to the
  decimal is explicitly not a goal (the two are complements, not a reconciliation
  target).
- **Company extension / custom tags** — v1 tracks the curated non-custom
  (`us-gaap`/`ifrs-full`/`dei`/`srt`) concept set only.
- **Cross-screener joins** (`fundamentals` ↔ `stocks` ↔ `edgar`) — future query
  layer.

## Environment

**No credentials required** — no API key for either access mode. Nothing is added
to `.env.example`. The mandatory pieces are policy, not secrets:

- A descriptive **`User-Agent`** on every request
  (`agentic-trading-bot ninadk.dev@gmail.com`) — `403` without it — reused from
  `edgar_screener`.
- The SEC **≤10 requests/second** fair-access cap, shared across all SEC
  screeners (recommended single throttle in `http_client`).
