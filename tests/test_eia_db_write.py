from sources.screeners.eia_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _meta(sid, unit="MBBL", label="L", cat="crude"):
    return {
        "series_id": sid,
        "route": "r",
        "label": label,
        "category": cat,
        "unit": unit,
        "frequency": "weekly",
    }


def test_write_observations_upsert_in_place():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1")], "t")
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 100.0}])
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 105.0}])
    assert conn.execute("SELECT value FROM eia_obs").fetchall() == [(105.0,)]


def test_upsert_series_preserves_first_seen_refreshes_meta():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1", unit="MBBL")], "t1")
    db.upsert_series(conn, [_meta("S1", unit="MBBL2")], "t2")
    row = conn.execute(
        "SELECT unit, first_seen, last_seen FROM series WHERE series_id='S1'"
    ).fetchone()
    assert row == ("MBBL2", "t1", "t2")


def test_prune_snapshots_not_obs():
    conn = _fresh()
    db.upsert_series(conn, [_meta("S1")], "t")
    db.write_observations(conn, "S1", [{"period": "2026-06-26", "value": 1.0}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM eia_obs").fetchone()[0] == 1
