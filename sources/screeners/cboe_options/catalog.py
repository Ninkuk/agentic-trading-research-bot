from dataclasses import dataclass

from sources.common.screener_common import select_ids


@dataclass(frozen=True)
class Underlying:
    symbol: str  # catalog key WITHOUT the index underscore (e.g. "SPX")
    is_index: bool  # True -> chain_url adds the leading "_" the CBOE API needs


# Starter watchlist (editable). Equities/ETFs use the plain ticker; indices are
# flagged is_index=True and fetched via the "_"-prefixed CBOE path.
CATALOG: list[Underlying] = [
    # mega-cap tech
    Underlying("AAPL", False),
    Underlying("MSFT", False),
    Underlying("NVDA", False),
    Underlying("AMZN", False),
    Underlying("GOOGL", False),
    Underlying("META", False),
    Underlying("TSLA", False),
    # high-volume single names
    Underlying("AMD", False),
    Underlying("NFLX", False),
    Underlying("AVGO", False),
    Underlying("PLTR", False),
    Underlying("COIN", False),
    Underlying("MSTR", False),
    Underlying("SMCI", False),
    # liquid other
    Underlying("JPM", False),
    Underlying("BAC", False),
    Underlying("XOM", False),
    Underlying("DIS", False),
    Underlying("BABA", False),
    # ETFs
    Underlying("SPY", False),
    Underlying("QQQ", False),
    Underlying("IWM", False),
    # indices (fetched as _SPX / _VIX)
    Underlying("SPX", True),
    Underlying("VIX", True),
]

_INDEX = {u.symbol for u in CATALOG if u.is_index}


def index_flag(symbol: str) -> bool:
    """True if `symbol` is a known catalog index; unknown symbols default False
    (treated as equities/ETFs)."""
    return symbol.strip() in _INDEX


# The option chain's selection rule is the catalog-wide one.
select_symbols = select_ids
