import sqlite3

import pytest

from sources.combiners.scorer import db


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def test_schema_tables(tmp_path):
    conn = _conn(tmp_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "snapshots",
        "prices",
        "registered_snapshots",
        "ticker_outcomes",
        "signal_outcomes",
        "regime_outcomes",
    } <= tables
    db.ensure_schema(conn)  # idempotent


def test_connect_wal_uri(tmp_path):
    conn = _conn(tmp_path)
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    other = tmp_path / "src.db"
    sqlite3.connect(str(other)).close()
    conn.execute("ATTACH DATABASE ? AS src", (f"file:{other}?mode=ro",))


def test_outcome_pk_prevents_dupes(tmp_path):
    conn = _conn(tmp_path)
    row = (1, "2026-07-06", "AAPL", 3, 3, 3, 0, 0, 5, "2026-07-02", 200.0, 600.0)
    ins = (
        "INSERT INTO ticker_outcomes (composite_snapshot_id,"
        " composite_date, symbol, score_sum, total, bullish, bearish,"
        " in_portfolio, horizon, entry_date, entry_close,"
        " bench_entry_close) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    conn.execute(ins, row)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, row)
    assert conn.execute("INSERT OR IGNORE INTO prices VALUES ('A','2026-07-02',1.0)").rowcount == 1
    assert conn.execute("INSERT OR IGNORE INTO prices VALUES ('A','2026-07-02',1.0)").rowcount == 0
