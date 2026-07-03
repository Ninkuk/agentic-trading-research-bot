import json
import time
import urllib.parse

import http_client

API_BASE = "https://api.stlouisfed.org/fred"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # FRED throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)


def require_api_key(api_key):
    """Return a non-empty API key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _build_url(path: str, params: dict, api_key: str) -> str:
    """Assemble a FRED API URL with api_key + file_type=json + caller params."""
    query = {**params, "api_key": api_key, "file_type": "json"}
    return f"{API_BASE}/{path}?{urllib.parse.urlencode(query)}"


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET with bounded backoff, retrying FRED throttling (429) and transient
    5xx/network errors. Other HTTP errors (e.g. 400) raise immediately."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def parse_observations(payload: dict) -> list[dict]:
    """Map a /series/observations payload to [{date, value}], turning FRED's
    '.' missing marker into None and numeric strings into floats."""
    rows = []
    for o in payload.get("observations", []):
        raw = o.get("value")
        value = None if raw in (None, ".") else float(raw)
        rows.append({"date": o["date"], "value": value})
    return rows


def fetch_series(series_id: str, api_key: str, get=_http_get) -> dict:
    """GET /fred/series metadata; return the single seriess[0] dict."""
    url = _build_url("series", {"series_id": series_id}, api_key)
    payload = json.loads(get(url))
    seriess = payload.get("seriess") or []
    if not seriess:
        raise ValueError(f"no series metadata for {series_id}")
    return seriess[0]


def fetch_observations(series_id: str, api_key: str, start=None,
                       get=_http_get) -> list[dict]:
    """GET /fred/series/observations; return parsed [{date, value}] rows."""
    params = {"series_id": series_id}
    if start:
        params["observation_start"] = start
    url = _build_url("series/observations", params, api_key)
    return parse_observations(json.loads(get(url)))
