"""build_health assembles the three health layers into one structured payload
for data.json. Covers: the dashboard job must not read its own log while
building tonight's section, a stale exit code must not re-red days the job
didn't run, and a degenerate log (unreadable, or a directory where a file was
expected) must not blank out other findings.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import health  # noqa: E402

NOW_LOCAL = health.dt.datetime(2026, 7, 22, 21, 13, 0)
NOW_UTC = health.dt.datetime(2026, 7, 23, 4, 13, 0, tzinfo=health.dt.UTC)


def _log(path, lines):
    path.write_text("\n".join(lines) + "\n" if lines else "")


def _build(tmp_path, monkeypatch, codes=None, running=None):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    monkeypatch.setattr(health, "job_exit_codes", lambda: codes or {})
    monkeypatch.setattr(health, "running_jobs", lambda: running or set())
    return health.build_health(logs, data, NOW_LOCAL, NOW_UTC)


def test_all_quiet_is_healthy(tmp_path, monkeypatch):
    result = _build(tmp_path, monkeypatch, codes={"fred": 0, "composite": None})
    assert result["healthy"] is True
    assert result["jobs_loaded"] == 2
    assert result["problems"] == []


def test_nonzero_exit_with_recent_log_is_reported(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(hours=1)
    _log(logs / "edgar.log", [f"[{ts:%Y-%m-%d %H:%M:%S}] start: edgar"])
    result = _build(tmp_path, monkeypatch, codes={"edgar": 1})
    assert len(result["problems"]) == 1
    assert result["problems"][0]["kind"] == "exit"
    assert result["problems"][0]["detail"] == "last exit 1"


def test_weekend_echo_is_suppressed(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(days=3)
    _log(logs / "preopen.log", [f"[{ts:%Y-%m-%d %H:%M:%S}] start: preopen"])
    result = _build(tmp_path, monkeypatch, codes={"preopen": 1})
    assert result["problems"] == []


def test_nonzero_exit_with_no_log_stays_loud(tmp_path, monkeypatch):
    result = _build(tmp_path, monkeypatch, codes={"ghost": 2})
    assert len(result["problems"]) == 1
    assert result["problems"][0]["kind"] == "exit"
    assert result["problems"][0]["target"] == "ghost"


def test_own_log_is_excluded(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(minutes=5)
    _log(
        logs / health.SELF_LOG,
        [f"[{ts:%Y-%m-%d %H:%M:%S}] start: dashboard", f"[{ts:%Y-%m-%d %H:%M:%S}] FAILED: boom"],
    )
    result = _build(tmp_path, monkeypatch)
    assert result["runs_24h"] == 0
    assert result["problems"] == []


def test_marker_findings_are_counts(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(minutes=5)
    _log(
        logs / "cboe_stats.log",
        [
            f"[{ts:%Y-%m-%d %H:%M:%S}] start: cboe stats",
            f"[{ts:%Y-%m-%d %H:%M:%S}] FAILED: step one",
            f"[{ts:%Y-%m-%d %H:%M:%S}] FAILED: step two",
        ],
    )
    result = _build(tmp_path, monkeypatch)
    assert result["problems"] == [
        {"kind": "log", "target": "cboe_stats", "detail": "2 FAILED lines in 24h"}
    ]


def test_one_degenerate_log_cannot_blank_the_rest(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (logs / "weird.log").mkdir()  # degenerate: a directory shaped like a log
    old = (NOW_UTC - health.dt.timedelta(days=30)).isoformat()
    with health.sqlite3.connect(data / "stale.db") as conn:
        conn.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT)")
        conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (old,))
        conn.commit()
    monkeypatch.setattr(health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(health, "running_jobs", lambda: {"weird"})
    result = health.build_health(logs, data, NOW_LOCAL, NOW_UTC)
    kinds = [p["kind"] for p in result["problems"]]
    assert "hung" in kinds
    assert "stale" in kinds


def test_unreadable_log_cannot_blank_the_rest(tmp_path, monkeypatch):
    """The directory case above is one failure mode of a broader class: any
    OSError raised while scanning a log (permission removed by a botched
    chmod, a different-UID wrapper run, log rotation mid-write) must not
    take down the whole report. Pin it with a real unreadable file, not just
    a directory, so an is_file()-only guard (which passes an unreadable file
    through) cannot silently satisfy this test for the wrong reason."""
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    locked = logs / "locked.log"
    locked.write_text("[2026-07-22 12:00:00] start: locked\n")
    locked.chmod(0o000)
    if os.access(locked, os.R_OK):
        pytest.skip("running with privileges that bypass file permissions (e.g. root)")
    old = (NOW_UTC - health.dt.timedelta(days=30)).isoformat()
    with health.sqlite3.connect(data / "stale.db") as conn:
        conn.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT)")
        conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (old,))
        conn.commit()
    monkeypatch.setattr(health, "job_exit_codes", lambda: {})
    monkeypatch.setattr(health, "running_jobs", lambda: set())
    try:
        result = health.build_health(logs, data, NOW_LOCAL, NOW_UTC)
    finally:
        locked.chmod(0o644)  # tmp_path cleanup must not fail on a locked file
    kinds = [p["kind"] for p in result["problems"]]
    assert "log" in kinds
    assert "stale" in kinds


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

    monkeypatch.setattr(health.subprocess, "run", fake_run)
    assert health.running_jobs() == {"reddit-intraday"}


def test_hung_job_reaches_the_digest_and_marks_it_unhealthy(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(minutes=45)
    _log(logs / "fred.log", [f"[{ts:%Y-%m-%d %H:%M:%S}] start: fred"])
    result = _build(tmp_path, monkeypatch, running={"fred"})
    assert result["healthy"] is False
    assert any(
        p["kind"] == "hung" and p["target"] == "fred" and "possible hang" in p["detail"]
        for p in result["problems"]
    )


def test_healthy_running_job_leaves_the_digest_green(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    ts = NOW_LOCAL - health.dt.timedelta(minutes=2)
    _log(logs / "fred.log", [f"[{ts:%Y-%m-%d %H:%M:%S}] start: fred"])
    result = _build(tmp_path, monkeypatch, running={"fred"})
    assert result["healthy"] is True
    assert not any("possible hang" in p["detail"] for p in result["problems"])


def test_jobs_running_normally_at_digest_time_are_not_flagged(tmp_path, monkeypatch):
    """composite (21:05), scorer (21:10), advisor (21:12) and dashboard (21:13)
    can still be running when the digest fires at 21:13. All are far under the
    15min default tier, so none may be reported."""
    logs = tmp_path / "logs"
    logs.mkdir(exist_ok=True)
    for job, minutes_ago in (("composite", 8), ("scorer", 3), ("advisor", 1)):
        ts = NOW_LOCAL - health.dt.timedelta(minutes=minutes_ago)
        _log(logs / f"{job}.log", [f"[{ts:%Y-%m-%d %H:%M:%S}] start: {job}"])
    running = {"composite", "scorer", "advisor", "dashboard"}
    result = _build(tmp_path, monkeypatch, running=running)
    assert result["healthy"] is True
    assert not any("possible hang" in p["detail"] for p in result["problems"])
