import json
import urllib.parse
import urllib.request

DATA_URL = "https://stockanalysis.com/_api/endpoints/screener/data-points"
_UA = {"User-Agent": "Mozilla/5.0"}


def parse_data_points(raw: dict) -> dict[str, dict]:
    """Extract {ticker: {field: value}} from the data-points response."""
    data = raw.get("data", {})
    inner = data.get("data") if isinstance(data, dict) else None
    if not isinstance(inner, dict):
        raise ValueError("unexpected data-points payload shape")
    return inner


def fetch_data_points(ids: list[str], type_: str = "s", url: str = DATA_URL) -> dict[str, dict]:
    query = urllib.parse.urlencode({"type": type_, "ids": " ".join(ids)})
    req = urllib.request.Request(f"{url}?{query}", headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.load(resp)
    return parse_data_points(raw)
