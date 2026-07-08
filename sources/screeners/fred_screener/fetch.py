import json
import time
import urllib.parse

import sources.common.http_client as http_client

API_BASE = "https://api.stlouisfed.org/fred"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})  # FRED throttles with 429
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)


def require_api_key(api_key):
    """Return a non-empty API key or raise. Never echoes the key value."""
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set; add it to .env (see .env.example)")
    return api_key


def _build_url(path: str, params: dict, api_key: str) -> str:
    """Assemble a FRED API URL with api_key + file_type=json + caller params."""
    query = {**params, "api_key": api_key, "file_type": "json"}
    return f"{API_BASE}/{path}?{urllib.parse.urlencode(query)}"


def _http_get(
    url: str,
    opener=_urlopen,
    attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    sleep=time.sleep,
) -> str:
    """GET with bounded backoff, retrying FRED throttling (429) and transient
    5xx/network errors. Other HTTP errors (e.g. 400) raise immediately."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


def parse_observations(payload: dict) -> list[dict]:
    """Map a /series/observations payload to [{date, value}], turning FRED's
    '.' missing marker into None and numeric strings into floats."""
    rows = []
    for o in payload.get("observations", []):
        raw = o.get("value")
        value = None if raw in (None, ".") else float(raw)
        rows.append({"date": o["date"], "value": value})
    return rows


def parse_observation_vintages(payload: dict) -> list[dict]:
    """Map a /series/observations payload with realtime_start to
    [{date, realtime_start, value}], turning FRED's '.' missing marker into None
    and numeric strings into floats."""
    rows = []
    for o in payload.get("observations", []):
        raw = o.get("value")
        value = None if raw in (None, ".") else float(raw)
        rows.append({"date": o["date"], "realtime_start": o["realtime_start"], "value": value})
    return rows


def fetch_series(series_id: str, api_key: str, get=_http_get) -> dict:
    """GET /fred/series metadata; return the single seriess[0] dict."""
    url = _build_url("series", {"series_id": series_id}, api_key)
    payload = json.loads(get(url))
    seriess = payload.get("seriess") or []
    if not seriess:
        raise ValueError(f"no series metadata for {series_id}")
    return seriess[0]


def fetch_observations(series_id: str, api_key: str, start=None, get=_http_get) -> list[dict]:
    """GET /fred/series/observations; return parsed [{date, value}] rows."""
    params = {"series_id": series_id}
    if start:
        params["observation_start"] = start
    url = _build_url("series/observations", params, api_key)
    return parse_observations(json.loads(get(url)))


# FRED per-request caps the vintage fetch must respect (both hit in the live
# 2026-07-07 backfill): /series/vintagedates returns at most 10000 dates/page;
# /series/observations rejects (HTTP 400) a realtime window spanning more than
# 2000 vintage dates and truncates any response at 100000 rows.
_VINTAGE_DATE_PAGE = 10000
_WINDOW_MAX_VINTAGE_DATES = 1500  # under the 2000 cap, with headroom
_OBS_PAGE_LIMIT = 100000


def fetch_vintage_dates(
    series_id: str, api_key: str, get=_http_get, page=_VINTAGE_DATE_PAGE
) -> list[str]:
    """GET /fred/series/vintagedates; return the series' ALFRED vintage
    (publication) dates, sorted ascending, offset-paginated past the page cap.
    A series absent from ALFRED has no vintage dates (the caller returns [])."""
    dates: list[str] = []
    offset = 0
    while True:
        url = _build_url(
            "series/vintagedates",
            {"series_id": series_id, "limit": str(page), "offset": str(offset)},
            api_key,
        )
        got = json.loads(get(url)).get("vintage_dates", [])
        dates.extend(got)
        if len(got) < page:
            break
        offset += page
    return sorted(dates)


def _fetch_vintage_window(
    series_id, api_key, rt_start, rt_end, start, get, page_limit
) -> list[dict]:
    """All vintage rows whose realtime range intersects [rt_start, rt_end],
    offset-paginated past the per-request row cap."""
    rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": series_id,
            "realtime_start": rt_start,
            "realtime_end": rt_end,
            "limit": str(page_limit),
            "offset": str(offset),
        }
        if start:
            params["observation_start"] = start
        url = _build_url("series/observations", params, api_key)
        payload = json.loads(get(url))
        n = len(payload.get("observations", []))
        rows.extend(parse_observation_vintages(payload))
        if n < page_limit:
            break
        offset += page_limit
    return rows


def fetch_observation_vintages(
    series_id: str,
    api_key: str,
    start=None,
    get=_http_get,
    get_vintage_dates=fetch_vintage_dates,
    window_max=_WINDOW_MAX_VINTAGE_DATES,
    page_limit=_OBS_PAGE_LIMIT,
) -> list[dict]:
    """Full ALFRED vintage history as [{date, realtime_start, value}], robust to
    FRED's per-request caps. FRED rejects a realtime window spanning >2000
    vintage dates and truncates any response at 100k rows, so we list the
    series' vintage dates, tile them into realtime windows under the cap, and
    offset-paginate each window. Windows tile FROM THE EARLIEST date so every
    value's true first-publication realtime_start lands unclamped in its owning
    window (FRED clamps realtime_start to a window's left edge — the clamped
    duplicates that produces in later windows are harmless: each restates the
    value genuinely current at that boundary). Rows are deduped by
    (date, realtime_start). A series with no vintage dates returns []."""
    vdates = get_vintage_dates(series_id, api_key, get=get)
    if not vdates:
        return []
    seen: dict[tuple[str, str], dict] = {}
    for i in range(0, len(vdates), window_max):
        window = vdates[i : i + window_max]
        for row in _fetch_vintage_window(
            series_id, api_key, window[0], window[-1], start, get, page_limit
        ):
            seen[(row["date"], row["realtime_start"])] = row
    return list(seen.values())
