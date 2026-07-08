from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    series_id: str
    theme: str  # growth|inflation|rates|labor|credit|housing|sentiment|benchmark


# Curated macro/regime reader. Ids verified live against the FRED API on
# 2026-07-02; any that 404 at implementation time should be dropped here.
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


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated series ids to fetch: ``only`` (or the
    full catalog) minus ``exclude``, then any ``add`` ids appended. Tokens are
    stripped; blanks and duplicates are dropped."""
    ids = list(only) if only else list(all_ids)
    ex = {e.strip() for e in (exclude or ())}
    out, seen = [], set()
    for i in list(ids) + list(add or ()):
        i = i.strip()
        if not i or i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out
