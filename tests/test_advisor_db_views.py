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
