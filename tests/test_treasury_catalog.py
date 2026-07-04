from treasury_screener.catalog import CATALOG, Dataset, select_ids

_FREQ = {"daily", "monthly", "event"}


def test_catalog_ids_unique_and_known():
    ids = [d.dataset_id for d in CATALOG]
    assert len(ids) == len(set(ids))
    assert {"dts_cash", "debt_penny", "avg_rates", "upcoming_auctions",
            "auction_results", "yield_curve"} <= set(ids)


def test_catalog_fields_valid():
    for d in CATALOG:
        assert d.frequency in _FREQ
        assert d.endpoint and d.table and d.date_field


def test_yield_curve_uses_xml_sentinel():
    yc = next(d for d in CATALOG if d.dataset_id == "yield_curve")
    assert yc.endpoint == "xml:yield_curve"


def test_select_ids_default_only_exclude_add_dedupe():
    ids = [d.dataset_id for d in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["dts_cash", "dts_cash"], None) == ["dts_cash"]
    assert "dts_cash" not in select_ids(ids, None, ["dts_cash"])
    assert select_ids(ids, ["dts_cash"], None, add=["x", " x "]) == ["dts_cash", "x"]
