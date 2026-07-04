import pytest

from sources.screeners.usda_screener import wasde

# Real OCE WASDE tidy-CSV shape (oce-wasde-report-data-2025-12.csv, 16 cols).
# Corn/United States appears in TWO tables: the U.S. domestic balance sheet
# (Million Bushels) and the world table's U.S. row (Million Metric Tons) — same
# (commodity, region, metric, market_year), different unit. The date lives in
# ReleaseDate; ReportDate is human text.
_H = ('"WasdeNumber","ReportDate","ReportTitle","Attribute",'
      '"ReliabilityProjection","Commodity","Region","MarketYear","ProjEstFlag",'
      '"AnnualQuarterFlag","Value","Unit","ReleaseDate","ReleaseTime",'
      '"ForecastYear","ForecastMonth"\n')


def _row(attr, commodity, region, my, value, unit):
    return (f'"666","December 2025","T","{attr}","","{commodity}","{region}",'
            f'"{my}","Proj.","Annual","{value}","{unit}","2025-12-09",'
            f'"12:00:00","2025","12"\n')


WASDE_CSV = _H + "".join([
    _row("Production", "Corn", "United States", "2025/26", "16752.00", "Million Bushels"),
    _row("Ending Stocks", "Corn", "United States", "2025/26", "2029.00", "Million Bushels"),
    _row("Use, Total", "Corn", "United States", "2025/26", "16280.00", "Million Bushels"),
    _row("Domestic, Total", "Corn", "United States", "2025/26", "13080.00", "Million Bushels"),
    _row("Exports", "Corn", "United States", "2025/26", "3200.00", "Million Bushels"),
    _row("Yield per Harvested Acre", "Corn", "United States", "2025/26", "186.00", "Bushels"),
    _row("Ending Stocks", "Corn", "United States", "2025/26", "51.53", "Million Metric Tons"),
    _row("Ending Stocks", "Wheat", "World", "2025/26", "270.5", "Million Metric Tons"),
])


def _by(rows, commodity, region, metric, unit=None):
    m = [r for r in rows if r["commodity"] == commodity
         and r["region"] == region and r["metric"] == metric
         and (unit is None or r["unit"] == unit)]
    return m[0] if m else None


def test_parse_wasde_maps_attributes_and_skips_non_balance():
    rows = wasde.parse_wasde_csv(WASDE_CSV)
    es = _by(rows, "Corn", "United States", "ending_stocks", "Million Bushels")
    assert es["value"] == 2029.0 and es["market_year"] == "2025/26"
    assert es["report_date"] == "2025-12-09"            # from ReleaseDate, not ReportDate
    assert _by(rows, "Corn", "United States", "production")["value"] == 16752.0
    assert _by(rows, "Corn", "United States", "total_use")["value"] == 16280.0
    # "Domestic, Total" (comma) normalizes to domestic_use
    assert _by(rows, "Corn", "United States", "domestic_use")["value"] == 13080.0
    assert _by(rows, "Corn", "United States", "exports")["value"] == 3200.0
    # non-balance attribute (yield) not ingested
    assert all(r["metric"] != "yield" for r in rows)
    assert _by(rows, "Corn", "United States", "yield") is None


def test_parse_wasde_keeps_both_unit_bases_distinct():
    rows = wasde.parse_wasde_csv(WASDE_CSV)
    # the same (commodity, region, metric, market_year) exists in two units
    bushels = _by(rows, "Corn", "United States", "ending_stocks", "Million Bushels")
    mmt = _by(rows, "Corn", "United States", "ending_stocks", "Million Metric Tons")
    assert bushels["value"] == 2029.0 and mmt["value"] == 51.53
    assert _by(rows, "Wheat", "World", "ending_stocks")["value"] == 270.5


def test_parse_wasde_is_header_case_insensitive():
    lower = WASDE_CSV.replace('"Attribute"', '"attribute"').replace(
        '"Commodity"', '"COMMODITY"').replace('"Value"', '"value"')
    rows = wasde.parse_wasde_csv(lower)
    assert _by(rows, "Corn", "United States", "ending_stocks",
               "Million Bushels")["value"] == 2029.0


def test_parse_wasde_raises_loudly_on_missing_required_column():
    broken = WASDE_CSV.replace('"Attribute"', '"SomethingElse"', 1)
    with pytest.raises(wasde.WasdeSchemaError):
        wasde.parse_wasde_csv(broken)


def test_wasde_csv_url_builds_release_path():
    assert wasde.wasde_csv_url(2025, 12).endswith(
        "/oce-wasde-report-data-2025-12.csv")


def test_fetch_wasde_returns_none_on_404():
    import urllib.error

    def get_404(url):
        raise urllib.error.HTTPError(url, 404, "nf", {}, None)

    assert wasde.fetch_wasde(2099, 1, get=get_404) is None
    assert wasde.fetch_wasde(2025, 12, get=lambda url: WASDE_CSV) is not None
