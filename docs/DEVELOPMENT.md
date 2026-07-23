# Developer guide

A signal-collection layer for discretionary trading: ~20 independent
**screeners** and **monitors** that each read one official data source (SEC,
FRED, CFTC, FINRA, CBOE, Treasury, NY Fed, EIA, USDA, …) into a per-source
SQLite database, then derive signals as SQL views. Four **combiners** read
those databases read-only and produce a market regime, a per-ticker scorecard,
position-sizing guidance, and a point-in-time backtest of the whole thing.

There is no order-placement path anywhere in this repository — the only account
interaction is _reading_ positions and fills. The live dashboard
(<https://ninkuk.github.io/agentic-trading-research-bot/>) is regenerated nightly at
9:13pm Phoenix, published at 9:20pm, and marked `noindex`.

```bash
uv run python main.py fred --db data/fred.db              # collect
uv run python main.py composite --db data/composite.db    # derive an opinion
sqlite3 data/composite.db 'SELECT * FROM v_scorecard'     # read it
```

## Why it's built this way

**Zero runtime dependencies.** Every source is fetched with `urllib`, parsed
into plain dicts, and written with `sqlite3` — all stdlib. A plain `git clone`
on any Python 3.12 runs the whole system; the only dev dependencies are
`pytest`, `ruff`, and `mypy`. This is a deliberate constraint: a pipeline meant
to run unattended for years shouldn't have a dependency tree rotting underneath
it.

**ELT, not ETL.** Fetchers store the raw or lightly-parsed response. Signals —
z-scores, YoY changes, regime flags, stocks-to-use ratios, blackout windows —
are computed in SQL views (`v_latest`, `v_zscore`, `v_upcoming`, …).
Recalibrating a threshold is a view change, not a re-fetch, and the stored data
stays untouched by whatever the current opinion is.

**Official primary sources.** Data comes from the issuing agency, not an
aggregator, with one vetted exception (stockanalysis.com) and one
clearly-labelled broker tier admitted only where no official source covers the
field.

**Determinism.** No wall-clock in the hot path. Time enters as an injected
`now_iso` parameter, and monitor views filter on a `calendar_now` singleton row
rather than `date('now')`. Network sits behind injectable `get=`/`opener=`
seams. The result:

```
~1300 passed in ~2s
```

The entire suite is offline — no network, no API keys, no fixtures fetched at
test time.

**Grading before acting.** The `scorer` combiner grades past opinions against
forward returns and compares what the human actually did against what was
flagged. It never feeds back automatically; re-weighting the catalog is a human
decision made by reading the efficacy views. `backtest` replays signals against
point-in-time data vintages so a macro report stays out of the replay until the
date it was really published.

## Quickstart

The short version is one command — it performs the setup steps below, runs a
short demo from the keyless sources, and offers the nightly schedule (macOS):

```bash
./setup.sh
```

Or, by hand:

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Ninkuk/agentic-trading-research-bot.git && cd agentic-trading-research-bot
uv sync
git config core.hooksPath .githooks     # lint/format/type/test gate, ~2s

cp .env.example .env                    # then fill in the free API keys
uv run python main.py --list            # every dispatcher name
uv run python main.py fred --db data/fred.db --keep-days 90
uv run pytest
```

Most sources need **no API key** — SEC, FINRA, CBOE, Treasury, NY Fed, and the
calendars all work out of the box. `FRED_API_KEY`, `EIA_API_KEY`, and
`NASS_API_KEY` are free; see `.env.example`.

Settings — tunables and API keys — can also be edited via
`uv run python config_ui.py`, a local web UI (loopback-only) that reads and
writes `.env` directly. Adding a new tunable? The `KNOBS` catalog in
`config_ui.py` is the single extension point.

> Every `--db` default is a bare cwd-relative filename. Always pass
> `data/<name>.db`, or you'll scatter databases across the repo root.

## What it collects

|                        | Sources                                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Macro / rates**      | `fred` (FRED + ALFRED vintages), `treasury` (auctions, yield curve), `nyfed` (RRP, SOFR), `econ_calendar`, `fomc` |
| **Positioning / flow** | `cftc` (COT, three families), `short_interest`, `short_volume`, `ats` (FINRA dark-pool), `ftd` (fails-to-deliver) |
| **Options / vol**      | `options` (CBOE chains, hourly), `cboe_stats` (VIX term structure, put/call)                                      |
| **Equities**           | `stocks`, `fundamentals` (SEC XBRL frames), `edgar` (filing activity), `earnings`                                 |
| **Commodities**        | `eia` (petroleum, natural gas), `usda` (NASS, WASDE)                                                              |
| **Sentiment**          | `reddit` (ApeWisdom)                                                                                              |
| **Calendars**          | `market_calendar` (holidays, OPEX — network-free)                                                                 |
| **Account**            | `portfolio`, `journal` — read-only position and fill state                                                        |

The four combiners touch no network at all; they ATTACH the source databases
read-only:

- **`composite`** — a market regime plus a per-ticker scorecard.
- **`scorer`** — grades composite's past opinions against forward returns, and
  owns the decision journal comparing human action to what was flagged.
- **`advisor`** — joins the scorecard against real holdings: book heat,
  disagreements, and volatility-scaled size caps. Decision support, never order
  generation.
- **`backtest`** — point-in-time replay. Read `excess`/`beats_baseline`, never
  `hit_rate` alone: the benchmark drifts upward, so a bullish flag "wins" by
  doing nothing.

Everything runs on a launchd schedule — see [SCHEDULE.md](SCHEDULE.md).

## Architecture

Every source is a package of the **same four files** — learn one, know all
twenty:

```
sources/screeners/fred_screener/
├── fetch.py      # network + pure parsing; network behind a get=/opener= seam
├── db.py         # schema, idempotent upserts, the v_* signal views, prune
├── run.py        # orchestration; testable run() + thin argparse main()
└── catalog.py    # the curated list of what to pull
```

```
sources/
├── common/       # connect() (WAL), http_client (backoff + rate limiting), monitor framework
├── screeners/    # 17 point-in-time readers
├── monitors/     # 4 forward-looking event calendars
└── combiners/    # 4 cross-source derivations
tools/            # pure helpers: reverse-DCF solver, options implied-move math
```

`registry.py` maps name → `main`; a source ships only once it's registered
there.

Two details worth calling out, because both are load-bearing and neither is
obvious:

- **Shared rate limiting.** Every SEC fetcher acquires from one process-wide
  token bucket keyed on `sec.gov`, so the 9 req/s per-IP cap is shared rather
  than silently doubled across the `www.` and `data.` hostnames.
- **Timestamps are UTC; calendar dates are Phoenix.** Slicing a date out of a
  UTC timestamp (`now_iso[:10]`) is a bug here — UTC midnight is 5pm Phoenix
  and eight scheduled jobs run after it, so the naive slice yields _tomorrow_
  for every one of them. Use `phx_date()`.

## Development

```bash
uv run pytest                  # ~1300 tests, offline, ~2s
uv run ruff check              # lint
uv run ruff format             # format
uv run mypy                    # types
```

All four gates run in the pre-commit hook. Tests mirror the module layout:
`tests/test_<name>_<layer>.py`, where layer is one of `catalog`, `fetch`,
`db_schema`, `db_write`, `db_views`, `run`.

Contributor guidance — the invariants to preserve, the spec → plan → build
workflow, and the data-source policy — lives in [CLAUDE.md](../CLAUDE.md).
