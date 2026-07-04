import dataclasses

from pipeline.promote import catalog


def test_default_config_values_pin_the_spec():
    c = catalog.DEFAULT_CONFIG
    assert (c.price_floor, c.dollar_volume_floor) == (5.0, 10_000_000.0)
    assert c.strong_extreme == 0.95
    assert (c.sector_cap, c.max_positions) == (2, 10)
    assert (c.risk_fraction, c.atr_mult, c.participation_cap) == (0.01, 2.0, 0.01)
    assert c.allow_short is False


def test_config_is_frozen():
    import pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        catalog.DEFAULT_CONFIG.price_floor = 1.0


def test_config_hash_is_stable_and_sensitive():
    h1 = catalog.config_hash(catalog.DEFAULT_CONFIG)
    h2 = catalog.config_hash(catalog.GateConfig())
    h3 = catalog.config_hash(dataclasses.replace(catalog.DEFAULT_CONFIG,
                                                 allow_short=True))
    assert h1 == h2 and len(h1) == 64
    assert h3 != h1


def test_required_points_and_horizon_order():
    assert "nextEarningsDate" in catalog.REQUIRED_STOCK_POINTS
    assert "sector" not in catalog.REQUIRED_ETF_POINTS
    assert catalog.HORIZON_ORDER["months"] > catalog.HORIZON_ORDER["weeks"]
