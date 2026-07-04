import gzip
import json
import time
import urllib.error
from datetime import datetime

import http_client

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

_urlopen = http_client.make_opener(
    _UA, limiter=http_client.SEC_RATE_LIMITER, limiter_key=http_client.SEC_HOST_KEY)


def _http_get(url: str, opener=_urlopen, attempts: int = _MAX_ATTEMPTS,
              base_delay: float = _BASE_DELAY, sleep=time.sleep) -> str:
    """GET with bounded backoff, retrying SEC throttling (403/429/503) and
    transient network errors. Non-retryable HTTP errors (e.g. 404) raise at
    once, preserving fetch_daily_index's 404 -> None handling."""
    return http_client.http_get(url, opener, _RETRY_STATUS, attempts,
                                base_delay, sleep)


def fetch_ticker_map(url: str = TICKER_MAP_URL, get=_http_get) -> dict:
    """Load company_tickers.json into {cik: {'ticker':..., 'title':...}}."""
    raw = json.loads(get(url))
    return {int(v["cik_str"]): {"ticker": v["ticker"], "title": v["title"]}
            for v in raw.values()}


def _is_missing_file_403(e: urllib.error.HTTPError) -> bool:
    """The EDGAR archive is S3-backed, so a nonexistent master.idx (weekend,
    market holiday, or before nightly publication) returns 403 with an S3
    ``<Code>AccessDenied</Code>`` XML body rather than 404. Distinguish that
    from a genuine SEC rate-limit 403 (an HTML throttle page) by the S3 marker,
    so the former can be treated like a missing day."""
    try:
        body = e.read()
    except Exception:
        return False
    if (e.headers.get("Content-Encoding") or "").lower() == "gzip":
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError):
            pass
    return b"<Code>AccessDenied</Code>" in body


def fetch_daily_index(index_date: str, get=_http_get):
    """Fetch + parse master.idx for a date. Returns rows, or None when the day
    has no index (HTTP 404, or an S3 AccessDenied 403 for a nonexistent file)
    so the caller can walk back to the previous trading day."""
    try:
        text = get(index_url(index_date))
    except urllib.error.HTTPError as e:
        if e.code == 404 or (e.code == 403 and _is_missing_file_403(e)):
            return None
        raise
    return parse_master(text)
