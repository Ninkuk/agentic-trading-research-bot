"""NY Fed Markets API client (key-free JSON) + per-domain pure parsers.
Envelope-agnostic: _first_list pulls the records array whatever the wrapper key."""
import json
import time
import urllib.parse

import http_client

API_BASE = "https://markets.newyorkfed.org/api"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _date(v):
    return (v or "")[:10] or None


def _build_url(endpoint, params=None) -> str:
    url = f"{API_BASE}{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def _first_list(obj):
    """Return the first list found anywhere in the JSON envelope, else []."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            r = _first_list(v)
            if r is not None:
                return r
    return None


def fetch_domain(endpoint, *, start=None, end=None, get=_http_get) -> list:
    """GET a domain history endpoint (windowed when start given); return records."""
    params = {}
    if start:
        params["startDate"] = start
    if end:
        params["endDate"] = end
    payload = json.loads(get(_build_url(endpoint, params or None)))
    return _first_list(payload) or []


def parse_reference_rates(records) -> list:
    out = []
    for r in records:
        rt = r.get("type") or r.get("rateType")
        d = _date(r.get("effectiveDate"))
        if not rt or not d:
            continue
        out.append({"rate_type": rt, "effective_date": d,
                    "percent_rate": _num(r.get("percentRate")),
                    "volume_bn": _num(r.get("volumeInBillions")),
                    "pct_1": _num(r.get("percentPercentile1")),
                    "pct_25": _num(r.get("percentPercentile25")),
                    "pct_75": _num(r.get("percentPercentile75")),
                    "pct_99": _num(r.get("percentPercentile99"))})
    return out


def parse_repo_ops(records, operation_type) -> list:
    out = []
    for r in records:
        oid = r.get("operationId")
        d = _date(r.get("operationDate"))
        if not oid or not d:
            continue
        out.append({"operation_id": str(oid), "operation_date": d,
                    "operation_type": operation_type,
                    "total_submitted": _num(r.get("totalAmtSubmitted")),
                    "total_accepted": _num(r.get("totalAmtAccepted")),
                    "award_rate": _num(r.get("awardRate")
                                       or r.get("percentAwardRate"))})
    return out


def parse_soma_holdings(records) -> list:
    out = []
    for r in records:
        d = _date(r.get("asOfDate"))
        if not d:
            continue
        out.append({"as_of_date": d,
                    "security_type": r.get("securityType") or "total",
                    "par_value": _num(r.get("parValue") or r.get("total"))})
    return out


def parse_primary_dealer(records) -> list:
    """Phase-2, tolerant: one row per (asOfDate, series key). 🟡 confirm shape."""
    out = []
    for r in records:
        d = _date(r.get("asOfDate"))
        key = r.get("keyId") or r.get("seriesBreakId") or r.get("series")
        if not d or not key:
            continue
        out.append({"as_of_date": d, "series_key": str(key),
                    "value": _num(r.get("value"))})
    return out
