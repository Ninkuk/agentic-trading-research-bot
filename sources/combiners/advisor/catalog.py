"""Advisor configuration. The advisor joins the composite scorecard against
real holdings; decision support only — it never places or sizes orders, and
it never writes back into anything it reads."""

from sources.combiners.composite.catalog import CROSSWALK

# Fraction of account equity a single position may put at risk per one-ATR
# adverse day (user-chosen default, 2026-07-07). Caps invert this:
# cap_shares = floor(max(0, RISK_BUDGET*equity - existing_group_heat) / ATR).
RISK_BUDGET = 0.01

# priceDate older than this many days vs the run's :today -> atr_stale = 1
# (5 covers a weekend plus a holiday).
ATR_MAX_AGE_DAYS = 5

COMPOSITE_DB = "composite.db"
PORTFOLIO_DB = "portfolio.db"
SCORER_DB = "scorer.db"
PRICE_DBS = ("stocks.db", "etfs.db")  # stocks first: it wins symbol collisions

# symbol -> crosswalk group, derived from composite's CROSSWALK at import
# time (a catalog test pins consistency). First group wins: DBA sits under
# both ags and softs, and grouping it with CORN/SOYB/WEAT (ags) keeps one
# bet per underlying exposure. Ungrouped symbols resolve to None downstream
# and count as their own single-member bet.
TICKER_GROUP: dict[str, str] = {}
for _group, _symbols in CROSSWALK.items():
    for _symbol in _symbols:
        TICKER_GROUP.setdefault(_symbol, _group)
