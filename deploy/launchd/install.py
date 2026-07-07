"""Generate and install the launchd schedule for all screeners/monitors.

Usage:
    python deploy/launchd/install.py            # write plists + (re)load them
    python deploy/launchd/install.py --uninstall
    python deploy/launchd/install.py --dry-run  # write/print plists, no launchctl

All times are local (America/Phoenix on this machine, fixed year-round).
Slot rationale lives with the cadence plan; the invariants encoded here:
  * SEC-touching jobs (edgar, ftd, fundamentals, earnings-in-preopen) each
    get a distinct hour — the shared rate limiter is per-process, so
    concurrent jobs would double-dip SEC's per-IP cap.
  * The pre-open batch is one serialized process (see preopen_batch.sh).
  * Weekday key: 0=Sunday .. 6=Saturday.
"""

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "deploy" / "launchd"
LOGS = REPO / "logs"
AGENTS = Path.home() / "Library" / "LaunchAgents"
PREFIX = "com.tradingbot"

MON_FRI = [1, 2, 3, 4, 5]


def weekly(weekdays, hour, minute):
    return [{"Weekday": w, "Hour": hour, "Minute": minute} for w in weekdays]


def monthly(days, hour, minute):
    return [{"Day": d, "Hour": hour, "Minute": minute} for d in days]


def hourly(weekdays, hours, minute):
    return [{"Weekday": w, "Hour": h, "Minute": minute} for w in weekdays for h in hours]


def yearly(months, day, hour, minute):
    return [{"Month": m, "Day": day, "Hour": hour, "Minute": minute} for m in months]


def job(name, *args):
    return ["/bin/bash", str(SCRIPTS / "run_job.sh"), name, "--db", f"data/{name}.db", *args]


def script(basename):
    return ["/bin/bash", str(SCRIPTS / basename)]


# name -> (ProgramArguments, StartCalendarInterval)
JOBS = {
    # -- intraday, weekdays (market hours 6:30am-2:00pm Phx across seasons) --
    "options-intraday": (job("options", "--keep-days", "90"), hourly(MON_FRI, range(6, 14), 30)),
    "reddit-intraday": (job("reddit", "--keep-days", "90"), hourly(MON_FRI, range(6, 14), 35)),
    # -- daily, weekdays --
    "preopen": (script("preopen_batch.sh"), weekly(MON_FRI, 4, 0)),
    "nyfed": (job("nyfed"), weekly(MON_FRI, 11, 30)),
    "portfolio": (script("portfolio_snapshot.sh"), weekly(MON_FRI, 14, 30)),
    "journal": (script("journal_sync.sh"), weekly(MON_FRI, 14, 40)),
    "options-close": (job("options", "--keep-days", "90"), weekly(MON_FRI, 14, 45)),
    "treasury": (job("treasury"), weekly(MON_FRI, 16, 30)),
    "fred": (job("fred"), weekly(MON_FRI, 16, 40)),
    "cboe-stats": (job("cboe_stats"), weekly(MON_FRI, 18, 0)),
    "short-volume": (job("short_volume"), weekly(MON_FRI, 18, 15)),
    "short-interest": (job("short_interest"), weekly(MON_FRI, 18, 30)),
    "edgar": (script("edgar_daily.sh"), weekly(MON_FRI, 20, 30)),
    # -- weekly --
    "econ-calendar": (job("econ_calendar"), weekly([1], 5, 0)),
    "fomc": (job("fomc"), weekly([1], 5, 10)),
    "ats": (job("ats"), weekly([1], 18, 45)),
    "eia": (job("eia"), weekly([3, 4, 5], 10, 15)),
    "cftc": (script("cftc_weekly.sh"), weekly([5], 14, 15)),
    "fundamentals": (
        [
            "/bin/bash",
            str(SCRIPTS / "run_job.sh"),
            "fundamentals",
            "--db",
            "data/sec_fundamentals.db",
        ],
        weekly([6], 6, 0),
    ),
    "ftd": (job("ftd"), weekly([0], 7, 0)),
    # -- monthly --
    "market-calendar": (job("market_calendar"), monthly([1], 5, 0)),
    "usda-nass": (job("usda"), monthly([2], 10, 15)),
    "usda-wasde": (job("usda", "--wasde"), monthly([12, 16], 10, 15)),
    # Revision re-absorption: ftd and short_interest re-fetch only ~1 month
    # of trailing periods on their weekly/daily runs, but SEC reposts FTD
    # half-months and FINRA corrects settlements later than that. A monthly
    # --full re-ingests the whole retention window; the replace-by-period
    # writers absorb any repost.
    "ftd-full": (job("ftd", "--full"), monthly([15], 8, 0)),
    "short-interest-full": (job("short_interest", "--full"), monthly([15], 19, 0)),
    # -- quarterly / yearly --
    # DERA quarterly ZIP lands ~6wk after quarter end; each ZIP carries the
    # amendments/restatements *filed* that quarter, which the weekly frames
    # job (current quarter only) never re-reads.
    "fundamentals-bulk": (
        [
            "/bin/bash",
            str(SCRIPTS / "run_job.sh"),
            "fundamentals",
            "--db",
            "data/sec_fundamentals.db",
            "--bulk",
        ],
        yearly([2, 5, 8, 11], 20, 9, 0),
    ),
    # The hand-transcribed holiday seed in market_calendar/catalog.py ends
    # 2027-12; --refresh merges live NYSE/SIFMA pages over it and fails
    # loudly on page drift (isolated here so drift can't break the seed-only
    # run). Must run every month, 30min after the seed job: each run does a
    # replace_forward_window, so the seed-only run wipes any refresh-added
    # events and this job re-adds them.
    "market-calendar-refresh": (job("market_calendar", "--refresh"), monthly([1], 5, 30)),
    # -- combine (every day, after all collectors incl. edgar's 15-min
    #    failure retry; before the nightly summary) --
    "composite": (job("composite", "--keep-days", "365"), weekly(range(7), 21, 5)),
    "scorer": (job("scorer", "--keep-days", "365"), weekly(range(7), 21, 10)),
    "advisor": (job("advisor", "--keep-days", "365"), weekly(range(7), 21, 12)),
    # -- observability (every day, after the 8:30pm edgar run + retry) --
    "daily-summary": (script("daily_summary.sh"), weekly(range(7), 21, 15)),
}


def label(name):
    return f"{PREFIX}.{name}"


def plist_path(name):
    return AGENTS / f"{label(name)}.plist"


def build(name, program_args, intervals):
    log = str(LOGS / f"{name}.log")
    return {
        "Label": label(name),
        "ProgramArguments": program_args,
        "WorkingDirectory": str(REPO),
        "StartCalendarInterval": intervals,
        "StandardOutPath": log,
        "StandardErrorPath": log,
    }


def launchctl(*args, check=False):
    return subprocess.run(["launchctl", *args], check=check, capture_output=True, text=True)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    uid = subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip()
    domain = f"gui/{uid}"

    if a.uninstall:
        for name in JOBS:
            launchctl("bootout", f"{domain}/{label(name)}")
            plist_path(name).unlink(missing_ok=True)
            print(f"removed {label(name)}")
        return

    AGENTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    for name, (program_args, intervals) in JOBS.items():
        path = plist_path(name)
        with open(path, "wb") as f:
            plistlib.dump(build(name, program_args, intervals), f)
        if a.dry_run:
            print(f"wrote {path} ({len(intervals)} intervals)")
            continue
        launchctl("bootout", f"{domain}/{label(name)}")  # ok if not loaded
        r = launchctl("bootstrap", domain, str(path))
        status = "loaded" if r.returncode == 0 else f"FAILED: {r.stderr.strip()}"
        print(f"{label(name)}: {status}")


if __name__ == "__main__":
    sys.exit(main())
