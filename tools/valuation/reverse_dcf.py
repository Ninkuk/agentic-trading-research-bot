"""Reverse DCF: solve for the discount rate a market price already implies.

A multiple is shorthand for a DCF. Rather than guess the "right" multiple, hold
the cash-flow assumptions fixed and ask what rate of return the current market
value is pricing in. A low implied return on optimistic assumptions is a bad
bet; a high implied return on conservative ones is an interesting one.

Pure: no network, no database, no wall clock. Every input is an argument.
"""

from collections.abc import Sequence

MAX_RATE = 1.0
"""Top of the search bracket. A 100%/yr implied return needs no more precision."""

_BRACKET_EPSILON = 1e-9
"""Nudge above terminal_growth, where present value diverges."""

_ITERATIONS = 200
"""Bisection halves the bracket each pass; 200 is far past float64 precision."""


def project_cash_flows(base_fcf: float, growth_rates: Sequence[float]) -> list[float]:
    """Compound `base_fcf` forward, one flow per entry in `growth_rates`.

    Raises ValueError on a non-positive base (a loss-making business is not a
    DCF input) or on a growth rate that wipes the flow out entirely.
    """
    if base_fcf <= 0:
        raise ValueError(f"base_fcf must be positive, got {base_fcf}")

    flows: list[float] = []
    cash_flow = base_fcf
    for growth in growth_rates:
        if growth <= -1.0:
            raise ValueError(f"growth_rates entries must exceed -1.0, got {growth}")
        cash_flow *= 1.0 + growth
        flows.append(cash_flow)
    return flows


def present_value(
    cash_flows: Sequence[float],
    rate: float,
    terminal_growth: float,
) -> float:
    """Discount `cash_flows` at `rate`, plus a Gordon-growth terminal value.

    Strictly decreasing in `rate` over `(terminal_growth, inf)` — the property
    that makes bisection an unconditionally convergent solver here.
    """
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    if rate <= terminal_growth:
        raise ValueError(
            f"rate must exceed terminal_growth for a finite value; "
            f"got rate={rate}, terminal_growth={terminal_growth}"
        )

    value = 0.0
    for period, cash_flow in enumerate(cash_flows, start=1):
        value += cash_flow / (1.0 + rate) ** period

    horizon = len(cash_flows)
    terminal = cash_flows[-1] * (1.0 + terminal_growth) / (rate - terminal_growth)
    value += terminal / (1.0 + rate) ** horizon
    return value


def implied_discount_rate(
    target_value: float,
    cash_flows: Sequence[float],
    terminal_growth: float,
) -> float | None:
    """Solve for the discount rate at which `cash_flows` are worth `target_value`.

    `target_value` is the market capitalisation for levered (equity) cash flows,
    or enterprise value for unlevered ones. The caller bridges; this function
    never guesses which kind of cash flow it was handed.

    Returns the implied rate, or None when no rate in `(terminal_growth, MAX_RATE]`
    prices the flows at `target_value` — i.e. the market implies a return above
    MAX_RATE. Returning None rather than clamping to MAX_RATE is deliberate: a
    clamped edge is a wrong answer wearing the costume of a right one.

    Raises ValueError on malformed input.
    """
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    if target_value <= 0:
        raise ValueError(f"target_value must be positive, got {target_value}")
    if terminal_growth >= MAX_RATE:
        raise ValueError(
            f"terminal_growth must be below MAX_RATE={MAX_RATE}, got {terminal_growth}"
        )

    low = terminal_growth + _BRACKET_EPSILON
    high = MAX_RATE

    # present_value is strictly decreasing in rate, so a root exists in
    # (low, high) iff pv(high) < target < pv(low). Both comparisons below are
    # deliberately inclusive of equality: if the target sits exactly at either
    # edge's present value, the "solution" is indistinguishable from having no
    # solution at all (an exact root at MAX_RATE looks identical to a target
    # that's just barely out of reach) — refuse rather than let the bisection
    # loop converge onto the edge and report it as a real answer.
    if present_value(cash_flows, high, terminal_growth) >= target_value:
        return None
    if present_value(cash_flows, low, terminal_growth) <= target_value:
        return None

    for _ in range(_ITERATIONS):
        midpoint = (low + high) / 2.0
        if present_value(cash_flows, midpoint, terminal_growth) > target_value:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0
