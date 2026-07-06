from sources.screeners.cboe_stats import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_pcr_extremes_flags_fear_at_high_percentile():
    conn = _fresh()
    for d, e in [
        ("2026-06-01", 0.5),
        ("2026-06-02", 0.6),
        ("2026-06-03", 0.7),
        ("2026-06-04", 0.8),
        ("2026-06-05", 1.2),
    ]:  # latest highest
        db.write_pcr(
            conn,
            [{"date": d, "total_pcr": e, "equity_pcr": e, "index_pcr": None, "total_volume": None}],
        )
    row = conn.execute("SELECT equity_pcr_pctile, equity_flag FROM v_pcr_extremes").fetchone()
    assert row[0] == 0.8 and row[1] == "fear"  # 4/5 of history below 1.2


def test_v_vix_term_structure_backwardation_flag():
    conn = _fresh()
    db.write_vix(
        conn,
        "VIX",
        [{"date": "2026-06-01", "open": None, "high": None, "low": None, "close": 20.0}],
    )
    db.write_vix(
        conn,
        "VIX3M",
        [{"date": "2026-06-01", "close": 18.0, "open": None, "high": None, "low": None}],
    )
    row = conn.execute("SELECT backwardation FROM v_vix_term_structure").fetchone()
    assert row[0] == 1  # close 20 > vix3m 18 -> stress


def test_v_latest_sentiment_one_row():
    conn = _fresh()
    db.write_pcr(
        conn,
        [
            {
                "date": "2026-06-01",
                "total_pcr": 0.9,
                "equity_pcr": 0.7,
                "index_pcr": None,
                "total_volume": None,
            }
        ],
    )
    db.write_vix(
        conn,
        "VIX",
        [{"date": "2026-06-01", "open": None, "high": None, "low": None, "close": 14.6}],
    )
    rows = conn.execute("SELECT vix_close, equity_pcr FROM v_latest_sentiment").fetchall()
    assert rows == [(14.6, 0.7)]
