import pytest

from sources.screeners.portfolio_screener import fetch

DOC = {
    "account": {"equity": "205.37", "cash": 12.4, "buying_power": "12.40"},
    "positions": [
        {"symbol": "gld", "quantity": "0.5", "average_buy_price": "301.2", "market_value": 155.0},
        {"symbol": "AAPL"},  # no quantity -> skipped
        {"quantity": 3},  # no symbol -> skipped
        {"symbol": "BRK.B", "quantity": 1},
    ],
}  # dot -> dash normalize


def test_parse_snapshot_coerces_and_normalizes():
    account, positions, _, skipped = fetch.parse_snapshot(DOC)
    assert account == {"equity": 205.37, "cash": 12.4, "buying_power": 12.4}
    assert positions[0] == {
        "symbol": "GLD",
        "quantity": 0.5,
        "avg_cost": 301.2,
        "market_value": 155.0,
    }
    assert positions[1]["symbol"] == "BRK-B"
    assert positions[1]["avg_cost"] is None
    assert skipped == 2


def test_parse_snapshot_rejects_non_dict():
    with pytest.raises(ValueError):
        fetch.parse_snapshot([1, 2])
    with pytest.raises(ValueError):
        fetch.parse_snapshot({"account": {}, "positions": "nope"})


def test_parse_snapshot_missing_account_yields_nulls():
    account, positions, _, skipped = fetch.parse_snapshot({"positions": []})
    assert account == {"equity": None, "cash": None, "buying_power": None}
    assert positions == [] and skipped == 0


def test_parse_snapshot_alt_field_names():
    # MCP payloads vary; the catalog maps aliases (shares/avg_cost/equity)
    account, positions, _, _ = fetch.parse_snapshot(
        {
            "account": {"equity": 100},
            "positions": [{"symbol": "SPY", "shares": 2, "avg_cost": 50.0, "equity": 101.0}],
        }
    )
    assert positions[0] == {
        "symbol": "SPY",
        "quantity": 2.0,
        "avg_cost": 50.0,
        "market_value": 101.0,
    }


def test_parse_snapshot_non_numeric_quantity_skipped():
    _, positions, _, skipped = fetch.parse_snapshot(
        {"positions": [{"symbol": "SPY", "quantity": "lots"}]}
    )
    assert positions == [] and skipped == 1


OPTION_DOC = {
    "account": {"equity": 205.37},
    "positions": [],
    "option_positions": [
        {
            "occ_symbol": "XLE260821C00095000",
            "underlying": "xle",
            "type": "call",
            "strike": 95.0,
            "expiration": "2026-08-21",
            "quantity": "1",
            "avg_cost": 2.50,
            "market_value": 310.0,
            "multiplier": 100,
        },
        {
            "occ_symbol": "XLE260918P00090000",
            "underlying": "XLE",
            "type": "put",
            "strike": 90.0,
            "expiration": "2026-09-18",
            "quantity": 2,
            "position_type": "short",
        },
    ],
}


def test_parse_option_positions_normalizes_and_signs():
    _, _, options, skipped = fetch.parse_snapshot(OPTION_DOC)
    assert skipped == 0
    assert options[0] == {
        "occ_symbol": "XLE260821C00095000",
        "underlying": "XLE",
        "type": "call",
        "strike": 95.0,
        "expiration": "2026-08-21",
        "quantity": 1.0,
        "avg_cost": 2.50,
        "market_value": 310.0,
        "multiplier": 100.0,
    }
    # a short leg carries a NEGATIVE quantity — sign is how downstream heat
    # will net it, so it must be pinned here, not derived later
    assert options[1]["quantity"] == -2.0
    assert options[1]["avg_cost"] is None


def test_parse_option_positions_skips_and_counts():
    _, _, options, skipped = fetch.parse_snapshot(
        {
            "option_positions": [
                {"underlying": "XLE", "quantity": 1},  # no occ_symbol
                {"occ_symbol": "X", "quantity": 1},  # no underlying
                {"occ_symbol": "X", "underlying": "XLE"},  # no quantity
                {"occ_symbol": "X2", "underlying": "XLE", "quantity": "lots"},
                "not-a-dict",
                {  # valid; junk type/expiration degrade to None, never skip
                    "occ_symbol": "XLE260821C00095000",
                    "underlying": "XLE",
                    "quantity": 1,
                    "type": "warrant",
                    "expiration": "2026-08-21T00:00:00",
                },
            ]
        }
    )
    assert skipped == 5
    assert len(options) == 1
    assert options[0]["type"] is None and options[0]["expiration"] is None


def test_parse_option_positions_absent_is_empty():
    _, _, options, skipped = fetch.parse_snapshot({"positions": []})
    assert options == [] and skipped == 0


def test_parse_option_positions_non_list_raises():
    with pytest.raises(ValueError):
        fetch.parse_snapshot({"option_positions": "nope"})
