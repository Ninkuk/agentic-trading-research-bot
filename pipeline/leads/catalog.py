from dataclasses import dataclass


@dataclass(frozen=True)
class Mapping:
    code: str          # CFTC contract market code (cftc_screener catalog key)
    etf: str           # one liquid, long-underlying ETF (never inverse/levered)
    asset_class: str   # copied from the cftc catalog; travels with the lead
    note: str = ""     # contract name, for humans


# COT -> ETF instrument map (spec D3). Direction is expressed in the lead's
# `direction` field, so every ETF here is plain-long-underlying. Unmapped
# catalog markets (VIX, softs, minor FX, ...) produce no lead by design.
# Append-only config.
ETF_MAP: list[Mapping] = [
    Mapping("13874A", "SPY", "equity_index", "E-Mini S&P 500"),
    Mapping("209742", "QQQ", "equity_index", "E-Mini Nasdaq-100"),
    Mapping("239742", "IWM", "equity_index", "E-Mini Russell 2000"),
    Mapping("042601", "SHY", "rates", "2-Year T-Note"),
    Mapping("043602", "IEF", "rates", "10-Year T-Note"),
    Mapping("020601", "TLT", "rates", "U.S. Treasury Bond"),
    Mapping("099741", "FXE", "fx", "Euro FX"),
    Mapping("097741", "FXY", "fx", "Japanese Yen"),
    Mapping("088691", "GLD", "metals", "Gold"),
    Mapping("084691", "SLV", "metals", "Silver"),
    Mapping("085692", "CPER", "metals", "Copper"),
    Mapping("067651", "USO", "energy", "WTI Crude Oil"),
    Mapping("023651", "UNG", "energy", "Natural Gas (Henry Hub)"),
    Mapping("002602", "CORN", "ags", "Corn"),
    Mapping("001602", "WEAT", "ags", "Chicago Wheat (SRW)"),
    Mapping("005602", "SOYB", "ags", "Soybeans"),
]

ETF_BY_CODE: dict[str, Mapping] = {m.code: m for m in ETF_MAP}

# Family precedence per asset class (spec D1): physicals take the
# disaggregated producer/merchant net, financials the TFF dealer net.
PHYSICAL_CLASSES = frozenset({"metals", "energy", "ags", "softs"})
FINANCIAL_CLASSES = frozenset({"equity_index", "rates", "fx"})

# COT extreme thresholds — match the source v_extremes convention (spec D2).
COT_LONG_THRESHOLD = 90.0    # commercial index >= -> long lead
COT_SHORT_THRESHOLD = 10.0   # commercial index <= -> short lead

# Quality composite (spec D4/D5).
QUALITY_MIN_DIMENSIONS = 2          # of 3; fewer -> name drops out (counted)
QUALITY_TOP_DECILE = 0.90           # rank_pct >= -> long
QUALITY_BOTTOM_DECILE = 0.10        # rank_pct <= -> short
REVENUE_TAGS = ("Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax")
GROWTH_WINDOW_DAYS = 35             # +/- tolerance around 12 months for YoY pair
GROWTH_RATIO_BOUNDS = (0.2, 5.0)    # latest/year-ago outside -> pair discarded

# Regime dial (spec D6) — defaults, flagged for Stage 6 calibration.
CPI_YOY_LATE_CYCLE = 3.0
UNRATE_LATE_CYCLE = 4.5
RISK_OFF_SCALAR = 0.5
RISK_ON_SCALAR = 1.0

# Tag vocabulary (pinned, extensible): enforced by writer-side validation in
# db.write_leads, not CHECK constraints — adding a value is a code change with
# a test, not a migration. momentum/carry are reserved for future legs.
VOCAB: dict[str, frozenset] = {
    "signal_type": frozenset({"mean_reversion", "quality", "momentum", "carry"}),
    "implementation": frozenset({"cross_sectional", "time_series"}),
    "horizon_band": frozenset({"weeks", "months"}),
}
