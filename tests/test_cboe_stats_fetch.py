import urllib.error

from cboe_stats import fetch

_PCR = ("DATE,TOTAL_PCR,EQUITY_PCR,INDEX_PCR,TOTAL_VOLUME\n"
        "2026-06-01,0.95,0.72,1.40,\"45,000,000\"\n"
        ",0.9,0.7,1.2,100\n")                       # blank date dropped
_VIX = ("Preamble line to skip\n"
        "DATE,OPEN,HIGH,LOW,CLOSE\n"
        "06/01/2026,14.1,15.0,13.9,14.6\n")
_VVIX = "DATE,VVIX\n2026-06-01,95.2\n"


def test_parse_pcr_csv_coerces_and_strips_commas():
    rows = fetch.parse_pcr_csv(_PCR)
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-06-01"
    assert rows[0]["equity_pcr"] == 0.72
    assert rows[0]["total_volume"] == 45000000       # comma-stripped int


def test_parse_vix_csv_skips_preamble_and_parses_mmddyyyy():
    rows = fetch.parse_vix_csv(_VIX)
    assert rows[0]["date"] == "2026-06-01"           # 06/01/2026 normalized
    assert rows[0]["close"] == 14.6 and rows[0]["open"] == 14.1


def test_parse_vix_csv_single_value_fallback_close():
    rows = fetch.parse_vix_csv(_VVIX)                 # DATE,VVIX (no CLOSE col)
    assert rows[0]["date"] == "2026-06-01" and rows[0]["close"] == 95.2


def test_fetch_vix_returns_none_on_403():
    def get(url):
        raise urllib.error.HTTPError(url, 403, "no", {}, None)

    assert fetch.fetch_vix("VIX", get=get) is None


def test_http_get_retries_503():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "e", {}, None)
        return _VVIX

    out = fetch._http_get("http://x", opener=opener, sleep=slept.append)
    assert out == _VVIX and slept == [1.0]
