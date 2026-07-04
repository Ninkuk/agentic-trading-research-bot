import urllib.error

import pytest

from pipeline.gate import llm

BODY = {"model": "claude-sonnet-5-20260203",
        "content": [{"type": "text", "text": '{"action":"approve",'
                     '"size_mult":0.8,"confidence":0.7,"rationale":"ok"}'}]}


def test_complete_posts_grammar_and_returns_body():
    calls = {}

    def fake_post(url, payload, headers):
        calls["url"], calls["payload"], calls["headers"] = url, payload, headers
        return BODY

    body = llm.complete("SYS", "USER", model="claude-sonnet-5",
                        api_key="KEY", post=fake_post)
    assert body is BODY
    assert calls["url"].endswith("/v1/messages")
    assert calls["payload"]["temperature"] == 0
    assert calls["payload"]["system"] == "SYS"
    assert calls["payload"]["messages"] == [{"role": "user", "content": "USER"}]
    assert calls["headers"]["x-api-key"] == "KEY"
    assert calls["headers"]["anthropic-version"] == "2023-06-01"
    assert llm.response_text(body).startswith('{"action"')
    assert llm.response_model(body) == "claude-sonnet-5-20260203"


def test_complete_retries_429_then_succeeds():
    attempts = []

    def flaky_post(url, payload, headers):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(url, 429, "rate", {}, None)
        return BODY

    slept = []
    body = llm.complete("s", "u", model="m", api_key="k", post=flaky_post,
                        sleep=slept.append)
    assert body is BODY and len(attempts) == 3 and len(slept) == 2


def test_complete_gives_up_after_bounded_attempts():
    def always_500(url, payload, headers):
        raise urllib.error.HTTPError(url, 500, "boom", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        llm.complete("s", "u", model="m", api_key="k", post=always_500,
                     sleep=lambda _t: None)


def test_complete_non_retryable_raises_immediately():
    attempts = []

    def forbidden(url, payload, headers):
        attempts.append(1)
        raise urllib.error.HTTPError(url, 403, "no", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        llm.complete("s", "u", model="m", api_key="k", post=forbidden,
                     sleep=lambda _t: None)
    assert len(attempts) == 1


def test_parse_agent_valid_and_truncation():
    out = llm.parse_agent('{"action":"veto","size_mult":0.0,'
                          '"confidence":0.9,"rationale":"' + "x" * 600 + '"}')
    assert out["action"] == "veto"
    assert len(out["rationale"]) == 500


def test_parse_agent_out_of_range_size_mult_is_ACCEPTED():
    # spec pin: clamping (with clamp_fired) handles it, not the parser
    out = llm.parse_agent('{"action":"approve","size_mult":1.7,'
                          '"confidence":0.8,"rationale":"r"}')
    assert out["size_mult"] == 1.7


@pytest.mark.parametrize("bad", [
    "prose, not json",
    '{"action":"maybe","size_mult":0.5,"confidence":0.5,"rationale":"r"}',
    '{"action":"approve","size_mult":0.5,"confidence":1.5,"rationale":"r"}',
    '{"action":"approve","size_mult":0.5,"confidence":0.5,"rationale":"r","x":1}',
    '{"action":"approve","size_mult":0.5,"rationale":"r"}',
    '[]',
    '{"action":"approve","size_mult":"big","confidence":0.5,"rationale":"r"}',
])
def test_parse_agent_malformed(bad):
    with pytest.raises(llm.MalformedResponse):
        llm.parse_agent(bad)
