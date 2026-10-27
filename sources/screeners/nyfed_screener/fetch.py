"""NY Fed Markets API client (key-free JSON) + per-domain pure parsers.
Envelope-agnostic: _first_list pulls the records array whatever the wrapper key."""

import json
import urllib.parse

import sources.common.http_client as http_client
from sources.common.http_client import DEFAULT_UA, RETRY_THROTTLE_5XX
from sources.common.parse import date_prefix, to_float

API_BASE = "https://markets.newyorkfed.org/api"
# The search.json endpoints return an EMPTY list when startDate is absent
# (live-verified), so every fetch sends one; this floor predates all
# published series (rates/repo begin 2000-07, SOMA 2003-07) = full history.
FULL_HISTORY_START = "2000-01-01"
_UA = DEFAULT_UA
_RETRY_STATUS = RETRY_THROTTLE_5XX
_urlopen = http_client.make_opener(_UA)


_http_get = http_client.make_getter(_urlopen, _RETRY_STATUS)


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
    """GET a domain history endpoint; return records. No ``start`` means full
    history — sent explicitly as FULL_HISTORY_START because the search.json
    endpoints treat a missing startDate as an empty window, not "everything"."""
    params = {"startDate": start or FULL_HISTORY_START}
    if end:
        params["endDate"] = end
    payload = json.loads(get(_build_url(endpoint, params)))
    return _first_list(payload) or []


def parse_reference_rates(records) -> list:
    out = []
    for r in records:
        rt = r.get("type") or r.get("rateType")
        d = date_prefix(r.get("effectiveDate"))
        if not rt or not d:
            continue
        out.append(
            {
                "rate_type": rt,
                "effective_date": d,
                "percent_rate": to_float(r.get("percentRate")),
                "volume_bn": to_float(r.get("volumeInBillions")),
                "pct_1": to_float(r.get("percentPercentile1")),
                "pct_25": to_float(r.get("percentPercentile25")),
                "pct_75": to_float(r.get("percentPercentile75")),
                "pct_99": to_float(r.get("percentPercentile99")),
            }
        )
    return out


# The single /rp/results/search.json feed carries both legs, tagged operationType.
_OP_TYPE_LIVE = {"repo": "Repo", "reverse_repo": "Reverse Repo"}
# SOMA summary is wide: these columns are per-security par-value totals.
_SOMA_SECURITIES = (
    "mbs",
    "cmbs",
    "tips",
    "frn",
    "tipsInflationCompensation",
    "notesbonds",
    "bills",
    "agencies",
    "total",
)


def _op_rate(details):
    """Operation-level rate from the details[] legs: the dominant (largest
    accepted) leg's award rate, falling back to its offering rate. Repo ops with
    nothing accepted fall back to the first leg's offering rate."""
    if not isinstance(details, list) or not details:
        return None
    best = max(details, key=lambda d: to_float(d.get("amtAccepted")) or 0.0)
    return to_float(best.get("percentAwardRate")) or to_float(best.get("percentOfferingRate"))


def parse_repo_ops(records, operation_type) -> list:
    """Keep only the requested leg (operationType) from the combined results feed
    and map it to a fact row. total_submitted/total_accepted are top-level; the
    rate is nested under details[] (absent at the record top level)."""
    want = _OP_TYPE_LIVE.get(operation_type, operation_type)
    out = []
    for r in records:
        if (r.get("operationType") or "") != want:
            continue
        oid = r.get("operationId")
        d = date_prefix(r.get("operationDate"))
        if not oid or not d:
            continue
        out.append(
            {
                "operation_id": str(oid),
                "operation_date": d,
                "operation_type": operation_type,
                "total_submitted": to_float(r.get("totalAmtSubmitted")),
                "total_accepted": to_float(r.get("totalAmtAccepted")),
                "award_rate": _op_rate(r.get("details")),
            }
        )
    return out


def parse_soma_holdings(records) -> list:
    """Melt the wide SOMA summary (security types as columns) into one row per
    (as_of_date, security_type). Blank cells are skipped; 0.00 is kept (a real
    zero holding). The 'total' column is retained as its own row."""
    out = []
    for r in records:
        d = date_prefix(r.get("asOfDate"))
        if not d:
            continue
        for sec in _SOMA_SECURITIES:
            val = to_float(r.get(sec))
            if val is None:  # blank cell -> not stored
                continue
            out.append({"as_of_date": d, "security_type": sec, "par_value": val})
    return out


def parse_primary_dealer(records) -> list:
    """Phase-2, tolerant: one row per (asOfDate, series key). 🟡 confirm shape."""
    out = []
    for r in records:
        d = date_prefix(r.get("asOfDate"))
        key = r.get("keyId") or r.get("seriesBreakId") or r.get("series")
        if not d or not key:
            continue
        out.append({"as_of_date": d, "series_key": str(key), "value": to_float(r.get("value"))})
    return out
