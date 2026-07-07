from sources.combiners.advisor import db as advisor_db
from sources.combiners.advisor import fetch
from sources.combiners.composite import db as composite_db
from sources.combiners.scorer import db as scorer_db
from sources.screeners.portfolio_screener import db as portfolio_db
from sources.screeners.stock_analysis_screener import db as stocks_db

PRICE_COLS = {"priceDate": "TEXT", "close": "REAL", "atr": "REAL"}


def _advisor_conn(tmp_path):
    """A real advisor.db connection — its own `snapshots` table must never
    shadow an attached DB's inside that DB's views."""
    conn = advisor_db.connect(str(tmp_path / "advisor.db"))
    advisor_db.ensure_schema(conn)
    return conn


def _mini_composite(dirpath, signals):
    conn = composite_db.connect(str(dirpath / "composite.db"))
    composite_db.ensure_schema(conn)
    sid = composite_db.write_snapshot(conn, "2026-07-06T21:05:00+00:00", len(signals))
    composite_db.write_signal_values(conn, sid, signals)
    composite_db.write_ticker_scores(conn, sid)
    composite_db.write_market_regime(conn, sid, {})
    conn.commit()
    conn.close()


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
            'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "atr")'
            " VALUES (?, ?, ?, ?, ?)",
            (sid, sym, "2026-07-07", close, atr),
        )
    conn.commit()
    conn.close()


def _mini_scorer(dirpath, reliable_signal="sig_a"):
    conn = scorer_db.connect(str(dirpath / "scorer.db"))
    scorer_db.ensure_schema(conn)
    # 30 matured, benchmarked rows for one (signal_id, horizon) group ->
    # n_bench = 30 -> reliable = 1 in v_signal_efficacy.
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
                reliable_signal,
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


def test_composite_readers_resolve_views_in_attached_schema(tmp_path):
    # NVDA: three voting signals summing to +4 -> flagged. AAPL: one -1 vote.
    _mini_composite(
        tmp_path,
        [
            _sig("sig_a", "NVDA", 2),
            _sig("sig_b", "NVDA", 1),
            _sig("sig_c", "NVDA", 1),
            _sig("stocks_rsi", "AAPL", -1),
        ],
    )
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "composite.db"))
    header = fetch.read_composite_header(conn)
    assert header["captured_at"] == "2026-07-06T21:05:00+00:00"
    expected_regime = conn.execute("SELECT regime FROM src.market_regime").fetchone()[0]
    assert header["regime"] == expected_regime
    scorecard = fetch.read_scorecard(conn)
    assert scorecard["NVDA"]["score_sum"] == 4 and scorecard["NVDA"]["total"] == 3
    assert scorecard["AAPL"]["score_sum"] == -1
    assert fetch.read_flagged(conn) == ["NVDA"]
    assert fetch.read_flag_signals(conn)["NVDA"] == {("sig_a", 0), ("sig_b", 0), ("sig_c", 0)}
    fetch.detach(conn)


def test_portfolio_readers(tmp_path):
    _mini_portfolio(tmp_path)
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "portfolio.db"))
    account = fetch.read_account(conn)
    assert account == {
        "equity": 10000.0,
        "cash": 2000.0,
        "buying_power": 1000.0,
        "captured_at": "2026-07-07T21:30:00+00:00",
    }
    positions = fetch.read_positions(conn)
    assert {p["symbol"] for p in positions} == {"AAPL", "XOM"}
    fetch.detach(conn)


def test_read_metrics_filters_to_requested_symbols(tmp_path):
    _mini_prices(tmp_path / "stocks.db", [("AAPL", 100.0, 2.0), ("OTHER", 50.0, 1.0)])
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "stocks.db"))
    metrics = fetch.read_metrics(conn, {"AAPL", "MISSING"})
    assert metrics == {"AAPL": {"atr": 2.0, "close": 100.0, "price_date": "2026-07-07"}}
    assert fetch.read_metrics(conn, set()) == {}
    fetch.detach(conn)


def test_read_reliable_signals(tmp_path):
    _mini_scorer(tmp_path, reliable_signal="sig_a")
    conn = _advisor_conn(tmp_path)
    fetch.attach_ro(conn, str(tmp_path / "scorer.db"))
    assert fetch.read_reliable_signals(conn) == {("sig_a", 0)}
    fetch.detach(conn)


def test_attach_ro_missing_file_raises(tmp_path):
    conn = _advisor_conn(tmp_path)
    try:
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass
