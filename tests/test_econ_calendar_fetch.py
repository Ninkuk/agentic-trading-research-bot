import json
import urllib.error

import pytest

from sources.monitors.econ_calendar import fetch
from sources.monitors.econ_calendar.catalog import Release

REL = {10: Release(10, "cpi_release", "Consumer Price Index",
                   "high", "inflation", "08:30")}
PAYLOAD = {"release_dates": [
    {"release_id": 10, "release_name": "Consumer Price Index", "date": "2026-08-12"},
    {"release_id": 999, "release_name": "Not In Catalog", "date": "2026-08-13"},
]}


def test_parse_filters_to_catalog_and_maps_fields():
    rows = fetch.parse_release_dates(PAYLOAD["release_dates"], REL)
    assert len(rows) == 1                       # 999 dropped
    r = rows[0]
    assert r["event_type"] == "cpi_release"
    assert r["event_date"] == "2026-08-12"
    assert r["event_time"] == "08:30"           # from the catalog known-time
    assert r["subtype"] == "10"                 # str(release_id)
    assert r["status"] == "scheduled"
    assert r["source"] == "fred"


def test_fetch_all_url_has_no_data_flag_and_realtime_start():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps(PAYLOAD)

    out = fetch.fetch_all_release_dates("SECRET", "2026-07-03", get=get)
    assert out == PAYLOAD["release_dates"]
    assert "include_release_dates_with_no_data=true" in seen["url"]
    assert "realtime_start=2026-07-03" in seen["url"]


def test_fetch_release_dates_url_includes_release_id_and_flag():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps(PAYLOAD)

    fetch.fetch_release_dates(10, "SECRET", "2026-07-03", get=get)
    assert "release_id=10" in seen["url"]
    assert "include_release_dates_with_no_data=true" in seen["url"]
    assert "realtime_start=2026-07-03" in seen["url"]


def test_require_api_key_raises_without_echoing_key():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "FRED_API_KEY" in str(exc.value)


def _http_error(code):
    return urllib.error.HTTPError("http://x?api_key=SECRET", code, "e", {}, None)


def test_http_get_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps(PAYLOAD)

    out = fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert json.loads(out) == PAYLOAD
    assert slept == [1.0]
