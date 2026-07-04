# Stage 5 — Scheduler, Two Clocks (`schedule`)

**Status:** Spec (no implementation plan yet)
**Grounding:** [PIPELINE_ROADMAP.md](../../PIPELINE_ROADMAP.md) Stage 5 ·
[research §6](../../research/2026-07-03-signal-to-candidate-pipeline.md) (🔵 — reasoned
from verified data properties). **Independent of Stages 1–4** — buildable now; job
targets that don't exist yet simply aren't registered.

## Purpose

Replace "run screeners whenever" with the two-clock design: **event-driven signal
jobs** tied to release calendars (a structural look-ahead defense — a job that only
fires on publication can't act on data before it exists) and **fixed daily gate
windows** (pre-close, optional pre-open). The scheduler is a *deterministic due-job
evaluator*, not a daemon: an external cron/launchd invokes it every ~15 minutes; given
the same `now_iso` and monitor DBs it always produces the same answer.

## Package shape

`pipeline/scheduler/`: `catalog.py` (the job table — triggers, targets, argv),
`extract.py` (read monitor DBs read-only), `db.py` (`schedule.db`), `run.py`
(`"schedule"` in `registry.py`). No network of its own — all calendar knowledge comes
from the already-built monitors (`econ_calendar`, `earnings`, `market_calendar`) plus
static rules. (`fomc` is *maintained* by the daily job but no v1 trigger consumes it;
a blackout-aware gate window is a possible future use, not spec'd.)

**Read-only correctness note:** the monitors' `v_upcoming*`/`v_early_closes` views
filter on each DB's `calendar_now.today`, which only that monitor's own run sets —
the scheduler must not depend on it (stale if today's maintenance hasn't run) and
cannot set it on a read-only connection. `extract.py` therefore queries the `events`
tables **directly**, binding `:today` derived from the scheduler's own `now_iso`.

## Time model (the one place wall-clock legitimately enters)

`now_iso` is injected as everywhere else; the cron wrapper passes real time, tests
pass fixtures. ET conversion via stdlib `zoneinfo` (`America/New_York`) — DST handled
correctly, no third-party dependency on macOS/Linux (system tzdata; caveat: Windows or
slim CI images would need the `tzdata` PyPI package — acceptable for a
macOS-deployed scheduler, noted for the "plain checkout" property). All trigger times below are ET. Trading-day and
early-close facts come from `market_calendar` (`is_trading_day(conn, d)` helper,
`v_early_closes`) — never hardcoded holiday math.

## Job catalog (v1)

`Job(name, trigger, argv_fn)` — trigger evaluated against `now_iso` + monitor DBs;
`trigger_key` is the identity that makes runs idempotent.

| Job | Trigger (clock 1: event-driven) | trigger_key |
|---|---|---|
| `cftc` | Friday ≥ 16:00 ET (COT posts ~15:30) | that Friday's date |
| `fred` | an `econ_calendar` event released today: `events` where `event_date = today` and now ≥ `event_time` + 15 min (`event_time` is populated per event at ingest; `release_time` exists only in `release_catalog`) | `event_type:event_date` |
| `fundamentals`, `stocks` | a watched ticker's earnings event today (earnings `events`), evaluated once post-close 18:00 ET; plus a weekly Sunday baseline sweep | `earnings:date` / `weekly:date` |
| `earnings`, `econ_calendar`, `fomc`, `market_calendar`, `treasury` | daily maintenance, 07:00 ET | `daily:date` |
| `leads` | any of {`cftc`,`fred`,`fundamentals`,`stocks`} has an `ok` run newer than the last `ok` `leads` run | `after:<newest upstream job>:<its trigger_key>` — N upstream successes coalesce into ONE due `leads` run keyed to the newest |
| `promote` | `leads` has an `ok` run newer than the last `ok` `promote` run | same coalescing pattern |

| Window (clock 2: fixed) | Trigger | trigger_key |
|---|---|---|
| `gate` pre-close | trading day, ≥ 15:30 ET (≥ 12:30 when *equity* markets close early — `events` where `event_type='early_close'`, NOT `bond_early_close`), once per day | `pre_close:<date>` |
| `gate` pre-open (off by default) | trading day, ≥ 09:00 ET, `--window pre_open` | `pre_open:<date>` |

The five-touchpoint intraday instinct is deliberately absent (research §6: mid-day
adds cost, not edge, at this data's cadence).

`argv_fn` notes: `promote`'s argv passes no `--equity` — it relies on the
`PIPELINE_EQUITY` env fallback (Stage 2), sourced from `.env` by the cron wrapper.
`gate`'s argv includes `--window pre_close` / `--window pre_open` (Stage 3 CLI).

## Idempotency & state — `schedule.db`

```sql
job_runs(job TEXT NOT NULL, trigger_key TEXT NOT NULL,
         attempt INTEGER NOT NULL,           -- 1, 2, 3, ... one ROW per attempt
         started_at TEXT NOT NULL, finished_at TEXT,
         status TEXT NOT NULL,               -- 'running' | 'ok' | 'error'
         error TEXT,                          -- type name only (secret hygiene)
         PRIMARY KEY (job, trigger_key, attempt));

snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          due_count INTEGER, ran_count INTEGER);
```
One row per attempt — retries are countable and history is preserved (an
overwrite-in-place PK couldn't express its own retry policy). A job is **due** iff its
trigger holds AND no `ok` row exists for `(job, trigger_key)` AND
`count(attempts) < max_attempts` (= 3; after that it stays failed until
`--retry job:key`, which is allowed to add attempts past the cap). A `running` row
older than 2 hours with no successor attempt is treated as `error` (crash recovery) —
the row itself is never rewritten; the next attempt is a new row.

Views: `v_due` (what would run now — requires `set_now` single-row param table, same
`calendar_now` pattern as `monitor_common`), `v_recent_runs`, `v_failures`.

## Execution model

`--run` executes due jobs **in-process** via `registry.REGISTRY[name](argv)` — same
process, sequential, in catalog order. No subprocesses, no parallelism: total runtime
is dominated by polite rate limits anyway, and sequential means one WAL writer per DB.
Per-job failures are caught as **`(Exception, SystemExit)`** — every registered `main`
is an argparse wrapper, and a bad argv raises `SystemExit`, which a bare
`except Exception` would let kill the whole tick. Recorded as `type(e).__name__` only;
skip-and-continue at the job level.

**Chaining within a tick:** due-evaluation loops to a fixpoint — after executing the
due set, re-evaluate; repeat until nothing new is due (bounded at 3 iterations, the
depth of the longest chain cftc → leads → promote). Without this, downstream jobs
would wait a tick per hop.

The cron side (documented in the README section this stage adds, not code) — note the
`.env` sourcing; scheduled `fred`/`eia`/`usda` jobs read keys from the environment:
```
*/15 * * * *  cd .../agentic-trading-bot && set -a && . ./.env && set +a && \
              uv run python main.py schedule --run >> schedule.log 2>&1
```

## CLI

```
uv run python main.py schedule --db schedule.db [--due | --run] \
  [--calendars-dir data/] [--window pre_open] [--retry job:trigger_key] [--keep-days 90]
```
`--due`: print due jobs as JSON lines (inspection, cron-dry-run). `--run`: execute
them. `run(db_path, calendars, registry=REGISTRY, now_iso=None, ...)` — the registry
itself is an injected seam, so tests drive fake jobs and never invoke real screeners.

## Prerequisite fix (invariant violation found during spec research)

`treasury_screener`'s `v_upcoming_auctions` uses `date('now')` — the only view in the
repo violating the injected-clock invariant. Before the scheduler consumes it, convert
it to the `calendar_now` pattern (tracked in FOLLOWUPS; independent one-line-ish fix).

## Testing

`tests/test_schedule_{catalog,extract,db_schema,db_write,db_views,run}.py` + registry
entry. Fixtures: monitor DBs built with `monitor_common.ensure_schema` + synthetic
events; fake registry recording invocations. Cases: DST boundary (a March/November
Friday), early-close gate shift, idempotency (second tick same `now_iso` runs
nothing), upstream-chains, max_attempts exhaustion, crash-recovery of stale `running`.

## Out of scope / deferred

Daemon mode; parallel job execution; notification on `v_failures`; backfill/catch-up
semantics beyond the natural "still due on next tick".
