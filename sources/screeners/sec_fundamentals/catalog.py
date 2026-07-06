from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    tag: str  # us-gaap tag, the stable key, e.g. "NetIncomeLoss"
    taxonomy: str  # us-gaap | ifrs-full | dei | srt
    unit: str  # USD | shares | USD/shares
    kind: str  # "instant" (balance-sheet stock) | "duration" (flow)
    group: str  # income | balance | cashflow | shares | per_share


# Curated headline concepts. Tags verified live against data.sec.gov at
# implementation; any tag returning no frames is dropped with a note. The `kind`
# drives the frames period suffix (instant -> trailing 'I'); the wrong suffix
# yields an empty frame.
CATALOG: list[Concept] = [
    # income (duration)
    Concept("Revenues", "us-gaap", "USD", "duration", "income"),
    Concept(
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap",
        "USD",
        "duration",
        "income",
    ),
    Concept("OperatingIncomeLoss", "us-gaap", "USD", "duration", "income"),
    Concept("NetIncomeLoss", "us-gaap", "USD", "duration", "income"),
    # balance (instant)
    Concept("Assets", "us-gaap", "USD", "instant", "balance"),
    Concept("Liabilities", "us-gaap", "USD", "instant", "balance"),
    Concept("StockholdersEquity", "us-gaap", "USD", "instant", "balance"),
    Concept("CashAndCashEquivalentsAtCarryingValue", "us-gaap", "USD", "instant", "balance"),
    # per-share / shares
    Concept("EarningsPerShareDiluted", "us-gaap", "USD/shares", "duration", "per_share"),
    Concept("CommonStockSharesOutstanding", "us-gaap", "shares", "instant", "shares"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Resolve the ordered, de-duplicated tags to fetch: ``only`` (or the full
    catalog) minus ``exclude``, then any ``add`` appended. Tokens stripped;
    blanks and duplicates dropped. Identical to fred_screener.catalog.select_ids."""
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
