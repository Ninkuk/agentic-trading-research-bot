import sqlite3

from sources.combiners.composite import db


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def test_ensure_schema_creates_tables(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    assert {"snapshots", "signal_values", "market_regime",
            "ticker_scores"} <= _tables(conn)


def test_ensure_schema_is_idempotent(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    db.ensure_schema(conn)  # must not raise


def test_connect_uses_wal_and_uri(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    # URI mode is on: an ATTACH with ?mode=ro must parse (target must exist)
    other = tmp_path / "src.db"
    sqlite3.connect(str(other)).close()
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{other}?mode=ro",))


def test_score_check_constraint(tmp_path):
    conn = db.connect(str(tmp_path / "composite.db"))
    db.ensure_schema(conn)
    conn.execute("INSERT INTO snapshots (captured_at, signals_expected)"
                 " VALUES ('2026-07-06T00:00:00+00:00', 1)")
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO signal_values (snapshot_id, signal_id, grain,"
            " entity, score) VALUES (1, 'x', 'ticker', 'AAPL', 3)")
