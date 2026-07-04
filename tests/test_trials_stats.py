import math

import pytest

from pipeline.trials import stats

RETS = [0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.00, 0.02]


def test_mean_stdev_sharpe():
    assert stats.mean(RETS) == pytest.approx(0.01125)
    assert stats.sample_stdev(RETS) == pytest.approx(0.020310096011589902)
    assert stats.sharpe(RETS) == pytest.approx(0.5539117094069972)


def test_skew_and_raw_kurtosis_population_moments():
    assert stats.skewness(RETS) == pytest.approx(-0.17944137135266425)
    assert stats.kurtosis_raw(RETS) == pytest.approx(1.9114521841794574)


def test_degenerate_series_return_none():
    assert stats.sample_stdev([0.01]) is None
    assert stats.sharpe([0.02, 0.02, 0.02]) is None      # sd == 0
    assert stats.skewness([0.02, 0.02]) is None          # m2 == 0
    assert stats.kurtosis_raw([5.0]) is None


def test_max_drawdown_compounded():
    # equity: 1.10 -> 0.88 -> 0.968; peak 1.10, trough 0.88 -> 20% dd
    assert stats.max_drawdown([0.10, -0.20, 0.10]) == pytest.approx(0.20)
    assert stats.max_drawdown([0.01, 0.02]) == 0.0


def test_expected_max_sharpe_fixture():
    # family SRs [0.5, 0.3, 0.8]: sd_SR = 0.2516611478423584, N = 3
    sr0 = stats.expected_max_sharpe(3, 0.2516611478423584)
    assert sr0 == pytest.approx(0.21461775838612585)


def test_expected_max_sharpe_edges():
    assert stats.expected_max_sharpe(1, 0.5) is None     # N < 2
    assert stats.expected_max_sharpe(3, 0.0) is None     # sd_SR == 0
    assert stats.expected_max_sharpe(3, None) is None


def test_deflated_sharpe_fixture():
    # SR=0.8, T=24, skew=-0.3, kurt=4.0, N=3, sd_SR as above:
    # denom = sqrt(1 - (-0.3)(0.8) + ((4-1)/4)(0.64)) = 1.3114877048604001
    dsr = stats.deflated_sharpe(0.8, 24, -0.3, 4.0, 3, 0.2516611478423584)
    assert dsr == pytest.approx(0.9838475849035124)


def test_dsr_denominator_normal_case():
    # skew=0, RAW kurt=3 (normal): denominator must be sqrt(1 + 0.5*SR^2).
    # An excess-kurtosis slip (kurt=0 at normality) would flip the term's sign.
    sr = 0.5
    dsr = stats.deflated_sharpe(sr, 100, 0.0, 3.0, 3, 0.2516611478423584)
    sr0 = stats.expected_max_sharpe(3, 0.2516611478423584)
    expected = __import__("statistics").NormalDist().cdf(
        (sr - sr0) * math.sqrt(99) / math.sqrt(1 + 0.5 * sr * sr))
    assert dsr == pytest.approx(expected)


def test_dsr_edges_return_none_never_fake_one():
    assert stats.deflated_sharpe(0.8, 24, -0.3, 4.0, 1, 0.25) is None   # N<2
    assert stats.deflated_sharpe(0.8, 24, -0.3, 4.0, 3, 0.0) is None    # sd_SR=0
    assert stats.deflated_sharpe(None, 24, -0.3, 4.0, 3, 0.25) is None  # no SR
    assert stats.deflated_sharpe(0.8, 1, -0.3, 4.0, 3, 0.25) is None    # T<2
    # negative denominator-squared (pathological skew/kurt) -> None
    assert stats.deflated_sharpe(2.0, 24, 5.0, 0.5, 3, 0.25) is None
