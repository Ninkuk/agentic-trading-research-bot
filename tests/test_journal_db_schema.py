import sqlite3

import pytest

from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def test_tables_exist(tmp_path):
    conn = _conn(tmp_path)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"decisions", "journal_runs"} <= names


def test_ensure_schema_idempotent(tmp_path):
    conn = _conn(tmp_path)
    db.ensure_schema(conn)  # second run must not raise


def test_action_and_side_checked(tmp_path):
    conn = _conn(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, recorded_at) VALUES ('XLE', 'held', ?)",
            (NOW,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, recorded_at)"
            " VALUES ('XLE', 'acted', 'short', ?)",
            (NOW,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, source, recorded_at)"
            " VALUES ('XLE', 'acted', 'api', ?)",
            (NOW,),
        )


def test_order_ref_unique_but_nulls_ok(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, order_ref, recorded_at)"
        " VALUES ('XLE', 'acted', 'buy', 'ref-1', ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, order_ref, recorded_at)"
            " VALUES ('XLE', 'acted', 'buy', 'ref-1', ?)",
            (NOW,),
        )
    # manual entries: repeated NULL order_refs are fine
    for _ in range(2):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, recorded_at)"
            " VALUES ('GLD', 'acted', 'buy', ?)",
            (NOW,),
        )


def test_one_explicit_pass_per_flag(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
        " VALUES ('GLD', 'passed', 7, ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
            " VALUES ('GLD', 'passed', 7, ?)",
            (NOW,),
        )
    # same symbol, different flag: fine; acted rows unconstrained
    conn.execute(
        "INSERT INTO decisions (symbol, action, composite_snapshot_id, recorded_at)"
        " VALUES ('GLD', 'passed', 8, ?)",
        (NOW,),
    )
    for _ in range(2):
        conn.execute(
            "INSERT INTO decisions (symbol, action, side, composite_snapshot_id,"
            " recorded_at) VALUES ('GLD', 'acted', 'buy', 7, ?)",
            (NOW,),
        )


def test_one_owner_per_window(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-03', '2026-07-06', ?, 2, 0, 0)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):  # second owner, same window
        conn.execute(
            "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
            " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
            " VALUES (9, '2026-07-05', '2026-07-06', ?, 3, 0, 0)",
            (NOW,),
        )
    # marker-only siblings (ticker_rows = 0) are fine
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (2, '2026-07-05', '2026-07-06', ?, 0, 0, 0)",
        (NOW,),
    )


def test_flag_constants_exist():
    assert db.FLAG_MIN_ABS_SCORE == 4 and db.FLAG_MIN_TOTAL == 3


def test_prune_never_touches_journal(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, recorded_at)"
        " VALUES ('XLE', 'acted', 'buy', '2020-01-01T00:00:00+00:00')"
    )
    conn.execute("INSERT INTO journal_runs (ran_at) VALUES ('2020-01-01T00:00:00+00:00')")
    conn.commit()
    db.prune(conn, keep_days=1, now_iso=NOW)
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM journal_runs").fetchone()[0] == 1
