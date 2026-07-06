"""Scorer configuration. The scorer grades composite opinions against
forward returns; it never feeds anything back into the composite."""

HORIZONS = (5, 10, 21)  # trading days (ledger price_date steps)
BENCHMARK = "SPY"  # lives in etfs.db
PRICE_DBS = ("stocks.db", "etfs.db")
COMPOSITE_DB = "composite.db"
# A row registers only if the symbol's first post-opinion close lands
# within this many calendar days AFTER the composite snapshot
# (halted/thin-symbol guard; 7 covers any holiday weekend).
ENTRY_MAX_AGE_DAYS = 7
