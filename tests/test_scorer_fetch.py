import sqlite3

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import fetch
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-06T21:05:00+00:00"
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL"}


def _mini_stocks(tmp_path):
    path = tmp_path / "stocks.db"
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 2, 's')", (NOW,)
    )
    conn.executemany(
        'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close") VALUES (1, ?, ?, ?)',
        [("AAPL", "2026-07-02", 200.0), ("XOM", "2026-07-02", 100.0), ("NULLED", None, None)],
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
