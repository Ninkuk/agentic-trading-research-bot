import pytest

from sources.combiners.scorer import journal


def _fill(**kw):
    base = dict(
        symbol="XLE",
        side="buy",
        price=94.30,
        quantity=2,
        filled_at="2026-07-07T14:31:00+00:00",
        order_ref="ref-1",
    )
    base.update(kw)
    return base


def test_valid_doc():
    fills, passes, _, skipped = journal.parse_doc(
        {"fills": [_fill()], "passes": [{"symbol": "gld", "note": "crowded"}]}
    )
    assert skipped == 0
    assert fills[0]["symbol"] == "XLE"
    assert fills[0]["fill_date"] == "2026-07-07"  # 14:31Z -7h = same date
    assert fills[0]["quantity"] == 2.0
    assert passes[0]["symbol"] == "GLD"  # symbols normalized upper


def test_fill_date_is_phoenix_local():
    # 5:30pm Phoenix on 07-06 = 00:30Z on 07-07. A raw UTC date would match
    # the opinion formed at 9:05pm that evening — AFTER the fill (look-ahead).
    fills, _, _, _ = journal.parse_doc({"fills": [_fill(filled_at="2026-07-07T00:30:00+00:00")]})
    assert fills[0]["fill_date"] == "2026-07-06"


def test_naive_timestamp_treated_as_utc():
    fills, _, _, _ = journal.parse_doc({"fills": [_fill(filled_at="2026-07-07T14:31:00")]})
    assert fills[0]["fill_date"] == "2026-07-07"


def test_missing_fields_skip_and_count():
    doc = {
        "fills": [
            _fill(symbol=""),
            _fill(side="short"),
            _fill(price="n/a"),  # non-numeric price string is invalid
            _fill(price=True),  # bools are not prices
            _fill(filled_at=None),
            _fill(filled_at="not-a-date!!"),
            _fill(filled_at="2026-07-07"),  # date-only: ambiguous, rejected
            "not-a-dict",
            _fill(order_ref=None, note=None),  # still valid: refs optional
        ],
        "passes": [{"note": "no symbol"}, {"symbol": "TLT"}],
    }
    fills, passes, _, skipped = journal.parse_doc(doc)
    assert len(fills) == 1 and fills[0]["order_ref"] is None
    assert len(passes) == 1 and passes[0]["symbol"] == "TLT"
    assert skipped == 9


def test_non_numeric_quantity_becomes_none():
    fills, _, _, skipped = journal.parse_doc({"fills": [_fill(quantity="two")]})
    assert skipped == 0 and fills[0]["quantity"] is None


def test_fills_sorted_chronologically_buys_first_on_tie():
    doc = {
        "fills": [
            _fill(order_ref="r3", filled_at="2026-07-08T14:00:00+00:00", side="sell"),
            _fill(order_ref="r2", filled_at="2026-07-08T14:00:00+00:00"),
            _fill(order_ref="r1", filled_at="2026-07-07T14:00:00+00:00"),
        ]
    }
    fills, _, _, _ = journal.parse_doc(doc)
    assert [f["order_ref"] for f in fills] == ["r1", "r2", "r3"]


def test_non_dict_doc_raises():
    with pytest.raises(ValueError):
        journal.parse_doc(["not", "a", "dict"])


def test_non_string_symbol_skip_and_count():
    # Regression: non-string symbols (e.g., integers) must be skipped and counted,
    # never raise AttributeError
    doc = {
        "fills": [
            _fill(symbol=123),  # integer symbol should be skipped
            _fill(),  # valid fill
        ],
        "passes": [
            {"symbol": 456},  # integer symbol in pass should be skipped
            {"symbol": "TLT", "note": "good"},  # valid pass
        ],
    }
    fills, passes, _, skipped = journal.parse_doc(doc)
    assert len(fills) == 1 and fills[0]["symbol"] == "XLE"
    assert len(passes) == 1 and passes[0]["symbol"] == "TLT"
    assert skipped == 2  # one fill with bad symbol, one pass with bad symbol


def test_placed_agent_passthrough():
    fills, _, _, skipped = journal.parse_doc(
        {
            "fills": [
                _fill(placed_agent="drip"),
                _fill(order_ref="r2", placed_agent=7),  # non-string -> None
                _fill(order_ref="r3"),  # absent -> None
            ]
        }
    )
    assert skipped == 0
    assert [f["placed_agent"] for f in fills] == ["drip", None, None]


def test_parse_verdicts_validates_and_uppercases():
    fills, passes, verdicts, skipped = journal.parse_doc(
        {
            "verdicts": [
                {
                    "symbol": " bbai ",
                    "verdict": "pass",
                    "verdict_date": "2026-07-22",
                    "doc": "BBAI-2026-07-21.md",
                    "note": "unproven",
                },
                {"symbol": "CRML", "verdict": "hold", "verdict_date": "2026-07-22"},  # bad enum
                {
                    "symbol": "EOSE",
                    "verdict": "pass",
                    "verdict_date": "2026-07-22T04:00:00+00:00",
                },  # timestamp, not date
                {
                    "symbol": "EOSE",
                    "verdict": "pass",
                    "verdict_date": "2026-13-40",
                },  # not a real date
                {"symbol": "", "verdict": "buy", "verdict_date": "2026-07-22"},  # no symbol
                "not-a-dict",
            ]
        }
    )
    assert fills == [] and passes == []
    assert skipped == 5
    assert verdicts == [
        {
            "symbol": "BBAI",
            "verdict": "pass",
            "verdict_date": "2026-07-22",
            "doc": "BBAI-2026-07-21.md",
            "note": "unproven",
            # Absent unless the doc supplies a correction reason; only its
            # presence licenses overwriting an already-recorded verdict.
            "corrects": None,
        }
    ]


def test_parse_empty_doc_returns_four_empty():
    assert journal.parse_doc({}) == ([], [], [], 0)


def _option_fill(**kw):
    base = _fill(
        symbol="AAPL",
        price=2.50,
        quantity=1,
        order_ref="opt-1",
        contract_ref="AAPL260821C00250000",
        position_effect="open",
        right="call",
        expiration="2026-08-21",
    )
    base.update(kw)
    return base


def test_option_open_derives_directional_side():
    # (broker side, right) -> directional intent; sell here is sell-to-open.
    cases = [
        (("buy", "call"), "buy"),
        (("buy", "put"), "sell"),
        (("sell", "call"), "sell"),
        (("sell", "put"), "buy"),
    ]
    for i, ((side, right), want) in enumerate(cases):
        fills, _, _, skipped = journal.parse_doc(
            {"fills": [_option_fill(side=side, right=right, order_ref=f"o{i}")]}
        )
        assert skipped == 0 and fills[0]["side"] == want, (side, right)
        assert fills[0]["contract_ref"] == "AAPL260821C00250000"
        assert fills[0]["position_effect"] == "open"
        assert fills[0]["expiration"] == "2026-08-21"


def test_option_close_needs_no_right_or_expiration():
    fills, _, _, skipped = journal.parse_doc(
        {"fills": [_option_fill(position_effect="close", right=None, expiration=None)]}
    )
    assert skipped == 0
    assert fills[0]["position_effect"] == "close"
    assert fills[0]["side"] == "buy"  # broker side passes through untouched


def test_option_fill_validation_skips_and_counts():
    doc = {
        "fills": [
            _option_fill(position_effect=None),  # option fills need an effect
            _option_fill(position_effect="expire"),  # bad enum
            _option_fill(right=None),  # open without a right: no direction
            _option_fill(right="warrant"),  # bad right
            _option_fill(expiration=None),  # open without expiration
            _option_fill(expiration="2026-08-21T00:00:00"),  # timestamp, not date
            _option_fill(expiration="2026-13-40"),  # not a real date
            _option_fill(multi_leg=True),  # spec: refuse multi-leg at the parser
            _option_fill(),  # valid control
        ]
    }
    fills, _, _, skipped = journal.parse_doc(doc)
    assert len(fills) == 1 and skipped == 8


def test_strategy_ref_passthrough():
    fills, _, _, skipped = journal.parse_doc(
        {"fills": [_option_fill(strategy_ref="ord-77"), _fill(order_ref="eq-1")]}
    )
    assert skipped == 0
    assert fills[0]["strategy_ref"] == "ord-77"
    assert fills[1]["strategy_ref"] is None  # equity fill: absent -> None


def test_broker_decimal_strings_accepted_for_price_and_quantity():
    # Live shape (2026-07-31 fractional first flight): the broker returns
    # every number as a decimal string; a verbatim-copying session must not
    # lose the fill (price) or its size (quantity).
    fills, _, _, skipped = journal.parse_doc(
        {"fills": [_fill(price="178.141500", quantity="0.056135")]}
    )
    assert skipped == 0
    assert fills[0]["price"] == 178.1415
    assert fills[0]["quantity"] == 0.056135


def test_non_numeric_price_string_still_skips():
    fills, _, _, skipped = journal.parse_doc({"fills": [_fill(price="n/a")]})
    assert fills == [] and skipped == 1


def _odoc(**kw):
    fill = {
        "symbol": "XLE",
        "side": "buy",
        "price": 2.50,
        "quantity": 1,
        "filled_at": "2026-07-07T14:31:00+00:00",
        "order_ref": "o1",
        "contract_ref": "XLE260821C00095000",
        "position_effect": "open",
        "right": "call",
        "expiration": "2026-08-21",
    }
    fill.update(kw)
    return {"fills": [fill]}


def test_option_open_retains_broker_side_through_remap():
    fills, _, _, skipped = journal.parse_doc(_odoc(side="buy", right="put"))
    assert skipped == 0
    assert fills[0]["side"] == "sell"  # directional intent
    assert fills[0]["broker_side"] == "buy"  # cash-sign truth


def test_option_close_broker_side_equals_side():
    fills, _, _, _ = journal.parse_doc(
        _odoc(position_effect="close", side="sell", right=None, expiration=None)
    )
    assert fills[0]["side"] == "sell" and fills[0]["broker_side"] == "sell"


def test_option_fill_requires_positive_contracts():
    for bad in (None, 0, -1, "x"):
        _, _, _, skipped = journal.parse_doc(_odoc(quantity=bad))
        assert skipped == 1


def test_equity_fill_quantity_still_optional():
    doc = {
        "fills": [
            {
                "symbol": "XLE",
                "side": "buy",
                "price": 94.30,
                "filled_at": "2026-07-07T14:31:00+00:00",
            }
        ]
    }
    fills, _, _, skipped = journal.parse_doc(doc)
    assert skipped == 0 and fills[0]["quantity"] is None
    assert "broker_side" not in fills[0]


def test_terminal_only_on_close_and_zeroes_price():
    fills, _, _, skipped = journal.parse_doc(
        _odoc(position_effect="close", side="sell", terminal="assign", price=9.99)
    )
    assert skipped == 0
    assert fills[0]["terminal"] == "assign" and fills[0]["price"] == 0.0
    _, _, _, skipped = journal.parse_doc(_odoc(terminal="exercise"))  # on an open
    assert skipped == 1
    _, _, _, skipped = journal.parse_doc(
        _odoc(position_effect="close", side="sell", terminal="expired")
    )
    assert skipped == 1
