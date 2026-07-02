import pytest

from screener.fetch import parse_data_points


def test_parse_data_points_extracts_ticker_map():
    raw = {"status": 200, "data": {"data": {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": None, "sector": "Energy"},
    }}}
    out = parse_data_points(raw)
    assert out == {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": None, "sector": "Energy"},
    }


def test_parse_data_points_rejects_bad_shape():
    with pytest.raises(ValueError):
        parse_data_points({"status": 200, "data": {"data": []}})
