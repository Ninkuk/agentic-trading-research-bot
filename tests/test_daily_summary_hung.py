"""A hung job must not be invisible.

launchctl reports a running job's exit code as None, and build_summary's check
is `if code not in (None, 0)` -- so a job stuck forever is silently skipped.
launchd will not re-spawn a StartCalendarInterval job while an instance is
alive, so that job never runs again while every nightly ntfy says "All healthy."
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
    assert daily_summary.hung_jobs({"fred": None}, NOW) == []


def test_running_job_past_limit_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", 45)
    out = daily_summary.hung_jobs({"fred": None}, NOW)
    assert len(out) == 1
    assert "fred" in out[0]


def test_slow_tier_job_is_given_the_longer_budget(tmp_path, monkeypatch):
    """30min would trip the default tier; a slow job must survive it. This
    fails if _SLOW_JOBS is ignored or collapsed into the default."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred-vintages", 30)
    assert daily_summary.hung_jobs({"fred-vintages": None}, NOW) == []


def test_slow_tier_job_past_its_own_limit_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred-vintages", 90)
    assert len(daily_summary.hung_jobs({"fred-vintages": None}, NOW)) == 1


def test_the_digest_never_reports_itself(tmp_path, monkeypatch):
    """daily-summary is running by definition while it builds the digest."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "daily-summary", 600)
    assert daily_summary.hung_jobs({"daily-summary": None}, NOW) == []


def test_finished_job_is_never_reported(tmp_path, monkeypatch):
    """Only code None means running. A job that exited hours ago is not hung."""
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    _log(tmp_path, "fred", 600)
    assert daily_summary.hung_jobs({"fred": 0}, NOW) == []
    assert daily_summary.hung_jobs({"fred": 1}, NOW) == []


def test_missing_log_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    assert daily_summary.hung_jobs({"ghost": None}, NOW) == []


def test_empty_and_unparseable_logs_do_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    (tmp_path / "empty.log").write_text("")
    (tmp_path / "garbage.log").write_text("no timestamp here\n[not-a-date] start: x\n")
    assert daily_summary.hung_jobs({"empty": None, "garbage": None}, NOW) == []


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
    assert daily_summary.hung_jobs({"fred": None}, NOW) == []


def test_every_slow_job_name_is_a_real_job():
    """A typo here makes that tier silently never apply -- no error anywhere.

    pyproject sets pythonpath = ["."], so deploy.launchd.install imports from
    the repo root without any sys.path juggling. Importing it is side-effect
    free: install.py only touches launchctl under `if __name__ == "__main__"`.
    """
    from deploy.launchd.install import JOBS

    assert set(JOBS) >= daily_summary._SLOW_JOBS
