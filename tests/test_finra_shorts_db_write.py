# tests/test_finra_shorts_db_write.py
from sources.screeners.finra_short_volume import db


def _rows(*specs):
    """spec tuples: (symbol, date, short_volume, total_volume)."""
    out = []
    for symbol, d, sv, tv in specs:
        out.append({"symbol": symbol, "date": d, "short_volume": sv,
                    "short_exempt_volume": 0, "total_volume": tv,
                    "short_ratio": (sv / tv if tv else None), "market": "Q"})
    return out


def test_replace_day_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("AA", "2024-06-14", 100, 200), ("BB", "2024-06-14", 300, 600))
    db.upsert_securities(conn, v1)
    assert db.replace_day(conn, "2024-06-14", v1) == 2
    assert conn.execute("SELECT COUNT(*) FROM short_volume").fetchone()[0] == 2

    # repost drops BB and revises AA's short_volume
    v2 = _rows(("AA", "2024-06-14", 150, 200))
    db.upsert_securities(conn, v2)
    assert db.replace_day(conn, "2024-06-14", v2) == 1
    assert [tuple(r) for r in conn.execute(
        "SELECT symbol, short_volume FROM short_volume")] == [("AA", 150)]


def test_upsert_securities_tracks_first_and_last_seen():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", 1, 2)))
    db.upsert_securities(conn, _rows(("AA", "2024-07-01", 1, 2)))
    db.upsert_securities(conn, _rows(("AA", "2024-05-01", 1, 2)))
    row = conn.execute(
        "SELECT first_seen, last_seen FROM securities WHERE symbol='AA'").fetchone()
    assert tuple(row) == ("2024-05-01", "2024-07-01")


def test_stored_days_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_day(conn, "2024-06-14", "t", 10)
    db.record_day(conn, "2024-05-31", "t", 5)
    db.record_day(conn, "2024-06-14", "t2", 11)   # upsert, not duplicate
    assert db.stored_days(conn) == ["2024-05-31", "2024-06-14"]


def test_prune_removes_old_snapshots_only():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", 1, 2)))
    db.replace_day(conn, "2024-06-14", _rows(("AA", "2024-06-14", 1, 2)))
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM short_volume").fetchone()[0] == 1  # untouched
