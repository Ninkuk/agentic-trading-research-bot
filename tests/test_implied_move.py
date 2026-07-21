import math

import pytest

from tools.options.implied_move import (
    REFUTE_SIGMAS,
    expected_absolute_move,
    one_sigma_move,
    realized_vol,
    refutes_timing,
)

# Live AAPL fixtures captured 2026-07-21 and verified against
# Brenner-Subrahmanyam: straddle/spot should land within ~1% of
# sqrt(2/pi) * sigma * sqrt(T).
AAPL_CALL, AAPL_PUT, AAPL_SPOT = 8.425, 7.800, 327.70
AAPL_IV, AAPL_DTE = 0.375211, 10


def test_expected_absolute_move_is_straddle_over_spot():
    assert expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT) == pytest.approx(
        0.04951174855050351
    )


def test_one_sigma_move_uses_calendar_years():
    assert one_sigma_move(AAPL_IV, AAPL_DTE) == pytest.approx(0.06210536661367661)


def test_one_sigma_exceeds_expected_absolute_move():
    """The straddle figure is the MEAN move, so it must sit BELOW 1 sigma.

    This is the error the design review caught: treating straddle/spot as a
    ceiling. If this assertion ever flips, the ceiling misreading is back.
    """
    exp = expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT)
    sig = one_sigma_move(AAPL_IV, AAPL_DTE)
    assert exp < sig
    assert sig / exp == pytest.approx(1.2543, abs=1e-3)


def test_expected_absolute_move_matches_brenner_subrahmanyam():
    exp = expected_absolute_move(AAPL_CALL, AAPL_PUT, AAPL_SPOT)
    predicted = math.sqrt(2 / math.pi) * one_sigma_move(AAPL_IV, AAPL_DTE)
    assert exp == pytest.approx(predicted, rel=0.01)


def test_realized_vol_matches_hand_computation():
    """closes -> returns [+r, -r]; sample stdev = r*sqrt(2), annualized *sqrt(252)."""
    r = 0.01
    closes = [100.0, 100.0 * math.exp(r), 100.0]
    assert realized_vol(closes, window=2) == pytest.approx(r * math.sqrt(2) * math.sqrt(252))


def test_realized_vol_of_flat_series_is_zero():
    assert realized_vol([100.0] * 10, window=5) == pytest.approx(0.0)


def test_realized_vol_uses_only_the_last_window_returns():
    quiet = [100.0] * 10
    shocked = quiet + [130.0, 100.0]
    assert realized_vol(shocked, window=2) > realized_vol(shocked, window=9)


def test_realized_vol_rejects_insufficient_history():
    with pytest.raises(ValueError, match="need 21 closes"):
        realized_vol([100.0] * 10, window=20)


def test_refutes_timing_when_thesis_needs_more_than_two_sigma():
    refuted, k, prob = refutes_timing(0.30, AAPL_IV, AAPL_DTE)
    assert refuted is True
    assert k == pytest.approx(4.8305, abs=1e-3)
    assert prob == pytest.approx(1.3619e-06, rel=1e-3)


def test_does_not_refute_between_one_and_two_sigma():
    """1.61 sigma is the market being less optimistic, NOT a refutation."""
    refuted, k, _ = refutes_timing(0.10, AAPL_IV, AAPL_DTE)
    assert refuted is False
    assert 1.0 < k < REFUTE_SIGMAS


def test_refutation_threshold_is_configurable():
    refuted, _, _ = refutes_timing(0.10, AAPL_IV, AAPL_DTE, sigmas=1.5)
    assert refuted is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"call_mark": -1.0, "put_mark": 1.0, "spot": 100.0},
        {"call_mark": 1.0, "put_mark": 1.0, "spot": 0.0},
    ],
)
def test_expected_absolute_move_rejects_bad_input(kwargs):
    with pytest.raises(ValueError):
        expected_absolute_move(**kwargs)


@pytest.mark.parametrize("iv,dte", [(0.0, 10), (-0.1, 10), (0.3, 0), (0.3, -5)])
def test_one_sigma_move_rejects_bad_input(iv, dte):
    with pytest.raises(ValueError):
        one_sigma_move(iv, dte)
