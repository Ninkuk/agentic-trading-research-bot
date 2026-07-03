import json
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.stlouisfed.org/fred"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # FRED throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0


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


def _urlopen(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def _retry_delay(err, attempt: int, base_delay: float) -> float:
    """Honor a numeric Retry-After header if present, else exponential backoff."""
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET a URL as text with bounded exponential backoff. Retryable: FRED
    throttling (429), transient 5xx, and transient network errors. Other HTTP
    errors (e.g. 400 bad request) raise immediately."""
    for attempt in range(1, attempts + 1):
        try:
            return opener(url)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_STATUS or attempt == attempts:
                raise
            sleep(_retry_delay(e, attempt, base_delay))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == attempts:
                raise
            sleep(_retry_delay(e, attempt, base_delay))
    raise AssertionError("unreachable")  # pragma: no cover


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
