"""Three pipeline-health layers -- launchctl exit codes, log activity, and DB
snapshot freshness -- assembled into the dashboard's nightly health section.
Structured findings only -- data.json is published to public gh-pages, so raw
log lines never enter the payload (a subprocess can print anything, including
a URL with an API key).
"""

import datetime as dt
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

PREFIX = "com.tradingbot."
# The section is built BY the dashboard job, which is running by definition
# while this module scans logs -- so it must never report itself as hung.
SELF_LOG = "dashboard.log"
_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
BAD_MARKERS = ("FAILED", "STALE", "Traceback", "Error:")

# How long a job may run before the health section calls it hung. INTERIM
# two-tier stopgap: replace with measured per-job values once env.sh's `end:`
# lines have accumulated. A threshold only matters for a job still plausibly
# running when the nightly dashboard job builds the health section; `edgar`
# is the only slow-tier entry load-bearing today -- the rest start hours
# earlier and are defensive against future schedule changes.
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
    "edgar",  # starts 43min before the health snapshot AND has a designed sleep 900 retry pause
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


def job_exit_codes():
    """{job-name: launchctl's last-exit-status column}.

    NOT a running-vs-not indicator, despite appearances. `launchctl list`
    prints 0 in this column both for "exited cleanly" and for "has never
    exited" (see status.sh), and -- the part that matters here -- a job that
    is CURRENTLY RUNNING still shows its PREVIOUS exit status in this column,
    not a sentinel. Verified live: all 35 jobs read 0 here, including one
    caught mid-run. Use running_jobs() for a running/not signal instead.
    """
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    codes = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].startswith(PREFIX):
            try:
                code = None if parts[1] == "-" else int(parts[1])
            except ValueError:
                continue
            codes[parts[2][len(PREFIX) :]] = code
    return codes


def running_jobs():
    """{job names} currently running, per launchctl's PID column.

    `launchctl list`'s three columns are PID, last-exit-status, label. As
    job_exit_codes documents, the exit-status column is ambiguous -- 0 means
    both "exited cleanly" and "never exited", and it holds a RUNNING job's
    PREVIOUS status, not a sentinel -- so it cannot answer "is this running
    right now". The PID column can: a running job shows a real PID there, an
    idle one shows "-". status.sh resolves the same ambiguity via
    `launchctl print` instead; this resolves it via the PID column so
    build_health can check all jobs with one `launchctl list` call here (a
    second, separate call is made by job_exit_codes() -- a job that exits
    between the two is simply not reported that snapshot; harmless, since
    it self-corrects the next time the health section is built).
    """
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    running = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].startswith(PREFIX) and parts[0] != "-":
            running.add(parts[2][len(PREFIX) :])
    return running


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


def build_health(
    logs_dir: Path, data_dir: Path, now_local: dt.datetime, now_utc: dt.datetime
) -> dict[str, Any]:
    """The three health layers as one structured payload. `now_local` is
    NAIVE Phoenix time (wrapper logs are stamped by bash `date`); `now_utc`
    is aware -- snapshot timestamps are stored UTC. Problems carry only
    code-formatted strings (job/db names, counts, limits) -- never raw log
    content; this document is published to public gh-pages."""
    problems: list[dict[str, str]] = []
    since = now_local - dt.timedelta(hours=24)

    codes = job_exit_codes()
    for job, code in sorted(codes.items()):
        if code in (None, 0):
            continue
        # launchctl holds the code until the job's NEXT run, so a weekday-only
        # job that failed Friday would re-red the weekend with no new
        # information. Report only while the run that produced it is in-window.
        log = logs_dir / f"{job}.log"
        progress = last_progress(log) if log.exists() else None
        if log.exists() and progress is not None and progress < since:
            continue
        problems.append({"kind": "exit", "target": job, "detail": f"last exit {code}"})

    problems.extend(hung_jobs(running_jobs(), now_local, logs_dir))

    total_runs = 0
    for log in sorted(logs_dir.glob("*.log")):
        if log.name == SELF_LOG:  # the dashboard job is running as it builds this
            continue
        try:
            runs, markers = scan_log(log, since)
        except Exception as e:
            # A degenerate entry (directory, unreadable permissions, a log
            # rotated out from under us) must not blank every other finding
            # -- report it and keep going, same idiom as hung_jobs.
            problems.append(
                {"kind": "log", "target": log.stem, "detail": f"scan failed ({type(e).__name__})"}
            )
            continue
        total_runs += runs
        for marker, count in sorted(markers.items()):
            noun = "line" if count == 1 else "lines"
            problems.append(
                {"kind": "log", "target": log.stem, "detail": f"{count} {marker} {noun} in 24h"}
            )

    problems.extend(stale_dbs(now_utc, data_dir))
    return {
        "healthy": not problems,
        "runs_24h": total_runs,
        "jobs_loaded": len(codes),
        "problems": problems,
    }
