from sources.screeners.edgar_screener.db import connect, ensure_schema

TABLES = {"snapshots", "filings", "issuers"}
VIEWS = {"v_latest", "v_tickered", "v_insider_activity", "v_events",
         "v_stakes", "v_offerings", "v_activity_history"}


def test_schema_creates_tables_and_views():
    conn = connect(":memory:")
    ensure_schema(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')").fetchall()}
    assert TABLES <= names
    assert VIEWS <= names


def test_ensure_schema_is_idempotent():
    conn = connect(":memory:")
    ensure_schema(conn)
    ensure_schema(conn)  # must not raise
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='filings'").fetchone()[0] == 1
