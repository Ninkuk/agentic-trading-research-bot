import urllib.error

from sources.screeners.cboe_stats import fetch

_VIX = ("Preamble line to skip\n"
        "DATE,OPEN,HIGH,LOW,CLOSE\n"
        "06/01/2026,14.1,15.0,13.9,14.6\n")
_VVIX = "DATE,VVIX\n2026-06-01,95.2\n"

# The stats the daily page server-renders into its Next.js RSC flight stream.
_PCR_PAYLOAD = (
    '{"data":{"optionsData":{'
    '"ratios":[{"name":"TOTAL PUT/CALL RATIO","value":"0.79"},'
    '{"name":"INDEX PUT/CALL RATIO","value":"0.97"},'
    '{"name":"EQUITY PUT/CALL RATIO","value":"0.53"}],'
    '"SUM OF ALL PRODUCTS":[{"name":"VOLUME","call":9428474,"put":7490078,'
    '"total":16918552},{"name":"OPEN INTEREST","call":1,"put":2,"total":3}]},'
    '"selectedDate":"2026-07-02","minDate":"2019-10-07"}}')


def _rsc_page(payload, split_at=60):
    """Wrap `payload` the way the live page ships it: escaped into JS string
    literals split across multiple self.__next_f.push chunks."""
    esc = payload.replace("\\", "\\\\").replace('"', '\\"')
    a, b = esc[:split_at], esc[split_at:]
    return (f'<html><script>self.__next_f.push([1,"{a}"])</script>'
            f'<script>self.__next_f.push([1,"{b}"])</script></html>')


def test_parse_pcr_page_reassembles_chunks_and_maps_row():
    rows = fetch.parse_pcr_page(_rsc_page(_PCR_PAYLOAD))
    assert rows == [{"date": "2026-07-02", "total_pcr": 0.79,
                     "equity_pcr": 0.53, "index_pcr": 0.97,
                     "total_volume": 16918552}]


def test_parse_pcr_page_without_stats_payload_yields_nothing():
    assert fetch.parse_pcr_page("<html><body>maintenance</body></html>") == []


def test_fetch_pcr_dt_param_and_403_skip():
    seen = []

    def get(url):
        seen.append(url)
        return _rsc_page(_PCR_PAYLOAD)

    fetch.fetch_pcr(get=get)
    assert "?dt=" not in seen[0]                     # no dt -> latest session
    fetch.fetch_pcr(get=get, dt="2026-06-30")
    assert seen[1].endswith("?dt=2026-06-30")

    def get403(url):
        raise urllib.error.HTTPError(url, 403, "no", {}, None)

    assert fetch.fetch_pcr(get=get403) is None       # skip, don't crash the run


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
