import sqlite3

import pytest

from sources.combiners.backtest import db, run


@pytest.fixture
def data_dir(tmp_path):
    """A data/ dir containing minimal real fred.db + cboe_stats.db."""
    c = sqlite3.connect(tmp_path / "fred.db")
    c.execute(
        "CREATE TABLE observation_vintages"
        " (series_id TEXT, date TEXT, realtime_start TEXT, value REAL)"
    )
    c.execute("CREATE TABLE observations (series_id TEXT, date TEXT, value REAL)")
    c.execute(
        "INSERT INTO observation_vintages VALUES ('T10Y2Y', '2025-01-01', '2025-01-01', -0.5)"
    )
    c.executemany(
        "INSERT INTO observations VALUES ('SP500', ?, ?)",
        [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)],
    )
    c.commit()
    c.close()
    # cboe_stats.db for the non-vintage market-grain signals (cboe_vix,
    # cboe_vix_backwardation both read vix_daily). High VIX every day.
    c = sqlite3.connect(tmp_path / "cboe_stats.db")
    c.execute("CREATE TABLE vix_daily (date TEXT, close REAL, vix3m REAL)")
    c.executemany(
        "INSERT INTO vix_daily VALUES (?, ?, ?)",
        [(f"2025-01-{d:02d}", 26.0, 24.0) for d in range(1, 31)],
    )
    c.commit()
    c.close()
    # nyfed.db (v_rrp_trend) + treasury.db (v_tga_trend): liquidity signals
    # whose derived change columns are harvested keyed by date. 5 rows each.
    c = sqlite3.connect(tmp_path / "nyfed.db")
    c.execute("CREATE TABLE v_rrp_trend (operation_date TEXT, change_vs_prior REAL)")
    c.executemany(
        "INSERT INTO v_rrp_trend VALUES (?, ?)",
        [(f"2025-01-{d:02d}", -1.0) for d in range(1, 6)],
    )
    c.commit()
    c.close()
    c = sqlite3.connect(tmp_path / "treasury.db")
    c.execute("CREATE TABLE v_tga_trend (record_date TEXT, wow_change REAL)")
    c.executemany(
        "INSERT INTO v_tga_trend VALUES (?, ?)",
        [(f"2025-01-{d:02d}", 2.0) for d in range(1, 6)],
    )
    c.commit()
    c.close()
    return str(tmp_path)


def test_run_copies_and_reports(data_dir, tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00"
    )
    assert (n_vint, n_bench) == (1, 30)
    out = capsys.readouterr().out
    assert "fred_curve" in out and "bearish" in out
    assert "cboe_vix" in out  # market-grain signal graded too
    conn = db.connect(str(tmp_path / "backtest.db"))
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, market_rows, sources_failed"
        " FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    conn.close()
    # market_rows: 30 cboe_vix + 30 cboe_vix_backwardation + 5 nyfed_rrp
    # + 5 tsy_tga = 70; all four source DBs present -> 0 failures
    assert row == (1, 30, 70, 0)


def test_run_missing_source_dbs_skip_and_count_failures(tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"),
        db_dir=str(tmp_path),  # none of the source DBs exist here
        now_iso="2025-02-01T00:00:00+00:00",
    )
    assert (n_vint, n_bench) == (0, 0)
    assert "FileNotFoundError" in capsys.readouterr().out
    conn = db.connect(str(tmp_path / "backtest.db"))
    (failed,) = conn.execute("SELECT sources_failed FROM snapshots WHERE id = ?", (sid,)).fetchone()
    conn.close()
    assert failed == 4  # fred.db, cboe_stats.db, nyfed.db, treasury.db all missing


def test_run_copies_market_obs_as_of(data_dir, tmp_path):
    sid, _, _ = run.run(
        str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00"
    )
    conn = db.connect(str(tmp_path / "backtest.db"))
    # cboe_vix (high VIX) graded bearish vs the falling SP500 spine -> hits
    row = conn.execute(
        "SELECT n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'cboe_vix' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    conn.close()
    assert row[0] == 24 and row[1] == pytest.approx(1.0)


def test_run_is_idempotent(data_dir, tmp_path):
    path = str(tmp_path / "backtest.db")
    run.run(path, db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00")
    run.run(path, db_dir=data_dir, now_iso="2025-02-02T00:00:00+00:00")
    conn = db.connect(path)
    counts = (
        conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone()[0],
        conn.execute("SELECT COUNT(*) FROM benchmark_closes").fetchone()[0],
    )
    conn.close()
    assert counts == (1, 30)


def test_run_rolls_back_partial_copy_and_zeroes_counts(data_dir, tmp_path):
    def boom(conn, series_id):
        raise RuntimeError("benchmark copy failed mid-run")

    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"),
        db_dir=data_dir,
        now_iso="2025-02-01T00:00:00+00:00",
        harvest_benchmark=boom,
    )
    assert (n_vint, n_bench) == (0, 0)
    conn = db.connect(str(tmp_path / "backtest.db"))
    header = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    data_count = conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone()[0]
    conn.close()
    assert header == (0, 0, 1)
    assert data_count == 0


def test_run_reports_neutral_n_days_not_n_bench(tmp_path, capsys):
    """Neutral rows must show n_days (all days), not n_bench (graded only, 0 for neutral)."""
    # Create a fred.db with a POSITIVE T10Y2Y value -> neutral score
    # (FRED_CURVE_SCORE = CASE WHEN value < 0 THEN -1 ELSE 0 END)
    c = sqlite3.connect(tmp_path / "fred.db")
    c.execute(
        "CREATE TABLE observation_vintages"
        " (series_id TEXT, date TEXT, realtime_start TEXT, value REAL)"
    )
    c.execute("CREATE TABLE observations (series_id TEXT, date TEXT, value REAL)")
    # Positive value -> score 0 (neutral)
    c.execute("INSERT INTO observation_vintages VALUES ('T10Y2Y', '2025-01-05', '2025-01-05', 0.5)")
    # SP500 closes for 30 days
    c.executemany(
        "INSERT INTO observations VALUES ('SP500', ?, ?)",
        [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)],
    )
    c.commit()
    c.close()

    data_dir = str(tmp_path)
    run.run(str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00")
    out = capsys.readouterr().out

    # Find the fred_curve neutral line
    neutral_lines = [line for line in out.split("\n") if "fred_curve" in line and "neutral" in line]
    assert len(neutral_lines) > 0, f"Expected fred_curve neutral line in output:\n{out}"

    # After the fix: should NOT show n=0 (the n_bench value for neutral rows)
    # The ungraded branch now prints n_days instead of n_bench
    neutral_line = neutral_lines[0]
    assert "ungraded" in neutral_line
    assert "n=0" not in neutral_line, (
        f"Regression: neutral row shows n=0 (n_bench) instead of n_days:\n{neutral_line}"
    )
