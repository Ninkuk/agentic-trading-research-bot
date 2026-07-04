import pytest

from sources.screeners.stock_analysis_screener import catalog
from sources.screeners.stock_analysis_screener.catalog import DataPoint, parse_catalog


def make_raw():
    # Minimal SvelteKit index-deduplicated payload.
    # pool[0] is the top object; every value is an index into the pool.
    pool = [
        {"count": 1, "data": 2, "dataPoints": 3},  # 0: top
        2,                                          # 1: count = 2
        [],                                         # 2: data (unused by catalog)
        [4, 5],                                     # 3: dataPoints -> defs at 4,5
        {"name": 6, "id": 7, "cat": 8},             # 4: def (no proOnly)
        {"name": 9, "id": 10, "cat": 8, "proOnly": 11},  # 5: def (proOnly)
        "Market Cap",                               # 6
        "marketCap",                                # 7
        "Valuation & Ratios",                       # 8
        "Altman Z-Score",                           # 9
        "zScore",                                   # 10
        True,                                       # 11
    ]
    return {"nodes": [
        {"type": "data", "data": ["session-node"]},
        {"type": "data", "data": pool},
    ]}


def test_parse_catalog_returns_points_and_count():
    points, count = parse_catalog(make_raw())
    assert count == 2
    assert points == [
        DataPoint("marketCap", "Market Cap", "Valuation & Ratios", False),
        DataPoint("zScore", "Altman Z-Score", "Valuation & Ratios", True),
    ]


def test_parse_catalog_raises_when_payload_missing():
    with pytest.raises(ValueError):
        parse_catalog({"nodes": [{"type": "data", "data": ["only-session"]}]})


def test_route_for_maps_screener_type_to_catalog_route():
    # Each screener type has its own catalog with different data-point ids;
    # fetching the stocks catalog for an ETF run silently sends wrong ids.
    assert catalog.route_for("s") == "/stocks/screener/"
    assert catalog.route_for("e") == "/etf/screener/"


def test_route_for_rejects_unknown_type():
    with pytest.raises(ValueError):
        catalog.route_for("x")
