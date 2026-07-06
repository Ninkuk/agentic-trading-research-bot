import json
import urllib.error

import pytest

from sources.screeners.usda_screener import fetch


def test_require_api_key_raises_without_echoing():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "NASS_API_KEY" in str(exc.value)
    assert fetch.require_api_key("KEY") == "KEY"


def test_build_url_includes_key_format_and_filters():
    url = fetch._build_url({"commodity_desc": "CORN", "statisticcat_desc": "STOCKS"}, "SECRET")
    assert url.startswith("https://quickstats.nass.usda.gov/api/api_GET/?")
    assert "key=SECRET" in url and "format=JSON" in url
    assert "commodity_desc=CORN" in url and "statisticcat_desc=STOCKS" in url


def test_parse_response_coerces_and_withheld_to_none():
    payload = {
        "data": [
            {"year": 2025, "Value": "1,875,000,000", "unit_desc": "BU"},
            {"year": 2024, "Value": "(D)", "unit_desc": "BU"},  # withheld
            {"Value": "5", "unit_desc": "BU"},  # no year -> drop
        ]
    }
    rows = fetch.parse_response(payload)
    assert len(rows) == 2
    assert rows[0] == {"period": "2025", "value": 1875000000.0, "unit": "BU"}
    assert rows[1]["value"] is None


def test_fetch_target_calls_get_and_parses():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"data": [{"year": 2025, "Value": "10", "unit_desc": "BU"}]})

    rows = fetch.fetch_target({"commodity_desc": "WHEAT"}, "K", get=get)
    assert rows[0]["value"] == 10.0 and "commodity_desc=WHEAT" in seen["url"]


def test_http_get_retries_503():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "e", {}, None)
        return "{}"

    fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert calls["n"] == 2 and slept == [1.0]
