import json
import math

import pytest

from tools.options.implied_move import (
    REFUTE_SIGMAS,
    expected_absolute_move,
    main,
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
    assert k == pytest.approx(4.2245023058879125, rel=1e-9)
    assert prob == pytest.approx(2.3946940006176614e-05, rel=1e-9)


def test_refutes_timing_uses_the_lognormal_transform_it_documents():
    """k must come from log1p(required_move)/sigma, not required_move/sigma.

    sigma*sqrt(T) is the stdev of LOG returns, so dividing an ARITHMETIC
    return by it overstates k and biases toward MORE refutation. A silent
    revert to the arithmetic form makes k jump back to 4.83, so pin the gap.
    """
    sigma = one_sigma_move(AAPL_IV, AAPL_DTE)
    _, k, _ = refutes_timing(0.30, AAPL_IV, AAPL_DTE)
    arithmetic_k = 0.30 / sigma
    assert k < arithmetic_k - 0.5
    assert k == pytest.approx(math.log1p(0.30) / sigma, rel=1e-12)


def test_does_not_refute_between_one_and_two_sigma():
    """1.53 sigma is the market being less optimistic, NOT a refutation."""
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


BASE_ARGS = [
    "--call-mark",
    "8.425",
    "--put-mark",
    "7.800",
    "--spot",
    "327.70",
    "--iv",
    "0.375211",
    "--dte",
    "10",
]


def test_cli_prints_both_move_figures(capsys):
    """Pin each value to ITS OWN row, not just anywhere in stdout.

    A value/label swap (6.21% on the mean row, 4.95% on the 1-sigma row)
    must fail this test even though both figures still appear somewhere.
    """
    assert main(BASE_ARGS) == 0
    lines = capsys.readouterr().out.splitlines()
    mean_line = next(ln for ln in lines if "expected absolute move" in ln)
    sigma_line = next(ln for ln in lines if ln.strip().startswith("1-sigma move"))
    assert "4.95%" in mean_line
    assert "6.21%" not in mean_line
    assert "6.21%" in sigma_line
    assert "4.95%" not in sigma_line


def test_cli_labels_the_straddle_figure_as_a_mean_not_a_ceiling(capsys):
    """The row that carries 4.95% must be the one labeled MEAN/not-a-ceiling.

    Asserting "mean" and "not a ceiling" appear anywhere in stdout would
    still pass if a regression attached those words to the 1-sigma row
    instead of the straddle row — this pins label and value together.
    """
    main(BASE_ARGS)
    lines = capsys.readouterr().out.splitlines()
    mean_value_line = next(ln for ln in lines if "4.95%" in ln)
    assert "mean" in mean_value_line.lower()
    assert "not a ceiling" in mean_value_line.lower()


def test_cli_emits_explicit_yes_no_rows_for_both_windows(tmp_path, capsys):
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0 + i * 0.5 for i in range(70)]))
    main([*BASE_ARGS, "--closes", str(closes)])
    out = capsys.readouterr().out
    assert "IV > RV60?" in out
    assert "IV > RV20?" in out


def test_cli_reports_insufficient_history_rather_than_silently_skipping(tmp_path, capsys):
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0 + i for i in range(25)]))
    main([*BASE_ARGS, "--closes", str(closes)])
    out = capsys.readouterr().out
    assert "insufficient history" in out
    assert "IV > RV20?" in out


def test_cli_reports_refutation_with_the_implied_probability(capsys):
    main([*BASE_ARGS, "--required-move", "0.30"])
    out = capsys.readouterr().out
    assert "4.22 sigma" in out
    assert "YES" in out


def test_cli_does_not_refute_a_sub_two_sigma_requirement(capsys):
    main([*BASE_ARGS, "--required-move", "0.10"])
    out = capsys.readouterr().out
    assert "refutes timing claim (> 2 sigma)?" in out
    assert [ln for ln in out.splitlines() if "refutes timing claim" in ln][0].endswith("NO")


def test_cli_refuses_bad_input_with_exit_2(capsys):
    assert main([*BASE_ARGS[:-2], "--dte", "0"]) == 2
    assert "refused" in capsys.readouterr().err


def test_cli_refuses_non_positive_required_move_with_exit_2(capsys):
    """Finding 1 regression: refutes_timing's ValueError must not escape main()."""
    assert main([*BASE_ARGS, "--required-move", "0"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""  # no half-printed table before the refusal
    assert "refused:" in captured.err


def test_cli_refuses_missing_closes_file_with_exit_2(tmp_path, capsys):
    """Finding 2 regression: a missing --closes file must refuse, not crash."""
    missing = tmp_path / "does-not-exist.json"
    assert main([*BASE_ARGS, "--closes", str(missing)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err


def test_cli_refuses_malformed_closes_json_with_exit_2(tmp_path, capsys):
    """Finding 2 regression: malformed JSON must refuse, not crash."""
    closes = tmp_path / "closes.json"
    closes.write_text("{not valid json")
    assert main([*BASE_ARGS, "--closes", str(closes)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err


def test_cli_refuses_non_numeric_closes_payload_with_exit_2(tmp_path, capsys):
    """Finding 2 regression: a bool (or other non-number) in the payload must refuse.

    isinstance(True, int) is True in Python, so this also checks bool is
    explicitly rejected rather than silently treated as a price of 1.0/0.0.
    """
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0, True, 101.0]))
    assert main([*BASE_ARGS, "--closes", str(closes)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err


def test_cli_refuses_directory_as_closes_with_exit_2(tmp_path, capsys):
    """Finding 1 regression: OSError (IsADirectoryError) must refuse, not crash.

    A directory passed as --closes should exit 2, not exit 1 with a traceback.
    """
    closes_dir = tmp_path / "closes_dir"
    closes_dir.mkdir()
    assert main([*BASE_ARGS, "--closes", str(closes_dir)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err


def test_cli_refuses_non_positive_close_rather_than_blaming_history(tmp_path, capsys):
    """A single 0.0 in a LONG, valid-length series is corrupt data, not short history.

    Before the fix, realized_vol's positivity ValueError was caught by the RV
    loop's `except ValueError` and rendered as "insufficient history" for BOTH
    windows at exit 0 — including RV20, whose window does not even contain the
    bad point. Corrupt prices must refuse, loudly, at exit 2.
    """
    closes = tmp_path / "closes.json"
    payload = [100.0 + i * 0.5 for i in range(71)]
    payload[40] = 0.0
    closes.write_text(json.dumps(payload))
    assert main([*BASE_ARGS, "--closes", str(closes)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err
    assert "insufficient history" not in captured.err


def test_cli_refuses_negative_close_with_exit_2(tmp_path, capsys):
    closes = tmp_path / "closes.json"
    closes.write_text(json.dumps([100.0, -101.0, 102.0]))
    assert main([*BASE_ARGS, "--closes", str(closes)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err


def test_cli_refuses_nan_in_closes_payload_with_exit_2(tmp_path, capsys):
    """Finding 2 regression: NaN / Infinity in JSON payload must refuse, not crash.

    JSON allows bare NaN/Infinity (non-standard), but they must be rejected
    rather than passed through to statistics.stdev() where they cause confusion.
    """
    closes = tmp_path / "closes.json"
    # Write raw NaN directly (json.dumps won't emit it by default)
    closes.write_text("[100.0, NaN, 101.0]")
    assert main([*BASE_ARGS, "--closes", str(closes)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refused:" in captured.err
