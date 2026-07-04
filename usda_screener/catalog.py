from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    commodity: str   # CORN | SOYBEANS | WHEAT
    metric: str      # PRODUCTION | ENDING_STOCKS | TOTAL_USE  (our label)
    query: dict      # NASS Quick Stats filter (short_desc, statisticcat_desc, ...)

    @property
    def id(self) -> str:
        return f"{self.commodity}:{self.metric}"


def _q(commodity, statcat, short_desc):
    return {"commodity_desc": commodity, "statisticcat_desc": statcat,
            "agg_level_desc": "NATIONAL", "short_desc": short_desc,
            "year__GE": "2000"}


# Curated corn/soy/wheat balance-sheet targets. short_desc / statisticcat_desc
# ids are 🟡 — confirm live under NASS's 50k-row cap; drop any that error.
CATALOG: list[Series] = [
    Series("CORN", "PRODUCTION", _q("CORN", "PRODUCTION",
           "CORN, GRAIN - PRODUCTION, MEASURED IN BU")),
    Series("CORN", "ENDING_STOCKS", _q("CORN", "STOCKS",
           "CORN, GRAIN - STOCKS, MEASURED IN BU")),
    Series("CORN", "TOTAL_USE", _q("CORN", "USE",
           "CORN, GRAIN - USE, TOTAL, MEASURED IN BU")),
    Series("SOYBEANS", "PRODUCTION", _q("SOYBEANS", "PRODUCTION",
           "SOYBEANS - PRODUCTION, MEASURED IN BU")),
    Series("SOYBEANS", "ENDING_STOCKS", _q("SOYBEANS", "STOCKS",
           "SOYBEANS - STOCKS, MEASURED IN BU")),
    Series("SOYBEANS", "TOTAL_USE", _q("SOYBEANS", "USE",
           "SOYBEANS - USE, TOTAL, MEASURED IN BU")),
    Series("WHEAT", "PRODUCTION", _q("WHEAT", "PRODUCTION",
           "WHEAT - PRODUCTION, MEASURED IN BU")),
    Series("WHEAT", "ENDING_STOCKS", _q("WHEAT", "STOCKS",
           "WHEAT - STOCKS, MEASURED IN BU")),
    Series("WHEAT", "TOTAL_USE", _q("WHEAT", "USE",
           "WHEAT - USE, TOTAL, MEASURED IN BU")),
]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated composite ids (FRED select_ids semantics)."""
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
