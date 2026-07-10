import pytest

from tools.valuation.reverse_dcf import project_cash_flows


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
