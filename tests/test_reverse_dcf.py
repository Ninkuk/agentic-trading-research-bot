import pytest

from tools.valuation.reverse_dcf import present_value, project_cash_flows


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
