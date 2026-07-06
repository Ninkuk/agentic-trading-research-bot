from sources.screeners.finra_ats import db


def _seed():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    rows = [
        {
            "week_start": "2026-06-01",
            "symbol": "A",
            "mpid": "M1",
            "ats_name": "Pool One",
            "trade_count": 3,
            "share_quantity": 100,
            "tier": "T1",
        },
        {
            "week_start": "2026-06-08",
            "symbol": "A",
            "mpid": "M1",
            "ats_name": "Pool One",
            "trade_count": 5,
            "share_quantity": 300,
            "tier": "T1",
        },
        {
            "week_start": "2026-06-08",
            "symbol": "A",
            "mpid": "M2",
            "ats_name": "Pool Two",
            "trade_count": 2,
            "share_quantity": 50,
            "tier": "T1",
        },
        {
            "week_start": "2026-06-08",
            "symbol": "B",
            "mpid": "M1",
            "ats_name": "Pool One",
            "trade_count": 1,
            "share_quantity": 400,
            "tier": "T1",
        },
    ]
    db.upsert_venues(conn, rows)
    for w in ("2026-06-01", "2026-06-08"):
        db.replace_week(conn, w, [r for r in rows if r["week_start"] == w])
    return conn


def test_v_latest_off_exchange_aggregates_newest_week_by_symbol():
    conn = _seed()
    rows = conn.execute("SELECT symbol, total_shares FROM v_latest_off_exchange").fetchall()
    # newest week 2026-06-08: B=400, A=300+50=350 -> B first
    assert rows == [("B", 400), ("A", 350)]


def test_v_top_dark_pools_ranks_venues_with_name():
    conn = _seed()
    rows = conn.execute("SELECT mpid, ats_name, total_shares FROM v_top_dark_pools").fetchall()
    # newest week: M1 = 300+400 = 700, M2 = 50
    assert rows[0] == ("M1", "Pool One", 700)
    assert rows[1] == ("M2", "Pool Two", 50)


def test_v_symbol_venue_history_series():
    conn = _seed()
    rows = conn.execute(
        "SELECT week_start, share_quantity FROM v_symbol_venue_history "
        "WHERE symbol='A' AND mpid='M1' ORDER BY week_start"
    ).fetchall()
    assert rows == [("2026-06-01", 100), ("2026-06-08", 300)]
