import urllib.error

import pytest

from sources.screeners.usda_screener import wasde


def _attr_row(idx, name, cells_by_year):
    """One attribute row in the report-XML shape: attributeN element holding
    year groups, each holding month groups whose Cell carries cell_valueN.
    cells_by_year: [(market_year, [month cell values in print order])]."""
    years = ""
    for my, months in cells_by_year:
        mgs = "".join(
            f'<m{idx}_month_group forecast_month{idx}="{fm}">'
            f'<Cell cell_value{idx}="{val}" /></m{idx}_month_group>'
            for fm, val in months
        )
        years += (
            f'<m{idx}_year_group market_year{idx}="{my}">'
            f"<m{idx}_month_group_Collection>{mgs}"
            f"</m{idx}_month_group_Collection></m{idx}_year_group>"
        )
    return (
        f'<m{idx}_attribute_group><attribute{idx} attribute{idx}="{name}">'
        f"<m{idx}_year_group_Collection>{years}</m{idx}_year_group_Collection>"
        f"</attribute{idx}></m{idx}_attribute_group>"
    )


def _matrix(idx, rows):
    return (
        f"<matrix{idx}><m{idx}_attribute_group_Collection>"
        + "".join(rows)
        + f"</m{idx}_attribute_group_Collection></matrix{idx}>"
    )


# sr12-shaped fixture: matrix1 = Feed Grains (MMT), matrix2 = Corn (bushels).
# Corn's Proj. year carries two month groups (May, then current Jun); footnote
# markers and leading spaces on attribute names mirror the live file.
_FEED_GRAIN_XML = (
    '<Report Name="wasde"><sr12>'
    '<Report Name="sr12" Report_Month="June 2026"'
    ' sub_report_title="U.S. Feed Grain and Corn Supply and Use  1/">'
    + _matrix(
        1,
        [
            _attr_row(1, "Ending Stocks", [("2025/26 Est.", [("", "57.2")])]),
            _attr_row(1, "Yield per Harvested Acre", [("2025/26 Est.", [("", "4.3")])]),
        ],
    )
    + _matrix(
        2,
        [
            _attr_row(2, "    Supply, Total", [("2025/26 Est.", [("", "17,787")])]),
            _attr_row(
                2, "    Use, Total  2/", [("2026/27 Proj.", [("May", "16,205"), ("Jun", "16,280")])]
            ),
            _attr_row(
                2, "Ending Stocks", [("2026/27 Proj.", [("May", "1,800"), ("Jun", "1,957")])]
            ),
            _attr_row(2, "Avg. Farm Price ($/bu)  4/", [("2025/26 Est.", [("", "4.20")])]),
        ],
    )
    + "</Report></sr12></Report>"
)


def _by(rows, commodity, metric, market_year=None):
    m = [
        r
        for r in rows
        if r["commodity"] == commodity
        and r["metric"] == metric
        and (market_year is None or r["market_year"] == market_year)
    ]
    return m[0] if m else None


def test_parse_wasde_xml_maps_matrices_to_curated_commodities():
    rows = wasde.parse_wasde_xml(_FEED_GRAIN_XML)
    fg = _by(rows, "Feed Grains", "ending_stocks")
    assert fg["value"] == 57.2 and fg["unit"] == "Million Metric Tons"
    corn = _by(rows, "Corn", "total_supply")
    assert corn["value"] == 17787.0 and corn["unit"] == "Million Bushels"
    assert all(r["region"] == "United States" for r in rows)
    assert all(r["report_date"] == "2026-06-01" for r in rows)


def test_parse_wasde_xml_takes_latest_forecast_month_and_strips_year_flags():
    rows = wasde.parse_wasde_xml(_FEED_GRAIN_XML)
    es = _by(rows, "Corn", "ending_stocks")
    assert es["value"] == 1957.0  # Jun supersedes May
    assert es["market_year"] == "2026/27"  # " Proj." stripped -> stable key
    assert _by(rows, "Corn", "total_use")["value"] == 16280.0
    assert _by(rows, "Feed Grains", "ending_stocks")["market_year"] == "2025/26"


def test_parse_wasde_xml_skips_non_balance_attributes():
    rows = wasde.parse_wasde_xml(_FEED_GRAIN_XML)
    assert all("price" not in r["metric"] and "yield" not in r["metric"] for r in rows)
    assert len([r for r in rows if r["commodity"] == "Corn"]) == 3


def test_parse_wasde_xml_raises_loudly_when_no_us_table_matches():
    with pytest.raises(wasde.WasdeSchemaError):
        wasde.parse_wasde_xml(
            '<Report Name="wasde"><sr08><Report Name="sr08"'
            ' sub_report_title="World Grains" /></sr08></Report>'
        )


def test_parse_wasde_xml_rejects_doctype():
    with pytest.raises(ValueError):
        wasde.parse_wasde_xml('<!DOCTYPE r [<!ENTITY a "b">]><Report />')


_PAGE = (
    '<a href="https://www.usda.gov/oce/commodity/wasde/wasde0726.xml">x</a>'
    '<a href="/oce/commodity/wasde/wasde0626v2.xml">y</a>'
    '<a href="/oce/commodity/wasde/wasde0626v2.xml">dup</a>'
    '<a href="/oce/commodity/wasde/wasde0626v2.pdf">pdf</a>'
)


def test_find_xml_urls_newest_first_absolute_deduped():
    urls = wasde.find_xml_urls(_PAGE)
    assert urls == [
        "https://www.usda.gov/oce/commodity/wasde/wasde0726.xml",
        "https://www.usda.gov/oce/commodity/wasde/wasde0626v2.xml",
    ]


def test_fetch_wasde_falls_back_past_the_prestaged_placeholder():
    def get(url):
        if url == wasde.REPORT_PAGE_URL:
            return _PAGE
        if "0726" in url:  # next month: HTML apology page
            return "<html><body>Please wait</body></html>"
        return _FEED_GRAIN_XML

    rows = wasde.fetch_wasde(get=get)
    assert rows and rows[0]["report_date"] == "2026-06-01"


def test_fetch_wasde_none_when_page_unavailable_or_no_candidates():
    def get_404(url):
        raise urllib.error.HTTPError(url, 404, "nf", {}, None)

    assert wasde.fetch_wasde(get=get_404) is None
    assert wasde.fetch_wasde(get=lambda url: "<html>no links</html>") is None
