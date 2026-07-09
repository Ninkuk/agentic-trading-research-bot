import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_ensure_schema_is_idempotent(conn):
    db.ensure_schema(conn)  # second call must not raise


def test_expected_tables_exist(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"snapshots", "signal_vintages", "benchmark_closes"} <= names


def test_ensure_schema_adds_market_rows_to_a_pre_market_obs_snapshots_table():
    """CREATE TABLE IF NOT EXISTS never widens an existing table, so a DB
    written before market_obs shipped keeps a snapshots table with no
    market_rows column and finish_snapshot raises on it."""
    c = db.connect(":memory:")
    c.executescript("""
        CREATE TABLE snapshots (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            captured_at    TEXT NOT NULL,
            vintage_rows   INTEGER NOT NULL DEFAULT 0,
            benchmark_rows INTEGER NOT NULL DEFAULT 0,
            sources_failed INTEGER NOT NULL DEFAULT 0
        );
    """)

    db.ensure_schema(c)

    sid = db.write_snapshot(c, "2026-07-09T04:30:00+00:00")
    db.finish_snapshot(c, sid, 7, 5, 0, 3)
    row = c.execute("SELECT vintage_rows, benchmark_rows, market_rows FROM snapshots").fetchone()
    assert row == (7, 5, 3)
    c.close()
