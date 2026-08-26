from sources.screeners.cboe_stats.catalog import CATALOG, enabled_ids, select_ids


def test_catalog_has_pcr_and_vol_indices():
    by_id = {f.feed_id: f for f in CATALOG}
    assert by_id["PCR"].kind == "pcr"
    assert {"VIX", "VIX3M", "VIX9D", "VVIX"} <= set(by_id)
    assert by_id["VIX"].kind == "vix"


def test_enabled_ids_includes_all_feeds():
    # PCR is on by default: it reads the daily market-statistics page's
    # server-rendered payload (the free CSV is discontinued).
    ids = enabled_ids()
    assert {"PCR", "VIX", "VIX3M", "VIX9D", "VVIX"} <= set(ids)


def test_select_ids_default_only_exclude_add():
    ids = [f.feed_id for f in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["VIX", "VIX"], None) == ["VIX"]
    assert "VIX" not in select_ids(ids, None, ["VIX"])
    assert select_ids(ids, ["VIX"], None, add=["RVX", " RVX "]) == ["VIX", "RVX"]


def test_cor3m_is_an_enabled_vix_kind_feed():
    """COR3M (Cboe 3-month implied correlation) ships on the same CDN CSV
    route as VIX and is enabled by default."""
    from sources.screeners.cboe_stats import catalog

    by_id = {f.feed_id: f for f in catalog.CATALOG}
    assert by_id["COR3M"].kind == "vix"
    assert "COR3M" in catalog.enabled_ids()
