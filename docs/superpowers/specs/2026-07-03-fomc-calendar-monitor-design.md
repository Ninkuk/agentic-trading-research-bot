# FOMC Calendar Monitor (Meetings / Blackout / Minutes) — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:** [Federal Reserve FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
— an **HTML page** (no ICS, no JSON, no API): meeting dates for the current and
next 1–2 years, tentative until the Fed confirms them. Statement/minutes
*release* pings come from the [Fed RSS feeds](https://www.federalreserve.gov/feeds/feeds.htm)
but those fire **after** a document posts, so they are confirmation-only, not
forward-looking.
**Confidence:** 🔵 light-research (single-pass scan, not adversarially verified) —
confirm the HTML structure and the blackout/minutes rules live at implementation.

## Goal

Turn the FOMC calendar into a **forward-looking macro-event feed** the trading
bot can plan around: when the next rate decision lands, when the Fed goes into
its **communication blackout** (so Fed-speak catalysts stop), when **minutes**
drop three weeks later, and which meetings carry a **Summary of Economic
Projections** ("dot plot") — the biggest macro-vol events of the quarter.

Unlike every existing screener (`stocks`, `reddit`, `edgar`, `fred`, `cftc`,
`ftd`, `short_volume`, `options`), which record what **already happened**, this
is the first of a new kind — an **event-date monitor**: a maintained calendar of
things that **will** happen, whose dates firm up and shift over time. It is a
sibling to the Earnings Calendar Monitor
(`2026-07-03-earnings-calendar-monitor-design.md`) and both sit on the shared
`monitor_common` framework defined in
`2026-07-03-event-monitor-framework-design.md`.

## Shared framework (referenced, not redefined here)

This package builds on **`monitor_common`** (see the framework spec). It does
**not** redefine the `events` / `snapshots` tables, the UPSERT-on
`(event_type, event_date, subtype)` write, the replace-forward-window delete, the
shared `v_upcoming` / `v_imminent` views, or the snapshot-only `prune`. This spec
covers only what is **FOMC-specific**: the HTML parser, the computed
derivations (minutes / blackout / SEP), the event-type vocabulary, and three
FOMC views. `connect` (WAL) comes from `screener_common`; `now_iso` is injected
everywhere so all "today / upcoming" logic is deterministic in tests.

## Source notes (light-research 2026-07-03 — confirm at implementation)

- **`fomccalendars.htm` is HTML, and that is the only forward source.** The Fed
  publishes no machine feed of *future* meeting dates. Meetings for the current
  year plus one or two years out appear on the page, marked **tentative** until
  confirmed (typically confirmed ~a year ahead). The parser must read the page
  and is therefore **fragile**: isolate it in one function and **fail loudly on
  schema drift** (see below) rather than silently emitting an empty calendar.
- **The RSS feeds are not forward-looking.** `feeds/press_monetary.xml` and the
  minutes feed only emit an item once a statement or minutes document is
  *published*. They cannot tell you a future date. Their *only* role here is to
  flip an already-stored event's `status` → `released` once the document posts —
  a **Phase 1.5** enrichment, not part of the core forward calendar.
- **Two-day meetings.** A regular FOMC meeting spans two days; the **decision +
  statement** land on **day 2 ~14:00 ET**, and (on meetings with a press
  conference) the **presser ~14:30 ET**. The page gives the day range; we store
  both the range and the decision day.
- **Tentative vs confirmed.** A meeting's `status` starts `tentative` and moves
  to `confirmed` when the Fed firms the date, then `released` after the
  statement posts. Because writes are UPSERTs keyed on
  `(event_type, event_date, subtype)`, a date that **shifts** while still
  tentative updates the row in place instead of duplicating it — see the subtype
  convention below, which keeps derived events pinned to their parent meeting.

## Computed derivations (we do NOT scrape these — we compute them)

Only the **meeting dates** are parsed. Everything else is derived from each
meeting's start/end date, so the calendar stays coherent even as dates shift:

- **Minutes release** = meeting **end date + 3 weeks (21 days)**. Emitted as a
  `fomc_minutes` event on that date.
- **SEP / dot plot** accompanies the roughly **quarterly** meetings
  (**March / June / September / December**). Those meetings get **`has_sep =
  true`** in their payload *and* a distinct **`fomc_sep`** event on the decision
  day, so the dot-plot dates are both queryable as their own events and visible
  as a flag on the meeting.
- **Communication blackout.** Begins the **second Saturday preceding** the
  meeting and ends the **day after** the meeting (midnight ET). Concretely:
  `blackout_start` = walk back from the meeting **start date** to the nearest
  preceding Saturday, then back one more week; `blackout_end` = meeting **end
  date + 1 day**. During this window FOMC members do not give speeches or
  interviews, so **Fed-speak catalysts stop** — a signal in its own right. Both
  bounds are stored (as `fomc_blackout_start` / `fomc_blackout_end` events, and
  redundantly in payload) so the boolean `v_in_blackout` helper is a cheap
  lookup.

## Data shape: a *forward calendar* (the new monitor family)

- The eight existing screeners are **backward** — cross-sectional snapshots,
  time-series, panels, or full-universe dumps of facts already true.
- `fomc_calendar` is a **forward calendar**: a small set of **future-dated
  events** (a handful of meetings × up to five derived events each ≈ dozens of
  rows) that are **re-derived every run** and **UPSERTed in place**. Past events
  are retained; future events beyond the parse horizon are replaced so a
  cancelled/rescheduled meeting disappears (the framework's optional
  replace-forward-window). History accumulates; it is not snapshot-scoped.

## Module layout (fetch / db / run triad, like every screener)

```
fomc_calendar/
    __init__.py
    fetch.py   # HTTP GET + the ISOLATED HTML parser (the only fragile code)
    db.py      # ensure_schema (delegates to monitor_common) + FOMC views
    run.py     # parse -> derive minutes/blackout/SEP -> upsert -> snapshot -> prune + CLI
```

Plus:
- Register `"fomc"` in `registry.py` (`from fomc_calendar.run import main as fomc_main`).
- **No credentials.** Nothing added to `.env.example`.

### `fetch.py`

- `parse_calendar(html) -> list[dict]` — **the one fragile function.** Extract
  each meeting as `{start_date, end_date, status, has_press_conference}` from the
  page's per-year blocks. It **fails loudly on schema drift**: if it parses zero
  meetings from non-empty HTML, or a row is missing a resolvable date, raise a
  clear `FomcCalendarParseError` instead of returning `[]` — a silent empty
  calendar is the dangerous failure mode here. Month/day text → `YYYY-MM-DD`
  via a small `_norm_date` helper; the tentative/confirmed marker → `status`.
- `fetch_calendar(get=_http_get) -> list[dict]` — GET the page, hand the body to
  `parse_calendar`. Text GET via `http_client.make_opener` + `http_client.http_get`
  with bounded backoff on the shared retry set; a descriptive
  `User-Agent: agentic-trading-bot ninadk.dev@gmail.com`.
- Pure derivations (network-free, unit-tested against fixed dates):
  `minutes_date(end_date)`, `blackout_window(start_date, end_date) -> (start, end)`,
  `is_sep_meeting(decision_date) -> bool` (month in {3,6,9,12}).
- `CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"`,
  `_RETRY_STATUS = frozenset({403, 429, 503})`.

### `run.py` — the event builder

`build_events(meetings, now_iso) -> list[dict]` expands each parsed meeting into
`events` rows:

| event_type | event_date | event_time (ET) | subtype | payload |
|---|---|---|---|---|
| `fomc_meeting` | decision day (day 2) | `14:00` | `''` | `{start, end, has_press_conference, has_sep}` |
| `fomc_sep` | decision day | `14:00` | *decision day* | `{}` (only on Mar/Jun/Sep/Dec) |
| `fomc_minutes` | end + 21d | `14:00` | *decision day* | `{}` |
| `fomc_blackout_start` | 2nd Sat before start | `NULL` | *decision day* | `{window_end}` |
| `fomc_blackout_end` | end + 1d | `NULL` | *decision day* | `{window_start}` |

**Subtype convention:** the meeting row uses `subtype = ''` (framework rule: `''`
not `NULL` when none); every **derived** event uses `subtype =` the parent
meeting's **decision date**, which pins minutes/SEP/blackout to their meeting and
keeps the UPSERT idempotent when a tentative date shifts. `status` starts
`tentative`, becomes `confirmed` when the parsed marker firms, `released` after
the (Phase 1.5) RSS flip. `source = 'federalreserve'`.

## Schema (owned by `monitor_common`; this package only adds views)

The `events` and `snapshots` DDL live in **`monitor_common`** — see the framework
spec for the authoritative definition (`events` PK `(event_type, event_date,
subtype)` with `event_time`, `title`, `status`, `source`, `payload`,
`fetched_at`; `snapshots` provenance with `id, captured_at, event_count,
source`). `db.ensure_schema(conn)` calls `monitor_common.ensure_schema(conn)`
then creates the three FOMC views below. Idempotent (`CREATE VIEW IF NOT
EXISTS`).

## Views (FOMC-specific, on top of the shared `v_upcoming` / `v_imminent`)

1. **`v_next_fomc`** — the single next `fomc_meeting` with `event_date >=
   :today`, carrying **`days_until`** (`julianday(event_date) - julianday(:today)`)
   and the **`has_sep`** flag (`json_extract(payload,'$.has_sep')`). The "when is
   the next decision, and is it a dot-plot one?" one-liner.
2. **`v_in_blackout`** — a **boolean helper other modules query**: is `:today`
   inside a communication-blackout window?
   `SELECT EXISTS(SELECT 1 FROM events WHERE event_type='fomc_blackout_start' AND
   event_date <= :today AND json_extract(payload,'$.window_end') >= :today)`.
   Lets any consumer gate Fed-speak-catalyst logic with one query.
3. **`v_upcoming_fomc_events`** — all FOMC event types with `event_date >=
   :today`, ordered by date, with a human `label` per type — the full forward
   agenda (meetings, SEP, minutes, blackout boundaries) in one list.

## Orchestration (`run.py`) + CLI

`run(db_path, horizon_days=None, keep_days=None, fetch_calendar=fetch.fetch_calendar,
now_iso=None) -> (snapshot_id, event_count)`:

1. `now_iso` injected (default UTC now); all today/horizon logic derives from it.
2. `meetings = fetch_calendar()` → `events = build_events(meetings, now_iso)`;
   optionally drop events beyond `--horizon-days` past `:today`.
3. `conn = connect(db_path); ensure_schema(conn)`.
4. `monitor_common.upsert_events(conn, events)` — UPSERT on
   `(event_type, event_date, subtype)`, then the optional
   replace-forward-window so a cancelled/rescheduled future meeting is dropped
   (past events retained).
5. `monitor_common.write_snapshot(conn, now_iso, len(events), 'federalreserve')`.
6. If `keep_days is not None`: `monitor_common.prune(conn, keep_days, now_iso)` —
   **snapshot provenance only; never future events.**
7. Return `(snapshot_id, event_count)`. Any per-meeting failure rolls back that
   meeting's writes and continues, logging **only `type(e).__name__`** (never
   `str(e)` / the URL) — repo-wide secret-hygiene rule. A `FomcCalendarParseError`
   (whole-page drift) aborts loudly — better no update than a wrong calendar.

**CLI** (`prog="fomc"`):
- `--db` (default `fomc.db`)
- `--horizon-days N` (cap how far forward to store; default: keep all parsed)
- `--keep-days N` (prune snapshot provenance only)

## Defaults (approved)

- **Cadence:** one poll per run is plenty — the calendar changes rarely (a
  confirmation or a rare reschedule). A weekly cron is ample.
- **Horizon:** store everything the page lists (~current + 1–2 years). `--horizon-days`
  is an optional cap, not a requirement.
- **Retention:** keep all events forever; `--keep-days` prunes only run-provenance
  snapshots, never the calendar.
- **Times:** decision `14:00` ET, presser `14:30` ET (a payload flag, not a
  separate event); minutes `14:00` ET; blackout boundaries have `event_time =
  NULL` (they are day-scoped). All ET, as published — no timezone math beyond the
  stored label.

## Testing (mirror `tests/`, inject fetch, pin `now_iso`)

- `test_fomc_fetch.py` — `parse_calendar` against a saved HTML fixture (right
  meeting count, dates, tentative/confirmed, press-conference flag); **drift
  guard**: non-empty HTML that parses zero meetings **raises**. Pure derivations:
  `minutes_date` (+21d), `blackout_window` (second-Saturday-before / end+1)
  across several seeded meeting dates, `is_sep_meeting` for the four quarter
  months and negatives for the others.
- `test_fomc_db_schema.py` — `ensure_schema` idempotent; the shared `events` /
  `snapshots` tables and the three FOMC views all exist; re-run is a no-op.
- `test_fomc_db_write.py` — `build_events` shape (five event types, subtype
  convention, `has_sep` only on quarter meetings); UPSERT updates a shifted
  tentative date **in place** (no duplicate); replace-forward-window drops a
  cancelled future meeting while retaining past ones.
- `test_fomc_db_views.py` — with a **pinned `now_iso`**: `v_next_fomc` picks the
  right next meeting + correct `days_until` + `has_sep`; `v_in_blackout` returns
  true only for a `:today` inside a seeded window and false just outside both
  bounds; `v_upcoming_fomc_events` ordering and horizon filter.
- `test_fomc_run.py` — `run()` with an **injected `fetch_calendar`** and pinned
  `now_iso`: end-to-end upsert + snapshot counts; a second run with one date
  firmed (tentative→confirmed) updates in place; `--keep-days` prunes snapshots
  only. **Secret-hygiene assertion**: a fetch raising an exception whose message
  contains a fake secret leaves that secret out of stderr/logs.
- `test_registry.py` — extend to assert `"fomc"` dispatches and `--list`
  includes it; existing routes unchanged.

## Non-goals (YAGNI)

- **Scraping minutes / statement text or the SEP tables themselves** — this is a
  *date* monitor; document contents belong to a future EDGAR/text screener.
- **Fed-speak (individual governor speeches) calendar** — a separate, noisier
  source; the blackout window already answers "can they speak right now?".
- **Live RSS `status → released` flips** — designed-for (Phase 1.5), not built in
  v1; the forward calendar stands alone without it.
- **Intraday timing precision / timezone conversion** — ET labels as published,
  no DST arithmetic.
- **Non-FOMC Fed events** (Beige Book, H.4.1, discount-rate minutes) — out of
  scope; addable as new `event_type`s later.

## Environment

**No new variables.** No API key, account, or token — a single public HTML GET
with the descriptive User-Agent already used across the project. Nothing added to
`.env.example`.
