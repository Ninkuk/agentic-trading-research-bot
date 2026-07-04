"""Forward earnings feed (stockanalysis.com, approved trusted exception) + EDGAR
8-K Item 2.02 confirmation.

Forward dates are decoded via the EXISTING stock_analysis_screener.probe decoder
(do not write a second devalue decoder). EDGAR only *confirms* a date after the
filing posts — it is never the forward source. Licensed data is internal-use only."""
import json
import sys
from datetime import date

from edgar_screener import fetch as _edgar
from stock_analysis_screener import probe

EARNINGS_ROUTE = "/stocks/earnings-calendar/"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

__all__ = ["EarningsFeedError", "fetch_forward", "timing_to_time",
           "confirm_via_edgar"]


class EarningsFeedError(Exception):
    """Raised when the forward feed yields zero rows from a non-empty payload."""


def _day_blocks(payload):
    if isinstance(payload, dict):
        return payload.get("data") or []
    if isinstance(payload, list):
        return payload
    return []


def _norm_date(v):
    return (v or "")[:10] or None


def fetch_forward(get=probe.page_data) -> list:
    """Decode the earnings-calendar payload and flatten day-blocks into normalized
    rows. `get(route)` returns the decoded page data (injected in tests). Fails
    loudly on drift."""
    payload = get(EARNINGS_ROUTE)
    rows = []
    for block in _day_blocks(payload):
        d = _norm_date(block.get("date"))
        for sym in block.get("rows", []):
            ticker = sym.get("s")
            if not ticker or not d:
                continue
            rows.append({
                "ticker": ticker, "name": sym.get("n"), "date": d,
                "timing": sym.get("t"), "eps_est": sym.get("e"),
                "eps_growth": sym.get("eg"), "rev_est": sym.get("r"),
                "rev_growth": sym.get("rg"), "mktcap": sym.get("m"),
            })
    if payload and not rows:
        raise EarningsFeedError(
            "no earnings rows decoded from non-empty payload (schema drift?)")
    return rows


def timing_to_time(t):
    """Map the stockanalysis timing code to a human event_time."""
    return {"bmo": "before open", "amc": "after close"}.get(t)


def _item_202_dates(payload) -> list:
    """Filing dates of 8-Ks carrying Item 2.02 (earnings) from a submissions
    payload's filings.recent parallel arrays."""
    recent = (payload.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    items = recent.get("items") or []
    dates = recent.get("filingDate") or []
    out = []
    for i, form in enumerate(forms):
        item = items[i] if i < len(items) else ""
        if form == "8-K" and "2.02" in (item or ""):
            if i < len(dates):
                out.append(dates[i])
    return out


def _near(scheduled, dates, window=3) -> bool:
    """True if any filing date is within +/-window days of the scheduled date."""
    try:
        s = date.fromisoformat(scheduled)
    except ValueError:
        return False
    for d in dates:
        try:
            if abs((date.fromisoformat(str(d)[:10]) - s).days) <= window:
                return True
        except ValueError:
            continue
    return False


def confirm_via_edgar(tickers, scheduled_by_ticker, get=_edgar._http_get,
                      tmap=_edgar.fetch_ticker_map) -> set:
    """For each watched ticker, resolve its CIK and look for an 8-K Item 2.02
    near a scheduled date -> confirm that (ticker, date). Per-ticker failures are
    skipped (type-name-only log); an unmapped ticker is skipped. Returns the set
    of confirmed (ticker, date) pairs."""
    cik_by_ticker = {v["ticker"]: k for k, v in tmap().items()}
    confirmed = set()
    for ticker in tickers:
        cik = cik_by_ticker.get(ticker)
        if cik is None:
            continue
        try:
            payload = json.loads(get(SUBMISSIONS_URL.format(cik=cik)))
        except Exception as e:  # skip-and-continue; never echo str(e)/url
            print(f"warning: EDGAR confirm {ticker}: {type(e).__name__}",
                  file=sys.stderr)
            continue
        filed = _item_202_dates(payload)
        for scheduled in scheduled_by_ticker.get(ticker, []):
            if _near(scheduled, filed):
                confirmed.add((ticker, scheduled))
    return confirmed
