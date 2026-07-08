import sqlite3

import pytest

from sources.combiners.composite import catalog, fetch

KNOWN_DBS = {
    "fred.db",
    "cboe_stats.db",
    "fomc.db",
    "econ_calendar.db",
    "market_calendar.db",
    "nyfed.db",
    "treasury.db",
    "cftc.db",
    "eia.db",
    "usda.db",
    "short_interest.db",
    "short_volume.db",
    "ftd.db",
    "reddit.db",
    "stocks.db",
    "edgar.db",
    "portfolio.db",
}
ASSET_CLASSES = {"ags", "rates", "energy", "softs", "metals", "fx", "equity_index"}


def test_signal_ids_unique_and_wellformed():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert len(ids) == len(set(ids))
    for s in catalog.SIGNALS:
        assert s["grain"] in ("market", "asset_class", "ticker")
        assert s["db"] in KNOWN_DBS
        assert s["staleness_budget_days"] >= 0
        assert "src." in s["sql"]  # reads the attached alias
        assert "calendar_now" not in s["sql"]  # one-clock rule


def test_regime_fields_reference_market_signals():
    market_ids = {s["signal_id"] for s in catalog.SIGNALS if s["grain"] == "market"}
    assert set(catalog.REGIME_FIELDS) <= market_ids


def test_crosswalk_classes_are_known():
    assert set(catalog.CROSSWALK) <= ASSET_CLASSES
    assert "fx" not in catalog.CROSSWALK  # direction incoherent; excluded


def test_select_ids():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert [s["signal_id"] for s in catalog.select_ids(None, None, None)] == ids
    only = catalog.select_ids([ids[0]], None, None)
    assert [s["signal_id"] for s in only] == [ids[0]]
    excl = catalog.select_ids(None, [ids[0]], None)
    assert ids[0] not in [s["signal_id"] for s in excl]
    with pytest.raises(ValueError):
        catalog.select_ids(["nope"], None, None)


# db filename -> the source's own db module, so ensure_schema builds the
# real (empty) schema each catalog SQL runs against. Any rename of a view,
# table, or column referenced by a catalog SQL fails this test loudly.
DB_MODULES = {
    "fred.db": "sources.screeners.fred_screener.db",
    "cboe_stats.db": "sources.screeners.cboe_stats.db",
    "fomc.db": "sources.monitors.fomc_calendar.db",
    "econ_calendar.db": "sources.monitors.econ_calendar.db",
    "market_calendar.db": "sources.monitors.market_calendar.db",
    "nyfed.db": "sources.screeners.nyfed_screener.db",
    "treasury.db": "sources.screeners.treasury_screener.db",
    "cftc.db": "sources.screeners.cftc_screener.db",
    "eia.db": "sources.screeners.eia_screener.db",
    "usda.db": "sources.screeners.usda_screener.db",
    "short_interest.db": "sources.screeners.finra_short_interest.db",
    "short_volume.db": "sources.screeners.finra_short_volume.db",
    "ftd.db": "sources.screeners.ftd_screener.db",
    "reddit.db": "sources.screeners.reddit_screener.db",
    "stocks.db": "sources.screeners.stock_analysis_screener.db",
    "edgar.db": "sources.screeners.edgar_screener.db",
    "portfolio.db": "sources.screeners.portfolio_screener.db",
}

# stocks.db's metrics table only gets its data-point columns via
# ensure_schema(conn, columns) — supply the ones stocks_rsi's SQL references.
_STOCKS_COLUMNS = {"rsi": "REAL", "dollarVolume": "REAL", "priceDate": "TEXT"}


def _build_source_db(db_file: str, path: str) -> None:
    import importlib

    mod = importlib.import_module(DB_MODULES[db_file])
    conn = mod.connect(path)
    if db_file == "stocks.db":
        mod.ensure_schema(conn, _STOCKS_COLUMNS)
    else:
        mod.ensure_schema(conn)
    conn.close()


@pytest.mark.parametrize("signal", catalog.SIGNALS, ids=lambda s: s["signal_id"])
def test_extraction_sql_executes_against_source_schema(signal, tmp_path):
    """Every catalog SQL must run against its source's real (empty) schema —
    fails loudly here if a source view/column is renamed."""
    assert signal["db"] in DB_MODULES, f"no DB_MODULES entry for {signal['db']}"
    path = str(tmp_path / signal["db"])
    _build_source_db(signal["db"], path)

    conn = sqlite3.connect(":memory:", uri=True)
    try:
        fetch.attach_ro(conn, path)
        rows = fetch.extract(conn, signal, today="2026-07-06")
    finally:
        conn.close()

    assert isinstance(rows, list)


def test_fred_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        FRED_CURVE_SCORE,
        FRED_HY_SPREAD_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert FRED_CURVE_SCORE in by_id["fred_curve"]["sql"]
    assert FRED_HY_SPREAD_SCORE in by_id["fred_hy_spread"]["sql"]


def test_cboe_score_cases_are_hoisted_constants():
    # Hoisted so the backtest combiner replays the IDENTICAL flag expression;
    # rendered composite SQL must be unchanged (constant interpolated back in).
    from sources.combiners.composite.catalog import (
        CBOE_VIX_BACKWARDATION_SCORE,
        CBOE_VIX_SCORE,
        SIGNALS,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert CBOE_VIX_SCORE in by_id["cboe_vix"]["sql"]
    assert CBOE_VIX_BACKWARDATION_SCORE in by_id["cboe_vix_backwardation"]["sql"]
    # the CASEs still reference their source columns verbatim
    assert "close >= 30" in CBOE_VIX_SCORE
    assert "close > vix3m" in CBOE_VIX_BACKWARDATION_SCORE


def test_liquidity_score_cases_are_hoisted_constants():
    from sources.combiners.composite.catalog import (
        NYFED_RRP_SCORE,
        SIGNALS,
        TSY_TGA_SCORE,
    )

    by_id = {s["signal_id"]: s for s in SIGNALS}
    assert NYFED_RRP_SCORE in by_id["nyfed_rrp"]["sql"]
    assert TSY_TGA_SCORE in by_id["tsy_tga"]["sql"]
    assert "change_vs_prior" in NYFED_RRP_SCORE
    assert "wow_change" in TSY_TGA_SCORE
