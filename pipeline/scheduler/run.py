"""Two-clock scheduler: deterministic due-job evaluator + in-process executor.

Cron wrapper (external; sources .env so scheduled fred/eia/usda read keys):
    */15 * * * *  cd .../agentic-trading-bot && set -a && . ./.env && set +a && \\
                  uv run python main.py schedule --run >> schedule.log 2>&1
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.scheduler import catalog, db, extract


def _gated(sched_conn, job_name, trigger_key, now_iso) -> bool:
    """True when state says do NOT run: already ok, attempts exhausted, or a
    live running row (a stale one counts as crashed and no longer blocks)."""
    if db.ok_exists(sched_conn, job_name, trigger_key):
        return True
    if db.attempt_count(sched_conn, job_name, trigger_key) >= catalog.MAX_ATTEMPTS:
        return True
    return db.live_running(sched_conn, job_name, trigger_key, now_iso,
                           catalog.STALE_RUNNING_HOURS)


def _trigger_keys(job, ctx, sched_conn, window_pre_open) -> list:
    """The trigger_keys for which this job's trigger holds right now (state is
    checked separately). Jobs whose monitor DB is missing yield nothing."""
    today, now_hhmm, weekday = ctx["today"], ctx["now_hhmm"], ctx["weekday"]
    if job.kind == "daily":
        return [f"daily:{today}"] if now_hhmm >= catalog.DAILY_MAINTENANCE_ET else []
    if job.kind == "cftc_weekly":
        return [today] if weekday == 4 and now_hhmm >= catalog.COT_POST_ET else []
    if job.kind == "econ_release":
        if ctx["econ"] is None:
            return []
        return [f"{etype}:{edate}" for etype, edate in extract.econ_released(
            ctx["econ"], today, now_hhmm,
            catalog.RELEASE_LAG_MIN, catalog.DEFAULT_EVENT_TIME)]
    if job.kind == "earnings":
        keys = []
        if (ctx["earnings"] is not None and now_hhmm >= catalog.EARNINGS_EVAL_ET
                and extract.earnings_count(ctx["earnings"], today) > 0):
            keys.append(f"earnings:{today}")
        if weekday == 6:  # Sunday baseline sweep
            keys.append(f"weekly:{today}")
        return keys
    if job.kind == "chain":
        newest = db.newest_ok_among(sched_conn, job.after)
        if newest is None:
            return []
        up_job, up_key, up_finished = newest
        last = db.last_ok_finished_at(sched_conn, job.name)
        if last is not None and last >= up_finished:
            return []
        return [f"after:{up_job}:{up_key}"]
    if job.kind == "gate":
        if ctx["market"] is None or not extract.is_trading_day(ctx["market"], today):
            return []
        if job.window == "pre_close":
            at = (catalog.PRE_CLOSE_EARLY_ET
                  if extract.equity_early_close(ctx["market"], today)
                  else catalog.PRE_CLOSE_ET)
            return [f"pre_close:{today}"] if now_hhmm >= at else []
        if job.window == "pre_open":
            if not window_pre_open:
                return []
            return [f"pre_open:{today}"] if now_hhmm >= catalog.PRE_OPEN_ET else []
    return []


def compute_due(sched_conn, ctx, registry, data_dir,
                window_pre_open=False, now_iso=None) -> list:
    """Everything that should run right now, in catalog order. Deterministic:
    same now_iso + same DBs -> same answer. Unregistered targets are skipped
    (spec: job targets that don't exist yet simply aren't registered)."""
    due = []
    for job in catalog.JOBS:
        if job.target not in registry:
            continue
        for key in _trigger_keys(job, ctx, sched_conn, window_pre_open):
            if not _gated(sched_conn, job.name, key, now_iso):
                due.append({"job": job.name, "trigger_key": key,
                            "argv": catalog.argv_for(job, data_dir)})
    return due


def _open_monitors(data_dir, connect_ro):
    """Open the three monitor DBs read-only; a missing one becomes None with a
    class-name-only warning (skip-and-continue at the trigger level)."""
    conns = {}
    for key, fname in (("econ", catalog.MONITOR_DB_FILES["econ_calendar"]),
                       ("earnings", catalog.MONITOR_DB_FILES["earnings"]),
                       ("market", catalog.MONITOR_DB_FILES["market_calendar"])):
        try:
            conns[key] = connect_ro(f"{data_dir}/{fname}")
        except Exception as e:
            conns[key] = None
            print(f"warning: monitor db {key} unavailable: {type(e).__name__}",
                  file=sys.stderr)
    return conns


def _execute(sched_conn, item, registry, now_iso) -> bool:
    """Run one due item in-process, one attempt row per try. Catches
    (Exception, SystemExit): every registered main is an argparse wrapper and a
    bad argv raises SystemExit, which a bare `except Exception` would let kill
    the whole tick. Records type name only (secret hygiene)."""
    job = catalog.JOB_BY_NAME[item["job"]]
    attempt = db.start_attempt(sched_conn, item["job"], item["trigger_key"],
                               now_iso)
    try:
        registry[job.target](item["argv"])
    except (Exception, SystemExit) as e:
        db.finish_attempt(sched_conn, item["job"], item["trigger_key"], attempt,
                          now_iso, "error", type(e).__name__)
        print(f"warning: job {item['job']} failed: {type(e).__name__}",
              file=sys.stderr)
        return False
    db.finish_attempt(sched_conn, item["job"], item["trigger_key"], attempt,
                      now_iso, "ok")
    return True


def run(db_path, data_dir="data", registry=None,
        connect_ro=pipeline_common.connect_ro, now_iso=None, do_run=False,
        window_pre_open=False, retry=None, keep_days=None):
    """One scheduler tick. Returns (due_count, ran_count). --due mode
    (do_run=False) prints the due set as JSON lines and executes nothing."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    if registry is None:
        from registry import REGISTRY as _reg  # deferred: tests inject fakes
        registry = _reg

    today, now_hhmm, weekday = extract.et_parts(now_iso)
    monitors = _open_monitors(data_dir, connect_ro)
    ctx = {"today": today, "now_hhmm": now_hhmm, "weekday": weekday, **monitors}

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        due_total = ran_total = 0
        # (job, trigger_key) pairs already attempted THIS tick. compute_due is
        # tick-stateless (a failed attempt doesn't get excluded by _gated until
        # MAX_ATTEMPTS), so the fixpoint loop below must track this itself:
        # otherwise a failing non-chain job gets re-executed on every fixpoint
        # iteration of the same tick, burning its whole retry budget in one go.
        attempted_this_tick = set()

        if retry:
            job_name, _, key = retry.partition(":")
            job = catalog.JOB_BY_NAME.get(job_name)
            if job and job.target in registry and not db.ok_exists(conn, job_name, key):
                item = {"job": job_name, "trigger_key": key,
                        "argv": catalog.argv_for(job, data_dir)}
                due_total += 1
                if do_run:
                    attempted_this_tick.add((job_name, key))
                    if _execute(conn, item, registry, now_iso):
                        ran_total += 1

        for _ in range(catalog.FIXPOINT_LIMIT):
            due = compute_due(conn, ctx, registry, data_dir,
                              window_pre_open=window_pre_open, now_iso=now_iso)
            due = [item for item in due
                   if (item["job"], item["trigger_key"]) not in attempted_this_tick]
            if not due:
                break
            due_total += len(due)
            if not do_run:
                for item in due:
                    print(json.dumps(item, separators=(",", ":")))
                break  # --due: one evaluation, no state change, no fixpoint
            for item in due:
                attempted_this_tick.add((item["job"], item["trigger_key"]))
                if _execute(conn, item, registry, now_iso):
                    ran_total += 1

        db.write_snapshot(conn, now_iso, due_total, ran_total)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        for m in monitors.values():
            if m is not None:
                m.close()
        conn.close()
    return due_total, ran_total


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="schedule",
        description="Two-clock due-job evaluator (invoke from cron every ~15m)")
    p.add_argument("--db", default="schedule.db")
    p.add_argument("--data-dir", default="data",
                   help="directory holding the monitor + job DBs")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--due", action="store_true",
                      help="print due jobs as JSON lines, run nothing")
    mode.add_argument("--run", action="store_true", help="execute due jobs")
    p.add_argument("--window", default=None, choices=["pre_open"],
                   help="also evaluate the opt-in pre-open gate window")
    p.add_argument("--retry", default=None, metavar="job:trigger_key",
                   help="force one more attempt past the failure cap")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    due, ran = run(a.db, data_dir=a.data_dir, do_run=a.run,
                   window_pre_open=(a.window == "pre_open"), retry=a.retry,
                   keep_days=a.keep_days)
    print(f"{'ran' if a.run else 'due'}: {ran if a.run else due} "
          f"(due {due}) [schedule.db: {a.db}]")


if __name__ == "__main__":
    main()
