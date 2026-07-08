import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def spine(c, rows):
    c.executemany("INSERT INTO benchmark_closes (date, close) VALUES (?, ?)", rows)


def vintage(c, series, date, realtime_start, value):
    c.execute(
        "INSERT INTO signal_vintages VALUES (?, ?, ?, ?)",
        (series, date, realtime_start, value),
    )


def pit(c, asof, series):
    return c.execute(
        "SELECT value FROM v_pit_signal WHERE asof_date = ? AND series_id = ?",
        (asof, series),
    ).fetchone()


# ---- v_pit_signal ----------------------------------------------------


def test_pit_no_lookahead_ignores_later_revision(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)  # future revision
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


def test_pit_reflects_revision_once_published(conn):
    spine(conn, [("2025-01-10", 100.0), ("2025-02-02", 101.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)
    assert pit(conn, "2025-02-02", "T10Y2Y") == (-0.7,)


def test_pit_hides_observation_published_after_asof(conn):
    # obs date is in the past but its FIRST vintage lands later: invisible.
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-15", 0.9)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (None,)


def test_pit_prefers_latest_observation_date(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-08", "2025-01-08", 0.3)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


# ---- v_replay_flags --------------------------------------------------


def test_flags_apply_composite_cases(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", -0.1)  # inverted -> -1
    vintage(conn, "BAMLH0A0HYM2", "2025-01-09", "2025-01-09", 5.5)  # >=5.0 -> -2
    rows = dict(
        conn.execute("SELECT signal_id, score FROM v_replay_flags WHERE asof_date = '2025-01-10'")
    )
    assert rows == {"fred_curve": -1, "fred_hy_spread": -2}


def test_flags_exclude_dates_with_no_published_value(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-15", 0.5)  # not yet published
    rows = conn.execute("SELECT * FROM v_replay_flags").fetchall()
    assert rows == []


# ---- v_replay_returns ------------------------------------------------


def test_returns_entry_strictly_after_and_horizon_offsets(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    row = conn.execute(
        "SELECT entry_date, exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row[0] == "2025-01-02"  # first close STRICTLY after D
    assert row[1] == "2025-01-07"  # 5 trading rows after entry
    assert row[2] == pytest.approx(107.0 / 102.0 - 1)


def test_returns_unmatured_dates_yield_null(conn):
    spine(conn, [("2025-01-01", 100.0), ("2025-01-02", 101.0)])
    row = conn.execute(
        "SELECT exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row == (None, None)


# ---- v_replay_efficacy -----------------------------------------------


def test_efficacy_grades_bearish_flag_against_falling_benchmark(conn):
    # 30 falling closes; curve inverted from day one -> every matured
    # bearish day is a hit at every horizon.
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    row = conn.execute(
        "SELECT n_bench, hit_rate, reliable FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    # 30 spine days; asof d has entry d+1, exit d+6 -> matured for d in 1..24
    assert row[0] == 24
    assert row[1] == pytest.approx(1.0)
    assert row[2] == 0  # 24 < RELIABLE_MIN_N (30)


def test_efficacy_wilson_ci_brackets_hit_rate(conn):
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    lo, hi = conn.execute(
        "SELECT hit_ci_lo, hit_ci_hi FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    assert 0.0 < lo < 1.0  # Wilson never collapses to zero width on all-hit
    assert hi >= 1.0 or hi == pytest.approx(1.0, abs=1e-9)


def test_efficacy_neutral_rows_reported_but_ungraded(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", 0.5)  # not inverted -> 0
    row = conn.execute(
        "SELECT n_days, n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'neutral' AND horizon = 5"
    ).fetchone()
    assert row[0] > 0  # reported
    assert row[1] == 0 and row[2] is None  # excluded from grading
