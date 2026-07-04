import json
import urllib.error

from sources.screeners.nyfed_screener import fetch


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


def test_parse_repo_ops_filters_by_type_and_extracts_rate_from_details():
    # /rp/results/search.json returns BOTH types; the parser keeps only the
    # requested one and pulls the rate from details[] (award, else offering).
    records = [
        {"operationId": "RRP1", "operationDate": "2026-06-01",
         "operationType": "Reverse Repo", "totalAmtSubmitted": "100",
         "totalAmtAccepted": "90",
         "details": [{"amtAccepted": 90, "percentOfferingRate": 4.25,
                      "percentAwardRate": 4.25}]},
        {"operationId": "RP2", "operationDate": "2026-06-01",
         "operationType": "Repo", "totalAmtSubmitted": "5",
         "totalAmtAccepted": "0",
         "details": [{"amtAccepted": 0, "percentOfferingRate": 3.75}]},
    ]
    rrp = fetch.parse_repo_ops(records, "reverse_repo")
    assert len(rrp) == 1                              # the Repo op is filtered out
    assert rrp[0]["operation_type"] == "reverse_repo"
    assert rrp[0]["operation_id"] == "RRP1"
    assert rrp[0]["total_submitted"] == 100.0 and rrp[0]["total_accepted"] == 90.0
    assert rrp[0]["award_rate"] == 4.25              # details percentAwardRate

    repo = fetch.parse_repo_ops(records, "repo")
    assert len(repo) == 1 and repo[0]["operation_id"] == "RP2"
    assert repo[0]["award_rate"] == 3.75             # offering-rate fallback


def test_parse_soma_holdings_melts_wide_format_per_security():
    # /soma/summary.json is wide: one row per date, security types as columns.
    rows = fetch.parse_soma_holdings([
        {"asOfDate": "2026-06-03", "mbs": "1000", "cmbs": "0.00", "tips": "500",
         "frn": "", "tipsInflationCompensation": "20", "notesbonds": "4000",
         "bills": "300", "agencies": "10", "total": "5830"}])
    by = {r["security_type"]: r["par_value"] for r in rows}
    assert by["mbs"] == 1000.0 and by["cmbs"] == 0.0     # zero is a real value
    assert by["notesbonds"] == 4000.0 and by["total"] == 5830.0
    assert "frn" not in by                               # blank cell skipped
    assert all(r["as_of_date"] == "2026-06-03" for r in rows)


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
