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

# Candidate-screen grading (candidates.py's list, read from stocks.db).
# Only list-ENTRY episodes grade: a name sits on the list for weeks, and
# grading every nightly sighting counts one call N times — the
# overlapping-sample trap v_signal_efficacy documents. A new episode
# begins only after the symbol has been absent this many calendar days.
STOCKS_DB = "stocks.db"
CANDIDATE_ENTRY_GAP_DAYS = 7
# 21/63 trading days grade the screen's dislocation-timing claim; 5/10d
# grade noise for a thesis measured in quarters. The multi-year quality
# claim is ungradeable here and stays research-ticker's job.
CANDIDATE_HORIZONS = (21, 63)

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

# One-shot historical backfill roster for `main.py pricehistory` (plan 005).
# Exactly the crosswalk proxies and their fan-out tickers: these are the only
# symbols the scorer benchmarks against and the backtest replays against, so
# they are the only ones whose history the ledger needs deep. A ticker-universe
# backfill (~11k symbols) is deliberately NOT here — it would hammer an
# unofficial endpoint and needs its own plan. Derived, never retyped, so the two
# cannot drift.
BACKFILL_SYMBOLS: tuple[str, ...] = tuple(sorted(CROSSWALK_BENCHMARK))
