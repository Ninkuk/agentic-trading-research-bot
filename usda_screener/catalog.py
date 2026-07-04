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


# Curated corn/soy/wheat targets, live-confirmed against NASS Quick Stats
# (2026-07, all under the 50k-row cap). TOTAL_USE is intentionally absent: NASS
# has no `statisticcat_desc='USE'` (the query 400s) and no total-use/disappearance
# short_desc for these grains — total use is a balance-sheet concept sourced from
# WASDE, not NASS survey data (see the usda-wasde follow-up, 1e). Production and
# ending stocks come from Quick Stats here.
CATALOG: list[Series] = [
    Series("CORN", "PRODUCTION", _q("CORN", "PRODUCTION",
           "CORN, GRAIN - PRODUCTION, MEASURED IN BU")),
    Series("CORN", "ENDING_STOCKS", _q("CORN", "STOCKS",
           "CORN, GRAIN - STOCKS, MEASURED IN BU")),
    Series("SOYBEANS", "PRODUCTION", _q("SOYBEANS", "PRODUCTION",
           "SOYBEANS - PRODUCTION, MEASURED IN BU")),
    Series("SOYBEANS", "ENDING_STOCKS", _q("SOYBEANS", "STOCKS",
           "SOYBEANS - STOCKS, MEASURED IN BU")),
    Series("WHEAT", "PRODUCTION", _q("WHEAT", "PRODUCTION",
           "WHEAT - PRODUCTION, MEASURED IN BU")),
    Series("WHEAT", "ENDING_STOCKS", _q("WHEAT", "STOCKS",
           "WHEAT - STOCKS, MEASURED IN BU")),
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
