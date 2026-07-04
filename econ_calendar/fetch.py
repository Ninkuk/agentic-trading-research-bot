import json

# Reuse the FRED client written once in fred_screener.fetch: same host, same key,
# same bounded backoff (429/5xx), same require_api_key (never echoes the key).
from sources.screeners.fred_screener.fetch import _build_url, _http_get, require_api_key

__all__ = ["require_api_key", "_http_get", "fetch_all_release_dates",
           "fetch_release_dates", "parse_release_dates"]

# The key parameter: default (false) strips future dates, making the endpoint
# backward-looking and useless for a monitor. 'true' surfaces the forward calendar.
_NO_DATA = "true"


def fetch_all_release_dates(api_key, today, get=_http_get) -> list[dict]:
    """Backbone call: all upcoming release dates from today forward."""
    url = _build_url("releases/dates", {
        "include_release_dates_with_no_data": _NO_DATA,
        "sort_order": "asc",
        "order_by": "release_date",
        "realtime_start": today,
    }, api_key)
    return json.loads(get(url)).get("release_dates", [])


def fetch_release_dates(release_id, api_key, today, get=_http_get) -> list[dict]:
    """Per-release variant: one release's upcoming dates from today forward."""
    url = _build_url("release/dates", {
        "release_id": release_id,
        "include_release_dates_with_no_data": _NO_DATA,
        "realtime_start": today,
        "sort_order": "asc",
    }, api_key)
    return json.loads(get(url)).get("release_dates", [])


def parse_release_dates(rows: list[dict], by_id: dict) -> list[dict]:
    """Pure: filter raw FRED release-date rows to catalog ids and map each to an
    events row. event_time comes from the catalog's known-time (FRED gives the
    date only). Status is 'scheduled' for v1 — FRED carries no verified
    provisional flag; firm-up to 'tentative'/'confirmed' is a documented follow-up."""
    out = []
    for raw in rows:
        release = by_id.get(raw.get("release_id"))
        if release is None:
            continue
        out.append({
            "event_type": release.event_type,
            "event_date": raw["date"],
            "event_time": release.release_time,
            "subtype": str(release.release_id),
            "title": raw.get("release_name") or release.label,
            "status": "scheduled",
            "source": "fred",
            "payload": json.dumps({"release_id": release.release_id}),
        })
    return out
