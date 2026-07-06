"""Scorer configuration. The scorer grades composite opinions against
forward returns; it never feeds anything back into the composite."""

HORIZONS = (5, 10, 21)  # trading days (ledger price_date steps)
BENCHMARK = "SPY"  # lives in etfs.db
PRICE_DBS = ("stocks.db", "etfs.db")
COMPOSITE_DB = "composite.db"
# A row registers only if its entry price is at most this many calendar
# days older than the composite snapshot (halted/delisted-symbol guard).
ENTRY_MAX_AGE_DAYS = 7
