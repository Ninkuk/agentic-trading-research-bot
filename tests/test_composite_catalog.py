import pytest

from sources.combiners.composite import catalog

KNOWN_DBS = {
    "fred.db", "cboe_stats.db", "fomc.db", "econ_calendar.db",
    "market_calendar.db", "nyfed.db", "treasury.db", "cftc.db", "eia.db",
    "usda.db", "short_interest.db", "short_volume.db", "ftd.db",
    "reddit.db", "stocks.db", "edgar.db", "portfolio.db",
}
ASSET_CLASSES = {"ags", "rates", "energy", "softs", "metals", "fx",
                 "equity_index"}


def test_signal_ids_unique_and_wellformed():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert len(ids) == len(set(ids))
    for s in catalog.SIGNALS:
        assert s["grain"] in ("market", "asset_class", "ticker")
        assert s["db"] in KNOWN_DBS
        assert s["staleness_budget_days"] >= 0
        assert "src." in s["sql"]          # reads the attached alias
        assert "calendar_now" not in s["sql"]  # one-clock rule


def test_regime_fields_reference_market_signals():
    market_ids = {s["signal_id"] for s in catalog.SIGNALS
                  if s["grain"] == "market"}
    assert set(catalog.REGIME_FIELDS) <= market_ids


def test_crosswalk_classes_are_known():
    assert set(catalog.CROSSWALK) <= ASSET_CLASSES
    assert "fx" not in catalog.CROSSWALK   # direction incoherent; excluded


def test_select_ids():
    ids = [s["signal_id"] for s in catalog.SIGNALS]
    assert [s["signal_id"] for s in catalog.select_ids(None, None, None)] == ids
    only = catalog.select_ids([ids[0]], None, None)
    assert [s["signal_id"] for s in only] == [ids[0]]
    excl = catalog.select_ids(None, [ids[0]], None)
    assert ids[0] not in [s["signal_id"] for s in excl]
    with pytest.raises(ValueError):
        catalog.select_ids(["nope"], None, None)
