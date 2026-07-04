from sources.screeners.sec_fundamentals.catalog import CATALOG, Concept, select_ids

_KINDS = {"instant", "duration"}
_GROUPS = {"income", "balance", "cashflow", "shares", "per_share"}
_UNIT_BY_GROUP = {"income": "USD", "balance": "USD", "cashflow": "USD",
                  "shares": "shares", "per_share": "USD/shares"}


def test_catalog_tags_unique():
    tags = [c.tag for c in CATALOG]
    assert len(tags) == len(set(tags))


def test_catalog_fields_valid_and_unit_matches_group():
    for c in CATALOG:
        assert c.kind in _KINDS
        assert c.group in _GROUPS
        assert c.taxonomy in {"us-gaap", "ifrs-full", "dei", "srt"}
        assert c.unit == _UNIT_BY_GROUP[c.group]


def test_catalog_has_headline_concepts():
    tags = {c.tag for c in CATALOG}
    assert {"Revenues", "NetIncomeLoss", "Assets", "StockholdersEquity",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"} <= tags


def test_balance_tags_are_instant_income_are_duration():
    by_tag = {c.tag: c for c in CATALOG}
    assert by_tag["Assets"].kind == "instant"
    assert by_tag["NetIncomeLoss"].kind == "duration"
    assert by_tag["CommonStockSharesOutstanding"].kind == "instant"


def test_select_ids_defaults_to_full_catalog():
    tags = [c.tag for c in CATALOG]
    assert select_ids(tags, None, None) == tags


def test_select_ids_only_exclude_add_dedupe_and_strip():
    tags = [c.tag for c in CATALOG]
    assert select_ids(tags, ["Assets", "Assets"], None) == ["Assets"]
    assert "Assets" not in select_ids(tags, None, ["Assets"])
    assert select_ids(tags, ["Assets"], None, add=["Foo", " Foo "]) == ["Assets", "Foo"]
