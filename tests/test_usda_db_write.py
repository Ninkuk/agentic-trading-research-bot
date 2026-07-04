from sources.screeners.usda_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_observations_upsert_in_place():
    conn = _fresh()
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 1800.0, "unit": "BU"}])
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 1875.0, "unit": "BU"}])
    assert conn.execute("SELECT value FROM usda_obs").fetchall() == [(1875.0,)]


def test_v_stocks_to_use_ratio():
    conn = _fresh()
    db.write_observations(conn, "CORN", "ENDING_STOCKS",
                          [{"period": "2025", "value": 2000.0, "unit": "BU"}])
    db.write_observations(conn, "CORN", "TOTAL_USE",
                          [{"period": "2025", "value": 14000.0, "unit": "BU"}])
    row = conn.execute("SELECT ending_stocks, total_use, stocks_to_use "
                       "FROM v_stocks_to_use WHERE commodity='CORN'").fetchone()
    assert row[0] == 2000.0 and row[1] == 14000.0
    assert abs(row[2] - (2000.0 / 14000.0)) < 1e-9


def test_v_stocks_to_use_null_when_total_use_absent():
    conn = _fresh()
    db.write_observations(conn, "WHEAT", "ENDING_STOCKS",
                          [{"period": "2025", "value": 800.0, "unit": "BU"}])
    row = conn.execute("SELECT total_use, stocks_to_use FROM v_stocks_to_use "
                       "WHERE commodity='WHEAT'").fetchone()
    assert row == (None, None)                    # partial selection -> NULL


def test_prune_snapshots_not_obs():
    conn = _fresh()
    db.write_observations(conn, "CORN", "PRODUCTION",
                          [{"period": "2025", "value": 15000.0, "unit": "BU"}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM usda_obs").fetchone()[0] == 1
