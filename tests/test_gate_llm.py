import json
import os
import subprocess
import urllib.error

import pytest

from pipeline.gate import catalog, llm

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


# --- complete_cli (headless `claude -p` backend; live-verified 2026-07-05:
# envelope is {"type":"result","is_error":false,"result":"...",
# "modelUsage":{"<served-model-id>":{...}}}) ---

def _cli_envelope(result_text, model="claude-sonnet-5-20260203",
                  is_error=False):
    return json.dumps({"type": "result", "subtype": "success",
                       "is_error": is_error, "result": result_text,
                       "modelUsage": {model: {"inputTokens": 1}}})


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_complete_cli_returns_messages_shaped_body():
    def fake_run(argv, **kw):
        return _Proc(stdout=_cli_envelope('{"action":"approve"}'))

    body = llm.complete_cli("SYS", "USER", model="claude-sonnet-5",
                            run_proc=fake_run)
    assert llm.response_text(body) == '{"action":"approve"}'
    assert llm.response_model(body) == "claude-sonnet-5-20260203"


def test_complete_cli_prompt_via_stdin_not_argv():
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"], seen["input"] = argv, kw["input"]
        return _Proc(stdout=_cli_envelope("ok"))

    llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run)
    assert seen["input"] == "USER"
    assert all("USER" not in a for a in seen["argv"])
    assert "--system-prompt" in seen["argv"] and "SYS" in seen["argv"]
    assert seen["argv"][:2] == [catalog.CLI_BIN, "-p"]


def test_complete_cli_strips_api_key_from_child_env(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["env"] = kw["env"]
        return _Proc(stdout=_cli_envelope("ok"))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run)
    assert "ANTHROPIC_API_KEY" not in seen["env"]


def test_complete_cli_ignores_api_key_arg():
    def fake_run(argv, **kw):
        return _Proc(stdout=_cli_envelope("ok"))

    body = llm.complete_cli("SYS", "USER", model="m", api_key="unused",
                            run_proc=fake_run)
    assert llm.response_text(body) == "ok"


def test_complete_cli_retries_nonzero_exit_then_raises():
    attempts = []

    def fake_run(argv, **kw):
        attempts.append(1)
        return _Proc(returncode=1, stderr="boom")

    slept = []
    with pytest.raises(llm.CLIError):
        llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run,
                         sleep=slept.append)
    assert len(attempts) == catalog.LLM_ATTEMPTS
    assert len(slept) == catalog.LLM_ATTEMPTS - 1


def test_complete_cli_retries_timeout_then_succeeds():
    attempts = []

    def fake_run(argv, **kw):
        attempts.append(1)
        if len(attempts) == 1:
            raise subprocess.TimeoutExpired(argv, catalog.CLI_TIMEOUT_S)
        return _Proc(stdout=_cli_envelope("ok"))

    body = llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run,
                            sleep=lambda _t: None)
    assert llm.response_text(body) == "ok" and len(attempts) == 2


def test_complete_cli_bad_envelope_json_is_retryable():
    attempts = []

    def fake_run(argv, **kw):
        attempts.append(1)
        if len(attempts) == 1:
            return _Proc(stdout="not json at all")
        return _Proc(stdout=_cli_envelope("ok"))

    body = llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run,
                            sleep=lambda _t: None)
    assert llm.response_text(body) == "ok" and len(attempts) == 2


def test_complete_cli_is_error_envelope_raises_after_retries():
    def fake_run(argv, **kw):
        return _Proc(stdout=_cli_envelope("nope", is_error=True))

    with pytest.raises(llm.CLIError):
        llm.complete_cli("SYS", "USER", model="m", run_proc=fake_run,
                         sleep=lambda _t: None)


def test_complete_cli_model_falls_back_to_requested():
    def fake_run(argv, **kw):
        return _Proc(stdout=json.dumps(
            {"type": "result", "is_error": False, "result": "ok"}))

    body = llm.complete_cli("SYS", "USER", model="claude-sonnet-5",
                            run_proc=fake_run)
    assert llm.response_model(body) == "claude-sonnet-5"


@pytest.mark.parametrize("bad_body", [
    {"content": []},
    {"content": [{"type": "text"}]},
])
def test_response_text_unexpected_shape_is_malformed(bad_body):
    # A well-formed HTTP 200 can still carry an unexpected shape (empty
    # content list, non-text block) — this must not raise a raw
    # KeyError/IndexError/TypeError that escapes the malformed-response
    # policy in run.py's _get_proposal.
    with pytest.raises(llm.MalformedResponse):
        llm.response_text(bad_body)
