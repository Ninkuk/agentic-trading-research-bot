# tests/test_finra_short_interest_db_write.py
from sources.screeners.finra_short_interest import db


def _rows(*specs):
    """spec tuples: (symbol, settlement_date, issue_name, current_short_qty)."""
    out = []
    for symbol, sdate, issue, cur in specs:
        out.append(
            {
                "symbol": symbol,
                "issue_name": issue,
                "settlement_date": sdate,
                "current_short_qty": cur,
                "previous_short_qty": None,
                "avg_daily_volume": 200000,
                "days_to_cover": 1.0,
                "change_pct": 0.0,
                "revision_flag": None,
                "market_class": "NNM",
            }
        )
    return out


def test_replace_settlement_replaces_and_drops_removed_rows():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    v1 = _rows(("AA", "2024-06-14", "ALPHA", 100), ("BB", "2024-06-14", "BETA", 300))
    db.upsert_securities(conn, v1)
    assert db.replace_settlement(conn, "2024-06-14", v1) == 2
    assert conn.execute("SELECT COUNT(*) FROM short_interest").fetchone()[0] == 2

    # repost drops BB and revises AA's current_short_qty
    v2 = _rows(("AA", "2024-06-14", "ALPHA", 150))
    db.upsert_securities(conn, v2)
    assert db.replace_settlement(conn, "2024-06-14", v2) == 1
    assert [
        tuple(r) for r in conn.execute("SELECT symbol, current_short_qty FROM short_interest")
    ] == [("AA", 150)]


def test_upsert_securities_refreshes_issue_name_to_newest_and_tracks_seen():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.upsert_securities(conn, _rows(("AA", "2024-06-14", "OLD CO", 1)))
    db.upsert_securities(conn, _rows(("AA", "2024-07-15", "NEW CO", 1)))
    db.upsert_securities(conn, _rows(("AA", "2024-05-15", "ANCIENT CO", 1)))
    issue, first, last = conn.execute(
        "SELECT issue_name, first_seen, last_seen FROM securities WHERE symbol='AA'"
    ).fetchone()
    assert issue == "NEW CO"  # newest settlement wins
    assert (first, last) == ("2024-05-15", "2024-07-15")


def test_stored_settlements_sorted_and_record_upserts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    db.record_settlement(conn, "2024-06-28", "t", 10)
    db.record_settlement(conn, "2024-06-14", "t", 5)
    db.record_settlement(conn, "2024-06-28", "t2", 11)  # upsert, not duplicate
    assert db.stored_settlements(conn) == ["2024-06-14", "2024-06-28"]


def test_prune_removes_old_snapshots_only_and_keeps_facts():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    facts = _rows(("AA", "2024-06-14", "ALPHA", 1))
    db.upsert_securities(conn, facts)
    db.replace_settlement(conn, "2024-06-14", facts)
    now = "2026-07-03T00:00:00+00:00"
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, now, 1, 1)
    assert db.prune(conn, 30, now) == 1
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM short_interest").fetchone()[0] == 1  # untouched
