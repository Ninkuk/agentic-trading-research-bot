from sources.screeners.cboe_options import db, run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _payload(underlying, iv30=27.8):
    return {
        "timestamp": "2026-07-03 17:46:09", "symbol": underlying,
        "data": {"symbol": underlying, "current_price": 100.0, "close": 100.5,
                 "iv30": iv30, "last_trade_time": "2026-07-02T16:00:00",
                 "options": [
                     {"option": f"{underlying}260717C00100000", "bid": 1.0,
                      "ask": 1.2, "iv": 0.3, "delta": 0.5, "gamma": 0.01,
                      "theta": -0.1, "vega": 0.2, "rho": 0.05,
                      "open_interest": 100.0, "volume": 250.0,
                      "last_trade_price": 1.1, "theo": 1.1}]}}


def test_run_ingests_symbols(tmp_path):
    dbp = str(tmp_path / "opt.db")
    sid, sc, rc = run_mod.run(
        dbp, symbols=["AAPL", "MSFT"], now_iso=NOW,
        fetch_chain=lambda sym, is_index: _payload(sym))
    assert (sc, rc) == (2, 2)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM option_snapshots").fetchone()[0] == 2
    # session_date came from the payload, not the wall clock
    assert conn.execute(
        "SELECT DISTINCT snapshot_date FROM option_snapshots").fetchone()[0] == "2026-07-02"
    assert conn.execute("SELECT COUNT(*) FROM underlying_daily").fetchone()[0] == 2


def test_run_skips_none_payload(tmp_path):
    dbp = str(tmp_path / "opt.db")

    def fc(sym, is_index):
        return None if sym == "ZZZZ" else _payload(sym)

    _, sc, rc = run_mod.run(dbp, symbols=["AAPL", "ZZZZ"], now_iso=NOW,
                            fetch_chain=fc)
    assert (sc, rc) == (1, 1)


def test_run_skips_failing_symbol_and_hides_message(tmp_path, capsys):
    dbp = str(tmp_path / "opt.db")

    def fc(sym, is_index):
        if sym == "BAD":
            raise RuntimeError("secret-token-leak")
        return _payload(sym)

    _, sc, _ = run_mod.run(dbp, symbols=["BAD", "AAPL"], now_iso=NOW,
                           fetch_chain=fc)
    assert sc == 1
    err = capsys.readouterr().err
    assert "BAD" in err and "RuntimeError" in err
    assert "secret-token-leak" not in err


def test_run_all_fail_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "opt.db")
    _, sc, rc = run_mod.run(dbp, symbols=["A"], now_iso=NOW,
                            fetch_chain=lambda sym, is_index: None)
    assert (sc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT symbol_count, row_count FROM snapshots").fetchone()) == (0, 0)


def test_run_default_symbols_from_catalog(tmp_path):
    dbp = str(tmp_path / "opt.db")
    seen = []

    def fc(sym, is_index):
        seen.append(sym)
        return None

    run_mod.run(dbp, now_iso=NOW, fetch_chain=fc)
    assert "AAPL" in seen and "SPX" in seen and len(seen) >= 20


def test_run_keep_days_prunes_headers(tmp_path):
    dbp = str(tmp_path / "opt.db")
    run_mod.run(dbp, symbols=["A"], now_iso=NOW,
                fetch_chain=lambda sym, is_index: None)
    conn = db.connect(dbp)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 0, 0)
    conn.close()
    run_mod.run(dbp, symbols=["A"], now_iso=NOW, keep_days=30,
                fetch_chain=lambda sym, is_index: None)
    conn = db.connect(dbp)
    old = conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE captured_at < '2020-01-01'"
    ).fetchone()[0]
    assert old == 0
