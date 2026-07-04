from sources.screeners.finra_ats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _row(week, symbol, mpid, shares=100, ats_name="ATS", tc=5, tier="T1"):
    return {"week_start": week, "symbol": symbol, "mpid": mpid,
            "ats_name": ats_name, "trade_count": tc, "share_quantity": shares,
            "tier": tier}


def test_upsert_venues_refreshes_name_and_extends_seen_window():
    conn = _fresh()
    db.upsert_venues(conn, [_row("2026-06-08", "A", "UBSA", ats_name="UBS ATS")])
    db.upsert_venues(conn, [_row("2026-06-15", "A", "UBSA", ats_name="UBS ATS v2")])
    row = conn.execute(
        "SELECT ats_name, first_seen, last_seen FROM venues WHERE mpid='UBSA'"
    ).fetchone()
    assert row == ("UBS ATS v2", "2026-06-08", "2026-06-15")


def test_replace_week_replaces_and_dedupes():
    conn = _fresh()
    db.upsert_venues(conn, [_row("2026-06-08", "A", "M1")])
    db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1", shares=100),
                                         _row("2026-06-08", "A", "M2", shares=50)])
    # a re-post that drops M2 leaves no orphan
    n = db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1", shares=200)])
    assert n == 1
    rows = conn.execute("SELECT mpid, share_quantity FROM ats_volume "
                        "ORDER BY mpid").fetchall()
    assert rows == [("M1", 200)]                 # M2 gone, M1 replaced


def test_record_week_stored_weeks_and_prune():
    conn = _fresh()
    db.replace_week(conn, "2026-06-08", [_row("2026-06-08", "A", "M1")])
    db.record_week(conn, "2026-06-08", "t", 1)
    db.record_week(conn, "2026-06-01", "t", 1)
    assert db.stored_weeks(conn) == ["2026-06-01", "2026-06-08"]
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM ats_volume").fetchone()[0] == 1
