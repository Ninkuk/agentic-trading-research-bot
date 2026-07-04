import json
import urllib.error

import pytest

from eia_screener import fetch


def test_require_api_key_raises_without_echoing():
    with pytest.raises(RuntimeError) as exc:
        fetch.require_api_key("")
    assert "EIA_API_KEY" in str(exc.value)
    assert fetch.require_api_key("KEY") == "KEY"


def test_build_url_encodes_bracket_arrays_and_key():
    url = fetch._build_url("petroleum/stoc/wstk", "WCESTUS1", "SECRET",
                           start="2026-01-01")
    assert "api_key=SECRET" in url
    assert "data%5B0%5D=value" in url                       # data[0]=value
    assert "facets%5Bseries%5D%5B%5D=WCESTUS1" in url        # facets[series][]
    assert "sort%5B0%5D%5Bcolumn%5D=period" in url
    assert "start=2026-01-01" in url
    assert url.startswith("https://api.eia.gov/v2/petroleum/stoc/wstk/data/?")


def test_parse_response_extracts_rows_and_unit():
    payload = {"response": {"data": [
        {"period": "2026-06-26", "value": "420500", "units": "MBBL"},
        {"period": "2026-06-19", "value": None, "units": "MBBL"},   # withheld
    ]}}
    rows, unit = fetch.parse_response(payload)
    assert unit == "MBBL"
    assert rows[0] == {"period": "2026-06-26", "value": 420500.0}
    assert rows[1]["value"] is None


def test_fetch_series_obs_calls_get_and_parses():
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"response": {"data": [
            {"period": "2026-06-26", "value": "1.0", "units": "BCF"}]}})

    rows, unit = fetch.fetch_series_obs("natural-gas/stor/wkly", "F", "K", get=get)
    assert unit == "BCF" and rows[0]["value"] == 1.0
    assert "facets%5Bseries%5D%5B%5D=F" in seen["url"]


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
