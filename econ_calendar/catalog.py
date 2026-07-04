from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Release:
    release_id: int      # FRED release id
    event_type: str      # stable per-release slug, e.g. 'cpi_release'
    label: str           # human name, e.g. 'Consumer Price Index'
    impact: str          # 'high' | 'med'
    category: str        # 'inflation' | 'labor' | 'growth' | 'consumer'
    release_time: str    # 'HH:MM' ET known time; sole source of events.event_time


# Curated high/med-impact U.S. macro releases. Ids are the spec's numbered set;
# confirm each live against /fred/releases before shipping and drop any that
# 404. Most U.S. macro data prints at 08:30 ET (BLS/BEA/Census).
CATALOG: list[Release] = [
    Release(10, "cpi_release", "Consumer Price Index", "high", "inflation", "08:30"),
    Release(50, "employment_situation", "Employment Situation", "high", "labor", "08:30"),
    Release(46, "ppi_release", "Producer Price Index", "high", "inflation", "08:30"),
    Release(53, "gdp_release", "Gross Domestic Product", "high", "growth", "08:30"),
    Release(99, "retail_sales_release", "Advance Retail Sales", "high", "consumer", "08:30"),
]


def select_ids(only=None, exclude=None) -> list[int]:
    """Resolve the ordered, de-duplicated release_ids to pull: ``only`` (or the
    full catalog) minus ``exclude``. Tokens may be str or int; blanks and
    duplicates are dropped."""
    ids = _coerce(only) if only else [r.release_id for r in CATALOG]
    ex = set(_coerce(exclude))
    out, seen = [], set()
    for i in ids:
        if i in ex or i in seen:
            continue
        seen.add(i)
        out.append(i)
    return out


def _coerce(values: Iterable) -> list[int]:
    """Turn an iterable of str/int tokens into ints, dropping blanks."""
    out = []
    for v in values or ():
        s = str(v).strip()
        if s:
            out.append(int(s))
    return out
