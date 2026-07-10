import sqlite3

import pytest

from sources.combiners.composite import catalog as cat
from sources.combiners.composite import run as run_mod
from sources.monitors.earnings_calendar import db as earnings_db
from sources.screeners.fred_screener import db as fred_db
from sources.screeners.portfolio_screener import db as pf_db

NOW = "2026-07-06T21:00:00+00:00"

FRED_SIG = {
    "signal_id": "fred_curve",
    "db": "fred.db",
    "grain": "market",
    "staleness_budget_days": 7,
    "sql": (
        "SELECT '*', value, CASE WHEN value < 0 THEN -1 ELSE 0 END,"
        " date FROM src.observations WHERE series_id='T10Y2Y'"
        " AND value IS NOT NULL ORDER BY date DESC LIMIT 1"
    ),
}
MISSING_SIG = {
    "signal_id": "ghost",
    "db": "nope.db",
    "grain": "market",
    "staleness_budget_days": 0,
    "sql": "SELECT '*', 1, 0, :today",
}
BROKEN_SIG = {
    "signal_id": "broken",
    "db": "fred.db",
    "grain": "market",
    "staleness_budget_days": 0,
    "sql": "SELECT nope FROM src.does_not_exist",
}
PHX_TODAY_SIG = {
    "signal_id": "phx_today",
    "db": "fred.db",
    "grain": "market",
    "staleness_budget_days": 0,
    "sql": "SELECT '*', 1, 0, :today",
}
PF_SIG = {
    "signal_id": "portfolio_holding",
    "db": "portfolio.db",
    "grain": "ticker",
    "staleness_budget_days": 3,
    "sql": (
        "SELECT p.symbol, p.quantity, 0, substr(s.captured_at, 1, 10)"
        " FROM src.positions p JOIN src.snapshots s ON s.id ="
        " p.snapshot_id WHERE p.snapshot_id = (SELECT id FROM"
        " src.snapshots ORDER BY captured_at DESC, id DESC LIMIT 1)"
    ),
}


def _mini_fred(dirpath):
    conn = fred_db.connect(str(dirpath / "fred.db"))
    fred_db.ensure_schema(conn)
    conn.execute(
        "INSERT INTO observations (series_id, date, value) VALUES ('T10Y2Y', '2026-07-03', -0.10)"
    )
    conn.commit()
    conn.close()


def _mini_portfolio(dirpath):
    conn = pf_db.connect(str(dirpath / "portfolio.db"))
    pf_db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (captured_at, position_count) VALUES (?, 1)", (NOW,))
    conn.execute("INSERT INTO positions (snapshot_id, symbol, quantity) VALUES (1, 'XOM', 10)")
    conn.commit()
    conn.close()


def test_run_happy_path_writes_all_tiers(tmp_path, capsys):
    _mini_fred(tmp_path)
    _mini_portfolio(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(out, str(tmp_path), now_iso=NOW, signals=[FRED_SIG, PF_SIG])
    assert (ok, failed) == (2, 0)
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT t10y2y, curve_inverted FROM v_latest_regime").fetchone() == (
        -0.10,
        1,
    )
    assert conn.execute(
        "SELECT in_portfolio FROM v_latest_scorecard WHERE symbol='XOM'"
    ).fetchone() == (1,)


def test_run_skips_missing_db_and_broken_sql(tmp_path, capsys):
    _mini_fred(tmp_path)
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(
        out, str(tmp_path), now_iso=NOW, signals=[FRED_SIG, MISSING_SIG, BROKEN_SIG]
    )
    assert (ok, failed) == (1, 2)
    err = capsys.readouterr().out
    assert "FileNotFoundError" in err and "OperationalError" in err
    # never leak details beyond the exception type name
    assert "does_not_exist" not in err
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT signals_ok, signals_failed FROM snapshots").fetchone() == (1, 2)


def test_run_never_writes_to_sources(tmp_path):
    _mini_fred(tmp_path)
    before = (tmp_path / "fred.db").read_bytes()
    run_mod.run(str(tmp_path / "composite.db"), str(tmp_path), now_iso=NOW, signals=[FRED_SIG])
    assert (tmp_path / "fred.db").read_bytes() == before


def test_run_phase2_failure_is_loud_and_header_honest(tmp_path, capsys, monkeypatch):
    _mini_fred(tmp_path)
    monkeypatch.setattr(
        run_mod.db,
        "write_market_regime",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom-secret")),
    )
    out = str(tmp_path / "composite.db")
    with pytest.raises(RuntimeError):
        run_mod.run(out, str(tmp_path), now_iso=NOW, signals=[FRED_SIG])
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT signals_ok, signals_failed FROM snapshots").fetchone() == (1, 0)
    assert conn.execute("SELECT COUNT(*) FROM market_regime").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM signal_values").fetchone()[0] == 1
    captured = capsys.readouterr().out
    assert "combine failed: RuntimeError" in captured
    assert "boom-secret" not in captured


def test_run_derives_today_on_shared_phoenix_clock(tmp_path):
    # 9:05pm Phoenix on Jul 7 is 4:05am UTC on Jul 8 (Phoenix is fixed UTC-7,
    # no DST). :today must bind to the Phoenix trading date (2026-07-07),
    # matching scorer/journal's _phx_date shift, not the raw UTC date.
    _mini_fred(tmp_path)
    out = str(tmp_path / "composite.db")
    evening_utc_now = "2026-07-08T04:05:00+00:00"
    run_mod.run(out, str(tmp_path), now_iso=evening_utc_now, signals=[PHX_TODAY_SIG])
    conn = sqlite3.connect(out)
    assert conn.execute(
        "SELECT obs_date, staleness_days FROM signal_values WHERE signal_id='phx_today'"
    ).fetchone() == ("2026-07-07", 0)


def test_main_argv_roundtrip(tmp_path, capsys):
    _mini_fred(tmp_path)
    run_mod.main(
        ["--db", str(tmp_path / "composite.db"), "--db-dir", str(tmp_path), "--only", "fred_curve"]
    )
    out = capsys.readouterr().out
    assert "composite snapshot" in out and "1 signals ok" in out


# --- earnings_imminent: per-ticker event gate (plan 002) --------------------

EARNINGS_SIG = next(s for s in cat.SIGNALS if s["signal_id"] == "earnings_imminent")


def _mini_earnings(tmp_path, rows):
    """rows: (event_date, ticker). Real monitor schema; PK is
    (event_type, event_date, subtype), so one ticker CAN hold several forward
    rows (a tentative estimate plus a confirmed date)."""
    conn = earnings_db.connect(str(tmp_path / "earnings.db"))
    earnings_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO events (event_type, event_date, subtype, source, fetched_at)"
        " VALUES ('earnings', ?, ?, 'test', '2026-07-08T04:05:00+00:00')",
        rows,
    )
    conn.commit()
    conn.close()


# 9:05pm Phoenix Jul 7 == 04:05Z Jul 8. The fixture MUST straddle the rollover:
# with a 21:05Z stamp a naive UTC date-slice would coincide with the Phoenix
# date and the test could not catch a clock mixup.
EVENING = "2026-07-08T04:05:00+00:00"
PHX_TODAY = "2026-07-07"


def test_run_emits_one_earnings_imminent_row_per_ticker(tmp_path):
    _mini_earnings(
        tmp_path,
        [
            ("2026-07-09", "AAPL"),  # +2 days
            ("2026-07-12", "AAPL"),  # +5 days: same ticker, must collapse to MIN
            ("2026-07-10", "MSFT"),  # +3 days
            ("2026-08-06", "NVDA"),  # +30 days: outside the 7-day window
            ("2026-07-06", "TSLA"),  # yesterday: already reported
        ],
    )
    out = str(tmp_path / "composite.db")
    run_mod.run(out, str(tmp_path), now_iso=EVENING, signals=[EARNINGS_SIG])

    conn = sqlite3.connect(out)
    rows = conn.execute(
        "SELECT entity, raw_value, score, grain, obs_date FROM signal_values"
        " WHERE signal_id='earnings_imminent' ORDER BY entity"
    ).fetchall()

    assert rows == [
        ("AAPL", 2.0, 0, "ticker", PHX_TODAY),
        ("MSFT", 3.0, 0, "ticker", PHX_TODAY),
    ]


def test_earnings_imminent_binds_today_on_the_phoenix_clock(tmp_path):
    """A ticker reporting on the Phoenix date itself is 0 days out. Under a raw
    UTC slice `today` would be 2026-07-08 and this row would fall out of the
    window's lower bound entirely."""
    _mini_earnings(tmp_path, [("2026-07-07", "AAPL")])
    out = str(tmp_path / "composite.db")
    run_mod.run(out, str(tmp_path), now_iso=EVENING, signals=[EARNINGS_SIG])
    conn = sqlite3.connect(out)
    assert conn.execute(
        "SELECT entity, raw_value, obs_date FROM signal_values WHERE signal_id='earnings_imminent'"
    ).fetchone() == ("AAPL", 0.0, PHX_TODAY)


def test_earnings_imminent_empty_source_yields_no_rows(tmp_path):
    _mini_earnings(tmp_path, [])
    out = str(tmp_path / "composite.db")
    sid, ok, failed = run_mod.run(out, str(tmp_path), now_iso=EVENING, signals=[EARNINGS_SIG])
    assert failed == 0, "an empty forward calendar is normal, not a failure"
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM signal_values").fetchone()[0] == 0
