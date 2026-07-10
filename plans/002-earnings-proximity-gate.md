# Plan 002: Make composite aware that a ticker reports earnings within days

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 5c14446..HEAD -- sources/combiners/composite sources/monitors/earnings_calendar`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S–M
- **Risk**: LOW
- **Depends on**: none (independent of plan 001; can run in parallel)
- **Category**: direction
- **Planned at**: commit `5c14446`, 2026-07-08

## Why this matters

`data/earnings.db` holds 553 forward earnings events. The monitor that fills it
runs daily inside the `preopen` job, and its watchlist is already scoped to
exactly the tickers that matter — portfolio holdings ∪ the `cboe_options`
catalog (see `docs/SCHEDULE.md`, the `preopen` row).

It feeds nothing. No combiner attaches `earnings.db`. Its view
`v_imminent_earnings` is referenced only by its own tests.

That view's docstring, written by whoever built it, states the intended
consumer outright:

```
-- Reporting within the horizon window (drives sizing / IV-crush decisions).
```

Nothing does sizing or IV-crush decisions with it.

The cost is concrete: composite has two **market-grain** event gates —
`fomc_blackout` and `econ_imminent` — but **no per-ticker event gate**. So a
ticker can accumulate a strong bullish technical score (say `stocks_rsi` says
oversold, `si_days_to_cover` says squeeze fuel), get flagged, and be handed to
the `advisor`, which computes a vol-scaled size cap for it — two days before it
reports earnings. Earnings is the single most common way a technical signal gets
run over. The system already knows the earnings date and never looks.

`stocks.db.metrics.nextEarningsDate` says the same thing a second way and is
also unconsumed (`grep -rn nextEarningsDate sources/combiners/` → 0 hits).

When this lands, composite records earnings proximity per ticker, `v_flagged`
consumers can see it, and the advisor's cap rows carry the warning.

## Current state

### The pattern you will copy: `fomc_blackout`, a score-0 gate

`sources/combiners/composite/catalog.py:136-151`:

```python
    {
        # Gate, not direction: score 0; regime tier reads the raw flag.
        "signal_id": "fomc_blackout",
        "db": "fomc.db",
        "grain": "market",
        "staleness_budget_days": 0,
        "sql": """
            SELECT '*',
                   EXISTS(SELECT 1 FROM src.events e
                          WHERE e.event_type = 'fomc_blackout_start'
                            AND e.event_date <= :today
                            AND json_extract(e.payload, '$.window_end')
                                >= :today),
                   0, :today
        """,
    },
```

Note the four things that make it a gate:

1. `score` is the literal `0` — it never votes, so it never moves `score_sum`.
2. `grain` is `market`, so `entity` is `'*'`.
3. `raw_value` carries the flag (here, an `EXISTS` → 0/1).
4. It is listed in `REGIME_FIELDS` so the raw value lands in a `market_regime` column.

Your new signal is the same idea at **ticker grain**, so it will be `entity =
symbol` and it will **not** appear in `REGIME_FIELDS` (that map is market-grain only).

### The contract every signal SQL must satisfy

`sources/combiners/composite/catalog.py:1-14`:

```
Every SQL runs against ONE source DB attached read-only as `src`, with
:today (YYYY-MM-DD) bound by the run. Required row shape:
    (entity, raw_value, score, obs_date)
entity is '*' (market), an asset class, or a ticker. score is an integer
-2..+2, positive = bullish for the entity — contrarian readings (crowded
shorts, panicky put buying) are applied HERE, not by consumers.

One-clock rule: never reference a source's calendar_now-dependent views
(monitor v_upcoming/v_imminent, treasury.v_upcoming_auctions, fred.v_asof);
query base tables with :today instead.
```

**Read that last paragraph twice.** It names `v_imminent` explicitly. You may
**not** consume `earnings.db`'s `v_imminent_earnings` view, even though it is
the view whose docstring motivated this plan. It filters on the source's
`calendar_now` singleton, which is a *different clock* from composite's
`:today`. You must query the `events` base table with `:today` instead.

### What `v_imminent_earnings` does (the logic you will re-express against base tables)

`sources/monitors/earnings_calendar/db.py:21-28`:

```sql
-- Reporting within the horizon window (drives sizing / IV-crush decisions).
CREATE VIEW IF NOT EXISTS v_imminent_earnings AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status
FROM events e, calendar_now p
WHERE e.event_type = 'earnings'
  AND e.event_date BETWEEN p.today
      AND date(p.today, '+' || p.horizon_days || ' days')
ORDER BY e.event_date;
```

Key facts for your rewrite:

- The **ticker lives in `events.subtype`**, not in a `ticker` column.
- `event_type` is the literal string `'earnings'`.
- `calendar_now p` supplies `p.today` and `p.horizon_days`. You replace `p.today`
  with the bound `:today` parameter and **hard-code your own horizon** in the SQL
  (do not read `horizon_days` — that is the source's clock/config, not composite's).

Confirm the shape yourself before writing SQL:

```
sqlite3 -readonly data/earnings.db "SELECT event_type, COUNT(*) FROM events GROUP BY 1;"
sqlite3 -readonly data/earnings.db "SELECT event_date, subtype, status FROM events WHERE event_type='earnings' ORDER BY event_date LIMIT 5;"
```

### The nearest ticker-grain exemplar in the catalog

`sources/combiners/composite/catalog.py:395-408` — `edgar_insider`, the other
score-0 ticker-grain signal:

```python
    {
        # Form 4 cluster = attention flag; direction unknown at index
        # level (buys and sells both file Form 4), hence score 0.
        "signal_id": "edgar_insider",
        "db": "edgar.db",
        "grain": "ticker",
        "staleness_budget_days": 5,
        "sql": """
            SELECT ticker, COUNT(*), 0, MAX(filed_date)
            FROM src.v_tickered
            WHERE bucket = 'insider' AND ticker IS NOT NULL
            GROUP BY ticker HAVING COUNT(*) >= 3
        """,
    },
```

This is your closest structural model: ticker entity, score 0, informational.

### How score-0 ticker rows are treated downstream (important — read before designing)

Two consumers deliberately **drop** score-0 ticker rows:

- `sources/combiners/scorer/fetch.py:52-63` — `read_signal_rows` selects
  `grain = 'ticker' AND score != 0`, because "score 0 has no direction to grade".
- `sources/combiners/advisor/fetch.py:38-51` — `read_flag_signals` likewise
  filters `score != 0`, because a score-0 row "carries no direction, so it is
  not evidence".

**Consequence you must accept:** a score-0 `earnings_imminent` signal will
correctly appear in `composite.db`'s `signal_values` table and in
`v_signal_detail`, but it will **not** be graded by the scorer and **not** be
cited as advisor evidence. That is the right behavior — earnings proximity is a
risk annotation, not a directional vote. Do not try to make it vote by giving it
a nonzero score. Do not modify those two filters.

### Repo conventions

- Signals are pure catalog entries. Adding one should touch `catalog.py` and its
  test, and nothing else in `sources/combiners/composite/`.
- `select_ids(only, exclude, add)` (`composite/catalog.py:453-466`) already gates
  which signals run, so an added signal is opt-out-able without code changes.
- Views `LEFT JOIN` so a partial `--only` run yields NULLs rather than erroring.
- **No network in tests**; the whole suite is offline.
- Timestamps UTC, calendar dates Phoenix (`phx_date` from `sources/common/clock.py`).
  Not directly relevant here — `:today` is bound by the run — but `staleness_budget_days`
  interacts with `obs_date`, so read the next bullet.
- `staleness_budget_days` is how many days old `obs_date` may be before the
  signal is considered stale. For a **forward-looking** calendar signal, `obs_date`
  should be `:today` by construction (like `usda_stocks_to_use`, which does
  `SELECT 'ags', AVG(...), CASE..., :today`), and the budget should be `0`.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tests (full) | `uv run pytest` | all pass, ~700 tests, <1s |
| Tests (filtered) | `uv run pytest -k earnings` | all pass |
| Lint | `uv run ruff check` | exit 0 |
| Format check | `uv run ruff format --check` | exit 0 |
| Types | `uv run mypy` | exit 0 |
| Run composite | `uv run python main.py composite --db data/composite.db` | prints a snapshot line |
| Inspect a DB | `sqlite3 -readonly data/earnings.db "<sql>"` | rows |

All four gates must pass before commit (`.githooks/pre-commit` runs them).

## Scope

**In scope** (the only files you may create or modify):

- `sources/combiners/composite/catalog.py` (modify) — add one `SIGNALS` entry
- `tests/test_composite_catalog.py` (modify) — assert the new entry's shape
- `tests/test_composite_run.py` (modify) — one integration test with a fake earnings.db
- `plans/README.md` (modify) — status row

**Out of scope** (do NOT touch, even though they look related):

- `sources/monitors/earnings_calendar/**` — the monitor and its views are correct
  and already tested. You are a *consumer*. Do not add a view there for composite
  to read; the one-clock rule forbids consuming its calendar-dependent views anyway.
- `sources/combiners/scorer/fetch.py` and `sources/combiners/advisor/fetch.py` —
  their `score != 0` filters are correct. Do not "fix" them to include your signal.
- `sources/combiners/composite/db.py` — no schema change is needed. A ticker-grain
  signal writes into the existing `signal_values` table. Do **not** add a column
  to `ticker_scores`.
- `REGIME_FIELDS` in `composite/catalog.py` — market-grain only. Your signal is
  ticker-grain and must not appear there.
- `sources/combiners/advisor/**` — surfacing earnings proximity in the advisor's
  cap rows is a genuine follow-on, but it needs `earnings.db` attached as a
  *fifth* source and that is a separate plan. Not here.
- `deploy/launchd/install.py` — no schedule change. `composite` already runs
  nightly at 9:05pm, after `preopen` refreshed `earnings.db` that morning.

## Git workflow

- Branch: `advisor/002-earnings-proximity-gate`
- Conventional commits, lowercase, scoped — matching `git log`:
  `feat(composite): gate ticker scores on earnings proximity`
- Do **not** add a Co-Authored-By trailer (user's global instruction).
- Do **not** push or open a PR.

## Steps

### Step 1: confirm the `earnings.db` base-table shape

Before writing SQL, verify the facts this plan asserts:

```
sqlite3 -readonly data/earnings.db "SELECT event_type, COUNT(*) FROM events GROUP BY 1;"
sqlite3 -readonly data/earnings.db "SELECT event_date, subtype, status, event_time FROM events WHERE event_type='earnings' ORDER BY event_date LIMIT 5;"
sqlite3 -readonly data/earnings.db "SELECT COUNT(DISTINCT subtype) FROM events WHERE event_type='earnings';"
```

**Verify**: `event_type` is `'earnings'` for all 553 rows; `subtype` holds a
ticker symbol (e.g. `AAPL`), not a description; `event_date` is `YYYY-MM-DD`.

If `subtype` does not hold tickers, STOP — the rest of this plan's SQL is wrong.

### Step 2: add the signal to `SIGNALS` in `sources/combiners/composite/catalog.py`

Insert it in the **ticker grain** section (after the `# --- ticker grain ---`
banner), placed next to `edgar_insider` since both are score-0 informational rows.

Target shape — note every element mirrors the conventions above:

```python
    {
        # Gate, not direction: score 0. A ticker reporting within the window
        # carries event risk that no technical signal prices in, so the row
        # annotates the scorecard rather than voting on it. Consumers that
        # grade or cite evidence already drop score-0 ticker rows
        # (scorer/fetch.py read_signal_rows, advisor/fetch.py read_flag_signals).
        # One-clock rule: earnings.db's v_imminent_earnings filters on its own
        # calendar_now, so query the events base table with :today instead.
        # raw_value = days until the print (0 = reports today).
        "signal_id": "earnings_imminent",
        "db": "earnings.db",
        "grain": "ticker",
        "staleness_budget_days": 0,
        "sql": """
            SELECT e.subtype,
                   CAST(julianday(MIN(e.event_date)) - julianday(:today)
                        AS INTEGER),
                   0, :today
            FROM src.events e
            WHERE e.event_type = 'earnings'
              AND e.subtype IS NOT NULL
              AND e.event_date >= :today
              AND e.event_date <= date(:today, '+7 days')
            GROUP BY e.subtype
        """,
    },
```

Design notes, so you can defend each choice:

- **`MIN(event_date)` + `GROUP BY subtype`**: a ticker can have more than one
  forward earnings row (a tentative estimate and a confirmed date both land in
  `events`, keyed `(event_type, event_date, subtype)`). Without the aggregate you
  would emit duplicate rows per ticker and violate composite's per-`(signal, entity)`
  uniqueness. This is the single most likely bug in this plan.
- **`+7 days`**: one trading week. Wide enough to matter for sizing, narrow
  enough that it isn't always-on. The `mcal_days_to_opex` signal uses the same
  `julianday` difference idiom (`composite/catalog.py:174-182`) — match it.
- **`obs_date = :today`**: the signal is forward-looking; its observation is
  "as of today, this is the distance". Hence `staleness_budget_days: 0`,
  exactly like `fomc_blackout` / `econ_imminent` / `mcal_days_to_opex`.
- **Do not add to `REGIME_FIELDS`.** That dict is market-grain only.

**Verify**:
```
uv run python -c "
from sources.combiners.composite.catalog import SIGNALS
s = [x for x in SIGNALS if x['signal_id']=='earnings_imminent'][0]
assert s['grain']=='ticker' and s['db']=='earnings.db' and s['staleness_budget_days']==0
print('ok', len(SIGNALS), 'signals')
"
```
→ prints `ok 24 signals`.

```
uv run python -c "
from sources.combiners.composite.catalog import REGIME_FIELDS
assert 'earnings_imminent' not in REGIME_FIELDS; print('not in REGIME_FIELDS: ok')
"
```
→ prints the ok line.

### Step 3: assert the one-clock rule is not violated

The catalog docstring forbids referencing calendar-dependent views. Make that
mechanically checked rather than trusted:

```
grep -n "v_imminent\|v_upcoming\|calendar_now\|v_asof" sources/combiners/composite/catalog.py
```
→ must return **only** the docstring's prohibition text (around line 11–13), and
no occurrence inside any `"sql"` string.

### Step 4: extend `tests/test_composite_catalog.py`

Read the existing tests in that file first and match their structure. Add:

- `test_earnings_imminent_is_a_ticker_grain_zero_score_gate` — assert `grain ==
  "ticker"`, `db == "earnings.db"`, `staleness_budget_days == 0`, and that the
  SQL's score literal is `0`.
- `test_earnings_imminent_not_in_regime_fields` — market-grain only.
- `test_earnings_imminent_sql_does_not_read_calendar_dependent_views` — assert
  none of `v_imminent`, `v_upcoming`, `calendar_now`, `v_asof` appear in the
  signal's `sql` string. (This encodes the one-clock rule as a test, which is the
  repo's habit — see how `test_journal_matching` pins thresholds to composite's
  view text.)
- `test_earnings_imminent_selectable_by_select_ids` — `select_ids(only=["earnings_imminent"])`
  returns exactly that one entry; `select_ids(exclude=["earnings_imminent"])` omits it.

**Verify**: `uv run pytest tests/test_composite_catalog.py` → all pass.

### Step 5: add one integration test in `tests/test_composite_run.py`

Read that file first: it builds fake source DBs in `tmp_path` and runs
`composite.run(...)` with injected seams. Follow its existing fixture pattern
exactly — do not invent a new one.

Write `test_run_emits_one_earnings_imminent_row_per_ticker`:

1. Build a fake `earnings.db` containing an `events` table with:
   - `('earnings', '<today+2>', 'AAPL')` and `('earnings', '<today+5>', 'AAPL')`
     — **two rows for the same ticker**, to prove the `GROUP BY`/`MIN` dedupe works
   - `('earnings', '<today+3>', 'MSFT')`
   - `('earnings', '<today+30>', 'NVDA')` — outside the 7-day window
   - `('earnings', '<today-1>', 'TSLA')` — in the past
2. Run composite with `--only earnings_imminent` (via `select_ids`).
3. Assert `signal_values` contains **exactly two** rows for `earnings_imminent`:
   `AAPL` with `raw_value == 2`, and `MSFT` with `raw_value == 3`.
4. Assert `NVDA` and `TSLA` are absent.
5. Assert both rows have `score == 0` and `grain == 'ticker'`.

**Pin the dates relative to an injected `now_iso`, never `date('now')`.** The
repo's determinism invariant requires it, and `CLAUDE.md` warns that fixtures for
evening jobs must straddle the UTC/Phoenix rollover. Composite runs at 9:05pm
Phoenix = 04:05Z the next day. So use a `now_iso` like
`"2026-07-09T04:05:00+00:00"` whose Phoenix date is `2026-07-08`, and assert the
signal's `:today` binding is `2026-07-08`. If you use `"2026-07-08T21:05:00+00:00"`
the test cannot catch a UTC/Phoenix mixup — which is precisely the bug this
fixture must be able to catch.

**Verify**: `uv run pytest tests/test_composite_run.py -k earnings` → passes.

### Step 6: run it for real and confirm rows land

```
uv run python main.py composite --db data/composite.db --only earnings_imminent
sqlite3 -readonly data/composite.db "SELECT entity, raw_value, score, grain FROM signal_values WHERE signal_id='earnings_imminent' AND snapshot_id=(SELECT MAX(id) FROM snapshots) ORDER BY raw_value LIMIT 10;"
```

→ Expect one row per ticker reporting in the next 7 days, `raw_value` = whole
days until the print, `score` = 0, `grain` = `ticker`. Zero duplicate entities:

```
sqlite3 -readonly data/composite.db "SELECT entity, COUNT(*) c FROM signal_values WHERE signal_id='earnings_imminent' AND snapshot_id=(SELECT MAX(id) FROM snapshots) GROUP BY 1 HAVING c > 1;"
```
→ must return **0 rows**.

Then run a full composite (all signals) and confirm nothing regressed:

```
uv run python main.py composite --db data/composite.db
uv run pytest
```

## Test plan

- `tests/test_composite_catalog.py` — 4 new tests (step 4).
- `tests/test_composite_run.py` — 1 new integration test (step 5), covering:
  happy path, per-ticker dedupe across duplicate event rows, out-of-window
  exclusion (future), past-event exclusion, score-0 invariant.
- Structural pattern: the existing tests in those two files. Do not introduce a
  new fixture style.

**Verify**: `uv run pytest` → all pass, 5 new tests, no net-new failures.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `uv run ruff check` exits 0
- [ ] `uv run ruff format --check` exits 0
- [ ] `uv run mypy` exits 0
- [ ] `uv run pytest` exits 0, with 5 new tests passing
- [ ] `uv run python -c "from sources.combiners.composite.catalog import SIGNALS; print(len(SIGNALS))"` → `24`
- [ ] `uv run python -c "from sources.combiners.composite.catalog import REGIME_FIELDS; assert 'earnings_imminent' not in REGIME_FIELDS"` → exit 0
- [ ] The `earnings_imminent` `sql` string contains none of: `v_imminent`, `v_upcoming`, `calendar_now`, `v_asof`
- [ ] After a real run: `sqlite3 -readonly data/composite.db "SELECT COUNT(*) FROM signal_values WHERE signal_id='earnings_imminent' AND score != 0"` → `0`
- [ ] After a real run, the duplicate-entity query in step 6 returns 0 rows
- [ ] `git status` shows no modified files outside the In-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Step 1 shows `events.subtype` does not hold ticker symbols for
  `event_type='earnings'`. All SQL in this plan depends on it.
- The full composite run's row count for **other** signals changes. Adding a
  signal must not perturb existing ones; if it does, something in the run loop is
  order-dependent and that is a bug worth reporting, not routing around.
- You conclude the signal needs a nonzero score to be useful. It does not — see
  "How score-0 ticker rows are treated downstream". If you believe otherwise,
  stop and report; changing this is a scoring-thesis decision, and per `CLAUDE.md`
  signal weighting is a human decision informed by measured efficacy.
- You find yourself wanting to modify `scorer/fetch.py` or `advisor/fetch.py`.
- A step's verification fails twice after a reasonable fix attempt.
- `data/earnings.db` has 0 rows in `events` (the `preopen` job may not have run).
  Composite's views `LEFT JOIN`, so this degrades to NULLs rather than erroring —
  but you cannot verify step 6 without data. Report and wait.

## Execution notes (added after implementation)

**The plan had a CRITICAL omission.** It asserted "no schema change is needed"
and put `composite/db.py` out of scope. That was wrong.

`ticker_scores.total` is `COUNT(*)` over ticker-grain signals — **evidence
breadth, not a vote count** (`composite/db.py:249-259`) — and `v_flagged` gates
on `ABS(score_sum) >= 4 AND total >= 3` (`composite/db.py:77-79`). Only
`portfolio_holding` was excluded, via `INFORMATIONAL_SIGNALS`. So a score-0
`earnings_imminent` row still widened the evidence base. Measured:

| | `score_sum` | `total` | flagged? |
|---|---|---|---|
| two real votes (+2, +2) | 4 | 2 | no |
| the same, **plus an earnings row** | 4 | **3** | **YES** |

A ticker would have been flagged **because** it reports earnings soon — the
exact inverse of the gate's purpose, and it would have silently changed which
tickers reach the advisor. The fix adds `earnings_imminent` to
`INFORMATIONAL_SIGNALS` (`composite/db.py:108`), pinned by
`test_earnings_imminent_is_informational_and_never_creates_a_flag`, which was
mutation-verified to fail when the entry is removed. `edgar_insider` is
deliberately left counting: a Form 4 cluster is real, if directionless, evidence
about the ticker, whereas an earnings date is not.

Two smaller things the plan also got wrong:

1. **The run-level test could not catch a missing `GROUP BY`.** `signal_values`
   has PK `(snapshot_id, signal_id, entity)` and the writer is `INSERT OR IGNORE`
   (`composite/db.py:130`), so a duplicate entity is silently swallowed and
   whichever row the scan yields first wins. A mutation test confirmed that
   deleting `MIN(...)`/`GROUP BY` changed nothing at the run level. The dedupe is
   therefore asserted on `fetch.extract()` — *before* the OR-IGNORE funnel — in
   `test_earnings_imminent_emits_exactly_one_row_per_ticker`, with the far date
   stored first so an accidental pass is impossible.

2. **Never verify with `--only` against the real `data/composite.db`.** A
   `--only` run still writes a full snapshot *with a `market_regime` row* built
   from zero market signals. The scorer keys on the presence of that row, and
   `registered_snapshots`' `UNIQUE(entry_date) WHERE ticker_rows > 0` means the
   degenerate snapshot can seize the window slot and block the real nightly
   opinion from ever registering. Verify against a copy of the DB.

## Maintenance notes

For the human/agent who owns this after it lands:

- **The `GROUP BY subtype` + `MIN(event_date)` is load-bearing.** The monitor
  framework's `upsert_events` lets a date firm up in place (tentative →
  confirmed), and `replace_forward_window` is cancellation-aware, but a ticker can
  still legitimately carry more than one forward `earnings` row. If you ever see
  duplicate `(signal_id, entity)` rows in `signal_values`, this is why.
- **The 7-day window is a hand-tuned constant**, like every other threshold in
  this catalog. Once plan 001 lands and the scorer has matured rows, you can
  measure whether flagged tickers inside the window underperform flagged tickers
  outside it — that is the empirical justification for widening or narrowing it.
  Until then, 7 is a judgment call, not a measurement.
- **The natural follow-on** (deliberately out of scope): teach the `advisor` to
  attach `earnings.db` and stamp an `earnings_in_days` column on `size_caps`, so
  the nightly digest and dashboard can print "cap 120 shares — reports in 2 days".
  That needs a fifth read-only attach in `advisor/run.py` and a schema column;
  it is a clean, separate plan.
- **What a reviewer should scrutinize**: (1) that no `"sql"` string references a
  `calendar_now`-dependent view; (2) that the run test's `now_iso` straddles the
  UTC→Phoenix date rollover (`T04:05:00+00:00`, not `T21:05:00+00:00`) — otherwise
  the test cannot catch a date-slicing bug; (3) that the signal is absent from
  `REGIME_FIELDS`.
