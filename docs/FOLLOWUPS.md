# Follow-ups & Backlog

Deferred work captured while building out the screener/monitor roadmap
([ROADMAP.md](ROADMAP.md)). The roadmap itself is **complete**.

**Status (this cycle):** the four low-ambiguity code follow-ups — **1a, 1b, 1c,
1d** — are now **built and tested** (§1). The five §2 live-verification screeners
were probed against their real endpoints: **`ats` was fixed**, several
`nyfed`/`cboe_stats` drifts were found and turned into precise fix specs, and the
two key-gated screeners (`eia`, `usda`) remain un-probed (no API keys in this
env). **1e** was researched — a machine-readable WASDE source was located (§1e).
§3 remains an un-spec'd idea backlog with a suggested build order.

**Priority key:** 🔴 high-leverage / low-ambiguity · 🟠 useful, some design ·
🔵 needs a spec + product decision first. ✅ done · 🟡 partially done / precise
follow-up recorded.

---

## 1. Deferred follow-ups on shipped screeners

### 1a. ✅ Shared ≤10 req/s SEC throttle in `http_client` — DONE
- **Shipped:** host-keyed token-bucket `RateLimiter` in `http_client.py` + one
  process-wide `SEC_RATE_LIMITER` (9 req/s, headroom under the 10 cap). All SEC
  openers (`edgar`, `ftd`, `fundamentals`) acquire under a single
  `SEC_HOST_KEY='sec.gov'` — **not** the literal hostname, which would split
  `www.sec.gov`/`data.sec.gov` into separate buckets and permit ~2× the intended
  aggregate rate. `make_opener` + `ftd._bytes_opener` gained `limiter`/
  `limiter_key` kwargs and pay the throttle before each request (retries
  included). TDD: fake-clock spacing, key independence, refill, shared-bucket
  wiring.

### 1b. ✅ `fundamentals --bulk` quarterly-ZIP run-loop — DONE
- **Shipped:** `fetch.bulk_zip_url` + `fetch.fetch_bulk` (bytes opener paying the
  shared SEC bucket; 404 → `None` so unpublished quarters skip). `run._ingest_bulk`
  enumerates `{YYYY}q{Q}` from `--start` (default: latest completed quarter)
  through the current quarter, `parse_bulk` → group by CIK → `upsert_companies` +
  `write_facts`. Company name/sic come from the ZIP's `sub.tsv` (labeled even with
  an empty ticker map). `--bulk` is now an alternate primary path (frames/
  companyfacts skipped). CLI `--start` added.

### 1c. ✅ Wider revision-lookback for `treasury` and `nyfed` — DONE
- **Shipped:** both floor the incremental fetch at `max_date − 7 days` (upsert-in-
  place absorbs the restatement) and add `--full` to re-pull from `--start` (or
  full history), ignoring the lookback. Event datasets and first-ever pulls are
  unchanged. TDD: a restated within-window prior-day row is re-absorbed; `--full`
  re-pulls full history.

### 1d. ✅ `earnings` cadence-based date estimation (EDGAR job "b") — DONE
- **Shipped:** `fetch.item_202_history` factors the per-ticker submissions lookup
  out of `confirm_via_edgar` (which reuses it). `fetch.estimate_next_report`
  projects the next date from the **median** inter-filing gap of stored 8-K Item
  2.02 dates, rolled forward past today (a stale-but-regular filer still gets a
  future date); median resists 8-K/A (tiny gap) and missed-quarter (double gap)
  outliers; needs ≥3 dates. `run.py` estimates only watched names **absent** from
  the forward feed (disjoint from the confirm set → no double EDGAR fetch), honors
  `--horizon-days`, and writes them `status='scheduled'` `source='edgar-estimate'`
  — distinct from `'stockanalysis'` (forward) and `'edgar'` (confirmation).

### 1e. 🔵 USDA WASDE-native balance-sheet ingestion — RESEARCHED, ready to build
- **Finding (changes the approach):** the WASDE ending-stocks/use balance sheet
  **is** available as a stable, machine-readable **OCE CSV** — no ESMIS file
  scraping needed. Two official routes, updated the day after each release:
  - Per-release: `https://www.usda.gov/sites/default/files/documents/oce-wasde-report-data-{YYYY}-{MM}.csv`
  - Consolidated history (2010–present), linked from the OCE "Historical WASDE
    Report Data" page.
- **Schema (tidy/long format, confirm exact column names on a networked run):**
  one row per `(Commodity, Region, Attribute, MarketYear)` with a projection/
  estimate flag, `Value`, and `Unit`. `Region` ∈ {World, United States};
  `Attribute` ∈ {Beginning Stocks, Production, Imports, Supply, Domestic Use/Feed,
  Exports, **Ending Stocks**, …}. Stocks-to-use is derivable directly
  (`Ending Stocks / Total Use`).
- **Recommended design:** add `usda_screener/fetch.py::fetch_wasde_csv(year,
  month)` + a tidy-CSV parser; enumerate releases like the `fundamentals --bulk`
  loop; write rows into `usda_obs` with `source='wasde'` and a `metric` derived
  from `Attribute` (e.g. `ending_stocks`, `total_use`) so `v_stocks_to_use`
  becomes WASDE-accurate instead of only as complete as Quick Stats' `TOTAL_USE`.
  Fits the official-primary-sources policy directly (OCE, no aggregator).
- **Remaining before build:** one networked run to confirm the exact CSV header
  names + the `Attribute` vocabulary, then a small `metric`/`source` mapping
  decision. The USDA host is slow — stream/allow a long timeout.

---

## 2. Live 🟡 endpoint / field verification — PROBED

The five §2 screeners were probed against their live services (read-only, project
UA). Results below; each parser still raises loudly on a zero-row shape change, so
the risk being checked is a **renamed field that parses to `None` and silently
drops data**.

| Screener | Result |
|---|---|
| `ats` | ✅ **Fixed.** Slug `otcMarket/weeklySummary` + body confirmed. Parser read `ATSName` (does **not** exist live → `ats_name` always `None`); now reads `marketParticipantName`. Two design calls remain (below). |
| `nyfed` | 🟡 `reference_rates` **confirmed**; `repo`/`rrp`/`soma` have real drifts (below). |
| `cboe_stats` | 🟡 4 VIX/VVIX routes **confirmed**; the **PCR route is broken** (below). |
| `eia` | ⛔ **Blocked** — needs `EIA_API_KEY` (unset in this env). |
| `usda` | ⛔ **Blocked** — needs `NASS_API_KEY` (unset in this env). |

### 2a. `ats` — remaining design calls (not silent-drop bugs)
- **OTC vs ATS scope:** the week-only `compareFilters` also returns non-ATS
  `OTC_*` `summaryTypeCode` rows (for wk 2026-06-08: ~4.3k `ATS_*`, ~0.9k `OTC_*`).
  Decide whether the "ATS dark-pool" screener should filter to `summaryTypeCode`
  starting `ATS_`, or intentionally keep both venue families.
- **Null `MPID` semantics:** blank `MPID` currently maps to the
  `NON_ATS_DEMINIMIS` sentinel, but in live data null `MPID` marks **symbol-level
  aggregate roll-ups** (`ATS_W_SMBL`, firm rows w/o MPID), not de-minimis venues
  — collapsing them all to one sentinel mislabels aggregates and can collide on
  the PK. Revisit alongside the scope decision.

### 2b. `nyfed` — precise fixes (evidence from live probe, base `markets.newyorkfed.org/api`)
- 🔴 **`repo` broken path.** `/rp/repo/all/results/search.json` returns **HTTP
  400** (∉ retry set → `http_get` raises → repo never ingests). Live path is
  **`/rp/results/search.json`** (200; returns both repo + reverse ops, so the
  parser must filter by operation type — confirm the type field/values live).
- 🟠 **`repo`/`rrp` rate + submitted fields.** `award_rate` and (RRP)
  `total_submitted` are **absent at the record top level** → always `None`. Rate
  detail is nested: repo under `details[]`
  (`percentWeightedAverageRate`/`percentHighRate`/…), RRP under `propositions[]`.
  Populating them means reaching into the nested arrays.
- 🟠 **`soma` wide-format drop.** `/soma/summary.json` returns **one row per
  `asOfDate` with security types as columns** (`mbs, cmbs, tips, frn, notesbonds,
  bills, agencies, total`). `securityType`/`parValue` don't exist; the parser
  survives only via fallbacks (`security_type='total'`, `par_value=r['total']`),
  so **only the daily total is captured and the per-security breakdown is silently
  dropped**. Fixing means melting wide→long (one row per security type) — a small
  schema/parser change to `(as_of_date, security_type)`.
- `primary_dealer` (disabled, phase-2): `/pd/get/all/timeseries.json` 400s (`all`
  invalid) and live PD field names are **lowercase** (`keyid`, `seriesbreak`,
  `asof`) vs the parser's camelCase. Already flagged; fix when enabling.

### 2c. `cboe_stats` — PCR route broken
- 🔴 **PCR feed dead.** The hardcoded
  `cdn.cboe.com/api/global/us_indices/daily_prices/put_call_ratio.csv` returns
  **403** (file absent; the same host+UA serves every `*_History.csv` at 200), so
  `_get_csv` swallows it and the PCR table never populates. No working combined
  put/call-ratio CSV route was found (legacy `www.cboe.com/publish/…/*pc.csv`
  paths now return the SPA HTML shell). **Needs the correct current Cboe route**
  (and the assumed `DATE,TOTAL_PCR,EQUITY_PCR,INDEX_PCR,TOTAL_VOLUME` combined
  schema re-confirmed against it) **or the PCR feed removed**. The 4 VIX/VVIX CDN
  routes + `_norm_date` (MM/DD/YYYY) + the VVIX single-series fallback are all
  confirmed correct — no change.

**Env note:** `EIA_API_KEY` and `NASS_API_KEY` are present in `.env.example` but
unset locally; set them (free registration) to unblock the `eia`/`usda` probes.

---

## 3. Idea 💡 backlog (no spec yet)

Un-spec'd future screeners. Each starts with a design spec (brainstorming →
`docs/superpowers/specs/`) before the build loop, and must fit the
**official-primary-sources-only** policy (the one approved exception,
stockanalysis.com, is already used).

- **Reg SHO threshold securities list** — SEC/exchange threshold-list membership
  (persistent fails). Complements `ftd` + `short_interest` for the squeeze signal.
- **SEC 13F institutional holdings** — quarterly institutional positions
  (`data.sec.gov` / EDGAR 13F). Panel keyed on `(cik/manager, cusip, quarter)`.
- **OCC cleared options/futures volume** — venue-agnostic cleared volume/OI from
  `theocc.com`; complements `cboe_stats`.
- **SEC N-PORT / N-MFP fund holdings** — mutual-fund / money-market-fund holdings.
- **FINRA TRACE corporate/agency bond data** — credit-tape read alongside the
  equity/venue screeners.

**Recommended order (signal value × feasibility, all official-source):**
1. **Reg SHO threshold list** — small, fully specifiable now, and directly
   completes the squeeze-signal trio with `ftd`/`short_interest`. Reuses the SEC
   scaffolding (UA + shared throttle from 1a).
2. **13F holdings** — high signal, reuses `data.sec.gov` + the throttle; the main
   work is the 13F XML/INFOTABLE parser and the panel schema.
3. **OCC cleared volume** — natural `cboe_stats` sibling; do after the `cboe_stats`
   PCR route (§2c) is resolved so the options package is coherent.
4. **N-PORT/N-MFP**, **TRACE** — larger parsers, lower marginal signal; schedule
   last.

---

## Suggested order if picking this up
1. **§2c / §2b fixes** — `cboe_stats` PCR route + `nyfed` `repo` path are the two
   🔴 silent/hard failures currently costing live data; cheap once the route/path
   is confirmed.
2. **1e (WASDE CSV)** — one networked run to confirm the CSV header, then wire the
   second fetch path; unlocks a WASDE-accurate stocks-to-use view.
3. **`eia`/`usda` §2 probes** — do once the API keys are set.
4. **§3 ideas** — start with the Reg SHO threshold list (spec first).
