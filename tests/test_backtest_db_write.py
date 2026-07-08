import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_insert_vintages_upserts_last_wins(conn):
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.5)])
    db.insert_vintages(conn, [("T10Y2Y", "2025-01-09", "2025-01-09", 0.6)])
    rows = conn.execute("SELECT value FROM signal_vintages").fetchall()
    assert rows == [(0.6,)]


def test_insert_benchmark_upserts(conn):
    db.insert_benchmark(conn, "SP500", [("2025-01-09", 6000.0)])
    db.insert_benchmark(conn, "SP500", [("2025-01-09", 6001.0)])
    rows = conn.execute("SELECT close FROM benchmark_closes").fetchall()
    assert rows == [(6001.0,)]


def test_snapshot_header_roundtrip(conn):
    sid = db.write_snapshot(conn, "2025-01-15T00:00:00+00:00")
    db.finish_snapshot(conn, sid, 10, 20, 1)
    row = conn.execute(
        "SELECT vintage_rows, benchmark_rows, sources_failed FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    assert row == (10, 20, 1)


def test_prune_deletes_only_old_headers_never_data(conn):
    old = db.write_snapshot(conn, "2024-01-01T00:00:00+00:00")
    new = db.write_snapshot(conn, "2025-01-14T00:00:00+00:00")
    db.insert_vintages(conn, [("T10Y2Y", "2020-01-09", "2020-01-09", 0.5)])
    db.insert_benchmark(conn, "SP500", [("2020-01-09", 3000.0)])
    n = db.prune(conn, keep_days=30, now_iso="2025-01-15T00:00:00+00:00")
    assert n == 1
    ids = [r[0] for r in conn.execute("SELECT id FROM snapshots")]
    assert ids == [new] and old not in ids
    assert conn.execute("SELECT COUNT(*) FROM signal_vintages").fetchone() == (1,)
    assert conn.execute("SELECT COUNT(*) FROM benchmark_closes").fetchone() == (1,)
