import sqlite3

import pytest

from sources.combiners.composite import db, run as run_mod
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.portfolio_screener import db as pf_db

NOW = "2026-07-06T21:00:00+00:00"

FRED_SIG = {
    "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 7,
    "sql": ("SELECT '*', value, CASE WHEN value < 0 THEN -1 ELSE 0 END,"
            " date FROM src.observations WHERE series_id='T10Y2Y'"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 1"),
}
MISSING_SIG = {
    "signal_id": "ghost", "db": "nope.db", "grain": "market",
    "staleness_budget_days": 0, "sql": "SELECT '*', 1, 0, :today",
}
BROKEN_SIG = {
    "signal_id": "broken", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 0, "sql": "SELECT nope FROM src.does_not_exist",
}
PF_SIG = {
    "signal_id": "portfolio_holding", "db": "portfolio.db",
    "grain": "ticker", "staleness_budget_days": 3,
    "sql": ("SELECT p.symbol, p.quantity, 0, substr(s.captured_at, 1, 10)"
            " FROM src.positions p JOIN src.snapshots s ON s.id ="
            " p.snapshot_id WHERE p.snapshot_id = (SELECT id FROM"
            " src.snapshots ORDER BY captured_at DESC, id DESC LIMIT 1)"),
}


def _mini_fred(dirpath):
    conn = fred_db.connect(str(dirpath / "fred.db"))
    fred_db.ensure_schema(conn)
    conn.execute("INSERT INTO observations (series_id, date, value)"
                 " VALUES ('T10Y2Y', '2026-07-03', -0.10)")
    conn.commit(); conn.close()


def _mini_portfolio(dirpath):
    conn = pf_db.connect(str(dirpath / "portfolio.db"))
    pf_db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (captured_at, position_count)"
                 " VALUES (?, 1)", (NOW,))
    conn.execute("INSERT INTO positions (snapshot_id, symbol, quantity)"
                 " VALUES (1, 'XOM', 10)")
    conn.commit(); conn.close()


def test_run_happy_path_writes_all_tiers(tmp_path, capsys):
    _mini_fred(tmp_path); _mini_portfolio(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(out, str(tmp_path), now_iso=NOW,
                                  signals=[FRED_SIG, PF_SIG])
    assert (ok, failed) == (2, 0)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT t10y2y, curve_inverted FROM v_latest_regime"
                        ).fetchone() == (-0.10, 1)
    assert conn.execute("SELECT in_portfolio FROM v_latest_scorecard"
                        " WHERE symbol='XOM'").fetchone() == (1,)


def test_run_skips_missing_db_and_broken_sql(tmp_path, capsys):
    _mini_fred(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(
        out, str(tmp_path), now_iso=NOW,
        signals=[FRED_SIG, MISSING_SIG, BROKEN_SIG])
    assert (ok, failed) == (1, 2)
    err = capsys.readouterr().out
    assert "FileNotFoundError" in err and "OperationalError" in err
    # never leak details beyond the exception type name
    assert "does_not_exist" not in err
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT signals_ok, signals_failed FROM snapshots"
                        ).fetchone() == (1, 2)


def test_run_never_writes_to_sources(tmp_path):
    _mini_fred(tmp_path)
    before = (tmp_path / "fred.db").read_bytes()
    run_mod.run(str(tmp_path / "composite.db"), str(tmp_path),
                now_iso=NOW, signals=[FRED_SIG])
    assert (tmp_path / "fred.db").read_bytes() == before


def test_run_phase2_failure_is_loud_and_header_honest(
        tmp_path, capsys, monkeypatch):
    _mini_fred(tmp_path)
    monkeypatch.setattr(
        run_mod.db, "write_market_regime",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom-secret")))
    out = str(tmp_path / "composite.db")
    with pytest.raises(RuntimeError):
        run_mod.run(out, str(tmp_path), now_iso=NOW, signals=[FRED_SIG])
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT signals_ok, signals_failed FROM snapshots"
                        ).fetchone() == (1, 0)
    assert conn.execute("SELECT COUNT(*) FROM market_regime"
                        ).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM signal_values"
                        ).fetchone()[0] == 1
    captured = capsys.readouterr().out
    assert "combine failed: RuntimeError" in captured
    assert "boom-secret" not in captured


def test_main_argv_roundtrip(tmp_path, capsys):
    _mini_fred(tmp_path)
    run_mod.main(["--db", str(tmp_path / "composite.db"),
                  "--db-dir", str(tmp_path), "--only", "fred_curve"])
    out = capsys.readouterr().out
    assert "composite snapshot" in out and "1 signals ok" in out
