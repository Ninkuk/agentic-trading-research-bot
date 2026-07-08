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
