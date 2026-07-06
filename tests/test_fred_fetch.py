import urllib.error

import pytest

from sources.screeners.fred_screener.fetch import (
    _build_url,
    _http_get,
    fetch_observations,
    fetch_series,
    parse_observations,
    require_api_key,
)

OBS_PAYLOAD = {
    "observations": [
        {"date": "2026-04-01", "value": "4.3"},
        {"date": "2026-05-01", "value": "."},  # missing marker
        {"date": "2026-06-01", "value": "4.2"},
    ]
}
SERIES_PAYLOAD = {
    "seriess": [
        {"id": "UNRATE", "title": "Unemployment Rate", "frequency": "Monthly", "units": "Percent"}
    ]
}


def test_parse_observations_maps_values_and_missing():
    rows = parse_observations(OBS_PAYLOAD)
    assert rows == [
        {"date": "2026-04-01", "value": 4.3},
        {"date": "2026-05-01", "value": None},
        {"date": "2026-06-01", "value": 4.2},
    ]


def test_build_url_includes_key_and_json_type():
    url = _build_url("series", {"series_id": "UNRATE"}, api_key="SECRET")
    assert url.startswith("https://api.stlouisfed.org/fred/series?")
    assert "series_id=UNRATE" in url
    assert "api_key=SECRET" in url
    assert "file_type=json" in url


def test_require_api_key_raises_without_echoing_key():
    with pytest.raises(RuntimeError) as exc:
        require_api_key("")
    assert "FRED_API_KEY" in str(exc.value)


def test_require_api_key_returns_present_key():
    assert require_api_key("abc123") == "abc123"


def test_fetch_series_returns_first_seriess_entry():
    got = fetch_series(
        "UNRATE", api_key="K", get=lambda url: __import__("json").dumps(SERIES_PAYLOAD)
    )
    assert got["id"] == "UNRATE"
    assert got["title"] == "Unemployment Rate"


def test_fetch_observations_parses_and_passes_start():
    seen = {}

    def fake_get(url):
        seen["url"] = url
        return __import__("json").dumps(OBS_PAYLOAD)

    rows = fetch_observations("UNRATE", api_key="K", start="2020-01-01", get=fake_get)
    assert rows[0] == {"date": "2026-04-01", "value": 4.3}
    assert "observation_start=2020-01-01" in seen["url"]


def _http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


def test_http_get_retries_on_429_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http_error(429)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0, 2.0]


def test_http_get_does_not_retry_400():
    def opener(url):
        raise _http_error(400)

    with pytest.raises(urllib.error.HTTPError) as exc:
        _http_get("http://x", opener=opener, sleep=lambda s: None)
    assert exc.value.code == 400


def test_http_get_retries_on_urlerror_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.URLError("connection reset")
        return "OK"

    assert _http_get("http://x", opener=opener, sleep=slept.append) == "OK"
    assert slept == [1.0]
