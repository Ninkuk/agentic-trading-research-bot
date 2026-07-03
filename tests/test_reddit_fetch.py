import pytest

from reddit_screener.fetch import fetch_filter, parse_page


def test_parse_page_coerces_types_and_unescapes_name():
    raw = {"count": 2, "pages": 1, "current_page": 1, "results": [
        {"rank": "1", "ticker": "MU", "name": "Micron",
         "mentions": "1147", "upvotes": "5135",
         "rank_24h_ago": "1", "mentions_24h_ago": "951"},
        {"rank": 2, "ticker": "SPY", "name": "SPDR S&amp;P 500 ETF",
         "mentions": 334, "upvotes": 1044,
         "rank_24h_ago": 3, "mentions_24h_ago": 302},
    ]}
    rows, pages = parse_page(raw)
    assert pages == 1
    assert rows[0] == {"ticker": "MU", "name": "Micron", "rank": 1,
                       "mentions": 1147, "upvotes": 5135,
                       "rank_24h_ago": 1, "mentions_24h_ago": 951}
    # HTML entity decoded, and string numerics coerced to int
    assert rows[1]["name"] == "SPDR S&P 500 ETF"
    assert rows[1]["rank"] == 2


def test_parse_page_tolerates_null_24h_fields():
    raw = {"pages": 1, "results": [
        {"rank": 5, "ticker": "NEW", "name": "New Co",
         "mentions": 3, "upvotes": 4,
         "rank_24h_ago": None, "mentions_24h_ago": None},
    ]}
    rows, _ = parse_page(raw)
    assert rows[0]["rank_24h_ago"] is None
    assert rows[0]["mentions_24h_ago"] is None


def test_parse_page_rejects_missing_results():
    with pytest.raises(ValueError):
        parse_page({"pages": 1})


def test_fetch_filter_accumulates_all_pages():
    pages = {
        1: {"pages": 2, "results": [
            {"rank": 1, "ticker": "AAA", "name": "A",
             "mentions": 10, "upvotes": 20,
             "rank_24h_ago": 2, "mentions_24h_ago": 5}]},
        2: {"pages": 2, "results": [
            {"rank": 2, "ticker": "BBB", "name": "B",
             "mentions": 8, "upvotes": 9,
             "rank_24h_ago": 1, "mentions_24h_ago": 12}]},
    }

    def fake_get_page(filter_, page):
        assert filter_ == "all-stocks"
        return pages[page]

    rows = fetch_filter("all-stocks", get_page=fake_get_page)
    assert [r["ticker"] for r in rows] == ["AAA", "BBB"]
