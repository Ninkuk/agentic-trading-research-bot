from sources.screeners.treasury_screener import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def test_v_yield_curve_latest_spread_and_inverted_flag():
    conn = _fresh()
    base = {
        c: None
        for c in [
            "mo1",
            "mo2",
            "mo3",
            "mo4",
            "mo6",
            "yr1",
            "yr2",
            "yr3",
            "yr5",
            "yr7",
            "yr10",
            "yr20",
            "yr30",
        ]
    }
    db.write_yield_curve(
        conn,
        [
            {**base, "record_date": "2026-01-01", "yr2": 3.0, "yr10": 4.0, "mo3": 3.5},
            {**base, "record_date": "2026-02-01", "yr2": 4.5, "yr10": 4.0, "mo3": 4.8},
        ],
    )
    row = conn.execute(
        "SELECT record_date, spread_2s10s, inverted FROM v_yield_curve_latest"
    ).fetchone()
    assert row[0] == "2026-02-01"  # newest
    assert abs(row[1] - (-0.5)) < 1e-9  # 4.0 - 4.5
    assert row[2] == 1  # inverted (spread < 0)


def test_v_upcoming_auctions_filters_future_ordered():
    conn = _fresh()
    db.write_upcoming_auctions(
        conn,
        [
            {
                "cusip": None,
                "security_type": "Bill",
                "security_term": "4-Week",
                "announcement_date": None,
                "auction_date": "2000-01-01",
                "issue_date": None,
            },
            {
                "cusip": None,
                "security_type": "Note",
                "security_term": "10-Year",
                "announcement_date": None,
                "auction_date": "2099-01-01",
                "issue_date": None,
            },
        ],
    )
    db.set_today(conn, "2050-01-01T12:00:00+00:00")
    dates = [r[0] for r in conn.execute("SELECT auction_date FROM v_upcoming_auctions")]
    assert dates == ["2099-01-01"]  # past dropped


def test_v_tga_trend_reads_both_dts_eras():
    conn = _fresh()
    db.write_dts_cash(
        conn,
        [
            # Legacy format (pre-2022-04-18): one row per account, real close col.
            {
                "record_date": "2022-04-14",
                "account_type": "Treasury General Account (TGA)",
                "open_balance": 900000.0,
                "close_balance": 910000.0,
            },
            # Modern format: the closing balance is its own account_type row whose
            # value the API publishes in open_today_bal -> open_balance.
            {
                "record_date": "2022-04-18",
                "account_type": "Treasury General Account (TGA) Opening Balance",
                "open_balance": 910000.0,
                "close_balance": None,
            },
            {
                "record_date": "2022-04-18",
                "account_type": "Treasury General Account (TGA) Closing Balance",
                "open_balance": 920000.0,
                "close_balance": None,
            },
            # Deposits/withdrawals rows must not leak into the balance series.
            {
                "record_date": "2022-04-18",
                "account_type": "Total TGA Deposits (Table II)",
                "open_balance": 50000.0,
                "close_balance": None,
            },
        ],
    )
    rows = dict(conn.execute("SELECT record_date, close_balance FROM v_tga_trend").fetchall())
    assert rows == {"2022-04-14": 910000.0, "2022-04-18": 920000.0}


def test_v_tga_trend_wow_change_spans_the_format_cutover():
    conn = _fresh()
    legacy = [
        {
            "record_date": f"2022-04-{d:02d}",
            "account_type": "Federal Reserve Account",
            "open_balance": None,
            "close_balance": 100.0 + d,
        }
        for d in (8, 11, 12, 13, 14)
    ]
    db.write_dts_cash(
        conn,
        legacy
        + [
            {
                "record_date": "2022-04-18",
                "account_type": "Treasury General Account (TGA) Closing Balance",
                "open_balance": 200.0,
                "close_balance": None,
            }
        ],
    )
    row = conn.execute(
        "SELECT close_balance, wow_change FROM v_tga_trend WHERE record_date='2022-04-18'"
    ).fetchone()
    assert row == (200.0, 200.0 - 108.0)  # LAG(5) reaches back into legacy era


def test_v_debt_trend_delta_vs_prior():
    conn = _fresh()
    db.write_debt_penny(
        conn,
        [
            {
                "record_date": "2026-01-01",
                "tot_pub_debt_out": 100.0,
                "debt_held_public": None,
                "intragov_hold": None,
            },
            {
                "record_date": "2026-01-02",
                "tot_pub_debt_out": 130.0,
                "debt_held_public": None,
                "intragov_hold": None,
            },
        ],
    )
    row = conn.execute(
        "SELECT change_vs_prior FROM v_debt_trend WHERE record_date='2026-01-02'"
    ).fetchone()
    assert row[0] == 30.0


def test_v_auction_demand_latest_per_term():
    conn = _fresh()
    for d, btc in [("2026-01-01", 2.0), ("2026-02-01", 3.0)]:
        db.write_auction_results(
            conn,
            [
                {
                    "cusip": f"c{d}",
                    "auction_date": d,
                    "security_type": "Note",
                    "security_term": "10-Year",
                    "high_yield": 4.0,
                    "bid_to_cover_ratio": btc,
                    "offering_amt": None,
                    "total_accepted": None,
                }
            ],
        )
    row = conn.execute(
        "SELECT auction_date, latest_btc, avg_btc FROM "
        "v_auction_demand WHERE security_term='10-Year'"
    ).fetchone()
    assert row[0] == "2026-02-01" and row[1] == 3.0
    assert abs(row[2] - 2.5) < 1e-9  # average of 2.0 and 3.0


def test_upcoming_auctions_uses_injected_today_not_wall_clock():
    conn = _fresh()
    conn.executemany(
        "INSERT INTO upcoming_auctions (cusip, security_type, security_term,"
        " announcement_date, auction_date, issue_date)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("A1", "Note", "10-Year", "2020-01-01", "2020-01-08", "2020-01-15"),
            ("A2", "Note", "10-Year", "2020-01-01", "2020-02-05", "2020-02-12"),
        ],
    )
    db.set_today(conn, "2020-01-20T12:00:00+00:00")
    rows = [r[0] for r in conn.execute("SELECT cusip FROM v_upcoming_auctions").fetchall()]
    assert rows == ["A2"]  # 2020 date: passes ONLY if the view ignores wall-clock


def test_ensure_schema_migrates_old_view():
    conn = db.connect(":memory:")
    conn.execute("CREATE VIEW v_upcoming_auctions AS SELECT 1 AS legacy")
    db.ensure_schema(conn)  # must drop-and-recreate, not keep the legacy body
    cols = [d[0] for d in conn.execute("SELECT * FROM v_upcoming_auctions").description]
    assert "auction_date" in cols
