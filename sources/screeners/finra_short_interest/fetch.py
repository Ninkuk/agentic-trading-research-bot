# finra_short_interest/fetch.py
import time
import urllib.error
from datetime import date as _date

import sources.common.http_client as http_client

FILES_BASE = "https://cdn.finra.org/equity/otcmarket/biweekly"

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
# CDN sits behind Cloudflare; a descriptive UA avoids bot-rule blocks. Retry the
# throttling/5xx family only. 403 is NOT retryable here: like the short-volume
# CDN, it signals "no file for this settlement date".
_RETRY_STATUS = frozenset({429, 503})
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0
_MIN_FIELDS = 14

_urlopen = http_client.make_opener(_UA)  # opener(url) -> decoded UTF-8 text


def settlement_url(date: str, base: str = FILES_BASE) -> str:
    """URL of the FINRA equity short-interest file for a 'YYYY-MM-DD' settlement
    date. Named by settlement date: shrt{YYYYMMDD}.csv (pipe-delimited body)."""
    return f"{base}/shrt{date.replace('-', '')}.csv"


def _norm_iso(raw) -> str | None:
    """Validate a 'YYYY-MM-DD' settlement date (FINRA emits ISO dates in-file);
    return it normalized, or None if it is not a valid ISO date."""
    raw = (raw or "").strip()
    try:
        return _date.fromisoformat(raw).isoformat()
    except (TypeError, ValueError):
        return None


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

    Pipe-delimited despite the .csv extension. Live column order (14 fields,
    confirmed against cdn.finra.org shrt files 2026-07):
      0 accountingYearMonthNumber | 1 symbolCode | 2 issueName |
      3 issuerServicesGroupExchangeCode | 4 marketClassCode |
      5 currentShortPositionQuantity | 6 previousShortPositionQuantity |
      7 stockSplitFlag | 8 averageDailyVolumeQuantity | 9 daysToCoverQuantity |
      10 revisionFlag | 11 changePercent | 12 changePreviousNumber |
      13 settlementDate (already 'YYYY-MM-DD')
    The header line drops naturally (its non-numeric quantity fails coercion).
    Any trailer/short/malformed line is skipped: fewer than 14 fields, or
    missing symbolCode, a valid ISO settlementDate, or a parseable
    currentShortPositionQuantity. days_to_cover / change_pct are FINRA-computed
    and stored as-is (blank -> None); they are never re-derived."""
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < _MIN_FIELDS:
            continue
        (
            _aym,
            symbol,
            issue,
            _exch,
            mclass,
            cur,
            prev,
            _split,
            adv,
            dtc,
            rev,
            chg,
            _chgprev,
            sdate,
        ) = (p.strip() for p in parts[:14])
        settlement_date = _norm_iso(sdate)
        current_short_qty = _to_int(cur)
        if not symbol or settlement_date is None or current_short_qty is None:
            continue
        rows.append(
            {
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
            }
        )
    return rows


def _http_get(
    url: str,
    opener=_urlopen,
    attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    sleep=time.sleep,
) -> str:
    """GET file text with bounded backoff, retrying 429/503 and transient
    network errors. Non-retryable HTTP errors (e.g. 403/404) raise at once, so
    fetch_settlement can map 403/404 -> None."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


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
