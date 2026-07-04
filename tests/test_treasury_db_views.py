from sources.screeners.treasury_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_yield_curve_latest_spread_and_inverted_flag():
    conn = _fresh()
    base = {c: None for c in ["mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2",
                              "yr3", "yr5", "yr7", "yr10", "yr20", "yr30"]}
    db.write_yield_curve(conn, [
        {**base, "record_date": "2026-01-01", "yr2": 3.0, "yr10": 4.0, "mo3": 3.5},
        {**base, "record_date": "2026-02-01", "yr2": 4.5, "yr10": 4.0, "mo3": 4.8},
    ])
    row = conn.execute("SELECT record_date, spread_2s10s, inverted "
                       "FROM v_yield_curve_latest").fetchone()
    assert row[0] == "2026-02-01"           # newest
    assert abs(row[1] - (-0.5)) < 1e-9      # 4.0 - 4.5
    assert row[2] == 1                      # inverted (spread < 0)


def test_v_upcoming_auctions_filters_future_ordered():
    conn = _fresh()
    db.write_upcoming_auctions(conn, [
        {"cusip": None, "security_type": "Bill", "security_term": "4-Week",
         "announcement_date": None, "auction_date": "2000-01-01", "issue_date": None},
        {"cusip": None, "security_type": "Note", "security_term": "10-Year",
         "announcement_date": None, "auction_date": "2099-01-01", "issue_date": None},
    ])
    dates = [r[0] for r in conn.execute(
        "SELECT auction_date FROM v_upcoming_auctions")]
    assert dates == ["2099-01-01"]          # past dropped


def test_v_debt_trend_delta_vs_prior():
    conn = _fresh()
    db.write_debt_penny(conn, [
        {"record_date": "2026-01-01", "tot_pub_debt_out": 100.0,
         "debt_held_public": None, "intragov_hold": None},
        {"record_date": "2026-01-02", "tot_pub_debt_out": 130.0,
         "debt_held_public": None, "intragov_hold": None},
    ])
    row = conn.execute("SELECT change_vs_prior FROM v_debt_trend "
                       "WHERE record_date='2026-01-02'").fetchone()
    assert row[0] == 30.0


def test_v_auction_demand_latest_per_term():
    conn = _fresh()
    for d, btc in [("2026-01-01", 2.0), ("2026-02-01", 3.0)]:
        db.write_auction_results(conn, [{"cusip": f"c{d}", "auction_date": d,
            "security_type": "Note", "security_term": "10-Year", "high_yield": 4.0,
            "bid_to_cover_ratio": btc, "offering_amt": None, "total_accepted": None}])
    row = conn.execute("SELECT auction_date, latest_btc, avg_btc FROM "
                       "v_auction_demand WHERE security_term='10-Year'").fetchone()
    assert row[0] == "2026-02-01" and row[1] == 3.0
    assert abs(row[2] - 2.5) < 1e-9         # average of 2.0 and 3.0
