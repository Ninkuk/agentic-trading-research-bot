from pipeline.trials import catalog


def test_required_data_points_cover_scoring_inputs():
    assert catalog.REQUIRED_DATA_POINTS == ("price", "low", "averageVolume")


def test_horizon_bands_match_leads_vocabulary():
    from pipeline.leads.catalog import VOCAB
    assert set(catalog.HORIZON_TRADING_DAYS) == VOCAB["horizon_band"]
    assert catalog.HORIZON_TRADING_DAYS == {"weeks": 20, "months": 60}


def test_defaults():
    assert catalog.DEFAULT_ENTRY_LAG == 1
    assert catalog.DEFAULT_FAMILY == "default"
    assert catalog.TRANSACTION_HAIRCUT == 0.0
