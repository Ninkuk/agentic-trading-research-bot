from cboe_stats.catalog import CATALOG, Feed, select_ids


def test_catalog_has_pcr_and_vol_indices():
    by_id = {f.feed_id: f for f in CATALOG}
    assert by_id["PCR"].kind == "pcr"
    assert {"VIX", "VIX3M", "VIX9D", "VVIX"} <= set(by_id)
    assert by_id["VIX"].kind == "vix"


def test_select_ids_default_only_exclude_add():
    ids = [f.feed_id for f in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["VIX", "VIX"], None) == ["VIX"]
    assert "VIX" not in select_ids(ids, None, ["VIX"])
    assert select_ids(ids, ["VIX"], None, add=["RVX", " RVX "]) == ["VIX", "RVX"]
