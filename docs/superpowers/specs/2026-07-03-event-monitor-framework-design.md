# Event-Date Monitor Framework — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** cross-cutting — no single feed. Backbone is the
[FRED `releases/dates` endpoint](https://fred.stlouisfed.org/docs/api/fred/releases_dates.html)
(reuses the existing `FRED_API_KEY`); per-monitor sources are cited in the
individual specs listed below.
**Confidence:** 🔵 light-research (single-pass source scan, not adversarially
verified) — confirm endpoints at implementation.

## Goal

Introduce a **new kind of screener** to the family: the **event-date monitor**.
Every screener written so far stores the **past** — a universe of entities ×
metrics captured as-of some historical date. A monitor stores the **future**: an
ingested, forward-looking **calendar** of dated, market-moving events (economic
releases, FOMC decisions, market holidays, OPEX, earnings, Treasury auctions),
and flags the ones that are **imminent** so the bot can de-risk, size, or stand
aside *before* the event lands rather than reading its aftermath.

This is the umbrella spec. It **defines `monitor_common`** — the shared
schema, write semantics, views, prune, and `now_iso` discipline that every
monitor reuses (the analogue of `screener_common` for this new kind) — and it
**maps the monitor family**, cross-referencing the per-monitor specs that build
on it.

## Why a new kind (contrast with the existing screeners)

The seven existing screeners span three data shapes, all **backward-looking**:

- **cross-sectional** (`stocks`, `reddit`, `edgar`) — a wide snapshot of entity
  state at one captured moment.
- **time-series** (`fred`) — decades of dated *observations* per series.
- **full-universe dumps / panels** (`cftc`, `ftd`, `short_volume`) —
  `(entity, date)` facts that accumulate as history.

In every one, `date` points **backward**: the newest row is the freshest *past*.
A monitor inverts this. Its rows are **future-dated** — the useful row is the
*next* one, not the last one. The questions it answers are prospective ("is a
CPI print inside the next 3 sessions?", "is Friday a half-day?", "is the market
in an FOMC blackout right now?"), and its central operation is not "what
happened" but **"what is about to happen, and how soon."** That difference —
future-dated rows, imminence as the primary signal, dates that *firm up* or *get
cancelled* before they arrive — is enough structural divergence to warrant its
own shared module rather than bending `screener_common` around it.

## Data shape: **forward calendar**

A fourth data-shape classification joins the three above:

- A monitor ingests a **forward calendar** — a set of scheduled future events,
  each an immutable-ish `(event_type, event_date, subtype)` fact that agencies
  **revise before it occurs** (tentative → scheduled → confirmed) and
  occasionally **cancel**. The store must let a date *shift in place* and let a
  cancellation *disappear*, while retaining events once they pass. History is
  not snapshot-scoped; the calendar is upserted and the past is retained.

## `monitor_common.py` (this spec defines it; the monitors USE it)

A sibling to `screener_common.py`. It reuses `screener_common.connect` (WAL) and
supplies the canonical events store, write helpers, shared views, and prune.

### Canonical schema

```sql
CREATE TABLE events (
    event_type TEXT NOT NULL,   -- 'fomc_meeting','cpi_release','opex','earnings',...
    event_date TEXT NOT NULL,   -- YYYY-MM-DD
    event_time TEXT,            -- 'HH:MM' ET if known else NULL
    subtype    TEXT,            -- ticker / release_id / auction term — part of
                                --   the natural key (use '' not NULL so it's a stable PK)
    title      TEXT,
    status     TEXT,            -- 'tentative','scheduled','confirmed','released'
    source     TEXT NOT NULL,
    payload    TEXT,            -- optional JSON extras
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (event_type, event_date, subtype)
);
CREATE TABLE snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT,
    event_count INTEGER,
    source      TEXT
);
CREATE INDEX ix_events_date ON events(event_date);
CREATE INDEX ix_events_type ON events(event_type);
```

- **`subtype` is part of the primary key and must never be NULL.** SQLite treats
  every NULL as distinct, so a NULL `subtype` would break the natural key and let
  duplicate rows accumulate for a single event. Monitors with no natural subtype
  (e.g. an FOMC meeting) write the **empty string `''`**, giving a stable PK.
- **`status` is a lifecycle**, not a boolean: an event enters `tentative` or
  `scheduled`, is later `confirmed`, and after it passes may be marked
  `released`. The status column is what lets `tentative→confirmed` firm-ups be
  observed rather than silently overwritten.

### Write semantics

- **`upsert_events(conn, rows, fetched_at) -> int`** — `INSERT ... ON
  CONFLICT(event_type, event_date, subtype) DO UPDATE` refreshing `event_time`,
  `title`, `status`, `source`, `payload`, `fetched_at`. A date that **firms up**
  (tentative → confirmed) or that carries a newly-published intraday time updates
  **in place**; no duplicate row. Dedupes within the batch (last wins), mirroring
  `fred_screener.db.write_observations`.
- **`replace_forward_window(conn, event_type, today, rows, fetched_at) -> int`**
  — for a single `event_type`, **delete future rows** (`event_date >= :today`)
  and re-insert the freshly-fetched set. This is the **cancellation-aware** path:
  if a source stops listing a previously-scheduled future event, upsert alone
  would leave a stale row forever; the delete-forward-then-insert makes
  cancellations disappear. **Past events (`event_date < :today`) are never
  touched** — history is retained regardless. Monitors choose per `event_type`:
  upsert when sources only ever add/firm-up, replace-forward when sources can
  retract.
- **`write_snapshot(conn, captured_at, event_count, source) -> id`** — one
  per-run header (provenance + counts), same role as every screener's
  `snapshots`.
- Every writer ends with `conn.commit()` (repo rule).

### Shared views

Views are parameterised on **`:today`**, which callers bind from the **injected
`now_iso`** (see below) — never `date('now')`, so tests are deterministic.

- **`v_upcoming`** — `SELECT * FROM events WHERE event_date >= :today ORDER BY
  event_date, event_time`. The forward calendar.
- **`v_imminent`** — `event_date BETWEEN :today AND date(:today, '+N days')`,
  ordered. The near-term watch list; `N` is the horizon.

Per-monitor views (e.g. `v_imminent_high_impact`, `v_next_opex`,
`v_upcoming_auctions`) **layer on top** of these, joining a monitor's catalog for
impact/labels.

### Prune

- **`prune(conn, keep_days, now_iso) -> int`** — a **single-table** delete of old
  **`snapshots`** provenance rows only (plain `DELETE FROM snapshots WHERE
  captured_at < cutoff`, exactly like `fred_screener.db.prune`), **not** the
  cascade `prune` in `screener_common`. **It must NEVER prune future events** —
  the whole point of a monitor is the forward calendar. An optional `--drop-past`
  helper may trim *far-past* events (`event_date < date(:today, '-K days')`) to
  keep the table small, but this is opt-in and defaults off. Retention default:
  keep the calendar, prune only run headers.

### `now_iso` injection (critical for a calendar)

All "today" / "upcoming" / "imminent" logic derives from an **injected
`now_iso`**, never wall-clock. For backward-looking screeners `now_iso` mainly
timestamps rows; for a monitor it is **load-bearing** — it decides which events
are future, imminent, or past, and which future rows `replace_forward_window`
deletes. Every monitor's `run()` accepts `now_iso=None` and defaults it to
`datetime.now(timezone.utc).isoformat()`, and every view binds `:today =
date(now_iso)`. Tests pin `now_iso` to exercise imminence boundaries.

### Registry integration

Each monitor ships the standard package triad `fetch.py` / `db.py` / `run.py`
(argparse `main`) + optional `catalog.py`, imports its DB layer through
`monitor_common`, and registers its `run.main` in `registry.py` under a
dispatcher name — identical to how the screeners register. Monitors and
screeners share one dispatcher; the *kind* is an internal distinction.

### HTML-drift isolation

Sources without a machine-readable feed (NYSE/SIFMA holiday pages, FOMC pages,
the earnings feed) are parsed by a **single isolated parser function** per
monitor that **fails loudly on schema drift** — if the expected table/anchor is
missing or the row count collapses to zero, raise, don't silently write an empty
calendar. This is the monitor analogue of the FTD/short-volume "skip a malformed
line" discipline, escalated: an empty forward calendar is dangerous (it reads as
"nothing is coming"), so drift must surface as an error, not a quiet no-op.

## Key architectural finding: FRED `releases/dates` is the economic backbone

The single most important structural insight for this family:

> **FRED's `releases/dates` endpoint is a unified backbone for U.S.
> economic-release dates.** Reusing the **existing** `fred_screener` API key, one
> API returns the forward schedule for CPI, PPI, the Employment Situation
> (nonfarm payrolls / unemployment), GDP, Retail Sales, PCE, JOLTS, and dozens
> more — so **most econ releases need no dedicated source at all.**

The bot already authenticates to FRED. Instead of scraping a half-dozen agency
calendars (BLS, BEA, Census), one authenticated API covers the entire
economic-release calendar. That collapses what looked like the largest slice of
the monitor family into a **single, cheap, high-reliability monitor**
(`econ_calendar`).

The events that **do** need their own source — because FRED does not carry them —
are the ones this family builds bespoke monitors for:

- **FOMC** — meeting dates come from the Fed; the **blackout window** and
  **minutes-release** dates are *computed* from the meeting date. (Not on FRED as
  a release calendar.)
- **Market holidays + early closes, and OPEX / quad-witching** — holidays are
  HTML (NYSE/SIFMA); OPEX is *computed* from the third-Friday rule against the
  holiday set. (Not on FRED.)
- **Earnings** — a per-ticker forward feed (stockanalysis.com) confirmed against
  EDGAR filings. (Not on FRED.)

## The monitor family

**Dedicated monitors** own a source and normalise it into `events`.
**Calendar views** layer a `v_upcoming_*` view onto an existing *data* screener
whose source already carries a forward schedule — no new package, just a view.

| Event(s) | Official source | Machine-readable? | Dedicated monitor vs calendar-view | Confidence |
|---|---|---|---|---|
| Econ releases — CPI, PPI, Employment Situation, GDP, Retail Sales, PCE, JOLTS, … | FRED `releases/dates` (reuses `FRED_API_KEY`) | ✅ JSON API | **Dedicated** — `econ_calendar` | 🔵 |
| FOMC meetings; blackout & minutes (computed) | federalreserve.gov (monetarypolicy) | ⚠️ HTML | **Dedicated** — `fomc_calendar` | 🔵 |
| Market holidays, early closes (equity + bond) | NYSE / Nasdaq / SIFMA hours pages | ⚠️ HTML | **Dedicated** — `market_calendar` | 🔵 |
| OPEX / quad-witching | *computed* (3rd-Friday rule vs holidays) | 🧮 computed | **Dedicated** — `market_calendar` | 🔵 |
| Earnings dates | stockanalysis.com forward feed + EDGAR confirm | ⚠️ HTML / undocumented | **Dedicated** — `earnings_calendar` | 🟡 |
| Treasury auctions (bills/notes/bonds/TIPS) | TreasuryDirect / fiscaldata API | ✅ JSON API | **Calendar view** on the treasury screener | 🔵 |
| EIA WPSR (weekly petroleum), NG storage | EIA release schedule | ⚠️ HTML / fixed cadence | **Calendar view** on the EIA screener | 🔵 |
| USDA WASDE / NASS reports | usda.gov `.ics` calendar | ✅ ICS | **Calendar view** on the USDA screener | 🔵 |

Per-monitor specs:

- **[2026-07-03-econ-calendar-monitor-design.md](./2026-07-03-econ-calendar-monitor-design.md)**
  — the FRED-backbone economic-release monitor.
- **[2026-07-03-fomc-calendar-monitor-design.md](./2026-07-03-fomc-calendar-monitor-design.md)**
  — FOMC meetings + computed blackout/minutes.
- **[2026-07-03-market-calendar-monitor-design.md](./2026-07-03-market-calendar-monitor-design.md)**
  — holidays / early closes / OPEX / quad-witching.
- **[2026-07-03-earnings-calendar-monitor-design.md](./2026-07-03-earnings-calendar-monitor-design.md)**
  — forward earnings feed + EDGAR confirmation.
- **[2026-07-03-treasury-fiscaldata-screener-design.md](./2026-07-03-treasury-fiscaldata-screener-design.md)**
  — Treasury data screener; exposes `v_upcoming_auctions`.
- **[2026-07-03-eia-energy-screener-design.md](./2026-07-03-eia-energy-screener-design.md)**
  — EIA energy data screener; exposes a WPSR/NG-storage schedule view.
- **[2026-07-03-usda-wasde-screener-design.md](./2026-07-03-usda-wasde-screener-design.md)**
  — USDA WASDE/NASS screener; exposes a `.ics`-derived schedule view.

## Recommended build order (value × low-effort × reliability)

1. **`econ_calendar`** (econ-release monitor) — **highest value, lowest effort.**
   Reuses the existing FRED key and HTTP scaffolding; one JSON API covers most of
   the calendar; deterministic and reliable. Build first.
2. **`market_calendar`** (holidays / early closes / OPEX) — small and
   deterministic, but more importantly it is **shared infrastructure**: the
   holiday table is the second pillar everything else leans on (OPEX
   Friday→Thursday shifts, EIA/USDA holiday slips, "is this a trading day"
   helpers). Build second so later monitors can depend on it.
3. **`fomc_calendar`** — a small HTML parse of the meeting schedule; blackout and
   minutes dates are *computed*. Modest effort, **very high impact** (FOMC days
   dominate rate-sensitive positioning).
4. **Treasury auctions** — nearly free: the source is already a JSON API in the
   Treasury data screener, so this is a `v_upcoming_auctions` view, not a new
   package.
5. **`earnings_calendar`** — highest ongoing value per name but built **last
   among the dedicated monitors** because its source (stockanalysis.com forward
   feed) is **undocumented and drift-prone**, and it needs EDGAR
   cross-confirmation. Deferring it lets the isolated-parser + fail-loud
   machinery mature on the safer HTML monitors first.
6. **EIA / USDA schedule views** — calendar views on their respective data
   screeners; lowest urgency, added when those screeners land.

Rationale for the ordering: front-load the API-backed, deterministic monitors
(1–4) that carry the most signal for the least drift risk and establish the
shared holiday infrastructure; defer the HTML/undocumented earnings source (5)
until the framework's fail-loud parsing is proven; treat the calendar views (6)
as thin add-ons to data screeners built for other reasons.

## Non-goals (YAGNI)

- **A generic scheduler / cron.** Monitors *ingest* calendars; when to run them
  is the caller's concern.
- **Intraday tick-level timing.** `event_time` is a best-effort `HH:MM` ET;
  minute-accurate release timing is out of scope.
- **Merging monitors and screeners into one base class.** They share
  `connect`/`prune`-style helpers via `monitor_common`, nothing more — same
  decision as the screeners (shapes differ).
- **Cross-monitor joins** (e.g. earnings ∩ OPEX week). A future query layer.
- **Timezone gymnastics.** All event times are U.S. Eastern by convention;
  `now_iso` is UTC ISO-8601 for pruning consistency with the screeners.

## Environment

- **No new credentials.** `econ_calendar` reuses `FRED_API_KEY` (already in
  `.env` / `.env.example`); the HTML/computed monitors need no key. `.env.example`
  is unchanged by this framework spec.
- **Dependency-free.** `urllib` + stdlib only, via `http_client.make_opener` /
  `http_client.http_get`, descriptive UA
  `agentic-trading-bot ninadk.dev@gmail.com`, bounded backoff on the retryable
  statuses each source uses.
- **Secret hygiene (repo-wide).** Per-item failures log **only**
  `type(e).__name__` — never `str(e)` / `e.url` (a FRED HTTPError embeds the API
  key in its URL) — and API keys are never printed.
