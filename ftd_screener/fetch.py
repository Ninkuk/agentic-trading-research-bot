# ftd_screener/fetch.py
import calendar

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
        rows.append({
            "cusip": cusip, "settlement_date": date,
            "symbol": symbol or None, "quantity": quantity, "price": p,
            "description": desc or None,
            "dollar_value": (quantity * p) if p is not None else None,
        })
    return rows, trailer_count
