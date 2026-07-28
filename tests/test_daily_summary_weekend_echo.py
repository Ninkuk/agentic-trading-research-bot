"""launchctl's last-exit code must not re-red the summary on days the job
doesn't run.

launchctl holds a job's exit status until its NEXT run. For a weekday-only
job that fails on Friday (2026-07-24: portfolio + journal blocked on a
permission prompt), Saturday's and Sunday's summaries re-reported `last exit
1` with no new information -- two of the six straight red nights of
2026-07-22..27 were pure weekend echo. The failure is alerted the night it
happens (this layer plus scan_log's in-window lines); repeating it while the
job hasn't run again adds nothing, and a job that stops running entirely is
stale_dbs' catch, not this layer's.
"""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


def _summary(tmp_path, monkeypatch, codes, now=None):
    monkeypatch.setattr(daily_summary, "LOGS", tmp_path)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "job_exit_codes", lambda: codes)
    monkeypatch.setattr(daily_summary, "running_jobs", lambda: set())
    monkeypatch.setattr(daily_summary, "signals_digest", lambda: [])
    monkeypatch.setattr(daily_summary, "advisor_digest", lambda: [])
    now = now or daily_summary.dt.datetime(2026, 7, 26, 21, 15, 0)  # Sunday
    return daily_summary.build_summary(now, daily_summary.dt.datetime.now(daily_summary.dt.UTC))


def test_stale_exit_code_from_a_job_that_did_not_run_today_is_suppressed(tmp_path, monkeypatch):
    # Friday's failed run is the log's newest start; Sunday's summary must not
    # repeat the corpse.
    (tmp_path / "portfolio.log").write_text(
        "[2026-07-24 14:30:05] start: portfolio snapshot\n"
        "[2026-07-24 14:30:25] end: portfolio snapshot (20s, exit 1)\n"
    )
    healthy, summary = _summary(tmp_path, monkeypatch, {"portfolio": 1})
    assert "last exit" not in summary
    assert healthy


def test_exit_code_with_an_in_window_run_still_reports(tmp_path, monkeypatch):
    # The night the failure happens, the run IS in-window: keep the line.
    (tmp_path / "portfolio.log").write_text(
        "[2026-07-26 14:30:05] start: portfolio snapshot\n"
        "[2026-07-26 14:30:25] end: portfolio snapshot (20s, exit 1)\n"
    )
    healthy, summary = _summary(tmp_path, monkeypatch, {"portfolio": 1})
    assert "portfolio: last exit 1" in summary
    assert not healthy


def test_exit_code_with_no_log_at_all_still_reports(tmp_path, monkeypatch):
    # No log to date the failure by -> stay conservative and report it.
    healthy, summary = _summary(tmp_path, monkeypatch, {"portfolio": 1})
    assert "portfolio: last exit 1" in summary
    assert not healthy
