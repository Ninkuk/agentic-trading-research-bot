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
**monitors** add a shared `monitor_common.py` and a forward-looking `events` table —
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

Cross-cutting: [CFTC revision lookback](superpowers/specs/2026-07-03-cftc-revision-lookback-design.md) ([plan](superpowers/plans/2026-07-03-cftc-revision-lookback.md)) · [stockanalysis __data.json catalog](stockanalysis_data_json_catalog.md).

## Planned 📐

_Nothing currently in this state — the last two planned screeners (`options`, `cftc --family`) are now Built. Next candidates carry a spec but no plan yet; see below._

---

## Spec'd — data screeners 📝

Deepen publishers already wired in (reuse existing pipelines):

| Conf | Dispatcher | Screener | Signal | Spec |
|---|---|---|---|---|
| 🟢 | `ats` | FINRA OTC/ATS dark-pool volume | Off-exchange venue concentration | [spec](superpowers/specs/2026-07-03-finra-ats-dark-pool-screener-design.md) |
| 🟢 | `fundamentals` | SEC XBRL fundamentals | Primary-source fundamentals (complements `stocks`) | [spec](superpowers/specs/2026-07-03-sec-fundamentals-screener-design.md) |

New official sources (confirm endpoints at build):

| Conf | Dispatcher | Screener | Signal | Spec |
|---|---|---|---|---|
| 🟡 | `treasury` | U.S. Treasury Fiscal Data | TGA/liquidity, debt, yield curve, auctions | [spec](superpowers/specs/2026-07-03-treasury-fiscaldata-screener-design.md) |
| 🟡 | `nyfed` | NY Fed Markets data | SOMA/QT pace, RRP, SOFR funding stress | [spec](superpowers/specs/2026-07-03-nyfed-markets-screener-design.md) |
| 🟡 | `cboe_stats` | CBOE market statistics | Market-wide put/call ratio, VIX term structure | [spec](superpowers/specs/2026-07-03-cboe-market-stats-screener-design.md) |
| 🟡 | `eia` | EIA energy inventories | Crude/gasoline/natgas builds & draws | [spec](superpowers/specs/2026-07-03-eia-energy-screener-design.md) |
| 🟡 | `usda` | USDA WASDE / NASS | Crop supply/demand, stocks-to-use | [spec](superpowers/specs/2026-07-03-usda-wasde-screener-design.md) |

## Spec'd — event-date monitors 📝

New "forward calendar" kind. Framework: [event-monitor-framework](superpowers/specs/2026-07-03-event-monitor-framework-design.md).

| Conf | Dispatcher | Monitor | Signal | Spec |
|---|---|---|---|---|
| 🔵 | `econ_calendar` | Economic release calendar (FRED backbone) | Upcoming CPI/PPI/jobs/GDP/retail dates | [spec](superpowers/specs/2026-07-03-econ-calendar-monitor-design.md) |
| 🔵 | `market_calendar` | Market holidays / early closes / OPEX | No-trade days, quad-witching (shared infra) | [spec](superpowers/specs/2026-07-03-market-calendar-monitor-design.md) |
| 🔵 | `fomc` | FOMC meetings / blackout / minutes | Rate-decision + blackout windows | [spec](superpowers/specs/2026-07-03-fomc-calendar-monitor-design.md) |
| 🔵 | `earnings` | Earnings calendar | Forward earnings dates (stockanalysis + EDGAR confirm) | [spec](superpowers/specs/2026-07-03-earnings-calendar-monitor-design.md) |

---

## Recommended build order

Ranked by signal × low effort × non-overlap (reuse of existing pipelines called out):

1. ~~**`cftc --family` (Disaggregated/TFF)**~~ — ✅ **Built** (see Built table). Cloned the existing CFTC Socrata pipeline. [plan](superpowers/plans/2026-07-03-cot-disaggregated-tff-screener.md)
2. ~~**`short_interest`**~~ — ✅ **Built** (see Built table). Cloned the `short_volume` CDN pattern; adds squeeze/days-to-cover. [plan](superpowers/plans/2026-07-03-finra-short-interest-screener.md)
3. **`econ_calendar`** — reuses the existing FRED key; unified upcoming-release backbone.
4. **`market_calendar`** — small, deterministic; shared infra other monitors depend on.
5. **`fundamentals`** — official XBRL fundamentals; reuses EDGAR CIK/UA handling.
6. **`fomc`** — small HTML parse + computed blackout/minutes; high macro impact.
7. **`treasury` auctions** — clean key-free JSON; auction calendar doubles as a monitor.
8. **`earnings`** — stockanalysis forward feed + EDGAR confirmation (undocumented source, build last).

Lower-priority / specialized: `ats`, `nyfed`, `cboe_stats`, `eia`, `usda`.

## Idea 💡 (no spec)

- OCC cleared options/futures volume (noted in `cboe_stats` spec).
- SEC 13F institutional holdings, N-PORT/N-MFP fund holdings, Reg SHO threshold list.
- FINRA TRACE corporate/agency bond data.
