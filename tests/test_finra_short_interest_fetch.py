# tests/test_finra_short_interest_fetch.py
import urllib.error

import pytest

from sources.screeners.finra_short_interest.fetch import (
    _http_get,
    fetch_settlement,
    parse_file,
    settlement_url,
)

# Pipe-delimited despite .csv. Real 14-column FINRA layout; settlementDate is
# already ISO. Header + 3 keepable rows + 3 droppable rows.
SAMPLE = (
    "accountingYearMonthNumber|symbolCode|issueName|"
    "issuerServicesGroupExchangeCode|marketClassCode|"
    "currentShortPositionQuantity|previousShortPositionQuantity|stockSplitFlag|"
    "averageDailyVolumeQuantity|daysToCoverQuantity|revisionFlag|changePercent|"
    "changePreviousNumber|settlementDate\n"
    "202406|AAL|AMERICAN AIRLINES|A|NNM|1500000|1200000||500000|3.0|A|25.0|300000|2024-06-14\n"
    "202406|ILLQ|ILLIQUID CORP|S|OTC|900000|900000||1000|999.99||-0.0|-100|2024-06-14\n"
    "202406|BLNK|BLANK NUMS|R|NNM|5000|||||||-50|2024-06-14\n"  # blank prev/adv/dtc/rev/chg -> None
    "202406||NO SYMBOL|A|NNM|100|100||500|1|A|0|0|2024-06-14\n"  # blank symbol -> skipped
    "202406|SHORT|TOO FEW FIELDS|A|NNM|100\n"  # < 14 fields -> skipped
    "Trailer|rec|count|x|y|z|w|v|u|t|s|r|q|badsdate\n"  # bad qty/date -> skipped
)


def test_parse_file_maps_columns_and_keeps_three_rows():
    rows = parse_file(SAMPLE)
    assert len(rows) == 3  # AAL + ILLQ + BLNK
    assert rows[0] == {
        "symbol": "AAL",
        "issue_name": "AMERICAN AIRLINES",
        "settlement_date": "2024-06-14",
        "current_short_qty": 1500000,
        "previous_short_qty": 1200000,
        "avg_daily_volume": 500000,
        "days_to_cover": pytest.approx(3.0),
        "change_pct": pytest.approx(25.0),
        "revision_flag": "A",
        "market_class": "NNM",
    }


def test_parse_file_blank_numerics_and_flags_become_none():
    blnk = [r for r in parse_file(SAMPLE) if r["symbol"] == "BLNK"][0]
    assert blnk["previous_short_qty"] is None
    assert blnk["avg_daily_volume"] is None
    assert blnk["change_pct"] is None
    assert blnk["days_to_cover"] is None
    assert blnk["revision_flag"] is None


def test_parse_file_header_row_is_dropped():
    header_only = SAMPLE.splitlines()[0] + "\n"
    assert parse_file(header_only) == []


def test_settlement_url_formats_settlement_date():
    assert settlement_url("2024-06-14") == (
        "https://cdn.finra.org/equity/otcmarket/biweekly/shrt20240614.csv"
    )


def test_fetch_settlement_parses_returned_text():
    def fake_get(url, opener=None):
        assert url.endswith("shrt20240614.csv")
        return SAMPLE

    rows = fetch_settlement("2024-06-14", get=fake_get)
    assert len(rows) == 3


def test_fetch_settlement_returns_none_on_404():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    assert fetch_settlement("2099-01-15", get=fake_get) is None


def test_fetch_settlement_returns_none_on_403():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)

    assert fetch_settlement("2099-01-15", get=fake_get) is None


def test_fetch_settlement_reraises_non_404_non_403():
    def fake_get(url, opener=None):
        raise urllib.error.HTTPError(url, 500, "err", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        fetch_settlement("2024-06-14", get=fake_get)


def test_http_get_retries_on_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0]
