import sqlite3

import pytest

from sources.screeners.orders import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def test_tables_and_views_exist(conn):
    names = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    }
    assert {
        "queue",
        "runs",
        "placements",
        "v_open_queue",
        "v_run_results",
        "v_unreconciled",
    } <= names


def test_ensure_schema_idempotent(conn):
    db.ensure_schema(conn)  # second call must not raise


def test_status_check_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, qty, ref_price, max_gap_pct, expires_on,"
            " status, queued_at) VALUES ('X', 1, 10, 3, '2026-07-28', 'bogus', 't')"
        )


def test_qty_and_ref_price_constraints(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, qty, ref_price, max_gap_pct, expires_on, queued_at)"
            " VALUES ('X', 0, 10, 3, '2026-07-28', 't')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, qty, ref_price, max_gap_pct, expires_on, queued_at)"
            " VALUES ('X', 1, 0.40, 3, '2026-07-28', 't')"
        )
