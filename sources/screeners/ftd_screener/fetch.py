# ftd_screener/fetch.py
import calendar
import io
import urllib.error
import urllib.request
import zipfile

import sources.common.http_client as http_client
from sources.common.http_client import DEFAULT_UA, RETRY_SEC
from sources.common.parse import coerce, yyyymmdd_to_iso

FILES_BASE = "https://www.sec.gov/files/data/fails-deliver-data"


def period_url(period: str, base: str = FILES_BASE) -> str:
    """URL of the ZIP for a period id like '202505a'."""
    return f"{base}/cnsfails{period}.zip"


def settlement_bounds(period: str) -> tuple[str, str]:
    """(start, end) YYYY-MM-DD dates a period covers. 'a' -> 01..15,
    'b' -> 16..last-day-of-month."""
    year, month, half = int(period[:4]), int(period[4:6]), period[6]
    last = calendar.monthrange(year, month)[1]
    if half == "a":
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-15"
    return f"{year:04d}-{month:02d}-16", f"{year:04d}-{month:02d}-{last:02d}"


def parse_file(text: str) -> tuple[list[dict], int | None]:
    """Parse an FTD file body into (rows, trailer_count).

    Pipe-delimited: SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY|DESCRIPTION|PRICE.
    Stops at the first 'Trailer' line (capturing 'Trailer record count N').
    The header line is dropped naturally (its non-numeric date/quantity fail
    coercion). Rows missing a CUSIP, a valid date, or a valid quantity are
    skipped. dollar_value = quantity * price (None if price missing)."""
    rows: list[dict] = []
    trailer_count: int | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("Trailer"):
            if "record count" in line:
                trailer_count = coerce(line.rsplit(" ", 1)[-1], int)
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue
        settle, cusip, symbol, qty, desc, price = (p.strip() for p in parts[:6])
        date = yyyymmdd_to_iso(settle)
        quantity = coerce(qty, int)
        if not cusip or date is None or quantity is None:
            continue
        p = coerce(price, float)
        rows.append(
            {
                "cusip": cusip,
                "settlement_date": date,
                "symbol": symbol or None,
                "quantity": quantity,
                "price": p,
                "description": desc or None,
                "dollar_value": (quantity * p) if p is not None else None,
            }
        )
    return rows, trailer_count


_UA = DEFAULT_UA
_RETRY_STATUS = RETRY_SEC  # SEC throttles with 403 (like EDGAR)


# Pay into the same process-wide SEC bucket as edgar/fundamentals (per-IP cap
# is domain-wide, not per-host) — see http_client.SEC_RATE_LIMITER.
_urlopen = http_client.make_opener(
    _UA, decode=False, limiter=http_client.SEC_RATE_LIMITER, limiter_key=http_client.SEC_HOST_KEY
)


# GET raw bytes with bounded backoff, retrying SEC throttling (403/429/503)
# and transient network errors. Non-retryable HTTP errors (e.g. 404) raise at
# once, preserving fetch_period's 404 -> None handling.
_http_get = http_client.make_getter(_urlopen, _RETRY_STATUS)


def fetch_period(period: str, get=_http_get, opener=None):
    """Download + parse one period's ZIP. Returns (rows, trailer_count), or
    None on HTTP 404 (period not yet published). Reads whichever single member
    the archive contains; decodes with errors='replace'."""
    op = opener if opener is not None else _urlopen
    try:
        blob = get(period_url(period), opener=op)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        if not names:  # malformed/empty archive -> caller's skip-and-continue
            raise ValueError(f"empty archive for period {period}")
        text = zf.read(names[0]).decode("utf-8", "replace")
    return parse_file(text)
