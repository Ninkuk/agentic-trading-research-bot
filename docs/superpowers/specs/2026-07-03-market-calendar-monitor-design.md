# Market Calendar Monitor (Holidays / Early Closes / OPEX) — Design

**Date:** 2026-07-03
**Status:** Approved (design), pending implementation plan
**Data source:**
[NYSE hours & calendars](https://www.nyse.com/markets/hours-calendars) (HTML),
the Nasdaq holiday page (equivalent HTML),
[SIFMA holiday schedule](https://www.sifma.org/resources/guides-playbooks/holiday-schedule)
(HTML, bond market), plus **OPEX / quad-witching computed in pure Python** from
the third-Friday rule against the holiday set. No API, no key.
**Confidence:** 🔵 light-research (single-pass source scan, not adversarially
verified) — confirm the seed dates against the official pages at implementation.

## Goal

Ingest the **U.S. market schedule** — equity and bond **holidays**, **early
closes** (half-days), and the **monthly OPEX / quarterly quad-witching**
expirations — into the shared `events` table, so the bot knows which sessions are
**closed, shortened, or expiration-driven** *ahead of time*.

This is a monitor of the new event-date kind (see
[2026-07-03-event-monitor-framework-design.md](./2026-07-03-event-monitor-framework-design.md)).
It is deliberately built **second in the family's build order** because it is the
**second pillar of shared infrastructure**: the holiday table is a dependency for
much of the rest of the system. Other monitors and screeners reuse it —
OPEX shifts Friday→Thursday around holidays, EIA and USDA release dates **slip**
when a federal holiday intervenes, and any "is the market open on date D" /
"what's the next trading day" question routes through here. So beyond producing
signals, this monitor **exposes clean trading-day helpers** other modules call.

Package `market_calendar`, dispatcher name `market_calendar`. Uses
`monitor_common` for schema, write helpers, shared views, prune, and `now_iso`.

## Source notes

- **NYSE holidays + early closes** —
  `https://www.nyse.com/markets/hours-calendars`. **HTML only — no CSV / JSON /
  ICS.** Half-days close **13:00 ET** (options **13:15 ET**). Published **~2–3
  years ahead**, so a seed table stays valid for a long horizon.
- **Nasdaq holiday page** — an equivalent HTML page; the equity holiday set
  matches NYSE (used as a cross-check, not a second source of truth).
- **SIFMA bond-market recommended holidays + early closes** —
  `https://www.sifma.org/resources/guides-playbooks/holiday-schedule` (HTML).
  **The bond calendar differs from equities**: the bond market observes
  **Columbus Day and Veterans Day** (equities do **not**), and has its own
  recommended early closes. Example **2026 bond early closes** (14:00 ET): **Apr
  3, May 22, Jul 2, Nov 27, Dec 24, Dec 31**. This divergence is exactly why bond
  vs equity is tracked as distinct `event_type`s.
- **OPEX / quad-witching** — **computed, not fetched.** Monthly equity/index
  option expiration is the **3rd Friday** of each month; **quad-witching** is the
  3rd Friday of **Mar / Jun / Sep / Dec** (stock options, index options, stock
  futures, index futures all expire). When that Friday is an exchange holiday, the
  expiration **shifts to the preceding Thursday** — fully deterministic **once the
  holiday set is known**. CBOE only publishes a **PDF**
  (`cdn.cboe.com/resources/options/...`); **prefer computing** over parsing a PDF.

> The seed dates above are from a single-pass read of the official pages (🔵) —
> re-confirm against NYSE/SIFMA at implementation before shipping the constant.

## Design: a **computed monitor with a small seeded/parsed input**

Unlike the API monitors (`econ_calendar`) that fetch a live feed each run, this
monitor is **largely computed**:

- **Holidays / early closes are small, deterministic, and published years
  ahead.** So **v1 seeds a table of known holidays and early closes** — hardcoded
  from the official NYSE / Nasdaq / SIFMA pages and cited in a `catalog.py`
  constant — refreshed by a **thin, optional HTML parser** that keeps the seed
  current without depending on a live fetch every run.
- **OPEX / quad-witching are pure-Python computation** from the third-Friday rule
  against that holiday set — no source at all.

This is the opposite balance from `econ_calendar`: there, the API is the source
and code is thin; here, **code is the source** and the small HTML/seed input just
supplies the holiday anchors. The thin HTML parser is **isolated and fails loudly
on schema drift** (framework rule) — an empty holiday parse must raise, never
silently blank the calendar (a monitor that reports "no holidays coming" is
dangerous).

## Data shape: forward calendar

Standard monitor shape. `events` rows this monitor writes:

| `event_type` | meaning | `event_time` | `subtype` |
|---|---|---|---|
| `market_holiday` | equity market fully closed | NULL | `''` |
| `early_close` | equity half-day | `'13:00'` (options `'13:15'`) | `''` |
| `bond_holiday` | bond market closed (SIFMA) | NULL | `''` |
| `bond_early_close` | bond half-day (SIFMA) | `'14:00'` | `''` |
| `opex` | monthly 3rd-Friday expiration | `'16:00'` | `''` |
| `quad_witching` | quarterly quad-witch | `'16:00'` | `''` |

- `subtype` is `''` throughout (no natural sub-key), keeping the
  `(event_type, event_date, '')` primary key stable.
- `status` = `'scheduled'` (holidays/OPEX are deterministic; no tentative
  lifecycle here).
- `title` — human label (`'Independence Day'`, `'June Quad Witching'`).
- `source` — `'nyse'` / `'sifma'` / `'computed'` per row.
- `event_time` populated for early closes and OPEX/quad-witching.

## Module layout

```
market_calendar/
    __init__.py
    catalog.py  # seed constants: known equity+bond holidays / early closes (cited from NYSE/SIFMA)
    fetch.py    # thin OPTIONAL HTML parser (isolated, fails loudly) to refresh the seed
    db.py       # ensure_schema (via monitor_common) + calendar views + trading-day helpers
    run.py      # seed + compute OPEX/quad-witching into events; argparse main
```

- Register `"market_calendar"` in `registry.py` (import `run.main as
  market_calendar_main`).
- `.env.example` unchanged — **no credentials.**

### `catalog.py` — seed constants

Hardcoded, cited holiday and early-close dates for equities (NYSE/Nasdaq) and
bonds (SIFMA), covering the published ~2–3-year horizon. A code comment cites the
source page and the date the constant was transcribed, so a future reader knows
when to re-confirm. Example structure:

```python
EQUITY_HOLIDAYS = {  # from nyse.com/markets/hours-calendars, transcribed 2026-07-03
    "2026-01-01": "New Year's Day",
    ...
}
EQUITY_EARLY_CLOSES = {"2026-11-27": "13:00", "2026-12-24": "13:00", ...}
BOND_HOLIDAYS = {...}        # SIFMA — includes Columbus Day, Veterans Day
BOND_EARLY_CLOSES = {        # SIFMA — 14:00 ET
    "2026-04-03": "14:00", "2026-05-22": "14:00", "2026-07-02": "14:00",
    "2026-11-27": "14:00", "2026-12-24": "14:00", "2026-12-31": "14:00",
}
```

### `fetch.py` — thin, optional HTML parser

- `parse_nyse_calendar(html) -> dict[date -> label/kind]` and
  `parse_sifma_calendar(html) -> ...` — **isolated parser functions** that
  extract the holiday/early-close table. **Fail loudly on drift**: if the target
  table/anchor is missing or the parsed count is zero, raise — never return an
  empty set that would blank the calendar.
- Used **optionally** (behind a `--refresh` flag) to update the seed; the default
  run trusts the seed constant. This keeps runs deterministic and network-free
  while giving a path to refresh without editing code.

### `run.py` — OPEX / quad-witching computation

Pure functions, no I/O:

- `third_friday(year, month) -> date`.
- `opex_dates(year, holidays) -> list[(date, kind)]` — the 3rd Friday of each
  month; mark Mar/Jun/Sep/Dec as `quad_witching`, others `opex`; **shift to the
  preceding Thursday** if the 3rd Friday is in `holidays`.
- Computed for `--years` forward from the injected `now_iso`.

### `db.py` — views + trading-day helpers

`ensure_schema` calls `monitor_common.ensure_schema(conn)` then creates views
layered on `v_upcoming` / `v_imminent`, all binding `:today` from the injected
`now_iso`:

- **`v_upcoming_closures`** — upcoming `market_holiday` + `early_close` (and bond
  variants), `event_date >= :today` ordered. "What's closed/short next."
- **`v_next_opex`** — the next `opex`/`quad_witching` on or after `:today`.
- **`v_early_closes`** — upcoming half-days (equity + bond) with `event_time`.
- **`v_is_trading_day(:d)`** — the shared helper: **given a date, is the equity
  market open** (not a weekend, not in `market_holiday`). Exposed as a view /
  small helper (`is_trading_day(conn, d)`, `next_trading_day(conn, d)`,
  `next_early_close(conn, d)`) that **other modules import** — this is the clean
  trading-day API the rest of the system reuses (OPEX shift logic, EIA/USDA
  holiday slips).

## Run / CLI

`run(db_path, horizon_days=None, keep_days=None, years=None, html_fetch=None,
     now_iso=None) -> (snapshot_id, event_count)`:

1. `now_iso = now_iso or datetime.now(timezone.utc).isoformat()`; `today =
   date(now_iso)`.
2. `conn = monitor_common.connect(db_path); ensure_schema(conn)`.
3. Seed holidays/early closes from `catalog.py` (optionally refreshed via the
   thin parser if `--refresh`), and **compute** `opex_dates` for `--years`
   forward.
4. Write via **`replace_forward_window`** per `event_type` (delete future rows of
   that type from `:today`, re-insert) so a corrected/removed holiday or a
   recomputed OPEX set **replaces cleanly** and stale future rows disappear; past
   events retained.
5. `write_snapshot(now_iso, event_count, source='market_calendar')`; then
   `prune(conn, keep_days, now_iso)` if given (snapshots only — **never** future
   events).
6. Return `(snapshot_id, event_count)`.

`now_iso` injectable; the optional HTML fetch injectable — a normal run is
network-free and fully deterministic.

**CLI** (`prog="market_calendar"`):
- `--db` (default `market_calendar.db`)
- `--horizon-days N` (imminence window for views; default 7)
- `--keep-days N` (prune snapshot provenance only)
- `--years N` (how many years of OPEX / quad-witching to compute forward;
  default 2)
- `--refresh` (optional: run the thin HTML parser to refresh the seed)

## Defaults (approved)

- **OPEX horizon:** `--years 2` computed forward (cheap, deterministic).
- **Imminence:** `--horizon-days 7` for the view band.
- **Retention:** keep the full forward calendar and past events; `--keep-days`
  prunes only run-provenance snapshots.
- **Seed source of truth:** the `catalog.py` constant (equities + bonds); the
  HTML parser is opt-in refresh, not a per-run dependency.

## Signal

- **Holidays** → no-trade days (skip scheduling, avoid stale-quote traps).
- **Early closes** → half-days carry **thin afternoon liquidity** and compressed
  ranges — size down, expect gappy fills.
- **OPEX** → monthly expiration brings **gamma / pinning** effects and **elevated
  volume**; the bot can anticipate pin-to-strike drift and volume spikes.
- **Quad-witching** → typically the **largest-volume sessions** of the quarter
  (four expirations at once) — outsized liquidity and volatility to plan around.

## Testing (mirror the monitor conventions)

- `test_market_calendar_fetch.py` — `parse_nyse_calendar` / `parse_sifma_calendar`
  extract the expected dates from an HTML fixture and **raise on drift** (missing
  table / zero rows). **Secret-hygiene assertion** (no key here, but the
  per-item error-logging path still asserts `type(e).__name__` only).
- `test_market_calendar_compute.py` — `third_friday` correctness; `opex_dates`
  tags Mar/Jun/Sep/Dec as `quad_witching`; **Friday→Thursday shift** when the 3rd
  Friday is a seeded holiday (e.g. a Good-Friday-adjacent case).
- `test_market_calendar_db_schema.py` — `ensure_schema` idempotent; `events` +
  `snapshots` + the calendar views/helpers exist.
- `test_market_calendar_db_write.py` — `replace_forward_window` deletes only
  future rows of the given type and re-inserts (a removed holiday disappears; past
  rows retained), with a **pinned `now_iso`**; `is_trading_day` /
  `next_trading_day` return correct results across a seeded holiday and a weekend.
- `test_market_calendar_run.py` — `run()` with **pinned `now_iso`** and injected
  (or seeded) input: OPEX/quad-witching computed for `--years`, holidays/early
  closes written, bond vs equity kept distinct, `keep_days` prunes snapshots but
  **not** future events.
- `test_registry.py` — extend to assert `"market_calendar"` dispatches.

## Non-goals (YAGNI)

- **Non-U.S. exchange calendars** (LSE, TSE, etc.) — U.S. equity + bond only.
- **Parsing the CBOE expiration PDF** — OPEX is computed; the PDF is not a
  dependency.
- **Intraday session micro-structure** (LULD halts, auction times) beyond the
  open/half-day/close distinction.
- **Settlement / T+1 clearing calendars** — a separate concern from the trading
  calendar.
- **A live per-run holiday fetch as the default** — the seed constant is the
  source of truth; `--refresh` is the opt-in updater.

## Environment

- **No credentials.** Pure HTML (opt-in) + pure computation.
- Dependency-free (`urllib` + stdlib) via `http_client.make_opener` /
  `http_client.http_get` for the optional refresh; UA
  `agentic-trading-bot ninadk.dev@gmail.com`; bounded backoff on the retryable
  statuses (Cloudflare/CDN pages can 403/429/503, same discipline as the FINRA
  screener).
- **Secret hygiene:** per-item errors log only `type(e).__name__`; writers end
  with `conn.commit()`.
