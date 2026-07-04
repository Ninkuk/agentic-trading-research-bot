from eia_screener.catalog import CATALOG, Series, select_ids

_CATS = {"crude", "cushing", "gasoline", "distillate", "production", "imports",
         "natgas", "custom"}


def test_catalog_ids_unique_have_route_and_facet():
    ids = [s.series_id for s in CATALOG]
    assert len(ids) == len(set(ids))
    for s in CATALOG:
        assert s.route and s.facet and s.category in _CATS


def test_catalog_covers_headline_categories():
    cats = {s.category for s in CATALOG}
    assert {"crude", "cushing", "gasoline", "natgas"} <= cats


def test_select_ids_default_only_exclude_add():
    ids = [s.series_id for s in CATALOG]
    assert select_ids(ids, None, None) == ids
    first = ids[0]
    assert select_ids(ids, [first, first], None) == [first]
    assert first not in select_ids(ids, None, [first])
    assert select_ids(ids, [first], None, add=["X", " X "]) == [first, "X"]
