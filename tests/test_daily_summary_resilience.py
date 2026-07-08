"""Characterization tests for daily_summary.py's crash-proofing.

The nightly digest is this system's primary "is anything broken" alert; a
single unguarded exception anywhere in summary assembly must never prevent
`notify.send` from being reached. Each case here asserts a push would still
be produced (build_summary/main complete without raising).
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

# daily_summary.py lives in deploy/launchd and inserts the repo root on
# sys.path itself at import; we only need its own dir on the path to import it.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


def _make_snapshots_db(path, captured_at):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT)")
        conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (captured_at,))
        conn.commit()


def test_stale_dbs_survives_malformed_timestamp(tmp_path, monkeypatch):
    _make_snapshots_db(tmp_path / "broken.db", "not-a-date")
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    result = daily_summary.stale_dbs(daily_summary.dt.datetime.now(daily_summary.dt.UTC))
    assert any("unparseable captured_at" in line for line in result)


def test_stale_dbs_survives_naive_timestamp(tmp_path, monkeypatch):
    _make_snapshots_db(tmp_path / "naive.db", "2026-07-08T21:00:00")
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    # Must not raise (naive datetime subtracted from an aware `now`).
    result = daily_summary.stale_dbs(daily_summary.dt.datetime.now(daily_summary.dt.UTC))
    assert isinstance(result, list)


def test_build_summary_degrades_never_raises(tmp_path, monkeypatch):
    # A malformed captured_at in a real data/ DB (Step 1's per-item guard)
    # surfaces as a "problems" entry rather than raising, and flips healthy
    # to False since build_summary treats any problem line as unhealthy.
    _make_snapshots_db(tmp_path / "broken.db", "not-a-date")
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    healthy, summary = daily_summary.build_summary(
        daily_summary.dt.datetime.now(), daily_summary.dt.datetime.now(daily_summary.dt.UTC)
    )
    assert healthy is False
    assert isinstance(summary, str)
    assert "unparseable captured_at" in summary


def test_main_still_notifies_when_build_fails(monkeypatch):
    def boom(now_local, now_utc):
        raise RuntimeError("build exploded")

    calls = []

    def fake_send(message, **kwargs):
        calls.append(message)

    monkeypatch.setattr(daily_summary, "build_summary", boom)
    monkeypatch.setattr(daily_summary.notify, "send", fake_send)

    result = daily_summary.main()

    assert len(calls) == 1
    assert "summary build failed" in calls[0]
    assert result == 0


def test_job_exit_codes_survives_non_integer_token(monkeypatch):
    # launchctl list columns are: PID, last-exit-status, label.
    fake_stdout = "1234\txyz\tcom.tradingbot.foo\n1234\t0\tcom.tradingbot.bar\n"

    class FakeResult:
        stdout = fake_stdout

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(daily_summary, "subprocess", subprocess)
    codes = daily_summary.job_exit_codes()
    assert "foo" not in codes
    assert codes.get("bar") == 0
