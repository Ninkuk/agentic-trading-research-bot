import json
import urllib.error

from sources.screeners.treasury_screener import fetch


def test_build_url_encodes_fields_filter_sort_and_pagination():
    url = fetch._build_url("v2/accounting/od/debt_to_penny",
                           fields=["record_date", "tot_pub_debt_out_amt"],
                           filter_="record_date:gte:2026-01-01",
                           sort="record_date", page_size=500, page_number=2)
    assert "format=json" in url
    assert "page%5Bsize%5D=500" in url and "page%5Bnumber%5D=2" in url
    assert "record_date%3Agte%3A2026-01-01" in url          # filter encoded
    assert "record_date%2Ctot_pub_debt_out_amt" in url      # fields joined


def test_fetch_dataset_follows_pagination_until_next_null():
    pages = [
        {"data": [{"record_date": "2026-01-01"}], "links": {"next": "&page=2"}},
        {"data": [{"record_date": "2026-01-02"}], "links": {"next": None}},
    ]
    calls = {"n": 0}

    def get(url):
        i = calls["n"]
        calls["n"] += 1
        return json.dumps(pages[i])

    rows = fetch.fetch_dataset("v2/accounting/od/debt_to_penny", get=get)
    assert [r["record_date"] for r in rows] == ["2026-01-01", "2026-01-02"]
    assert calls["n"] == 2


def test_parse_dts_cash_coerces_and_keeps_account_type():
    rows = fetch.parse_dts_cash([
        {"record_date": "2026-01-02", "account_type": "Treasury General Account (TGA)",
         "open_today_bal": "750000", "close_today_bal": "800000"},
        {"record_date": "2026-01-02", "account_type": "Federal Reserve Account",
         "open_today_bal": "", "close_today_bal": None},
    ])
    assert rows[0]["close_balance"] == 800000.0
    assert rows[1]["open_balance"] is None      # blank -> None


def test_parse_debt_penny_and_avg_rates_and_auctions():
    d = fetch.parse_debt_penny([{"record_date": "2026-01-02",
        "tot_pub_debt_out_amt": "34000000000000",
        "debt_held_public_amt": "27000000000000",
        "intragov_hold_amt": "7000000000000"}])[0]
    assert d["tot_pub_debt_out"] == 34000000000000.0

    a = fetch.parse_avg_rates([{"record_date": "2026-01-31",
        "security_type_desc": "Marketable", "security_desc": "Treasury Notes",
        "avg_interest_rate_amt": "2.75"}])[0]
    assert a["avg_interest_rate"] == 2.75 and a["security_desc"] == "Treasury Notes"

    ua = fetch.parse_upcoming_auctions([{"cusip": "", "security_type": "Note",
        "security_term": "10-Year", "announcemt_date": "2026-01-05",
        "auction_date": "2026-01-12", "issue_date": "2026-01-15"}])[0]
    assert ua["auction_date"] == "2026-01-12" and ua["announcement_date"] == "2026-01-05"

    ar = fetch.parse_auction_results([{"cusip": "912828XX", "auction_date": "2026-01-12",
        "security_type": "Note", "security_term": "10-Year", "high_yield_rate": "4.1",
        "bid_to_cover_ratio": "2.6", "offering_amt": "39000000000",
        "total_accepted_amt": "39000000000"}])[0]
    assert ar["bid_to_cover_ratio"] == 2.6 and ar["high_yield"] == 4.1


def test_parse_yield_curve_extracts_tenors():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom"
        xmlns:m="http://x/m" xmlns:d="http://x/d"><entry><content>
        <m:properties>
          <d:NEW_DATE>2026-01-02T00:00:00</d:NEW_DATE>
          <d:BC_3MONTH>4.3</d:BC_3MONTH>
          <d:BC_2YEAR>3.8</d:BC_2YEAR>
          <d:BC_10YEAR>3.9</d:BC_10YEAR>
        </m:properties></content></entry></feed>"""
    rows = fetch.parse_yield_curve(xml)
    assert rows[0]["record_date"] == "2026-01-02"
    assert rows[0]["mo3"] == 4.3 and rows[0]["yr2"] == 3.8 and rows[0]["yr10"] == 3.9
    assert rows[0]["yr30"] is None              # absent tenor -> None


def test_parse_yield_curve_rejects_doctype_entity_bomb():
    import pytest
    bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "AAAA">]>'
            '<feed><entry></entry></feed>')
    with pytest.raises(ValueError):
        fetch.parse_yield_curve(bomb)


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "e", {}, None)


def test_fetch_dataset_retries_503_then_succeeds():
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise _http_error(503)
        return json.dumps({"data": [], "links": {"next": None}})

    def get(url):
        return fetch._http_get(url, opener=opener, sleep=slept.append)

    fetch.fetch_dataset("v2/accounting/od/debt_to_penny", get=get)
    assert calls["n"] == 2 and slept == [1.0]
