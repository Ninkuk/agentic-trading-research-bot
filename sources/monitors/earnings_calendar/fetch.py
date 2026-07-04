"""Forward earnings feed (stockanalysis.com, approved trusted exception) + EDGAR
8-K Item 2.02 confirmation.

Forward dates are decoded via the EXISTING stock_analysis_screener.probe decoder
(do not write a second devalue decoder). EDGAR only *confirms* a date after the
filing posts — it is never the forward source. Licensed data is internal-use only."""
import json
import sys
from datetime import date, timedelta
from statistics import median

from sources.screeners.edgar_screener import fetch as _edgar
from sources.screeners.stock_analysis_screener import probe

EARNINGS_ROUTE = "/stocks/earnings-calendar/"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Fewest historical Item-2.02 filings needed to trust a cadence estimate
# (>= this many dates -> >= min-1 gaps). Two dates (one gap) is too noisy.
_MIN_HISTORY = 3

__all__ = ["EarningsFeedError", "fetch_forward", "timing_to_time",
           "confirm_via_edgar", "item_202_history", "estimate_next_report"]


class EarningsFeedError(Exception):
    """Raised when the forward feed yields zero rows from a non-empty payload."""


def _day_blocks(payload):
    """Per-day blocks (each a dict with a `date` + a symbol list). The live shape
    nests them as earnings[week].days[day]; fall back to the legacy top-level
    `data` list. Top-level `days` (counts only, no symbols) is intentionally
    ignored."""
    if isinstance(payload, dict):
        weeks = payload.get("earnings")
        if isinstance(weeks, list):
            return [day for wk in weeks for day in (wk or {}).get("days") or []]
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
        for sym in block.get("symbols") or block.get("rows") or []:
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


def item_202_history(tickers, get=_edgar._http_get,
                     tmap=_edgar.fetch_ticker_map) -> dict:
    """For each ticker, resolve its CIK and return its historical 8-K Item 2.02
    (earnings) filing dates, in the submissions payload's order (most recent
    first). Per-ticker failures are skipped (type-name-only log); an unmapped
    ticker is omitted. This is the raw material for both confirmation (job a)
    and cadence estimation (job b)."""
    cik_by_ticker = {v["ticker"]: k for k, v in tmap().items()}
    out = {}
    for ticker in tickers:
        cik = cik_by_ticker.get(ticker)
        if cik is None:
            continue
        try:
            payload = json.loads(get(SUBMISSIONS_URL.format(cik=cik)))
        except Exception as e:  # skip-and-continue; never echo str(e)/url
            print(f"warning: EDGAR history {ticker}: {type(e).__name__}",
                  file=sys.stderr)
            continue
        out[ticker] = _item_202_dates(payload)
    return out


def confirm_via_edgar(tickers, scheduled_by_ticker, get=_edgar._http_get,
                      tmap=_edgar.fetch_ticker_map) -> set:
    """For each watched ticker, look for an 8-K Item 2.02 near a scheduled date
    -> confirm that (ticker, date). Returns the set of confirmed (ticker, date)
    pairs. Reuses item_202_history for the per-ticker filing lookup."""
    history = item_202_history(tickers, get=get, tmap=tmap)
    confirmed = set()
    for ticker in tickers:
        filed = history.get(ticker, [])
        for scheduled in scheduled_by_ticker.get(ticker, []):
            if _near(scheduled, filed):
                confirmed.add((ticker, scheduled))
    return confirmed


def _as_date(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


def estimate_next_report(dates, today, min_history: int = _MIN_HISTORY):
    """Project a name's next earnings date from the spacing of its past 8-K
    Item 2.02 filings: the median inter-filing gap added to the most recent
    filing, then rolled forward until strictly after ``today`` so the estimate
    is always the next FUTURE date (a regular filer with a stale last filing
    still gets a sensible projection). Returns an ISO date, or None when there
    are fewer than ``min_history`` usable dates or the cadence is degenerate.
    Median (not mean) resists outliers like 8-K/A amendments (tiny gap) or a
    missed quarter (double gap)."""
    parsed = sorted({d for d in (_as_date(x) for x in dates) if d is not None})
    if len(parsed) < min_history:
        return None
    gap = int(median((b - a).days for a, b in zip(parsed, parsed[1:])))
    if gap <= 0:
        return None
    t = _as_date(today)
    nxt = parsed[-1] + timedelta(days=gap)
    while t is not None and nxt <= t:
        nxt += timedelta(days=gap)
    return nxt.isoformat()
