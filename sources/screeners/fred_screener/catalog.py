from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


@dataclass(frozen=True)
class Series:
    series_id: str
    theme: str  # growth|inflation|rates|labor|credit|housing|sentiment|benchmark


# Curated macro/regime reader. Ids are verified live against the FRED API;
# any that 404 at implementation time should be dropped here.
CATALOG: list[Series] = [
    # growth
    Series("GDPC1", "growth"),
    Series("INDPRO", "growth"),
    Series("PAYEMS", "growth"),
    Series("RSAFS", "growth"),
    # inflation
    Series("CPIAUCSL", "inflation"),
    Series("CPILFESL", "inflation"),
    Series("PCEPILFE", "inflation"),
    Series("T5YIE", "inflation"),
    Series("T10YIE", "inflation"),
    # rates
    Series("DFF", "rates"),
    Series("DGS2", "rates"),
    Series("DGS10", "rates"),
    Series("DGS30", "rates"),
    Series("T10Y2Y", "rates"),
    Series("T10Y3M", "rates"),
    # labor
    Series("UNRATE", "labor"),
    Series("ICSA", "labor"),
    Series("CIVPART", "labor"),
    Series("JTSJOL", "labor"),
    # credit
    Series("BAMLH0A0HYM2", "credit"),
    Series("BAMLC0A0CM", "credit"),
    Series("DRSFRMACBS", "credit"),
    # housing
    Series("HOUST", "housing"),
    Series("PERMIT", "housing"),
    Series("CSUSHPINSA", "housing"),
    Series("MORTGAGE30US", "housing"),
    # sentiment
    Series("UMCSENT", "sentiment"),
    Series("VIXCLS", "sentiment"),
    Series("STLFSI4", "sentiment"),
    Series("NFCI", "sentiment"),
    # benchmark (grading spine for the backtest combiner; FRED licensing
    # caps SP500 history at ~10 years)
    Series("SP500", "benchmark"),
]


# Themes whose series carry no ALFRED vintage history — benchmark price spines
# (e.g. SP500) are licensed/unrevised and 400 on the vintage endpoints. run.py
# skips --vintages for these; their plain observations are still fetched.
VINTAGELESS_THEMES = frozenset({"benchmark"})
