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

# Matched benchmark per crosswalk ticker (composite's CROSSWALK fans asset
# classes out to these). Grading a commodity proxy as excess-vs-SPY flatters
# it whenever equities fall, so each crosswalked row is graded against its
# own asset class. The class proxies themselves map to None: self-benchmark
# is degenerate (excess identically 0), so they grade unbenchmarked (raw
# return only). Resolution uses .get(entity) — an unknown crosswalk ticker
# grades unbenchmarked, never silently vs SPY. A catalog test pins this map
# to composite.catalog.CROSSWALK.
CROSSWALK_BENCHMARK: dict[str, str | None] = {
    # energy -> XLE
    "XLE": None,
    "XOM": "XLE",
    "CVX": "XLE",
    "USO": "XLE",
    # metals -> GLD
    "GLD": None,
    "GDX": "GLD",
    "SLV": "GLD",
    "FCX": "GLD",
    "COPX": "GLD",
    # ags + softs -> DBA
    "DBA": None,
    "CORN": "DBA",
    "SOYB": "DBA",
    "WEAT": "DBA",
    # rates -> TLT
    "TLT": None,
    "IEF": "TLT",
    # equity_index -> SPY
    "SPY": None,
    "QQQ": "SPY",
    "IWM": "SPY",
}
