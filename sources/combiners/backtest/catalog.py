"""Replay roster for the point-in-time backtest: which composite signals
are replayed, with the score CASE imported from composite (flags cannot
drift) and horizons imported from the scorer (grading windows match)."""

from typing import Any

from sources.combiners.composite.catalog import (
    CBOE_EQUITY_PCR_SCORE,
    CBOE_VIX_BACKWARDATION_SCORE,
    CBOE_VIX_SCORE,
    EIA_WEEKLY_CHANGE_SCORE,
    FRED_CURVE_SCORE,
    FRED_HY_SPREAD_SCORE,
    NYFED_RRP_SCORE,
    TSY_TGA_SCORE,
)
from sources.combiners.scorer.catalog import HORIZONS

FRED_DB = "fred.db"
CBOE_DB = "cboe_stats.db"
NYFED_DB = "nyfed.db"
TREASURY_DB = "treasury.db"
EIA_DB = "eia.db"
SCORER_DB = "scorer.db"
BENCHMARK_SERIES = "SP500"  # default (market-grain) spine; unrevised index closes

# Asset-class proxy benchmarks copied from scorer.db's permanent price ledger
# (the only growing close history for these tickers). Deep history accrues over
# time -- until then an asset-class replay grades few/no rows, which is correct
# (degrades gracefully), not an error.
CLASS_BENCHMARKS: list[dict[str, Any]] = [
    {"symbol": "XLE", "db": SCORER_DB},  # energy proxy
]

# FRED regime signals: ALFRED-vintage replay (revision-aware; realtime_start
# gives the exact as-of read).
REPLAY_SIGNALS: list[dict[str, Any]] = [
    {"signal_id": "fred_curve", "series_id": "T10Y2Y", "score_case": FRED_CURVE_SCORE},
    {
        "signal_id": "fred_hy_spread",
        "series_id": "BAMLH0A0HYM2",
        "score_case": FRED_HY_SPREAD_SCORE,
    },
]

# Non-vintage market-grain signals: unrevised, same-day-published exchange
# series with no ALFRED vintage trail. Their point-in-time read is simply
# "latest observation on or before D" (the with-caveat class from the spike —
# a repost of an old date would overwrite silently, accepted). Each copies its
# raw score-input columns into market_obs.val1/val2, and the replay aliases
# those back to the column names the imported composite CASE expects, so the
# SAME flag is replayed. All graded against the shared SP500 spine.
#   harvest_sql : SELECT (obs_date, val1, val2) from the src DB (val2 NULL ok)
#   aliases     : CASE-column-name -> stored column ('val1' | 'val2')
#   raw_expr    : the raw_value shown, in terms of the aliased names
MARKET_OBS_SIGNALS: list[dict[str, Any]] = [
    {
        "signal_id": "cboe_vix",
        "db": CBOE_DB,
        "harvest_sql": "SELECT date, close, NULL FROM src.vix_daily WHERE close IS NOT NULL",
        "aliases": {"close": "val1"},
        "raw_expr": "close",
        "score_case": CBOE_VIX_SCORE,
    },
    {
        "signal_id": "cboe_vix_backwardation",
        "db": CBOE_DB,
        "harvest_sql": (
            "SELECT date, close, vix3m FROM src.vix_daily"
            " WHERE close IS NOT NULL AND vix3m IS NOT NULL"
        ),
        "aliases": {"close": "val1", "vix3m": "val2"},
        "raw_expr": "close - vix3m",
        "score_case": CBOE_VIX_BACKWARDATION_SCORE,
    },
    {
        # Liquidity flow: the source view's change_vs_prior is stable at the
        # operation's own date (diff to the immediately-prior op, both known
        # then), so harvesting it keyed by operation_date is PIT-honest. NY
        # Fed publishes same-day -> minimal lag caveat.
        "signal_id": "nyfed_rrp",
        "db": NYFED_DB,
        "harvest_sql": (
            "SELECT operation_date, change_vs_prior, NULL FROM src.v_rrp_trend"
            " WHERE change_vs_prior IS NOT NULL"
        ),
        "aliases": {"change_vs_prior": "val1"},
        "raw_expr": "change_vs_prior",
        "score_case": NYFED_RRP_SCORE,
    },
    {
        # Same shape as nyfed_rrp: wow_change is stable at its record_date.
        # DTS publishes next business day -> ~1-day lag caveat (with-caveat
        # class in the spike); the scorer's next-day entry buffers the return
        # side already.
        "signal_id": "tsy_tga",
        "db": TREASURY_DB,
        "harvest_sql": (
            "SELECT record_date, wow_change, NULL FROM src.v_tga_trend WHERE wow_change IS NOT NULL"
        ),
        "aliases": {"wow_change": "val1"},
        "raw_expr": "wow_change",
        "score_case": TSY_TGA_SCORE,
    },
    {
        # Windowed, not latest-scalar: the score reads a trailing-252
        # percentile that must be recomputed as-of each date (an old
        # percentile isn't stable when the window slides). flag_mode="pctile"
        # routes it through the dedicated v_pit_pcr view; only the raw
        # equity_pcr is copied (val1), and the CASE reuses `pctile` verbatim.
        "signal_id": "cboe_equity_pcr",
        "db": CBOE_DB,
        "flag_mode": "pctile",
        "harvest_sql": (
            "SELECT date, equity_pcr, NULL FROM src.pcr_daily WHERE equity_pcr IS NOT NULL"
        ),
        "score_case": CBOE_EQUITY_PCR_SCORE,
    },
    # ---- asset-class grain (graded vs a sector proxy, not SP500) ----
    # change_pct history is computed from eia_obs week-over-week (the source's
    # v_weekly_change is latest-only). change_pct is stable at its report
    # period, so it's a latest-scalar as-of read; graded vs XLE (energy).
    {
        "signal_id": "eia_crude_stocks",
        "db": EIA_DB,
        "benchmark": "XLE",
        "harvest_sql": (
            "SELECT o.period,"
            " 100.0 * (o.value - p.value) / p.value AS change_pct, NULL"
            " FROM src.eia_obs o"
            " JOIN src.eia_obs p ON p.series_id = o.series_id"
            " AND p.period = (SELECT MAX(p2.period) FROM src.eia_obs p2"
            "                 WHERE p2.series_id = o.series_id AND p2.period < o.period)"
            " WHERE o.series_id = 'WCESTUS1'"
            " AND o.value IS NOT NULL AND p.value IS NOT NULL AND p.value != 0"
        ),
        "aliases": {"change_pct": "val1"},
        "raw_expr": "change_pct",
        "score_case": EIA_WEEKLY_CHANGE_SCORE,
    },
    {
        "signal_id": "eia_natgas_storage",
        "db": EIA_DB,
        "benchmark": "XLE",
        "harvest_sql": (
            "SELECT o.period,"
            " 100.0 * (o.value - p.value) / p.value AS change_pct, NULL"
            " FROM src.eia_obs o"
            " JOIN src.eia_obs p ON p.series_id = o.series_id"
            " AND p.period = (SELECT MAX(p2.period) FROM src.eia_obs p2"
            "                 WHERE p2.series_id = o.series_id AND p2.period < o.period)"
            " WHERE o.series_id = 'NW2_EPG0_SWO_R48_BCF'"
            " AND o.value IS NOT NULL AND p.value IS NOT NULL AND p.value != 0"
        ),
        "aliases": {"change_pct": "val1"},
        "raw_expr": "change_pct",
        "score_case": EIA_WEEKLY_CHANGE_SCORE,
    },
]

__all__ = [
    "BENCHMARK_SERIES",
    "CBOE_DB",
    "CLASS_BENCHMARKS",
    "EIA_DB",
    "FRED_DB",
    "HORIZONS",
    "MARKET_OBS_SIGNALS",
    "NYFED_DB",
    "REPLAY_SIGNALS",
    "SCORER_DB",
    "TREASURY_DB",
]
