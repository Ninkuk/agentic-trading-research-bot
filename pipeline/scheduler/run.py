"""Two-clock scheduler: deterministic due-job evaluator + in-process executor.

Cron wrapper (external; sources .env so scheduled fred/eia/usda read keys):
    */15 * * * *  cd .../agentic-trading-bot && set -a && . ./.env && set +a && \\
                  uv run python main.py schedule --run >> schedule.log 2>&1
"""
import sys

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
