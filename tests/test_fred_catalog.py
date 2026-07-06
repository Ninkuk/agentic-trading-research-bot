from sources.screeners.fred_screener.catalog import CATALOG, Series, select_ids

VALID_THEMES = {"growth", "inflation", "rates", "labor", "credit", "housing", "sentiment"}


def test_catalog_ids_are_unique():
    ids = [s.series_id for s in CATALOG]
    assert len(ids) == len(set(ids))


def test_catalog_entries_have_valid_themes():
    assert CATALOG, "catalog must not be empty"
    for s in CATALOG:
        assert isinstance(s, Series)
        assert s.theme in VALID_THEMES, f"{s.series_id} has bad theme {s.theme}"


def test_select_ids_defaults_to_full_catalog():
    all_ids = [s.series_id for s in CATALOG]
    assert select_ids(all_ids, only=None, exclude=None) == all_ids


def test_select_ids_only_subsets_and_preserves_order():
    out = select_ids(["A", "B", "C"], only=["C", "A"], exclude=None)
    assert out == ["C", "A"]


def test_select_ids_excludes():
    out = select_ids(["A", "B", "C"], only=None, exclude=["B"])
    assert out == ["A", "C"]


def test_select_ids_strips_dedupes_and_drops_blanks():
    out = select_ids(["A"], only=["B", " B ", "", "C", "C"], exclude=None)
    assert out == ["B", "C"]


def test_select_ids_appends_add_after_selection():
    out = select_ids(["A", "B"], only=None, exclude=None, add=["Z", "A"])
    # add is appended; duplicates against the existing selection are dropped
    assert out == ["A", "B", "Z"]
