import json
import urllib.error

from finra_ats import fetch

# Field names mirror the LIVE otcMarket/weeklySummary schema: the venue name is
# `marketParticipantName` (NOT `ATSName`, which does not exist in live records),
# and each record carries a `summaryTypeCode`. Only the granular per-(symbol,
# venue) ATS rows (`ATS_W_SMBL_FIRM`) are ingested — non-ATS OTC and aggregate
# roll-ups are filtered out (they'd double-count and carry no MPID).
_JSON = json.dumps([
    {"summaryTypeCode": "ATS_W_SMBL_FIRM", "weekStartDate": "2026-06-08",
     "issueSymbolIdentifier": "AAPL", "MPID": "UBSA",
     "marketParticipantName": "UBS ATS", "totalWeeklyTradeCount": "1234",
     "totalWeeklyShareQuantity": "567890", "tierIdentifier": "T1"},
    {"summaryTypeCode": "ATS_W_SMBL_FIRM", "weekStartDate": "2026-06-08",
     "issueSymbolIdentifier": "AAPL", "MPID": "", "marketParticipantName": "",
     "totalWeeklyTradeCount": "5", "totalWeeklyShareQuantity": "",
     "tierIdentifier": "T1"},   # blank MPID -> de-minimis sentinel (defensive)
    {"summaryTypeCode": "OTC_W_SMBL_FIRM", "weekStartDate": "2026-06-08",
     "issueSymbolIdentifier": "AAPL", "MPID": "", "totalWeeklyTradeCount": "50",
     "totalWeeklyShareQuantity": "999"},          # non-ATS OTC -> filtered out
    {"summaryTypeCode": "ATS_W_SMBL", "weekStartDate": "2026-06-08",
     "issueSymbolIdentifier": "AAPL", "MPID": "",
     "totalWeeklyShareQuantity": "888"},          # aggregate roll-up -> filtered
    {"summaryTypeCode": "ATS_W_SMBL_FIRM", "weekStartDate": "2026-06-08",
     "issueSymbolIdentifier": "", "MPID": "X",    # no symbol -> skipped
     "totalWeeklyTradeCount": "1"},
])


def test_week_body_selects_the_week():
    body = fetch.week_body("2026-06-08")
    dumped = json.dumps(body)
    assert "weekStartDate" in dumped and "2026-06-08" in dumped


def test_parse_rows_json_coerces_and_sentinels_deminimis():
    rows = fetch.parse_rows(_JSON, "json")
    # OTC, aggregate-rollup, and symbol-less rows all dropped -> 2 ATS rows
    assert len(rows) == 2
    assert {r["symbol"] for r in rows} == {"AAPL"}
    assert rows[0]["mpid"] == "UBSA" and rows[0]["share_quantity"] == 567890
    assert rows[0]["trade_count"] == 1234 and rows[0]["tier"] == "T1"
    assert rows[0]["ats_name"] == "UBS ATS"          # from marketParticipantName
    assert rows[1]["mpid"] == "NON_ATS_DEMINIMIS"    # blank MPID -> sentinel
    assert rows[1]["share_quantity"] is None         # blank -> None


def test_parse_rows_filters_non_ats_and_aggregate_summary_types():
    rows = fetch.parse_rows(_JSON, "json")
    # the OTC_W_SMBL_FIRM (999 shares) and ATS_W_SMBL rollup (888) are excluded
    assert all(r["share_quantity"] not in (999, 888) for r in rows)


def test_parse_rows_csv():
    csv_text = ("summaryTypeCode,weekStartDate,issueSymbolIdentifier,MPID,"
                "marketParticipantName,totalWeeklyTradeCount,"
                "totalWeeklyShareQuantity,tierIdentifier\n"
                "ATS_W_SMBL_FIRM,2026-06-08,MSFT,CDEL,Citadel Connect,10,2000,T1\n")
    rows = fetch.parse_rows(csv_text, "csv")
    assert rows == [{"week_start": "2026-06-08", "symbol": "MSFT",
                     "mpid": "CDEL", "ats_name": "Citadel Connect",
                     "trade_count": 10, "share_quantity": 2000, "tier": "T1"}]


def test_fetch_week_posts_and_parses(monkeypatch):
    seen = {}

    def opener(url):
        seen["url"] = url
        return _JSON

    rows = fetch.fetch_week("2026-06-08", opener=opener)
    assert len(rows) == 2
    assert "otcMarket" in seen["url"]


def test_fetch_week_returns_none_on_403_404():
    def opener(url):
        raise urllib.error.HTTPError(url, 404, "no", {}, None)

    assert fetch.fetch_week("2026-06-08", opener=opener) is None
