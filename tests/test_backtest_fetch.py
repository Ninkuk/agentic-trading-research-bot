import sqlite3

import pytest

from sources.combiners.backtest import fetch


@pytest.fixture
def fred_db(tmp_path):
    path = tmp_path / "fred.db"
    c = sqlite3.connect(path)
    c.execute(
        "CREATE TABLE observation_vintages"
        " (series_id TEXT, date TEXT, realtime_start TEXT, value REAL)"
    )
    c.execute("CREATE TABLE observations (series_id TEXT, date TEXT, value REAL)")
    c.executemany(
        "INSERT INTO observation_vintages VALUES (?, ?, ?, ?)",
        [
            ("T10Y2Y", "2025-01-09", "2025-01-09", 0.5),
            ("UNRELATED", "2025-01-09", "2025-01-09", 9.9),
        ],
    )
    c.executemany(
        "INSERT INTO observations VALUES (?, ?, ?)",
        [
            ("SP500", "2025-01-09", 6000.0),
            ("SP500", "2025-01-10", None),  # FRED '.' placeholder
            ("T10Y2Y", "2025-01-09", 0.5),
        ],
    )
    c.commit()
    c.close()
    return str(path)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", uri=True)
    yield c
    c.close()


def test_attach_ro_missing_file_raises(conn, tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))


def test_harvest_vintages_filters_to_requested_series(conn, fred_db):
    fetch.attach_ro(conn, fred_db)
    rows = fetch.harvest_vintages(conn, ["T10Y2Y"])
    fetch.detach(conn)
    assert rows == [("T10Y2Y", "2025-01-09", "2025-01-09", 0.5)]


def test_harvest_benchmark_filters_series_and_nulls(conn, fred_db):
    fetch.attach_ro(conn, fred_db)
    rows = fetch.harvest_benchmark(conn, "SP500")
    fetch.detach(conn)
    assert rows == [("2025-01-09", 6000.0)]
