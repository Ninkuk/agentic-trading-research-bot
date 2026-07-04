# finra_short_interest/fetch.py
import time
import urllib.error

import http_client

FILES_BASE = "https://cdn.finra.org/equity/otcmarket/biweekly"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family only. 403 is NOT retryable here: like the short-volume
# CDN, it signals "no file for this settlement date".
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_MIN_FIELDS = 13

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def settlement_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the FINRA equity short-interest file for a 'YYYY-MM-DD' settlement
    date. Named by settlement date: shrt{YYYYMMDD}.csv (pipe-delimited body)."""
    return f"{base}/shrt{date.replace('-', '')}.csv"


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


def _to_int(raw):
    """Integer, tolerant of a trailing '.0' FINRA may emit for share quantities.
    The header row's non-numeric value fails float() -> None -> line dropped."""
    return _num(raw, lambda v: int(float(v)))


def _to_float(raw):
    return _num(raw, float)


def parse_file(text: str) -> list[dict]:
    """Parse a FINRA equity short-interest file body into rows.

    Pipe-delimited despite the .csv extension. Column order:
      accountingYearMonthNumber | symbolCode | issueName | marketClassCode |
      currentShortPositionQuantity | previousShortPositionQuantity |
      changePercent | averageDailyVolumeQuantity | daysToCoverQuantity |
      revisionFlag | stockSplitFlag | newIssueFlag | settlementDate
    The header line drops naturally (its non-numeric quantity fails coercion).
    Any trailer/short/malformed line is skipped: fewer than 13 fields, or
    missing symbolCode, a valid 8-digit settlementDate, or a parseable
    currentShortPositionQuantity. days_to_cover / change_pct are FINRA-computed
    and stored as-is (blank -> None); they are never re-derived."""
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < _MIN_FIELDS:
            continue
        (_aym, symbol, issue, mclass, cur, prev, chg,
         adv, dtc, rev, _split, _new, sdate) = (p.strip() for p in parts[:13])
        settlement_date = _norm_date(sdate)
        current_short_qty = _to_int(cur)
        if not symbol or settlement_date is None or current_short_qty is None:
            continue
        rows.append({
            "symbol": symbol,
            "issue_name": issue or None,
            "settlement_date": settlement_date,
            "current_short_qty": current_short_qty,
            "previous_short_qty": _to_int(prev),
            "avg_daily_volume": _to_int(adv),
            "days_to_cover": _to_float(dtc),
            "change_pct": _to_float(chg),
            "revision_flag": rev or None,
            "market_class": mclass or None,
        })
    return rows


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET file text with bounded backoff, retrying 429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
    fetch_settlement can map 403/404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_settlement(date: str, get=_http_get, opener=None):
    """Download + parse one settlement's file. Returns list[dict], or None on
    HTTP 403/404 (absent / not-yet-published settlement)."""
    op = opener if opener is not None else _urlopen
    try:
        text = get(settlement_url(date), opener=op)
    except urllib.error.HTTPError as e:
        # CDN returns 403 (not 404) for dates with no file; both mean skip.
        if e.code in (403, 404):
            return None
        raise
    return parse_file(text)
