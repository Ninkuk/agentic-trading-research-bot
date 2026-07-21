"""Options-market arithmetic for the research skills.

Pure functions: no network, no DB, no clock.

The point of this module is to keep vol arithmetic out of skill prose, where a
plausible-looking wrong formula survives review. Specifically: `straddle/spot`
is the EXPECTED ABSOLUTE move (~sqrt(2/pi) * sigma * sqrt(T), the
Brenner-Subrahmanyam approximation), NOT a ceiling. On the AAPL fixture it is
4.95% while the true 1-sigma move is 6.21%, and a move of that size is exceeded
roughly 42% of the time. Gating a verdict on it as a maximum produces false
refutations.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

TRADING_DAYS = 252
CALENDAR_DAYS = 365
REFUTE_SIGMAS = 2.0


def expected_absolute_move(call_mark: float, put_mark: float, spot: float) -> float:
    """ATM straddle divided by spot — the MEAN absolute move, not an upper bound."""
    if spot <= 0:
        raise ValueError("spot must be positive")
    if call_mark < 0 or put_mark < 0:
        raise ValueError("marks must be non-negative")
    return (call_mark + put_mark) / spot


def one_sigma_move(iv: float, days_to_expiry: int) -> float:
    """sigma * sqrt(T), T in calendar years. The true 1-sigma move."""
    if iv <= 0:
        raise ValueError("iv must be positive")
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be positive")
    return iv * math.sqrt(days_to_expiry / CALENDAR_DAYS)


def realized_vol(closes: Sequence[float], window: int) -> float:
    """Annualized close-to-close volatility over the last `window` returns.

    Close-to-close (not Parkinson/Garman-Klass) is deliberate: earnings gap
    overnight, and intraday-range estimators are blind to exactly that gap.
    """
    if window < 2:
        raise ValueError("window must be at least 2")
    if len(closes) < window + 1:
        raise ValueError(f"need {window + 1} closes, got {len(closes)}")
    if any(c <= 0 for c in closes):
        raise ValueError("closes must be positive")
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    return statistics.stdev(returns[-window:]) * math.sqrt(TRADING_DAYS)


def refutes_timing(
    required_move: float,
    iv: float,
    days_to_expiry: int,
    sigmas: float = REFUTE_SIGMAS,
) -> tuple[bool, float, float]:
    """Does the options market refute a thesis's TIMING claim?

    Returns (refuted, k_sigmas, probability), where k_sigmas expresses
    required_move in sigmas and probability is P(|move| >= required_move) under
    a lognormal. Refutation requires the thesis to need a move beyond `sigmas`
    sigma — a claim about probability, not a vague "the market disagrees".

    Between 1 and `sigmas` sigma the market is merely less optimistic than the
    thesis. That is NOT a refutation and must not be reported as one.
    """
    if required_move <= 0:
        raise ValueError("required_move must be positive")
    sigma = one_sigma_move(iv, days_to_expiry)
    k = required_move / sigma
    probability = math.erfc(k / math.sqrt(2))
    return k > sigmas, k, probability
