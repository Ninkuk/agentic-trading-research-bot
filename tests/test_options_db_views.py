from sources.screeners.cboe_options import db

FA = "2026-07-03T00:00:00+00:00"


def _contract_row(underlying, snapshot_date, strike):
    return {
        "occ_symbol": f"{underlying}{snapshot_date[2:4]}{snapshot_date[5:7]}"
        f"{snapshot_date[8:10]}C{int(strike * 1000):08d}",
        "underlying": underlying,
        "expiration": "2026-08-21",
        "strike": strike,
        "type": "call",
        "bid": 1.0,
        "ask": 1.2,
        "mark": 1.1,
        "last": 1.1,
        "theo": 1.1,
        "iv": 0.3,
        "delta": 0.5,
        "gamma": 0.01,
        "theta": -0.1,
        "vega": 0.2,
        "rho": 0.05,
        "open_interest": 100,
        "volume": 250,
        "underlying_price": 100.0,
        "vol_oi_ratio": 2.5,
    }


def _daily_row(underlying, iv30):
    return {
        "underlying": underlying,
        "underlying_price": 100.0,
        "close": 100.5,
        "iv30": iv30,
        "total_call_volume": 250,
        "total_put_volume": 100,
        "put_call_volume_ratio": 0.4,
        "total_call_oi": 100,
        "total_put_oi": 80,
        "put_call_oi_ratio": 0.8,
    }


def _seed(conn):
    """Two underlyings, AAA and BBB, whose latest snapshot dates differ:
    AAA's latest is 2026-07-02, BBB's latest (and the run's global MAX) is
    2026-07-03. A per-underlying-latest view must keep both; a global-MAX
    view would silently drop AAA."""
    db.upsert_underlying(conn, "AAA", False, "2026-07-01")
    db.upsert_underlying_daily(conn, "2026-07-01", _daily_row("AAA", 10.0))
    db.upsert_underlying_daily(conn, "2026-07-02", _daily_row("AAA", 20.0))
    db.replace_day(conn, "2026-07-02", "AAA", [_contract_row("AAA", "2026-07-02", 150.0)], FA)

    db.upsert_underlying(conn, "BBB", False, "2026-07-03")
    db.upsert_underlying_daily(conn, "2026-07-03", _daily_row("BBB", 30.0))
    db.replace_day(conn, "2026-07-03", "BBB", [_contract_row("BBB", "2026-07-03", 250.0)], FA)


def test_v_latest_sentiment_is_per_underlying_latest_not_global_max():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn)
    rows = conn.execute(
        "SELECT underlying, snapshot_date FROM v_latest_sentiment ORDER BY underlying"
    ).fetchall()
    assert rows == [("AAA", "2026-07-02"), ("BBB", "2026-07-03")]


def test_v_unusual_activity_includes_both_underlyings_own_latest_day():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn)
    rows = conn.execute(
        "SELECT underlying, snapshot_date FROM v_unusual_activity ORDER BY underlying"
    ).fetchall()
    assert rows == [("AAA", "2026-07-02"), ("BBB", "2026-07-03")]


def test_v_iv_rank_includes_both_underlyings_own_latest_day():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    _seed(conn)
    rows = {
        r[0]: r
        for r in conn.execute("SELECT underlying, snapshot_date, iv30, iv_rank FROM v_iv_rank")
    }
    assert set(rows) == {"AAA", "BBB"}
    # AAA's latest iv30 (20.0) is the max of its own [10.0, 20.0] history
    # => iv_rank 100.0. AAA must NOT be evicted by BBB's later global date.
    assert rows["AAA"][1] == "2026-07-02"
    assert rows["AAA"][2] == 20.0
    assert rows["AAA"][3] == 100.0
    assert rows["BBB"][1] == "2026-07-03"
    assert rows["BBB"][2] == 30.0
