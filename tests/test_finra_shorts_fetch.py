# tests/test_finra_shorts_fetch.py
import urllib.error

import pytest

from finra_short_volume.fetch import (
    _http_get, day_url, fetch_day, parse_file,
)

SAMPLE = (
    "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n"
    "20240614|AAL|900|100|1500|B,Q,N\n"
    "20240614|ZERO|0|0|0|Q\n"          # total_volume 0 -> ratio None, still kept
    "20240614||50|0|100|Q\n"           # blank symbol -> skipped
    "20240614|SHORT|5|0\n"             # too few fields -> skipped
    "Trailer|record|count|3|x|y\n"     # footer-ish: date 'Trailer' invalid -> skipped
)


def test_parse_file_maps_and_computes_ratio():
    rows = parse_file(SAMPLE)
    assert len(rows) == 2              # AAL + ZERO; blank/short/footer dropped
    assert rows[0] == {
        "symbol": "AAL", "date": "2024-06-14",
        "short_volume": 900, "short_exempt_volume": 100,
        "total_volume": 1500,
        "short_ratio": pytest.approx(900 / 1500),
        "market": "B,Q,N",
    }


def test_parse_file_zero_total_volume_gives_none_ratio():
    zero = [r for r in parse_file(SAMPLE) if r["symbol"] == "ZERO"][0]
    assert zero["total_volume"] == 0
    assert zero["short_ratio"] is None


def test_parse_file_header_row_is_dropped():
    rows = parse_file(
        "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n")
    assert rows == []


def test_day_url():
    assert day_url("2024-06-14") == (
        "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20240614.txt")


def test_fetch_day_parses_returned_text():
    def fake_get(url, opener=None):
        assert url.endswith("CNMSshvol20240614.txt")
        return SAMPLE

    rows = fetch_day("2024-06-14", get=fake_get)
    assert len(rows) == 2


def test_fetch_day_returns_none_on_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    assert fetch_day("2099-01-01", get=fake_get) is None


def test_fetch_day_returns_none_on_403():
    """CDN returns 403 for dates with no file (weekends/holidays); treat as skip."""
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)

    assert fetch_day("2099-01-01", get=fake_get) is None


def test_fetch_day_reraises_non_404_non_403():
    """Non-retryable HTTP errors like 500 must still raise."""
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 500, "err", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_day("2024-06-14", get=fake_get)


def test_http_get_retries_on_429_then_succeeds():
    """429 (throttling) is retryable; earlier 403 was misclassified as retryable."""
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 429, "throttle", {}, None)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0]


def test_http_get_does_not_retry_on_403():
    """403 is non-retryable (CDN signals 'no file for this date'); raise at once."""
    def opener(url):
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)

    with pytest.raises(urllib.error.HTTPError) as excinfo:
        _http_get("http://x", opener=opener)
    assert excinfo.value.code == 403
