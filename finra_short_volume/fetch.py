# finra_short_volume/fetch.py
import time
import urllib.error

import http_client

FILES_BASE = "https://cdn.finra.org/equity/regsho/daily"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family (same shape the edgar/cftc fetchers already handle).
# Note: 403 is not retryable for this CDN; it signals "no file for this date".
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def day_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the consolidated-NMS short-volume file for a 'YYYY-MM-DD' date."""
    return f"{base}/CNMSshvol{date.replace('-', '')}.txt"


def _norm_date(raw) -> str | None:
    """YYYYMMDD -> YYYY-MM-DD; None if not exactly 8 digits."""
    raw = (raw or "").strip()
    if len(raw) != 8 or not raw.isdigit():
        return None
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _num(raw, cast):
    """Coerce a stripped string via cast; blank/unparseable -> None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return None


def parse_file(text: str) -> list[dict]:
    """Parse a daily CNMS short-volume file body into rows.

    Pipe-delimited: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market.
    The header line drops naturally (its non-numeric date/volume fail coercion).
    Any footer/summary or malformed line is skipped: a row with fewer than 6
    fields, or missing a symbol, a valid 8-digit date, or a valid total_volume.
    short_ratio = short_volume / total_volume (None when total_volume is 0)."""
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue
        d_raw, symbol, sv, sev, tv, market = (p.strip() for p in parts[:6])
        date = _norm_date(d_raw)
        short_volume = _num(sv, int)
        total_volume = _num(tv, int)
        if not symbol or date is None or short_volume is None or total_volume is None:
            continue
        short_ratio = (short_volume / total_volume) if total_volume else None
        rows.append({
            "symbol": symbol, "date": date,
            "short_volume": short_volume,
            "short_exempt_volume": _num(sev, int),
            "total_volume": total_volume,
            "short_ratio": short_ratio,
            "market": market or None,
        })
    return rows


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET file text with bounded backoff, retrying 403/429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 404) raise at once, so
    fetch_day can map 404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_day(date: str, get=_http_get, opener=None):
    """Download + parse one trading day's CNMS file. Returns list[dict], or
    None on HTTP 403/404 (weekend/holiday/not-yet-published or forbidden)."""
    op = opener if opener is not None else _urlopen
    try:
        text = get(day_url(date), opener=op)
    except urllib.error.HTTPError as e:
        # This CDN returns 403 (not 404) for dates with no file; both mean skip.
        if e.code in (403, 404):
            return None
        raise
    return parse_file(text)
