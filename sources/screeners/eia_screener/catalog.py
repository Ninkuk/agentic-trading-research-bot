from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


@dataclass(frozen=True)
class Series:
    series_id: str  # canonical key we store (often == facet)
    route: str  # v2 route, e.g. "petroleum/stoc/wstk"
    facet: str  # EIA facets[series][] value
    label: str
    category: str  # crude|cushing|gasoline|distillate|production|imports|natgas|custom


# Curated weekly WPSR + NG-storage series. Route/facet ids 🟡 confirm live; drop
# any that 404 with a note.
CATALOG: list[Series] = [
    Series("WCESTUS1", "petroleum/stoc/wstk", "WCESTUS1", "Crude oil stocks (ex-SPR)", "crude"),
    Series(
        "W_EPC0_SAX_YCUOK_MBBL",
        "petroleum/stoc/wstk",
        "W_EPC0_SAX_YCUOK_MBBL",
        "Cushing OK crude stocks",
        "cushing",
    ),
    Series("WGTSTUS1", "petroleum/stoc/wstk", "WGTSTUS1", "Total gasoline stocks", "gasoline"),
    Series("WDISTUS1", "petroleum/stoc/wstk", "WDISTUS1", "Distillate stocks", "distillate"),
    Series(
        "WCRFPUS2", "petroleum/sum/sndw", "WCRFPUS2", "Crude oil field production", "production"
    ),
    Series("WCRIMUS2", "petroleum/sum/sndw", "WCRIMUS2", "Crude oil imports", "imports"),
    Series(
        "NW2_EPG0_SWO_R48_BCF",
        "natural-gas/stor/wkly",
        "NW2_EPG0_SWO_R48_BCF",
        "Working gas in storage (Lower 48)",
        "natgas",
    ),
]
