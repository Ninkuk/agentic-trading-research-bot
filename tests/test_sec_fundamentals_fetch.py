import io
import json
import urllib.error
import zipfile

import pytest

from sec_fundamentals import fetch


def test_cik_str_zero_pads_to_ten_digits():
    assert fetch.cik_str(320193) == "CIK0000320193"


def test_parse_frame_maps_and_coerces():
    payload = {"data": [
        {"cik": 320193, "entityName": "APPLE INC", "end": "2024-09-28",
         "val": "391035000000", "accn": "0000320193-24-000123"},
        {"cik": 789019, "entityName": "MSFT", "end": "2024-06-30",
         "val": 245122000000, "accn": "x"},
    ]}
    rows = fetch.parse_frame(payload)
    assert rows[0]["cik"] == 320193
    assert rows[0]["value"] == 391035000000.0     # numeric string coerced
    assert rows[0]["period_end"] == "2024-09-28"
    assert rows[0]["accession"] == "0000320193-24-000123"
    assert rows[0]["form"] is None                # frames carry no form
    assert rows[1]["value"] == 245122000000.0


def test_fetch_frame_builds_url_with_unit_path_and_period(monkeypatch):
    seen = {}

    def get(url):
        seen["url"] = url
        return json.dumps({"data": []})

    fetch.fetch_frame("EarningsPerShareDiluted", "USD/shares", "CY2024Q3",
                      get=get)
    assert "/us-gaap/EarningsPerShareDiluted/USD-per-shares/CY2024Q3.json" in seen["url"]


def test_parse_company_facts_filters_curated_tags_and_coerces():
    payload = {"facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": [
            {"end": "2024-09-28", "val": 93736000000, "fy": 2024, "fp": "FY",
             "form": "10-K", "filed": "2024-11-01", "accn": "a1"},
        ]}},
        "SomeExtensionTag": {"units": {"USD": [
            {"end": "2024-09-28", "val": 1, "form": "10-K", "accn": "a2"}]}},
    }}}
    rows = fetch.parse_company_facts(payload, {"NetIncomeLoss"})
    assert len(rows) == 1                          # extension tag ignored
    r = rows[0]
    assert r["tag"] == "NetIncomeLoss" and r["form"] == "10-K"
    assert r["value"] == 93736000000.0 and r["period_end"] == "2024-09-28"
    assert r["fiscal_year"] == 2024 and r["accession"] == "a1"


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_frame_retries_403_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(403)
        return json.dumps({"data": []})

    # inject the opener into the shared bounded-backoff via a get closure
    def get(url):
        from edgar_screener.fetch import _http_get
        return _http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_frame("Assets", "USD", "CY2024Q3I", get=get)
    assert calls["n"] == 2 and slept == [1.0]


def test_bulk_zip_url_builds_quarter_path():
    url = fetch.bulk_zip_url(2023, 2)
    assert url.endswith("/2023q2.zip")
    assert "financial-statement-data-sets" in url


def test_fetch_bulk_returns_bytes_success_none_on_404_raises_other():
    assert fetch.fetch_bulk(2023, 2, get=lambda url: b"ZIPBYTES") == b"ZIPBYTES"

    def get_404(url):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)
    assert fetch.fetch_bulk(2099, 4, get=get_404) is None   # unpublished -> skip

    def get_500(url):
        raise urllib.error.HTTPError(url, 500, "boom", {}, None)
    with pytest.raises(urllib.error.HTTPError):
        fetch.fetch_bulk(2023, 2, get=get_500)


def test_parse_bulk_joins_num_and_sub_filters_tags_skips_empty():
    sub = "adsh\tcik\tname\tsic\tform\tperiod\tfy\tfp\tfiled\n" \
          "acc1\t320193\tAPPLE INC\t3571\t10-K\t20240928\t2024\tFY\t20241101\n"
    num = "adsh\ttag\tversion\tddate\tqtrs\tuom\tvalue\n" \
          "acc1\tNetIncomeLoss\tus-gaap/2024\t20240928\t4\tUSD\t93736000000\n" \
          "acc1\tIgnoredTag\tus-gaap/2024\t20240928\t4\tUSD\t1\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("sub.tsv", sub)
        z.writestr("num.tsv", num)
    rows = fetch.parse_bulk(buf.getvalue(), {"NetIncomeLoss"})
    assert len(rows) == 1
    assert rows[0]["cik"] == 320193 and rows[0]["form"] == "10-K"
    assert rows[0]["value"] == 93736000000.0
    assert rows[0]["period_end"] == "2024-09-28"   # ddate normalized to ISO
