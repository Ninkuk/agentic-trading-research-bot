# Plan 000: Harvest the actual close, not the previous close — and rebuild the ledger

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**:
> `git diff --stat 5c14446..HEAD -- sources/combiners/scorer sources/combiners/advisor`

## Status

- **Priority**: P0 — blocks 001, and silently corrupts 003
- **Effort**: M
- **Risk**: MED (rewrites a permanent, never-pruned table)
- **Depends on**: none. **Blocks**: 001, 003.
- **Category**: bug
- **Planned at**: commit `5c14446`, 2026-07-09
- **Found by**: the step-1 spike of plan 001

## Why this matters

`sources/combiners/scorer/fetch.py:12` harvests the permanent price ledger with:

```sql
SELECT DISTINCT symbol, "priceDate", "close" FROM src.metrics
```

**`close` is not the close for `priceDate`.** It is the *previous session's*
close. This repo's own reverse-engineered field catalog says so at
`docs/stockanalysis_data_json_catalog.md:190-197`:

| field | documented meaning |
|---|---|
| `price` | Stock Price |
| `close` | **Previous Close** |

Verified empirically against two independent sources. For `SPY`:

| `priceDate` | `metrics.close` | `metrics.price` | true close (CBOE + stockanalysis history) |
|---|---|---|---|
| 2026-07-02 | 745.76 | **744.78** | 744.78 |
| 2026-07-06 | 744.78 | **751.28** | 751.28 |
| 2026-07-07 | 751.28 | **747.71** | 747.71 |
| 2026-07-08 | 747.71 | **745.40** | 745.40 |

`metrics.close` matched the true close 0/6 times; `metrics.price` matched 6/6.

So every row in `scorer.db.prices` holds a real close stamped with the **next
trading day's date**.

### Consequence 1 — the look-ahead the code was written to prevent

`entry_for()` (`scorer/db.py:488-501`) deliberately selects the first close
*strictly after* `composite_date`. Its docstring:

> The composite forms its opinion at 9:05pm using data through that day's
> close, so entering at that same close would silently pocket the overnight gap
> (look-ahead).

But the row it selects — dated `D+1` — actually contains **`D`'s close**. The
scorer therefore enters every position at the close of the day the opinion was
formed. It has exactly the look-ahead bias it was designed to avoid. No test
caught this: the offline fixtures generate their own internally-consistent
prices, so the mislabeling is invisible to them.

### Consequence 2 — the advisor is a session stale

`sources/combiners/advisor/fetch.py:83` reads the same `"close"` column into
`metrics[symbol]["close"]`, consumed at `advisor/db.py:198` (`build_position_heat`)
and `advisor/db.py:266` (`build_size_caps`). Every `price`, `heat_dollars`,
`weight_pct`, and `cap_dollars` is computed from the prior session's close.

### Consequence 3 — it silently breaks plan 001

Plan 001 backfills true closes from the history endpoint. Written into a ledger
whose existing rows are shifted one session, every symbol would get a systematic
mismatch at the seam — and `v_basis_breaks` would **not** catch it, because two
adjacent closes have a ratio near 1.0, well inside `BASIS_BREAK_LO=0.55` /
`BASIS_BREAK_HI=1.8`.

### Why now

Nothing has matured. `SELECT COUNT(*) FROM v_signal_efficacy` → 0.

| table | rows | matured |
|---|---|---|
| `signal_outcomes` | 4,857 | 0 |
| `ticker_outcomes` | 4,533 | 0 |
| `regime_outcomes` | 3 | 0 |

No conclusion has ever been drawn from this data. `prices` is 33,061 rows over
23 dates. `prices` and the outcome tables are **permanent and never pruned**
(`scorer/db.py:1-5`), so this is the cheapest moment this bug will ever be
fixable.

## Current state

### The bug site — `sources/combiners/scorer/fetch.py:7-14`

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

### The second bug site — `sources/combiners/advisor/fetch.py:73-87`

```python
def read_metrics(conn, symbols) -> dict:
    """symbol -> {atr, close, price_date} from a price DB's v_latest.
    Column names are stockanalysis.com camelCase — keep them quoted."""
    ...
            f'SELECT symbol, "atr", "close", "priceDate" FROM src.v_latest'
```

### The ledger is append-only — `sources/combiners/scorer/db.py:475-485`

`insert_prices` uses `INSERT OR IGNORE`. **Existing rows always win**, so simply
fixing the column and re-running the nightly job does *nothing* — the wrong rows
are already there and will be preferred forever. A rebuild must explicitly
`DELETE` first.

### Re-registration is gated — `sources/combiners/scorer/db.py:672`

```python
return {r[0] for r in conn.execute("SELECT composite_snapshot_id FROM registered_snapshots")}
```

A composite snapshot already present in `registered_snapshots` is never
re-registered. So clearing the bad outcome rows also requires clearing their
`registered_snapshots` rows.

Note `registered_snapshots` carries `CREATE UNIQUE INDEX idx_owner_window ON
registered_snapshots (entry_date) WHERE ticker_rows > 0` — deletion is fine;
re-insertion must not collide.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Tests | `uv run pytest` | all pass |
| Lint | `uv run ruff check` | exit 0 |
| Format | `uv run ruff format --check` | exit 0 |
| Types | `uv run mypy` | exit 0 |
| Rebuild | `uv run python main.py scorer --db data/scorer.db --db-dir data --rebuild-prices` | prints rebuild + harvest counts |

## Scope

**In scope**:
- `sources/combiners/scorer/fetch.py` — harvest `"price"`
- `sources/combiners/advisor/fetch.py` — read `"price"`
- `sources/combiners/scorer/db.py` — add `rebuild_prices()`
- `sources/combiners/scorer/run.py` — add `--rebuild-prices` flag
- `tests/test_scorer_fetch.py`, `tests/test_scorer_db_write.py`,
  `tests/test_scorer_run.py`, `tests/test_advisor_fetch.py` — regression tests
- `docs/stockanalysis_data_json_catalog.md` — flag the trap inline
- `plans/README.md`

**Out of scope**:
- `stocks.db` / `etfs.db` schemas — `metrics` correctly stores *both* fields;
  the screener is right, the consumer was wrong.
- `insert_prices`, the `prices` schema, `BASIS_BREAK_*`, `entry_for` — all correct.
- `decisions` / `journal_runs` — fill prices come from the broker, not the ledger.
- Any composite/backtest file.

## Steps

### Step 1: fix `harvest_prices`

```python
def harvest_prices(conn) -> list:
    """(symbol, price_date, close) across ALL retained source snapshots.

    Reads "price", NOT "close". stockanalysis.com's screener names these
    fields from a live-quote perspective: `price` is the last close for
    `priceDate`, and `close` is the PREVIOUS session's close (see
    docs/stockanalysis_data_json_catalog.md:190-197). Harvesting "close"
    stamped every close with the NEXT trading day's date, which handed
    entry_for() the composite date's own close and reintroduced exactly the
    overnight look-ahead that function exists to prevent.

    INSERT OR IGNORE downstream dedupes, and re-harvesting nightly self-heals
    ledger gaps within the source's retention window.
    """
    return conn.execute(
        'SELECT DISTINCT symbol, "priceDate", "price" FROM src.metrics'
        ' WHERE "priceDate" IS NOT NULL AND "price" IS NOT NULL'
    ).fetchall()
```

### Step 2: fix `advisor.read_metrics`

Select `"price"`. Keep the returned dict key `close` — it *is* the closing price
for `price_date`, and two call sites (`advisor/db.py:198,266`) depend on the key.
Add the same warning comment.

### Step 3: add `rebuild_prices()` to `scorer/db.py`

```python
def rebuild_prices(conn) -> tuple[int, int, int]:
    """Destructive, one-shot repair for the off-by-one-session ledger.

    prices is INSERT OR IGNORE, so a corrected harvester cannot overwrite the
    bad rows — they must be deleted. Unmatured outcome rows hold entry_close
    values read from those bad rows, so they are deleted too and re-register
    on the next run. Their registered_snapshots gate rows go with them.

    REFUSES to run if any outcome row has matured: a matured row's forward
    return was computed from mislabeled closes and cannot be silently repaired.
    Returns (prices_deleted, outcomes_deleted, registrations_deleted).
    """
```

It must:
1. Count matured rows across `signal_outcomes`, `ticker_outcomes`,
   `regime_outcomes`. If **any** is non-zero, `raise RuntimeError` naming the
   counts. Do not proceed.
2. `DELETE FROM prices`.
3. `DELETE FROM {signal,ticker,regime}_outcomes WHERE matured_at IS NULL`.
4. `DELETE FROM registered_snapshots` for `composite_snapshot_id`s that now have
   no surviving outcome rows in any of the three tables.
5. Single transaction; commit once.

### Step 4: add `--rebuild-prices` to `scorer/run.py`

A flag on `main(argv)`, threaded to `run(...)` as a keyword. When set, call
`db.rebuild_prices(conn)` **after** `ensure_schema` and **before** the harvest
loop, and print the three counts. Default off. Never scheduled.

### Step 5: regression tests

These must fail against the old code. That is the point.

`tests/test_scorer_fetch.py`:
- `test_harvest_prices_reads_price_not_close` — build a fake `src.metrics` where
  `close = 100.0` and `price = 101.0` for one `priceDate`; assert the harvested
  tuple carries `101.0`. **This is the test that would have caught the bug.**
- `test_harvest_prices_skips_null_price`

`tests/test_advisor_fetch.py`:
- `test_read_metrics_reads_price_not_close` — same shape, via `v_latest`.

`tests/test_scorer_db_write.py`:
- `test_rebuild_prices_deletes_prices_and_unmatured_outcomes`
- `test_rebuild_prices_refuses_when_any_outcome_matured` — assert `RuntimeError`
- `test_rebuild_prices_keeps_registrations_with_matured_rows`

`tests/test_scorer_run.py`:
- `test_run_with_rebuild_reharvests_corrected_prices` — seed the ledger with a
  wrong row, run with `rebuild_prices=True`, assert the corrected value replaced it.

### Step 6: document the trap

In `docs/stockanalysis_data_json_catalog.md`, next to the `close` row, add a
bold warning that `close` is Previous Close and that `price` is the close for
`priceDate` — citing this plan.

### Step 7: back up, rebuild, verify against an independent source

> ⚠️ **`cp` is not a safe backup for this DB.** `scorer.db` is in WAL mode and
> routinely carries megabytes of uncheckpointed `-wal`. `cp` of the main file
> alone can yield a database with **zero rows** (measured 2026-07-09: main 4.1 MB,
> `-wal` 7.7 MB, `cp`-copy `SELECT COUNT(*) FROM prices` → `0`). The backup taken
> during this plan's execution happened to be valid only because the WAL was
> checkpointed at that moment. Use `.backup`.

```
BK="data/scorer.db.bak-$(date +%Y%m%dT%H%M%S)"
sqlite3 data/scorer.db ".backup '$BK'"
sqlite3 -readonly "$BK" "SELECT COUNT(*) FROM prices;"   # must NOT be 0
uv run python main.py scorer --db data/scorer.db --db-dir data --rebuild-prices
```

Verify the corrected ledger against **CBOE** (`options.db`, an entirely separate
feed):

```
sqlite3 -readonly data/scorer.db "ATTACH 'file:data/options.db?mode=ro' AS o;
SELECT p.price_date, p.close AS ledger, u.close AS cboe,
       ROUND(p.close - u.close, 4) AS diff
FROM prices p JOIN o.underlying_daily u
  ON u.underlying = p.symbol AND u.snapshot_date = p.price_date
WHERE p.symbol = 'SPY' ORDER BY p.price_date;"
```
→ every `diff` must be `0.0`.

## Done criteria

- [ ] `uv run ruff check` / `ruff format --check` / `mypy` all exit 0
- [ ] `uv run pytest` exits 0 with the new regression tests passing
- [ ] `grep -c '"close"' sources/combiners/scorer/fetch.py` → `0`
- [ ] The SPY ledger-vs-CBOE diff query returns all `0.0`
- [ ] `sqlite3 data/scorer.db "SELECT COUNT(*) FROM signal_outcomes WHERE matured_at IS NOT NULL"` → `0` (nothing was destroyed that had matured)
- [ ] A backup file `data/scorer.db.bak-*` exists
- [ ] `git status` shows no files outside the in-scope list

## STOP conditions

- Any outcome row has `matured_at IS NOT NULL` before the rebuild. Then real
  results were computed from bad closes; report and stop — the repair is a
  larger conversation.
- The ledger-vs-CBOE diff is non-zero after the rebuild.
- `metrics.price` is NULL for a material fraction of symbols (check first:
  `SELECT COUNT(*) FROM metrics WHERE "price" IS NULL`). If `price` is sparse
  where `close` was dense, the fix trades one bug for data loss — report.
- You find a third consumer of `metrics."close"` outside scorer/advisor.

## Deviation from plan, discovered during execution

The plan specified one rule ("read `price`, not `close`"). Executing it surfaced
a **second, dependent bug** that the plan did not anticipate, and the fix is
incomplete without it.

`close` names a *finished* session, so it is settled by construction. `price`
names the *current* session, so a snapshot captured before settlement reports an
unsettled value. Measured on real data: the `stocks.db` snapshot captured
`2026-07-09T05:12Z` (= 21:12 Phoenix on 07-08) reported `NVDA price = 201.01`
for `priceDate = 2026-07-08`, while the true close was `204.12` (CBOE and the
`/history/` endpoint agree). 15 of the 24 optionable underlyings were wrong the
same way. Rule 1 alone therefore traded a systematic one-day shift for a
sporadic same-day error.

`harvest_prices` now applies **rule 2**: only harvest a `priceDate` from a
snapshot captured on a strictly later **Phoenix** calendar day. It also uses
`MIN(snapshot_id)` to make the pick deterministic when several settled snapshots
carry the same `priceDate` — `SELECT DISTINCT` left `INSERT OR IGNORE` to freeze
whichever row the scan yielded first (186 such ambiguous pairs existed in
`stocks.db`).

Measured against CBOE, an entirely independent feed:

| harvest rule | rows compared | agree | disagree |
|---|---|---|---|
| `close` (original) | 88 | 73 | 15 |
| `price`, all snapshots | 76 | 61 | 15 |
| `price`, settled-only (**shipped**) | 66 | **66** | **0** |

Basis breaks in the real ledger fell from **89 to 26**, and the surviving 26 are
genuine corporate actions (e.g. `CRIS 0.3466 → 5.94`, a reverse split).

A third guard was added: SQLite resolves an unknown double-quoted identifier to a
**string literal**, so a `metrics` table without a `price` column would have
harvested the text `'price'` into the permanent ledger. `harvest_prices` now
raises instead, and `run()` skips that source loudly.

## Maintenance notes

- **The nightly job must never pass `--rebuild-prices`.** It is a one-shot repair.
- **Rule 2 makes the ledger lag by one session.** A `priceDate` is only harvested
  once a later Phoenix day's snapshot exists. The nightly `preopen` job (4:00am
  Phoenix) supplies exactly that, so steady-state lag is one calendar day — which
  is what `entry_for`'s next-day-entry contract already assumes. An intraday
  `stocks` run can never poison the ledger.
- After this lands, plan 001's basis question resolves cleanly: the history
  endpoint's `c` equals `metrics.price` for the same date (verified on SPY/XLE
  2026-07-08), so backfilled history and forward harvest agree.
- The history endpoint's `c` **is** retroactively split-adjusted (NVDA 2024-06-07
  reads 120.888, not ~1208.88). That is benign for backfill — the series is
  internally consistent — but a split *after* backfill will break the seam, which
  is what `v_basis_breaks` and the pending-hold in `mature()` exist to catch.
- The class of bug: a field named `close` that means "previous close". Any new
  consumer of `metrics` should check the catalog doc before trusting a field name.