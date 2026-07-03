import json
import time
import urllib.error
import urllib.request
from datetime import datetime

ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/daily-index"

_FORM_BUCKETS = {
    "4": "insider", "4/A": "insider",
    "8-K": "event", "8-K/A": "event",
    "SC 13D": "stake", "SC 13D/A": "stake",
    "SC 13G": "stake", "SC 13G/A": "stake",
    "S-1": "offering", "S-1/A": "offering",
    "10-K": "periodic", "10-K/A": "periodic",
    "10-Q": "periodic", "10-Q/A": "periodic",
}


def classify(form: str) -> str:
    """Map a raw SEC form type to a signal bucket."""
    if form in _FORM_BUCKETS:
        return _FORM_BUCKETS[form]
    if form.startswith("424B"):
        return "offering"
    return "other"


def parse_master(text: str) -> list[dict]:
    """Parse a pipe-delimited master.idx into filing dicts. Skips the header
    block (through the '---' divider) and any malformed line."""
    rows = []
    started = False
    for line in text.splitlines():
        if not started:
            if line.startswith("---"):
                started = True
            continue
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        cik, company, form, filed, path = parts
        try:
            cik_i = int(cik)
        except ValueError:
            continue
        accession = path.rsplit("/", 1)[-1]
        if accession.endswith(".txt"):
            accession = accession[:-4]
        rows.append({
            "cik": cik_i,
            "company": company,
            "form": form,
            "filed_date": f"{filed[:4]}-{filed[4:6]}-{filed[6:8]}",
            "path": path,
            "accession": accession,
            "bucket": classify(form),
        })
    return rows


def index_url(index_date: str, base: str = ARCHIVES_BASE) -> str:
    """Build the master.idx URL for a YYYY-MM-DD date, computing its quarter."""
    d = datetime.fromisoformat(index_date)
    qtr = (d.month - 1) // 3 + 1
    return f"{base}/{d.year}/QTR{qtr}/master.{d.strftime('%Y%m%d')}.idx"


TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}


_RETRY_STATUS = frozenset({403, 429, 503})  # SEC throttles with 403 (not 429)
_MAX_ATTEMPTS = 5
_BASE_DELAY = 1.0


def _urlopen(url: str) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def _retry_delay(err, attempt: int, base_delay: float) -> float:
    """Honor a numeric Retry-After header if present, else exponential backoff."""
    headers = getattr(err, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None
    if retry_after is not None and str(retry_after).isdigit():
        return float(retry_after)
    return base_delay * (2 ** (attempt - 1))


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET a URL as text, retrying transient SEC throttling (403/429/503) with
    bounded exponential backoff. Non-retryable errors (e.g. 404) raise at once,
    preserving fetch_daily_index's 404 -> None handling."""
    for attempt in range(1, attempts + 1):
        try:
            return opener(url)
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_STATUS or attempt == attempts:
                raise
            sleep(_retry_delay(e, attempt, base_delay))
    raise AssertionError("unreachable: loop returns or raises")  # pragma: no cover


def fetch_ticker_map(url: str = TICKER_MAP_URL, get=_http_get) -> dict:
    """Load company_tickers.json into {cik: {'ticker':..., 'title':...}}."""
    raw = json.loads(get(url))
    return {int(v["cik_str"]): {"ticker": v["ticker"], "title": v["title"]}
            for v in raw.values()}


def fetch_daily_index(index_date: str, get=_http_get):
    """Fetch + parse master.idx for a date. Returns rows, or None on HTTP 404."""
    try:
        text = get(index_url(index_date))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return parse_master(text)
