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
from the already-built monitors (`econ_calendar`, `earnings`, `fomc`,
`market_calendar`) plus static rules.

## Time model (the one place wall-clock legitimately enters)

`now_iso` is injected as everywhere else; the cron wrapper passes real time, tests
pass fixtures. ET conversion via stdlib `zoneinfo` (`America/New_York`) — DST handled
correctly, no third-party dependency. All trigger times below are ET. Trading-day and
early-close facts come from `market_calendar` (`is_trading_day(conn, d)` helper,
`v_early_closes`) — never hardcoded holiday math.

## Job catalog (v1)

`Job(name, trigger, argv_fn)` — trigger evaluated against `now_iso` + monitor DBs;
`trigger_key` is the identity that makes runs idempotent.

| Job | Trigger (clock 1: event-driven) | trigger_key |
|---|---|---|
| `cftc` | Friday ≥ 16:00 ET (COT posts ~15:30) | that Friday's date |
| `fred` | an `econ_calendar` event released today: `v_upcoming_releases` where `event_date = today` and now ≥ `release_time` + 15 min | `event_type:event_date` |
| `fundamentals`, `stocks` | a watched ticker's earnings event today (`v_upcoming_earnings`), evaluated once post-close 18:00 ET; plus a weekly Sunday baseline sweep | `earnings:date` / `weekly:date` |
| `earnings`, `econ_calendar`, `fomc`, `market_calendar`, `treasury` | daily maintenance, 07:00 ET | `daily:date` |
| `leads` | any of {`cftc`,`fred`,`fundamentals`,`stocks`} succeeded since the last `leads` run | `after:<upstream_job>:<upstream_trigger_key>` |
| `promote` | `leads` succeeded since last `promote` run | same pattern |

| Window (clock 2: fixed) | Trigger |
|---|---|
| `gate` pre-close | trading day, ≥ 15:30 ET (≥ 12:30 on early closes — from `v_early_closes`), runs once per day |
| `gate` pre-open (off by default) | trading day, ≥ 09:00 ET, `--window pre_open` |

The five-touchpoint intraday instinct is deliberately absent (research §6: mid-day
adds cost, not edge, at this data's cadence).

## Idempotency & state — `schedule.db`

```sql
job_runs(job TEXT NOT NULL, trigger_key TEXT NOT NULL,
         started_at TEXT NOT NULL, finished_at TEXT,
         status TEXT NOT NULL,               -- 'running' | 'ok' | 'error'
         error TEXT,                          -- type name only (secret hygiene)
         PRIMARY KEY (job, trigger_key));

snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT NOT NULL,
          due_count INTEGER, ran_count INTEGER);
```
A job is **due** iff its trigger holds AND no `job_runs` row exists for
`(job, trigger_key)` with status `ok`. An `error` row leaves the job due again on the
next tick (bounded by `max_attempts = 3` per trigger_key, then it stays failed until
`--retry job:key`). A stale `running` row older than 2 hours is treated as `error`
(crash recovery).

Views: `v_due` (what would run now — requires `set_now` single-row param table, same
`calendar_now` pattern as `monitor_common`), `v_recent_runs`, `v_failures`.

## Execution model

`--run` executes due jobs **in-process** via `registry.REGISTRY[name](argv)` — same
process, sequential, in catalog order (upstream before downstream so one tick can
carry cftc → leads → promote through). No subprocesses, no parallelism: total runtime
is dominated by polite rate limits anyway, and sequential means one WAL writer per DB.
Per-job failures are caught (`type(e).__name__` only), recorded, and don't stop the
tick — skip-and-continue at the job level.

The cron side (documented in the README section this stage adds, not code):
```
*/15 * * * *  cd .../agentic-trading-bot && uv run python main.py schedule --run >> schedule.log 2>&1
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
