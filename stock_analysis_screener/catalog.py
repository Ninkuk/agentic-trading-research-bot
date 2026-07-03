import json
import urllib.request
from dataclasses import dataclass

CATALOG_URL = "https://stockanalysis.com/stocks/screener/__data.json"
_UA = {"User-Agent": "Mozilla/5.0"}


@dataclass(frozen=True)
class DataPoint:
    id: str
    name: str
    category: str
    is_pro: bool


def parse_catalog(raw: dict) -> tuple[list[DataPoint], int]:
    """Decode SvelteKit index-deduplicated payload -> (data_points, universe_count)."""
    pool = None
    for node in raw.get("nodes", []):
        data = node.get("data") if isinstance(node, dict) else None
        if (isinstance(data, list) and data and isinstance(data[0], dict)
                and "dataPoints" in data[0]):
            pool = data
            break
    if pool is None:
        raise ValueError("screener payload node not found in __data.json")

    top = pool[0]

    def deref(idx):
        return pool[idx]

    count = deref(top["count"])
    points: list[DataPoint] = []
    for dp_idx in deref(top["dataPoints"]):
        obj = deref(dp_idx)
        if not isinstance(obj, dict) or "id" not in obj:
            continue
        points.append(DataPoint(
            id=deref(obj["id"]),
            name=deref(obj["name"]) if "name" in obj else "",
            category=deref(obj["cat"]) if "cat" in obj else "",
            is_pro=bool(deref(obj["proOnly"])) if "proOnly" in obj else False,
        ))
    return points, count


def fetch_catalog(url: str = CATALOG_URL) -> tuple[list[DataPoint], int]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = json.load(resp)
    return parse_catalog(raw)
