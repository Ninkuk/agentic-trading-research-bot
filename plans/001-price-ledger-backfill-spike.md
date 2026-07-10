# Plan 001: Determine how to backfill `scorer.db`'s price ledger with historical closes, and backfill the benchmark proxies

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **This is a SPIKE plan.** Step 1 is an investigation whose result determines
> whether steps 3–6 are even correct. Do not skip ahead. If step 1's finding
> contradicts this plan's stated assumption, that is a STOP condition, not
> something to work around.
>
> **Drift check (run first)**:
> `git diff --stat 5c14446..HEAD -- sources/combiners/scorer sources/combiners/backtest sources/screeners/stock_analysis_screener`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `5c14446`, 2026-07-08

## Why this matters

`scorer.db`'s `prices` table is the permanent close-price ledger that the
whole evaluation half of this system stands on: the scorer grades composite
opinions against forward returns read from it, and the `backtest` combiner
replays signals against benchmarks copied out of it. Today that ledger is
**11,047 symbols wide but only ~3–4 trading days deep**, because it is fed
forward-only — one close per symbol per nightly run.

The consequences are concrete and currently visible on disk:

- `sqlite3 data/scorer.db "SELECT COUNT(*) FROM v_signal_efficacy"` returns **0**.
  No signal has ever been graded. Nobody knows whether any of composite's 23
  signals works.
- The `eia_crude_stocks` and `eia_natgas_storage` replays are fully coded in
  `sources/combiners/backtest/catalog.py` but grade ~0 rows, because they grade
  against `XLE` and the ledger has ~3 days of `XLE`.
- `docs/BACKLOG.md` defers the entire CFTC backtest tranche on exactly this,
  naming "data availability" as blocker #1 and listing `GLD`/`DBA`/`TLT`
  history as step 1 of its build recipe.

Meanwhile, the project's own documentation already records the solution.
`docs/stockanalysis_data_json_catalog.md:68` catalogues the route
`/stocks/{T}/history/` as *"OHLCV bars `{o,h,l,c,a,v,t,ch}`, range-adjustable,
back to 1982"*. stockanalysis.com is this repo's **approved** data source (see
"Data-source policy" in `CLAUDE.md`), the `devalue` decoder needed to read that
route already exists in `sources/screeners/stock_analysis_screener/probe.py`,
and **no code fetches it.**

When this lands, the `eia_*` replay produces graded rows immediately, step 1 of
the backlog's CFTC recipe is satisfied, and signal efficacy begins converging in
days instead of months.

**The one thing that can go wrong, and why this is a spike:** the ledger stores
each day's close *on that day's price basis, with no adjusted history to correct
from* (`sources/combiners/scorer/db.py:17-25`). If the history endpoint returns
**split-adjusted** closes, backfilled rows will silently disagree with
forward-harvested rows for any symbol that has ever split — producing a false
price discontinuity that corrupts forward returns. Step 1 exists to settle this
empirically before a single permanent row is written.

## Current state

### Files and their roles

- `sources/combiners/scorer/db.py` — owns the `prices` table, the basis-break
  guard constants, and `insert_prices`. **The `prices` table is never pruned.**
- `sources/combiners/scorer/fetch.py` — `harvest_prices()`; the forward-only feeder.
- `sources/combiners/scorer/catalog.py` — `CROSSWALK_BENCHMARK`, which already
  enumerates exactly the proxy tickers that need history.
- `sources/combiners/backtest/catalog.py` — `CLASS_BENCHMARKS`, currently `[XLE]`.
- `sources/screeners/stock_analysis_screener/probe.py` — generic `__data.json`
  fetch + `devalue` decode for **any** stockanalysis.com route. Entry point:
  `page_data(path)`.
- `sources/screeners/stock_analysis_screener/fetch.py` — the existing screener
  fetcher. Note it does **not** use `probe.py`; it hits a different endpoint.

### The `prices` table (from `sqlite3 data/scorer.db ".schema prices"`)

```sql
CREATE TABLE prices (
    symbol     TEXT NOT NULL,
    price_date TEXT NOT NULL,
    close      REAL NOT NULL,
    PRIMARY KEY (symbol, price_date)
);
```

### The write path — `sources/combiners/scorer/db.py:475-485`

```python
def insert_prices(conn, rows) -> int:
    n = 0
    for symbol, price_date, close in rows:
        if symbol is None or price_date is None or close is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, price_date, close) VALUES (?, ?, ?)",
            (symbol, price_date, close),
        )
        n += cur.rowcount
    return n
```

`INSERT OR IGNORE` means **existing rows always win**. A backfill can never
overwrite a forward-harvested row. This is what makes the backfill additive and
low-risk *for existing rows* — and it is also exactly why a basis mismatch would
create a discontinuity rather than a clean overwrite.

### The forward feeder — `sources/combiners/scorer/fetch.py:7-14`

```python
def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots —
    INSERT OR IGNORE downstream dedupes, and re-harvesting nightly
    self-heals ledger gaps within the source's retention window."""
    return conn.execute(
        'SELECT DISTINCT symbol, "priceDate", "close" FROM src.metrics'
        ' WHERE "priceDate" IS NOT NULL AND "close" IS NOT NULL'
    ).fetchall()
```

So forward rows are whatever `stocks.db`/`etfs.db` `metrics.close` held on the
day of capture — i.e. **unadjusted, as-of-that-day**.

### The basis-break guard — `sources/combiners/scorer/db.py:17-25`

```python
# Basis-break guard bounds: the ledger stores each day's close on that day's
# price basis with no adjusted history to correct from, so a split shows up
# as a consecutive-date ratio near 1/2, 1/3, 2, 5, ... — outside these
# bounds. Multiplication (not division) so a zero prev-close flags
# conservatively. Sub-threshold splits (3:2, ratio 0.667) pass undetected —
# accepted residual, see docs/superpowers/specs/2026-07-06-scorer-basis-
# guard-design.md.
BASIS_BREAK_LO = 0.55  # forward splits >= 2:1 land below this
BASIS_BREAK_HI = 1.8  # reverse splits >= 1:2 land above this
```

There is a companion view `v_basis_breaks` (`scorer/db.py:310-320`) that lists
every consecutive-date move outside those bounds. **This view is your primary
verification instrument in this plan.**

### The proxies that need history — `sources/combiners/scorer/catalog.py:21-45`

```python
CROSSWALK_BENCHMARK: dict[str, str | None] = {
    # energy -> XLE
    "XLE": None, "XOM": "XLE", "CVX": "XLE", "USO": "XLE",
    # metals -> GLD
    "GLD": None, "GDX": "GLD", "SLV": "GLD", "FCX": "GLD", "COPX": "GLD",
    # ags + softs -> DBA
    "DBA": None, "CORN": "DBA", "SOYB": "DBA", "WEAT": "DBA",
    # rates -> TLT
    "TLT": None, "IEF": "TLT",
    # equity_index -> SPY
    "SPY": None, "QQQ": "SPY", "IWM": "SPY",
}
```

That is **18 tickers**. They are the entire scope of this plan's backfill. Do
not backfill the other ~11,000 symbols; see "Out of scope".

### The backtest's benchmark roster — `sources/combiners/backtest/catalog.py:27-33`

```python
# Asset-class proxy benchmarks copied from scorer.db's permanent price ledger
# (the only growing close history for these tickers). Deep history accrues over
# time -- until then an asset-class replay grades few/no rows, which is correct
# (degrades gracefully), not an error.
CLASS_BENCHMARKS: list[dict[str, Any]] = [
    {"symbol": "XLE", "db": SCORER_DB},  # energy proxy
]
```

### The decoder you will reuse — `sources/screeners/stock_analysis_screener/probe.py`

Public functions: `data_url(path)`, `fetch_data_json(path, timeout=60)`,
`decode_nodes(raw)`, `page_data(path)`, `summarize(value, ...)`, `main(argv)`.

`page_data(path)` fetches `https://stockanalysis.com{path}__data.json`, decodes
the `devalue` pool, and returns the page's decoded data structure.

It is runnable as a module (verified):

```
uv run python -m sources.screeners.stock_analysis_screener.probe /stocks/AAPL/statistics/
```

### Repo conventions you must match

- **Zero runtime third-party dependencies.** stdlib only (`urllib`, `sqlite3`,
  `json`, `argparse`). Do not add a dependency. `pytest`/`ruff`/`mypy` are
  dev-only.
- **Four-file package shape**: `fetch.py` (network + *pure* parsing),
  `db.py` (schema/writers/views), `run.py` (orchestration with injected seams),
  `catalog.py` (what to pull). Read
  `sources/combiners/backtest/fetch.py` and `sources/combiners/backtest/run.py`
  as your exemplar — `backtest` is the combiner most similar to what you're adding.
- **No network in tests.** Every `fetch.py` function takes a `get=`/`opener=`
  seam; every `run()` takes `fetch_*=` seams. Tests inject fakes. The suite is
  fully offline. Keep it that way.
- **Secret hygiene on errors.** On a per-item failure: `conn.rollback()` then
  print **only** `type(e).__name__` — never `str(e)`, `repr(e)`, or `e.url`.
  (A urllib `HTTPError` carries the request URL, which may embed an api_key.)
- **Timestamps UTC, calendar dates Phoenix.** Never slice a date out of a
  timestamp. Use `phx_date(now_iso)` from `sources/common/clock.py`. Not
  directly relevant here (history rows carry their own dates) but do not violate it.
- Column names from stockanalysis.com are camelCase and stay quoted in SQL
  (see `sources/combiners/advisor/fetch.py:83`).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests (full) | `uv run pytest` | all pass, ~700 tests, <1s |
| Tests (one file) | `uv run pytest tests/test_pricehistory_fetch.py` | all pass |
| Lint | `uv run ruff check` | exit 0 |
| Format check | `uv run ruff format --check` | exit 0 |
| Types | `uv run mypy` | exit 0 |
| Probe a route | `uv run python -m sources.screeners.stock_analysis_screener.probe <path>` | decoded structure printed |
| Read the ledger | `sqlite3 -readonly data/scorer.db "<sql>"` | rows |

All four gates (`ruff check`, `ruff format`, `mypy`, `pytest`) must pass before
any commit; the pre-commit hook in `.githooks/pre-commit` runs them.

## Scope

**In scope** (the only files you may create or modify):

- `sources/combiners/scorer/pricehistory.py` (create) — the backfill fetcher + CLI
- `sources/combiners/scorer/catalog.py` (modify) — add the backfill symbol list
- `sources/combiners/backtest/catalog.py` (modify) — extend `CLASS_BENCHMARKS`
- `tests/test_pricehistory_fetch.py` (create)
- `tests/test_pricehistory_run.py` (create)
- `registry.py` (modify) — register the new dispatcher name
- `tests/test_registry.py` (modify) — add the new name
- `docs/BACKLOG.md` (modify) — only to update the deferral note if step 6 succeeds
- `plans/README.md` (modify) — status row
- `plans/001-findings.md` (create) — the spike's written finding from step 1

**Out of scope** (do NOT touch, even though they look related):

- `sources/combiners/scorer/fetch.py` — the forward `harvest_prices` path is
  correct and load-bearing. Backfill is a *separate* entry point. Changing the
  nightly harvester risks the one working feeder.
- `sources/combiners/scorer/run.py` — do **not** wire backfill into the nightly
  scorer run. Backfill is a manual, one-shot operation (like `ftd --full`).
- `sources/combiners/scorer/db.py` — do not change `insert_prices`, the
  `prices` schema, `BASIS_BREAK_LO/HI`, or any view. You are a *writer* into an
  existing table via the existing function.
- **Backfilling more than the 18 `CROSSWALK_BENCHMARK` tickers.** ~11,000
  symbols × years of history is a hammering of an unofficial endpoint that
  `CLAUDE.md` explicitly warns against ("stockanalysis.com is an unofficial
  endpoint; don't hammer it"). Ticker-grain backfill is a separate, later plan.
- `deploy/launchd/install.py` — do not add a scheduled job. This is manual.

## Git workflow

- Branch: `advisor/001-price-ledger-backfill`
- Conventional commits, lowercase, scoped — matching `git log`:
  `feat(scorer): backfill the price ledger from stockanalysis history`
- Commit per step or per logical unit.
- Do **not** add a Co-Authored-By trailer (user's global instruction).
- Do **not** push or open a PR.

## Steps

### Step 1 (SPIKE — do this first, write down the answer): determine the adjustment basis of `/stocks/{T}/history/`

This decides whether the rest of the plan is safe.

Pick a symbol with a large, recent, unambiguous split. **NVDA had a 10-for-1
split effective 2024-06-10.** Its pre-split close on 2024-06-07 was roughly
**\$1,208**; the split-adjusted equivalent is roughly **\$120.8**.

Fetch and inspect:

```
uv run python -m sources.screeners.stock_analysis_screener.probe /stocks/NVDA/history/
```

If that route's payload is not directly readable, write a throwaway script (do
not commit it) that calls `probe.page_data("/stocks/NVDA/history/")` and prints
the first few bars plus the keys of a bar object. You are looking for the
`{o,h,l,c,a,v,t,ch}` bar shape documented at
`docs/stockanalysis_data_json_catalog.md:68`.

Answer these four questions and **write them into `plans/001-findings.md`**:

1. What is the exact decoded shape? (list of dicts? dict of arrays? what is `t` —
   epoch seconds, ms, or an ISO date string?)
2. Does the route return the full history by default, or does it need a range
   parameter? If a parameter is needed, what is it? (The page UI shows a "6M"
   selector; query params carry through to `__data.json`.)
3. **The load-bearing question**: for `t` = 2024-06-07, is `c` ≈ 1208
   (unadjusted) or ≈ 120.8 (split-adjusted)? And what is `a` at that date?
4. How many bars come back for a full-history request, and what is the oldest `t`?

**Decision rule** — record which branch you took:

- If **`c` is unadjusted** (≈1208): `c` matches the forward feeder's basis.
  Use `c`. Proceed to step 2 as written.
- If **`c` is split-adjusted** (≈120.8) and `a` is also adjusted: **neither
  column matches the forward feeder's basis for symbols that split.** This is a
  STOP condition — see STOP conditions. Do not "just use `c` anyway".

> Why this is not paranoia: the ledger has no adjusted history to correct from
> (`scorer/db.py:17-25`). Mixing bases within one symbol's series makes
> `entry_close` and `exit_close` incomparable, which silently corrupts every
> `fwd_return` computed across the seam. `INSERT OR IGNORE` guarantees the
> corruption is *permanent* — existing rows win, so you cannot fix it by
> re-running.

**Verify**: `plans/001-findings.md` exists and answers all four questions with
concrete observed values (not guesses). Print the actual bar you inspected.

### Step 2: add the backfill symbol list to `sources/combiners/scorer/catalog.py`

Append a module-level constant. Derive it from `CROSSWALK_BENCHMARK` rather than
retyping the tickers, so the two can never drift:

```python
# One-shot historical backfill roster for `main.py pricehistory` (plan 001).
# Exactly the crosswalk proxies and their fan-out tickers: these are the only
# symbols the scorer benchmarks against and the backtest replays against, so
# they are the only ones whose history the ledger needs deep. Ticker-grain
# backfill (the ~11k screener universe) is deliberately NOT here — see
# docs/BACKLOG.md.
BACKFILL_SYMBOLS: tuple[str, ...] = tuple(sorted(CROSSWALK_BENCHMARK))
```

**Verify**:
```
uv run python -c "from sources.combiners.scorer.catalog import BACKFILL_SYMBOLS as B; print(len(B), B[:4])"
```
→ prints `18` and a sorted tuple beginning with `('CORN', 'COPX', 'CVX', 'DBA')`.

### Step 3: write `sources/combiners/scorer/pricehistory.py` — fetch + pure parse

Two layers, strictly separated (this is the repo's `fetch.py` contract):

```python
def parse_history(payload) -> list[tuple[str, float]]:
    """Pure. (price_date, close) pairs from one decoded /history/ payload.
    price_date is YYYY-MM-DD. Rows with a null close are dropped, never
    defaulted. Sorted ascending by date."""

def fetch_history(symbol: str, get=...) -> list[tuple[str, float]]:
    """Network. `get` is the injectable seam: a callable taking the route
    path and returning the decoded payload. Defaults to probe.page_data."""
```

Requirements:

- `get=` **must** default to `probe.page_data` and be overridable. Tests inject
  a fake; no test may touch the network.
- Use the column determined in step 1 (`c` or `a`), and put a one-line comment
  naming *which* and *why*, citing the finding.
- Convert `t` to a `YYYY-MM-DD` string. If `t` is epoch seconds, use
  `datetime.fromtimestamp(t, tz=UTC).date().isoformat()`. **Do not** use naive
  `datetime.fromtimestamp`.
- Be a polite client. Between symbols, sleep. Reuse
  `sources/common/http_client.py`'s `RateLimiter` if it fits; otherwise a plain
  `time.sleep(1.0)` between symbols is acceptable and must be injectable
  (`sleep=time.sleep`) so tests run instantly.
- Set a real `User-Agent` (probe.py already does).

**Verify**: `uv run mypy` → exit 0. `uv run ruff check` → exit 0.

### Step 4: write the `run(...)` + `main(argv)` orchestration in the same module

Follow `sources/combiners/backtest/run.py` for shape.

```python
def run(db_path, symbols, *, fetch_history=fetch_history, sleep=time.sleep) -> tuple[int, int, list[str]]:
    """Returns (symbols_ok, rows_inserted, failed_symbols)."""
```

Requirements:

- Open with `sources.combiners.scorer.db.connect(db_path)` and call that
  module's `ensure_schema` before writing.
- Write **only** through `sources.combiners.scorer.db.insert_prices`. Do not
  hand-roll the INSERT.
- **Skip-and-continue per symbol**, matching every other source: wrap each
  symbol in `try/except Exception`, `conn.rollback()`, print
  `f"FAILED {symbol}: {type(e).__name__}"`, append to `failed`, continue.
  Never print `str(e)` / `repr(e)` / `e.url`.
- `main(argv)` is a thin argparse wrapper with:
  - `--db` (default `scorer.db`; note `CLAUDE.md` warns every `--db` default is
    a bare cwd-relative filename — the operator must pass `data/scorer.db`)
  - `--only` / `--exclude` selection over `BACKFILL_SYMBOLS`
  - `--dry-run` that fetches and reports counts but writes nothing
- Print a final line: `pricehistory: N symbols, M rows inserted, K failed`.

Register it in `registry.py` under the name `pricehistory`, and add that name
to `tests/test_registry.py`.

**Verify**:
```
uv run python main.py --list | grep pricehistory
```
→ prints `pricehistory`.

### Step 5: write the tests

Create `tests/test_pricehistory_fetch.py` and `tests/test_pricehistory_run.py`.
Model them structurally on `tests/test_backtest_fetch.py` and
`tests/test_backtest_run.py`.

`tests/test_pricehistory_fetch.py` — all offline, fake payloads:

- `test_parse_history_returns_sorted_date_close_pairs`
- `test_parse_history_drops_null_close_rather_than_defaulting`
- `test_parse_history_converts_epoch_to_iso_date` (pin the exact expected date;
  if `t` is epoch seconds this catches a timezone-off-by-one)
- `test_fetch_history_uses_injected_get_seam` (assert the fake `get` was called
  with the expected route path; assert no network)

`tests/test_pricehistory_run.py` — against a `tmp_path` sqlite file:

- `test_run_inserts_rows_into_prices`
- `test_run_is_idempotent` — run twice, assert the second run inserts **0** rows
  (proves `INSERT OR IGNORE` semantics hold and re-running is safe)
- `test_run_never_overwrites_an_existing_forward_row` — pre-insert
  `('XLE', '2026-07-07', 999.0)`, backfill a different close for that date,
  assert the value is still `999.0`
- `test_run_skips_and_continues_on_one_symbol_failure` — one symbol's fetch
  raises; assert the other symbols still land and the failed symbol is returned
- `test_run_failure_message_does_not_leak_exception_text` — raise
  `Exception("secret-token-in-url")`; assert `"secret-token-in-url"` is not in
  captured stdout

**Verify**: `uv run pytest tests/test_pricehistory_fetch.py tests/test_pricehistory_run.py` → all pass.

### Step 6: run the real backfill, then verify the ledger did not break

This is the only step that touches the operator's real `data/scorer.db`.
**Back it up first** — the table is permanent and `INSERT OR IGNORE` makes bad
rows unfixable by re-running:

```
cp data/scorer.db data/scorer.db.pre-001-backup
```

Dry run first:

```
uv run python main.py pricehistory --db data/scorer.db --dry-run
```

Then the real run:

```
uv run python main.py pricehistory --db data/scorer.db
```

Now verify, in order. **Every one of these must hold.**

1. Depth arrived:
```
sqlite3 -readonly data/scorer.db "SELECT symbol, COUNT(*) n, MIN(price_date), MAX(price_date) FROM prices WHERE symbol IN ('SPY','XLE','GLD','DBA','TLT') GROUP BY symbol;"
```
→ five rows, each with `n` in the thousands and `MIN(price_date)` years in the past.

2. **No basis breaks were introduced** in the backfilled symbols:
```
sqlite3 -readonly data/scorer.db "SELECT symbol, COUNT(*) FROM v_basis_breaks WHERE symbol IN (SELECT DISTINCT symbol FROM prices) GROUP BY symbol ORDER BY 2 DESC LIMIT 20;"
```
→ For the 18 backfilled symbols, expect **zero or a small number of rows that
correspond to genuine historical splits or reverse-splits** of that ETF. A
backfilled symbol showing a break at the *seam* — i.e. a break whose
`price_date` is within the last week — means the backfilled basis disagrees with
the forward-harvested basis. **That is a STOP condition.** Check explicitly:
```
sqlite3 -readonly data/scorer.db "SELECT * FROM v_basis_breaks WHERE price_date >= date('now','-14 days');"
```
→ must return **0 rows**.

3. Pre-existing forward rows were preserved (spot-check one):
```
sqlite3 -readonly data/scorer.db "SELECT * FROM prices WHERE symbol='SPY' AND price_date='2026-07-07';"
```
→ still present, with its original close.

### Step 7: extend the backtest's benchmark roster and confirm the `eia_*` replay lights up

In `sources/combiners/backtest/catalog.py`, extend `CLASS_BENCHMARKS` to the
four proxies the backlog's recipe names, and update the stale comment:

```python
# Asset-class proxy benchmarks copied from scorer.db's permanent price ledger.
# Backfilled to full history by `main.py pricehistory` (plan 001), so an
# asset-class replay now grades against real depth rather than a few days.
CLASS_BENCHMARKS: list[dict[str, Any]] = [
    {"symbol": "XLE", "db": SCORER_DB},  # energy proxy
    {"symbol": "GLD", "db": SCORER_DB},  # metals proxy
    {"symbol": "DBA", "db": SCORER_DB},  # ags + softs proxy
    {"symbol": "TLT", "db": SCORER_DB},  # rates proxy
]
```

Re-run the backtest and confirm the previously-empty `eia_*` grading now
produces rows:

```
uv run python main.py backtest --db data/backtest.db
sqlite3 -readonly data/backtest.db "SELECT signal_id, benchmark, COUNT(*) FROM v_replay_efficacy GROUP BY 1,2 ORDER BY 1;"
```
→ rows for `eia_crude_stocks` and `eia_natgas_storage` against benchmark `XLE`,
where before there were none. The seven SP500-graded signals must **still** be
present (regression check — compare against the 60 rows `v_replay_efficacy` had
before this plan).

If `eia_*` still grades zero rows, do **not** start editing view SQL. Stop and
report: the cause is upstream (either the backfill didn't cover the graded date
range, or the `eia_*` signal history in `backtest.db` is itself shallow), and
diagnosing it is a separate task.

### Step 8: update `docs/BACKLOG.md`

The CFTC deferral note gives two reasons. Reason 1 ("Data availability") is now
resolved for the proxy benchmarks. Edit **only** that reason to record that
step 1 of the build recipe is done, naming `main.py pricehistory`. Leave reason 2
("Unvalidatable-now complexity" — the as-of rolling percentile) exactly as
written; this plan does not touch it.

Do not delete the backlog entry. The CFTC tranche remains deferred.

## Test plan

New tests, listed in step 5. In summary:

- `tests/test_pricehistory_fetch.py` — 4 tests: parse shape, null handling,
  date conversion, injected seam.
- `tests/test_pricehistory_run.py` — 5 tests: insert, idempotence, no-overwrite,
  skip-and-continue, no exception-text leak.

Structural pattern: `tests/test_backtest_fetch.py` / `tests/test_backtest_run.py`.

All offline. No test may perform a network call. If you find yourself wanting to
hit stockanalysis.com from a test, you have mis-wired the `get=` seam.

**Verify**: `uv run pytest` → all pass, 9 new tests, no net-new failures.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `plans/001-findings.md` exists and answers step 1's four questions with observed values
- [ ] `uv run ruff check` exits 0
- [ ] `uv run ruff format --check` exits 0
- [ ] `uv run mypy` exits 0
- [ ] `uv run pytest` exits 0, with 9 new tests passing
- [ ] `uv run python main.py --list | grep -c pricehistory` → `1`
- [ ] `sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM prices WHERE symbol='XLE'"` → > 1000
- [ ] `sqlite3 -readonly data/scorer.db "SELECT COUNT(*) FROM v_basis_breaks WHERE price_date >= date('now','-14 days')"` → `0`
- [ ] `sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM v_replay_efficacy WHERE signal_id LIKE 'eia_%'"` → > 0
- [ ] `sqlite3 -readonly data/backtest.db "SELECT COUNT(*) FROM v_replay_efficacy"` → >= 60 (no regression)
- [ ] `git status` shows no modified files outside the In-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- **Step 1 finds `c` is split-adjusted.** Do not backfill. Report the finding
  and the value of `a` at the split date. Resolving this needs a design decision
  (e.g. store an `adjusted` flag column, or backfill only never-split ETFs, or
  reconcile the seam) that is above this plan's authority and would change the
  `prices` schema — which is explicitly out of scope.
- **Step 6 check 2 finds any `v_basis_breaks` row within the last 14 days.**
  This means the backfilled basis disagrees with the forward-harvested basis at
  the seam. Restore `data/scorer.db.pre-001-backup` and report.
- The `/stocks/{T}/history/` route returns something other than the documented
  `{o,h,l,c,a,v,t,ch}` bar shape, or `probe.page_data` fails to decode it. (The
  documented shape may have drifted; `CLAUDE.md`'s "live-verify source schemas"
  invariant applies.)
- stockanalysis.com returns HTTP 403/429 for more than 2 of the 18 symbols. You
  are being rate-limited. Do not add retries or reduce the sleep — report.
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching `scorer/db.py`, `scorer/fetch.py`, or
  `scorer/run.py`.
- You discover the assumption **"`prices` is append-only and never pruned"** is
  false. (Check: `scorer/db.py`'s `prune` docstring. If prune deletes price
  rows, the whole backfill is pointless.)

## Maintenance notes

For the human/agent who owns this after it lands:

- **The seam is the permanent hazard.** This ledger now contains rows from two
  writers with potentially different bases: historical (backfill) and forward
  (`harvest_prices`). Any future symbol that splits will create a genuine break.
  `v_basis_breaks` is the audit trail; the scorer's `mature()` already holds
  affected rows pending. Watch it after every corporate action in the 18 proxies.
- **Ticker VII is already poisoned.** Before this plan,
  `SELECT * FROM prices WHERE symbol='VII'` returns 4 rows dated `2018-07-11`,
  inherited from a stale `priceDate` in `stocks.db.metrics`. The ledger trusts
  the source's `priceDate` blindly. This is pre-existing, out of scope here, and
  worth a separate small fix — it demonstrates the class of bug a wider backfill
  would amplify.
- **What a reviewer should scrutinize**: (1) that `insert_prices` was reused and
  not re-implemented; (2) that the `get=` seam really is injected and no test
  hits the network; (3) the date-conversion test's expected value, which is
  where a UTC/local off-by-one would hide; (4) that `--dry-run` truly writes nothing.
- **Explicitly deferred out of this plan**: backfilling the ~11,000-symbol
  ticker universe (needed for the ticker-grain forward-return spine, which would
  unlock `si_days_to_cover`, `si_spike`, `sv_ratio_spike`, `ftd_persistent`,
  `stocks_rsi`, `reddit_trending`). That is a much larger job with a real
  rate-limit budget question, and it should not be attempted until this
  18-symbol backfill has run cleanly for a few weeks. It is the natural
  follow-on and the biggest remaining prize.
- Once efficacy rows accumulate, `v_signal_recommendation` (already rendered by
  `deploy/launchd/dashboard.py:547`) starts saying something. Re-weighting the
  composite catalog remains a **human** decision by design — do not automate it.
