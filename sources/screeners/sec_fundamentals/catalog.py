from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


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
