from collections.abc import Iterable

# Data-point ids whose values are always text: categories, dates, currencies,
# identifiers, and Yes/No flags. Forces TEXT even if a sample looks numeric.
STRING_IDS: frozenset[str] = frozenset(
    {
        "n",
        "marketCapCategory",
        "industry",
        "sector",
        "exchange",
        "country",
        "usState",
        "high52Date",
        "low52Date",
        "allTimeHighDate",
        "allTimeLowDate",
        "priceDate",
        "ipoDate",
        "lastReportDate",
        "fiscalYearEnd",
        "last10kFilingDate",
        "earningsDate",
        "nextEarningsDate",
        "lastEarningsDate",
        "earningsTime",
        "exDivDate",
        "paymentDate",
        "lastSplitDate",
        "lastSplitType",
        "isSpac",
        "optionable",
        "ma50vs200",
        "priceCurrency",
        "financialCurrency",
        "sic",
        "cik",
        "isin",
        "cusip",
        "website",
        "analystRatings",
        "analystRatingsTop",
        "payoutFrequency",
        "tag",
    }
)


def infer_affinity(values: Iterable[object]) -> str:
    """REAL if every non-null value is a non-bool number, else TEXT (all-null -> TEXT)."""
    saw_value = False
    for v in values:
        if v is None:
            continue
        saw_value = True
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return "TEXT"
    return "REAL" if saw_value else "TEXT"


def column_type(dp_id: str, values: Iterable[object]) -> str:
    """SQLite affinity for a data-point column: STRING_IDS override, else inferred."""
    if dp_id in STRING_IDS:
        return "TEXT"
    return infer_affinity(values)
