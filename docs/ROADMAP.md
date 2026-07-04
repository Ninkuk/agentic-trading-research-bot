# Screener & Monitor Roadmap

Single index of every data screener and event-date monitor in the bot: what's
built, what's designed, and what's next. This is the parent tracker — update the
**Status** column as work progresses.

**Source of truth for "Built"** is `registry.py` (a screener ships only once it's
registered in `REGISTRY`). Specs live in `docs/superpowers/specs/`, implementation
plans in `docs/superpowers/plans/`.

## Status legend

| Status | Meaning |
|---|---|
| ✅ Built | Registered in `registry.py`, tested, in use |
| 📐 Planned | Spec **and** implementation plan written; not yet built |
| 📝 Spec'd | Design spec written; no plan yet |
| 💡 Idea | Mentioned as a future add; no spec |

**Confidence** (for un-built items) — how verified the data source is:
🟢 endpoints live-checked · 🟡 located, confirm at build · 🔵 light-research, confirm at build.

## Architecture (every screener follows this)

`fetch.py` (network + pure parse) → `db.py` (SQLite schema + writes + views + prune)
→ `run.py` (incremental orchestration + argparse CLI), registered in `registry.py`,
sharing `screener_common.connect` (WAL) and `http_client` bounded-backoff. Event-date
**monitors** add a shared `monitor_common.py` (now built — landed with `econ_calendar`)
and a forward-looking `events` table —
see [event-monitor-framework](superpowers/specs/2026-07-03-event-monitor-framework-design.md).

Data-source policy: **official primary sources only** for new screeners, with one
approved exception — **stockanalysis.com** (already trusted/used). The existing
`reddit` (ApeWisdom) and `stocks` (stockanalysis.com) screeners stay as-is.

---

## Built ✅

| Dispatcher | Screener | Signal | Spec | Plan |
|---|---|---|---|---|
| `stocks` | StockAnalysis fundamentals | Equity fundamentals snapshot | — | — |
| `reddit` | ApeWisdom social sentiment | Retail/social mention velocity | [spec](superpowers/specs/2026-07-02-reddit-screener-design.md) | [plan](superpowers/plans/2026-07-02-reddit-screener.md) |
| `edgar` | SEC EDGAR daily-index filings | Insider (Form 4), 8-K, 13D/G, S-1/424B, 10-K/Q | [spec](superpowers/specs/2026-07-02-edgar-screener-design.md) | [plan](superpowers/plans/2026-07-02-edgar-screener.md) |
| `fred` | FRED macro time series | Macro indicators | [spec](superpowers/specs/2026-07-02-fred-screener-design.md) | [plan](superpowers/plans/2026-07-02-fred-screener.md) |
| `cftc` (`--family`) | CFTC COT — Legacy + Disaggregated + TFF | Futures positioning / COT index; +managed-money (disagg) & leveraged-fund (TFF) nets | [spec](superpowers/specs/2026-07-03-cftc-screener-design.md) · [disagg/tff](superpowers/specs/2026-07-03-cot-disaggregated-tff-screener-design.md) | [plan](superpowers/plans/2026-07-03-cftc-screener.md) · [disagg/tff](superpowers/plans/2026-07-03-cot-disaggregated-tff-screener.md) |
| `ftd` | SEC Fails-to-Deliver | CNS settlement fails | [spec](superpowers/specs/2026-07-03-ftd-screener-design.md) | [plan](superpowers/plans/2026-07-03-ftd-screener.md) |
| `short_volume` | FINRA daily short-sale volume | Daily shorting pressure | [spec](superpowers/specs/2026-07-03-finra-short-volume-screener-design.md) | [plan](superpowers/plans/2026-07-03-finra-short-volume-screener.md) |
| `short_interest` | FINRA Equity Short Interest | Settled short position / days-to-cover / squeeze | [spec](superpowers/specs/2026-07-03-finra-short-interest-screener-design.md) | [plan](superpowers/plans/2026-07-03-finra-short-interest-screener.md) |
| `options` | CBOE per-contract options | Per-ticker IV / greeks / OI / Vol-OI | [spec](superpowers/specs/2026-07-03-cboe-options-screener-design.md) | [plan](superpowers/plans/2026-07-03-cboe-options-screener.md) |
| `econ_calendar` | FRED economic-release calendar (**first event-date monitor**) | Forward CPI/PPI/jobs/GDP/retail/PCE/JOLTS release dates | [spec](superpowers/specs/2026-07-03-econ-calendar-monitor-design.md) · [framework](superpowers/specs/2026-07-03-event-monitor-framework-design.md) | [plan](superpowers/plans/2026-07-03-econ-calendar-monitor.md) |
| `market_calendar` | Market holidays / early closes / OPEX (**shared trading-day helpers**) | No-trade days, half-days, monthly OPEX / quad-witching; `is_trading_day`/`next_trading_day`/`next_early_close` | [spec](superpowers/specs/2026-07-03-market-calendar-monitor-design.md) | [plan](superpowers/plans/2026-07-03-market-calendar-monitor.md) |
| `fundamentals` | SEC XBRL fundamentals (primary-source panel) | Auditable revenue/income/assets/equity/EPS + derived margin/ROE/D-E + restatements | [spec](superpowers/specs/2026-07-03-sec-fundamentals-screener-design.md) | [plan](superpowers/plans/2026-07-03-sec-fundamentals-screener.md) |
| `fomc` | FOMC meetings / blackout / minutes / SEP | Rate-decision + computed blackout windows (`v_in_blackout`), minutes (+21d), dot-plot meetings | [spec](superpowers/specs/2026-07-03-fomc-calendar-monitor-design.md) | [plan](superpowers/plans/2026-07-03-fomc-calendar-monitor.md) |
| `treasury` | U.S. Treasury Fiscal Data (liquidity/supply) | TGA cash swings, debt-to-penny, avg rates, 2s10s curve/inversion, **auction calendar** (`v_upcoming_auctions`) + bid-to-cover demand | [spec](superpowers/specs/2026-07-03-treasury-fiscaldata-screener-design.md) | [plan](superpowers/plans/2026-07-03-treasury-fiscaldata-screener.md) |
| `earnings` | Forward earnings calendar (stockanalysis + EDGAR confirm) | When each watched name reports (before/after bell); EDGAR 8-K Item 2.02 confirms (`v_earnings_confirmed`) | [spec](superpowers/specs/2026-07-03-earnings-calendar-monitor-design.md) | [plan](superpowers/plans/2026-07-03-earnings-calendar-monitor.md) |
| `ats` | FINRA OTC/ATS dark-pool volume (weekly per-venue panel) | Which dark pools trade a name + off-exchange concentration; `v_top_dark_pools` / `v_latest_off_exchange` | [spec](superpowers/specs/2026-07-03-finra-ats-dark-pool-screener-design.md) | [plan](superpowers/plans/2026-07-03-finra-ats-dark-pool-screener.md) |
| `nyfed` | NY Fed Markets data (funding/liquidity) | SOFR & SOFR-IORB spread, ON-RRP take-up trend, SOMA QT runoff; `v_sofr_latest`/`v_rrp_trend`/`v_soma_runoff` | [spec](superpowers/specs/2026-07-03-nyfed-markets-screener-design.md) | [plan](superpowers/plans/2026-07-03-nyfed-markets-screener.md) |
| `cboe_stats` | CBOE market-wide put/call + VIX sentiment | Put/call extremes (contrarian), VIX term structure/backwardation; `v_pcr_extremes`/`v_vix_term_structure`/`v_latest_sentiment` | [spec](superpowers/specs/2026-07-03-cboe-market-stats-screener-design.md) | [plan](superpowers/plans/2026-07-03-cboe-market-stats-screener.md) |

Cross-cutting: [CFTC revision lookback](superpowers/specs/2026-07-03-cftc-revision-lookback-design.md) ([plan](superpowers/plans/2026-07-03-cftc-revision-lookback.md)) · [stockanalysis __data.json catalog](stockanalysis_data_json_catalog.md).

## Planned 📐

_Nothing currently in this state — the last two planned screeners (`options`, `cftc --family`) are now Built. Next candidates carry a spec but no plan yet; see below._

---

## Spec'd — data screeners 📝

New official sources (confirm endpoints at build):

| Conf | Dispatcher | Screener | Signal | Spec |
|---|---|---|---|---|
| 🟡 | `eia` | EIA energy inventories | Crude/gasoline/natgas builds & draws | [spec](superpowers/specs/2026-07-03-eia-energy-screener-design.md) |
| 🟡 | `usda` | USDA WASDE / NASS | Crop supply/demand, stocks-to-use | [spec](superpowers/specs/2026-07-03-usda-wasde-screener-design.md) |

## Spec'd — event-date monitors 📝

_All three spec'd event-date monitors (`market_calendar`, `fomc`, `earnings`) are now **Built** on the shared [event-monitor-framework](superpowers/specs/2026-07-03-event-monitor-framework-design.md) (`monitor_common`). Nothing pending in this state._

---

## Recommended build order

Ranked by signal × low effort × non-overlap (reuse of existing pipelines called out):

1. ~~**`cftc --family` (Disaggregated/TFF)**~~ — ✅ **Built** (see Built table). Cloned the existing CFTC Socrata pipeline. [plan](superpowers/plans/2026-07-03-cot-disaggregated-tff-screener.md)
2. ~~**`short_interest`**~~ — ✅ **Built** (see Built table). Cloned the `short_volume` CDN pattern; adds squeeze/days-to-cover. [plan](superpowers/plans/2026-07-03-finra-short-interest-screener.md)
3. ~~**`econ_calendar`**~~ — ✅ **Built** (see Built table). First event-date monitor; established the shared `monitor_common` framework (events table, upsert/replace-forward, imminence views, snapshot-only prune) that the remaining monitors reuse. [plan](superpowers/plans/2026-07-03-econ-calendar-monitor.md)
4. ~~**`market_calendar`**~~ — ✅ **Built** (see Built table). Small, deterministic; seeded NYSE/SIFMA holidays + pure-computed OPEX/quad-witching. Added the shared trading-day helpers (`is_trading_day`/`next_trading_day`/`next_early_close`) other monitors and screeners reuse. [plan](superpowers/plans/2026-07-03-market-calendar-monitor.md)
5. ~~**`fundamentals`**~~ — ✅ **Built** (see Built table). Official XBRL fundamentals panel; reuses EDGAR CIK/UA handling + FRED-style upsert/prune; ratios derived in SQL views. **Follow-ups deferred:** a shared ≤10 req/s SEC throttle in `http_client` (across `edgar`/`ftd`/`fundamentals`), and the `--bulk` quarterly-ZIP run-loop (`parse_bulk` is built + tested; the flag is accepted but the ZIP download loop is not yet wired into `run`). [plan](superpowers/plans/2026-07-03-sec-fundamentals-screener.md)
6. ~~**`fomc`**~~ — ✅ **Built** (see Built table). Small isolated HTML parse (meeting dates only) + pure-computed minutes/blackout/SEP on `monitor_common`; exposes `v_in_blackout` boolean helper other modules gate Fed-speak logic on. Phase-1.5 RSS `status→released` flip deferred (spec Non-goal). [plan](superpowers/plans/2026-07-03-fomc-calendar-monitor.md)
7. ~~**`treasury` auctions**~~ — ✅ **Built** (see Built table). Clean key-free FiscalData JSON (paged) + one XML par-curve branch; 6 datasets, ELT liquidity/supply views. Auction calendar ships as `v_upcoming_auctions` (the event-monitor framework reads it — no separate monitor). Wider revision-lookback deferred as a follow-up. [plan](superpowers/plans/2026-07-03-treasury-fiscaldata-screener.md)
8. ~~**`earnings`**~~ — ✅ **Built** (see Built table). stockanalysis forward feed (reuses the `probe` devalue decoder) + EDGAR 8-K Item-2.02 confirmation on `monitor_common`. Cadence-based *estimation* (projecting a next date from historical Item-2.02 spacing) deferred as a follow-up. [plan](superpowers/plans/2026-07-03-earnings-calendar-monitor.md)

**✅ The ranked build order (items 1–8) is complete.** Working through the lower-priority / specialized tail: `ats` ✅ Built, `nyfed` ✅ Built, `cboe_stats` ✅ Built; remaining (each has a spec, no plan yet): `eia`, `usda` — see the Spec'd — data screeners table above.

## Idea 💡 (no spec)

- OCC cleared options/futures volume (noted in `cboe_stats` spec).
- SEC 13F institutional holdings, N-PORT/N-MFP fund holdings, Reg SHO threshold list.
- FINRA TRACE corporate/agency bond data.
