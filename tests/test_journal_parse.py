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
    fills, passes, skipped = journal.parse_doc(
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
    fills, _, _ = journal.parse_doc({"fills": [_fill(filled_at="2026-07-07T00:30:00+00:00")]})
    assert fills[0]["fill_date"] == "2026-07-06"


def test_naive_timestamp_treated_as_utc():
    fills, _, _ = journal.parse_doc({"fills": [_fill(filled_at="2026-07-07T14:31:00")]})
    assert fills[0]["fill_date"] == "2026-07-07"


def test_missing_fields_skip_and_count():
    doc = {
        "fills": [
            _fill(symbol=""),
            _fill(side="short"),
            _fill(price="94.30"),  # string price is invalid
            _fill(price=True),  # bools are not prices
            _fill(filled_at=None),
            _fill(filled_at="not-a-date!!"),
            _fill(filled_at="2026-07-07"),  # date-only: ambiguous, rejected
            "not-a-dict",
            _fill(order_ref=None, note=None),  # still valid: refs optional
        ],
        "passes": [{"note": "no symbol"}, {"symbol": "TLT"}],
    }
    fills, passes, skipped = journal.parse_doc(doc)
    assert len(fills) == 1 and fills[0]["order_ref"] is None
    assert len(passes) == 1 and passes[0]["symbol"] == "TLT"
    assert skipped == 9


def test_non_numeric_quantity_becomes_none():
    fills, _, skipped = journal.parse_doc({"fills": [_fill(quantity="two")]})
    assert skipped == 0 and fills[0]["quantity"] is None


def test_fills_sorted_chronologically_buys_first_on_tie():
    doc = {
        "fills": [
            _fill(order_ref="r3", filled_at="2026-07-08T14:00:00+00:00", side="sell"),
            _fill(order_ref="r2", filled_at="2026-07-08T14:00:00+00:00"),
            _fill(order_ref="r1", filled_at="2026-07-07T14:00:00+00:00"),
        ]
    }
    fills, _, _ = journal.parse_doc(doc)
    assert [f["order_ref"] for f in fills] == ["r1", "r2", "r3"]


def test_missing_sections_ok():
    assert journal.parse_doc({}) == ([], [], 0)


def test_non_dict_doc_raises():
    with pytest.raises(ValueError):
        journal.parse_doc(["not", "a", "dict"])
