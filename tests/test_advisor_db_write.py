import pytest

from sources.combiners.advisor import catalog, db

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


# --- exit advice (plan 003) -------------------------------------------------

# Import, never restate: a reviewer showed a hardcoded 2.0 here means a
# change to catalog.STOP_ATR_MULTIPLE is only caught by the integration test.
STOP_MULT = catalog.STOP_ATR_MULTIPLE
TRIM_FRAC = catalog.TRIM_FRACTION_STRONG


def _heat(**kw):
    base = {
        "symbol": "AAPL",
        "quantity": 10.0,
        "price": 100.0,
        "avg_cost": 80.0,
        "atr": 3.0,
        "atr_stale": 0,
        "score_sum": 0,
        "total": 5,
    }
    base.update(kw)
    return base


def _one(**kw):
    return db.build_exit_advice([_heat(**kw)], STOP_MULT, TRIM_FRAC)[0]


def test_stop_price_is_two_atr_below_price():
    r = _one()
    assert r["stop_price"] == 94.0
    assert r["stop_distance_pct"] == pytest.approx(6.0)


def test_null_atr_yields_null_stop():
    r = _one(atr=None)
    assert r["stop_price"] is None and r["stop_distance_pct"] is None


def test_stale_atr_yields_null_stop_even_with_a_good_atr():
    """An ATR-derived stop from a stale ATR looks authoritative and isn't."""
    r = _one(atr_stale=1)
    assert r["stop_price"] is None and r["stop_distance_pct"] is None
    assert r["atr"] == 3.0, "the stale ATR is still reported, just not used"


def test_nonpositive_stop_price_yields_null():
    """Low price, high ATR: a stop at or below zero is not advice."""
    assert _one(price=5.0, atr=3.0)["stop_price"] is None
    assert _one(price=6.0, atr=3.0)["stop_price"] is None  # exactly 0.0


def test_null_avg_cost_yields_null_unrealized_not_zero():
    """0.0 would read as 'flat'; the truth is 'entry unknown'."""
    assert _one(avg_cost=None)["unrealized_pct"] is None


def test_zero_avg_cost_does_not_raise():
    """Gifted/promotional shares can carry avg_cost 0.0."""
    assert _one(avg_cost=0.0)["unrealized_pct"] is None


def test_unrealized_pct_sign_and_magnitude():
    assert _one(avg_cost=80.0, price=100.0)["unrealized_pct"] == pytest.approx(25.0)
    assert _one(avg_cost=125.0, price=100.0)["unrealized_pct"] == pytest.approx(-20.0)


def test_trim_only_when_strong():
    # mirrors composite v_flagged: score_sum <= -3 AND total >= 2
    assert _one(score_sum=-2, total=5)["trim_shares"] is None  # score floor
    assert _one(score_sum=-9, total=1)["trim_shares"] is None  # total floor
    assert _one(score_sum=-3, total=2)["trim_shares"] == 5.0  # both met
    assert _one(score_sum=3, total=5)["trim_shares"] is None  # bullish


def test_strong_flag_matches_trim_presence():
    for kw in ({"score_sum": -3, "total": 2}, {"score_sum": -2, "total": 5}):
        r = _one(**kw)
        assert bool(r["strong"]) == (r["trim_shares"] is not None)


def test_trim_shares_are_fractional_not_floored():
    """Flooring would zero every trim on a small position — the same failure
    build_size_caps guards against with fractional cap_shares."""
    assert _one(quantity=7.0, score_sum=-4, total=3)["trim_shares"] == 3.5
    assert _one(quantity=1.0, score_sum=-4, total=3)["trim_shares"] == 0.5


def test_missing_score_sum_is_not_strong():
    """A held symbol composite has no opinion on must never be trimmed."""
    r = _one(score_sum=None, total=None)
    assert r["strong"] == 0 and r["trim_shares"] is None


def test_row_emitted_for_every_held_position_not_only_disagreements():
    rows = db.build_exit_advice(
        [_heat(symbol="AAPL", score_sum=5), _heat(symbol="XOM", score_sum=-9, total=4)],
        STOP_MULT,
        TRIM_FRAC,
    )
    assert [r["symbol"] for r in rows] == ["AAPL", "XOM"]
    assert rows[0]["trim_shares"] is None and rows[1]["trim_shares"] == 5.0
    assert all(r["stop_price"] == 94.0 for r in rows), "a stop is advice before the thesis breaks"


def test_stop_and_trim_refuse_a_short_position():
    """`stop_price = price - k*ATR` and `trim = qty * frac` both assume LONG.
    A short leg would get a stop BELOW entry (a short's stop belongs above) and
    a NEGATIVE trim. The book is long-only; refuse rather than invert."""
    r = db.build_exit_advice([_heat(quantity=-10.0, score_sum=-9, total=4)], STOP_MULT, TRIM_FRAC)[
        0
    ]
    assert r["stop_price"] is None
    assert r["stop_distance_pct"] is None
    assert r["trim_shares"] is None
    assert r["strong"] == 1, "strong still reports; it mirrors v_disagreements"


def test_zero_quantity_yields_no_stop_or_trim():
    r = _one(quantity=0.0, score_sum=-9, total=4)
    assert r["stop_price"] is None and r["trim_shares"] is None


def test_nan_atr_does_not_slip_past_the_nonpositive_stop_guard():
    """NaN <= 0 is False, so a bare comparison guard lets a NaN stop through."""
    r = _one(atr=float("nan"))
    assert r["stop_price"] is None and r["stop_distance_pct"] is None


def test_infinite_atr_yields_null_stop():
    assert _one(atr=float("inf"))["stop_price"] is None


def test_nonpositive_atr_yields_null_stop():
    assert _one(atr=0.0)["stop_price"] is None
    assert _one(atr=-1.0)["stop_price"] is None


def test_negative_avg_cost_yields_null_unrealized():
    """A negative cost basis would invert the sign of unrealized_pct."""
    assert _one(avg_cost=-50.0)["unrealized_pct"] is None


def test_nan_price_yields_null_everywhere():
    r = _one(price=float("nan"))
    assert r["stop_price"] is None and r["unrealized_pct"] is None
