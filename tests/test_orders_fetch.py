import copy

import pytest

from sources.screeners.orders import fetch

PLAN_DOC = {
    "as_of": "2026-07-27T13:33:00+00:00",
    "quotes": [
        {"symbol": "TSLA", "ask": 312.40, "quote_ts": "2026-07-27T13:32:50+00:00"},
        {"symbol": "HALT", "ask": None, "quote_ts": None},
    ],
    "portfolio": {"settled_cash": 4200.50},
}


def test_parse_plan_input():
    pi = fetch.parse_plan_input(PLAN_DOC)
    assert pi.as_of == "2026-07-27T13:33:00+00:00"
    assert pi.quotes["TSLA"].ask == 312.40
    assert pi.quotes["HALT"].ask is None  # missing ask parses; plan vetoes it
    assert pi.settled_cash == 4200.50


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("as_of"),
        lambda d: d.pop("portfolio"),
        lambda d: d["portfolio"].pop("settled_cash"),
        lambda d: d.__setitem__("quotes", "nope"),
        lambda d: d["quotes"][0].pop("symbol"),
    ],
)
def test_structural_problems_raise_valueerror(mutate):
    doc = copy.deepcopy(PLAN_DOC)
    mutate(doc)
    with pytest.raises(ValueError):
        fetch.parse_plan_input(doc)


def test_parse_record_input():
    doc = {
        "results": [
            {
                "queue_id": 3,
                "ref_id": "u-u-i-d",
                "account_number": "TESTACCT0",
                "order_id": "ord-1",
                "state": "placed",
                "raw": {"anything": True},
            },
            {
                "queue_id": 4,
                "ref_id": "u2",
                "account_number": "TESTACCT0",
                "order_id": None,
                "state": "error",
                "raw": {"detail": "rejected"},
            },
        ]
    }
    results = fetch.parse_record_input(doc)
    assert [r.queue_id for r in results] == [3, 4]
    assert results[0].state == "placed" and results[1].order_id is None
    with pytest.raises(ValueError):
        fetch.parse_record_input({"results": [{"queue_id": 1, "state": "exploded"}]})


def test_parse_reconcile_input():
    doc = {
        "orders": [{"order_id": "ord-1", "ref_id": "u-u-i-d", "symbol": "TSLA", "state": "filled"}]
    }
    orders = fetch.parse_reconcile_input(doc)
    assert orders[0].order_id == "ord-1"
