"""CBOE market-statistics + VIX CSV client. Shares only the CBOE-CDN UA and the
bounded-backoff helper with cboe_options — nothing else. Pure CSV parsers,
network-free-testable. Dates come from the CSV, never the wall clock."""
import csv
import io
import time
import urllib.error
from datetime import datetime

import sources.common.http_client as http_client

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

# PCR feed is disabled by default (catalog._ENABLED): this route 403s and Cboe
# no longer publishes a free daily put/call-ratio CSV (verified 2026-07; not on
# FRED release 200 either). URL kept as the documented shape for a future paid
# DataShop source. The VIX/VVIX CDN routes below are live-confirmed.
PCR_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/put_call_ratio.csv"
_VIX_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"

__all__ = ["parse_pcr_csv", "parse_vix_csv", "fetch_pcr", "fetch_vix"]


def _http_get(url, opener=_urlopen, attempts=_MAX_ATTEMPTS, base_delay=_BASE_DELAY,
              sleep=time.sleep):
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay,
                                sleep)


def _num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int(v):
    f = _num(v)
    return int(f) if f is not None else None


def _norm_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_pcr_csv(text) -> list:
    rows = []
    for rec in csv.DictReader(io.StringIO(text)):
        norm = {(k or "").strip().upper().replace(" ", "_").replace("/", "_"): v
                for k, v in rec.items()}
        d = _norm_date(norm.get("DATE"))
        if not d:
            continue
        rows.append({"date": d, "total_pcr": _num(norm.get("TOTAL_PCR")),
                     "equity_pcr": _num(norm.get("EQUITY_PCR")),
                     "index_pcr": _num(norm.get("INDEX_PCR")),
                     "total_volume": _int(norm.get("TOTAL_VOLUME"))})
    return rows


def parse_vix_csv(text) -> list:
    """Parse a CBOE index CSV. Skips any preamble before the DATE header.
    close = CLOSE column, or (single-series files like DATE,VVIX) the last cell."""
    rows = []
    header = None
    for parts in csv.reader(io.StringIO(text)):
        if not parts:
            continue
        upper = [p.strip().upper() for p in parts]
        if header is None:
            if "DATE" in upper:
                header = upper
            continue
        rec = dict(zip(header, parts))
        d = _norm_date(rec.get("DATE"))
        if not d:
            continue
        close = _num(rec.get("CLOSE"))
        if close is None and len(parts) > 1:
            close = _num(parts[-1])              # single-value fallback
        rows.append({"date": d, "open": _num(rec.get("OPEN")),
                     "high": _num(rec.get("HIGH")), "low": _num(rec.get("LOW")),
                     "close": close})
    return rows


def _get_csv(url, get):
    try:
        return get(url)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None                          # skip this feed
        raise


def fetch_pcr(get=_http_get):
    text = _get_csv(PCR_URL, get)
    return None if text is None else parse_pcr_csv(text)


def fetch_vix(feed_id, get=_http_get):
    text = _get_csv(f"{_VIX_BASE}/{feed_id}_History.csv", get)
    return None if text is None else parse_vix_csv(text)
