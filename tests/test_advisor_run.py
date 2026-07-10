import sqlite3

import pytest

from sources.combiners.advisor import run as run_mod
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db
from sources.screeners.portfolio_screener import db as portfolio_db
from sources.screeners.stock_analysis_screener import db as stocks_db

# The real 9:12pm-Phoenix advisor slot, which is already the NEXT UTC day.
# Fixtures must straddle the rollover or they cannot catch a UTC/Phoenix mixup:
# this instant is Phoenix 2026-07-07 but UTC 2026-07-08.
NOW = "2026-07-08T04:12:00+00:00"
# `price` is the close FOR priceDate; `close` is stockanalysis's PREVIOUS
# close. Fixtures write them distinct so reading the wrong one cannot pass.
PRICE_COLS = {"priceDate": "TEXT", "close": "REAL", "price": "REAL", "atr": "REAL"}


def _sig(signal_id, entity, score):
    return dict(
        signal_id=signal_id,
        grain="ticker",
        entity=entity,
        raw_value=1.0,
        score=score,
        obs_date="2026-07-06",
        staleness_days=0.0,
    )


def _mini_composite(dirpath):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    signals = [
        _sig("sig_a", "NVDA", 2),
        _sig("sig_b", "NVDA", 1),
        _sig("sig_c", "NVDA", 1),  # NVDA: +4 over 3 votes -> flagged
        _sig("stocks_rsi", "AAPL", -1),  # AAPL: held + negative -> disagreement
    ]
    # composite's own 9:05pm slot on Phoenix 2026-07-06 -> 04:05 UTC the 7th
    sid = composite_db.write_snapshot(conn, "2026-07-07T04:05:00+00:00", len(signals))
    composite_db.write_signal_values(conn, sid, signals)
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()


def _mini_portfolio(dirpath):
    conn = portfolio_db.connect(str(dirpath / "portfolio.db"))
    portfolio_db.ensure_schema(conn)
    portfolio_db.write_snapshot(
        conn,
        "2026-07-07T21:30:00+00:00",
        {"equity": 10000.0, "cash": 2000.0, "buying_power": 1000.0},
        [
            {"symbol": "AAPL", "quantity": 10.0, "avg_cost": 90.0, "market_value": 1000.0},
            {"symbol": "XOM", "quantity": 5.0, "avg_cost": 70.0, "market_value": 400.0},
        ],
    )
    conn.close()


def _mini_prices(path, rows):
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, PRICE_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, 's')",
        ("2026-07-07T11:00:00+00:00", len(rows)),
    )
    sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
    for sym, close, atr in rows:
        conn.execute(
            'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price", "atr")'
            " VALUES (?, ?, ?, ?, ?, ?)",
            (sid, sym, "2026-07-07", close - 1.0, close, atr),
        )
    conn.commit()
    conn.close()


def _mini_scorer(dirpath):
    conn = scorer_db.connect(str(dirpath / "scorer.db"))
    scorer_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                i,
                "2026-06-01",
                "sig_a",
                f"T{i}",
                1,
                0,
                5,
                "2026-06-02",
                100.0,
                "SPY",
                500.0,
                "2026-06-09",
                110.0,
                0.10,
                0.01,
                "2026-06-09T21:10:00+00:00",
            )
            for i in range(1, 31)
        ],
    )
    conn.commit()
    conn.close()


def _full_fixture(tmp_path):
    _mini_composite(tmp_path)
    _mini_portfolio(tmp_path)
    _mini_prices(tmp_path / "stocks.db", [("AAPL", 100.0, 2.0), ("NVDA", 100.0, 4.0)])
    _mini_prices(tmp_path / "etfs.db", [("XOM", 80.0, 4.0)])
    _mini_scorer(tmp_path)


def test_full_cycle(tmp_path):
    _full_fixture(tmp_path)
    out = str(tmp_path / "advisor.db")
    sid, n_heat, n_caps = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert (n_heat, n_caps) == (2, 1)  # AAPL + XOM held; NVDA flagged
    conn = sqlite3.connect(out)
    # header provenance frozen in
    assert conn.execute(
        "SELECT equity, buying_power, portfolio_captured_at, composite_captured_at,"
        " sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone() == (
        10000.0,
        1000.0,
        "2026-07-07T21:30:00+00:00",
        "2026-07-07T04:05:00+00:00",
        0,
    )
    # heat: AAPL 10x2=20 (from stocks.db), XOM 5x4=20 (from etfs.db fallback)
    heat = dict(conn.execute("SELECT symbol, heat_dollars FROM v_latest_heat"))
    assert heat == {"AAPL": 20.0, "XOM": 20.0}
    # NVDA cap: floor(0.01*10000/4)=25 shares = $2500 > $1000 buying power
    cap = conn.execute(
        "SELECT cap_shares, cap_dollars, exceeds_buying_power, direction,"
        " reliable_signals, total_signals, already_held FROM v_latest_caps"
    ).fetchone()
    assert cap == (25.0, 2500.0, 1, "bullish", 1, 3, 0)
    # AAPL is a (weak) disagreement
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_disagreements")] == ["AAPL"]


def test_missing_sources_skip_and_continue(tmp_path, capsys):
    out = str(tmp_path / "advisor.db")
    sid, n_heat, n_caps = run_mod.run(out, str(tmp_path), now_iso=NOW)
    assert (n_heat, n_caps) == (0, 0)
    err = capsys.readouterr().out
    # composite, portfolio, scorer missing -> 3 skips; price DBs are never
    # attached because there are no symbols to look up. Type names only.
    assert err.count("FileNotFoundError") == 3
    assert "Traceback" not in err
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    # the header owns the distinction between "empty book" and "failed reads"
    assert conn.execute("SELECT positions, sources_failed FROM v_book_heat").fetchone() == (0, 3)


def test_prune_via_keep_days(tmp_path):
    _full_fixture(tmp_path)
    out = str(tmp_path / "advisor.db")
    run_mod.run(out, str(tmp_path), now_iso="2026-01-01T21:12:00+00:00")
    run_mod.run(out, str(tmp_path), now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_atr_staleness_is_judged_on_the_phoenix_date(tmp_path):
    """A priceDate exactly ATR_MAX_AGE_DAYS old is fresh, not stale.

    Regression: advisor derived `today` from now_iso[:10] (UTC). At the 9:12pm
    Phoenix slot that is already tomorrow, so every ATR age came out one day
    high and this 5-day-old price tripped atr_stale a day early — eating the
    holiday margin ATR_MAX_AGE_DAYS was sized for.
    """
    _mini_composite(tmp_path)
    _mini_portfolio(tmp_path)
    # NOW is Phoenix 2026-07-07; 5 calendar days back is exactly the budget.
    for name, rows in (("stocks.db", [("AAPL", 100.0, 2.0)]), ("etfs.db", [("XOM", 80.0, 4.0)])):
        conn = stocks_db.connect(str(tmp_path / name))
        stocks_db.ensure_schema(conn, PRICE_COLS)
        conn.execute(
            "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, ?, 's')",
            ("2026-07-07T11:00:00+00:00", len(rows)),
        )
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        for sym, close, atr in rows:
            conn.execute(
                'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price", "atr")'
                " VALUES (?, ?, ?, ?, ?, ?)",
                (sid, sym, "2026-07-02", close - 1.0, close, atr),
            )
        conn.commit()
        conn.close()
    _mini_scorer(tmp_path)

    out = str(tmp_path / "advisor.db")
    run_mod.run(out, str(tmp_path), now_iso=NOW)
    conn = sqlite3.connect(out)
    stale = dict(conn.execute("SELECT symbol, atr_stale FROM v_latest_heat"))
    assert stale == {"AAPL": 0, "XOM": 0}


def test_main_argv(tmp_path, capsys):
    _full_fixture(tmp_path)
    run_mod.main(["--db", str(tmp_path / "advisor.db"), "--db-dir", str(tmp_path)])
    assert "advisor snapshot" in capsys.readouterr().out
