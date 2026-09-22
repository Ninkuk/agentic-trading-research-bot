import pytest

from sources.screeners.stock_analysis_screener.fetch import fetch_data_points, parse_data_points


def test_parse_data_points_extracts_ticker_map():
    raw = {
        "status": 200,
        "data": {
            "data": {
                "AAA": {"price": 10.0, "sector": "Tech"},
                "BBB": {"price": None, "sector": "Energy"},
            }
        },
    }
    out = parse_data_points(raw)
    assert out == {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": None, "sector": "Energy"},
    }


def test_parse_data_points_rejects_bad_shape():
    with pytest.raises(ValueError):
        parse_data_points({"status": 200, "data": {"data": []}})


def test_fetch_data_points_sends_descriptive_user_agent():
    # Cloudflare challenges the bare "Mozilla/5.0" token (HTTP 403, cf-mitigated:
    # challenge); the repo's descriptive UA passes. Pin it so a "tidy-up" can't
    # silently take the screener offline again.
    import io
    import json

    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["ua"] = req.get_header("User-agent")
        return io.BytesIO(json.dumps({"data": {"data": {"SPY": {"price": 1.0}}}}).encode())

    out = fetch_data_points(["price"], "e", urlopen=fake_urlopen)
    assert out == {"SPY": {"price": 1.0}}
    assert seen["ua"] == "agentic-trading-research-bot ninadk.dev@gmail.com"
