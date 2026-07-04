import json
from datetime import date

import pytest

from sources.monitors.earnings_calendar import fetch

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


# Real live shape (2026-07): rows moved from top-level data[].rows to
# earnings[week].days[day].symbols; per-symbol keys (s/n/t/e/eg/r/rg/m) unchanged.
# Top-level "days" carries counts only (no symbols) and must be ignored.
DECODED_NESTED = {
    "view": "Daily",
    "days": [{"date": "2026-07-06", "day": "Monday", "count": 2}],
    "earnings": [
        {"weekOf": "2026-07-06", "days": [
            {"date": "2026-07-06", "symbols": [
                {"s": "AAPL", "n": "Apple Inc.", "t": "amc", "e": 1.5, "eg": 10,
                 "r": 9e10, "rg": 5, "m": 3e12},
            ]},
            {"date": "2026-07-07", "symbols": [
                {"s": "MSFT", "n": "Microsoft Corp.", "t": "bmo", "e": 2.9},
            ]},
        ]},
    ],
}


def test_fetch_forward_decodes_new_nested_earnings_shape():
    rows = fetch.fetch_forward(get=lambda path: DECODED_NESTED)
    assert len(rows) == 2
    aapl = next(r for r in rows if r["ticker"] == "AAPL")
    assert aapl["date"] == "2026-07-06" and aapl["timing"] == "amc"
    assert aapl["name"] == "Apple Inc." and aapl["mktcap"] == 3e12
    msft = next(r for r in rows if r["ticker"] == "MSFT")
    assert msft["date"] == "2026-07-07" and msft["timing"] == "bmo"


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


def test_item_202_history_returns_earnings_filing_dates_per_ticker():
    subs = {"filings": {"recent": {
        "form": ["8-K", "10-Q", "8-K", "8-K"],
        "items": ["2.02,9.01", "", "5.02", "2.02"],   # 1st + 4th are earnings
        "filingDate": ["2026-07-07", "2026-05-01", "2026-06-01", "2026-04-05"],
    }}}
    hist = fetch.item_202_history(
        ["AAPL"], get=lambda url: json.dumps(subs),
        tmap=lambda: {320193: {"ticker": "AAPL", "title": "Apple Inc."}})
    assert hist == {"AAPL": ["2026-07-07", "2026-04-05"]}


def test_item_202_history_skips_unmapped_ticker():
    hist = fetch.item_202_history(
        ["NOPE"], get=lambda url: "{}",
        tmap=lambda: {320193: {"ticker": "AAPL", "title": "Apple"}})
    assert hist == {}


def test_estimate_next_report_projects_from_median_gap():
    dates = ["2026-01-15", "2026-04-16", "2026-07-16"]     # ~91-day cadence
    assert fetch.estimate_next_report(dates, "2026-07-20") == "2026-10-15"


def test_estimate_next_report_none_when_insufficient_history():
    assert fetch.estimate_next_report(["2026-04-16", "2026-07-16"],
                                      "2026-07-20") is None


def test_estimate_next_report_rolls_forward_past_today_for_stale_history():
    # a regular filer whose last 8-K is stale: roll the cadence forward so the
    # estimate is always the next FUTURE date, not one already in the past.
    dates = ["2025-07-01", "2025-10-01", "2025-12-30"]
    est = fetch.estimate_next_report(dates, "2026-07-20")
    assert est is not None
    assert date.fromisoformat(est) > date.fromisoformat("2026-07-20")


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
