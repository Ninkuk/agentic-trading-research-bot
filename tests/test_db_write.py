import json
import sqlite3

from sources.screeners.stock_analysis_screener.db import (
    connect,
    ensure_schema,
    prune,
    write_snapshot,
)


def setup_conn():
    conn = connect(":memory:")
    ensure_schema(conn, {"price": "REAL", "sector": "TEXT"})
    return conn


def test_write_snapshot_stores_rows_and_returns_id():
    conn = setup_conn()
    data = {
        "AAA": {"price": 10.0, "sector": "Tech"},
        "BBB": {"price": 20.0},
    }  # BBB missing sector -> NULL
    sid = write_snapshot(conn, "2026-07-02T00:00:00+00:00", "src", data, ["price", "sector"])
    assert isinstance(sid, int)
    count = conn.execute("SELECT universe_count FROM snapshots WHERE id=?", (sid,)).fetchone()[0]
    assert count == 2
    row = conn.execute(
        "SELECT price, sector FROM metrics WHERE snapshot_id=? AND symbol='BBB'", (sid,)
    ).fetchone()
    assert row == (20.0, None)


def test_v_latest_returns_only_newest_snapshot():
    conn = setup_conn()
    write_snapshot(
        conn, "2026-07-01T00:00:00+00:00", "src", {"AAA": {"price": 1.0}}, ["price", "sector"]
    )
    write_snapshot(
        conn, "2026-07-02T00:00:00+00:00", "src", {"AAA": {"price": 2.0}}, ["price", "sector"]
    )
    prices = [r[0] for r in conn.execute("SELECT price FROM v_latest").fetchall()]
    assert prices == [2.0]


def test_prune_removes_old_snapshots_and_their_metrics():
    conn = setup_conn()
    old = write_snapshot(
        conn, "2026-06-01T00:00:00+00:00", "src", {"AAA": {"price": 1.0}}, ["price", "sector"]
    )
    write_snapshot(
        conn, "2026-07-02T00:00:00+00:00", "src", {"AAA": {"price": 2.0}}, ["price", "sector"]
    )
    deleted = prune(conn, keep_days=7, now_iso="2026-07-02T00:00:00+00:00")
    assert deleted == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert (
        conn.execute("SELECT COUNT(*) FROM metrics WHERE snapshot_id=?", (old,)).fetchone()[0] == 0
    )


def test_write_snapshot_json_encodes_nonscalar_values():
    # stockanalysis.com now returns arrays for some Company-Info data-points
    # (e.g. inIndex=["SP500","NASDAQ100"], tags=["clean-energy"]). SQLite cannot
    # bind a list/dict, so the writer must JSON-encode non-scalars to TEXT
    # (reversible + queryable via json_each) rather than crash.
    conn = setup_conn()
    ensure_schema(conn, {"inIndex": "TEXT", "tags": "TEXT"})
    data = {"AAA": {"price": 10.0, "inIndex": ["SP500", "NASDAQ100"], "tags": ["clean-energy"]}}
    sid = write_snapshot(
        conn, "2026-07-02T00:00:00+00:00", "src", data, ["price", "inIndex", "tags"]
    )
    row = conn.execute(
        "SELECT price, inIndex, tags FROM metrics WHERE snapshot_id=? AND symbol='AAA'", (sid,)
    ).fetchone()
    assert row[0] == 10.0  # scalars pass through untouched
    assert json.loads(row[1]) == ["SP500", "NASDAQ100"]
    assert json.loads(row[2]) == ["clean-energy"]


def test_ensure_schema_and_write_handle_embedded_quote_identifier():
    weird = 'a"b'
    conn = connect(":memory:")
    ensure_schema(conn, {weird: "REAL"})
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()}
    assert weird in cols

    write_snapshot(conn, "2026-07-02T00:00:00+00:00", "src", {"AAA": {weird: 1.5}}, [weird])

    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM metrics WHERE symbol='AAA'").fetchone()
    assert row[weird] == 1.5
