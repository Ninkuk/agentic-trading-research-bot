import sqlite3

import pytest

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import fetch
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-06T21:05:00+00:00"
# stockanalysis: `price` is the close FOR priceDate; `close` is the PREVIOUS
# session's close. The fixture keeps them distinct so a harvester reading the
# wrong one cannot pass.
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL", "price": "REAL"}


def _mini_stocks(tmp_path):
    path = tmp_path / "stocks.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 2, 's')", (NOW,)
    )
    conn.executemany(
        'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price")'
        " VALUES (1, ?, ?, ?, ?)",
        [
            # close = prior session, price = the close for priceDate
            ("AAPL", "2026-07-02", 199.0, 200.0),
            ("XOM", "2026-07-02", 99.0, 100.0),
            ("NULLED", None, None, None),
        ],
    )
    conn.commit()
    conn.close()
    return str(path)


def _stocks_with_unsettled_row(tmp_path):
    """Snapshot A (Phoenix 07-03) reports a SETTLED 07-02 close. Snapshot B is
    captured the evening of 07-06 (04:12Z on 07-07 = 21:12 Phoenix on 07-06) and
    reports an UNSETTLED same-day price for priceDate 07-06."""
    path = tmp_path / "unsettled.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.executemany(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 1, 's')",
        [("2026-07-03T11:00:00+00:00",), ("2026-07-07T04:12:00+00:00",)],
    )
    conn.executemany(
        'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price")'
        " VALUES (?, ?, ?, ?, ?)",
        [
            (1, "AAPL", "2026-07-02", 199.0, 200.0),  # settled
            (2, "AAPL", "2026-07-06", 200.0, 205.0),  # unsettled same-day
        ],
    )
    conn.commit()
    conn.close()
    return str(path)


def _mini_composite(tmp_path):
    path = tmp_path / "composite.db"
    conn = composite_db.connect(str(path))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, NOW, 2)
    composite_db.write_signal_values(
        conn,
        sid,
        [
            dict(
                signal_id="si_days_to_cover",
                grain="ticker",
                entity="AAPL",
                raw_value=12.0,
                score=2,
                obs_date="2026-06-15",
                staleness_days=21.0,
            ),
            dict(
                signal_id="portfolio_holding",
                grain="ticker",
                entity="XOM",
                raw_value=10.0,
                score=0,
                obs_date="2026-07-06",
                staleness_days=0.0,
            ),
            dict(
                signal_id="fred_curve",
                grain="market",
                entity="*",
                raw_value=0.35,
                score=0,
                obs_date="2026-07-02",
                staleness_days=4.0,
            ),
        ],
    )
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    # a phase-2-failed snapshot: header but no regime row
    composite_db.write_snapshot(conn, "2026-07-07T21:05:00+00:00", 2)
    conn.commit()
    conn.close()
    return str(path), sid


def test_harvest_prices_skips_nulls(tmp_path):
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, _mini_stocks(tmp_path))
    rows = sorted(fetch.harvest_prices(conn))
    assert rows == [("AAPL", "2026-07-02", 200.0), ("XOM", "2026-07-02", 100.0)]


def test_harvest_prices_reads_price_not_previous_close(tmp_path):
    """Regression: `close` is stockanalysis's PREVIOUS close. Harvesting it
    stamped each close with the next trading day's date, handing entry_for()
    the composite date's own close (look-ahead). price=200/100, close=199/99."""
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, _mini_stocks(tmp_path))
    closes = {sym: close for sym, _, close in fetch.harvest_prices(conn)}
    assert closes == {"AAPL": 200.0, "XOM": 100.0}
    assert 199.0 not in closes.values(), "harvested the previous close"


def test_harvest_prices_excludes_unsettled_same_day_price(tmp_path):
    """A snapshot taken the evening of D reports an unsettled `price` for
    priceDate=D. Only snapshots from a LATER Phoenix day are trustworthy.
    The fixture's 04:12Z capture is 21:12 Phoenix the PREVIOUS day, so it must
    not contribute — a naive UTC date-slice would wrongly keep it."""
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, _stocks_with_unsettled_row(tmp_path))
    rows = fetch.harvest_prices(conn)
    assert rows == [("AAPL", "2026-07-02", 200.0)]
    assert all(d != "2026-07-06" for _, d, _ in rows), "harvested an unsettled same-day price"


def test_harvest_prices_is_deterministic_across_duplicate_settled_snapshots(tmp_path):
    """Several settled snapshots can carry the same priceDate. INSERT OR IGNORE
    freezes whichever row appears first, so the pick must not depend on scan
    order: MIN(snapshot_id) wins."""
    path = tmp_path / "dupes.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.executemany(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 1, 's')",
        [("2026-07-03T11:00:00+00:00",), ("2026-07-04T11:00:00+00:00",)],
    )
    conn.executemany(
        'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price")'
        " VALUES (?, ?, ?, ?, ?)",
        [(1, "AAPL", "2026-07-02", 199.0, 200.0), (2, "AAPL", "2026-07-02", 199.0, 111.0)],
    )
    conn.commit()
    conn.close()
    c = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(c, str(path))
    assert fetch.harvest_prices(c) == [("AAPL", "2026-07-02", 200.0)]


def test_harvest_prices_raises_when_price_column_absent(tmp_path):
    """SQLite resolves an unknown double-quoted identifier to a string literal,
    so a missing `price` column would silently harvest the text 'price' into
    the permanent ledger. It must raise instead."""
    path = tmp_path / "noprice.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, {"priceDate": "TEXT", "close": "REAL"})
    conn.commit()
    conn.close()
    c = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(c, str(path))
    with pytest.raises(ValueError, match="price"):
        fetch.harvest_prices(c)


def test_reads_composite_only_regimed_snapshots(tmp_path):
    path, sid = _mini_composite(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    assert fetch.read_snapshots(conn) == [(sid, "2026-07-06")]
    tickers = fetch.read_ticker_scores(conn, sid)
    assert {t["symbol"] for t in tickers} == {"AAPL", "XOM"}
    sigs = fetch.read_signal_rows(conn, sid)
    assert [s["signal_id"] for s in sigs] == ["si_days_to_cover"]  # no score-0
    assert fetch.read_regime(conn, sid) == "mixed"
