import sqlite3

from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import run as run_mod
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-06T21:10:00+00:00"
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL"}
DAYS = ["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-06"]


def _mini_prices(path, symbols_start):
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    for i, d in enumerate(DAYS):
        conn.execute(
            "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 1, 's')",
            (f"{d}T11:00:00+00:00",),
        )
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for sym, start in symbols_start.items():
            conn.execute(
                "INSERT INTO metrics (snapshot_id, symbol,"
                ' "priceDate", "close") VALUES (?, ?, ?, ?)',
                (sid, sym, d, start + i),
            )
    conn.commit()
    conn.close()


def _mini_composite(dirpath, date="2026-07-01"):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, f"{date}T21:05:00+00:00", 1)
    composite_db.write_signal_values(
        conn,
        sid,
        [
            dict(
                signal_id="stocks_rsi",
                grain="ticker",
                entity="AAPL",
                raw_value=25.0,
                score=1,
                obs_date=date,
                staleness_days=0.0,
            )
        ],
    )
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()


def test_full_cycle(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    out = str(tmp_path / "scorer.db")
    sid, harvested, registered, matured, skipped = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert harvested == 10  # 5 dates x 2 symbols
    assert registered > 0 and skipped == 0
    conn = sqlite3.connect(out)
    # entry is the first close after 07-01 -> 07-02; +5/+10/+21 pending
    # (only 1 fwd day), so nothing matured yet
    assert matured == 0
    assert conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0] > 0
    # header records honest counts
    assert conn.execute("SELECT harvested, registered FROM snapshots").fetchone() == (
        10,
        registered,
    )


def test_rerun_is_idempotent(tmp_path):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    out = str(tmp_path / "scorer.db")
    run_mod.run(out, str(tmp_path), now_iso=NOW)
    sid2, harvested2, registered2, matured2, skipped2 = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert (harvested2, registered2) == (0, 0)  # nothing new
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM registered_snapshots").fetchone()[0] == 1


def test_missing_source_skip_and_continue(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    # no etfs.db, no composite.db
    out = str(tmp_path / "scorer.db")
    sid, harvested, registered, matured, skipped = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert harvested == 5 and registered == 0
    err = capsys.readouterr().out
    # two missing sources -> two skip lines, type names only, no traceback
    assert err.count("FileNotFoundError") == 2
    assert "Traceback" not in err


def test_main_argv(tmp_path, capsys):
    _mini_prices(tmp_path / "stocks.db", {"AAPL": 100.0})
    _mini_prices(tmp_path / "etfs.db", {"SPY": 500.0})
    _mini_composite(tmp_path)
    run_mod.main(["--db", str(tmp_path / "scorer.db"), "--db-dir", str(tmp_path)])
    assert "scorer snapshot" in capsys.readouterr().out
