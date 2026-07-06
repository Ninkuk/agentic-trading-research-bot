import sqlite3

import pytest

from sources.combiners.composite import fetch
from sources.screeners.fred_screener import db as fred_db

SIG = {
    "signal_id": "fred_curve", "db": "fred.db", "grain": "market",
    "staleness_budget_days": 7,
    "sql": ("SELECT '*', value, CASE WHEN value < 0 THEN -1 ELSE 0 END,"
            " date FROM src.observations WHERE series_id='T10Y2Y'"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 1"),
}


def _mini_fred(tmp_path):
    """Real fred schema via the source's own ensure_schema — combiner
    tests break loudly if the source schema drifts."""
    path = tmp_path / "fred.db"
    conn = fred_db.connect(str(path))
    fred_db.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO observations (series_id, date, value) VALUES (?,?,?)",
        [("T10Y2Y", "2026-07-01", 0.35), ("T10Y2Y", "2026-07-03", -0.10)])
    conn.commit()
    conn.close()
    return str(path)


def test_attach_ro_missing_file_raises(tmp_path):
    conn = sqlite3.connect(":memory:", uri=True)
    with pytest.raises(FileNotFoundError):
        fetch.attach_ro(conn, str(tmp_path / "nope.db"))


def test_attach_is_readonly(tmp_path):
    path = _mini_fred(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO src.observations (series_id, date, value)"
                     " VALUES ('X', '2026-01-01', 1)")


def test_extract_normalizes_rows(tmp_path):
    path = _mini_fred(tmp_path)
    conn = sqlite3.connect(":memory:", uri=True)
    fetch.attach_ro(conn, path)
    rows = fetch.extract(conn, SIG, today="2026-07-06")
    assert rows == [{
        "signal_id": "fred_curve", "grain": "market", "entity": "*",
        "raw_value": -0.10, "score": -1, "obs_date": "2026-07-03",
        "staleness_days": 3,
    }]
    fetch.detach(conn)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT 1 FROM src.observations")


def test_staleness_days():
    assert fetch.staleness_days("2026-07-06", "2026-07-03") == 3
    assert fetch.staleness_days("2026-07-06", None) is None
    assert fetch.staleness_days("2026-07-06", "not-a-date") is None
