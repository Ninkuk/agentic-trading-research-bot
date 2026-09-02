"""Dashboard view coverage — the registry `tests/test_dashboard_coverage.py`
enforces so a view added to any source's db.py cannot stay off the
dashboard silently.

A view counts as surfaced when (a) a dashboard section exporter reads it
(observed at test time through SQLite's authorizer, never hand-listed),
(b) a combiner's fetch/catalog names it (its output reaches the page as a
regime input, a scorecard signal or an advisor number), or (c) it is
listed in `UNSURFACED` with the reason a reader would want. A view in
none of the three fails the test; an `UNSURFACED` entry that a section
now reads also fails, so the allowlist cannot go stale.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sources.combiners.advisor import db as advisor_db
from sources.combiners.backtest import db as backtest_db
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db
from sources.monitors.earnings_calendar import db as earnings_db
from sources.monitors.econ_calendar import db as econ_db
from sources.monitors.fomc_calendar import db as fomc_db
from sources.monitors.market_calendar import db as market_calendar_db
from sources.screeners.cboe_options import db as options_db
from sources.screeners.cboe_stats import db as cboe_stats_db
from sources.screeners.cftc_screener import db as cftc_db
from sources.screeners.edgar_screener import db as edgar_db
from sources.screeners.eia_screener import db as eia_db
from sources.screeners.finra_ats import db as ats_db
from sources.screeners.finra_short_interest import db as short_interest_db
from sources.screeners.finra_short_volume import db as short_volume_db
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.ftd_screener import db as ftd_db
from sources.screeners.nyfed_screener import db as nyfed_db
from sources.screeners.orders import db as orders_db
from sources.screeners.portfolio_screener import db as portfolio_db
from sources.screeners.reddit_screener import db as reddit_db
from sources.screeners.sec_fundamentals import db as sec_fundamentals_db
from sources.screeners.stock_analysis_screener import db as stocks_db
from sources.screeners.treasury_screener import db as treasury_db
from sources.screeners.usda_screener import db as usda_db

# stocks.db/etfs.db grow their metrics columns from each fetch; a schema-only
# build needs the ones the candidates screen selects or its SQL fails.
_STOCKS_COLS = {
    "sector": "TEXT",
    "marketCap": "REAL",
    "dollarVolume": "REAL",
    "roic": "REAL",
    "roic5y": "REAL",
    "fcfYield": "REAL",
    "revenueGrowth3Y": "REAL",
    "revenueGrowth": "REAL",
    "revenueThisYear": "REAL",
    "revenueNextYear": "REAL",
    "netDebtEbitda": "REAL",
    "sharesYoY": "REAL",
    "fScore": "REAL",
    "rsi": "REAL",
    "ch6m": "REAL",
    "high52ch": "REAL",
    "zScore": "REAL",
    "interestCoverage": "REAL",
    "priceDate": "TEXT",
    "isin": "TEXT",
    "isPrimaryListing": "TEXT",
    "netIncome": "REAL",
    "operatingCF": "REAL",
    "assets": "REAL",
    "atr": "REAL",
}

# data/<file> -> the ensure_schema that owns it. The launchd installer names
# the files (several run.py defaults differ: finra_ats.db, cboe_options.db,
# fundamentals.db), so this map, not the defaults, is the source of truth.
DB_SCHEMAS: dict[str, Callable[[Any], None]] = {
    "advisor.db": advisor_db.ensure_schema,
    "ats.db": ats_db.ensure_schema,
    "backtest.db": backtest_db.ensure_schema,
    "cboe_stats.db": cboe_stats_db.ensure_schema,
    "cftc.db": cftc_db.ensure_schema,
    "composite.db": composite_db.ensure_schema,
    "earnings.db": earnings_db.ensure_schema,
    "econ_calendar.db": econ_db.ensure_schema,
    "edgar.db": edgar_db.ensure_schema,
    "eia.db": eia_db.ensure_schema,
    "etfs.db": lambda conn: stocks_db.ensure_schema(conn, _STOCKS_COLS),
    "fomc.db": fomc_db.ensure_schema,
    "fred.db": fred_db.ensure_schema,
    "ftd.db": ftd_db.ensure_schema,
    "market_calendar.db": market_calendar_db.ensure_schema,
    "nyfed.db": nyfed_db.ensure_schema,
    "options.db": options_db.ensure_schema,
    "orders.db": orders_db.ensure_schema,
    "portfolio.db": portfolio_db.ensure_schema,
    "reddit.db": reddit_db.ensure_schema,
    "scorer.db": scorer_db.ensure_schema,
    "sec_fundamentals.db": sec_fundamentals_db.ensure_schema,
    "short_interest.db": short_interest_db.ensure_schema,
    "short_volume.db": short_volume_db.ensure_schema,
    "stocks.db": lambda conn: stocks_db.ensure_schema(conn, _STOCKS_COLS),
    "treasury.db": treasury_db.ensure_schema,
    "usda.db": usda_db.ensure_schema,
}

# (db file, view) -> why it has no card. A view a shown view is built from
# is already covered (the gate observes transitive reads); only views
# nothing on the page touches belong here.
UNSURFACED: dict[tuple[str, str], str] = {
    (
        "market_calendar.db",
        "v_upcoming_closures",
    ): "folds both markets' holidays and early closes into one list; the holidays card queries events by type so kind can name the market",
    (
        "composite.db",
        "v_score_history",
    ): "per-ticker score history; the ticker drill-down chart and the scorecard sparklines read it for headline symbols",
    ("earnings.db", "v_upcoming"): "monitor framework base view; earnings-specific views are shown",
    (
        "earnings.db",
        "v_imminent",
    ): "monitor framework base view; v_imminent_earnings feeds composite",
    (
        "econ_calendar.db",
        "v_imminent",
    ): "monitor framework base view; v_imminent_high_impact feeds composite",
    (
        "econ_calendar.db",
        "v_upcoming_releases",
    ): "the 30-day window behind week-ahead's v_this_week",
    ("fomc.db", "v_upcoming"): "monitor framework base view; v_next_fomc is shown",
    ("fomc.db", "v_imminent"): "monitor framework base view; composite reads the blackout flag",
    ("fomc.db", "v_upcoming_fomc_events"): "the full window behind v_next_fomc",
    ("ftd.db", "v_security_history"): "per-security history grain under v_spikes / v_latest_fails",
    (
        "market_calendar.db",
        "v_upcoming",
    ): "monitor framework base view; closures/opex views are shown",
    ("market_calendar.db", "v_imminent"): "monitor framework base view",
    (
        "sec_fundamentals.db",
        "v_frame_cross_section",
    ): "frame-grain facts; sec-screener/candidates read the pivot",
    ("short_interest.db", "v_latest"): "unfiltered report grain under v_high_days_to_cover",
    ("short_volume.db", "v_latest"): "unfiltered daily grain under v_high_short_ratio",
    ("etfs.db", "v_latest"): "ETF universe; advisor reads ATR from it",
}
