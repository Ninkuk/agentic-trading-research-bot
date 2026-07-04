import json
import urllib.error

from nyfed_screener import fetch


def test_build_url_encodes_dates():
    url = fetch._build_url("/rates/all/search.json",
                           {"startDate": "2026-01-01", "endDate": "2026-02-01"})
    assert "startDate=2026-01-01" in url and "endDate=2026-02-01" in url


def test_fetch_domain_extracts_records_from_envelope():
    payload = {"refRates": [{"effectiveDate": "2026-06-01", "type": "SOFR",
                             "percentRate": "5.31"}]}

    def get(url):
        return json.dumps(payload)

    recs = fetch.fetch_domain("/rates/all/search.json", get=get)
    assert recs and recs[0]["type"] == "SOFR"


def test_parse_reference_rates_coerces():
    rows = fetch.parse_reference_rates([
        {"effectiveDate": "2026-06-01", "type": "SOFR", "percentRate": "5.31",
         "volumeInBillions": "2100"},
        {"effectiveDate": "", "type": "SOFR", "percentRate": "5.0"},   # no date
    ])
    assert len(rows) == 1
    assert rows[0]["rate_type"] == "SOFR" and rows[0]["percent_rate"] == 5.31
    assert rows[0]["volume_bn"] == 2100.0


def test_parse_repo_ops_tags_operation_type():
    rows = fetch.parse_repo_ops([
        {"operationId": "RP1", "operationDate": "2026-06-01",
         "totalAmtSubmitted": "100", "totalAmtAccepted": "90"}], "reverse_repo")
    assert rows[0]["operation_type"] == "reverse_repo"
    assert rows[0]["operation_id"] == "RP1" and rows[0]["total_accepted"] == 90.0


def test_parse_soma_holdings():
    rows = fetch.parse_soma_holdings([
        {"asOfDate": "2026-06-03", "securityType": "total", "parValue": "7.2e12"}])
    assert rows[0]["as_of_date"] == "2026-06-03"
    assert rows[0]["security_type"] == "total" and rows[0]["par_value"] == 7.2e12


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_domain_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps({"refRates": []})

    def get(url):
        return fetch._http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_domain("/rates/all/search.json", get=get)
    assert calls["n"] == 2 and slept == [1.0]
