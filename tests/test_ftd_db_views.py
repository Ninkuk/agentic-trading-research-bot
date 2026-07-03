# tests/test_ftd_db_views.py
from ftd_screener import db


def _seed(conn, cusip, series):
    """series: list of (settlement_date, quantity). Seeds one cusip under its
    own period label (replace_period deletes by period, so per-cusip labels
    keep seeds independent)."""
    rows = [{"cusip": cusip, "settlement_date": d, "symbol": cusip,
             "quantity": q, "price": 1.0, "description": cusip,
             "dollar_value": float(q)} for d, q in series]
    db.upsert_securities(conn, rows)
    db.replace_period(conn, f"seed-{cusip}", rows)


def test_v_persistent_active_streak_of_six():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    dates = ["2025-05-01", "2025-05-02", "2025-05-05",
             "2025-05-06", "2025-05-07", "2025-05-08"]
    _seed(conn, "A", [(d, 20000) for d in dates])
    row = conn.execute(
        "SELECT streak_days, active FROM v_persistent WHERE cusip='A'").fetchone()
    assert tuple(row) == (6, 1)


def test_v_fail_streaks_below_threshold_day_splits_streak():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    # 3 days >=10k, one day <10k (present but excluded), 3 more days >=10k
    _seed(conn, "A", [("2025-05-01", 20000), ("2025-05-02", 20000),
                      ("2025-05-05", 20000), ("2025-05-06", 5000),
                      ("2025-05-07", 20000), ("2025-05-08", 20000),
                      ("2025-05-09", 20000)])
    streaks = sorted(r[0] for r in conn.execute(
        "SELECT streak_days FROM v_fail_streaks WHERE cusip='A'"))
    assert streaks == [3, 3]
    assert conn.execute(
        "SELECT COUNT(*) FROM v_persistent WHERE cusip='A'").fetchone()[0] == 0


def test_v_spikes_ratio_against_trailing_average():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn, "A", [("2025-05-01", 1000), ("2025-05-02", 1000),
                      ("2025-05-05", 1000), ("2025-05-06", 1000),
                      ("2025-05-07", 5000)])
    q, base, ratio = conn.execute(
        "SELECT quantity, base, spike_ratio FROM v_spikes "
        "WHERE cusip='A'").fetchone()
    assert q == 5000
    assert base == 1000.0
    assert ratio == 5.0


def test_v_latest_fails_returns_only_max_date():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn, "A", [("2025-05-01", 100), ("2025-05-07", 200)])
    _seed(conn, "B", [("2025-05-07", 300)])
    got = {r[0]: r[1] for r in conn.execute(
        "SELECT cusip, quantity FROM v_latest_fails")}
    assert got == {"A": 200, "B": 300}
