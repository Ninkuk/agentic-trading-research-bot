from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    dataset_id: str   # local key, e.g. "dts_cash"
    endpoint: str     # FiscalData path or "xml:yield_curve" sentinel
    table: str        # target table
    date_field: str   # API record-date field
    frequency: str    # daily | monthly | event


# Curated Treasury datasets. Slugs/fields confirmed live at implementation; any
# that 404s is dropped with a note.
CATALOG: list[Dataset] = [
    Dataset("dts_cash", "v1/accounting/dts/operating_cash_balance",
            "dts_cash", "record_date", "daily"),
    Dataset("debt_penny", "v2/accounting/od/debt_to_penny",
            "debt_penny", "record_date", "daily"),
    Dataset("avg_rates", "v2/accounting/od/avg_interest_rates",
            "avg_rates", "record_date", "monthly"),
    Dataset("upcoming_auctions", "v1/accounting/od/upcoming_auctions",
            "upcoming_auctions", "auction_date", "event"),
    Dataset("auction_results", "v1/accounting/od/auctions_query",
            "auction_results", "auction_date", "event"),
    Dataset("yield_curve", "xml:yield_curve", "yield_curve", "record_date",
            "daily"),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list[str]:
    """Ordered, de-duplicated dataset ids: ``only`` (or full catalog) minus
    ``exclude``, then ``add`` appended. Tokens stripped; blanks/dupes dropped.
    Identical to fred_screener.catalog.select_ids."""
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
