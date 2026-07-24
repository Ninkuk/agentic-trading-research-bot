from sources.combiners.advisor import db


def _row(**kw):
    base = {
        "symbol": "AAPL",
        "group_name": None,
        "quantity": 1.0,
        "market_value": 100.0,
        "avg_cost": None,
        "atr": 1.0,
        "price": 100.0,
        "price_date": "2026-07-07",
        "heat_dollars": 1.0,
        "heat_pct": 0.0001,
        "weight_pct": 0.01,
        "score_sum": 0,
        "bullish": 0,
        "bearish": 0,
        "total": 0,
        "atr_stale": 0,
    }
    base.update(kw)
    return base


def _seed(conn, captured_at, heat_rows, cap_rows=()):
    sid = db.write_snapshot(conn, captured_at)
    db.write_position_heat(conn, sid, list(heat_rows))
    db.write_size_caps(conn, sid, list(cap_rows))
    db.finish_snapshot(
        conn,
        sid,
        {"equity": 10000.0, "cash": 0.0, "buying_power": 0.0, "captured_at": captured_at},
        {"snapshot_id": 1, "captured_at": captured_at, "regime": "risk_on"},
    )
    conn.commit()
    return sid


def _fresh(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    return conn


def test_latest_views_scope_to_newest_snapshot(tmp_path):
    conn = _fresh(tmp_path)
    _seed(conn, "2026-07-06T21:12:00+00:00", [_row(symbol="OLD")])
    _seed(conn, "2026-07-07T21:12:00+00:00", [_row(symbol="NEW")])
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_latest_heat")] == ["NEW"]


def test_book_heat_totals_and_coverage(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="AAPL", market_value=1000.0, atr=2.0, heat_dollars=20.0, heat_pct=0.002),
            _row(
                symbol="NOATR",
                market_value=1000.0,
                atr=None,
                heat_dollars=None,
                heat_pct=None,
                atr_stale=None,
            ),
        ],
    )
    row = conn.execute(
        "SELECT positions, heat_dollars, heat_pct, heat_coverage FROM v_book_heat"
    ).fetchone()
    assert row == (2, 20.0, 0.002, 0.5)  # half the book's value has an ATR


def test_book_heat_empty_book_yields_a_row(tmp_path):
    conn = _fresh(tmp_path)
    _seed(conn, "2026-07-07T21:12:00+00:00", [])
    row = conn.execute("SELECT positions, heat_dollars, heat_coverage FROM v_book_heat").fetchone()
    assert row == (0, None, None)


def test_group_heat_collapses_crosswalk_groups(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="XOM", group_name="energy", heat_dollars=20.0, heat_pct=0.002),
            _row(symbol="XLE", group_name="energy", heat_dollars=10.0, heat_pct=0.001),
            _row(symbol="AAPL", group_name=None, heat_dollars=5.0, heat_pct=0.0005),
        ],
    )
    rows = {
        r[0]: (r[1], r[2])
        for r in conn.execute("SELECT bet, members, heat_dollars FROM v_group_heat")
    }
    assert rows["energy"] == (2, 30.0)
    assert rows["AAPL"] == (1, 5.0)


def test_disagreements_only_negative_scores_with_strong_flag(tmp_path):
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="LIKED", score_sum=3, total=3),
            _row(symbol="MILD", score_sum=-1, total=2),
            _row(symbol="BAD", score_sum=-4, total=3),
        ],
    )
    rows = {r[0]: r[1] for r in conn.execute("SELECT symbol, strong FROM v_disagreements")}
    assert rows == {"MILD": 0, "BAD": 1}


def test_latest_caps_scope(tmp_path):
    conn = _fresh(tmp_path)
    cap = {
        "symbol": "NVDA",
        "direction": "bullish",
        "score_sum": 4,
        "atr": 4.0,
        "price": 100.0,
        "cap_shares": 25,
        "cap_dollars": 2500.0,
        "group_name": None,
        "group_heat_pct": 0.0,
        "reliable_signals": 1,
        "total_signals": 3,
        "exceeds_buying_power": 1,
        "already_held": 0,
    }
    _seed(conn, "2026-07-06T21:12:00+00:00", [], [dict(cap, symbol="STALE")])
    _seed(conn, "2026-07-07T21:12:00+00:00", [], [cap])
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_latest_caps")] == ["NVDA"]


def test_v_exit_advice_scopes_to_the_latest_snapshot(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    old = db.write_snapshot(conn, "2026-07-06T21:12:00+00:00")
    new = db.write_snapshot(conn, "2026-07-07T21:12:00+00:00")
    for sid, sym in ((old, "OLD"), (new, "NEW")):
        conn.execute(
            "INSERT INTO exit_advice (snapshot_id, symbol, quantity) VALUES (?, ?, 1.0)",
            (sid, sym),
        )
    conn.commit()
    assert [r[0] for r in conn.execute("SELECT symbol FROM v_exit_advice")] == ["NEW"]


def _orow(**kw):
    base = {
        "occ_symbol": "XLE260821P00095000",
        "underlying": "XLE",
        "group_name": None,
        "type": "put",
        "expiration": "2026-08-21",
        "quantity": 1.0,
        "multiplier": 100.0,
        "market_value": 250.0,
        "delta": -0.5,
        "delta_date": "2026-07-07",
        "atr": 3.0,
        "price": 95.0,
        "price_date": "2026-07-07",
        "share_equiv": -50.0,
        "heat_dollars": -150.0,
        "heat_pct": -0.015,
        "uncovered": 0,
        "short_leg": 0,
    }
    base.update(kw)
    return base


def test_group_heat_nets_option_hedge_before_magnitude(tmp_path):
    # The spec's worked failure: shares 300 + protective put -150 must read
    # as a 150 bet, not 450 — a hedge REDUCES heat.
    conn = _fresh(tmp_path)
    sid = _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [_row(symbol="XLE", heat_dollars=300.0, heat_pct=0.03)],
    )
    db.write_option_heat(conn, sid, [_orow()])
    conn.commit()
    row = conn.execute(
        "SELECT members, symbols, heat_dollars, net_heat_dollars FROM v_group_heat"
        " WHERE bet = 'XLE'"
    ).fetchone()
    assert row[0] == 2 and "XLE260821P00095000" in row[1]
    assert row[2] == 150.0 and row[3] == 150.0


def test_group_heat_net_short_group_reports_magnitude(tmp_path):
    conn = _fresh(tmp_path)
    sid = _seed(conn, "2026-07-07T21:12:00+00:00", [])
    db.write_option_heat(conn, sid, [_orow()])
    conn.commit()
    row = conn.execute(
        "SELECT heat_dollars, net_heat_dollars FROM v_group_heat WHERE bet = 'XLE'"
    ).fetchone()
    assert row == (150.0, -150.0)  # magnitude positive, net keeps the sign


def test_book_heat_option_legs_and_uncovered_count(tmp_path):
    conn = _fresh(tmp_path)
    sid = _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [_row(symbol="AAPL", market_value=1000.0, atr=2.0, heat_dollars=20.0, heat_pct=0.002)],
    )
    db.write_option_heat(
        conn,
        sid,
        [
            _orow(),  # covered long put, MV 250
            _orow(
                occ_symbol="XLE260918C00100000",
                type="call",
                quantity=-1.0,
                market_value=-250.0,
                short_leg=1,
                uncovered=1,
                heat_dollars=150.0,
                heat_pct=0.015,
            ),
        ],
    )
    conn.commit()
    row = conn.execute(
        "SELECT positions, option_legs, uncovered_option_legs, heat_coverage FROM v_book_heat"
    ).fetchone()
    assert row[0] == 1 and row[1] == 2 and row[2] == 1
    # coverage weights option legs by |market_value|: covered 1000+250 of 1500
    assert abs(row[3] - 1250.0 / 1500.0) < 1e-9


def test_book_heat_unchanged_for_equity_only_book(tmp_path):
    # Increment (c) must not move the equity-only numbers (the (a) gate).
    conn = _fresh(tmp_path)
    _seed(
        conn,
        "2026-07-07T21:12:00+00:00",
        [
            _row(symbol="AAPL", market_value=1000.0, atr=2.0, heat_dollars=20.0, heat_pct=0.002),
            _row(
                symbol="NOATR",
                market_value=1000.0,
                atr=None,
                heat_dollars=None,
                heat_pct=None,
                atr_stale=None,
            ),
        ],
    )
    row = conn.execute(
        "SELECT positions, option_legs, heat_dollars, heat_pct, heat_coverage,"
        " uncovered_option_legs FROM v_book_heat"
    ).fetchone()
    assert row == (2, 0, 20.0, 0.002, 0.5, 0)
