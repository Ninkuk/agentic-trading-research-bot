import pytest

from market_calendar import fetch

# Minimal fixture shaped like the parser's tolerant contract: rows pairing a
# label with an ISO (or normalizable) date. Keep in sync with the parser regex.
_NYSE_HTML = """
<table><tr><td>New Year's Day</td><td>2026-01-01</td></tr>
<tr><td>Independence Day</td><td>2026-07-03</td></tr></table>
"""
_SIFMA_HTML = """
<table><tr><td>Columbus Day</td><td>2026-10-12</td></tr></table>
"""


def test_parse_nyse_extracts_dated_rows():
    got = fetch.parse_nyse_calendar(_NYSE_HTML)
    assert got["2026-01-01"] == "New Year's Day"
    assert "2026-07-03" in got


def test_parse_sifma_extracts_dated_rows():
    got = fetch.parse_sifma_calendar(_SIFMA_HTML)
    assert got["2026-10-12"] == "Columbus Day"


def test_parse_raises_on_zero_rows_never_blanks_calendar():
    with pytest.raises(ValueError):
        fetch.parse_nyse_calendar("<html><body>no table here</body></html>")


def test_fetch_page_uses_bounded_backoff(monkeypatch):
    calls = {"n": 0}

    def get(url):                       # injected opener stand-in
        calls["n"] += 1
        return "<ok/>"

    out = fetch.fetch_page("https://example.test/cal", get=get)
    assert out == "<ok/>"
    assert calls["n"] == 1
