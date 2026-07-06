"""EIA Open Data API v2 client. Near-clone of fred_screener.fetch: an API key in
the query string (never logged), plus EIA's bracket-array params built via an
ordered (key, value) tuple list + urlencode(doseq=True) so repeated
facets[series][] survive."""

import json
import time
import urllib.parse

import sources.common.http_client as http_client

API_BASE = "https://api.eia.gov/v2"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

__all__ = ["require_api_key", "parse_response", "fetch_series_obs"]


def require_api_key(api_key):
    """Return a non-empty key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError("EIA_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _http_get(
    url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY, sleep=time.sleep
):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_url(route, facet, api_key, start=None) -> str:
    """Assemble a v2 data URL. Ordered tuples + doseq so bracket-array keys
    (data[0], facets[series][], sort[0][...]) encode correctly."""
    pairs = [
        ("api_key", api_key),
        ("frequency", "weekly"),
        ("data[0]", "value"),
        ("facets[series][]", facet),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
    ]
    if start:
        pairs.append(("start", start))
    return f"{API_BASE}/{route}/data/?" + urllib.parse.urlencode(pairs, doseq=True)


def parse_response(payload) -> tuple:
    """Map response.data[] to ([{period, value}], unit). Withheld value -> None."""
    data = (payload.get("response") or {}).get("data") or []
    rows, unit = [], None
    for d in data:
        period = d.get("period")
        if not period:
            continue
        rows.append({"period": str(period)[:10], "value": _num(d.get("value"))})
        unit = unit or d.get("units") or d.get("unit")
    return rows, unit


def fetch_series_obs(route, facet, api_key, start=None, get=_http_get) -> tuple:
    """GET one series' weekly observations. Returns (rows, unit)."""
    payload = json.loads(get(_build_url(route, facet, api_key, start)))
    return parse_response(payload)
