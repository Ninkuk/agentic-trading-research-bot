import pytest

from sources.screeners.portfolio_screener import fetch

DOC = {"account": {"equity": "205.37", "cash": 12.4, "buying_power": "12.40"},
       "positions": [
           {"symbol": "gld", "quantity": "0.5", "average_buy_price": "301.2",
            "market_value": 155.0},
           {"symbol": "AAPL"},                        # no quantity -> skipped
           {"quantity": 3},                           # no symbol -> skipped
           {"symbol": "BRK.B", "quantity": 1}]}       # dot -> dash normalize


def test_parse_snapshot_coerces_and_normalizes():
    account, positions, skipped = fetch.parse_snapshot(DOC)
    assert account == {"equity": 205.37, "cash": 12.4, "buying_power": 12.4}
    assert positions[0] == {"symbol": "GLD", "quantity": 0.5,
                            "avg_cost": 301.2, "market_value": 155.0}
    assert positions[1]["symbol"] == "BRK-B"
    assert positions[1]["avg_cost"] is None
    assert skipped == 2


def test_parse_snapshot_rejects_non_dict():
    with pytest.raises(ValueError):
        fetch.parse_snapshot([1, 2])
    with pytest.raises(ValueError):
        fetch.parse_snapshot({"account": {}, "positions": "nope"})


def test_parse_snapshot_missing_account_yields_nulls():
    account, positions, skipped = fetch.parse_snapshot({"positions": []})
    assert account == {"equity": None, "cash": None, "buying_power": None}
    assert positions == [] and skipped == 0


def test_parse_snapshot_alt_field_names():
    # MCP payloads vary; the catalog maps aliases (shares/avg_cost/equity)
    account, positions, _ = fetch.parse_snapshot({
        "account": {"equity": 100},
        "positions": [{"symbol": "SPY", "shares": 2, "avg_cost": 50.0,
                       "equity": 101.0}]})
    assert positions[0] == {"symbol": "SPY", "quantity": 2.0,
                            "avg_cost": 50.0, "market_value": 101.0}


def test_parse_snapshot_non_numeric_quantity_skipped():
    _, positions, skipped = fetch.parse_snapshot(
        {"positions": [{"symbol": "SPY", "quantity": "lots"}]})
    assert positions == [] and skipped == 1
