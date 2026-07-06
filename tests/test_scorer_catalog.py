from sources.combiners.scorer import catalog


def test_constants_wellformed():
    assert catalog.HORIZONS == (5, 10, 21)
    assert catalog.BENCHMARK == "SPY"
    assert catalog.PRICE_DBS == ("stocks.db", "etfs.db")
    assert catalog.COMPOSITE_DB == "composite.db"
    assert catalog.ENTRY_MAX_AGE_DAYS >= 5
