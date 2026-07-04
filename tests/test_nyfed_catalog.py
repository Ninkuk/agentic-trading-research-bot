from sources.screeners.nyfed_screener.catalog import CATALOG, Domain, enabled_ids, select_ids


def test_catalog_ids_unique_and_v1_present():
    ids = [d.domain_id for d in CATALOG]
    assert len(ids) == len(set(ids))
    assert {"reference_rates", "rrp", "repo", "soma"} <= set(ids)


def test_primary_dealer_defined_but_disabled_by_default():
    assert "primary_dealer" in {d.domain_id for d in CATALOG}
    assert "primary_dealer" not in enabled_ids()


def test_select_ids_default_only_exclude_add():
    e = enabled_ids()
    assert select_ids(e, None, None) == e
    assert select_ids(e, ["repo", "repo"], None) == ["repo"]
    assert "repo" not in select_ids(e, None, ["repo"])
    assert select_ids(e, ["soma"], None, add=["primary_dealer"]) == \
        ["soma", "primary_dealer"]
