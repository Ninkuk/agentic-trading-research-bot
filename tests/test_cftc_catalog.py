# tests/test_cftc_catalog.py
from sources.screeners.cftc_screener.catalog import CATALOG, Market, select_ids

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


# --- family extension ---
from sources.screeners.cftc_screener.catalog import DISAGG_CATALOG, FAMILIES, Family, TFF_CATALOG

_PHYSICAL = {"metals", "energy", "ags", "softs"}
_FINANCIAL = {"equity_index", "rates", "fx"}


def test_families_registry_resolves_three_names():
    assert set(FAMILIES) == {"legacy", "disaggregated", "tff"}
    for fam in FAMILIES.values():
        assert isinstance(fam, Family)
        assert fam.catalog, f"{fam.name} catalog must be non-empty"
        assert fam.dataset_id and fam.fact_table and fam.field_map


def test_family_fact_tables_are_distinct():
    tables = {f.fact_table for f in FAMILIES.values()}
    assert tables == {"cot", "cot_disagg", "cot_tff"}


def test_disagg_catalog_is_physical_commodities_only():
    assert DISAGG_CATALOG
    assert all(m.asset_class in _PHYSICAL for m in DISAGG_CATALOG)


def test_tff_catalog_is_financials_only():
    assert TFF_CATALOG
    assert all(m.asset_class in _FINANCIAL for m in TFF_CATALOG)


def test_family_catalogs_partition_the_legacy_catalog():
    # Disaggregated + TFF together cover exactly the legacy catalog, no overlap.
    disagg = {m.code for m in DISAGG_CATALOG}
    tff = {m.code for m in TFF_CATALOG}
    legacy = {m.code for m in FAMILIES["legacy"].catalog}
    assert disagg.isdisjoint(tff)
    assert disagg | tff == legacy
