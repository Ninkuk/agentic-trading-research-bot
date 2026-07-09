"""The digest must not read its own log.

`build_summary` writes every problem it finds into logs/daily-summary.log (the
launchd StandardOutPath). If the next night's scan re-reads that file, each
problem is reported again -- prefixed `daily-summary:` -- and written again,
so a single transient failure keeps the nightly alert red forever. The alert
is only useful if it goes green once the underlying job recovers.
"""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


def _summary(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)  # no DBs -> no staleness noise
    monkeypatch.setattr(daily_summary, "job_exit_codes", lambda: {})
    monkeypatch.setattr(daily_summary, "signals_digest", lambda: [])
    monkeypatch.setattr(daily_summary, "advisor_digest", lambda: [])
    now = daily_summary.dt.datetime(2026, 7, 8, 21, 15, 0)
    return daily_summary.build_summary(now, daily_summary.dt.datetime.now(daily_summary.dt.UTC))


def test_yesterdays_digest_does_not_resurface_as_todays_problem(tmp_path, monkeypatch):
    """A recovered job's old STALE line, echoed into daily-summary.log by the
    previous run, must not count as a problem today."""
    (tmp_path / "daily-summary.log").write_text(
        "[2026-07-08 21:15:05] start: daily summary\n"
        "portfolio: [2026-07-08 14:30:43] STALE: no portfolio snapshot in the last 2h\n"
    )
    healthy, summary = _summary(tmp_path, monkeypatch)
    assert "daily-summary:" not in summary
    assert healthy


def test_a_real_job_log_still_reports_its_problem(tmp_path, monkeypatch):
    """The exclusion is scoped to the digest's own log -- every other job log
    is still scanned."""
    (tmp_path / "portfolio.log").write_text(
        "[2026-07-08 21:14:00] start: portfolio snapshot\n"
        "[2026-07-08 21:14:30] STALE: no portfolio snapshot in the last 2h\n"
    )
    healthy, summary = _summary(tmp_path, monkeypatch)
    assert "portfolio:" in summary
    assert not healthy
