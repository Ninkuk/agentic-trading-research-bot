from sources.combiners.composite import catalog as composite_catalog
from sources.combiners.scorer import catalog


def test_constants_wellformed():
    assert catalog.HORIZONS == (5, 10, 21)
    assert catalog.BENCHMARK == "SPY"
    assert catalog.PRICE_DBS == ("stocks.db", "etfs.db")
    assert catalog.COMPOSITE_DB == "composite.db"
    assert catalog.ENTRY_MAX_AGE_DAYS >= 5


def test_crosswalk_benchmark_covers_composite_crosswalk():
    fanned = {t for ts in composite_catalog.CROSSWALK.values() for t in ts}
    # exact key set: drift in either combiner fails here
    assert set(catalog.CROSSWALK_BENCHMARK) == fanned


def test_crosswalk_benchmarks_are_unbenchmarked_class_proxies():
    for ticker, bench in catalog.CROSSWALK_BENCHMARK.items():
        if bench is None:
            continue  # class proxy: explicitly unbenchmarked
        # every benchmark is itself a crosswalk ticker mapping to None
        assert catalog.CROSSWALK_BENCHMARK.get(bench, "missing") is None, (
            f"{ticker} -> {bench}: benchmark must be a class proxy"
        )
