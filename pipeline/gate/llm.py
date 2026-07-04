"""The one place the pipeline talks to an LLM. stdlib urllib behind an
injected `post` seam (no network in tests); bounded retries reusing
http_client.retry_delay. Secret hygiene: never log the URL, body (contains
the masked prompt) or headers (contain the key) — exception type names only,
and that responsibility lives in run.py's catch."""
import json
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


def response_text(body: dict) -> str:
    return body["content"][0]["text"]


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
