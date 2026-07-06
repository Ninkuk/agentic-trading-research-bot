# tests/test_cftc_fetch.py
import json
import urllib.error

import pytest

from sources.screeners.cftc_screener.fetch import (
    _build_url,
    _headers,
    _http_get,
    _make_opener,
    _urlopen,
    fetch_market_rows,
    parse_rows,
)

# One realistic Socrata record (subset of the 133 fields), values as strings.
REC = {
    "cftc_contract_market_code": "088691",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-06-23T00:00:00.000",
    "open_interest_all": "352167",
    "noncomm_positions_long_all": "217028",
    "noncomm_positions_short_all": "35689",
    "noncomm_positions_spread": "31295",  # NOTE: no _all suffix
    "comm_positions_long_all": "64579",
    "comm_positions_short_all": "269983",
    "nonrept_positions_long_all": "39265",
    "nonrept_positions_short_all": "15200",
    "change_in_open_interest_all": "12837",
    "change_in_noncomm_long_all": "5901",
    "change_in_noncomm_short_all": "4782",
    "change_in_comm_long_all": "6359",
    "change_in_comm_short_all": "4200",
    "pct_of_oi_noncomm_long_all": "61.6",
    "pct_of_oi_noncomm_short_all": "10.1",
    "pct_of_oi_comm_long_all": "18.3",
    "pct_of_oi_comm_short_all": "76.7",
    "traders_tot_all": "282",
    "traders_noncomm_long_all": "152",
    "traders_noncomm_short_all": "61",
    "traders_comm_long_all": "45",
    "traders_comm_short_all": "46",
    "conc_net_le_4_tdr_long_all": "20.2",
    "conc_net_le_8_tdr_long_all": "28.4",
    "conc_net_le_4_tdr_short_all": "35.5",
    "conc_net_le_8_tdr_short_all": "51.1",
}


def test_parse_rows_maps_and_coerces():
    [row] = parse_rows([REC])
    assert row["code"] == "088691"
    assert row["report_date"] == "2026-06-23"  # timestamp truncated
    assert row["name"] == "GOLD - COMMODITY EXCHANGE INC."
    assert row["open_interest"] == 352167  # int
    assert row["noncomm_long"] == 217028
    assert row["noncomm_spread"] == 31295  # sourced from _spread (no _all)
    assert row["pct_oi_noncomm_long"] == 61.6  # float
    assert row["conc_net_8_short"] == 51.1
    assert row["traders_total"] == 282


def test_parse_rows_missing_fields_become_none():
    [row] = parse_rows(
        [{"cftc_contract_market_code": "X", "report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000"}]
    )
    assert row["open_interest"] is None
    assert row["pct_oi_comm_long"] is None


def test_parse_rows_skips_records_without_code_or_date():
    assert parse_rows([{"report_date_as_yyyy_mm_dd": "2026-01-06T00:00:00.000"}]) == []
    assert parse_rows([{"cftc_contract_market_code": "X"}]) == []


def test_build_url_full_history():
    url = _build_url("088691")
    assert url.startswith("https://publicreporting.cftc.gov/resource/6dca-aqww.json?")
    assert "cftc_contract_market_code%3D%27088691%27" in url  # code='088691' urlencoded
    assert "report_date_as_yyyy_mm_dd" in url and "order" in url


def test_build_url_incremental_uses_since():
    url = _build_url("088691", since="2026-06-23")
    assert "2026-06-23T00%3A00%3A00" in url  # > 'since T00:00:00'


def test_headers_includes_token_when_present():
    assert _headers("TOK")["X-App-Token"] == "TOK"


def test_headers_omits_token_when_absent():
    assert "X-App-Token" not in _headers()


def test_make_opener_without_token_is_default():
    assert _make_opener(None) is _urlopen


def test_make_opener_with_token_is_distinct_opener():
    op = _make_opener("TOK")
    assert op is not _urlopen and callable(op)


def test_fetch_market_rows_parses_and_passes_since():
    seen = {}

    def fake_get(url, opener=None):
        seen["url"] = url
        return json.dumps([REC])

    rows = fetch_market_rows("088691", since="2026-06-16", get=fake_get)
    assert rows[0]["code"] == "088691"
    assert "2026-06-16T00%3A00%3A00" in seen["url"]


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


# --- family extension ---
from sources.screeners.cftc_screener.fetch import DISAGG_FIELDS, LEGACY_FIELDS, TFF_FIELDS

# A Disaggregated Socrata record (subset), values as strings.
DISAGG_REC = {
    "cftc_contract_market_code": "088691",
    "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
    "report_date_as_yyyy_mm_dd": "2026-06-23T00:00:00.000",
    "open_interest_all": "500000",
    "m_money_positions_long_all": "120000",
    "m_money_positions_short_all": "40000",
    "swap_positions_long_all": "30000",
    "pct_of_oi_m_money_long_all": "24.0",
    "conc_net_le_4_tdr_long_all": "18.2",
}


def test_field_maps_are_disjoint_triples():
    for fmap in (LEGACY_FIELDS, DISAGG_FIELDS, TFF_FIELDS):
        assert fmap, "field map must be non-empty"
        for col, api, cast in fmap:  # unpack proves 3-tuple shape
            assert isinstance(col, str) and isinstance(api, str)
            assert cast in (int, float)
        cols = [c for c, _a, _cast in fmap]
        assert len(cols) == len(set(cols)), "db columns must be unique"


def test_build_url_targets_family_dataset():
    url = _build_url("088691", dataset_id="72hh-3qpy")
    assert url.startswith("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?")
    assert "cftc_contract_market_code%3D%27088691%27" in url


def test_build_url_defaults_to_legacy_dataset():
    assert _build_url("088691").startswith(
        "https://publicreporting.cftc.gov/resource/6dca-aqww.json?"
    )


def test_parse_rows_with_disagg_field_map():
    [row] = parse_rows([DISAGG_REC], DISAGG_FIELDS)
    assert row["code"] == "088691"
    assert row["report_date"] == "2026-06-23"  # timestamp truncated
    assert row["name"] == "GOLD - COMMODITY EXCHANGE INC."
    assert row["mm_long"] == 120000  # int coercion
    assert row["mm_short"] == 40000
    assert row["pct_oi_mm_long"] == 24.0  # float coercion
    assert row["conc_net_4_long"] == 18.2
    assert row["mm_spread"] is None  # absent -> None


def test_fetch_market_rows_threads_dataset_and_field_map():
    seen = {}

    def fake_get(url, opener=None):
        seen["url"] = url
        return json.dumps([DISAGG_REC])

    rows = fetch_market_rows(
        "088691", dataset_id="72hh-3qpy", field_map=DISAGG_FIELDS, get=fake_get
    )
    assert "72hh-3qpy.json" in seen["url"]
    assert rows[0]["mm_long"] == 120000
