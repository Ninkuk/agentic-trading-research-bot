# Earnings Calendar Monitor — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source (forward):** [stockanalysis.com earnings calendar](https://stockanalysis.com/stocks/earnings-calendar/)
via its SvelteKit data endpoint
`https://stockanalysis.com/stocks/earnings-calendar/__data.json` — one
unauthenticated GET returns ~3 months of forward earnings dates for the whole US
market.
**Data source (official confirmation):** [SEC EDGAR submissions API](https://data.sec.gov/submissions/CIK##########.json)
— 8-K **Item 2.02** ("Results of Operations and Financial Condition"), no key,
descriptive UA + ≤10 req/s (reuses `edgar_screener`).
**Confidence:** 🔵 light-research (single-pass scan, not adversarially verified) —
confirm the payload field shapes and the Item-2.02 detection live at
implementation.

## Data-source policy note (read first)

The bot's rule for **new** screeners is **official sources only**, with one
approved exception the user already relies on: **stockanalysis.com** (a trusted
aggregator; see the project's standing "stockanalysis.com trusted exception"
note and `docs/stockanalysis_data_json_catalog.md`). This monitor needs that
exception because **there is no free, official, forward-looking earnings feed** —
the SEC only knows an earnings date *after* the company files. So the honest
design **pairs** the trusted aggregator (which gives forward dates) with an
**official detector** (EDGAR 8-K Item 2.02) that **confirms** each date once it
actually happens. Forward guess from stockanalysis; ground truth from EDGAR.

## Goal

Give the bot a **forward earnings calendar** for the names it holds or watches,
so it can manage risk **into a print**: size positions down, roll or close
options ahead of IV crush, and avoid being surprised by an overnight gap. The
value is entirely forward-looking — *when* does XYZ report, before or after the
bell — not the historical result.

This is an **event-date monitor**, the new forward-calendar kind introduced
alongside the FOMC Calendar Monitor
(`2026-07-03-fomc-calendar-monitor-design.md`). Both sit on the shared
`monitor_common` framework
(`2026-07-03-event-monitor-framework-design.md`) and both reuse existing repo
machinery — here, the `stock_analysis_screener` `devalue` decoder and the
`edgar_screener` SEC client.

## Shared framework (referenced, not redefined here)

Built on **`monitor_common`** (framework spec). This package does **not**
redefine the `events` / `snapshots` tables, the UPSERT-on
`(event_type, event_date, subtype)` write, the replace-forward-window, the shared
`v_upcoming` / `v_imminent` views, or the snapshot-only `prune`. It covers only
what is **earnings-specific**: the forward-feed decoder, the EDGAR confirmation
step, the event mapping, and four earnings views. `connect` (WAL) from
`screener_common`; `now_iso` injected so all today/upcoming logic is
deterministic.

## Source notes (light-research 2026-07-03 — confirm at implementation)

### Primary forward feed — stockanalysis.com (approved exception)

- **One GET, whole market, ~3 months forward.** The earnings-calendar route's
  `__data.json` returns roughly 75 forward days grouped into ~15 week-blocks
  (~620 KB; catalogued in `docs/stockanalysis_data_json_catalog.md`). The server
  **anchors to the current week and looks ~3 months forward regardless of query
  params**, so query strings are ignored — one poll per day is sufficient; be a
  polite client (real User-Agent, sane rate).
- **It is `devalue`-encoded, not plain JSON.** Decode with the **existing**
  helper `stock_analysis_screener.probe.page_data("/stocks/earnings-calendar/")`
  (the same flat-pool back-reference decoder the stocks screener already uses).
  **Do not write a second decoder.**
- **Shape** (per the catalog): a list of **day-blocks**, each
  `{date, day, count, beforeOpenCount, afterCloseCount, ...}` holding per-symbol
  rows with these fields:

  | field | meaning |
  |---|---|
  | `s` | ticker |
  | `n` | company name |
  | `t` | timing — `bmo` (before open) / `amc` (after close) |
  | `e` | EPS estimate |
  | `eg` | EPS growth % |
  | `r` | revenue estimate |
  | `rg` | revenue growth % |
  | `m` | market cap |

- **Undocumented + licensed.** Isolate the decode/normalize in one function that
  **fails loudly on schema drift** (missing `s`/`date`, or zero rows from a
  non-empty payload → raise, don't store an empty calendar). Treat the data as
  **internal-use only** — power the bot's decisions, **do not republish**.

### Official confirmation / fallback — SEC EDGAR 8-K Item 2.02

- **`data.sec.gov/submissions/CIK##########.json`** gives a company's recent
  filing history (form types + the 8-K **`items`** list). An **8-K carrying Item
  `2.02`** is the company reporting results — the official earnings signal. No
  key; **descriptive UA + ≤10 req/s**, and the SEC's IP+fingerprint 403 behavior
  is already handled by `edgar_screener`'s bounded-backoff client (reuse its
  opener / retry set — see the standing "EDGAR SEC rate-limit" note). Ticker→CIK
  resolves through `edgar_screener.fetch.fetch_ticker_map`.
- **Two jobs:** (a) **confirm** — once a watched name's Item-2.02 8-K posts on/near
  its scheduled date, flip that event `status` scheduled → `confirmed`/`released`
  and stamp `source='edgar'`; (b) **estimate** — when the forward feed lacks a
  name, project its **next** date from the issuer's historical quarterly Item-2.02
  cadence (dates are ~90 days apart).
- **It is backward-confirming, state that plainly.** EDGAR detects an earnings
  event **after** the filing, so it can never be the *forward* source — only the
  confirmer and the cadence-based estimator. The forward dates always originate
  from stockanalysis.

## Data shape: a *forward calendar* (the new monitor family)

Like the FOMC monitor, this is a **forward calendar**, not a backward snapshot:
future-dated `earnings` events that **firm up and shift** as report dates
approach, **UPSERTed in place** on each run. Default scope is a **watchlist**, so
it is dozens of rows, not the whole ~5k-name market. Past events are retained;
future events beyond the horizon are replaced so a cancelled/moved date
disappears (the framework's replace-forward-window).

## Module layout (fetch / db / run triad, like every screener)

```
earnings_calendar/
    __init__.py
    fetch.py   # forward-feed decode (via probe.page_data) + EDGAR Item-2.02 confirm
    db.py      # ensure_schema (delegates to monitor_common) + earnings views
    run.py     # decode -> upsert -> (optional) EDGAR confirm -> snapshot -> prune + CLI
```

Plus:
- Register `"earnings"` in `registry.py`
  (`from earnings_calendar.run import main as earnings_main`).
- **No credentials.** Nothing added to `.env.example`.

### `fetch.py`

- `fetch_forward(get=stock_analysis_screener.probe.page_data) -> list[dict]` —
  decode the earnings-calendar payload and flatten the day-blocks into normalized
  rows `{ticker, name, date, timing, eps_est, eps_growth, rev_est, rev_growth,
  mktcap}`. **The one fragile function**: fails loudly on schema drift. `get` is
  injected so tests run against a saved decoded fixture with no network.
- `timing_to_time(t) -> str | None` — `bmo` → `'before open'`, `amc` →
  `'after close'`, anything else → `None`.
- `confirm_via_edgar(tickers, scheduled_by_ticker, get=..., tmap=...) -> dict` —
  for each watched ticker: resolve CIK (`edgar_screener.fetch.fetch_ticker_map`),
  GET its `submissions` JSON with the **reused edgar client** (descriptive UA,
  bounded backoff), find any **8-K with `2.02` in its items** near the scheduled
  date → mark that `(ticker, date)` **confirmed**; expose the issuer's historical
  Item-2.02 dates for cadence estimation. Injected fetchers for testability.
- `SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"`,
  `EARNINGS_ROUTE = "/stocks/earnings-calendar/"`. Reuses
  `edgar_screener`'s `_UA` / `_RETRY_STATUS` — no new HTTP config.

### `run.py` — the event builder

`build_events(rows, now_iso) -> list[dict]` maps each normalized forward row to
an `events` row:

| column | value |
|---|---|
| `event_type` | `'earnings'` |
| `subtype` | ticker (`s`) |
| `event_date` | report date (`YYYY-MM-DD`) |
| `event_time` | `'before open'` / `'after close'` / `NULL` (from `t`) |
| `title` | company name (`n`) |
| `status` | `'scheduled'` (from stockanalysis) → `'confirmed'` (EDGAR) |
| `source` | `'stockanalysis'` → `'edgar'` on confirmation |
| `payload` | JSON `{eps_est, rev_est, mktcap, timing}` |

## Schema (owned by `monitor_common`; this package only adds views)

The `events` / `snapshots` DDL is defined in **`monitor_common`** (framework
spec: `events` PK `(event_type, event_date, subtype)` with `event_time`,
`title`, `status`, `source`, `payload`, `fetched_at`; `snapshots` provenance).
`db.ensure_schema(conn)` calls `monitor_common.ensure_schema(conn)` then creates
the four earnings views. Idempotent.

## Views (earnings-specific, on top of shared `v_upcoming` / `v_imminent`)

All filter `event_type = 'earnings'` and are parameterized on `:today` (and an
optional watchlist join — the module is scoped to watched names by default):

1. **`v_upcoming_earnings`** — all earnings events with `event_date >= :today`,
   ordered by date then market cap, optionally **joined to a watchlist** table so
   only held/watched tickers surface.
2. **`v_imminent_earnings`** — the next **N** days (`event_date` between `:today`
   and `:today + :n`) — the "reporting this week/next" watch list that drives
   position-sizing and IV-crush decisions.
3. **`v_this_week_earnings`** — events in the current Mon–Fri window — the classic
   "who prints this week" cut.
4. **`v_earnings_confirmed`** — events where `status IN ('confirmed','released')`
   and `source='edgar'` — the **EDGAR-verified** subset, so consumers can
   distinguish a firm print from an aggregator estimate.

## Orchestration (`run.py`) + CLI

`run(db_path, horizon_days=None, keep_days=None, only=None,
fetch_forward=fetch.fetch_forward, confirm=fetch.confirm_via_edgar,
now_iso=None) -> (snapshot_id, event_count)`:

1. `now_iso` injected; all today/horizon logic derives from it.
2. `rows = fetch_forward()`; if `only` (watchlist tickers) given, filter to it —
   **default scope is the watchlist, not the whole 5k+ market.** Drop rows beyond
   `--horizon-days` past `:today`.
3. `events = build_events(rows, now_iso)`.
4. `conn = connect(db_path); ensure_schema(conn)`;
   `monitor_common.upsert_events(conn, events)` (UPSERT on
   `(event_type, event_date, subtype)`), then the optional replace-forward-window.
5. **Optional EDGAR confirmation:** for the watched tickers, resolve their CIKs
   and call `confirm(...)`; flip matched events to `confirmed`/`released` with
   `source='edgar'`.
6. `monitor_common.write_snapshot(conn, now_iso, event_count, 'stockanalysis')`.
7. If `keep_days is not None`: `monitor_common.prune(conn, keep_days, now_iso)` —
   **snapshot provenance only; never future events.**
8. Return `(snapshot_id, event_count)`. Per-ticker EDGAR failures roll back that
   ticker's writes and continue, logging **only `type(e).__name__`** (never
   `str(e)` / the URL) — repo-wide secret-hygiene rule. Whole-payload decode
   drift aborts loudly.

**CLI** (`prog="earnings"`):
- `--db` (default `earnings.db`)
- `--horizon-days N` (cap how far forward to store)
- `--keep-days N` (prune snapshot provenance only)
- `--only TICKER [TICKER ...]` (restrict to these names; default: the bot's
  watchlist, **not** the full market)

## Defaults (approved)

- **Cadence:** one poll per day — the feed re-anchors to the current week each
  request, and daily is plenty for a forward calendar.
- **Scope:** **watchlist by default** (dozens of names). `--only` overrides;
  pulling the whole ~5k universe is possible but off by default (noise +
  respect for the source).
- **Horizon:** the feed's native ~3 months (~75 days); `--horizon-days` caps it
  tighter if wanted.
- **Confirmation:** EDGAR confirm runs only for the watched CIKs — a handful of
  ≤10 req/s calls, well within SEC fair-access.
- **Retention:** keep all events; `--keep-days` prunes only run-provenance
  snapshots, never the calendar.

## Testing (mirror `tests/`, inject fetch, pin `now_iso`)

- `test_earnings_fetch.py` — `fetch_forward` against a saved **decoded** fixture
  (day-blocks flattened, `timing` mapped, estimates carried); **drift guard**:
  non-empty payload yielding zero rows / missing `s` **raises**. `timing_to_time`
  mapping. `confirm_via_edgar` with an **injected** submissions fixture: an 8-K
  with Item `2.02` near the date confirms; one without does not; CIK-resolution
  miss is skipped, not fatal.
- `test_earnings_db_schema.py` — `ensure_schema` idempotent; shared `events` /
  `snapshots` tables + the four earnings views exist; re-run is a no-op.
- `test_earnings_db_write.py` — `build_events` mapping (subtype=ticker,
  event_time from timing, payload JSON); UPSERT updates a **shifted** report date
  in place (no duplicate); an EDGAR confirm flips `status`/`source`;
  replace-forward-window drops a moved-away future date while retaining past ones.
- `test_earnings_db_views.py` — with a **pinned `now_iso`**: `v_upcoming_earnings`
  date filter + watchlist join; `v_imminent_earnings` N-day window boundaries;
  `v_this_week_earnings` Mon–Fri cut; `v_earnings_confirmed` shows only
  EDGAR-verified rows.
- `test_earnings_run.py` — `run()` with **injected** `fetch_forward` + `confirm`
  and pinned `now_iso`: end-to-end upsert + snapshot counts; `--only` filters to
  the watchlist; a second run confirms a previously-scheduled event; `--keep-days`
  prunes snapshots only. **Secret-hygiene assertion**: an EDGAR fetch raising an
  exception whose message embeds a fake secret leaves it out of stderr/logs.
- `test_registry.py` — extend to assert `"earnings"` dispatches and `--list`
  includes it; existing routes unchanged.

## Non-goals (YAGNI)

- **Whisper numbers / crowd-sourced estimates** — only the aggregator's published
  consensus estimates (`e`/`r`) are stored.
- **Intraday / real-time confirmation** — the EDGAR confirm is a batch pass, not
  a live 8-K stream.
- **Non-US issuers** — the forward feed and the CIK join are US-market; foreign
  listings are out of scope.
- **Replacing the existing `stocks` screener** — that snapshots fundamentals;
  this monitors *dates*. They are complementary, not overlapping.
- **Republishing the licensed stockanalysis data** — internal decision support
  only.

## Environment

**No new variables.** stockanalysis.com needs no key (approved trusted source);
EDGAR needs only the descriptive User-Agent already configured in
`edgar_screener`. Nothing added to `.env.example`.
