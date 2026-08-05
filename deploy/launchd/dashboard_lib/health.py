"""Three pipeline-health layers ported from the retired daily_summary.py:
launchctl exit codes, log activity, and DB snapshot freshness. Structured
findings only -- data.json is published to public gh-pages, so raw log
lines never enter the payload (a subprocess can print anything, including a
URL with an API key).
"""

import datetime as dt
import re
import sqlite3
from pathlib import Path

PREFIX = "com.tradingbot."
# The section is built BY the dashboard job, which is running by definition
# while this module scans logs -- so it must never report itself as hung.
SELF_LOG = "dashboard.log"
_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
BAD_MARKERS = ("FAILED", "STALE", "Traceback", "Error:")

# How long a job may run before the digest calls it hung. INTERIM two-tier
# stopgap: replace with measured per-job values once env.sh's `end:` lines have
# accumulated (~2 weeks). A stopgap with no recorded end date becomes permanent.
#
# A threshold only matters for a job still plausibly running at 21:15 (the
# digest fires once, nightly) -- i.e. one that starts within roughly an hour
# of it. Measured gaps: dashboard 2min, advisor 3min, scorer 5min, composite
# 10min -- all safe under the default tier. `edgar` (20:30, 45min before the
# digest) is the only slow-tier entry that is actually load-bearing today;
# every other _SLOW_JOBS entry starts 2h-17h earlier; if still alive at
# digest time it would be flagged under either tier, so those are defensive
# against future schedule changes rather than currently load-bearing.
HUNG_DEFAULT_MIN = 15
HUNG_SLOW_MIN = 60
SLOW_JOBS = {
    "fred-vintages",  # ~80 API calls, ~1.7M rows re-upserted
    "preopen",  # one screener step, not the whole 4-step run, drives this budget
    "portfolio",  # headless `claude -p`
    "journal",  # headless `claude -p`
    "backtest",  # point-in-time replay
    "ftd-full",  # re-ingests 24 months
    "short-interest-full",  # re-ingests ~12 months
    "fundamentals-bulk",  # downloads + ingests a DERA quarterly ZIP
    "edgar",  # starts 45min before the digest AND has a designed sleep 900 retry pause
    "research-nightly",  # headless `claude -p` per ticker, ~20min each, up to 3
}

# Max acceptable age (days) of the newest snapshot, by DB filename. Defaults
# to 4 (daily jobs surviving a weekend + a holiday). Slower cadences:
MAX_AGE_DAYS = {
    "ats.db": 9,
    "backtest.db": 9,
    "cftc.db": 9,
    "eia.db": 9,
    "econ_calendar.db": 9,
    "fomc.db": 9,
    "sec_fundamentals.db": 9,
    "ftd.db": 10,
    "usda.db": 35,
    "market_calendar.db": 35,
}
DEFAULT_MAX_AGE_DAYS = 4

# Snapshot column holding the count of domain rows written by the newest run,
# per DB filename. A fresh snapshot whose count is 0 means a silent-empty
# fetch (see plan 002) -- flagged even though captured_at looks current. DBs
# absent from this map are not count-checked (freshness-only, as before).
ROW_COUNT_COL = {
    "ats.db": "row_count",
    "cboe_stats.db": "row_count",
    "cftc.db": "row_count",
    "composite.db": "signals_ok",
    "earnings.db": "event_count",
    "econ_calendar.db": "event_count",
    "edgar.db": "filing_count",
    "eia.db": "observation_count",
    "etfs.db": "universe_count",
    "fomc.db": "event_count",
    "fred.db": "observation_count",
    "ftd.db": "row_count",
    "market_calendar.db": "event_count",
    "nyfed.db": "row_count",
    "options.db": "row_count",
    "reddit.db": "ticker_count",
    "sec_fundamentals.db": "fact_count",
    "short_interest.db": "row_count",
    "short_volume.db": "row_count",
    "stocks.db": "universe_count",
    "treasury.db": "row_count",
    "usda.db": "observation_count",
}

# DBs that legitimately write zero-row snapshots on some runs -- never flag
# these for an empty count (probe days / bimonthly / empty-by-design domains).
EMPTY_OK = {
    "ftd.db",  # SEC fails-to-deliver probe days write zero-row snapshots
    "short_interest.db",  # FINRA short interest is bimonthly; off-cycle runs are empty
    "nyfed.db",  # some NY Fed domains (iorb, primary_dealer) are empty by design
}


def last_progress(path):
    """Timestamp of the most recent `start:` or `step:` line, or None.

    Returns a NAIVE datetime in LOCAL (Phoenix) time: wrapper logs are stamped
    by bash `date`, and build_summary compares against now_local. Do NOT route
    this through phx_date -- that converts UTC-stored instants and would be
    wrong here.

    A job progressing through env.sh's step_start markers must keep resetting
    its clock -- that is the correct hang semantic (a STUCK step should trip
    the tier; a job still moving through steps should not) -- so this counts
    `step:` lines as progress too, same as `start:`. The consequence: for a
    multi-step wrapper (cftc_weekly.sh, preopen_batch.sh) the age this
    returns is the CURRENT STEP's, not the whole run's, so the hung-job tier
    budgets a stuck step, not total runtime.
    """
    newest = None
    for line in path.read_text(errors="replace").splitlines():
        if "start:" not in line and "step:" not in line:
            continue
        m = _TS.match(line)
        if not m:
            continue
        try:
            ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if newest is None or ts > newest:
            newest = ts
    return newest


def scan_log(path: Path, since: dt.datetime) -> tuple[int, dict[str, int]]:
    """(runs_started, {marker: line count}) within the window. Counts only
    `start:` lines as a run (env.sh step_start emits `step:` for sub-steps,
    which must not inflate the headline). Untimestamped lines (tracebacks)
    inherit the in-window state of the last timestamped line. Returns marker
    COUNTS, never the lines themselves: this feeds a payload published to
    public gh-pages, and a log line can carry anything a subprocess printed."""
    runs = 0
    markers: dict[str, int] = {}
    in_window = False
    for line in path.read_text(errors="replace").splitlines():
        m = _TS.match(line)
        if m:
            ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            in_window = ts >= since
        if not in_window:
            continue
        if "start:" in line and m:
            runs += 1
        for marker in BAD_MARKERS:
            if marker in line:  # first match only: one line = one finding
                markers[marker] = markers.get(marker, 0) + 1
                break
    return runs, markers


def hung_jobs(running: set[str], now_local: dt.datetime, logs_dir: Path) -> list[dict[str, str]]:
    """[problem dicts] for jobs in `running` that have been running past their limit.

    `running` is a set of job names currently running (see running_jobs()).
    Membership in that set IS the running signal -- launchctl's exit-status
    column cannot supply one (see job_exit_codes), so without a set built
    from the PID column a hung job is invisible, and launchd will not
    re-spawn it while the instance is alive.

    A running job with NO determinable start (missing log, or a log with no
    parseable `start:`/`step:` marker) is reported rather than skipped -- a
    wrapper that hangs BEFORE reaching job_start (a stalled `source .env`,
    slow PATH resolution) would otherwise leave an empty log and stay
    invisible forever, which is the exact class of invisibility this feature
    exists to remove.

    Detection only: never kills or restarts anything.
    """
    problems = []
    for job in sorted(running):
        if f"{job}.log" == SELF_LOG:
            continue
        try:
            path = logs_dir / f"{job}.log"
            if not path.exists():
                problems.append(
                    {
                        "kind": "hung",
                        "target": job,
                        "detail": "running with no log — start time unknown",
                    }
                )
                continue
            started = last_progress(path)
            if started is None:
                problems.append(
                    {
                        "kind": "hung",
                        "target": job,
                        "detail": "running with an unparseable log — start time unknown",
                    }
                )
                continue
            minutes = (now_local - started).total_seconds() / 60
        except Exception as e:
            problems.append(
                {"kind": "hung", "target": job, "detail": f"hang check failed ({type(e).__name__})"}
            )
            continue
        limit = HUNG_SLOW_MIN if job in SLOW_JOBS else HUNG_DEFAULT_MIN
        if minutes > limit:
            problems.append(
                {
                    "kind": "hung",
                    "target": job,
                    "detail": f"running {int(minutes)}min (limit {limit}min) — possible hang",
                }
            )
    return problems


def stale_dbs(now_utc: dt.datetime, data_dir: Path) -> list[dict[str, str]]:
    problems = []
    for db in sorted(data_dir.glob("*.db")):
        try:
            with sqlite3.connect(db) as conn:
                latest = conn.execute("SELECT MAX(captured_at) FROM snapshots").fetchone()[0]
        except sqlite3.Error:
            continue  # not a snapshots-bearing DB; not ours to judge
        if latest is None:
            problems.append({"kind": "stale", "target": db.name, "detail": "no snapshots"})
            continue
        try:
            captured = dt.datetime.fromisoformat(latest)
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=dt.UTC)
            age = now_utc - captured
        except (ValueError, TypeError):
            problems.append(
                {"kind": "stale", "target": db.name, "detail": "unparseable captured_at"}
            )
            continue
        limit = MAX_AGE_DAYS.get(db.name, DEFAULT_MAX_AGE_DAYS)
        if age > dt.timedelta(days=limit):
            problems.append(
                {
                    "kind": "stale",
                    "target": db.name,
                    "detail": f"{age.days}d old (limit {limit}d)",
                }
            )
        col = ROW_COUNT_COL.get(db.name)
        if col and db.name not in EMPTY_OK:
            try:
                with sqlite3.connect(db) as conn:
                    n = conn.execute(
                        f"SELECT {col} FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1"
                    ).fetchone()[0]
            except sqlite3.Error:
                n = None  # column vanished / schema drift — skip the count check
            if n == 0:
                problems.append(
                    {
                        "kind": "empty",
                        "target": db.name,
                        "detail": "newest snapshot has 0 rows (empty fetch?)",
                    }
                )
    return problems
