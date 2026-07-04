# Follow-ups & Backlog

Deferred work captured while building out the screener/monitor roadmap
([ROADMAP.md](ROADMAP.md)). The roadmap itself is **complete**.

**Status:** §1 (1a–1e) is **fully built and tested**. §2 live-verification is
**complete** — every screener was probed against its real endpoint; drifts were
fixed and verified live. §3 remains an un-spec'd idea backlog (prioritized).
Only a few intentionally-deferred sub-items remain (each noted inline).

**Priority key:** ✅ done · 🟠 small deferred sub-item · 💡 idea (needs a spec).

---

## 1. Deferred follow-ups on shipped screeners — ALL DONE ✅

### 1a. ✅ Shared ≤10 req/s SEC throttle in `http_client`
Host-keyed token-bucket `RateLimiter` + one process-wide `SEC_RATE_LIMITER`
(9 req/s). All SEC openers (`edgar`, `ftd`, `fundamentals`) acquire under a single
`SEC_HOST_KEY='sec.gov'` (not the literal host, which would split www/data and
double the rate). TDD: fake-clock spacing, key independence, refill, wiring.

### 1b. ✅ `fundamentals --bulk` quarterly-ZIP run-loop
`fetch_bulk`/`bulk_zip_url` (bytes opener on the shared SEC bucket; 404→skip) +
`run._ingest_bulk` enumerating `{YYYY}q{Q}` from `--start` through the current
quarter → `parse_bulk` → grouped upsert. CLI `--start`.

### 1c. ✅ Wider revision-lookback for `treasury` and `nyfed`
Both floor the incremental fetch at `max_date − 7 days` + a `--full` re-pull.
TDD: a restated within-window prior-day row is re-absorbed.

### 1d. ✅ `earnings` cadence-based EDGAR date estimation (job "b")
`item_202_history` + `estimate_next_report` (median inter-filing gap, rolled
forward past today). Watched names absent from the feed get a `scheduled`
`edgar-estimate` event, honoring `--horizon-days`.

### 1e. ✅ USDA WASDE balance-sheet ingestion
The machine-readable OCE CSV (`oce-wasde-report-data-{YYYY}-{MM}.csv`) supplies
the ending-stocks/use balance sheet Quick Stats structurally can't (see §2).
`usda_screener/wasde.py` (tolerant, fail-loud tidy-CSV parser) + `wasde_obs`
sibling table + `v_wasde_stocks_to_use` (`unit` is in the PK — a grain's U.S.
line appears in both the U.S.-domestic bushels table and the world-table metric-
tons row; STU falls back to domestic_use+exports where there's no "Use, Total").
`run_wasde` walks back to the newest published release; `--wasde` CLI.
**Verified end-to-end against the real Dec-2025 CSV:** 42 commodities, 3149 obs;
US STU Corn 0.125, Wheat 0.439, Sorghum 0.101. (Live HTTP fetch not exercised —
the USDA file host was unreachable from the build env; URL builder + 404 handling
are unit-tested. Confirm the live fetch on any run from a reachable network.)

---

## 2. Live endpoint / field verification — COMPLETE ✅

All five screeners were probed against their live services (read-only, project
UA / keys). Every parser now matches live reality.

| Screener | Result |
|---|---|
| `ats` | ✅ **Fixed.** `marketParticipantName` (was always-null `ATSName`); ingest only granular `ATS_W_SMBL_FIRM` rows. Live: 7104 rows, 0 null-MPID, 31/31 venues named. |
| `nyfed` | ✅ **Fixed.** `repo` 400→`/rp/results/search.json` (filter by `operationType`); `rrp`/`repo` `total_submitted`+`award_rate` from the results feed / `details[]`; `soma` melted wide→long. Live: repo 26 + rrp 13 ops with rates; soma across all 9 security types. |
| `cboe_stats` | ✅ **Fixed.** PCR feed disabled by default (Cboe discontinued the free daily P/C CSV; not on FRED either). 4 VIX/VVIX CDN routes confirmed. |
| `eia` | ✅ **Confirmed** — all 7 series, routes, facets, bracket-param round-trip, field names match live. No change. |
| `usda` | ✅ **Fixed.** Dropped the 3 `TOTAL_USE` targets (NASS has no `statisticcat='USE'`; total use → WASDE, 1e). 6 targets confirmed live. |

### Deferred §2 sub-items (intentional, low-severity)
- 🟠 **`nyfed` `award_rate` / rate nesting.** `award_rate` is derived from the
  dominant `details[]` leg. The per-security detail rows (each leg's
  submitted/accepted/rate) are not stored individually — only the operation
  total + a representative rate. Add a `repo_op_details` child table if the
  per-leg breakdown is ever needed.
- 🟠 **`nyfed` `primary_dealer`** (phase-2, disabled): `/pd/get/all/...` 400s and
  live field names are lowercase (`keyid`/`seriesbreak`/`asof`). Fix when enabling.
- 🟠 **`cboe_stats` PCR** stays code-complete but off; wire a paid Cboe DataShop
  source and `--only PCR` to re-enable, or delete the feed.
- 🟠 **`usda` quarterly-stocks vintage.** Quick Stats `STOCKS` returns quarterly
  grain-stock levels; `parse_response` maps each to its year and the writer
  keeps last-wins per (commodity, metric, year) — so `ENDING_STOCKS` is a
  quarterly value, not the marketing-year ending stock. This is the imprecision
  WASDE (1e) supersedes; prefer `v_wasde_stocks_to_use` for a true balance sheet.
  A future refinement could filter Quick Stats to a canonical `reference_period`.

---

## 3. Idea 💡 backlog (no spec yet) — deferred by choice

Un-spec'd future screeners. Each starts with a design spec (brainstorming →
`docs/superpowers/specs/`) before the build loop, and must fit the
**official-primary-sources-only** policy (the one approved exception,
stockanalysis.com, is already used).

**Recommended build order (signal × feasibility, all official-source):**
1. **Reg SHO threshold securities list** — small, fully specifiable now; completes
   the squeeze-signal trio with `ftd`/`short_interest`. Reuses the SEC
   scaffolding + shared throttle (1a).
2. **SEC 13F institutional holdings** — high signal; reuses `data.sec.gov` + the
   throttle. Main work: the 13F INFOTABLE XML parser + a `(manager, cusip,
   quarter)` panel.
3. **OCC cleared options/futures volume** — venue-agnostic cleared totals from
   `theocc.com`; natural `cboe_stats` sibling (do after the PCR source question).
4. **SEC N-PORT / N-MFP fund holdings**, **FINRA TRACE bond data** — larger
   parsers, lower marginal signal; schedule last.

---

## Env note
`.env` needs `FRED_API_KEY`, `EIA_API_KEY`, `NASS_API_KEY` (all free; query
params, never logged). The WASDE feed (1e) needs no key. Runs read keys from the
environment — export from `.env` before invoking (e.g. `usda`/`eia`).
