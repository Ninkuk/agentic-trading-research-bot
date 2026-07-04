import html
import json
import urllib.request

API_BASE = "https://apewisdom.io/api/v1.0/filter"
_UA = {"User-Agent": "Mozilla/5.0"}

_NUMERIC_FIELDS = ("rank", "mentions", "upvotes", "rank_24h_ago", "mentions_24h_ago")


def _to_int(value):
    """Coerce API numerics to int; None/'' -> None (new-entrant 24h fields)."""
    if value is None or value == "":
        return None
    return int(value)


def _normalize(row: dict) -> dict:
    out = {"ticker": row["ticker"], "name": html.unescape(row.get("name") or "")}
    for field in _NUMERIC_FIELDS:
        out[field] = _to_int(row.get(field))
    return out


def parse_page(raw: dict) -> tuple[list[dict], int]:
    """Normalize one ApeWisdom page -> (rows, total_pages). Raises on bad shape.

    Rows with a missing or empty ticker are dropped: ticker is the observations
    primary key (NOT NULL), so such rows are unusable and must not crash or
    poison the snapshot."""
    results = raw.get("results")
    if not isinstance(results, list):
        raise ValueError("unexpected ApeWisdom payload: missing 'results' list")
    pages = _to_int(raw.get("pages")) or 1
    rows = [_normalize(r) for r in results if r.get("ticker")]
    return rows, pages


def _http_get_page(filter_: str, page: int, base: str = API_BASE) -> dict:
    req = urllib.request.Request(f"{base}/{filter_}/page/{page}", headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_filter(filter_: str, get_page=_http_get_page) -> list[dict]:
    """Fetch every page of a filter and return the accumulated normalized rows."""
    rows, pages = parse_page(get_page(filter_, 1))
    for page in range(2, pages + 1):
        more, _ = parse_page(get_page(filter_, page))
        rows.extend(more)
    return rows
