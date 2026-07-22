"""A hung job must not be invisible.

launchctl's exit-status column cannot tell a running job from an idle one --
it holds a RUNNING job's PREVIOUS exit status, not a sentinel, and reads 0
both for "exited cleanly" and "has never exited" (see status.sh). Without
running_jobs() reading the PID column instead, a job stuck forever is
silently skipped, and launchd will not re-spawn a StartCalendarInterval job
while an instance is alive -- so that job never runs again while every
nightly ntfy says "All healthy."
"""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

NOW = daily_summary.dt.datetime(2026, 7, 22, 21, 15, 0)


def _log(tmp_path, name, minutes_ago):
    """Write logs/<name>.log whose last `start:` line is `minutes_ago` old."""
    ts = NOW - daily_summary.dt.timedelta(minutes=minutes_ago)
    (tmp_path / f"{name}.log").write_text(f"[{ts:%Y-%m-%d %H:%M:%S}] start: {name}\n")


def test_running_job_within_limit_is_not_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", 5)
    assert daily_summary.hung_jobs({"fred"}, NOW) == []


def test_running_job_past_limit_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", 45)
    out = daily_summary.hung_jobs({"fred"}, NOW)
    assert len(out) == 1
    assert "fred" in out[0]


def test_slow_tier_job_is_given_the_longer_budget(tmp_path, monkeypatch):
    """30min would trip the default tier; a slow job must survive it. This
    fails if _SLOW_JOBS is ignored or collapsed into the default."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred-vintages", 30)
    assert daily_summary.hung_jobs({"fred-vintages"}, NOW) == []


def test_slow_tier_job_past_its_own_limit_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred-vintages", 90)
    assert len(daily_summary.hung_jobs({"fred-vintages"}, NOW)) == 1


def test_the_digest_never_reports_itself(tmp_path, monkeypatch):
    """daily-summary is running by definition while it builds the digest."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "daily-summary", 600)
    assert daily_summary.hung_jobs({"daily-summary"}, NOW) == []


def test_job_absent_from_running_set_is_never_reported(tmp_path, monkeypatch):
    """A set has no "finished" members -- only membership in `running` makes
    a job eligible to be reported. An idle job's old start line (however
    stale) is not evidence of a hang."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", 600)
    assert daily_summary.hung_jobs(set(), NOW) == []


def test_running_job_with_no_log_is_reported_not_silently_skipped(tmp_path, monkeypatch):
    """A wrapper that hangs BEFORE reaching job_start (stalled `source .env`,
    slow PATH resolution) leaves no log at all. That must not crash -- and
    must not stay silent either: silence here is the exact invisibility this
    feature exists to remove."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    out = daily_summary.hung_jobs({"ghost"}, NOW)
    assert len(out) == 1
    assert "ghost" in out[0]


def test_running_job_with_unparseable_log_is_reported_not_silently_skipped(tmp_path, monkeypatch):
    """A log with no parseable start marker (empty, or garbage) must not
    crash, and -- same reasoning as the no-log case -- must not be silently
    dropped either."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    (tmp_path / "empty.log").write_text("")
    (tmp_path / "garbage.log").write_text("no timestamp here\n[not-a-date] start: x\n")
    out = daily_summary.hung_jobs({"empty", "garbage"}, NOW)
    assert len(out) == 2
    assert any("empty" in line for line in out)
    assert any("garbage" in line for line in out)


def test_last_start_wins_over_earlier_ones(tmp_path, monkeypatch):
    """A log accumulates runs; only the most recent start: matters."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    old = NOW - daily_summary.dt.timedelta(minutes=600)
    recent = NOW - daily_summary.dt.timedelta(minutes=3)
    (tmp_path / "fred.log").write_text(
        f"[{old:%Y-%m-%d %H:%M:%S}] start: fred\n"
        f"[{old:%Y-%m-%d %H:%M:%S}] end: fred (2s, exit 0)\n"
        f"[{recent:%Y-%m-%d %H:%M:%S}] start: fred\n"
    )
    assert daily_summary.hung_jobs({"fred"}, NOW) == []


def test_directory_shaped_log_produces_a_visible_failure_not_a_crash(tmp_path, monkeypatch):
    """A degenerate log -- here, a DIRECTORY named <job>.log -- raises
    IsADirectoryError on read. That must surface as a visible problem line,
    never propagate, and per this repo's secret-hygiene rule the message may
    carry the exception TYPE NAME only (never str(e)/repr(e))."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    (tmp_path / "ghostjob.log").mkdir()
    out = daily_summary.hung_jobs({"ghostjob"}, NOW)
    assert out == ["ghostjob: hang check failed (IsADirectoryError)"]


def test_boundary_at_exactly_the_limit_is_not_flagged(tmp_path, monkeypatch):
    """The chosen inequality is `>`, not `>=`: a job running exactly at its
    limit has not yet exceeded it."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", daily_summary._HUNG_DEFAULT_MIN)
    assert daily_summary.hung_jobs({"fred"}, NOW) == []


def test_scan_log_counts_only_start_lines_as_runs(tmp_path):
    """step: lines are per-step progress markers (cftc_weekly.sh: one per
    family, preopen_batch.sh: one per screener), not separate runs -- scan_log
    must count only start: lines toward the "N runs in 24h" headline, or a
    single cftc run would inflate the count 3x (preopen: 4x)."""
    since = NOW - daily_summary.dt.timedelta(hours=24)
    ts = NOW - daily_summary.dt.timedelta(minutes=10)
    path = tmp_path / "cftc.log"
    path.write_text(
        f"[{ts:%Y-%m-%d %H:%M:%S}] start: cftc\n"
        f"[{ts:%Y-%m-%d %H:%M:%S}] step: cftc --family tff\n"
        f"[{ts:%Y-%m-%d %H:%M:%S}] step: cftc --family disaggregated\n"
        f"[{ts:%Y-%m-%d %H:%M:%S}] step: cftc --family financial\n"
    )
    runs, bad = daily_summary.scan_log(path, since)
    assert runs == 1
    assert bad == []


def test_last_progress_returns_the_newest_step_marker(tmp_path):
    """A multi-step wrapper (cftc_weekly.sh, preopen_batch.sh) emits one
    `start:` line for the whole run, then a `step:` line per sub-step.
    last_progress must return the newest of EITHER, so a job still
    progressing through steps keeps resetting its clock -- the age reported
    is the current step's, not the whole run's."""
    start = NOW - daily_summary.dt.timedelta(minutes=20)
    step = NOW - daily_summary.dt.timedelta(minutes=2)
    path = tmp_path / "cftc.log"
    path.write_text(
        f"[{start:%Y-%m-%d %H:%M:%S}] start: cftc\n"
        f"[{step:%Y-%m-%d %H:%M:%S}] step: cftc --family tff\n"
    )
    assert daily_summary.last_progress(path) == step


def test_running_jobs_detects_running_via_pid_column_not_status_column(monkeypatch):
    """The captured line that motivated this fix: a RUNNING job (reddit-intraday,
    mid-run) reads a real PID in column 0 and 0 -- not a sentinel -- in the
    exit-status column, identically to an idle job (fred). Only the PID
    column distinguishes them."""
    fake_stdout = "2703\t0\tcom.tradingbot.reddit-intraday\n-\t0\tcom.tradingbot.fred\n"

    class FakeResult:
        stdout = fake_stdout

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(daily_summary.subprocess, "run", fake_run)
    assert daily_summary.running_jobs() == {"reddit-intraday"}


def test_edgar_45min_into_its_designed_retry_sleep_is_not_flagged(tmp_path, monkeypatch):
    """edgar starts at 20:30, 45min before the 21:15 digest, and
    edgar_daily.sh's `sleep 900` retry pause is a DESIGNED wait, not a hang.
    Under the 15min default tier this would false-alarm every time SEC
    throttles edgar into its retry sleep."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "edgar", 45)
    assert daily_summary.hung_jobs({"edgar"}, NOW) == []


def test_every_slow_job_name_is_a_real_job():
    """A typo here makes that tier silently never apply -- no error anywhere.

    pyproject sets pythonpath = ["."], so deploy.launchd.install imports from
    the repo root without any sys.path juggling. Importing it is side-effect
    free: install.py only touches launchctl under `if __name__ == "__main__"`.
    """
    from deploy.launchd.install import JOBS

    assert set(JOBS) >= daily_summary._SLOW_JOBS


def _summary(tmp_path, monkeypatch, running, codes=None):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)  # no DBs -> no staleness noise
    monkeypatch.setattr(daily_summary, "job_exit_codes", lambda: codes or {})
    monkeypatch.setattr(daily_summary, "running_jobs", lambda: running)
    monkeypatch.setattr(daily_summary, "signals_digest", lambda: [])
    monkeypatch.setattr(daily_summary, "advisor_digest", lambda: [])
    return daily_summary.build_summary(NOW, daily_summary.dt.datetime.now(daily_summary.dt.UTC))


def test_hung_job_reaches_the_digest_and_marks_it_unhealthy(tmp_path, monkeypatch):
    _log(tmp_path, "fred", 45)
    healthy, summary = _summary(tmp_path, monkeypatch, {"fred"})
    assert "fred" in summary
    assert "possible hang" in summary
    assert not healthy


def test_healthy_running_job_leaves_the_digest_green(tmp_path, monkeypatch):
    _log(tmp_path, "fred", 2)
    healthy, summary = _summary(tmp_path, monkeypatch, {"fred"})
    assert "possible hang" not in summary
    assert healthy


def test_jobs_running_normally_at_digest_time_are_not_flagged(tmp_path, monkeypatch):
    """composite (21:05), scorer (21:10), advisor (21:12) and dashboard (21:13)
    can still be running when the digest fires at 21:15. All are far under the
    15min default tier, so none may be reported."""
    for job, started in (("composite", 10), ("scorer", 5), ("advisor", 3), ("dashboard", 2)):
        _log(tmp_path, job, started)
    running = {"composite", "scorer", "advisor", "dashboard"}
    healthy, summary = _summary(tmp_path, monkeypatch, running)
    assert "possible hang" not in summary
    assert healthy
