from cboe_options import catalog


def test_catalog_has_starter_symbols():
    syms = {u.symbol for u in catalog.CATALOG}
    assert {"AAPL", "SPY", "SPX", "VIX"} <= syms


def test_indices_are_flagged():
    by = {u.symbol: u.is_index for u in catalog.CATALOG}
    assert by["SPX"] is True and by["VIX"] is True
    assert by["AAPL"] is False and by["SPY"] is False


def test_index_flag_defaults_false_for_unknown():
    assert catalog.index_flag("SPX") is True
    assert catalog.index_flag("AAPL") is False
    assert catalog.index_flag("ZZZZ") is False


def test_select_symbols_only_exclude_add():
    all_syms = ["AAPL", "MSFT", "NVDA"]
    assert catalog.select_symbols(all_syms, None, None) == ["AAPL", "MSFT", "NVDA"]
    assert catalog.select_symbols(all_syms, ["AAPL", "NVDA"], None) == ["AAPL", "NVDA"]
    assert catalog.select_symbols(all_syms, None, ["MSFT"]) == ["AAPL", "NVDA"]
    assert catalog.select_symbols(all_syms, None, None, ["TSLA"]) == [
        "AAPL", "MSFT", "NVDA", "TSLA"]


def test_select_symbols_dedupes_and_strips():
    assert catalog.select_symbols(["AAPL"], None, None, [" AAPL ", "MSFT"]) == [
        "AAPL", "MSFT"]
