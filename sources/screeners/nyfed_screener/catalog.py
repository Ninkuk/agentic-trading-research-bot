from dataclasses import dataclass

from sources.common.screener_common import select_ids as select_ids  # re-exported


@dataclass(frozen=True)
class Domain:
    domain_id: str  # reference_rates | rrp | repo | soma | primary_dealer
    endpoint: str  # NY Fed history path
    table: str  # target table
    date_field: str  # API date field


CATALOG: list[Domain] = [
    Domain("reference_rates", "/rates/all/search.json", "reference_rates", "effectiveDate"),
    # Both legs come from the single combined results feed (returns Repo +
    # Reverse Repo, tagged operationType); the parser filters to its leg. The
    # old per-leg paths were wrong: /rp/repo/all/results 400'd, and the reverse
    # propositions feed lacked totalAmtSubmitted + the details[] rate.
    Domain("rrp", "/rp/results/search.json", "repo_ops", "operationDate"),
    Domain("repo", "/rp/results/search.json", "repo_ops", "operationDate"),
    Domain("soma", "/soma/summary.json", "soma_holdings", "asOfDate"),
    Domain("primary_dealer", "/pd/get/all/timeseries.json", "primary_dealer_stats", "asOfDate"),
]

# primary_dealer is phase 2: defined but off by default (opt-in via --only/--add).
_ENABLED = {"reference_rates", "rrp", "repo", "soma"}


def enabled_ids() -> list:
    return [d.domain_id for d in CATALOG if d.domain_id in _ENABLED]
