from collections.abc import Iterable
from dataclasses import dataclass


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


def select_symbols(all_symbols: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated symbols to fetch: ``only`` (or all)
    minus ``exclude``, then any ``add`` appended. Tokens stripped; blanks and
    duplicates dropped."""
    syms = list(only) if only else list(all_symbols)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for s in list(syms) + list(add or ()):
        s = s.strip()
        if not s or s in ex or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
