"""A hung job must not be invisible.

launchctl's exit-status column cannot tell a running job from an idle one --
it holds a RUNNING job's PREVIOUS exit status, not a sentinel, and reads 0
both for "exited cleanly" and "has never exited" (see status.sh). Without
running_jobs() reading the PID column instead, a job stuck forever is
silently skipped, and launchd will not re-spawn a StartCalendarInterval job
while an instance is alive -- so that job never runs again while the
dashboard's health section keeps reporting "All healthy."
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import health  # noqa: E402

NOW = health.dt.datetime(2026, 7, 22, 21, 13, 0)


def _log(tmp_path, name, minutes_ago):
    """Write logs/<name>.log whose last `start:` line is `minutes_ago` old."""
    ts = NOW - health.dt.timedelta(minutes=minutes_ago)
    (tmp_path / f"{name}.log").write_text(f"[{ts:%Y-%m-%d %H:%M:%S}] start: {name}\n")


def test_running_job_within_limit_is_not_reported(tmp_path):
    _log(tmp_path, "fred", 5)
    assert health.hung_jobs({"fred"}, NOW, tmp_path) == []


def test_running_job_past_limit_is_reported(tmp_path):
    _log(tmp_path, "fred", 45)
    out = health.hung_jobs({"fred"}, NOW, tmp_path)
    assert len(out) == 1
    assert out[0]["target"] == "fred"


def test_slow_tier_job_is_given_the_longer_budget(tmp_path):
    """30min would trip the default tier; a slow job must survive it. This
    fails if SLOW_JOBS is ignored or collapsed into the default."""
    _log(tmp_path, "fred-vintages", 30)
    assert health.hung_jobs({"fred-vintages"}, NOW, tmp_path) == []


def test_slow_tier_job_past_its_own_limit_is_reported(tmp_path):
    _log(tmp_path, "fred-vintages", 90)
    assert len(health.hung_jobs({"fred-vintages"}, NOW, tmp_path)) == 1


def test_the_dashboard_job_never_reports_itself(tmp_path):
    """dashboard is running by definition while it builds the health section."""
    _log(tmp_path, "dashboard", 600)
    assert health.hung_jobs({"dashboard"}, NOW, tmp_path) == []


def test_job_absent_from_running_set_is_never_reported(tmp_path):
    """A set has no "finished" members -- only membership in `running` makes
    a job eligible to be reported. An idle job's old start line (however
    stale) is not evidence of a hang."""
    _log(tmp_path, "fred", 600)
    assert health.hung_jobs(set(), NOW, tmp_path) == []


def test_running_job_with_no_log_is_reported_not_silently_skipped(tmp_path):
    """A wrapper that hangs BEFORE reaching job_start (stalled `source .env`,
    slow PATH resolution) leaves no log at all. That must not crash -- and
    must not stay silent either: silence here is the exact invisibility this
    feature exists to remove."""
    out = health.hung_jobs({"ghost"}, NOW, tmp_path)
    assert len(out) == 1
    assert out[0]["target"] == "ghost"


def test_running_job_with_unparseable_log_is_reported_not_silently_skipped(tmp_path):
    """A log with no parseable start marker (empty, or garbage) must not
    crash, and -- same reasoning as the no-log case -- must not be silently
    dropped either."""
    (tmp_path / "empty.log").write_text("")
    (tmp_path / "garbage.log").write_text("no timestamp here\n[not-a-date] start: x\n")
    out = health.hung_jobs({"empty", "garbage"}, NOW, tmp_path)
    assert len(out) == 2
    assert any(p["target"] == "empty" for p in out)
    assert any(p["target"] == "garbage" for p in out)


def test_last_start_wins_over_earlier_ones(tmp_path):
    """A log accumulates runs; only the most recent start: matters."""
    old = NOW - health.dt.timedelta(minutes=600)
    recent = NOW - health.dt.timedelta(minutes=3)
    (tmp_path / "fred.log").write_text(
        f"[{old:%Y-%m-%d %H:%M:%S}] start: fred\n"
        f"[{old:%Y-%m-%d %H:%M:%S}] end: fred (2s, exit 0)\n"
        f"[{recent:%Y-%m-%d %H:%M:%S}] start: fred\n"
    )
    assert health.hung_jobs({"fred"}, NOW, tmp_path) == []


def test_directory_shaped_log_produces_a_visible_failure_not_a_crash(tmp_path):
    """A degenerate log -- here, a DIRECTORY named <job>.log -- raises
    IsADirectoryError on read. That must surface as a visible problem, never
    propagate, and per this repo's secret-hygiene rule the detail may carry
    the exception TYPE NAME only (never str(e)/repr(e))."""
    (tmp_path / "ghostjob.log").mkdir()
    out = health.hung_jobs({"ghostjob"}, NOW, tmp_path)
    assert out == [
        {"kind": "hung", "target": "ghostjob", "detail": "hang check failed (IsADirectoryError)"}
    ]


def test_boundary_at_exactly_the_limit_is_not_flagged(tmp_path):
    """The chosen inequality is `>`, not `>=`: a job running exactly at its
    limit has not yet exceeded it."""
    _log(tmp_path, "fred", health.HUNG_DEFAULT_MIN)
    assert health.hung_jobs({"fred"}, NOW, tmp_path) == []


def test_last_progress_returns_the_newest_step_marker(tmp_path):
    """A multi-step wrapper (cftc_weekly.sh, preopen_batch.sh) emits one
    `start:` line for the whole run, then a `step:` line per sub-step.
    last_progress must return the newest of EITHER, so a job still
    progressing through steps keeps resetting its clock -- the age reported
    is the current step's, not the whole run's."""
    start = NOW - health.dt.timedelta(minutes=20)
    step = NOW - health.dt.timedelta(minutes=2)
    path = tmp_path / "cftc.log"
    path.write_text(
        f"[{start:%Y-%m-%d %H:%M:%S}] start: cftc\n"
        f"[{step:%Y-%m-%d %H:%M:%S}] step: cftc --family tff\n"
    )
    assert health.last_progress(path) == step


def test_edgar_43min_into_its_designed_retry_sleep_is_not_flagged(tmp_path):
    """edgar starts at 20:30, 43min before the 21:13 dashboard health
    snapshot, and edgar_daily.sh's `sleep 900` retry pause is a DESIGNED
    wait, not a hang. Under the 15min default tier this would false-alarm
    every time SEC throttles edgar into its retry sleep."""
    _log(tmp_path, "edgar", 43)
    assert health.hung_jobs({"edgar"}, NOW, tmp_path) == []


def test_every_slow_job_name_is_a_real_job():
    """A typo here makes that tier silently never apply -- no error anywhere.

    pyproject sets pythonpath = ["."], so deploy.launchd.install imports from
    the repo root without any sys.path juggling. Importing it is side-effect
    free: install.py only touches launchctl under `if __name__ == "__main__"`.
    """
    from deploy.launchd.install import JOBS

    assert set(JOBS) >= health.SLOW_JOBS
