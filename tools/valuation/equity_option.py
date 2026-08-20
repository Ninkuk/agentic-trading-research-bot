"""Equity as a call option on firm value — Damodaran's distressed-equity lens.

Pure functions: no network, no DB, no clock.

Limited liability makes equity a call on the firm's assets with strike equal
to the debt's face value: on liquidation, equity collects max(V - D, 0). For
a healthy business the option value and DCF-minus-debt agree; for a highly
levered one they diverge, and the divergence IS the finding — equity in a
firm worth less than its debt still carries real value, all of it time
premium (the chance assets recover before the debt comes due). Two
inversions follow: volatility is a shareholder asset (and a creditor cost),
and a maturity extension raises equity value.

Conventions follow Damodaran's worked examples (Investment Valuation ch. 5,
packet3): the riskless rate is plugged in as the continuous rate (convert a
discrete rate with ln(1+r) for exactness — his own examples do not), debt is
collapsed to one zero-coupon issue whose face includes cumulated expected
coupons and whose maturity is the face-weighted duration, and firm
volatility may be built from the equity and debt legs via
var = we^2*se^2 + wd^2*sd^2 + 2*we*wd*rho*se*sd.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EquityOptionResult:
    equity_value: float
    debt_value: float
    implied_debt_yield: float
    prob_covers_debt: float


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _require_positive_finite(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite, got {value}")


def firm_volatility(
    equity_vol: float, debt_vol: float, debt_weight: float, correlation: float
) -> float:
    """Combine equity- and debt-leg volatilities into a firm-value volatility.

    debt_weight is debt's share of firm value in [0, 1]; debt_vol may be 0
    (riskless debt) but equity_vol must be positive.
    """
    _require_positive_finite("equity_vol", equity_vol)
    if not math.isfinite(debt_vol) or debt_vol < 0:
        raise ValueError(f"debt_vol must be non-negative and finite, got {debt_vol}")
    if not math.isfinite(debt_weight) or not 0 <= debt_weight <= 1:
        raise ValueError(f"debt_weight must be in [0, 1], got {debt_weight}")
    if not math.isfinite(correlation) or not -1 <= correlation <= 1:
        raise ValueError(f"correlation must be in [-1, 1], got {correlation}")
    we = 1.0 - debt_weight
    variance = (
        we**2 * equity_vol**2
        + debt_weight**2 * debt_vol**2
        + 2.0 * we * debt_weight * correlation * equity_vol * debt_vol
    )
    return math.sqrt(variance)


def equity_as_call(
    firm_value: float,
    debt_face: float,
    duration_years: float,
    risk_free: float,
    firm_vol: float,
) -> EquityOptionResult:
    """Black-Scholes call on firm value with strike = debt face.

    Also returns the debt side (firm - equity), the discrete annualized yield
    that debt value implies against its face, and N(d2) — the risk-neutral
    probability the firm covers its debt at maturity.
    """
    _require_positive_finite("firm_value", firm_value)
    _require_positive_finite("debt_face", debt_face)
    _require_positive_finite("duration_years", duration_years)
    _require_positive_finite("firm_vol", firm_vol)
    if not math.isfinite(risk_free):
        raise ValueError(f"risk_free must be finite, got {risk_free}")

    sqrt_t = math.sqrt(duration_years)
    d1 = (math.log(firm_value / debt_face) + (risk_free + firm_vol**2 / 2.0) * duration_years) / (
        firm_vol * sqrt_t
    )
    d2 = d1 - firm_vol * sqrt_t
    equity = firm_value * _norm_cdf(d1) - debt_face * math.exp(
        -risk_free * duration_years
    ) * _norm_cdf(d2)
    debt = firm_value - equity
    implied_yield = (debt_face / debt) ** (1.0 / duration_years) - 1.0
    return EquityOptionResult(
        equity_value=equity,
        debt_value=debt,
        implied_debt_yield=implied_yield,
        prob_covers_debt=_norm_cdf(d2),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Value equity as a call option on firm value (levered/distressed names)."
    )
    parser.add_argument(
        "--firm-value",
        type=float,
        required=True,
        help="firm value: EV-paired DCF of assets in place, or market EV",
    )
    parser.add_argument(
        "--debt-face",
        type=float,
        required=True,
        help="debt face value including cumulated expected coupons",
    )
    parser.add_argument(
        "--duration", type=float, required=True, help="face-weighted debt duration, years"
    )
    parser.add_argument(
        "--risk-free",
        type=float,
        required=True,
        help="riskless rate, used as the continuous rate (decimal)",
    )
    parser.add_argument(
        "--firm-vol", type=float, help="firm-value volatility (decimal); or pass the legs below"
    )
    parser.add_argument("--equity-vol", type=float, help="equity volatility (decimal)")
    parser.add_argument("--debt-vol", type=float, help="debt volatility (decimal)")
    parser.add_argument("--debt-weight", type=float, help="debt share of firm value, 0-1")
    parser.add_argument(
        "--correlation",
        type=float,
        default=0.5,
        help="equity-debt correlation (default 0.5, Damodaran's Eurotunnel value)",
    )
    parser.add_argument(
        "--market-cap", type=float, help="traded market equity, for a side-by-side comparison row"
    )
    args = parser.parse_args(argv)

    try:
        legs = [args.equity_vol, args.debt_vol, args.debt_weight]
        if args.firm_vol is not None and any(v is not None for v in legs):
            raise ValueError("pass --firm-vol or the equity/debt legs, not both")
        if args.firm_vol is not None:
            vol = args.firm_vol
        elif all(v is not None for v in legs):
            vol = firm_volatility(
                args.equity_vol, args.debt_vol, args.debt_weight, args.correlation
            )
        else:
            raise ValueError(
                "volatility missing: pass --firm-vol, or all of "
                "--equity-vol --debt-vol --debt-weight"
            )
        if args.market_cap is not None:
            _require_positive_finite("market_cap", args.market_cap)
        result = equity_as_call(args.firm_value, args.debt_face, args.duration, args.risk_free, vol)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str]] = [
        ("firm value", f"{args.firm_value:,.2f}"),
        ("debt face (incl. cumulated coupons)", f"{args.debt_face:,.2f}"),
        ("duration (years)", f"{args.duration:.2f}"),
        ("riskless rate (continuous)", f"{args.risk_free:.2%}"),
        ("firm volatility", f"{vol:.2%}"),
        ("equity value (call on firm)", f"{result.equity_value:,.2f}"),
        ("debt value (firm - equity)", f"{result.debt_value:,.2f}"),
        ("implied debt yield", f"{result.implied_debt_yield:.2%}"),
        ("risk-neutral P(firm covers debt at maturity)", f"{result.prob_covers_debt:.2%}"),
    ]
    if args.market_cap is not None:
        rows.append(("market equity", f"{args.market_cap:,.2f}"))
        rows.append(("option/market ratio", f"{result.equity_value / args.market_cap:.2f}x"))
    for label, value in rows:
        print(f"{label:<46}{value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
