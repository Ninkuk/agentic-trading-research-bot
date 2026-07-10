"""Reverse DCF: solve for the discount rate a market price already implies.

A multiple is shorthand for a DCF. Rather than guess the "right" multiple, hold
the cash-flow assumptions fixed and ask what rate of return the current market
value is pricing in. A low implied return on optimistic assumptions is a bad
bet; a high implied return on conservative ones is an interesting one.

Pure: no network, no database, no wall clock. Every input is an argument.
"""

from collections.abc import Sequence


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
