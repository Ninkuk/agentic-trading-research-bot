from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


@dataclass(frozen=True)
class Feed:
    feed_id: str  # PCR | VIX | VIX3M | VIX9D | VVIX | COR3M
    kind: str  # "pcr" | "vix"


CATALOG: list[Feed] = [
    Feed("PCR", "pcr"),
    Feed("VIX", "vix"),
    Feed("VIX3M", "vix"),
    Feed("VIX9D", "vix"),
    Feed("VVIX", "vix"),
    Feed("COR3M", "vix"),  # 3-month implied correlation; same CDN CSV shape as VIX
]

# All feeds on by default. PCR is sourced from the daily market-statistics
# page's server-rendered payload (the free CSV Cboe discontinued in 2025 —
# see fetch.PCR_URL); it yields one session per run, so history accrues from
# the daily schedule (or a ?dt= backfill loop).
_ENABLED = {"PCR", "VIX", "VIX3M", "VIX9D", "VVIX", "COR3M"}


def enabled_ids() -> list:
    return [f.feed_id for f in CATALOG if f.feed_id in _ENABLED]
