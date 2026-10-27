# finra_short_volume/fetch.py
import urllib.error

import sources.common.http_client as http_client
from sources.common.http_client import DEFAULT_UA, RETRY_CDN
from sources.common.parse import coerce, yyyymmdd_to_iso

FILES_BASE = "https://cdn.finra.org/equity/regsho/daily"

_UA = DEFAULT_UA
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family (same shape the edgar/cftc fetchers already handle).
# Note: 403 is not retryable for this CDN; it signals "no file for this date".
_RETRY_STATUS = RETRY_CDN

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def day_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the consolidated-NMS short-volume file for a 'YYYY-MM-DD' date."""
    return f"{base}/CNMSshvol{date.replace('-', '')}.txt"


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
        date = yyyymmdd_to_iso(d_raw)
        short_volume = coerce(sv, int)
        total_volume = coerce(tv, int)
        if not symbol or date is None or short_volume is None or total_volume is None:
            continue
        short_ratio = (short_volume / total_volume) if total_volume else None
        rows.append(
            {
                "symbol": symbol,
                "date": date,
                "short_volume": short_volume,
                "short_exempt_volume": coerce(sev, int),
                "total_volume": total_volume,
                "short_ratio": short_ratio,
                "market": market or None,
            }
        )
    return rows


# GET file text with bounded backoff, retrying 429/503 and transient
# network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
# fetch_day can map 403/404 -> None (this CDN 403s for dates with no file).
_http_get = http_client.make_getter(_urlopen, _RETRY_STATUS)


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
