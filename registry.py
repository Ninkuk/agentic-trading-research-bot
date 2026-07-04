import sys

from cftc_screener.run import main as cftc_main
from edgar_screener.run import main as edgar_main
from fred_screener.run import main as fred_main
from ftd_screener.run import main as ftd_main
from finra_short_volume.run import main as short_volume_main
from finra_short_interest.run import main as short_interest_main
from cboe_options.run import main as options_main
from econ_calendar.run import main as econ_calendar_main
from market_calendar.run import main as market_calendar_main
from fomc_calendar.run import main as fomc_main
from earnings_calendar.run import main as earnings_main
from reddit_screener.run import main as reddit_main
from stock_analysis_screener.run import main as stocks_main
from sec_fundamentals.run import main as fundamentals_main
from treasury_screener.run import main as treasury_main
from finra_ats.run import main as ats_main
from nyfed_screener.run import main as nyfed_main
from cboe_stats.run import main as cboe_stats_main
from eia_screener.run import main as eia_main

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
        print(f"unknown screener: {name}; choose from {', '.join(REGISTRY)}",
              file=sys.stderr)
        raise SystemExit(2)
    REGISTRY[name](rest)
