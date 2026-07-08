import sqlite3

import pytest

from sources.combiners.backtest import db, run


@pytest.fixture
def data_dir(tmp_path):
    """A data/ dir containing a minimal real fred.db."""
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
    return str(tmp_path)


def test_run_copies_and_reports(data_dir, tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"), db_dir=data_dir, now_iso="2025-02-01T00:00:00+00:00"
    )
    assert (n_vint, n_bench) == (1, 30)
    out = capsys.readouterr().out
    assert "fred_curve" in out and "bearish" in out
    conn = db.connect(str(tmp_path / "backtest.db"))
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    conn.close()
    assert row == (1, 30, 0)


def test_run_missing_fred_db_skips_and_counts_failure(tmp_path, capsys):
    sid, n_vint, n_bench = run.run(
        str(tmp_path / "backtest.db"),
        db_dir=str(tmp_path),  # no fred.db here
        now_iso="2025-02-01T00:00:00+00:00",
    )
    assert (n_vint, n_bench) == (0, 0)
    assert "FileNotFoundError" in capsys.readouterr().out
    conn = db.connect(str(tmp_path / "backtest.db"))
    (failed,) = conn.execute("SELECT sources_failed FROM snapshots WHERE id = ?", (sid,)).fetchone()
    conn.close()
    assert failed == 1


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
