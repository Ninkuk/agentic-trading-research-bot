# tests/test_ftd_db_write.py
from ftd_screener import db


def _rows(*specs):
    """spec tuples: (cusip, settlement_date, symbol, quantity, price)."""
    out = []
    for cusip, date, symbol, qty, price in specs:
        out.append({
            "cusip": cusip, "settlement_date": date, "symbol": symbol,
            "quantity": qty, "price": price, "description": f"{symbol} corp",
            "dollar_value": (qty * price if price is not None else None),
        })
    return out


def test_replace_period_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("A", "2025-05-01", "AA", 100, 1.0),
               ("B", "2025-05-01", "BB", 200, 2.0))
    db.upsert_securities(conn, v1)
    assert db.replace_period(conn, "202505a", v1) == 2
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 2

    # repost drops B and revises A's quantity
    v2 = _rows(("A", "2025-05-01", "AA", 150, 1.0))
    db.upsert_securities(conn, v2)
    assert db.replace_period(conn, "202505a", v2) == 1
    assert [tuple(r) for r in conn.execute(
        "SELECT cusip, quantity FROM fails")] == [("A", 150)]


def test_upsert_securities_tracks_first_last_seen_and_latest_label():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("A", "2025-05-01", "OLD", 1, None)))
    db.upsert_securities(conn, _rows(("A", "2025-05-20", "NEW", 1, None)))
    db.upsert_securities(conn, _rows(("A", "2025-04-01", "EARLY", 1, None)))
    row = conn.execute(
        "SELECT symbol, first_seen, last_seen FROM securities "
        "WHERE cusip='A'").fetchone()
    assert tuple(row) == ("NEW", "2025-04-01", "2025-05-20")


def test_stored_periods_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_period(conn, "202505a", ("2025-05-01", "2025-05-15"), "t", 10, 10)
    db.record_period(conn, "202504b", ("2025-04-16", "2025-04-30"), "t", 5, 5)
    assert db.stored_periods(conn) == ["202504b", "202505a"]


def test_prune_removes_old_snapshots_only():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("A", "2025-05-01", "AA", 1, None)))
    db.replace_period(conn, "202505a", _rows(("A", "2025-05-01", "AA", 1, None)))
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 1  # untouched
