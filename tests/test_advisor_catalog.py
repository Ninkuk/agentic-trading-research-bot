from sources.combiners.advisor import catalog
from sources.combiners.composite.catalog import CROSSWALK


def test_risk_budget_default():
    # 1% of equity per position per 1-ATR adverse day (user-set 2026-07-07).
    assert catalog.RISK_BUDGET == 0.01


def test_ticker_group_covers_every_crosswalk_ticker():
    for _group, syms in CROSSWALK.items():  # _group: ruff B007 (unused)
        for sym in syms:
            assert catalog.TICKER_GROUP[sym] in CROSSWALK


def test_ticker_group_first_group_wins():
    # DBA appears under both ags and softs; first (ags) wins so DBA shares
    # a bet with CORN/SOYB/WEAT rather than being its own group.
    assert catalog.TICKER_GROUP["DBA"] == "ags"


def test_price_db_order_stocks_first():
    # stocks.db is attached first and wins symbol collisions.
    assert catalog.PRICE_DBS == ("stocks.db", "etfs.db")
