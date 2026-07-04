# Follow-ups & Backlog

Deferred work captured while building out the screener/monitor roadmap
([ROADMAP.md](ROADMAP.md)). The roadmap itself is **complete** — everything here
is either a documented follow-up on a shipped screener, a live-verification task,
or an un-spec'd idea. Nothing here has an implementation plan yet.

**Priority key:** 🔴 high-leverage / low-ambiguity · 🟠 useful, some design ·
🔵 needs a spec + product decision first.

---

## 1. Deferred follow-ups on shipped screeners

These are intentional cuts recorded in the corresponding Built rows / plan
Self-Reviews. Each has a clear home and a known shape.

### 1a. 🔴 Shared ≤10 req/s SEC throttle in `http_client`
- **Why:** `edgar`, `ftd`, and `fundamentals` all hit `*.sec.gov`, and the SEC
  fair-access cap is **per-source, not per-screener** — running them back-to-back
  can exceed 10 req/s in aggregate and earn a 403.
- **What:** a small token-bucket rate limiter keyed on the SEC host, living in
  `http_client` (or `screener_common`), that every SEC fetcher pays into. The
  existing bounded-backoff absorbs the occasional 403 today, but a proactive
  throttle is the right fix now that there are three SEC screeners and
  `fundamentals` fans out per-entity.
- **Scope:** cross-cutting; touches `http_client.py` + the three SEC fetchers'
  `make_opener`/`http_get` call sites. No new data source. TDD: a fake clock +
  `sleep` recorder asserts the limiter spaces calls.
- **Source:** `fundamentals` plan (deferred non-goal); spec §"one shared throttle".

### 1b. 🟠 `fundamentals --bulk` quarterly-ZIP run-loop
- **Why:** `sec_fundamentals.fetch.parse_bulk` is **built and unit-tested**
  (`num.tsv ⋈ sub.tsv`, skips the empty `2009q1` placeholder), but the `--bulk`
  flag is only *accepted* — `run()` does not yet download the quarterly ZIPs and
  loop them into `write_facts`.
- **What:** wire the ZIP download + per-quarter loop into `run(bulk=True)`:
  enumerate `{YYYY}q{Q}.zip` from `--start`'s quarter to the latest published,
  fetch each (404 on unpublished future quarters → skip), `parse_bulk` →
  `write_facts`/`upsert_companies`. Reuse the existing SEC opener + backoff.
- **Scope:** `sec_fundamentals/run.py` + `fetch.py` (a `fetch_bulk_zip` helper).
  `parse_bulk` is done, so this is orchestration + tests only.
- **Source:** `fundamentals` plan Task 5 note + roadmap Built row.

### 1c. 🟠 Wider revision-lookback for `treasury` and `nyfed`
- **Why:** both use `since = max(stored date)` (inclusive), which only re-absorbs
  the **boundary day's** restatement. Fiscal agencies (DTS) and the NY Fed
  restate rows a few days back, so a naive floor can miss revisions — the same
  lesson learned on CFTC (see [[incremental-since-misses-revisions]]).
- **What:** floor at `max_date − N trailing days` (e.g. 7) for the daily/weekly
  domains, plus a `--full` re-ingest option, mirroring the CFTC revision-lookback
  design. Upsert-in-place already handles the overwrite; this only widens the
  fetch window.
- **Scope:** `treasury_screener/run.py`, `nyfed_screener/run.py` — small change to
  the `since` computation + a test that a restated prior-day row is re-absorbed.
- **Source:** `treasury` + `nyfed` plans (incremental-`since` notes).

### 1d. 🔵 `earnings` cadence-based date estimation (EDGAR job "b")
- **Why:** `earnings` currently does forward dates (stockanalysis) + EDGAR
  **confirmation** (job "a"). The spec's job "b" — *estimating* a name's next
  report date from the historical spacing of its 8-K Item-2.02 filings (~90 days
  apart) — was deferred.
- **What:** when the forward feed lacks a watched name, project its next date from
  the mean/median gap of its stored Item-2.02 dates; write it as a `scheduled`
  event with `source='edgar-estimate'` so consumers can distinguish it from an
  aggregator date and a confirmation.
- **Scope:** `earnings_calendar/fetch.py` (expose historical Item-2.02 dates from
  `confirm_via_edgar`) + `run.py` (estimate + write). Needs a small product call
  on how to label/rank an estimate vs a real forward date.
- **Source:** `earnings` spec §"two jobs (b) estimate"; plan deferred note.

### 1e. 🔵 USDA WASDE-native (OCE/ESMIS) balance-sheet ingestion
- **Why:** `usda` v1 sources what **NASS Quick Stats** exposes (production,
  stocks, use). The full WASDE **ending-stocks/use balance sheet** is distributed
  via USDA OCE/ESMIS downloadable files, **not** Quick Stats — so the
  stocks-to-use view is only as complete as Quick Stats' `TOTAL_USE` coverage.
- **What:** confirm the machine-readable WASDE data access (OCE/ESMIS release
  files), add a second fetch path + parser, and write the WASDE balance rows into
  `usda_obs` (or a sibling table) so `v_stocks_to_use` is WASDE-accurate.
- **Scope:** new fetch/parse path in `usda_screener/fetch.py`; possibly a new
  `metric`/`source` distinction. Needs live confirmation of the ESMIS format.
- **Source:** `usda` spec §B (WASDE balance sheets); plan confirm-then-wire note.

---

## 2. Live 🟡 endpoint / field verification

Five screeners shipped with **deliberately tolerant parsers** and 🟡-confidence
source details (routes, dataset slugs, field names, envelope keys). They are
tested against fixtures and are safe, but the real API slugs/fields should be
confirmed against the live services (needs API keys + a networked run), adjusting
each parser **and its fixture together** where reality differs. Drop any
catalog entry that 404s, with a note.

| Screener | Confirm | Needs |
|---|---|---|
| `ats` | `otcMarket` weekly dataset slug (`_DATASET`) + JSON field names | anon POST |
| `nyfed` | domain history paths + JSON envelope keys + field names | anon GET |
| `cboe_stats` | PCR market-stats CSV route + per-index CDN CSV routes/headers | anon GET |
| `eia` | v2 routes + facet ids per catalog series; bracket-param round-trip | `EIA_API_KEY` |
| `usda` | Quick Stats `short_desc`/`statisticcat_desc` per target; 50k-row cap | `NASS_API_KEY` |

Each screener's parser raises loudly on a header/shape change that yields zero
rows, so a silent-blank is not the failure mode — but a renamed field that still
parses to `None` would quietly drop data, which is what the live check catches.

**New keys added to `.env.example` this cycle:** `EIA_API_KEY`, `NASS_API_KEY`
(free registration; both are query params, never logged).

---

## 3. Idea 💡 backlog (no spec yet)

Un-spec'd future screeners. Each would start with a design spec (brainstorming →
`docs/superpowers/specs/`) before entering the build loop, and must fit the
**official-primary-sources-only** policy (the one approved exception,
stockanalysis.com, is already used).

- **OCC cleared options/futures volume** — cross-market cleared volume/OI from
  `theocc.com` (noted in the `cboe_stats` spec as a natural third fact table in
  that package). Complements `cboe_stats` (venue-agnostic cleared totals).
- **SEC 13F institutional holdings** — quarterly institutional positions
  (`data.sec.gov` / EDGAR 13F filings). A different filing family from
  `fundamentals`; a panel keyed on `(cik/manager, cusip, quarter)`.
- **SEC N-PORT / N-MFP fund holdings** — mutual-fund / money-market-fund holdings
  disclosures.
- **Reg SHO threshold securities list** — SEC/exchange threshold-list membership
  (persistent fails); complements `ftd` + `short_interest` for the squeeze signal.
- **FINRA TRACE corporate/agency bond data** — bond trade reporting; credit-tape
  read to sit alongside the equity/venue screeners.

---

## Suggested order if picking this up

1. **1a (SEC throttle)** — highest leverage, no new data source, protects three
   existing screeners.
2. **1b (`fundamentals --bulk`)** — unlocks full-universe backfill; `parse_bulk`
   is already done, so it's orchestration-only.
3. **1c (revision-lookback)** — small, correctness-improving, two screeners.
4. **§2 live verification** — do opportunistically whenever keys + network are
   available; cheap and de-risks the 🟡 screeners.
5. **1d / 1e** — need a product decision (labeling estimates; ESMIS format).
6. **§3 ideas** — each needs a spec first; pick by signal value.
