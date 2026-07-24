"""MAX_AGE_DAYS must outlive each DB's scheduled run gap (install.py).

`stale_dbs` ages every data/*.db against MAX_AGE_DAYS with a 4-day default
sized for daily jobs, while install.py owns the real cadence — two parallel
registries that have drifted before: backtest shipped as a weekly Saturday
job with no MAX_AGE_DAYS entry, so the nightly summary false-alarmed
"backtest.db: 5d old (limit 4d)" every Wed-Fri night. This test derives each
DB's worst-case healthy age from the schedule itself so the next
slow-cadence job cannot ship without a matching limit.
"""

import sys
from itertools import pairwise
from pathlib import Path

# Both modules live in deploy/launchd (not a package); import them the same
# way the other daily_summary tests do.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402
import install  # noqa: E402


def _max_gap_days(intervals):
    """Worst-case days between consecutive runs of one StartCalendarInterval."""
    first = intervals[0]
    if "Weekday" in first:  # weekly()/hourly(): circular gap over the week
        days = sorted({e["Weekday"] for e in intervals})
        return max([b - a for a, b in pairwise(days)] + [7 - days[-1] + days[0]])
    if "Month" in first:  # yearly() carries Month+Day, so check Month first
        months = sorted({e["Month"] for e in intervals})
        gaps = [b - a for a, b in pairwise(months)] + [12 - months[-1] + months[0]]
        return 31 * max(gaps)
    days = sorted({e["Day"] for e in intervals})  # monthly()
    return max([b - a for a, b in pairwise(days)] + [31 - days[-1] + days[0]])


def _healthy_age_by_db():
    """db filename -> worst-case healthy age via its most frequent writer.

    Only jobs with an explicit --db in ProgramArguments are derivable; the
    script-driven slots (portfolio, journal, edgar, preopen, cftc) all write
    daily-or-faster DBs already covered by the 4-day default.
    """
    gaps = {}
    for prog_args, intervals in install.JOBS.values():
        if "--db" not in prog_args:
            continue
        db = Path(prog_args[prog_args.index("--db") + 1]).name
        gap = _max_gap_days(intervals)
        gaps[db] = min(gap, gaps.get(db, gap))
    return gaps


def test_max_age_limit_outlives_every_scheduled_run_gap():
    # Strictly greater: run hour precedes the 21:15 summary, so at limit ==
    # gap a healthy DB can already read gap-days-plus-hours old (the daily
    # default is 4 for a 3-day Fri->Mon gap for exactly this reason).
    violations = []
    for db, gap in sorted(_healthy_age_by_db().items()):
        limit = daily_summary.MAX_AGE_DAYS.get(db, daily_summary.DEFAULT_MAX_AGE_DAYS)
        if limit <= gap:
            violations.append(
                f"{db}: scheduled writer runs every {gap}d but stale_dbs limit is "
                f"{limit}d — add an entry to MAX_AGE_DAYS in daily_summary.py"
            )
    assert not violations, "\n".join(violations)


def test_schedule_derivation_sees_the_slow_jobs():
    # Guard the derivation itself: if install.py's arg shape changes and
    # --db stops being parseable, the coherence test would silently pass on
    # an empty dict. These three cadence classes must always be visible.
    gaps = _healthy_age_by_db()
    assert gaps["backtest.db"] == 7  # weekly Saturday
    assert gaps["fred.db"] <= 4  # daily writer governs over fred-vintages
    assert gaps["market_calendar.db"] >= 28  # monthly
