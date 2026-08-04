"""Order-execution configuration. Dollar caps and the account number load
from the environment (.env — a public repo must not publish account scale);
the committed HARD_* ceilings bound what the env may request, preserving the
git-gated property without the disclosure."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

__all__ = [
    "HARD_MAX_ORDER_NOTIONAL",
    "HARD_MAX_DAILY_NOTIONAL",
    "WINDOW_START_MIN",
    "WINDOW_END_MIN",
    "SLIPPAGE",
    "STALE_QUOTE_SEC",
    "MIN_REF_PRICE",
    "MIN_NOTIONAL",
    "Limits",
    "load_limits",
]

HARD_MAX_ORDER_NOTIONAL = 5_000.0
HARD_MAX_DAILY_NOTIONAL = 10_000.0
WINDOW_START_MIN = 2
WINDOW_END_MIN = 45
SLIPPAGE = Decimal("1.002")
STALE_QUOTE_SEC = 300
MIN_REF_PRICE = 1.0  # cents rounding distorts sub-$1 limits; refuse at queue time
MIN_NOTIONAL = 1.0  # broker minimum for dollar-based (fractional) orders

_REQUIRED = (
    "ROBINHOOD_ACCOUNT_NUMBER",
    "ORDERS_MAX_ORDER_NOTIONAL",
    "ORDERS_MAX_DAILY_NOTIONAL",
    "ORDERS_CASH_FLOOR",
)


@dataclass(frozen=True)
class Limits:
    account_number: str
    max_order_notional: float
    max_daily_notional: float
    cash_floor: float


def load_limits(env: Mapping[str, str]) -> Limits:
    missing = [k for k in _REQUIRED if not env.get(k)]
    if missing:
        raise ValueError(f"missing required env: {', '.join(missing)}")
    try:
        order_cap = float(env["ORDERS_MAX_ORDER_NOTIONAL"])
        daily_cap = float(env["ORDERS_MAX_DAILY_NOTIONAL"])
        floor = float(env["ORDERS_CASH_FLOOR"])
    except ValueError:
        raise ValueError("caps must be numeric") from None
    if order_cap <= 0 or daily_cap <= 0 or floor < 0:
        raise ValueError("caps must be positive (floor may be 0)")
    if order_cap > HARD_MAX_ORDER_NOTIONAL or daily_cap > HARD_MAX_DAILY_NOTIONAL:
        raise ValueError("env cap exceeds committed hard ceiling")
    return Limits(env["ROBINHOOD_ACCOUNT_NUMBER"], order_cap, daily_cap, floor)
