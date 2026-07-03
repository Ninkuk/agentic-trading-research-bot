# tests/test_cftc_catalog.py
from cftc_screener.catalog import CATALOG, Market, select_ids

VALID_CLASSES = {"equity_index", "rates", "fx", "metals", "energy", "ags", "softs"}


def test_catalog_codes_are_unique():
    codes = [m.code for m in CATALOG]
    assert len(codes) == len(set(codes))


def test_catalog_entries_have_valid_asset_classes():
    assert CATALOG, "catalog must not be empty"
    for m in CATALOG:
        assert isinstance(m, Market)
        assert m.asset_class in VALID_CLASSES, f"{m.code} bad class {m.asset_class}"


def test_select_ids_defaults_to_full_catalog():
    all_codes = [m.code for m in CATALOG]
    assert select_ids(all_codes, only=None, exclude=None) == all_codes


def test_select_ids_only_subsets_and_preserves_order():
    assert select_ids(["A", "B", "C"], only=["C", "A"], exclude=None) == ["C", "A"]


def test_select_ids_excludes():
    assert select_ids(["A", "B", "C"], only=None, exclude=["B"]) == ["A", "C"]


def test_select_ids_strips_dedupes_and_drops_blanks():
    assert select_ids(["A"], only=["B", " B ", "", "C", "C"], exclude=None) == ["B", "C"]


def test_select_ids_appends_add_after_selection():
    assert select_ids(["A", "B"], only=None, exclude=None, add=["Z", "A"]) == ["A", "B", "Z"]
