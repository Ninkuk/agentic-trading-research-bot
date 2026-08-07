import sqlite3

import pytest

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db, fetch
from sources.screeners.portfolio_screener import db as portfolio_db
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


def _scorer_conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _mini_portfolio(path, snapshots):
    """snapshots: [(captured_at, equity, cash)] written via the real
    portfolio_screener writer, so column drift breaks this test loudly."""
    conn = portfolio_db.connect(str(path))
    portfolio_db.ensure_schema(conn)
    for captured_at, equity, cash in snapshots:
        portfolio_db.write_snapshot(
            conn, captured_at, {"equity": equity, "cash": cash, "buying_power": cash}, []
        )
    conn.close()


def test_harvest_equity_prefers_postclose_window(tmp_path):
    # Both rows land on Phoenix date 2026-07-07: 21:30Z = 14:30 Phoenix
    # (in-window) and 04:22Z NEXT UTC DAY = 21:22 Phoenix (the overnight
    # glitch shape observed in the real db). The in-window row must win
    # even though the glitch row has the later captured_at.
    src = tmp_path / "portfolio.db"
    _mini_portfolio(
        src,
        [
            ("2026-07-07T21:30:00+00:00", 200.4, 200.4),
            ("2026-07-08T04:22:00+00:00", 16.2, 184.15),
        ],
    )
    conn = _scorer_conn(tmp_path)
    fetch.attach_ro(conn, str(src))
    rows = fetch.harvest_equity(conn)
    fetch.detach(conn)
    assert rows == [("2026-07-07", 200.4, 200.4, "2026-07-07T21:30:00+00:00")]


def test_harvest_equity_skips_date_whose_only_snapshot_is_zero_equity(tmp_path):
    # The real 2026-07-13 shape: a single snapshot, INSIDE the post-close
    # window, reading $0.00 equity with cash intact. Harvesting it would put
    # an exactly -100% leg in the permanent ledger and pin every chained
    # window at -100% forever, so the date must drop out entirely (an
    # ordinary ledger gap) while neighbouring dates harvest normally.
    src = tmp_path / "portfolio.db"
    _mini_portfolio(
        src,
        [
            ("2026-07-13T21:30:00+00:00", 0.0, 200.4),
            ("2026-07-14T21:30:00+00:00", 200.4, 200.4),
        ],
    )
    conn = _scorer_conn(tmp_path)
    fetch.attach_ro(conn, str(src))
    rows = fetch.harvest_equity(conn)
    fetch.detach(conn)
    assert rows == [("2026-07-14", 200.4, 200.4, "2026-07-14T21:30:00+00:00")]


def test_harvest_equity_falls_back_to_last_row_of_date(tmp_path):
    # A date with ONLY out-of-window snapshots still harvests (latest wins).
    src = tmp_path / "portfolio.db"
    _mini_portfolio(
        src,
        [
            ("2026-07-09T04:58:00+00:00", 10.8, 189.38),  # 2026-07-08 21:58 Phoenix
            ("2026-07-09T04:20:00+00:00", 11.0, 189.38),  # 2026-07-08 21:20 Phoenix
        ],
    )
    conn = _scorer_conn(tmp_path)
    fetch.attach_ro(conn, str(src))
    rows = fetch.harvest_equity(conn)
    fetch.detach(conn)
    assert rows == [("2026-07-08", 10.8, 189.38, "2026-07-09T04:58:00+00:00")]
