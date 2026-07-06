"""CBOE market-statistics + VIX CSV client. Shares only the CBOE-CDN UA and the
bounded-backoff helper with cboe_options — nothing else. Pure parsers,
network-free-testable. Dates come from the source, never the wall clock."""
import csv
import io
import json
import re
import time
import urllib.error
from datetime import datetime

import sources.common.http_client as http_client

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_urlopen = http_client.make_opener(_UA)

# Cboe discontinued the free put/call-ratio CSV (the old CDN route 403s), but
# the daily market-statistics page server-renders the same ratios + volumes
# into its Next.js RSC stream — that page IS the PCR feed now (live-verified
# 2026-07; history back to 2019-10-07 via ?dt=YYYY-MM-DD). The VIX/VVIX CDN
# CSV routes below are unchanged and live-confirmed.
PCR_URL = "https://www.cboe.com/markets/us/options/market-statistics/daily/"
_VIX_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"

__all__ = ["parse_pcr_page", "parse_vix_csv", "fetch_pcr", "fetch_vix"]


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


# One RSC flight chunk: self.__next_f.push([1,"<escaped JS string>"])
_RSC_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_SELECTED_DATE = re.compile(r'"selectedDate":"(\d{4}-\d{2}-\d{2})"')


def _rsc_stream(html) -> str:
    """Reassemble the page's RSC flight stream: each push payload is a JS
    string literal (arbitrarily chunked), decoded and concatenated in order."""
    return "".join(json.loads(f'"{m}"')
                   for m in _RSC_PUSH.findall(html or ""))


def _balanced_object(s, start):
    """The JSON text of the object opening at s[start] ('{'), string-aware."""
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None


def parse_pcr_page(html) -> list:
    """Extract the day's put/call ratios + total volume from the daily
    market-statistics page's server-rendered "optionsData" payload. Returns a
    single-row list (the page shows one session), or [] when the payload is
    absent (maintenance shell, layout change)."""
    stream = _rsc_stream(html)
    key = stream.find('"optionsData"')
    date_m = _SELECTED_DATE.search(stream)
    if key < 0 or not date_m:
        return []
    obj_start = stream.find("{", key + len('"optionsData"'))
    text = _balanced_object(stream, obj_start) if obj_start >= 0 else None
    if text is None:
        return []
    try:
        od = json.loads(text)
    except ValueError:
        return []
    ratios = {(r.get("name") or "").upper(): _num(r.get("value"))
              for r in od.get("ratios") or []}
    volume = next((_int(r.get("total"))
                   for r in od.get("SUM OF ALL PRODUCTS") or []
                   if (r.get("name") or "").upper() == "VOLUME"), None)
    return [{"date": date_m.group(1),
             "total_pcr": ratios.get("TOTAL PUT/CALL RATIO"),
             "equity_pcr": ratios.get("EQUITY PUT/CALL RATIO"),
             "index_pcr": ratios.get("INDEX PUT/CALL RATIO"),
             "total_volume": volume}]


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


def fetch_pcr(get=_http_get, dt=None):
    """Fetch the daily-stats page (latest session, or a past one via dt) and
    parse its PCR row. None on 403/404 -> the run skips the feed."""
    url = PCR_URL + (f"?dt={dt}" if dt else "")
    text = _get_csv(url, get)
    return None if text is None else parse_pcr_page(text)


def fetch_vix(feed_id, get=_http_get):
    text = _get_csv(f"{_VIX_BASE}/{feed_id}_History.csv", get)
    return None if text is None else parse_vix_csv(text)
