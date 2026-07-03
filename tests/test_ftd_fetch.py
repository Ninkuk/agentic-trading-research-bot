# tests/test_ftd_fetch.py
import pytest

from ftd_screener.fetch import (
    parse_file, period_url, settlement_bounds,
)

SAMPLE = (
    "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n"
    "20250501|B38564108|CMBT|111|CMB.TECH NV (BEL)|9.51\n"
    "20250502|000000000|BLANKQTY||CORP|\n"          # blank quantity -> skipped
    "20250502|C00948205|AGRI|12336|AGRIFORCE|2.13\n"
    "20250505||NOCUSIP|50|NO CUSIP CO|1.00\n"        # blank cusip -> skipped
    "Trailer record count 2\n"
    "Trailer total quantity of shares 12447\n"
)


def test_parse_file_maps_and_coerces():
    rows, trailer = parse_file(SAMPLE)
    assert trailer == 2
    assert len(rows) == 2                       # blank-qty and blank-cusip skipped
    assert rows[0] == {
        "cusip": "B38564108", "settlement_date": "2025-05-01",
        "symbol": "CMBT", "quantity": 111, "price": 9.51,
        "description": "CMB.TECH NV (BEL)",
        "dollar_value": pytest.approx(111 * 9.51),
    }
    assert rows[1]["cusip"] == "C00948205"
    assert rows[1]["dollar_value"] == pytest.approx(12336 * 2.13)


def test_parse_file_blank_price_gives_none():
    rows, trailer = parse_file("20250501|X1|SYM|100|A NAME|\n")
    assert trailer is None                      # no trailer line present
    assert rows[0]["price"] is None
    assert rows[0]["dollar_value"] is None


def test_parse_file_header_row_is_dropped():
    # header's SETTLEMENT DATE is non-numeric -> filtered; QUANTITY cell non-int too
    rows, _ = parse_file(
        "SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n")
    assert rows == []


def test_period_url():
    assert period_url("202505a") == (
        "https://www.sec.gov/files/data/fails-deliver-data/cnsfails202505a.zip")


def test_settlement_bounds_first_half():
    assert settlement_bounds("202505a") == ("2025-05-01", "2025-05-15")


def test_settlement_bounds_second_half_uses_month_end():
    assert settlement_bounds("202502b") == ("2025-02-16", "2025-02-28")  # non-leap
    assert settlement_bounds("202405b") == ("2024-05-16", "2024-05-31")
