# ftd_screener/fetch.py
import calendar
import io
import time
import urllib.error
import urllib.request
import zipfile

import sources.common.http_client as http_client

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
                trailer_count = _num(line.rsplit(" ", 1)[-1], int)
            continue
        parts = line.split("|")
        if len(parts) < 6:
            continue
        settle, cusip, symbol, qty, desc, price = (p.strip() for p in parts[:6])
        date = _norm_date(settle)
        quantity = _num(qty, int)
        if not cusip or date is None or quantity is None:
            continue
        p = _num(price, float)
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


_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({403, 429, 503})  # SEC throttles with 403 (like EDGAR)
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0


def _bytes_opener(headers: dict, timeout: int = 60, *, limiter=None, limiter_key: str = ""):
    """opener(url)->bytes for binary (ZIP) downloads. Unlike
    http_client.make_opener, does NOT decode the body. When a ``limiter`` is
    supplied, pays ``limiter.acquire(limiter_key)`` before each request."""

    def opener(url: str) -> bytes:
        if limiter is not None:
            limiter.acquire(limiter_key)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    return opener


# Pay into the same process-wide SEC bucket as edgar/fundamentals (per-IP cap
# is domain-wide, not per-host) — see http_client.SEC_RATE_LIMITER.
_urlopen = _bytes_opener(
    _UA, limiter=http_client.SEC_RATE_LIMITER, limiter_key=http_client.SEC_HOST_KEY
)


def _http_get(
    url: str,
    opener=_urlopen,
    attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    sleep=time.sleep,
) -> bytes:
    """GET raw bytes with bounded backoff, retrying SEC throttling (403/429/503)
    and transient network errors. Non-retryable HTTP errors (e.g. 404) raise at
    once, preserving fetch_period's 404 -> None handling."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts, base_delay, sleep)


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
