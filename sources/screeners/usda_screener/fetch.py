"""USDA NASS Quick Stats API client. Near-clone of eia_screener.fetch: an API key
in the query string (never logged) + a pure parser. Withheld markers ((D)/(Z)/
(NA)) and blanks map to None."""

import json
import urllib.parse

import sources.common.http_client as http_client
from sources.common.http_client import DEFAULT_UA, RETRY_THROTTLE_5XX

API_URL = "https://quickstats.nass.usda.gov/api/api_GET/"
_UA = DEFAULT_UA
_RETRY_STATUS = RETRY_THROTTLE_5XX
_urlopen = http_client.make_opener(_UA)

__all__ = ["require_api_key", "parse_response", "fetch_target"]


def require_api_key(api_key):
    """Return a non-empty key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError("NASS_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


_http_get = http_client.make_getter(_urlopen, _RETRY_STATUS)


def _num(v):
    """Comma-stripped float; withheld ((D)/(Z)/(NA)) or blank -> None."""
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v or v.startswith("("):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _build_url(query, api_key) -> str:
    pairs = [("key", api_key), ("format", "JSON")] + sorted(query.items())
    return API_URL + "?" + urllib.parse.urlencode(pairs)


def parse_response(payload) -> list:
    """Map NASS data[] to [{period, value, unit}]. period is the year; rows with
    no year are dropped."""
    rows = []
    for d in payload.get("data") or []:
        year = d.get("year")
        if year in (None, ""):
            continue
        rows.append(
            {"period": str(year), "value": _num(d.get("Value")), "unit": d.get("unit_desc")}
        )
    return rows


def fetch_target(query, api_key, get=_http_get) -> list:
    """GET one (commodity, metric) target's rows via its NASS query dict."""
    return parse_response(json.loads(get(_build_url(query, api_key))))
