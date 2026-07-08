from sources.combiners.backtest import catalog
from sources.combiners.composite.catalog import (
    FRED_CURVE_SCORE,
    FRED_HY_SPREAD_SCORE,
    SIGNALS,
)
from sources.combiners.scorer.catalog import HORIZONS


def test_replay_signals_reference_composite_case_constants():
    by_id = {s["signal_id"]: s for s in catalog.REPLAY_SIGNALS}
    assert by_id["fred_curve"]["score_case"] is FRED_CURVE_SCORE
    assert by_id["fred_hy_spread"]["score_case"] is FRED_HY_SPREAD_SCORE


def test_replay_signal_ids_exist_in_composite():
    composite_ids = {s["signal_id"] for s in SIGNALS}
    assert {s["signal_id"] for s in catalog.REPLAY_SIGNALS} <= composite_ids


def test_replay_series_ids_match_composite_sql():
    by_id = {s["signal_id"]: s for s in SIGNALS}
    for s in catalog.REPLAY_SIGNALS:
        assert f"series_id = '{s['series_id']}'" in by_id[s["signal_id"]]["sql"]


def test_horizons_come_from_scorer():
    assert catalog.HORIZONS is HORIZONS


def test_benchmark_constants():
    assert catalog.BENCHMARK_SERIES == "SP500"
    assert catalog.FRED_DB == "fred.db"
