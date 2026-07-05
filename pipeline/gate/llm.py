"""The one place the pipeline talks to an LLM. Two backends behind the same
injected `complete=` seam: `complete` (raw Messages API, needs a key) and
`complete_cli` (headless `claude -p`, subscription auth — the default under
the strictly-no-ANTHROPIC_API_KEY policy). Both sit behind injectable seams
(`post=` / `run_proc=`, no network or subprocess in tests); bounded retries
reuse http_client.retry_delay. Secret hygiene: never log the URL, body
(contains the masked prompt), headers (contain the key) or subprocess
stderr — exception type names only, and that responsibility lives in
run.py's catch."""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from pipeline.gate import catalog
from sources.common.http_client import retry_delay

API_URL = "https://api.anthropic.com/v1/messages"
_RETRY_STATUS = {429, 500, 502, 503, 529}


class MalformedResponse(ValueError):
    """The agent's reply violated the fixed output grammar."""


def _post(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={**headers, "content-type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def complete(system: str, user: str, *, model: str, api_key: str,
             post=None, sleep=time.sleep) -> dict:
    """One Messages call. Returns the parsed response body. Retries transient
    transport failures (429/5xx/URLError) LLM_ATTEMPTS times with
    Retry-After-aware backoff; other HTTP errors raise immediately."""
    post = post or _post
    payload = {"model": model, "max_tokens": catalog.MAX_TOKENS,
               "temperature": 0, "system": system,
               "messages": [{"role": "user", "content": user}]}
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    for attempt in range(1, catalog.LLM_ATTEMPTS + 1):
        try:
            return post(API_URL, payload, headers)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_STATUS or attempt == catalog.LLM_ATTEMPTS:
                raise
            sleep(retry_delay(e, attempt, 1.0))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == catalog.LLM_ATTEMPTS:
                raise
            sleep(retry_delay(e, attempt, 1.0))


class CLIError(RuntimeError):
    """The claude CLI backend failed after LLM_ATTEMPTS tries. Carries only
    a short cause tag (exit code / exception type name) — never stderr."""


def complete_cli(system: str, user: str, *, model: str, api_key=None,
                 run_proc=subprocess.run, sleep=time.sleep) -> dict:
    """One headless `claude -p` completion (subscription auth — the
    no-API-key policy path). Returns a Messages-shaped body so
    response_text / response_model / parse_agent and every downstream
    guardrail stay backend-agnostic. `api_key` is accepted and ignored
    (seam compatibility with `complete`).

    The user prompt travels via stdin, never argv (`ps` hygiene); the child
    env never carries ANTHROPIC_API_KEY, so auth is structurally
    subscription-only. The served model is pinned from the envelope's
    modelUsage (falling back to the requested name), keeping the Stage 4
    reproducibility contract. Retries LLM_ATTEMPTS times on timeout,
    non-zero exit, an unparseable envelope, or is_error; then raises
    CLIError. No temperature control exists on this path — rationales may
    vary run-to-run; bounds are unaffected (resolve.py clamps regardless,
    and replay re-derives from the STORED proposal)."""
    argv = [catalog.CLI_BIN, "-p", "--output-format", "json",
            "--model", model, "--system-prompt", system]
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    last = "unknown"
    for attempt in range(1, catalog.LLM_ATTEMPTS + 1):
        proc = None
        try:
            proc = run_proc(argv, input=user, capture_output=True, text=True,
                            timeout=catalog.CLI_TIMEOUT_S, env=env)
        except (subprocess.TimeoutExpired, OSError) as e:
            last = type(e).__name__
        if proc is not None and proc.returncode == 0:
            try:
                envelope = json.loads(proc.stdout)
            except ValueError as e:
                envelope, last = None, type(e).__name__
            if envelope is not None and not envelope.get("is_error"):
                served = next(iter(envelope.get("modelUsage") or {}), model)
                return {"content": [{"type": "text",
                                     "text": envelope.get("result", "")}],
                        "model": served}
            if envelope is not None:
                last = "is_error"
        elif proc is not None:
            last = f"exit {proc.returncode}"
        if attempt < catalog.LLM_ATTEMPTS:
            sleep(retry_delay(None, attempt, 1.0))
    raise CLIError(last)


def response_text(body: dict) -> str:
    """Extract the agent's reply text. A well-formed HTTP 200 can still carry
    an unexpected shape (empty content list, non-text block) — treat that as
    a malformed reply rather than letting KeyError/IndexError/TypeError
    escape and halt the run."""
    try:
        return body["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise MalformedResponse(str(e)) from None


def response_model(body: dict):
    """The reproducibility pin: what actually served the decision (request
    ids are aliases whose server-side resolution can change)."""
    return body.get("model")


_KEYS = {"action", "size_mult", "confidence", "rationale"}


def parse_agent(text: str) -> dict:
    """Strict grammar validation. Extra/missing keys, non-dict, bad action,
    bad numbers, out-of-[0,1] confidence -> MalformedResponse. Out-of-range
    size_mult is ACCEPTED (the code clamp + clamp_fired handles it — spec
    section 5 governs). Overlong rationale is truncated."""
    try:
        obj = json.loads(text)
    except ValueError as e:
        raise MalformedResponse(str(e)) from None
    if not isinstance(obj, dict) or set(obj) != _KEYS:
        raise MalformedResponse("wrong keys")
    if obj["action"] not in ("approve", "veto"):
        raise MalformedResponse("bad action")
    try:
        size_mult = float(obj["size_mult"])
        confidence = float(obj["confidence"])
    except (TypeError, ValueError):
        raise MalformedResponse("non-numeric") from None
    if isinstance(obj["size_mult"], bool) or isinstance(obj["confidence"], bool):
        raise MalformedResponse("boolean where number expected")
    if not 0.0 <= confidence <= 1.0:
        raise MalformedResponse("confidence out of range")
    if not isinstance(obj["rationale"], str):
        raise MalformedResponse("rationale not a string")
    return {"action": obj["action"], "size_mult": size_mult,
            "confidence": confidence,
            "rationale": obj["rationale"][:catalog.RATIONALE_MAX]}
