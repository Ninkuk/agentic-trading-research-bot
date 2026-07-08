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
    # pcr_daily for the windowed cboe_equity_pcr signal (8 obs)
    c.execute("CREATE TABLE pcr_daily (date TEXT, equity_pcr REAL)")
    c.executemany(
        "INSERT INTO pcr_daily VALUES (?, ?)",
        [(f"2025-01-{d:02d}", 0.5 + 0.05 * d) for d in range(1, 9)],
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
    # scorer.db price ledger: XLE class-proxy benchmark (10 rising closes)
    c = sqlite3.connect(tmp_path / "scorer.db")
    c.execute("CREATE TABLE prices (symbol TEXT, price_date TEXT, close REAL)")
    c.executemany(
        "INSERT INTO prices VALUES ('XLE', ?, ?)",
        [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 11)],
    )
    c.commit()
    c.close()
    # eia.db raw obs: crude + natgas (4 each -> 3 week-over-week change rows each)
    c = sqlite3.connect(tmp_path / "eia.db")
    c.execute("CREATE TABLE eia_obs (series_id TEXT, period TEXT, value REAL)")
    for series in ("WCESTUS1", "NW2_EPG0_SWO_R48_BCF"):
        c.executemany(
            "INSERT INTO eia_obs VALUES (?, ?, ?)",
            [(series, f"2025-01-{d:02d}", 100.0 - d) for d in range(1, 5)],
        )
    c.commit()
    c.close()
    return str(tmp_path)


def test_run_copies_and_reports(data_dir, tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00"
    )
    assert (n_vint, n_bench) == (1, 40)  # 30 SP500 + 10 XLE closes
    out = capsys.readouterr().out
    assert "fred_curve" in out and "bearish" in out
    assert "cboe_vix" in out  # market-grain signal graded too
    assert "eia_crude_stocks" in out  # asset-class signal graded vs XLE
    conn = db.connect(str(tmp_path / "backtest.db"))
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, market_rows, sources_failed"
        " FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    conn.close()
    # benchmark_rows: 30 SP500 + 10 XLE = 40.
    # market_rows: 30 cboe_vix + 30 cboe_vix_backwardation + 8 cboe_equity_pcr
    # + 5 nyfed_rrp + 5 tsy_tga + 3 eia_crude + 3 eia_natgas = 84.
    # all source DBs present -> 0 failures
    assert row == (1, 40, 84, 0)


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
    # fred, scorer (XLE), cboe_stats, nyfed, treasury, eia — all six missing
    assert failed == 6


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
    assert counts == (1, 40)  # 30 SP500 + 10 XLE, idempotent across reruns


def test_run_rolls_back_partial_copy_and_zeroes_counts(data_dir, tmp_path):
    def boom(conn, series_id):
        raise RuntimeError("benchmark copy failed mid-run")

    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"),
        db_dir=data_dir,
        now_iso="2025-02-01T00:00:00+00:00",
        harvest_benchmark=boom,
    )
    # The FRED block (vintages + SP500) rolls back together and records no
    # stale counts. The XLE class benchmark is an INDEPENDENT block (uses
    # harvest_price_ledger, not the boom'd harvest_benchmark), so it still
    # succeeds — proving the failure is isolated to its own source.
    assert n_vint == 0
    conn = db.connect(str(tmp_path / "backtest.db"))
    vintage_rows, failed = conn.execute(
        "SELECT vintage_rows, sources_failed FROM snapshots WHERE id = ?", (sid,)
    ).fetchone()
    data_count = conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone()[0]
    sp500 = conn.execute(
        "SELECT COUNT(*) FROM benchmark_closes WHERE benchmark = 'SP500'"
    ).fetchone()[0]
    xle = conn.execute("SELECT COUNT(*) FROM benchmark_closes WHERE benchmark = 'XLE'").fetchone()[
        0
    ]
    conn.close()
    assert vintage_rows == 0 and data_count == 0 and sp500 == 0  # FRED block gone
    assert failed == 1 and xle == 10  # only FRED failed; XLE copied independently


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
