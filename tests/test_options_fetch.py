import json
import urllib.error

import pytest

from cboe_options import fetch


def _payload():
    """Trimmed CBOE chain: 2 calls + 1 put on one expiration."""
    return {
        "timestamp": "2026-07-03 17:46:09",
        "symbol": "AAPL",
        "data": {
            "symbol": "AAPL", "current_price": 308.45, "close": 308.63,
            "iv30": 27.803, "last_trade_time": "2026-07-02T16:00:00",
            "options": [
                {"option": "AAPL260717C00210000", "bid": 97.8, "ask": 100.35,
                 "iv": 1.02, "delta": 0.97, "gamma": 0.0008, "theta": -0.13,
                 "vega": 0.03, "rho": 0.07, "open_interest": 3131.0,
                 "volume": 40.0, "last_trade_price": 99.0, "theo": 99.08},
                {"option": "AAPL260717C00300000", "bid": 15.0, "ask": 15.5,
                 "iv": 0.30, "delta": 0.55, "gamma": 0.01, "theta": -0.2,
                 "vega": 0.4, "rho": 0.1, "open_interest": 0.0,
                 "volume": 500.0, "last_trade_price": 15.2, "theo": 15.25},
                {"option": "AAPL260717P00300000", "bid": 6.0, "ask": 6.4,
                 "iv": 0.28, "delta": -0.45, "gamma": 0.01, "theta": -0.18,
                 "vega": 0.38, "rho": -0.09, "open_interest": 2000.0,
                 "volume": 300.0, "last_trade_price": 6.2, "theo": 6.2},
            ],
        },
    }


def test_chain_url_equity_and_index():
    assert fetch.chain_url("AAPL", False).endswith("/options/AAPL.json")
    assert fetch.chain_url("SPX", True).endswith("/options/_SPX.json")


def test_parse_occ_call_and_put():
    assert fetch.parse_occ("AAPL260717C00210000") == (
        "AAPL", "2026-07-17", "call", 210.0)
    assert fetch.parse_occ("AAPL260717P00300000") == (
        "AAPL", "2026-07-17", "put", 300.0)


def test_parse_occ_index_and_adjusted_roots():
    # index root with digits, and a fractional strike
    assert fetch.parse_occ("SPXW260320C05000000")[0] == "SPXW"
    assert fetch.parse_occ("AAPL1260717C00007500") == (
        "AAPL1", "2026-07-17", "call", 7.5)


def test_parse_occ_rejects_garbage():
    assert fetch.parse_occ("NOTANOPTION") is None
    assert fetch.parse_occ("") is None


def test_session_date_prefers_last_trade_time():
    assert fetch.session_date(_payload()) == "2026-07-02"
    # falls back to top-level timestamp date when last_trade_time missing
    p = _payload(); p["data"]["last_trade_time"] = None
    assert fetch.session_date(p) == "2026-07-03"
    assert fetch.session_date({"data": {}}) is None


def test_parse_chain_contracts_and_derived():
    daily, contracts = fetch.parse_chain(_payload(), "AAPL")
    assert len(contracts) == 3
    c0 = next(c for c in contracts if c["occ_symbol"] == "AAPL260717C00210000")
    assert c0["underlying"] == "AAPL"
    assert c0["expiration"] == "2026-07-17"
    assert c0["type"] == "call" and c0["strike"] == 210.0
    assert c0["open_interest"] == 3131 and c0["volume"] == 40
    assert c0["mark"] == pytest.approx((97.8 + 100.35) / 2)
    assert c0["vol_oi_ratio"] == pytest.approx(40 / 3131)
    assert c0["underlying_price"] == 308.45
    # zero-OI contract uses max(oi,1) => ratio == volume
    c_zero = next(c for c in contracts if c["occ_symbol"] == "AAPL260717C00300000")
    assert c_zero["vol_oi_ratio"] == pytest.approx(500.0)


def test_parse_chain_daily_rollup():
    daily, _ = fetch.parse_chain(_payload(), "AAPL")
    assert daily["underlying"] == "AAPL"
    assert daily["iv30"] == 27.803
    assert daily["total_call_volume"] == 540   # 40 + 500
    assert daily["total_put_volume"] == 300
    assert daily["put_call_volume_ratio"] == pytest.approx(300 / 540)
    assert daily["total_call_oi"] == 3131       # 3131 + 0
    assert daily["total_put_oi"] == 2000
    assert daily["put_call_oi_ratio"] == pytest.approx(2000 / 3131)


def test_fetch_chain_404_returns_none():
    def get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
    assert fetch.fetch_chain("ZZZZ", False, get=get) is None


def test_fetch_chain_parses_json():
    body = json.dumps(_payload())
    assert fetch.fetch_chain("AAPL", False, get=lambda url, opener=None: body)[
        "symbol"] == "AAPL"


def test_http_get_retries_then_raises_non_retryable():
    calls = {"n": 0}

    def opener(url):
        calls["n"] += 1
        raise urllib.error.HTTPError(url, 503, "busy", None, None)

    slept = []
    with pytest.raises(urllib.error.HTTPError):
        fetch._http_get("u", opener=opener, attempts=3, base_delay=0.1,
                        sleep=slept.append)
    assert calls["n"] == 3 and len(slept) == 2

    def opener403(url):
        raise urllib.error.HTTPError(url, 403, "no", None, None)
    with pytest.raises(urllib.error.HTTPError):
        fetch._http_get("u", opener=opener403, attempts=3, sleep=slept.append)
