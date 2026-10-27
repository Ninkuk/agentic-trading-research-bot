from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


@dataclass(frozen=True)
class Dataset:
    dataset_id: str  # local key, e.g. "dts_cash"
    endpoint: str  # FiscalData path or "xml:yield_curve" sentinel
    table: str  # target table
    date_field: str  # API record-date field
    frequency: str  # daily | monthly | event


# Curated Treasury datasets. Slugs/fields confirmed live at implementation; any
# that 404s is dropped with a note.
CATALOG: list[Dataset] = [
    Dataset(
        "dts_cash", "v1/accounting/dts/operating_cash_balance", "dts_cash", "record_date", "daily"
    ),
    Dataset("debt_penny", "v2/accounting/od/debt_to_penny", "debt_penny", "record_date", "daily"),
    Dataset(
        "avg_rates", "v2/accounting/od/avg_interest_rates", "avg_rates", "record_date", "monthly"
    ),
    Dataset(
        "upcoming_auctions",
        "v1/accounting/od/upcoming_auctions",
        "upcoming_auctions",
        "auction_date",
        "event",
    ),
    Dataset(
        "auction_results",
        "v1/accounting/od/auctions_query",
        "auction_results",
        "auction_date",
        "event",
    ),
    Dataset("yield_curve", "xml:yield_curve", "yield_curve", "record_date", "daily"),
]
