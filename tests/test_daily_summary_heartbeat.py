"""Tests for the external dead-man's-switch ping (`heartbeat()`).

Exercises the best-effort ping in isolation (no network): a fake `get` seam
stands in for the real HTTP call, and HEALTHCHECK_URL is monkeypatched via
the environment. Mirrors the resilience style of test_daily_summary_advisor.py
and test_daily_summary_resilience.py — never let a ping failure raise or
affect main()'s exit code, and never let the URL leak to stderr.
"""

import sys
import urllib.error
from pathlib import Path

# daily_summary.py lives in deploy/launchd and inserts the repo root on
# sys.path itself at import; we only need its own dir on the path to import it.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


def test_unset_url_is_noop(monkeypatch):
    monkeypatch.delenv("HEALTHCHECK_URL", raising=False)
    calls = []

    def fake_get(url):
        calls.append(url)

    daily_summary.heartbeat(get=fake_get)

    assert calls == []


def test_set_url_pings_once(monkeypatch):
    dummy_url = "https://hc-ping.com/dummy-uuid"
    monkeypatch.setenv("HEALTHCHECK_URL", dummy_url)
    calls = []

    def fake_get(url):
        calls.append(url)

    daily_summary.heartbeat(get=fake_get)

    assert calls == [dummy_url]


def test_ping_failure_is_swallowed(monkeypatch, capsys):
    dummy_url = "https://hc-ping.com/dummy-uuid"
    monkeypatch.setenv("HEALTHCHECK_URL", dummy_url)

    def fake_get(url):
        raise urllib.error.URLError("x")

    daily_summary.heartbeat(get=fake_get)  # must not raise

    captured = capsys.readouterr()
    assert dummy_url not in captured.err
    assert "URLError" in captured.err


def test_main_returns_0_when_ping_fails(monkeypatch):
    dummy_url = "https://hc-ping.com/dummy-uuid"
    monkeypatch.setenv("HEALTHCHECK_URL", dummy_url)

    monkeypatch.setattr(daily_summary, "build_summary", lambda now_local, now_utc: (True, "ok"))
    monkeypatch.setattr(daily_summary.notify, "send", lambda message, **kwargs: None)

    def fake_default_get(url):
        raise urllib.error.URLError("x")

    # Patch _default_get so main()'s no-arg heartbeat() call exercises the
    # real swallow-path rather than bypassing heartbeat entirely.
    monkeypatch.setattr(daily_summary, "_default_get", fake_default_get)

    result = daily_summary.main()

    assert result == 0
