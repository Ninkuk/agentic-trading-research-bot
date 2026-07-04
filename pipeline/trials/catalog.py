# Data-point ids the walk-forward scorer needs in stocks.db/etfs.db metrics.
# Declared up front so a DB built with --only excluding one fails with a clear
# missing-id list instead of `OperationalError: no such column`.
REQUIRED_DATA_POINTS = ("price", "low", "averageVolume")

# Horizon-band exit defaults, in TRADING days (market_calendar, never
# date arithmetic). Keys must track pipeline/leads catalog VOCAB horizon_band.
HORIZON_TRADING_DAYS = {"weeks": 20, "months": 60}

DEFAULT_ENTRY_LAG = 1     # entry at the 1st snapshot AFTER as_of_date (t+1)
DEFAULT_FAMILY = "default"

# Per-trade cost haircut: NOT modeled in v1, but recorded in every
# evaluation's detail JSON so the omission is visible (spec: out of scope).
TRANSACTION_HAIRCUT = 0.0
