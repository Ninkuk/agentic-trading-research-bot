import pytest

from tools.valuation.reverse_dcf import (
    MAX_RATE,
    implied_discount_rate,
    present_value,
    project_cash_flows,
)


def test_project_applies_growth_compounding() -> None:
    flows = project_cash_flows(100.0, [0.10, 0.10])
    assert flows == pytest.approx([110.0, 121.0])


def test_project_empty_growth_yields_no_flows() -> None:
    assert project_cash_flows(100.0, []) == []


def test_project_rejects_non_positive_base_fcf() -> None:
    # A loss-making business is a harder analysis, not a DCF input.
    with pytest.raises(ValueError, match="base_fcf"):
        project_cash_flows(0.0, [0.10])
    with pytest.raises(ValueError, match="base_fcf"):
        project_cash_flows(-5.0, [0.10])


def test_project_rejects_total_wipeout_growth() -> None:
    # g <= -1.0 drives the flow to zero or negative; the terminal term is then nonsense.
    with pytest.raises(ValueError, match="growth_rates"):
        project_cash_flows(100.0, [-1.0])


def test_present_value_discounts_a_single_flow_with_terminal() -> None:
    # One flow of 110 at r=10%, g=0%.
    #   explicit: 110 / 1.1                      = 100.0
    #   terminal: (110 * 1.0 / 0.10) / 1.1       = 1000.0
    assert present_value([110.0], 0.10, 0.0) == pytest.approx(1100.0)


def test_present_value_is_strictly_decreasing_in_rate() -> None:
    # This monotonicity is what makes bisection valid. Guard it.
    flows = project_cash_flows(100.0, [0.05] * 5)
    rates = [0.06, 0.08, 0.10, 0.15, 0.30, 0.60, 1.0]
    values = [present_value(flows, r, 0.02) for r in rates]
    assert values == sorted(values, reverse=True)
    assert len({round(v, 9) for v in values}) == len(values)  # strictly, not weakly


def test_present_value_diverges_as_rate_approaches_terminal_growth() -> None:
    flows = project_cash_flows(100.0, [0.0])
    near = present_value(flows, 0.02 + 1e-9, 0.02)
    far = present_value(flows, 0.50, 0.02)
    assert near > 1e9
    assert far < 1e3


def test_present_value_rejects_rate_at_or_below_terminal_growth() -> None:
    with pytest.raises(ValueError, match="rate must exceed terminal_growth"):
        present_value([100.0], 0.02, 0.02)
    with pytest.raises(ValueError, match="rate must exceed terminal_growth"):
        present_value([100.0], 0.01, 0.02)


def test_present_value_rejects_empty_cash_flows() -> None:
    with pytest.raises(ValueError, match="cash_flows"):
        present_value([], 0.10, 0.02)


def test_implied_rate_round_trips_a_known_rate() -> None:
    # Build a target value from a known rate, then recover that rate.
    flows = project_cash_flows(100.0, [0.08, 0.08, 0.08, 0.08, 0.08])
    target = present_value(flows, 0.11, 0.025)
    assert implied_discount_rate(target, flows, 0.025) == pytest.approx(0.11, abs=1e-9)


def test_implied_rate_falls_when_price_rises() -> None:
    # Pay more for the same cash flows, earn less. The whole point of the tool.
    flows = project_cash_flows(100.0, [0.05] * 5)
    cheap = implied_discount_rate(1_000.0, flows, 0.02)
    dear = implied_discount_rate(3_000.0, flows, 0.02)
    assert cheap is not None and dear is not None
    assert cheap > dear


def test_implied_rate_returns_none_when_priced_above_the_bracket() -> None:
    # A market cap so low that even a 100% discount rate overvalues it:
    # no root in (g, 1.0]. Report no-solution, never clamp to 1.0.
    flows = project_cash_flows(100.0, [0.05] * 5)
    result = implied_discount_rate(1.0, flows, 0.02)
    assert result is None


def test_implied_rate_never_returns_the_bracket_edge_as_a_solution() -> None:
    # Mutation guard. An implementation that clamped instead of refusing would
    # return MAX_RATE here, and MAX_RATE is a *valid-looking* rate. Assert on
    # value, never identity: `is not MAX_RATE` is true even when the value is
    # 1.0, so an identity check would pass against the very bug it guards.
    flows = project_cash_flows(100.0, [0.05] * 5)
    result = implied_discount_rate(1.0, flows, 0.02)
    assert result is None, f"clamped to {result} instead of refusing"


def test_implied_rate_stays_strictly_inside_the_bracket_when_solvable() -> None:
    # The other side of the same guard: a solvable input must land strictly
    # between the bounds, never on MAX_RATE.
    flows = project_cash_flows(100.0, [0.05] * 5)
    rate = implied_discount_rate(200.0, flows, 0.02)
    assert rate is not None
    assert 0.02 < rate < MAX_RATE


def test_implied_rate_solution_always_exceeds_terminal_growth() -> None:
    flows = project_cash_flows(100.0, [0.03] * 5)
    rate = implied_discount_rate(8_000.0, flows, 0.025)
    assert rate is not None
    assert rate > 0.025


def test_implied_rate_rejects_non_positive_target_value() -> None:
    flows = project_cash_flows(100.0, [0.05])
    with pytest.raises(ValueError, match="target_value"):
        implied_discount_rate(0.0, flows, 0.02)
    with pytest.raises(ValueError, match="target_value"):
        implied_discount_rate(-100.0, flows, 0.02)


def test_implied_rate_rejects_terminal_growth_at_or_above_max_rate() -> None:
    flows = project_cash_flows(100.0, [0.05])
    with pytest.raises(ValueError, match="terminal_growth"):
        implied_discount_rate(1_000.0, flows, 1.0)


def test_implied_rate_rejects_empty_cash_flows() -> None:
    with pytest.raises(ValueError, match="cash_flows"):
        implied_discount_rate(1_000.0, [], 0.02)
