import sqlite3

from screener_common import connect, prune


def _mk(conn):
    conn.executescript(
        "CREATE TABLE snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at TEXT);"
        "CREATE TABLE kids(snapshot_id INTEGER, v INTEGER);"
    )


def test_connect_sets_wal_mode(tmp_path):
    conn = connect(str(tmp_path / "x.db"))
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_prune_deletes_old_snapshots_and_children():
    conn = sqlite3.connect(":memory:")
    _mk(conn)
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (1, '2026-06-01T00:00:00+00:00')")
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (2, '2026-07-02T00:00:00+00:00')")
    conn.execute("INSERT INTO kids VALUES (1, 10), (2, 20)")
    removed = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00",
                    child_table="kids")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM kids").fetchone()[0] == 1
    assert conn.execute("SELECT snapshot_id FROM kids").fetchone()[0] == 2


def test_prune_no_old_snapshots_returns_zero():
    conn = sqlite3.connect(":memory:")
    _mk(conn)
    conn.execute("INSERT INTO snapshots(id, captured_at) VALUES (1, '2026-07-02T00:00:00+00:00')")
    assert prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00",
                 child_table="kids") == 0
