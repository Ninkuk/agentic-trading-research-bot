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


def test_qty_xor_notional_constraint(conn):
    # Exactly one of qty/notional: both, neither, and sub-$1 notional all refuse.
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, qty, notional, ref_price, max_gap_pct,"
            " expires_on, queued_at) VALUES ('X', 1, 10.0, 10, 3, '2026-07-28', 't')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, ref_price, max_gap_pct, expires_on, queued_at)"
            " VALUES ('X', 10, 3, '2026-07-28', 't')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO queue (symbol, notional, ref_price, max_gap_pct,"
            " expires_on, queued_at) VALUES ('X', 0.50, 10, 3, '2026-07-28', 't')"
        )
    conn.execute(
        "INSERT INTO queue (symbol, notional, ref_price, max_gap_pct, expires_on,"
        " queued_at) VALUES ('X', 10.0, 10, 3, '2026-07-28', 't')"
    )


_PRE_NOTIONAL_QUEUE = """
CREATE TABLE queue (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol            TEXT NOT NULL,
    qty               INTEGER NOT NULL CHECK (qty > 0),
    ref_price         REAL NOT NULL CHECK (ref_price >= 1.0),
    max_gap_pct       REAL NOT NULL CHECK (max_gap_pct >= 0),
    expires_on        TEXT NOT NULL,
    note              TEXT,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
        ('queued','planned','placed','vetoed','expired','failed')),
    ref_id            TEXT UNIQUE,
    planned_limit     TEXT,
    queued_at         TEXT NOT NULL,
    resolved_at       TEXT,
    resolution_reason TEXT
);
CREATE VIEW v_open_queue AS
SELECT id, symbol, qty, ref_price, max_gap_pct, expires_on, note, queued_at
FROM queue WHERE status = 'queued' ORDER BY id;
"""


def test_migration_from_pre_notional_schema(tmp_path):
    # A live pre-notional DB (the 2026-07-28 shape) is rebuilt in place:
    # rows keep their ids with notional NULL, the placements FK still points
    # at 'queue', and the recreated views expose the new column.
    path = str(tmp_path / "orders.db")
    old = sqlite3.connect(path)
    old.executescript(_PRE_NOTIONAL_QUEUE)
    old.execute(
        "INSERT INTO queue (id, symbol, qty, ref_price, max_gap_pct, expires_on,"
        " status, queued_at) VALUES (7, 'DECK', 1, 103.0, 3, '2026-07-28', 'placed', 't')"
    )
    old.commit()
    old.close()
    conn = db.connect(path)
    db.ensure_schema(conn)
    row = conn.execute("SELECT id, symbol, qty, notional, status FROM queue").fetchone()
    assert row == (7, "DECK", 1, None, "placed")
    # New-shape insert works and the migrated view exposes notional.
    conn.execute(
        "INSERT INTO queue (symbol, notional, ref_price, max_gap_pct, expires_on,"
        " queued_at) VALUES ('INTU', 10.0, 312.0, 3, '2026-07-31', 't')"
    )
    (open_row,) = conn.execute("SELECT symbol, qty, notional FROM v_open_queue").fetchall()
    assert open_row == ("INTU", None, 10.0)
    # AUTOINCREMENT continued past the copied id.
    assert conn.execute("SELECT MAX(id) FROM queue").fetchone()[0] > 7
    # No placements FK drift: the referenced table is still named 'queue'.
    fk = conn.execute("PRAGMA foreign_key_list(placements)").fetchall()
    assert {f[2] for f in fk} == {"queue", "runs"}
    conn.close()


def test_ensure_schema_migration_idempotent(tmp_path):
    path = str(tmp_path / "orders.db")
    for _ in range(2):
        conn = db.connect(path)
        db.ensure_schema(conn)
        conn.close()


def test_fresh_schema_accepts_cancelled_status(conn):
    conn.execute(
        "INSERT INTO queue (symbol, qty, ref_price, max_gap_pct, expires_on,"
        " status, queued_at) VALUES ('X', 1, 10, 3, '2026-08-04', 'cancelled', 't')"
    )


_PRE_CANCELLED_QUEUE = """
CREATE TABLE queue (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol            TEXT NOT NULL,
    qty               INTEGER CHECK (qty IS NULL OR qty > 0),
    notional          REAL CHECK (notional IS NULL OR notional >= 1.0),
    ref_price         REAL NOT NULL CHECK (ref_price >= 1.0),
    max_gap_pct       REAL NOT NULL CHECK (max_gap_pct >= 0),
    expires_on        TEXT NOT NULL,
    note              TEXT,
    status            TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
        ('queued','planned','placed','vetoed','expired','failed')),
    ref_id            TEXT UNIQUE,
    planned_limit     TEXT,
    queued_at         TEXT NOT NULL,
    resolved_at       TEXT,
    resolution_reason TEXT,
    CHECK ((qty IS NOT NULL) + (notional IS NOT NULL) = 1)
);
CREATE VIEW v_open_queue AS
SELECT id, symbol, qty, notional, ref_price, max_gap_pct, expires_on, note, queued_at
FROM queue WHERE status = 'queued' ORDER BY id;
"""


def test_migration_from_pre_cancelled_schema(tmp_path):
    # A live post-notional DB (the 2026-07-31 shape) has the six-status CHECK
    # baked into its DDL; ensure_schema must rebuild it in place so 'cancelled'
    # is accepted, preserving row ids and the placements FK target.
    path = str(tmp_path / "orders.db")
    old = sqlite3.connect(path)
    old.executescript(_PRE_CANCELLED_QUEUE)
    old.execute(
        "INSERT INTO queue (id, symbol, notional, ref_price, max_gap_pct, expires_on,"
        " status, queued_at) VALUES (6, 'LOPE', 10.0, 149.81, 3, '2026-08-04', 'queued', 't')"
    )
    old.commit()
    old.close()
    conn = db.connect(path)
    db.ensure_schema(conn)
    conn.execute("UPDATE queue SET status='cancelled' WHERE id=6")
    row = conn.execute("SELECT id, symbol, notional, status FROM queue").fetchone()
    assert row == (6, "LOPE", 10.0, "cancelled")
    fk = conn.execute("PRAGMA foreign_key_list(placements)").fetchall()
    assert {f[2] for f in fk} == {"queue", "runs"}
    conn.close()
