from dataclasses import dataclass

from sources.screeners.stock_analysis_screener import probe

CATALOG_ROUTE = "/stocks/screener/"


@dataclass(frozen=True)
class DataPoint:
    id: str
    name: str
    category: str
    is_pro: bool


def parse_catalog(raw: dict) -> tuple[list[DataPoint], int]:
    """Decode the screener __data.json payload -> (data_points, universe_count).

    Uses the shared ``probe`` decoder to unflatten the ``devalue`` pool, then
    reads the screener slice off the resulting page dict (the node carrying
    ``dataPoints``)."""
    for node in probe.decode_nodes(raw):
        if isinstance(node, dict) and "dataPoints" in node:
            points = [
                DataPoint(dp["id"], dp.get("name", ""), dp.get("cat", ""),
                          bool(dp.get("proOnly", False)))
                for dp in node["dataPoints"]
                if isinstance(dp, dict) and "id" in dp
            ]
            return points, node["count"]
    raise ValueError("screener payload node not found in __data.json")


def fetch_catalog(route: str = CATALOG_ROUTE) -> tuple[list[DataPoint], int]:
    return parse_catalog(probe.fetch_data_json(route))
