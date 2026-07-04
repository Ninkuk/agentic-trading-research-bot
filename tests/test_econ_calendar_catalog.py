from econ_calendar.catalog import CATALOG, Release, select_ids

_VALID_IMPACT = {"high", "med"}
_VALID_CATEGORY = {"inflation", "labor", "growth", "consumer"}


def test_catalog_release_ids_unique():
    ids = [r.release_id for r in CATALOG]
    assert len(ids) == len(set(ids))


def test_catalog_fields_valid_and_every_release_has_a_time():
    for r in CATALOG:
        assert r.impact in _VALID_IMPACT
        assert r.category in _VALID_CATEGORY
        assert r.release_time and ":" in r.release_time


def test_catalog_has_the_high_impact_core():
    types = {r.event_type for r in CATALOG}
    assert {"cpi_release", "employment_situation", "ppi_release",
            "gdp_release"} <= types


def test_select_ids_defaults_to_full_catalog():
    assert select_ids() == [r.release_id for r in CATALOG]


def test_select_ids_only_keeps_order():
    assert select_ids(only=["10", "46"]) == [10, 46]


def test_select_ids_exclude_removes():
    got = select_ids(exclude=["10"])
    assert 10 not in got and 46 in got


def test_select_ids_strips_and_dedupes():
    assert select_ids(only=[" 10 ", "10", "46"]) == [10, 46]
