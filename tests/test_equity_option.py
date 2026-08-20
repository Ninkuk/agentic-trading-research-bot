import math

import pytest

from tools.valuation.equity_option import equity_as_call, firm_volatility, main

# Damodaran's worked example (Investment Valuation 2nd ed. ch. 5 / packet3
# slides 77-83): firm value $100M, sigma 40%, one zero-coupon $80M face due in
# 10 years, riskless rate 10%. His printed results: equity $75.94M, debt
# $24.06M, implied debt rate 12.77%. The example plugs the 10% rate straight
# into Black-Scholes as the continuous rate — the tool follows that convention.
BASE = dict(firm_value=100.0, debt_face=80.0, duration_years=10.0, risk_free=0.10, firm_vol=0.40)


def test_base_case_matches_damodaran_equity_value():
    assert equity_as_call(**BASE).equity_value == pytest.approx(75.94, abs=0.05)


def test_base_case_matches_damodaran_debt_value_and_yield():
    r = equity_as_call(**BASE)
    assert r.debt_value == pytest.approx(24.06, abs=0.05)
    assert r.implied_debt_yield == pytest.approx(0.1277, abs=1e-3)


def test_base_case_risk_neutral_coverage_probability_is_n_d2():
    assert equity_as_call(**BASE).prob_covers_debt == pytest.approx(0.631, abs=1e-3)


def test_catastrophe_case_equity_keeps_time_premium_value():
    """Firm worth $50M against $80M face: equity is deep out of the money yet
    worth $30.44M (Damodaran's printed value) — the time-premium lesson."""
    r = equity_as_call(**{**BASE, "firm_value": 50.0})
    assert r.equity_value == pytest.approx(30.44, abs=0.05)


def test_equity_plus_debt_equals_firm_value():
    r = equity_as_call(**BASE)
    assert r.equity_value + r.debt_value == pytest.approx(BASE["firm_value"], rel=1e-12)


def test_equity_never_below_intrinsic_floor():
    r = equity_as_call(**BASE)
    floor = BASE["firm_value"] - BASE["debt_face"] * math.exp(
        -BASE["risk_free"] * BASE["duration_years"]
    )
    assert r.equity_value >= max(floor, 0.0)


def test_equity_rises_with_volatility():
    calm = equity_as_call(**{**BASE, "firm_vol": 0.20}).equity_value
    wild = equity_as_call(**{**BASE, "firm_vol": 0.60}).equity_value
    assert wild > calm


def test_equity_rises_with_duration_and_falls_with_face():
    base = equity_as_call(**BASE).equity_value
    assert equity_as_call(**{**BASE, "duration_years": 15.0}).equity_value > base
    assert equity_as_call(**{**BASE, "debt_face": 100.0}).equity_value < base


def test_near_zero_vol_solvent_firm_converges_to_intrinsic():
    r = equity_as_call(**{**BASE, "firm_vol": 1e-6})
    floor = BASE["firm_value"] - BASE["debt_face"] * math.exp(
        -BASE["risk_free"] * BASE["duration_years"]
    )
    assert r.equity_value == pytest.approx(floor, rel=1e-6)


# Eurotunnel early-1998 fixture (packet3 slides 92-95): sigma_e=41%,
# sigma_d=17%, rho=0.5, 85% debt -> firm variance 0.0335.
def test_firm_volatility_matches_eurotunnel_combination():
    vol = firm_volatility(equity_vol=0.41, debt_vol=0.17, debt_weight=0.85, correlation=0.5)
    assert vol**2 == pytest.approx(0.0335, abs=5e-4)


def test_firm_volatility_with_all_equity_is_equity_vol():
    assert firm_volatility(0.41, 0.17, 0.0, 0.5) == pytest.approx(0.41)


@pytest.mark.parametrize(
    "override",
    [
        {"firm_value": 0.0},
        {"firm_value": -5.0},
        {"debt_face": 0.0},
        {"duration_years": 0.0},
        {"firm_vol": 0.0},
        {"firm_vol": float("nan")},
    ],
)
def test_equity_as_call_refuses_bad_domain(override):
    with pytest.raises(ValueError):
        equity_as_call(**{**BASE, **override})


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(equity_vol=0.0, debt_vol=0.1, debt_weight=0.5, correlation=0.5),
        dict(equity_vol=0.4, debt_vol=-0.1, debt_weight=0.5, correlation=0.5),
        dict(equity_vol=0.4, debt_vol=0.1, debt_weight=1.5, correlation=0.5),
        dict(equity_vol=0.4, debt_vol=0.1, debt_weight=0.5, correlation=1.5),
    ],
)
def test_firm_volatility_refuses_bad_domain(kwargs):
    with pytest.raises(ValueError):
        firm_volatility(**kwargs)


def _base_argv():
    return [
        "--firm-value",
        "100",
        "--debt-face",
        "80",
        "--duration",
        "10",
        "--risk-free",
        "0.10",
        "--firm-vol",
        "0.40",
    ]


def test_cli_prints_equity_debt_and_probability_rows(capsys):
    assert main(_base_argv()) == 0
    out = capsys.readouterr().out
    assert "equity value (call on firm)" in out
    assert "75.94" in out
    assert "implied debt yield" in out
    assert "12.77%" in out
    assert "risk-neutral P(firm covers debt at maturity)" in out


def test_cli_market_cap_adds_comparison_rows(capsys):
    assert main([*_base_argv(), "--market-cap", "60"]) == 0
    out = capsys.readouterr().out
    assert "market equity" in out
    assert "option/market ratio" in out


def test_cli_builds_firm_vol_from_legs(capsys):
    argv = [
        "--firm-value",
        "2312",
        "--debt-face",
        "8865",
        "--duration",
        "10.93",
        "--risk-free",
        "0.06",
        "--equity-vol",
        "0.41",
        "--debt-vol",
        "0.17",
        "--debt-weight",
        "0.85",
        "--correlation",
        "0.5",
    ]
    assert main(argv) == 0
    out = capsys.readouterr().out
    # Eurotunnel: Damodaran's printed equity value is (British pounds) 122M.
    assert "equity value (call on firm)" in out


def test_cli_refuses_both_vol_paths(capsys):
    rc = main([*_base_argv(), "--equity-vol", "0.4", "--debt-vol", "0.1", "--debt-weight", "0.5"])
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err.startswith("refused:")
    assert captured.out == ""


def test_cli_refuses_missing_vol(capsys):
    argv = [
        "--firm-value",
        "100",
        "--debt-face",
        "80",
        "--duration",
        "10",
        "--risk-free",
        "0.10",
    ]
    rc = main(argv)
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err.startswith("refused:")
    assert captured.out == ""


def test_cli_refuses_bad_domain_without_partial_table(capsys):
    rc = main(
        [
            "--firm-value",
            "-1",
            "--debt-face",
            "80",
            "--duration",
            "10",
            "--risk-free",
            "0.10",
            "--firm-vol",
            "0.40",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.err.startswith("refused:")
    assert captured.out == ""
