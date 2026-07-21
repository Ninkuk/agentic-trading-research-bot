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

import argparse
import json
import math
import statistics
import sys
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


def _render(rows: list[tuple[str, str]]) -> str:
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"{label.ljust(width)}  {value}" for label, value in rows)


def _load_closes(path: str) -> list[float]:
    """Load and validate a closes JSON file.

    Raises ValueError (never a raw FileNotFoundError, JSONDecodeError, or
    TypeError) so every bad-input path funnels through the same refusal
    handling in main().
    """
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        raise ValueError(f"closes file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"closes file is not valid JSON: {exc}") from None

    if not isinstance(payload, list):
        raise ValueError("closes file must contain a JSON array of numbers")

    closes: list[float] = []
    for item in payload:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"closes file must contain only numbers, found {type(item).__name__}")
        closes.append(float(item))
    return closes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.options.implied_move",
        description=(
            "Print the options-implied move table. The straddle figure is a MEAN, never a ceiling."
        ),
    )
    parser.add_argument("--call-mark", type=float, required=True)
    parser.add_argument("--put-mark", type=float, required=True)
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument("--iv", type=float, required=True, help="ATM IV as a decimal, e.g. 0.3752")
    parser.add_argument("--dte", type=int, required=True, help="calendar days to expiry")
    parser.add_argument(
        "--closes",
        default=None,
        help="path to a JSON file holding daily closes, oldest first",
    )
    parser.add_argument(
        "--required-move",
        type=float,
        default=None,
        help="move the thesis needs, as a decimal (0.30 = 30%%)",
    )
    args = parser.parse_args(argv)

    # All domain validation happens here, before any row is built or printed.
    # A caller must never see a half-printed table followed by an error.
    try:
        expected = expected_absolute_move(args.call_mark, args.put_mark, args.spot)
        sigma = one_sigma_move(args.iv, args.dte)

        closes: list[float] | None = None
        if args.closes:
            closes = _load_closes(args.closes)

        refutation: tuple[bool, float, float] | None = None
        if args.required_move is not None:
            refutation = refutes_timing(args.required_move, args.iv, args.dte)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str]] = [
        ("spot", f"{args.spot:.2f}"),
        ("dte (calendar days)", str(args.dte)),
        ("ATM IV", f"{args.iv * 100:.2f}%"),
        ("expected absolute move (MEAN, not a ceiling)", f"{expected * 100:.2f}%"),
        ("1-sigma move", f"{sigma * 100:.2f}%"),
    ]

    if closes is not None:
        for window in (60, 20):
            try:
                rv = realized_vol(closes, window)
            except ValueError:
                # A valid-but-short series is NOT a refusal — the table must
                # still render this window's rows, visibly UNKNOWN.
                rows.append((f"RV{window}", "insufficient history"))
                rows.append((f"IV > RV{window}?", "UNKNOWN"))
                continue
            rows.append((f"RV{window}", f"{rv * 100:.2f}%"))
            rows.append((f"IV > RV{window}?", "YES" if args.iv > rv else "NO"))

    if refutation is not None:
        refuted, k, probability = refutation
        rows += [
            ("thesis requires", f"{args.required_move * 100:.2f}%"),
            ("that is", f"{k:.2f} sigma"),
            ("P(|move| >= required)", f"{probability:.6%}"),
            (
                f"refutes timing claim (> {REFUTE_SIGMAS:g} sigma)?",
                "YES" if refuted else "NO",
            ),
        ]

    print(_render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
