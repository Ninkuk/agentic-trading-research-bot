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


_OLD_SIGNAL_OUTCOMES = """
CREATE TABLE signal_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    entity                TEXT NOT NULL,
    score                 INTEGER NOT NULL,
    via_crosswalk         INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon)
)
"""


def test_signal_outcomes_has_benchmark_column(tmp_path):
    conn = _conn(tmp_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    assert "benchmark" in cols


def test_benchmark_column_migrates_old_db(tmp_path):
    path = str(tmp_path / "old.db")
    raw = sqlite3.connect(path)
    raw.execute(_OLD_SIGNAL_OUTCOMES)
    raw.commit()
    raw.close()
    conn = db.connect(path)
    db.ensure_schema(conn)  # must ALTER the column in before creating views
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signal_outcomes)")}
    assert "benchmark" in cols
    db.ensure_schema(conn)  # idempotent second run
    views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"v_signal_efficacy", "v_bucket_performance", "v_pending"} <= views
    # SQLite validates view column refs at QUERY time, not CREATE time —
    # actually querying proves the migrated column satisfies the views
    assert conn.execute("SELECT * FROM v_signal_efficacy").fetchall() == []


def test_research_verdict_tables_exist(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(research_verdicts)")}
    assert {"id", "symbol", "verdict", "verdict_date", "doc", "note", "recorded_at"} <= cols
    cols = {r[1] for r in conn.execute("PRAGMA table_info(verdict_outcomes)")}
    assert {
        "verdict_id",
        "symbol",
        "horizon",
        "entry_date",
        "entry_close",
        "bench_entry_close",
        "exit_date",
        "exit_close",
        "fwd_return",
        "bench_fwd_return",
        "matured_at",
    } <= cols
    cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_runs)")}
    assert "verdicts_recorded" in cols
    conn.close()


def test_research_verdict_enum_and_unique_enforced(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    ins = (
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date,"
        " recorded_at) VALUES (?, ?, ?, '2026-07-22T20:00:00+00:00')"
    )
    conn.execute(ins, ("BBAI", "pass", "2026-07-22"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("BBAI", "hold", "2026-07-23"))  # bad enum
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("BBAI", "buy", "2026-07-22"))  # dup (symbol, date)
    conn.close()


def test_verdicts_recorded_migrates_existing_db(tmp_path):
    # A journal_runs table created WITHOUT the column (pre-migration DB)
    # gains it on the next ensure_schema, like decisions.placed_agent.
    path = str(tmp_path / "scorer.db")
    conn = db.connect(path)
    conn.execute(
        "CREATE TABLE journal_runs (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " ran_at TEXT NOT NULL, fills_seen INTEGER NOT NULL DEFAULT 0,"
        " matched INTEGER NOT NULL DEFAULT 0, freelance INTEGER NOT NULL DEFAULT 0,"
        " exits_attached INTEGER NOT NULL DEFAULT 0,"
        " passes_recorded INTEGER NOT NULL DEFAULT 0,"
        " duplicates_skipped INTEGER NOT NULL DEFAULT 0,"
        " skipped INTEGER NOT NULL DEFAULT 0)"
    )
    conn.commit()
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(journal_runs)")}
    assert "verdicts_recorded" in cols
    conn.close()
