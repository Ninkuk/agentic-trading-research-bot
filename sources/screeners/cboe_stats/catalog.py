from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    feed_id: str   # PCR | VIX | VIX3M | VIX9D | VVIX
    kind: str      # "pcr" | "vix"


CATALOG: list[Feed] = [
    Feed("PCR", "pcr"),
    Feed("VIX", "vix"),
    Feed("VIX3M", "vix"),
    Feed("VIX9D", "vix"),
    Feed("VVIX", "vix"),
]

# PCR is defined but OFF by default: Cboe discontinued the free daily put/call-
# ratio feed (the old CDN/datahouse CSVs 403 or return the SPA shell, and it is
# not on FRED). Its parser is kept for anyone who wires a paid DataShop source;
# opt in with `--only PCR`. The VIX/VVIX CDN feeds are live-confirmed.
_ENABLED = {"VIX", "VIX3M", "VIX9D", "VVIX"}


def enabled_ids() -> list:
    return [f.feed_id for f in CATALOG if f.feed_id in _ENABLED]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated feed ids (FRED select_ids semantics)."""
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
