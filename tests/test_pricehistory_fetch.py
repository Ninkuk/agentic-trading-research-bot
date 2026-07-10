import pytest

from sources.combiners.scorer import pricehistory

# `c` is the split-adjusted close; `a` is ALSO dividend-adjusted. Fixtures keep
# them distinct so a parser reading the wrong field cannot pass.
BARS = [
    {"t": "2026-07-08", "c": 300.0, "a": 290.0},  # newest-first, as the API returns
    {"t": "2026-07-07", "c": 200.0, "a": 190.0},
    {"t": "2026-07-06", "c": 100.0, "a": 90.0},
]
FLAT = {"status": 200, "data": BARS}  # the ?range=Max shape
NESTED = {"status": 200, "data": {"data": BARS, "news": [], "other": {}}}  # the bare-URL shape
BEFORE = "2026-07-08"


def test_parse_history_accepts_the_flat_range_max_shape():
    assert pricehistory.parse_history(FLAT, BEFORE) == [
        ("2026-07-06", 100.0),
        ("2026-07-07", 200.0),
    ]


def test_parse_history_accepts_the_bare_url_dict_shape():
    """The bare URL nests one level deeper for some symbols and 404s for others.
    The shape is not stable across query strings, so tolerate both."""
    assert pricehistory.parse_history(NESTED, BEFORE) == [
        ("2026-07-06", 100.0),
        ("2026-07-07", 200.0),
    ]


def test_parse_history_returns_ascending_pairs():
    dates = [d for d, _ in pricehistory.parse_history(FLAT, "2026-07-09")]
    assert dates == sorted(dates), "API returns newest-first; the ledger wants ascending"


def test_parse_history_uses_c_not_a():
    """`a` is dividend-adjusted and would diverge from the forward feeder on
    every payer (XOM 2015-01-02: c=92.83, a=57.09)."""
    closes = [c for _, c in pricehistory.parse_history(FLAT, "2026-07-09")]
    assert closes == [100.0, 200.0, 300.0]
    assert 90.0 not in closes and 290.0 not in closes


def test_parse_history_drops_bars_on_or_after_before_date():
    """The settled-only rule: the current session's `c` is a live price while
    the market is open. `before_date` is exclusive."""
    out = pricehistory.parse_history(FLAT, "2026-07-07")
    assert out == [("2026-07-06", 100.0)]
    assert all(d < "2026-07-07" for d, _ in out)


def test_parse_history_drops_null_close_rather_than_defaulting():
    payload = {"data": [{"t": "2026-07-06", "c": None}, {"t": "2026-07-05", "c": 50.0}]}
    assert pricehistory.parse_history(payload, BEFORE) == [("2026-07-05", 50.0)]


def test_parse_history_returns_empty_list_for_an_empty_series():
    """A delisted symbol legitimately has no bars. That is not a schema error;
    run() is where a zero-row symbol becomes loud."""
    assert pricehistory.parse_history({"data": []}, BEFORE) == []


@pytest.mark.parametrize("payload", [{}, {"data": 5}, {"data": "nope"}])
def test_parse_history_raises_on_unexpected_payload_shape(payload):
    with pytest.raises((ValueError, KeyError, TypeError)):
        pricehistory.parse_history(payload, BEFORE)


@pytest.mark.parametrize("bad", [1717718400, "2026/07/06", "20260706", None])
def test_parse_history_raises_on_non_iso_date(bad):
    """001 assumed `t` was an epoch integer. It is an ISO string; a silent
    fromtimestamp() would have written garbage dates into a permanent table."""
    with pytest.raises(ValueError):
        pricehistory.parse_history({"data": [{"t": bad, "c": 1.0}]}, BEFORE)


def test_fetch_history_uses_injected_get_seam():
    seen = []

    def fake_get(symbol):
        seen.append(symbol)
        return FLAT

    rows = pricehistory.fetch_history("XLE", BEFORE, get=fake_get)
    assert seen == ["XLE"]
    assert rows == [("2026-07-06", 100.0), ("2026-07-07", 200.0)]
