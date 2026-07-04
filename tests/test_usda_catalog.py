from usda_screener.catalog import CATALOG, Series, select_ids


def test_catalog_ids_unique_and_have_query():
    ids = [s.id for s in CATALOG]
    assert len(ids) == len(set(ids))
    for s in CATALOG:
        assert isinstance(s.query, dict) and s.query
        assert ":" in s.id


def test_catalog_covers_corn_soy_wheat_balance():
    ids = {s.id for s in CATALOG}
    assert {"CORN:ENDING_STOCKS", "CORN:TOTAL_USE", "SOYBEANS:ENDING_STOCKS",
            "WHEAT:ENDING_STOCKS"} <= ids


def test_select_ids_default_only_exclude_add():
    ids = [s.id for s in CATALOG]
    assert select_ids(ids, None, None) == ids
    assert select_ids(ids, ["CORN:ENDING_STOCKS", "CORN:ENDING_STOCKS"], None) \
        == ["CORN:ENDING_STOCKS"]
    assert "CORN:ENDING_STOCKS" not in select_ids(ids, None, ["CORN:ENDING_STOCKS"])
    assert select_ids(ids, ["CORN:TOTAL_USE"], None,
                      add=["WHEAT:TOTAL_USE", " WHEAT:TOTAL_USE "]) \
        == ["CORN:TOTAL_USE", "WHEAT:TOTAL_USE"]
