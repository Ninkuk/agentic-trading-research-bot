import io
import urllib.error

import pytest

from sources.common import notify


def _capture(calls):
    def post(url, data, headers):
        calls.append((url, data, headers))
    return post


def test_send_posts_message_to_topic_url():
    calls = []
    notify.send("hello", topic="t0pic", post=_capture(calls))
    (url, data, headers), = calls
    assert url == "https://ntfy.sh/t0pic"
    assert data == b"hello"
    assert headers == {}


def test_send_sets_title_priority_tags_and_token_headers():
    calls = []
    notify.send("m", topic="t", title="Daily summary", priority="high",
                tags=["warning", "chart"], token="tok", post=_capture(calls))
    headers = calls[0][2]
    assert headers["Title"] == "Daily summary"
    assert headers["Priority"] == "high"
    assert headers["Tags"] == "warning,chart"
    assert headers["Authorization"] == "Bearer tok"


def test_send_reads_topic_and_server_from_env(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "env-topic")
    monkeypatch.setenv("NTFY_SERVER", "https://ntfy.example.com/")
    calls = []
    notify.send("m", post=_capture(calls))
    assert calls[0][0] == "https://ntfy.example.com/env-topic"


def test_send_without_topic_raises(monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    with pytest.raises(RuntimeError, match="NTFY_TOPIC"):
        notify.send("m", post=_capture([]))


def test_send_scrubs_topic_from_transport_errors():
    def post(url, data, headers):
        raise urllib.error.HTTPError(url, 429, "too many", None, None)
    with pytest.raises(RuntimeError) as exc:
        notify.send("m", topic="secret-topic", post=post)
    assert "secret-topic" not in str(exc.value)
    assert "HTTPError" in str(exc.value)


def test_main_sends_argv_message(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "t")
    calls = []
    monkeypatch.setattr(notify, "_default_post", _capture(calls))
    assert notify.main(["body", "--title", "T", "--tags", "a,b"]) == 0
    url, data, headers = calls[0]
    assert data == b"body"
    assert headers["Tags"] == "a,b"


def test_main_reads_stdin_when_message_omitted(monkeypatch):
    monkeypatch.setenv("NTFY_TOPIC", "t")
    monkeypatch.setattr("sys.stdin", io.StringIO("from stdin"))
    calls = []
    monkeypatch.setattr(notify, "_default_post", _capture(calls))
    assert notify.main([]) == 0
    assert calls[0][1] == b"from stdin"


def test_main_returns_1_and_type_name_only_on_failure(monkeypatch, capsys):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert notify.main(["m"]) == 1
    assert "NTFY_TOPIC" in capsys.readouterr().err
