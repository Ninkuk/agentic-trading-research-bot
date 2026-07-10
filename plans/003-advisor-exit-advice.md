# Plan 003: Give the advisor an exit side — ATR stop distances and trim suggestions for held positions

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 5c14446..HEAD -- sources/combiners/advisor sources/screeners/portfolio_screener`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `5c14446`, 2026-07-08

## Why this matters

The `advisor` combiner answers "how much should I buy?" and then goes silent.
It computes a vol-scaled size cap for every bullish flag, and for bearish flags
it emits a row with a `NULL` cap and no further advice —
`sources/combiners/advisor/db.py:246-249` says so explicitly:

```
Bearish flags carry NULL caps: the book is long-only, so the
row itself (direction, score, group) is the advice, never a buy size.
```

Likewise `v_disagreements` surfaces every held position that today's composite
now scores negative — and stops there. It tells you the thesis broke. It does
not tell you what to do about it.

So the human gets help with entry, which is the easy half, and is entirely on
their own for exit, which is the hard and emotional half.

This is worth doing because it is **disproportionately cheap**. Every input a
stop or a trim needs is *already joined into one table*, once per snapshot, by
code that already runs:

- `position_heat` has `symbol, quantity, market_value, atr, price, price_date,
  heat_dollars, heat_pct, weight_pct, score_sum, bullish, bearish, total,
  atr_stale, group_name` (`advisor/db.py:30-48`).

The only missing input is `avg_cost`, which **exists in `portfolio.db` but is
not read** — `advisor/fetch.py:66-70` selects `symbol, quantity, market_value`
and drops it. That one column is what separates "you are down 12% from entry"
from "the score turned negative".

When this lands, the advisor emits, per held position: an ATR-based stop
distance, the distance from that stop to the current price, and — when the
composite strongly disagrees with a holding — a suggested trim size, expressed
the same vol-scaled way `size_caps` expresses entries.

**This stays inside the project's hard invariant**: decision support, never
order generation. It writes rows to a SQLite view. It does not place, size, or
transmit an order, and it must not.

## Current state

### The advisor's own docstring — `sources/combiners/advisor/db.py:1-6`

```python
"""advisor.db: snapshot-scoped sizing/risk advice — per-position ATR heat,
composite disagreements, and vol-scaled size caps. Everything cascades on
prune; the permanent record lives upstream (scorer.db), not here.

Heat/cap math is pure Python (build_* helpers) because it joins data already
fetched from four source DBs; views only scope and aggregate."""
```

Two rules to obey: **math in Python `build_*` helpers, aggregation in views**,
and **nothing here is permanent** (everything cascades on prune).

### `position_heat` — the table you will read from — `advisor/db.py:30-48`

```sql
CREATE TABLE IF NOT EXISTS position_heat (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    group_name   TEXT,
    quantity     REAL NOT NULL,
    market_value REAL,
    atr          REAL,
    price        REAL,
    price_date   TEXT,
    heat_dollars REAL,
    heat_pct     REAL,
    weight_pct   REAL,
    score_sum    INTEGER,
    bullish      INTEGER,
    bearish      INTEGER,
    total        INTEGER,
    atr_stale    INTEGER,
    PRIMARY KEY (snapshot_id, symbol)
);
```

Note: **no `avg_cost`.** That is the gap you close in step 1.

### `v_disagreements` — the trigger — `advisor/db.py:111-117`

```sql
-- Holdings today's composite scores negative (long book: bearish evidence
-- against something held). strong mirrors composite v_flagged thresholds.
DROP VIEW IF EXISTS v_disagreements;
CREATE VIEW v_disagreements AS
SELECT *, (score_sum <= -{STRONG_MIN_ABS_SCORE} AND total >= {STRONG_MIN_TOTAL}) AS strong
FROM v_latest_heat
WHERE score_sum < 0;
```

With, at `advisor/db.py:11-15`:

```python
# Strong-disagreement thresholds, mirroring composite v_flagged
# (|score_sum| >= 4 AND total >= 3). A schema test pins these to
# composite.db's view text so the two drift together.
STRONG_MIN_ABS_SCORE = 4
STRONG_MIN_TOTAL = 3
```

**Do not restate those thresholds anywhere new.** Reuse the constants.

### The reader that drops `avg_cost` — `advisor/fetch.py:66-70`

```python
def read_positions(conn) -> list:
    return [
        {"symbol": r[0], "quantity": r[1], "market_value": r[2]}
        for r in conn.execute("SELECT symbol, quantity, market_value FROM src.v_latest_positions")
    ]
```

### The source column that exists — `sources/screeners/portfolio_screener/db.py:27-34`

```sql
CREATE TABLE IF NOT EXISTS positions (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    quantity     REAL NOT NULL,
    avg_cost     REAL,
    market_value REAL,
    PRIMARY KEY (snapshot_id, symbol)
);
```

`avg_cost` is nullable. Your code must treat `NULL` as "unknown entry", not as 0.

`v_latest_positions` is `SELECT p.* FROM positions p WHERE p.snapshot_id = (…latest…)`,
so it already exposes `avg_cost`. Only the reader's SELECT list needs widening.

### The existing cap math you will mirror — `advisor/db.py:242-254`

```python
    """One row per flagged ticker. The cap inverts the risk budget and
    shrinks by heat already carried through the same crosswalk group (a
    group is one bet): allowed = max(0, budget*equity - group_heat), then
    cap_shares = allowed / ATR — FRACTIONAL, matching Robinhood fractional
    sizing (flooring to whole shares would zero every cap on a small
    account). Bearish flags carry NULL caps: the book is long-only, so the
    row itself (direction, score, group) is the advice, never a buy size.
    Same-group sibling caps each see the same remaining budget —
    alternatives, not a shopping list. exceeds_buying_power and the
    reliable-evidence counts are annotations, never gates (reliable = the
    scorer's n_bench >= 30 sample floor, not proof a signal works);
    flag_signals/reliable_ids intersect on (signal_id, via_crosswalk)
    pairs so crosswalk-only reliability never cites as direct evidence."""
```

Two idioms to carry over: **shares stay fractional** (never floor), and
**annotations, never gates**.

### The `atr_stale` flag matters

`position_heat.atr_stale` marks positions whose ATR came from a stale metrics
row. `v_book_heat` computes `heat_coverage` precisely so "missing ATR can never
silently understate heat". Your exit advice is ATR-derived, so a stale or NULL
ATR must produce a **NULL stop**, never a silently wrong one. Carry `atr_stale`
through to the new rows.

### Repo conventions

- stdlib only. No new dependency.
- Views are `DROP VIEW IF EXISTS` + `CREATE VIEW` every run (`advisor/db.py:69`:
  "Views are DROP+CREATEd every run (scorer pattern) so edits deploy nightly").
- Pure `build_*` helpers, tested directly; views only scope/aggregate.
- Tests mirror module layout: `tests/test_advisor_<layer>.py` where layer ∈
  {`catalog`, `fetch`, `db_schema`, `db_write`, `db_views`, `run`}.
- No network in tests.
- Timestamps UTC; calendar dates Phoenix (`phx_date` from `sources/common/clock.py`).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests (full) | `uv run pytest` | all pass, ~700 tests, <1s |
| Tests (advisor) | `uv run pytest -k advisor` | all pass |
| Lint | `uv run ruff check` | exit 0 |
| Format check | `uv run ruff format --check` | exit 0 |
| Types | `uv run mypy` | exit 0 |
| Run advisor | `uv run python main.py advisor --db data/advisor.db` | prints a snapshot line |
| Inspect | `sqlite3 -readonly data/advisor.db "<sql>"` | rows |

All four gates must pass before commit (`.githooks/pre-commit` runs them).

## Scope

**In scope**:

- `sources/combiners/advisor/fetch.py` (modify) — widen `read_positions` to select `avg_cost`
- `sources/combiners/advisor/db.py` (modify) — add `avg_cost` + exit columns to
  `position_heat`; add `build_exit_advice`; add `v_exit_advice`
- `sources/combiners/advisor/run.py` (modify) — call the new builder, write the rows
- `sources/combiners/advisor/catalog.py` (modify) — the stop/trim constants
- `tests/test_advisor_fetch.py` (modify)
- `tests/test_advisor_db_schema.py` (modify)
- `tests/test_advisor_db_write.py` (modify)
- `tests/test_advisor_db_views.py` (modify)
- `tests/test_advisor_run.py` (modify)
- `plans/README.md` (modify) — status row

**Out of scope** (do NOT touch, even though they look related):

- `sources/screeners/portfolio_screener/**` — `avg_cost` is already captured.
  Nothing to change upstream.
- `size_caps` table and `build_size_caps` — the entry side is correct and tested.
  Do not "unify" entry and exit into one table. They answer different questions
  and have different NULL semantics.
- `STRONG_MIN_ABS_SCORE` / `STRONG_MIN_TOTAL` — reuse; do not redefine, do not retune.
  A schema test pins them to composite's view text; changing them breaks that pin.
- **Anything that places, sizes for transmission, or formats an order.** The
  project invariant is decision support, never order generation. No broker calls,
  no MCP tool use, no "suggested order payload".
- `deploy/launchd/dashboard.py` and `deploy/launchd/daily_summary.py` — surfacing
  the new view in the nightly digest/dashboard is a natural follow-on but is a
  separate plan. Note that `daily_summary.py`'s digest helpers must be **total**
  (they run outside `main`'s try, so a crash there kills the whole nightly ntfy
  push) — which is exactly why wiring it in deserves its own careful plan.
- `sources/combiners/scorer/**` — the exit advice is not graded. It is advice.

## Git workflow

- Branch: `advisor/003-exit-advice`
- Conventional commits, lowercase, scoped:
  `feat(advisor): ATR stop distances and trim advice for held positions`
- Do **not** add a Co-Authored-By trailer (user's global instruction).
- Do **not** push or open a PR.

## Steps

### Step 1: widen `read_positions` to carry `avg_cost`

In `sources/combiners/advisor/fetch.py`:

```python
def read_positions(conn) -> list:
    """avg_cost is nullable in portfolio.db (Robinhood does not always report
    it); NULL means "entry unknown", never zero."""
    return [
        {"symbol": r[0], "quantity": r[1], "market_value": r[2], "avg_cost": r[3]}
        for r in conn.execute(
            "SELECT symbol, quantity, market_value, avg_cost FROM src.v_latest_positions"
        )
    ]
```

Update `tests/test_advisor_fetch.py`'s existing `read_positions` test to assert
the new key, and add `test_read_positions_preserves_null_avg_cost`.

**Verify**: `uv run pytest tests/test_advisor_fetch.py` → passes.

### Step 2: add the exit constants to `sources/combiners/advisor/catalog.py`

Read that file first (it is short) and match its comment density.

```python
# Exit advice (plan 003). ATR multiple for the stop: 2x ATR is the common
# swing-trading default and matches the 1%-risk entry sizing already used by
# build_size_caps (a 2-ATR stop on a cap-sized position risks ~the budget).
# Hand-tuned, like every other threshold here; revisit once the scorer has
# matured rows showing whether stopped-out positions actually keep falling.
STOP_ATR_MULTIPLE = 2.0

# Fraction of a position to trim when the composite STRONGLY disagrees
# (score_sum <= -4 AND total >= 3, mirroring composite v_flagged). Half, not
# all: the composite is one opinion and has never been graded (v_signal_efficacy
# is empty until plan 001 lands). A full exit would over-trust an unmeasured signal.
TRIM_FRACTION_STRONG = 0.5

# Weak disagreement (score_sum < 0 but not strong): no trim suggested, the
# row is the advice. Mirrors build_size_caps' NULL-cap convention for bearish flags.
```

**Verify**: `uv run python -c "from sources.combiners.advisor.catalog import STOP_ATR_MULTIPLE, TRIM_FRACTION_STRONG; print(STOP_ATR_MULTIPLE, TRIM_FRACTION_STRONG)"` → `2.0 0.5`

### Step 3: add `avg_cost` to `position_heat`, and create the `exit_advice` table

In `sources/combiners/advisor/db.py`:

1. Add `avg_cost REAL,` to the `position_heat` DDL (after `market_value`).
2. Add a new snapshot-scoped table:

```sql
CREATE TABLE IF NOT EXISTS exit_advice (
    snapshot_id      INTEGER NOT NULL REFERENCES snapshots(id),
    symbol           TEXT NOT NULL,
    quantity         REAL NOT NULL,
    price            REAL,
    avg_cost         REAL,
    atr              REAL,
    atr_stale        INTEGER NOT NULL DEFAULT 0,
    score_sum        INTEGER,
    total            INTEGER,
    strong           INTEGER NOT NULL DEFAULT 0,
    stop_price       REAL,
    stop_distance_pct REAL,
    unrealized_pct   REAL,
    trim_shares      REAL,
    PRIMARY KEY (snapshot_id, symbol)
);
```

**This is a schema change to an existing table.** `advisor.db` exists on disk
with rows. `ensure_schema` uses `CREATE TABLE ... IF NOT EXISTS`, which will
**not** add a column to an existing table. Follow the repo's established
migration idiom — see `sources/combiners/backtest/db.py` (`fix(backtest): widen
an existing snapshots table when market_rows is added`, commit `6287d7e`) and
`sources/combiners/scorer/db.py`'s `ensure_schema`, which both do:

```python
cols = {r[1] for r in conn.execute("PRAGMA table_info(position_heat)")}
if "avg_cost" not in cols:
    conn.execute("ALTER TABLE position_heat ADD COLUMN avg_cost REAL")
```

Read one of those two sites and copy the pattern exactly.

Also extend `prune` so `exit_advice` cascades with the snapshot, exactly as
`position_heat` and `size_caps` do. **Check `prune`'s existing body and add your
table to the same cascade.** Missing this leaks rows forever.

**Verify**:
```
uv run pytest tests/test_advisor_db_schema.py
uv run python -c "
import sqlite3, tempfile, os
from sources.combiners.advisor import db
p = os.path.join(tempfile.mkdtemp(),'a.db')
c = db.connect(p); db.ensure_schema(c)
print(sorted(r[1] for r in c.execute('PRAGMA table_info(position_heat)')))
print(sorted(r[1] for r in c.execute('PRAGMA table_info(exit_advice)')))
"
```
→ `position_heat` includes `avg_cost`; `exit_advice` has the 14 columns above.

Then prove the migration works on an **existing** DB (this is the risky path):
```
cp data/advisor.db /tmp/advisor-migrate-test.db
uv run python -c "
from sources.combiners.advisor import db
c = db.connect('/tmp/advisor-migrate-test.db'); db.ensure_schema(c)
print('avg_cost' in {r[1] for r in c.execute('PRAGMA table_info(position_heat)')})
"
```
→ prints `True`.

### Step 4: write `build_exit_advice` — a pure helper

In `sources/combiners/advisor/db.py`, beside `build_position_heat` and
`build_size_caps`. Signature mirrors theirs (plain data in, list of rows out):

```python
def build_exit_advice(heat_rows) -> list:
    """One row per HELD position (every row in position_heat), not just the
    disagreements — a stop is advice you want before the thesis breaks, not
    after. `strong` mirrors composite v_flagged (score_sum <= -STRONG_MIN_ABS_SCORE
    AND total >= STRONG_MIN_TOTAL) and is the only trigger for a trim.

    NULL discipline, matching build_size_caps:
      - atr is NULL or atr_stale -> stop_price/stop_distance_pct are NULL.
        An ATR-derived stop from a stale ATR is worse than no stop.
      - avg_cost is NULL -> unrealized_pct is NULL, never 0.
      - not strong -> trim_shares is NULL (the row itself is the advice).
    Shares stay FRACTIONAL (no flooring), matching Robinhood fractional sizing
    and build_size_caps' cap_shares.
    """
```

Math, precisely:

- `stop_price = price - STOP_ATR_MULTIPLE * atr` — but only when `atr` is not
  NULL, `atr_stale` is falsy, and `price` is not NULL. Otherwise NULL.
  If the computed `stop_price` is `<= 0`, emit NULL (a stop below zero is
  meaningless; this happens on a low-priced, high-ATR name).
- `stop_distance_pct = 100.0 * (price - stop_price) / price` when both defined.
- `unrealized_pct = 100.0 * (price - avg_cost) / avg_cost` when `avg_cost` is not
  NULL **and non-zero**. Guard the division; `avg_cost` of `0.0` is possible for
  a gifted/promotional share and must not raise `ZeroDivisionError`.
- `strong = (score_sum is not None and score_sum <= -STRONG_MIN_ABS_SCORE and
  total is not None and total >= STRONG_MIN_TOTAL)`.
- `trim_shares = quantity * TRIM_FRACTION_STRONG` when `strong`, else NULL.

Import `STRONG_MIN_ABS_SCORE` / `STRONG_MIN_TOTAL` from where they already live
(`advisor/db.py` module scope) and `STOP_ATR_MULTIPLE` / `TRIM_FRACTION_STRONG`
from `advisor/catalog.py`. Do not re-declare any of them.

Add a `write_exit_advice(conn, snapshot_id, rows)` writer next to the existing
writers, following their exact shape (parameterized executemany, `conn.commit()`
if the neighbours commit).

**Verify**: `uv run pytest tests/test_advisor_db_write.py` → passes (after step 6).

### Step 5: create `v_exit_advice` and wire the builder into `run.py`

View, added to `_VIEWS` (which is DROP+CREATEd every run):

```sql
DROP VIEW IF EXISTS v_exit_advice;
CREATE VIEW v_exit_advice AS
SELECT e.* FROM exit_advice e
JOIN v_latest_snapshot l ON e.snapshot_id = l.id;
```

In `sources/combiners/advisor/run.py`, after `position_heat` rows are built and
written (you need them as input), call `build_exit_advice(heat_rows)` and
`write_exit_advice(...)`. Read `run.py` first and insert into the existing
ordering; do not restructure it. Extend the final printed summary line to
include the exit-advice row count, matching the existing format.

`build_position_heat` must now also carry `avg_cost` from the widened
`read_positions` into the `position_heat` row it produces.

**Verify**:
```
uv run python main.py advisor --db data/advisor.db
sqlite3 -readonly data/advisor.db "SELECT symbol, quantity, price, atr, stop_price, ROUND(stop_distance_pct,2), ROUND(unrealized_pct,2), strong, trim_shares FROM v_exit_advice ORDER BY symbol;"
```
→ one row per held position. Positions with a usable ATR have a `stop_price`
strictly below `price`. Positions with `atr_stale=1` or NULL `atr` have NULL
`stop_price`. `trim_shares` is non-NULL only where `strong = 1`.

Cross-check the trigger agrees with the existing view:
```
sqlite3 -readonly data/advisor.db "SELECT (SELECT COUNT(*) FROM v_exit_advice WHERE strong=1) = (SELECT COUNT(*) FROM v_disagreements WHERE strong=1);"
```
→ `1`.

### Step 6: tests

Follow the existing structure in each file; do not invent a new fixture style.

`tests/test_advisor_db_write.py` — pure-function tests on `build_exit_advice`:

- `test_stop_price_is_two_atr_below_price`
- `test_null_atr_yields_null_stop` 
- `test_stale_atr_yields_null_stop` — `atr_stale=1` with a perfectly good ATR
- `test_nonpositive_stop_price_yields_null` — high ATR relative to price
- `test_null_avg_cost_yields_null_unrealized_not_zero`
- `test_zero_avg_cost_does_not_raise` — must not `ZeroDivisionError`
- `test_trim_only_when_strong` — `score_sum=-3,total=5` → no trim;
  `score_sum=-4,total=3` → trim; `score_sum=-9,total=2` → no trim (total floor)
- `test_trim_shares_are_fractional` — `quantity=7` → `3.5`, not `3`
- `test_row_emitted_for_every_held_position_not_only_disagreements`

`tests/test_advisor_db_schema.py`:

- `test_exit_advice_table_exists_with_expected_columns`
- `test_ensure_schema_adds_avg_cost_to_existing_position_heat` — build an old-shape
  `position_heat` without `avg_cost`, run `ensure_schema`, assert the column appears
- `test_prune_cascades_exit_advice` — insert a snapshot + exit_advice row, prune it,
  assert zero orphans

`tests/test_advisor_db_views.py`:

- `test_v_exit_advice_scopes_to_latest_snapshot` — two snapshots, assert only the
  newer one's rows appear (model on the existing `v_latest_heat` test)

`tests/test_advisor_run.py`:

- `test_run_writes_exit_advice_rows` — end-to-end with the file's existing fake
  source DBs; assert one `exit_advice` row per position.

**Verify**: `uv run pytest -k advisor` → all pass, ~13 new tests.

## Test plan

Summarized above. Coverage targets, in priority order:

1. **NULL discipline** — the single most likely source of wrong advice. A stop
   computed from a stale ATR, or an `unrealized_pct` of `0` standing in for
   "unknown entry", are both silently plausible and both wrong.
2. **The `strong` trigger** boundary conditions on both thresholds.
3. **Fractional shares** — flooring would zero out trims on small positions,
   the same failure `build_size_caps` explicitly guards against.
4. **The migration** on an existing-shape table (step 3), since `advisor.db`
   exists on disk with live rows.

Structural pattern: the existing tests in each of the five advisor test files.

**Verify**: `uv run pytest` → all pass, no net-new failures.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `uv run ruff check` exits 0
- [ ] `uv run ruff format --check` exits 0
- [ ] `uv run mypy` exits 0
- [ ] `uv run pytest` exits 0, with ~13 new tests passing
- [ ] `sqlite3 -readonly data/advisor.db "SELECT COUNT(*) FROM v_exit_advice"` equals `SELECT COUNT(*) FROM v_latest_heat`
- [ ] `sqlite3 -readonly data/advisor.db "SELECT COUNT(*) FROM v_exit_advice WHERE stop_price >= price"` → `0`
- [ ] `sqlite3 -readonly data/advisor.db "SELECT COUNT(*) FROM v_exit_advice WHERE trim_shares IS NOT NULL AND strong = 0"` → `0`
- [ ] `sqlite3 -readonly data/advisor.db "SELECT COUNT(*) FROM v_exit_advice WHERE stop_price IS NOT NULL AND (atr IS NULL OR atr_stale = 1)"` → `0`
- [ ] The step-5 cross-check against `v_disagreements` returns `1`
- [ ] `grep -rn "place_order\|place_equity_order\|submit" sources/combiners/advisor/` → no matches
- [ ] `git status` shows no modified files outside the In-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `PRAGMA table_info(positions)` on `data/portfolio.db` shows no `avg_cost`
  column. The whole `unrealized_pct` half of this plan depends on it.
- The `ALTER TABLE` migration in step 3 fails on the real `data/advisor.db`, or
  the post-migration `ensure_schema` is not idempotent (run it twice; the second
  run must be a no-op, not an error).
- You conclude the advisor must read a *fifth* source DB to do this. It must
  not — every input is already in `position_heat` plus the one `avg_cost` column.
  If you think otherwise, you have mis-scoped; stop and report.
- You find yourself writing anything that constructs an order, calls an MCP
  tool, or formats a broker payload. That violates the project's central
  invariant. Stop immediately.
- A step's verification fails twice after a reasonable fix attempt.
- `data/advisor.db` has zero rows in `position_heat` (an empty book, or the
  `portfolio` job has not run). You cannot verify steps 5–6 against real data.
  Unit tests still pass; report and let a human confirm against a live book.

## Execution notes (added after implementation)

- **The plan's out-of-scope list was too narrow.** `write_position_heat` binds
  parameters by name, so adding `avg_cost` to `position_heat` broke three test
  fixtures that hand-build heat rows: `tests/test_advisor_db_views.py:_row`,
  `tests/test_dashboard.py:_build_advisor_db`, and a positional
  `INSERT INTO position_heat VALUES (...)` in `tests/test_dashboard.py`. All
  three were updated (the positional insert became column-named). The strict
  named binding is a *feature* — a future change that silently drops `avg_cost`
  fails loudly rather than writing NULLs — so the writer was NOT loosened to
  `.get()` defaults.
- `run()` now returns a 4-tuple `(sid, n_heat, n_caps, n_exit)`; two call sites
  in `tests/test_advisor_run.py` were updated.
- Verified against a **copy** of the real DBs, never the live ones. On the real
  book: `DHR`, price 191.33, avg_cost 177.14 → `unrealized_pct` +8.0%,
  `stop_price` 180.52 (5.7% away), `strong=0` so `trim_shares` is NULL. All five
  machine-checkable invariants held, including `strong` agreeing exactly with
  `v_disagreements`.
- The migration was exercised against the real `advisor.db` shape (which lacked
  `avg_cost`): `ensure_schema` added the column and was idempotent on re-run.
- `price` here is now the *settled* close, courtesy of plan 000. Before that fix
  every stop would have been computed from the prior session's close.

## Maintenance notes

For the human/agent who owns this after it lands:

- **`STOP_ATR_MULTIPLE = 2.0` and `TRIM_FRACTION_STRONG = 0.5` are judgment,
  not measurement.** They were chosen to be conservative because
  `v_signal_efficacy` is empty — the composite has never been graded. Once
  plan 001 backfills the price ledger and efficacy rows accumulate, the honest
  move is to measure whether positions that hit a 2-ATR stop actually keep
  falling, and retune. Until then, do not present these numbers as validated.
- **The advisor now has an asymmetry of its own**: `size_caps` is emitted only
  for *flagged* tickers, while `exit_advice` is emitted for *every held*
  position. That is intentional (you want a stop before the thesis breaks), but
  it means the two tables have different row counts and must not be joined naively.
- **The natural follow-on, deliberately deferred**: surfacing `v_exit_advice` in
  the nightly ntfy digest and the dashboard. Note the trap recorded in project
  memory: `daily_summary.py`'s `build_summary` runs **outside** `main`'s
  try/except, so a non-`sqlite3` error in a digest helper kills the entire nightly
  push. Any digest section reading `v_exit_advice` must be **total** — it must
  guard the NULL-by-design columns (`stop_price`, `trim_shares`, `unrealized_pct`)
  rather than assume them present. That is why it is not in this plan.
- **What a reviewer should scrutinize**: (1) every NULL guard in
  `build_exit_advice`, especially `avg_cost == 0` and `stop_price <= 0`;
  (2) that `prune` cascades the new table; (3) that the migration is idempotent;
  (4) that no threshold constant was redefined rather than imported;
  (5) that `trim_shares` is fractional.
