import pytest

from sources.monitors.market_calendar import fetch

# Fixtures trimmed from the live pages (2026-07-06). Keep in sync with the
# parser regexes: NYSE = year-per-column header + year-less date cells;
# SIFMA = h3/span groups under a "U.S. Holiday Recommendations" section.
_NYSE_HTML = """
<table class="table-data"><thead><tr style="background-color:#71c5e3ff">
<th>Holiday</th><th>2026</th><th>2027</th><th>2028</th></tr></thead><tbody>
<tr><th>New Year&#x2019;s Day</th><td>Thursday, January 1</td>
<td>Friday, January 1</td><td>—*</td></tr>
<tr><th>Independence Day</th><td>Friday, July 3 (Independence Day observed) </td>
<td>Monday, July 5 (Independence Day observed) </td><td>Tuesday, July 4**</td></tr>
<tr><th>Thanksgiving Day</th><td>Thursday, November 26***</td>
<td>Thursday, November 25***</td><td>Thursday, November 23*** </td></tr>
</tbody></table>
"""
_SIFMA_HTML = """
<h2 class="rt-Heading">U.S. Holiday Recommendations</h2>
<h3 class="font-heading">Columbus Day</h3>
<span class="font-label">Monday, October 12, 2026</span>
<h3 class="font-heading">Thanksgiving Day</h3>
<span class="font-label">Thursday, November 26, 2026</span>
<p>Early Close (2:00 p.m. Eastern Time): Friday, November 27, 2026</p>
<h2 class="rt-Heading">U.K. Holiday Recommendations</h2>
<h3 class="font-heading">Boxing Day</h3>
<span class="font-label">Monday, December 28, 2026</span>
"""


def test_parse_nyse_year_columns_and_dateless_cells():
    got = fetch.parse_nyse_calendar(_NYSE_HTML)
    assert got["2026-01-01"] == "New Year’s Day"      # entity unescaped
    assert got["2027-01-01"] == "New Year’s Day"      # year from column header
    assert "2028-01-01" not in got                     # "—*" cell skipped
    assert got["2026-07-03"] == "Independence Day"     # "(observed)" note ok
    assert got["2028-07-04"] == "Independence Day"     # footnote stars ok
    assert got["2028-11-23"] == "Thanksgiving Day"


def test_parse_sifma_us_section_only():
    got = fetch.parse_sifma_calendar(_SIFMA_HTML)
    assert got["2026-10-12"] == "Columbus Day"
    assert got["2026-11-26"] == "Thanksgiving Day"
    assert "2026-12-28" not in got                     # U.K. section excluded


def test_parse_raises_on_zero_rows_never_blanks_calendar():
    with pytest.raises(ValueError):
        fetch.parse_nyse_calendar("<html><body>no table here</body></html>")
    with pytest.raises(ValueError):
        fetch.parse_sifma_calendar("<html><body>no US section</body></html>")
    with pytest.raises(ValueError):  # US heading present but zero entries
        fetch.parse_sifma_calendar("<h2>U.S. Holiday Recommendations</h2>")


def test_fetch_page_uses_bounded_backoff(monkeypatch):
    calls = {"n": 0}

    def get(url):                       # injected opener stand-in
        calls["n"] += 1
        return "<ok/>"

    out = fetch.fetch_page("https://example.test/cal", get=get)
    assert out == "<ok/>"
    assert calls["n"] == 1
