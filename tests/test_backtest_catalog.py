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


def test_class_benchmarks_are_exactly_the_scorer_crosswalk_proxies():
    """CLASS_BENCHMARKS must stay in lockstep with the scorer's crosswalk
    proxies — the tickers whose CROSSWALK_BENCHMARK value is None (they
    self-benchmark). SPY is excluded: it is the market-grain spine's own proxy
    and the backtest grades market signals against BENCHMARK_SERIES (SP500)."""
    from sources.combiners.scorer.catalog import CROSSWALK_BENCHMARK

    proxies = {s for s, b in CROSSWALK_BENCHMARK.items() if b is None} - {"SPY"}
    assert {b["symbol"] for b in catalog.CLASS_BENCHMARKS} == proxies
    assert all(b["db"] == catalog.SCORER_DB for b in catalog.CLASS_BENCHMARKS)


def test_class_benchmarks_are_backfillable():
    """Every class benchmark must be in the pricehistory backfill roster, or its
    spine stays 3 days deep and its signals grade nothing."""
    from sources.combiners.scorer.catalog import BACKFILL_SYMBOLS

    assert {b["symbol"] for b in catalog.CLASS_BENCHMARKS} <= set(BACKFILL_SYMBOLS)


def test_publication_lags_are_pinned_to_the_real_release_schedules():
    """The lag VALUES are the whole fix; a test that passes them explicitly
    proves nothing about the catalog. Pin them, with the schedule that justifies
    each. Over-lagged by a day on purpose: a holiday-shifted release must never
    leak. Sources: EIA WPSR (Wed 10:30 ET, +1 on holiday weeks), EIA WNGSR
    (Thu 10:30 ET), Treasury DTS (next business day)."""
    lags = {s["signal_id"]: s["publication_lag_days"] for s in catalog.MARKET_OBS_SIGNALS}
    assert lags == {
        "cboe_vix": 0,  # exchange close, same session
        "cboe_vix_backwardation": 0,  # exchange close, same session
        "cboe_equity_pcr": 0,  # daily stats for that session
        "nyfed_rrp": 0,  # operation results ~1:15pm ET on operation_date
        "tsy_tga": 1,  # DTS publishes the next business day
        "eia_crude_stocks": 6,  # week ends Fri -> released Wed (+1 holiday)
        "eia_natgas_storage": 7,  # week ends Fri -> released Thu (+1 holiday)
    }


def test_weekly_eia_lags_clear_the_period_end_by_at_least_five_days():
    """A weekly report covering a Friday cannot be public the same day. Any lag
    below 5 reintroduces look-ahead regardless of the exact release weekday."""
    lags = {s["signal_id"]: s["publication_lag_days"] for s in catalog.MARKET_OBS_SIGNALS}
    for sig in ("eia_crude_stocks", "eia_natgas_storage"):
        assert lags[sig] >= 5, f"{sig} would be readable before it was published"
