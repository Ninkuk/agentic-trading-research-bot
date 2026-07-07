import sys

from sources.combiners.composite.run import main as composite_main
from sources.combiners.scorer.journal import main as journal_main
from sources.combiners.scorer.run import main as scorer_main
from sources.monitors.earnings_calendar.run import main as earnings_main
from sources.monitors.econ_calendar.run import main as econ_calendar_main
from sources.monitors.fomc_calendar.run import main as fomc_main
from sources.monitors.market_calendar.run import main as market_calendar_main
from sources.screeners.cboe_options.run import main as options_main
from sources.screeners.cboe_stats.run import main as cboe_stats_main
from sources.screeners.cftc_screener.run import main as cftc_main
from sources.screeners.edgar_screener.run import main as edgar_main
from sources.screeners.eia_screener.run import main as eia_main
from sources.screeners.finra_ats.run import main as ats_main
from sources.screeners.finra_short_interest.run import main as short_interest_main
from sources.screeners.finra_short_volume.run import main as short_volume_main
from sources.screeners.fred_screener.run import main as fred_main
from sources.screeners.ftd_screener.run import main as ftd_main
from sources.screeners.nyfed_screener.run import main as nyfed_main
from sources.screeners.portfolio_screener.run import main as portfolio_main
from sources.screeners.reddit_screener.run import main as reddit_main
from sources.screeners.sec_fundamentals.run import main as fundamentals_main
from sources.screeners.stock_analysis_screener.run import main as stocks_main
from sources.screeners.treasury_screener.run import main as treasury_main
from sources.screeners.usda_screener.run import main as usda_main

REGISTRY = {
    "stocks": stocks_main,
    "reddit": reddit_main,
    "edgar": edgar_main,
    "fred": fred_main,
    "cftc": cftc_main,
    "ftd": ftd_main,
    "short_volume": short_volume_main,
    "short_interest": short_interest_main,
    "options": options_main,
    "fundamentals": fundamentals_main,
    "econ_calendar": econ_calendar_main,
    "market_calendar": market_calendar_main,
    "fomc": fomc_main,
    "earnings": earnings_main,
    "treasury": treasury_main,
    "ats": ats_main,
    "nyfed": nyfed_main,
    "cboe_stats": cboe_stats_main,
    "eia": eia_main,
    "usda": usda_main,
    "portfolio": portfolio_main,
    "composite": composite_main,
    "scorer": scorer_main,
    "journal": journal_main,
}


def dispatch(argv=None):
    """Route `<name> [args...]` to a registered screener. `--list` prints names."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("--list", "-l", "list"):
        for name in REGISTRY:
            print(name)
        return
    name, rest = argv[0], argv[1:]
    if name not in REGISTRY:
        print(f"unknown screener: {name}; choose from {', '.join(REGISTRY)}", file=sys.stderr)
        raise SystemExit(2)
    REGISTRY[name](rest)
