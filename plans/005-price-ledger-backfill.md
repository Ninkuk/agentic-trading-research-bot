# Plan 005: Backfill the price ledger's benchmark proxies from stockanalysis history

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan in
> `plans/README.md`.
>
> **Supersedes `plans/001-price-ledger-backfill-spike.md`.** Do not execute 001.
> Its step-1 spike ran, fired its STOP condition, and in doing so uncovered a
> pre-existing bug in the ledger that plan 000 then fixed. Every premise 001 was
> written against has changed. 001 is retained only as the record of that spike.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (writes to a permanent, never-pruned table)
- **Depends on**: **plan 000 must already be applied.** It is, in the working
  tree, uncommitted.
- **Category**: direction
- **Planned at**: commit `5c14446` **plus the uncommitted plan-000 changes**, 2026-07-09
- **Supersedes**: `plans/001-price-ledger-backfill-spike.md`

### Drift check (run first)

```
git diff --stat 5c14446..HEAD -- sources/combiners/scorer sources/combiners/backtest
grep -c 'm."price"' sources/combiners/scorer/fetch.py          # must be >= 1
grep -c 'def rebuild_prices' sources/combiners/scorer/db.py     # must be 1
sqlite3 -readonly data/scorer.db "SELECT close FROM prices WHERE symbol='SPY' AND price_date='2026-07-07';"
```

The last query **must return `747.71`**. If it returns `751.28`, plan 000 is not
applied and this plan is unsafe — **STOP**. Backfilling true closes into a
ledger whose rows are shifted one session would create a systematic mismatch on
every symbol, and `v_basis_breaks` would not catch it (two adjacent closes have
a ratio near 1.0, well inside `BASIS_BREAK_LO=0.55` / `BASIS_BREAK_HI=1.8`).

## Why this matters

`scorer.db.prices` is the permanent close ledger. Two things read it: the
scorer, to compute forward returns; and the `backtest` combiner, which copies
asset-class proxy benchmarks out of it. It is **11,049 symbols wide and ~3 days
deep**, because it is only ever fed forward, one close per symbol per night.

The cost is measurable right now. `backtest.db`:

| | rows |
|---|---|
| `eia_crude_stocks` signal observations (back to **1982-08-27**) | 2,283 |
| `eia_natgas_storage` signal observations (back to 2010-01-08) | 860 |
| `SP500` benchmark closes (from `fred.db`, 10y) | 2,513 |
| **`XLE` benchmark closes (from `scorer.db.prices`)** | **3** |

So 3,143 fully-harvested signal observations grade against **three** benchmark
closes. The result, from `v_replay_efficacy`:

```
signal_id           direction  horizon  n_days  n_bench  hit_rate  reliable
eia_crude_stocks    neutral    5        3       0        NULL      0
eia_natgas_storage  bearish    5        3       0        NULL      0
```

`n_bench = 0`, `hit_rate` NULL. The replay code is finished and correct; it has
nothing to grade against. Compare `fred_curve`, which shares the deep SP500
spine: `n_days = 546`, `n_bench = 546`, `hit_rate = 0.394`, `reliable = 1`.

### Exactly why the benchmark depth is the whole bottleneck

`v_pit_market` (in `backtest.db`) does:

```sql
FROM (VALUES ('eia_crude_stocks','XLE'), ...) o
JOIN benchmark_closes d ON d.benchmark = o.benchmark
```

— it iterates **benchmark trading days** and forward-fills the latest
`market_obs` value as-of each one. `v_replay_efficacy` then INNER JOINs flags to
returns on `(benchmark, asof_date)`.

Two consequences an executor must internalize:

1. **`n_days` is bounded by `COUNT(benchmark_closes)`, not by signal depth.**
   XLE has 3 closes → `n_days = 3`. That is the entire explanation.
2. **The EIA report date never has to be a trading day.** Every EIA observation
   lands on a Friday (`strftime('%w', obs_date) = '5'` for all 3,143 rows), and
   several of those Fridays are market holidays (2026-07-03, every Good Friday).
   It does not matter: forward-fill carries the last report onto each XLE date.
   Do **not** "fix" a date-alignment problem — there isn't one.

So after the backfill, `n_days` for `eia_*` should jump from `3` to **thousands**
(XLE has ~6,918 bars back to 1998-12-23). Note the pre-1998 EIA observations —
crude goes back to 1982-08-27 — are simply never as-of'd, because
`benchmark_closes` starts at XLE's inception. That is correct behavior, not loss.

**Watch the `direction` column.** `hit` is NULL when `score = 0`, so a `neutral`
row always has `n_bench = 0` no matter how deep the spine. Today
`eia_crude_stocks` shows only a `neutral` row (its 3 sampled days were all
within ±2% change). Success means **non-neutral** rows appear with `n_bench > 0`.

`docs/BACKLOG.md` defers the entire CFTC backtest tranche on exactly this,
naming benchmark availability as blocker #1 and `GLD`/`DBA`/`TLT` history as
step 1 of its build recipe. `backtest/catalog.py` carries the resigned comment
that `scorer.db` is "the only growing close history for these tickers… Deep
history accrues over time."

It does not have to. `docs/stockanalysis_data_json_catalog.md:68` already
catalogues `/stocks/{T}/history/` as OHLCV back to 1982, on the one domain
`CLAUDE.md` marks as an approved exception. Nothing fetches it.

**When this lands**: `eia_*` grades against a real XLE spine immediately, step 1
of the backlog's CFTC recipe is satisfied (`GLD`/`DBA`/`TLT`), and the scorer's
own crosswalk benchmarks stop being three days deep.

## What plan 001 got wrong (read this before starting)

001 assumed the blocker was *split adjustment*. It ran its spike, found that the
history endpoint returns **split-adjusted** closes, and stopped. That finding is
true but it was **not** the real hazard, and the STOP it triggered was correct
for the wrong reason.

The real hazard was that `harvest_prices` had been reading the wrong column
entirely (`close`, which is stockanalysis's *Previous* Close). Plan 000 fixed
that. With the ledger corrected, split-adjustment is **benign**, and this has
been verified empirically rather than argued:

For all **18** proxy symbols × their 3 existing ledger dates — 54 comparisons —
the endpoint's `c` matches the corrected ledger **exactly**:

```
agree=54  disagree=0  api-missing=0  fetch-fails=[]
```

Why it is benign: the backfill writes one internally-consistent series (all bars
on today's split basis). The overlap with existing forward rows agrees, so
`INSERT OR IGNORE` keeping the existing rows changes nothing. A split occurring
*after* the backfill produces a seam between stored historical rows and new
forward rows — but that is exactly the situation that exists today with no
backfill at all, and it is what `v_basis_breaks` and the pending-hold in
`mature()` exist to catch.

001 also assumed `t` was an epoch integer and that `probe.page_data` could fetch
full history. Both are false. See "Current state".

## Current state

### The endpoint (established by probing; do not re-derive)

**Use the JSON API, not the `__data.json` route.**

```
GET https://stockanalysis.com/api/symbol/s/{SYMBOL}/history?range=Max
User-Agent: Mozilla/5.0
```

- The SvelteKit route `/stocks/{T}/history/__data.json` **ignores `range`** and
  returns only ~124 bars (6 months). `probe.page_data` reads that route. Do not
  use it for this.
- `?range=Max` returns full history: NVDA gives **6,905 bars back to 1999-01-25**.
  Other accepted values include `1M`, `5Y`, `10Y`.

Response shape **with `?range=Max`** (measured 2026-07-09 on SPY, NVDA, XLE):

```json
{"status":200,
 "data":[{"a":204.12,"c":204.12,"h":205.16,"l":195.06,
          "o":195.18,"t":"2026-07-08","v":145890318,"ch":3.65}, ...]}
```

- **`payload["data"]` IS the bar list.** It is a flat JSON array, not nested.
- Bars are **newest-first**.
- `t` is an **ISO date string `YYYY-MM-DD`**, not an epoch integer.
- `c` = close, **retroactively split-adjusted**. `a` = close adjusted for splits
  **and dividends**.

> **Do not omit `?range=Max`.** The bare URL is a *different* response: for NVDA
> it returns `{"status":200,"data":{"data":[...124 bars...],"news":…,"other":…}}`
> — `data` is a **dict** — and for `SPY` and `XLE` it returns **HTTP 404**.
> An earlier draft of this plan mis-transcribed the bare-NVDA shape as the
> `range=Max` shape and told the executor to read `payload["data"]["data"]`.
> That would have raised on all 18 symbols and inserted zero rows.
>
> Because the shape is demonstrably not stable across query strings, accept
> **both** and fail loudly on anything else (`CLAUDE.md`: live-verify source
> schemas; a wrong assumption silently drops rows rather than erroring):
>
> ```python
> bars = payload["data"]                       # KeyError -> let it raise
> if isinstance(bars, dict):                   # the bare-URL shape
>     bars = bars["data"]
> if not isinstance(bars, list):
>     raise ValueError(f"unexpected history payload: {type(bars).__name__}")
> ```

Bar counts observed: SPY **8,415** back to `1993-02-01`; XLE **6,918** back to
`1998-12-23`; NVDA **6,905** back to `1999-01-25`. Inceptions differ per proxy;
that is expected.

**Use `c`.** The forward feeder stores the raw close as of capture, which for a
symbol with no split since is identical to `c`. `a` would silently diverge on
every dividend.

Proof `c` is split-adjusted, if you want it: NVDA split 10-for-1 effective
2024-06-10. `c` for `t = 2024-06-07` is `120.888`; the unadjusted close that day
was ~$1,208.88.

### The write path — `sources/combiners/scorer/db.py`

```python
def insert_prices(conn, rows) -> int:
    for symbol, price_date, close in rows:
        if symbol is None or price_date is None or close is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, price_date, close) VALUES (?, ?, ?)",
            (symbol, price_date, close),
        )
```

`INSERT OR IGNORE` — **existing rows always win**. A backfill can never overwrite
a forward-harvested row. That is what makes this additive; it is also why a bad
row would be permanent. `prices` is never pruned (`scorer/db.py` `prune`
docstring).

### The settled-only rule you must honor

`scorer/fetch.py:harvest_prices` (post-plan-000) only harvests a `priceDate` from
a snapshot captured on a **strictly later Phoenix calendar day**, because
stockanalysis's `price` for the current session is unsettled mid-day.

The history endpoint's newest bar has the same hazard: run intraday, `c` for
today is a live price, not a close. **Your backfill must skip any bar whose `t`
is >= the current Phoenix date.** Use `phx_date(now_iso)` from
`sources/common/clock.py`. Never slice a date out of a timestamp.

**Known, accepted cost of this rule.** If the backfill runs *after* the close on
a trading day D, D's bar is settled and the rule discards it anyway. That is one
day of one symbol, and the nightly forward harvester picks it up the next
morning from `stocks.db`/`etfs.db`. Do not try to be clever about market hours —
the repo has no market-clock primitive, and a wrong guess writes an unsettled
price into a permanent, never-pruned table.

### The symbols in scope — `sources/combiners/scorer/catalog.py`

```python
CROSSWALK_BENCHMARK: dict[str, str | None] = {
    "XLE": None, "XOM": "XLE", "CVX": "XLE", "USO": "XLE",
    "GLD": None, "GDX": "GLD", "SLV": "GLD", "FCX": "GLD", "COPX": "GLD",
    "DBA": None, "CORN": "DBA", "SOYB": "DBA", "WEAT": "DBA",
    "TLT": None, "IEF": "TLT",
    "SPY": None, "QQQ": "SPY", "IWM": "SPY",
}
```

**18 symbols. That is the entire scope.** Not the other ~11,031.

### The backtest's benchmark roster — `sources/combiners/backtest/catalog.py`

```python
CLASS_BENCHMARKS: list[dict[str, Any]] = [
    {"symbol": "XLE", "db": SCORER_DB},  # energy proxy
]
```

`run.py` loops these and calls `fetch.harvest_price_ledger(conn, symbol)`, which
reads `src.prices` and writes via `db.insert_benchmark`. That writer uses
**`INSERT OR REPLACE`** (`backtest/db.py:311`), so `backtest.db` self-heals from
a corrected/deepened ledger on the next run. No `backtest.db` surgery is needed.

### Side effects on the scorer (analysed; do not re-derive)

`prices` is read by `mature()` and `entry_for()`, so deepening it *could* have
changed grading. It does not. Verified:

- **The horizon walk is per-symbol and strictly forward**
  (`scorer/db.py:722-730`): `xdate` is the Nth ledger date with
  `p.price_date > t.entry_date`. Backfilled rows are all in the **past**, so no
  existing outcome's exit date can move.
- **`entry_for()` picks the first close after `composite_date`**, and every
  registered `composite_date` is `2026-07-06`. Past history cannot satisfy it.
- **The basis-break guard is windowed** to `(entry_date, x.xdate]`
  (`scorer/db.py:695-706`). `USO` reverse-split 1:8 in 2020; that break is
  decades outside any current entry/exit window and will not hold rows pending.
  It *will* correctly appear in `v_basis_breaks` — which is why step 6's seam
  check is scoped to `price_date >= '2026-06-01'`.

One genuine, benign effect: the backfill adds `2026-07-08` for the 18 proxies
(it is settled and before today's Phoenix date), one day ahead of the other
~11,031 symbols whose ledgers still end at `2026-07-07`. Each symbol's horizon
walk counts *its own* ledger dates, so this is not an inconsistency — but it does
mean the 18 have gapless history while the rest have only what the nightly
harvester captured. That asymmetry already exists today; the backfill widens it.
Nothing in this plan should try to close it.

### Repo conventions you must match

- **Zero runtime third-party dependencies.** stdlib only (`urllib`, `sqlite3`,
  `json`, `argparse`). `ruff`/`mypy`/`pytest` are dev-only. Do not add a dep.
- **Four-file package shape**: `fetch.py` (network + *pure* parsing), `db.py`,
  `run.py` (injected seams), `catalog.py`. Read `sources/combiners/backtest/fetch.py`
  and `run.py` as the closest exemplar.
- **No network in tests.** Every fetcher takes a `get=` seam; every `run()` takes
  `fetch_*=` seams. The whole suite is offline. Keep it that way.
- **Secret hygiene on errors.** Per-item failure: `conn.rollback()`, then print
  **only** `type(e).__name__` — never `str(e)`, `repr(e)`, `e.url`. A urllib
  `HTTPError` carries the request URL.
- **Timestamps UTC, calendar dates Phoenix.** `phx_date(now_iso)`, never `[:10]`.
- **Be a polite client.** `CLAUDE.md`: "stockanalysis.com is an unofficial
  endpoint; don't hammer it." 18 requests, ≥0.7s apart.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Tests | `uv run pytest` | all pass (baseline: 1104) |
| Lint | `uv run ruff check` | exit 0 |
| Format | `uv run ruff format --check` | exit 0 |
| Types | `uv run mypy` | exit 0 |
| List dispatchers | `uv run python main.py --list` | includes `pricehistory` after step 4 |
| Read a DB | `sqlite3 -readonly data/<x>.db "<sql>"` | rows |

## Scope

**In scope** (the only files you may create or modify):

- `sources/combiners/scorer/pricehistory.py` (create)
- `sources/combiners/scorer/catalog.py` (modify — add `BACKFILL_SYMBOLS`)
- `sources/combiners/backtest/catalog.py` (modify — extend `CLASS_BENCHMARKS`)
- `tests/test_pricehistory_fetch.py` (create)
- `tests/test_pricehistory_run.py` (create)
- `tests/test_backtest_catalog.py` (modify — pin the new benchmarks)
- `registry.py` + `tests/test_registry.py` (modify — register `pricehistory`)
- `docs/BACKLOG.md` (modify — only the deferral note, only if step 7 succeeds)
- `plans/README.md` (modify — status row)

**Out of scope** (do NOT touch):

- `sources/combiners/scorer/fetch.py` — the forward harvester is correct
  post-000. Backfill is a **separate entry point**.
- `sources/combiners/scorer/run.py` — do **not** wire backfill into the nightly
  run. It is a manual one-shot, like `ftd --full`.
- `sources/combiners/scorer/db.py` — do not touch `insert_prices`, the `prices`
  schema, `BASIS_BREAK_*`, `rebuild_prices`, or any view. You are a writer into
  an existing table via the existing function.
- `sources/combiners/backtest/db.py` / `fetch.py` / `run.py` — `INSERT OR REPLACE`
  already self-heals. Only the catalog changes.
- **Backfilling beyond the 18 `CROSSWALK_BENCHMARK` symbols.** A ticker-universe
  backfill is a separate, larger plan with a real rate-limit budget question.
- `deploy/launchd/install.py` — no scheduled job.

## Git workflow

- Branch: `advisor/005-price-ledger-backfill`
- Conventional commits, lowercase, scoped (match `git log`):
  `feat(scorer): backfill benchmark proxies from stockanalysis history`
- Do **not** add a `Co-Authored-By` trailer.
- Do **not** push or open a PR.

## Steps

### Step 1: verify the ground truth before writing anything

```
sqlite3 -readonly data/scorer.db "SELECT close FROM prices WHERE symbol='SPY' AND price_date='2026-07-07';"
sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM benchmark_closes WHERE benchmark='XLE';"
sqlite3 -readonly data/backtest.db "SELECT signal_id, n_bench FROM v_replay_efficacy WHERE signal_id LIKE 'eia%' LIMIT 2;"
```

**Verify**: `747.71`; `3`; `n_bench` is `0` for both `eia_*` rows.

If SPY reads `751.28`, plan 000 is not applied — **STOP** (see Drift check).

### Step 2: add `BACKFILL_SYMBOLS` to `sources/combiners/scorer/catalog.py`

Derive it, never retype it, so the two can't drift:

```python
# One-shot historical backfill roster for `main.py pricehistory` (plan 005).
# Exactly the crosswalk proxies and their fan-out tickers: these are the only
# symbols the scorer benchmarks against and the backtest replays against, so
# they are the only ones whose history the ledger needs deep. A ticker-universe
# backfill (~11k symbols) is deliberately NOT here — see docs/BACKLOG.md.
BACKFILL_SYMBOLS: tuple[str, ...] = tuple(sorted(CROSSWALK_BENCHMARK))
```

**Verify**:
```
uv run python -c "from sources.combiners.scorer.catalog import BACKFILL_SYMBOLS as B; print(len(B), B[:4])"
```
→ `18 ('COPX', 'CORN', 'CVX', 'DBA')`

### Step 3: write `sources/combiners/scorer/pricehistory.py` — network + pure parse

Two layers, strictly separated:

```python
HISTORY_URL = "https://stockanalysis.com/api/symbol/s/{symbol}/history"
_UA = {"User-Agent": "Mozilla/5.0"}


def parse_history(payload, before_date: str) -> list[tuple[str, float]]:
    """Pure. (price_date, close) for bars STRICTLY BEFORE before_date, sorted
    ascending. Uses `c` (split-adjusted close), never `a` (also dividend-
    adjusted). Bars with a null/absent close are dropped, never defaulted."""


def fetch_history(symbol: str, get=_default_get) -> dict:
    """Network. `get` is the injectable seam: takes a symbol, returns the
    decoded JSON payload. Tests inject a fake; no test touches the network."""
```

Requirements, each of which has a test in step 5:

- `parse_history` reads `payload["data"]`, which is the bar list under
  `?range=Max`. Tolerate the bare-URL dict form (`payload["data"]["data"]`) and
  raise `ValueError` on anything that is not ultimately a list. An **empty list
  is a valid response** (a delisted symbol) — return `[]`, do not raise. Loudness
  belongs in `run()`: a symbol yielding 0 rows must be reported as failed, not
  silently counted as a success.
- Use `bar["c"]`. Assert in a comment why not `a`.
- `t` is already `YYYY-MM-DD`. Do **not** call `datetime.fromtimestamp`.
  Validate the shape (10 chars, two dashes) and raise if it isn't.
- **`before_date` filter is mandatory**: drop bars with `t >= before_date`.
  The caller passes `phx_date(now_iso)`. This mirrors the settled-only rule.
- `get=` must default to a real fetcher and be overridable.

### Step 4: write `run(...)` + `main(argv)` in the same module; register it

Follow `sources/combiners/backtest/run.py` for shape.

```python
def run(db_path, symbols, *, now_iso=None, fetch_history=fetch_history,
        sleep=time.sleep) -> tuple[int, int, list[str]]:
    """Returns (symbols_ok, rows_inserted, failed_symbols)."""
```

- `now_iso` defaults to `datetime.now(UTC).isoformat()`; `before_date =
  phx_date(now_iso)`.
- Open with `scorer.db.connect`; call its `ensure_schema` before writing.
- Write **only** through `scorer.db.insert_prices`. Do not hand-roll the INSERT.
- **Skip-and-continue per symbol**: `try/except Exception`, `conn.rollback()`,
  print `f"FAILED {symbol}: {type(e).__name__}"`, append to `failed`, continue.
  Never print `str(e)`, `repr(e)`, or `e.url`.
- `sleep(0.7)` between symbols; injectable so tests run instantly.
- `main(argv)` argparse: `--db` (default `scorer.db`; the operator must pass
  `data/scorer.db` — every `--db` default in this repo is a bare cwd-relative
  filename), `--only` / `--exclude` over `BACKFILL_SYMBOLS`, and `--dry-run`
  which fetches and reports counts but writes nothing.
- Final line: `pricehistory: N symbols, M rows inserted, K failed`.

Register `"pricehistory"` in `registry.py`; add it to `tests/test_registry.py`.

**Verify**: `uv run python main.py --list | grep -c pricehistory` → `1`

### Step 5: tests (all offline)

Model on `tests/test_backtest_fetch.py` / `tests/test_backtest_run.py`.

`tests/test_pricehistory_fetch.py`:
- `test_parse_history_returns_ascending_date_close_pairs`
- `test_parse_history_uses_c_not_a` — fixture where `c=100.0`, `a=99.0`; assert `100.0`
- `test_parse_history_drops_bars_on_or_after_before_date` — the settled rule; a
  bar dated exactly `before_date` must be excluded
- `test_parse_history_drops_null_close_rather_than_defaulting`
- `test_parse_history_accepts_the_flat_range_max_shape` — `{"data": [bar, ...]}`
- `test_parse_history_accepts_the_bare_url_dict_shape` — `{"data": {"data": [bar]}}`
- `test_parse_history_returns_empty_list_for_an_empty_series` — `{"data": []}`
  returns `[]` and does **not** raise (a delisted symbol is valid)
- `test_parse_history_raises_on_unexpected_payload_shape` — `{}` (no `data` key)
  and `{"data": 5}` must raise
- `test_run_reports_a_symbol_that_yields_zero_rows_as_failed`
- `test_parse_history_raises_on_non_iso_date` — `t = 1717718400` must raise
- `test_fetch_history_uses_injected_get_seam` — assert the fake `get` was called
  with the symbol; assert no network

`tests/test_pricehistory_run.py` (against `tmp_path`):
- `test_run_inserts_rows_into_prices`
- `test_run_is_idempotent` — second run inserts **0** rows
- `test_run_never_overwrites_an_existing_forward_row` — pre-insert
  `('XLE','2026-07-07',999.0)`, backfill a different close for that date, assert
  it is still `999.0`
- `test_run_skips_and_continues_on_one_symbol_failure`
- `test_run_failure_message_does_not_leak_exception_text` — raise
  `Exception("secret-token-in-url")`; assert that string is absent from stdout
- `test_run_excludes_todays_bar` — inject `now_iso` whose Phoenix date is
  `2026-07-08`; a bar dated `2026-07-08` must not land. **Use an evening
  `now_iso` that straddles the UTC rollover** (e.g. `2026-07-09T04:05:00+00:00`,
  whose Phoenix date is `2026-07-08`), or the test cannot catch a UTC/Phoenix mixup.
- `test_dry_run_writes_nothing`

**Verify**: `uv run pytest tests/test_pricehistory_fetch.py tests/test_pricehistory_run.py` → all pass.

### Step 6: back up, dry-run, then backfill

`prices` is permanent and `INSERT OR IGNORE` makes a bad row unfixable by
re-running. Back up first — **but not with `cp`.**

> ### ⚠️ `cp data/scorer.db` produces an EMPTY database
>
> `scorer.db` is opened `PRAGMA journal_mode=WAL` (`scorer/db.py:connect`).
> Measured 2026-07-09: the main file is 4.1 MB and `data/scorer.db-wal` is
> **7.7 MB of uncheckpointed content**. Copying the main file alone captures
> none of it:
>
> ```
> cp data/scorer.db /tmp/main-only.db
> sqlite3 -readonly /tmp/main-only.db "SELECT COUNT(*) FROM prices;"   ->  0
> ```
>
> **Zero rows.** Restoring such a "backup" after a failed run would destroy the
> ledger — and the orphaned live `-wal` replayed onto a mismatched main file
> typically yields `database disk image is malformed`. Every STOP condition in
> this plan that says "restore the backup" depends on the backup being real.

Use SQLite's own backup, which checkpoints the WAL for you:

```
BK="data/scorer.db.bak-005-$(date +%Y%m%dT%H%M%S)"
sqlite3 data/scorer.db ".backup '$BK'"
sqlite3 -readonly "$BK" "SELECT COUNT(*) FROM prices;"     # must be > 33000, NOT 0
sqlite3 -readonly "$BK" "SELECT close FROM prices WHERE symbol='SPY' AND price_date='2026-07-07';"
```

**Verify the backup before proceeding.** If `COUNT(*)` is `0`, stop — you have no
safety net. (`cp data/scorer.db data/scorer.db-wal data/scorer.db-shm` together
also works, as does `PRAGMA wal_checkpoint(TRUNCATE)` before a `cp`. `.backup` is
the least error-prone.)

Then:

```
uv run python main.py pricehistory --db data/scorer.db --dry-run
uv run python main.py pricehistory --db data/scorer.db
```

Then verify, in order. **All must hold.**

1. Depth arrived:
```
sqlite3 -readonly data/scorer.db "SELECT symbol, COUNT(*) n, MIN(price_date), MAX(price_date) FROM prices WHERE symbol IN ('SPY','XLE','GLD','DBA','TLT') GROUP BY symbol;"
```
→ five rows, each `n` in the thousands, `MIN(price_date)` years in the past.

2. **No seam break.** A break whose `price_date` is recent means the backfilled
   basis disagrees with the forward-harvested basis:
```
sqlite3 -readonly data/scorer.db "SELECT * FROM v_basis_breaks WHERE symbol IN ('SPY','QQQ','IWM','XLE','XOM','CVX','USO','GLD','GDX','SLV','FCX','COPX','DBA','CORN','SOYB','WEAT','TLT','IEF') AND price_date >= '2026-06-01';"
```
→ **0 rows**. And as a stronger property, backfilled history should contain **no**
breaks at all, because `c` is retroactively split-adjusted (a `USO` series spanning
its 2020 1:8 reverse split is smooth). Check:
```
sqlite3 -readonly data/scorer.db "SELECT symbol, COUNT(*) FROM v_basis_breaks WHERE symbol='USO' GROUP BY 1;"
```
→ 0 rows. A break inside backfilled history means the series is not on one basis —
**STOP**.

3. Existing forward rows preserved. **Note that a bare value check is useless
   here**: the API returns the same `747.71`, so it cannot distinguish "row
   preserved" from "row overwritten with an identical value". `INSERT OR IGNORE`
   cannot overwrite, but assert the property that actually discriminates — the
   row count grew by exactly the number of *new* dates:

```
# BEFORE the backfill, record the baseline:
sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM prices WHERE symbol='SPY';"     # expect 3
# AFTER:
sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM prices WHERE symbol='SPY';"
```
→ `after == (bars returned with t < phx_today) `, and the run's own
`rows_inserted` for SPY == `after - 3`. If `rows_inserted` equals `after`, the
three pre-existing rows were counted as inserts and `INSERT OR IGNORE` is not
doing what this plan assumes — **STOP**.

The no-overwrite property is asserted properly in
`test_run_never_overwrites_an_existing_forward_row` (step 5), which seeds a
*deliberately different* close and proves it survives. That is the real guard;
this on-disk check is only a smoke test.

4. Cross-check against CBOE, an independent feed, for the overlap:
```
sqlite3 -readonly data/scorer.db "ATTACH 'file:data/options.db?mode=ro' AS o;
SELECT COUNT(*) compared, SUM(ABS(p.close-u.close)<0.005) agree
FROM prices p JOIN o.underlying_daily u
  ON u.underlying=p.symbol AND u.snapshot_date=p.price_date;"
```
→ `compared == agree`.

### Step 7: extend `CLASS_BENCHMARKS` and confirm `eia_*` lights up

In `sources/combiners/backtest/catalog.py`, replace the stale comment and add
the three proxies the backlog's recipe names:

```python
# Asset-class proxy benchmarks copied from scorer.db's permanent price ledger.
# Backfilled to full history by `main.py pricehistory` (plan 005), so an
# asset-class replay grades against real depth rather than a few days.
CLASS_BENCHMARKS: list[dict[str, Any]] = [
    {"symbol": "XLE", "db": SCORER_DB},  # energy proxy
    {"symbol": "GLD", "db": SCORER_DB},  # metals proxy
    {"symbol": "DBA", "db": SCORER_DB},  # ags + softs proxy
    {"symbol": "TLT", "db": SCORER_DB},  # rates proxy
]
```

Add a test in `tests/test_backtest_catalog.py` pinning `CLASS_BENCHMARKS` to the
subset of `scorer.catalog.CROSSWALK_BENCHMARK` whose value is `None` (the class
proxies themselves), so the two can never drift.

> **Only `XLE` changes anything today.** `eia_crude_stocks` and
> `eia_natgas_storage` are the only replayed asset-class signals, and both grade
> against `XLE` — which is already in `CLASS_BENCHMARKS`. `GLD`/`DBA`/`TLT` are
> **pre-positioning** for the deferred CFTC tranche (`docs/BACKLOG.md`); adding
> them now costs one line each and satisfies step 1 of that recipe, but expect
> **no new efficacy rows from them**. Do not treat their absence from
> `v_replay_efficacy` as a failure.

Re-run and compare:

```
uv run python main.py backtest --db data/backtest.db
sqlite3 -readonly data/backtest.db "SELECT benchmark, COUNT(*) FROM benchmark_closes GROUP BY 1;"
sqlite3 -readonly data/backtest.db "SELECT signal_id, horizon, n_days, n_bench, ROUND(hit_rate,3) FROM v_replay_efficacy WHERE signal_id LIKE 'eia%' ORDER BY 1,2;"
sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM v_replay_efficacy;"
```

→ `XLE`/`GLD`/`DBA`/`TLT` each with thousands of closes (XLE ~6,918 back to
1998-12-23; DBA ~4,905 back to 2007-01-08 — the proxies have different
inceptions and that is fine). `eia_*` `n_days` jumps from `3` to thousands, and
at least one **non-`neutral`** `eia_*` row has `n_bench > 0` with a non-NULL
`hit_rate`. Total `v_replay_efficacy` count is **>= 60** (the pre-existing
SP500-graded signals must not regress).

A `neutral` row with `n_bench = 0` is **not** a failure — `hit` is NULL whenever
`score = 0`. Judge success on the non-neutral rows.

If `eia_*` still shows `n_bench = 0`, **do not start editing view SQL**. Stop and
report. The cause is upstream (the backfill did not cover the graded date range,
or `market_obs` and `benchmark_closes` don't overlap), and diagnosing it is a
separate task.

### Step 8: update `docs/BACKLOG.md`

The CFTC deferral note gives two reasons. Reason 1 ("Data availability") is now
resolved for the proxy benchmarks. Edit **only** that reason, recording that
step 1 of the build recipe is done and naming `main.py pricehistory`. Leave
reason 2 ("Unvalidatable-now complexity" — the as-of rolling percentile) exactly
as written. **Do not delete the entry.** The CFTC tranche remains deferred.

## Test plan

Steps 5 and 7. Summary: 7 tests in `test_pricehistory_fetch.py`, 7 in
`test_pricehistory_run.py`, 1 in `test_backtest_catalog.py`.

Coverage targets, in priority order:
1. **The `before_date` filter.** An unsettled same-day bar entering a permanent
   table is the highest-cost failure. Its test must straddle the UTC→Phoenix
   rollover or it proves nothing.
2. **`c` not `a`.** A dividend-adjusted series diverges silently on every payer.
3. **No-overwrite.** `INSERT OR IGNORE` semantics must be asserted, not assumed.
4. **Shape validation raises.** Silent `[]` on a changed payload is the repo's
   named failure mode.

All offline. If you want to hit stockanalysis from a test, you have mis-wired
the `get=` seam.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `uv run ruff check` exits 0
- [ ] `uv run ruff format --check` exits 0
- [ ] `uv run mypy` exits 0
- [ ] `uv run pytest` exits 0, with 15 new tests passing, no net-new failures
- [ ] `uv run python main.py --list | grep -c pricehistory` → `1`
- [ ] `sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM prices WHERE symbol='XLE'"` → `> 1000`
- [ ] `sqlite3 -readonly data/scorer.db "SELECT close FROM prices WHERE symbol='SPY' AND price_date='2026-07-07'"` → `747.71`
- [ ] Step 6's seam query returns **0 rows**
- [ ] Step 6's CBOE cross-check has `compared == agree`
- [ ] `sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM v_replay_efficacy WHERE signal_id LIKE 'eia%' AND direction != 'neutral' AND n_bench > 0"` → `> 0`
- [ ] `sqlite3 -readonly data/backtest.db "SELECT MAX(n_days) FROM v_replay_efficacy WHERE signal_id LIKE 'eia%'"` → `> 1000` (was 3)
- [ ] `sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM v_replay_efficacy"` → `>= 60`
- [ ] A backup `data/scorer.db.bak-005-*` exists **and** `sqlite3 -readonly <backup> "SELECT COUNT(*) FROM prices"` returns `> 33000` (not `0` — see the WAL warning in step 6)
- [ ] `git status` shows no modified files outside the In-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report (do not improvise) if:

- **`SELECT close FROM prices WHERE symbol='SPY' AND price_date='2026-07-07'`
  does not return `747.71`.** Plan 000 is not applied. Backfilling now would
  create a systematic one-session mismatch that `v_basis_breaks` cannot see.
- **Step 6 check 2 returns any row.** The backfilled basis disagrees with the
  forward basis at the seam. Restore the backup and report.
- **Step 6 check 4 shows `compared != agree`.** An independent feed disagrees
  with the ledger.
- `payload["data"]` is neither a list nor a dict containing a list, or `t` is
  not `YYYY-MM-DD`. The API drifted; `CLAUDE.md`'s live-verify invariant applies.
- stockanalysis returns HTTP 403 or 429 for more than 2 of the 18 symbols. You
  are being rate-limited. **Do not add retries or shorten the sleep** — report.
- A step's verification fails twice after a reasonable fix attempt.
- The work appears to require touching `scorer/fetch.py`, `scorer/run.py`,
  `scorer/db.py`, or any `backtest/` file other than `catalog.py`.
- You discover `prices` is pruned after all (check `scorer/db.py`'s `prune`
  docstring). Then the backfill is pointless.

## Maintenance notes

- **The ledger now has two writers with different bases.** Historical rows come
  from `c` (split-adjusted as of the backfill date); forward rows come from
  `metrics.price` (raw as of capture). They agree today — 54/54 across the 18
  proxies. A future corporate action in any proxy creates a real seam.
  `v_basis_breaks` is the audit trail and `mature()` holds affected rows pending.
  Watch it after any split in the 18.
- **Backfilled history contains NO basis breaks, by construction.** An earlier
  draft of this plan predicted `v_basis_breaks` rows inside `USO`'s history from
  its April 2020 1:8 reverse split. That was wrong: `c` is *retroactively*
  split-adjusted, so the series is smooth across the split
  (`USO 2020-04-27..30: 17.52 → 18.00 → 19.12`). Any break that appears inside
  backfilled history means the series is **not** internally consistent and is a
  real problem — investigate, don't dismiss it. Breaks arise only from splits
  occurring *after* the backfill, at the seam with forward-harvested rows.
- **Ticker `VII` still holds a 2018-07-11 row** at `close = 0.206`, inherited
  from a stale `priceDate` in `stocks.db.metrics`. It is not in the 18 and is
  untouched here. It demonstrates the class of bug a ticker-universe backfill
  would amplify — fix that before attempting one.
- **What a reviewer should scrutinize**: (1) that `insert_prices` was reused, not
  re-implemented; (2) that the `get=` seam is real and no test hits the network;
  (3) the `before_date` test's `now_iso` — a `T21:xx` stamp cannot catch a
  UTC/Phoenix mixup, only a `T04:xx` one can; (4) that `--dry-run` truly writes
  nothing; (5) that `parse_history` raises rather than returning `[]` on a shape
  change.
- **The prize this unblocks, in order**: `eia_*` grading (immediate); the
  backlog's CFTC asset-class replay (step 1 satisfied); and — the largest
  remaining tranche — a per-ticker forward-return spine for the 6 ticker-grain
  signals (`si_days_to_cover`, `si_spike`, `sv_ratio_spike`, `ftd_persistent`,
  `stocks_rsi`, `reddit_trending`), which needs the ~11k-symbol backfill this
  plan deliberately excludes. Do not attempt that until this one has run cleanly
  for several weeks.
