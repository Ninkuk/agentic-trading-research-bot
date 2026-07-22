"""FINRA OTC/ATS (dark-pool) transparency via the anonymous api.finra.org query
API. POSTs a compareFilters body but reuses http_client's backoff unchanged: the
loop only calls opener(url), so a body-capturing POST closure drops straight in."""

import csv
import io
import json
import time
import urllib.error
import urllib.request

import sources.common.http_client as http_client

_DATASET = "weeklySummary"  # confirmed live (otcMarket/weeklySummary, anon POST)
API_URL = f"https://api.finra.org/data/group/otcMarket/name/{_DATASET}"
_UA = {"User-Agent": "agentic-trading-research-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_DEMINIMIS = "NON_ATS_DEMINIMIS"
# The weeklySummary feed carries several summaryTypeCodes: granular per-(symbol,
# venue) rows plus symbol-only / firm-only aggregate roll-ups, for both ATS and
# non-ATS OTC. We ingest only the granular ATS venue rows — the dark-pool signal
# this screener's ats_volume/dark_pools schema is built for. The other types are
# either non-ATS (OTC_*), or aggregates that would double-count and carry no MPID.
_ATS_GRANULAR = "ATS_W_SMBL_FIRM"

__all__ = ["week_body", "parse_rows", "fetch_week"]


def week_body(week_start: str, limit: int = 10000) -> dict:
    """compareFilters JSON body selecting one week (weekStartDate EQUAL date)."""
    return {
        "compareFilters": [
            {"compareType": "EQUAL", "fieldName": "weekStartDate", "fieldValue": week_start}
        ],
        "limit": limit,
    }


def _to_int(raw):
    raw = ("" if raw is None else str(raw)).strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _records(text, fmt):
    if fmt == "csv":
        return list(csv.DictReader(io.StringIO(text)))
    data = json.loads(text)
    if isinstance(data, list):
        return data
    return data.get("data") or data.get("results") or []


def parse_rows(text: str, fmt: str) -> list:
    """Map API records to the curated fact-row shape. Rows missing symbol or week
    are skipped; blank MPID -> the de-minimis sentinel so the PK holds."""
    out = []
    for r in _records(text, fmt):
        if (r.get("summaryTypeCode") or "").strip() != _ATS_GRANULAR:
            continue  # skip OTC + aggregate roll-ups
        symbol = (r.get("issueSymbolIdentifier") or r.get("symbol") or "").strip()
        week = (r.get("weekStartDate") or "").strip()
        if not symbol or not week:
            continue
        mpid = (r.get("MPID") or "").strip() or _DEMINIMIS
        # Live otcMarket records carry the venue name in `marketParticipantName`;
        # `ATSName` (assumed pre-verification) does not exist in the live schema
        # and left ats_name always None. Keep ATSName as a CSV-export fallback.
        ats_name = (r.get("marketParticipantName") or r.get("ATSName") or "").strip() or None
        out.append(
            {
                "week_start": week,
                "symbol": symbol,
                "mpid": mpid,
                "ats_name": ats_name,
                "trade_count": _to_int(r.get("totalWeeklyTradeCount")),
                "share_quantity": _to_int(r.get("totalWeeklyShareQuantity")),
                "tier": (r.get("tierIdentifier") or "").strip() or None,
            }
        )
    return out


def _post_opener(body: dict):
    """opener(url)->text that POSTs the JSON body. Captures the body so
    http_client.http_get's opener(url) call issues the POST unchanged."""
    data = json.dumps(body).encode("utf-8")
    headers = {**_UA, "Content-Type": "application/json", "Accept": "application/json"}

    def opener(url):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", "replace")

    return opener


def _http_get(url, opener, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY, sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


def fetch_week(week_start, get=_http_get, opener=None):
    """POST + parse one week. Returns rows, or None on HTTP 403/404 (not yet
    published / absent). 429/503 + transient errors retried by the backoff."""
    op = opener if opener is not None else _post_opener(week_body(week_start))
    try:
        text = get(API_URL, opener=op)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise
    return parse_rows(text, "json")
