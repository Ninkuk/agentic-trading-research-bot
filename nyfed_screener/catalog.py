from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    domain_id: str    # reference_rates | rrp | repo | soma | primary_dealer
    endpoint: str     # NY Fed history path
    table: str        # target table
    date_field: str   # API date field


CATALOG: list[Domain] = [
    Domain("reference_rates", "/rates/all/search.json", "reference_rates",
           "effectiveDate"),
    Domain("rrp", "/rp/reverserepo/propositions/search.json", "repo_ops",
           "operationDate"),
    Domain("repo", "/rp/repo/all/results/search.json", "repo_ops",
           "operationDate"),
    Domain("soma", "/soma/summary.json", "soma_holdings", "asOfDate"),
    Domain("primary_dealer", "/pd/get/all/timeseries.json",
           "primary_dealer_stats", "asOfDate"),
]

# primary_dealer is phase 2: defined but off by default (opt-in via --only/--add).
_ENABLED = {"reference_rates", "rrp", "repo", "soma"}


def enabled_ids() -> list:
    return [d.domain_id for d in CATALOG if d.domain_id in _ENABLED]


def select_ids(all_ids: Iterable[str], only, exclude, add=None) -> list:
    """Ordered, de-duplicated domain ids (FRED select_ids semantics)."""
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
