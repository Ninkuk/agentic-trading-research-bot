from cboe_stats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_write_vix_column_merge_does_not_blank_siblings():
    conn = _fresh()
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 14.0, "high": 15.0,
                                "low": 13.5, "close": 14.6}])
    db.write_vix(conn, "VIX3M", [{"date": "2026-06-01", "open": None,
                                  "high": None, "low": None, "close": 16.2}])
    row = conn.execute(
        "SELECT close, vix3m FROM vix_daily WHERE date='2026-06-01'").fetchone()
    assert row == (14.6, 16.2)                   # VIX close preserved, vix3m added


def test_write_vix_reupsert_overwrites_in_place():
    conn = _fresh()
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 1, "high": 1,
                                "low": 1, "close": 14.6}])
    db.write_vix(conn, "VIX", [{"date": "2026-06-01", "open": 1, "high": 1,
                                "low": 1, "close": 15.0}])
    assert conn.execute("SELECT close FROM vix_daily").fetchall() == [(15.0,)]


def test_write_pcr_upsert():
    conn = _fresh()
    n = db.write_pcr(conn, [{"date": "2026-06-01", "total_pcr": 0.95,
                             "equity_pcr": 0.72, "index_pcr": 1.4,
                             "total_volume": 45000000}])
    assert n == 1
    assert conn.execute("SELECT equity_pcr FROM pcr_daily").fetchone()[0] == 0.72


def test_prune_snapshots_not_facts():
    conn = _fresh()
    db.write_pcr(conn, [{"date": "2026-06-01", "total_pcr": 1.0, "equity_pcr": 1.0,
                         "index_pcr": 1.0, "total_volume": 1}])
    db.write_snapshot(conn, "2026-01-01T00:00:00+00:00", 1, 1)
    db.write_snapshot(conn, "2026-07-03T00:00:00+00:00", 1, 1)
    removed = db.prune(conn, keep_days=30, now_iso="2026-07-03T00:00:00+00:00")
    assert removed == 1
    assert conn.execute("SELECT COUNT(*) FROM pcr_daily").fetchone()[0] == 1
