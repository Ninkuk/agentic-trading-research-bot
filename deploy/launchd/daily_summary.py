"""Build and send the daily run summary over ntfy.

Reads three health layers (same as status.sh, but judged, not just listed):
  1. launchctl last-exit codes for every com.tradingbot.* job
  2. logs/*.log activity in the last 24h — runs started, FAILED/STALE lines
  3. data/*.db snapshot freshness vs. each DB's expected cadence

Run from the repo root (the launchd wrapper guarantees it). Exit 0 even on
an unhealthy summary — the notification IS the alert; only a failure to
notify exits non-zero so it surfaces in launchctl/status.sh.
"""
import datetime as dt
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.common import notify  # noqa: E402

LOGS = Path("logs")
DATA = Path("data")
PREFIX = "com.tradingbot."
_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
_BAD = ("FAILED", "STALE", "Traceback", "Error:")

# Max acceptable age (days) of the newest snapshot, by DB filename. Defaults
# to 4 (daily jobs surviving a weekend + a holiday). Slower cadences:
MAX_AGE_DAYS = {
    "ats.db": 9, "cftc.db": 9, "eia.db": 9, "econ_calendar.db": 9,
    "fomc.db": 9, "sec_fundamentals.db": 9, "ftd.db": 10,
    "usda.db": 35, "market_calendar.db": 35,
}
DEFAULT_MAX_AGE_DAYS = 4


def job_exit_codes():
    """{job-name: last exit code} from launchctl (None while running)."""
    out = subprocess.run(["launchctl", "list"], capture_output=True,
                         text=True).stdout
    codes = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].startswith(PREFIX):
            codes[parts[2][len(PREFIX):]] = (None if parts[1] == "-"
                                             else int(parts[1]))
    return codes


def scan_log(path, since):
    """(runs_started, [bad lines]) within the window. Untimestamped lines
    (e.g. tracebacks) inherit the in-window state of the last timestamped
    line, so a crash between two starts is attributed correctly."""
    runs, bad, in_window = 0, [], False
    for line in path.read_text(errors="replace").splitlines():
        m = _TS.match(line)
        if m:
            ts = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            in_window = ts >= since
        if not in_window:
            continue
        if "start:" in line and m:
            runs += 1
        if any(marker in line for marker in _BAD):
            bad.append(f"{path.stem}: {line.strip()[:160]}")
    return runs, bad


def stale_dbs(now):
    stale = []
    for db in sorted(DATA.glob("*.db")):
        try:
            with sqlite3.connect(db) as conn:
                latest = conn.execute(
                    "SELECT MAX(captured_at) FROM snapshots").fetchone()[0]
        except sqlite3.Error:
            continue  # not a snapshots-bearing DB; not ours to judge
        if latest is None:
            stale.append(f"{db.name}: no snapshots")
            continue
        age = now - dt.datetime.fromisoformat(latest)
        limit = MAX_AGE_DAYS.get(db.name, DEFAULT_MAX_AGE_DAYS)
        if age > dt.timedelta(days=limit):
            stale.append(f"{db.name}: {age.days}d old (limit {limit}d)")
    return stale


def build_summary(now_local, now_utc):
    total_runs, problems = 0, []

    codes = job_exit_codes()
    for job, code in sorted(codes.items()):
        if code not in (None, 0):
            problems.append(f"{job}: last exit {code}")

    since = now_local - dt.timedelta(hours=24)
    for log in sorted(LOGS.glob("*.log")):
        runs, bad = scan_log(log, since)
        total_runs += runs
        problems.extend(bad)

    problems.extend(stale_dbs(now_utc))

    healthy = not problems
    lines = [f"{total_runs} runs in the last 24h, "
             f"{len(codes)} jobs loaded."]
    lines += problems if problems else ["All healthy."]
    return healthy, "\n".join(lines[:30])


def main():
    healthy, summary = build_summary(dt.datetime.now(),
                                     dt.datetime.now(dt.timezone.utc))
    try:
        notify.send(summary,
                    title="trading-bot daily summary",
                    priority="default" if healthy else "high",
                    tags=["white_check_mark"] if healthy else ["warning"])
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
