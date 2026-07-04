import json

import pytest

from earnings_calendar import fetch

# Decoded fixture shaped per the catalog: day-blocks each with a date + symbol
# rows (s/n/t/e/eg/r/rg/m). Confirm vs a live decode at implementation.
DECODED = {"data": [
    {"date": "2026-07-06", "day": "Monday", "count": 2, "rows": [
        {"s": "AAPL", "n": "Apple Inc.", "t": "amc", "e": 1.5, "eg": 10,
         "r": 9e10, "rg": 5, "m": 3e12},
        {"s": "MSFT", "n": "Microsoft Corp.", "t": "bmo", "e": 2.9, "eg": 8,
         "r": 6e10, "rg": 12, "m": 2.5e12},
    ]},
]}


def test_fetch_forward_flattens_and_normalizes():
    rows = fetch.fetch_forward(get=lambda path: DECODED)
    assert len(rows) == 2
    aapl = next(r for r in rows if r["ticker"] == "AAPL")
    assert aapl["date"] == "2026-07-06" and aapl["timing"] == "amc"
    assert aapl["name"] == "Apple Inc." and aapl["mktcap"] == 3e12
    assert aapl["eps_est"] == 1.5


def test_fetch_forward_raises_on_zero_rows_from_nonempty():
    with pytest.raises(fetch.EarningsFeedError):
        fetch.fetch_forward(get=lambda path: {"data": [{"date": "2026-07-06",
                                                        "rows": []}]})


def test_timing_to_time_mapping():
    assert fetch.timing_to_time("bmo") == "before open"
    assert fetch.timing_to_time("amc") == "after close"
    assert fetch.timing_to_time("") is None


def test_confirm_via_edgar_matches_item_202_near_date():
    subs = {"filings": {"recent": {
        "form": ["8-K", "10-Q", "8-K"],
        "items": ["2.02,9.01", "", "5.02"],       # only the first is earnings
        "filingDate": ["2026-07-07", "2026-05-01", "2026-06-01"],
    }}}

    def get(url):
        return json.dumps(subs)

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    confirmed = fetch.confirm_via_edgar(
        ["AAPL"], {"AAPL": ["2026-07-06"]}, get=get, tmap=tmap)
    assert ("AAPL", "2026-07-06") in confirmed     # 8-K 2.02 filed 07-07 (±3d)


def test_confirm_skips_unmapped_ticker_and_non_202():
    subs = {"filings": {"recent": {"form": ["8-K"], "items": ["5.02"],
                                   "filingDate": ["2026-07-07"]}}}

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    # MSFT unmapped -> skipped; AAPL has no 2.02 near date -> not confirmed
    confirmed = fetch.confirm_via_edgar(
        ["AAPL", "MSFT"], {"AAPL": ["2026-07-06"], "MSFT": ["2026-07-06"]},
        get=lambda url: json.dumps(subs), tmap=tmap)
    assert confirmed == set()


def test_confirm_per_ticker_error_is_skipped_not_fatal(capsys):
    def get(url):
        raise RuntimeError("https://data.sec.gov?x=SECRET boom")

    def tmap():
        return {320193: {"ticker": "AAPL", "title": "Apple Inc."}}

    confirmed = fetch.confirm_via_edgar(
        ["AAPL"], {"AAPL": ["2026-07-06"]}, get=get, tmap=tmap)
    assert confirmed == set()
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
