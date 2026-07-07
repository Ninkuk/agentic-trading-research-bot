from sources.combiners.advisor import db

TODAY = "2026-07-07"


def _pos(symbol, quantity, market_value):
    return {"symbol": symbol, "quantity": quantity, "market_value": market_value}


def _metric(atr, close, price_date=TODAY):
    return {"atr": atr, "close": close, "price_date": price_date}


def _score(score_sum, total=3, bullish=None, bearish=None):
    if bullish is None:
        bullish = total if score_sum > 0 else 0
    if bearish is None:
        bearish = total if score_sum < 0 else 0
    return {"score_sum": score_sum, "bullish": bullish, "bearish": bearish, "total": total}


GROUPS = {"XLE": "energy", "XOM": "energy"}


def test_position_heat_computes_heat_and_weight():
    rows = db.build_position_heat(
        [_pos("AAPL", 10.0, 1000.0)],
        {"AAPL": _score(-1, total=1)},
        {"AAPL": _metric(atr=2.0, close=100.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    (r,) = rows
    assert r["heat_dollars"] == 20.0  # 10 shares x 2.0 ATR
    assert r["heat_pct"] == 0.002  # 20 / 10000
    assert r["weight_pct"] == 0.1
    assert r["group_name"] is None  # AAPL is not crosswalked
    assert r["score_sum"] == -1 and r["atr_stale"] == 0


def test_position_heat_missing_atr_is_null_not_skipped():
    rows = db.build_position_heat(
        [_pos("OBSCURE", 5.0, 500.0)],
        {},
        {},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    (r,) = rows
    assert r["heat_dollars"] is None and r["heat_pct"] is None
    assert r["atr_stale"] is None and r["score_sum"] is None
    assert r["weight_pct"] == 0.05  # weight still computable


def test_position_heat_stale_atr_flagged():
    rows = db.build_position_heat(
        [_pos("AAPL", 1.0, 100.0)],
        {},
        {"AAPL": _metric(atr=2.0, close=100.0, price_date="2026-06-20")},
        equity=10000.0,
        today=TODAY,  # 17 days later > 5
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    assert rows[0]["atr_stale"] == 1


def test_size_cap_inverts_risk_budget():
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=[],
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={"NVDA": {("sig_a", 0), ("sig_b", 0), ("sig_c", 0)}},
        reliable_ids={("sig_a", 0)},
    )
    (c,) = caps
    assert c["cap_shares"] == 25.0  # 0.01*10000 / 4.0 (fractional, no floor)
    assert c["cap_dollars"] == 2500.0
    assert c["direction"] == "bullish"
    assert c["exceeds_buying_power"] == 1  # 2500 > 1000
    assert c["already_held"] == 0
    assert (c["reliable_signals"], c["total_signals"]) == (1, 3)


def test_size_cap_is_fractional_on_small_accounts():
    # $200 account: budget $2, ATR 4.0 -> 0.5 shares. Flooring to int would
    # zero every cap the advisor ever emits at this equity.
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=[],
        equity=200.0,
        buying_power=500.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["cap_shares"] == 0.5
    assert c["cap_dollars"] == 50.0


def test_bearish_flag_never_gets_a_buy_cap():
    # Long-only book: a bearish flag's row IS the advice; caps stay NULL
    # even with ATR and equity known — a buy size on an avoid signal is
    # wrong advice.
    caps = db.build_size_caps(
        ["SHORTY"],
        {"SHORTY": _score(-4)},
        {"SHORTY": _metric(atr=2.0, close=50.0)},
        heat_rows=[],
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["direction"] == "bearish"
    assert c["cap_shares"] is None and c["cap_dollars"] is None
    assert c["exceeds_buying_power"] == 0


def test_size_cap_shrinks_by_existing_group_heat():
    heat_rows = db.build_position_heat(
        [_pos("XOM", 5.0, 400.0)],
        {},
        {"XOM": _metric(atr=4.0, close=80.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    caps = db.build_size_caps(
        ["XLE"],
        {"XLE": _score(4)},
        {"XLE": _metric(atr=2.0, close=50.0)},
        heat_rows=heat_rows,
        equity=10000.0,
        buying_power=99999.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    # budget 100 - existing energy heat 20 (XOM 5x4) = 80 -> 80/2 = 40.0
    assert c["cap_shares"] == 40.0
    assert c["group_name"] == "energy"
    assert c["group_heat_pct"] == 0.002


def test_size_cap_missing_atr_is_null_row():
    # Bullish so this exercises the missing-ATR path, not the bearish one.
    caps = db.build_size_caps(
        ["MYSTERY"],
        {"MYSTERY": _score(4)},
        {},
        heat_rows=[],
        equity=10000.0,
        buying_power=None,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    (c,) = caps
    assert c["cap_shares"] is None and c["cap_dollars"] is None
    assert c["direction"] == "bullish"
    assert c["exceeds_buying_power"] == 0


def test_writers_roundtrip_and_header_finish(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    sid = db.write_snapshot(conn, "2026-07-07T21:12:00+00:00")
    heat = db.build_position_heat(
        [_pos("AAPL", 10.0, 1000.0)],
        {"AAPL": _score(1, total=1)},
        {"AAPL": _metric(atr=2.0, close=100.0)},
        equity=10000.0,
        today=TODAY,
        ticker_group=GROUPS,
        atr_max_age_days=5,
    )
    caps = db.build_size_caps(
        ["NVDA"],
        {"NVDA": _score(4)},
        {"NVDA": _metric(atr=4.0, close=100.0)},
        heat_rows=heat,
        equity=10000.0,
        buying_power=1000.0,
        risk_budget=0.01,
        ticker_group=GROUPS,
        flag_signals={},
        reliable_ids=set(),
    )
    assert db.write_position_heat(conn, sid, heat) == 1
    assert db.write_size_caps(conn, sid, caps) == 1
    db.finish_snapshot(
        conn,
        sid,
        {
            "equity": 10000.0,
            "cash": 2000.0,
            "buying_power": 1000.0,
            "captured_at": "2026-07-07T14:30:00+00:00",
        },
        {"snapshot_id": 9, "captured_at": "2026-07-06T21:05:00+00:00", "regime": "risk_on"},
    )
    conn.commit()
    row = conn.execute(
        "SELECT equity, buying_power, portfolio_captured_at, composite_captured_at, regime"
        " FROM snapshots WHERE id = ?",
        (sid,),
    ).fetchone()
    assert row == (
        10000.0,
        1000.0,
        "2026-07-07T14:30:00+00:00",
        "2026-07-06T21:05:00+00:00",
        "risk_on",
    )


def test_finish_snapshot_tolerates_missing_upstream(tmp_path):
    conn = db.connect(str(tmp_path / "advisor.db"))
    db.ensure_schema(conn)
    sid = db.write_snapshot(conn, "2026-07-07T21:12:00+00:00")
    db.finish_snapshot(conn, sid, None, None, sources_failed=3)
    conn.commit()
    assert conn.execute(
        "SELECT equity, regime, sources_failed FROM snapshots WHERE id=?", (sid,)
    ).fetchone() == (None, None, 3)
