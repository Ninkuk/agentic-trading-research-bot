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
