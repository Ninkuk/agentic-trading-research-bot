import pytest

from sources.screeners.orders import catalog

GOOD_ENV = {
    "ROBINHOOD_ACCOUNT_NUMBER": "TESTACCT0",
    "ORDERS_MAX_ORDER_NOTIONAL": "1000",
    "ORDERS_MAX_DAILY_NOTIONAL": "2000",
    "ORDERS_CASH_FLOOR": "500",
}


def test_load_limits_happy_path():
    lim = catalog.load_limits(GOOD_ENV)
    assert lim.account_number == "TESTACCT0"
    assert lim.max_order_notional == 1000.0
    assert lim.cash_floor == 500.0


@pytest.mark.parametrize("missing", sorted(GOOD_ENV))
def test_each_var_is_required(missing):
    env = {k: v for k, v in GOOD_ENV.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        catalog.load_limits(env)


def test_env_cannot_exceed_committed_ceilings():
    env = dict(GOOD_ENV, ORDERS_MAX_ORDER_NOTIONAL=str(catalog.HARD_MAX_ORDER_NOTIONAL + 1))
    with pytest.raises(ValueError, match="ceiling"):
        catalog.load_limits(env)
    env = dict(GOOD_ENV, ORDERS_MAX_DAILY_NOTIONAL=str(catalog.HARD_MAX_DAILY_NOTIONAL + 1))
    with pytest.raises(ValueError, match="ceiling"):
        catalog.load_limits(env)


def test_nonnumeric_and_negative_refused():
    for k in ("ORDERS_MAX_ORDER_NOTIONAL", "ORDERS_CASH_FLOOR"):
        with pytest.raises(ValueError):
            catalog.load_limits(dict(GOOD_ENV, **{k: "abc"}))
        with pytest.raises(ValueError):
            catalog.load_limits(dict(GOOD_ENV, **{k: "-1"}))
