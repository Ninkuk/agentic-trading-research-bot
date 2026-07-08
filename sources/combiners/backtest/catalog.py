"""Replay roster for the point-in-time backtest: which composite signals
are replayed, with the score CASE imported from composite (flags cannot
drift) and horizons imported from the scorer (grading windows match)."""

from typing import Any

from sources.combiners.composite.catalog import FRED_CURVE_SCORE, FRED_HY_SPREAD_SCORE
from sources.combiners.scorer.catalog import HORIZONS

FRED_DB = "fred.db"
BENCHMARK_SERIES = "SP500"  # grading spine; unrevised index closes

REPLAY_SIGNALS: list[dict[str, Any]] = [
    {"signal_id": "fred_curve", "series_id": "T10Y2Y", "score_case": FRED_CURVE_SCORE},
    {
        "signal_id": "fred_hy_spread",
        "series_id": "BAMLH0A0HYM2",
        "score_case": FRED_HY_SPREAD_SCORE,
    },
]

__all__ = ["BENCHMARK_SERIES", "FRED_DB", "HORIZONS", "REPLAY_SIGNALS"]
