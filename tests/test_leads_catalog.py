from pipeline.leads import catalog
from sources.screeners.cftc_screener.catalog import CATALOG as CFTC_CATALOG


def test_every_mapping_code_exists_in_cftc_catalog():
    cftc_by_code = {m.code: m for m in CFTC_CATALOG}
    for m in catalog.ETF_MAP:
        assert m.code in cftc_by_code, m
        # asset_class travels with the lead (spec D2/D3): must match the source
        assert m.asset_class == cftc_by_code[m.code].asset_class, m


def test_mapping_asset_classes_partition_into_families():
    for m in catalog.ETF_MAP:
        assert (m.asset_class in catalog.PHYSICAL_CLASSES) != (
            m.asset_class in catalog.FINANCIAL_CLASSES), m


def test_etf_by_code_indexes_the_map():
    assert catalog.ETF_BY_CODE["088691"].etf == "GLD"
    assert len(catalog.ETF_BY_CODE) == len(catalog.ETF_MAP)


def test_no_duplicate_codes_or_etfs():
    codes = [m.code for m in catalog.ETF_MAP]
    etfs = [m.etf for m in catalog.ETF_MAP]
    assert len(set(codes)) == len(codes)
    assert len(set(etfs)) == len(etfs)


def test_vocab_pins_the_tag_vocabulary():
    assert "mean_reversion" in catalog.VOCAB["signal_type"]
    assert "quality" in catalog.VOCAB["signal_type"]
    assert catalog.VOCAB["implementation"] == frozenset(
        {"cross_sectional", "time_series"})
    assert catalog.VOCAB["horizon_band"] == frozenset({"weeks", "months"})


def test_thresholds_match_extreme_convention():
    assert catalog.COT_LONG_THRESHOLD == 90.0
    assert catalog.COT_SHORT_THRESHOLD == 10.0
    assert catalog.RISK_OFF_SCALAR == 0.5
