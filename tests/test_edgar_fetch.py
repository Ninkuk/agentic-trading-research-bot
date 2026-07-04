from sources.screeners.edgar_screener.fetch import classify, index_url, parse_master

MASTER = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    Jun 2, 2025
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/

CIK|Company Name|Form Type|Date Filed|File Name
--------------------------------------------------------------------------------
1000623|Mativ Holdings, Inc.|4|20250602|edgar/data/1000623/0001562180-25-004291.txt
1318605|Tesla, Inc.|8-K|20250602|edgar/data/1318605/0001318605-25-000123.txt
789019|MICROSOFT CORP|424B5|20250602|edgar/data/789019/0000789019-25-000045.txt
garbage_line_without_pipes
999|Missing Path Co|10-Q|20250602
"""


def test_classify_buckets():
    assert classify("4") == "insider"
    assert classify("4/A") == "insider"
    assert classify("8-K") == "event"
    assert classify("SC 13D") == "stake"
    assert classify("SC 13G/A") == "stake"
    assert classify("S-1") == "offering"
    assert classify("424B5") == "offering"   # prefix match
    assert classify("424B2") == "offering"
    assert classify("10-K") == "periodic"
    assert classify("3") == "other"


def test_parse_master_extracts_valid_rows_only():
    rows = parse_master(MASTER)
    assert len(rows) == 3          # 2 malformed lines skipped
    first = rows[0]
    assert first["cik"] == 1000623
    assert first["company"] == "Mativ Holdings, Inc."
    assert first["form"] == "4"
    assert first["bucket"] == "insider"
    assert first["filed_date"] == "2025-06-02"
    assert first["accession"] == "0001562180-25-004291"
    assert first["path"] == "edgar/data/1000623/0001562180-25-004291.txt"


def test_parse_master_classifies_each_row():
    buckets = [r["bucket"] for r in parse_master(MASTER)]
    assert buckets == ["insider", "event", "offering"]


def test_index_url_computes_quarter():
    assert index_url("2025-06-02").endswith("/2025/QTR2/master.20250602.idx")
    assert index_url("2025-01-15").endswith("/2025/QTR1/master.20250115.idx")
    assert index_url("2025-12-31").endswith("/2025/QTR4/master.20251231.idx")


import json
import urllib.error

from sources.screeners.edgar_screener.fetch import fetch_daily_index, fetch_ticker_map


def test_fetch_ticker_map_indexes_by_cik():
    raw = json.dumps({
        "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    })
    tmap = fetch_ticker_map(get=lambda url: raw)
    assert tmap[320193] == {"ticker": "AAPL", "title": "Apple Inc."}
    assert tmap[1045810]["ticker"] == "NVDA"


def test_fetch_daily_index_parses_when_present():
    def fake_get(url):
        assert url.endswith("/2025/QTR2/master.20250602.idx")
        return MASTER
    rows = fetch_daily_index("2025-06-02", get=fake_get)
    assert [r["bucket"] for r in rows] == ["insider", "event", "offering"]


def test_fetch_daily_index_returns_none_on_404():
    def fake_get(url):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
    assert fetch_daily_index("2025-06-01", get=fake_get) is None


def test_fetch_daily_index_reraises_non_404():
    def fake_get(url):
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)
    try:
        fetch_daily_index("2025-06-01", get=fake_get)
        assert False, "expected HTTPError to propagate"
    except urllib.error.HTTPError as e:
        assert e.code == 500


import gzip
import io

# SEC serves the EDGAR archive from S3: a master.idx that does not exist
# (weekend/holiday/before nightly publication) returns 403 with an S3
# AccessDenied XML body, NOT 404. It must behave like 404 so run()'s walk-back
# to the previous trading day proceeds instead of aborting.
_ACCESS_DENIED = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<Error><Code>AccessDenied</Code><Message>Access Denied</Message>'
    b'<RequestId>2N0SQHAW7Q1SEM6V</RequestId></Error>')


def _s3_403(url, body, content_encoding=None):
    hdrs = {"Content-Type": "application/xml"}
    if content_encoding:
        hdrs["Content-Encoding"] = content_encoding
    return urllib.error.HTTPError(url, 403, "Forbidden", hdrs, io.BytesIO(body))


def test_fetch_daily_index_returns_none_on_missing_file_403():
    def fake_get(url):
        raise _s3_403(url, _ACCESS_DENIED)
    assert fetch_daily_index("2026-07-03", get=fake_get) is None


def test_fetch_daily_index_returns_none_on_gzipped_missing_file_403():
    # The real S3 error body arrives gzip-encoded.
    def fake_get(url):
        raise _s3_403(url, gzip.compress(_ACCESS_DENIED), content_encoding="gzip")
    assert fetch_daily_index("2026-07-03", get=fake_get) is None


def test_fetch_daily_index_reraises_throttle_403():
    # A genuine SEC rate-limit 403 is an HTML throttle page with no S3
    # AccessDenied marker and must still propagate.
    def fake_get(url):
        raise urllib.error.HTTPError(
            url, 403, "Forbidden", {"Content-Type": "text/html"},
            io.BytesIO(b"<html>Request Rate Threshold Exceeded</html>"))
    try:
        fetch_daily_index("2026-07-03", get=fake_get)
        assert False, "expected throttle 403 to propagate"
    except urllib.error.HTTPError as e:
        assert e.code == 403


def _http_error(code, retry_after=None):
    hdrs = {"Retry-After": retry_after} if retry_after is not None else {}
    return urllib.error.HTTPError("http://x", code, "err", hdrs, None)


def test_http_get_retries_on_403_then_succeeds():
    from sources.screeners.edgar_screener.fetch import _http_get
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http_error(403)
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert calls["n"] == 3
    assert slept == [1.0, 2.0]   # exponential backoff before attempts 2 and 3


def test_http_get_gives_up_after_attempts_on_persistent_403():
    from sources.screeners.edgar_screener.fetch import _http_get
    slept = []

    def opener(url):
        raise _http_error(403)

    try:
        _http_get("http://x", opener=opener, attempts=4, base_delay=1.0,
                  sleep=slept.append)
        assert False, "expected HTTPError after exhausting retries"
    except urllib.error.HTTPError as e:
        assert e.code == 403
    assert len(slept) == 3   # attempts-1 backoffs, then raise


def test_http_get_does_not_retry_404():
    from sources.screeners.edgar_screener.fetch import _http_get
    slept = []

    def opener(url):
        raise _http_error(404)

    try:
        _http_get("http://x", opener=opener, sleep=slept.append)
        assert False, "404 must raise immediately"
    except urllib.error.HTTPError as e:
        assert e.code == 404
    assert slept == []   # no retry on 404


def test_http_get_retries_on_urlerror_then_succeeds():
    # Transient non-HTTP failures (connection reset, DNS) must also be retried,
    # not just HTTP status codes.
    from sources.screeners.edgar_screener.fetch import _http_get
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("connection reset")
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert calls["n"] == 3
    assert slept == [1.0, 2.0]


def test_http_get_retries_on_timeout():
    # A socket read timeout is a TimeoutError, not an HTTPError/URLError.
    from sources.screeners.edgar_screener.fetch import _http_get
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("read timed out")
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [1.0]


def test_http_get_gives_up_after_persistent_urlerror():
    from sources.screeners.edgar_screener.fetch import _http_get
    slept = []

    def opener(url):
        raise urllib.error.URLError("connection reset")

    try:
        _http_get("http://x", opener=opener, attempts=3, base_delay=1.0,
                  sleep=slept.append)
        assert False, "expected URLError after exhausting retries"
    except urllib.error.URLError:
        pass
    assert len(slept) == 2   # attempts-1 backoffs, then raise


def test_http_get_honors_retry_after_header():
    from sources.screeners.edgar_screener.fetch import _http_get
    calls = {"n": 0}
    slept = []

    def opener(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429, retry_after="7")
        return "OK"

    out = _http_get("http://x", opener=opener, base_delay=1.0, sleep=slept.append)
    assert out == "OK"
    assert slept == [7.0]   # Retry-After header overrides exponential backoff
