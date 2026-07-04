import pytest

from pipeline.trials import evaluate
from sources.common import monitor_common
from sources.screeners.stock_analysis_screener import db as stocks_db_mod
from pipeline.leads import db as leads_db

COLS = {"price": "REAL", "low": "REAL", "averageVolume": "REAL"}
NOW = "2026-07-04T12:00:00+00:00"


def _price_db(snapshots):
    """snapshots: list of (captured_at, {symbol: (price, low)})."""
    conn = stocks_db_mod.connect(":memory:")
    stocks_db_mod.ensure_schema(conn, COLS)
    for cap, quotes in snapshots:
        data = {sym: {"price": p, "low": lo, "averageVolume": 1e6}
                for sym, (p, lo) in quotes.items()}
        stocks_db_mod.write_snapshot(conn, cap, "test", data, list(COLS))
    return conn


def _calendar(holidays=()):
    conn = monitor_common.connect(":memory:")
    monitor_common.ensure_schema(conn)
    if holidays:
        monitor_common.upsert_events(
            conn, [{"event_type": "market_holiday", "event_date": d,
                    "source": "test"} for d in holidays], NOW)
    return conn


def _leads(rows):
    """rows: (instrument, instrument_kind, direction, horizon_band, as_of_date)."""
    conn = leads_db.connect(":memory:")
    leads_db.ensure_schema(conn)
    sid = leads_db.write_snapshot(conn, NOW)
    leads_db.write_leads(conn, sid, [
        {"instrument": i, "instrument_kind": k, "direction": d,
         "signal": "quality_composite" if k == "stock" else "cot_commercial_extreme",
         "signal_type": "quality" if k == "stock" else "mean_reversion",
         "implementation": "cross_sectional",
         "horizon_band": h, "score": 1.0, "rank_pct": None,
         "as_of_date": a, "details": "{}"}
        for i, k, d, h, a in rows])
    return conn


def test_check_required_columns_lists_all_missing():
    conn = stocks_db_mod.connect(":memory:")
    stocks_db_mod.ensure_schema(conn, {"price": "REAL"})   # low+avgVol missing
    with pytest.raises(ValueError) as e:
        evaluate.check_required_columns(conn, "stocks.db")
    assert "low" in str(e.value) and "averageVolume" in str(e.value)


def test_load_price_history_normalizes_and_dedupes_dates():
    conn = _price_db([
        ("2026-07-01T10:00:00+00:00", {"BRK.B": (100.0, 99.0)}),
        ("2026-07-01T20:00:00+00:00", {"BRK.B": (101.0, 99.5)}),  # same day, later wins
        ("2026-07-02T20:00:00+00:00", {"BRK.B": (102.0, 100.0)}),
    ])
    dates, history = evaluate.load_price_history(conn)
    assert dates == ["2026-07-01", "2026-07-02"]
    assert history["2026-07-01"]["BRK-B"] == (101.0, 99.5)


def test_trading_days_between_skips_weekend_and_holiday():
    cal = _calendar(holidays=["2026-07-03"])
    # Thu 07-02 .. Mon 07-06: Fri is a holiday, Sat/Sun weekend -> 1 (Monday)
    assert evaluate.trading_days_between(cal, "2026-07-02", "2026-07-06") == 1


def test_score_lead_t_plus_1_and_horizon_exit():
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    history = {d: {"AAA": (p, p - 1)} for d, p in
               zip(dates, (100.0, 110.0, 120.0, 130.0))}
    cal = _calendar()
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "weeks",
            "as_of_date": "2026-07-01"}
    # horizon_days=2: entry 07-02 (t+1, price 110), exit after 2 trading days
    # -> 07-06 (price 130)
    r = evaluate.score_lead(lead, dates, history, cal, horizon_days=2)
    assert r["entry_date"] == "2026-07-02"
    assert r["exit_date"] == "2026-07-06"
    assert r["ret"] == pytest.approx((130.0 - 110.0) / 110.0)
    assert not r["truncated"]


def test_score_lead_short_direction_inverts():
    dates = ["2026-07-01", "2026-07-02", "2026-07-03"]
    history = {d: {"AAA": (p, p - 1)} for d, p in zip(dates, (100.0, 100.0, 90.0))}
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "short", "horizon_band": "weeks",
            "as_of_date": "2026-07-01"}
    r = evaluate.score_lead(lead, dates, history, _calendar(), horizon_days=1)
    assert r["ret"] == pytest.approx(0.10)


def test_score_lead_entry_on_last_snapshot_is_censored_at_zero():
    # Entry lands on the final available snapshot date: nothing more to
    # observe, so the loop never resolves. Must NOT read as a genuine
    # fully-resolved 0.0% flat trade.
    dates = ["2026-07-01", "2026-07-02"]
    history = {"2026-07-01": {"AAA": (100.0, 99.0)},
               "2026-07-02": {"AAA": (105.0, 104.0)}}
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "weeks",
            "as_of_date": "2026-07-01"}
    r = evaluate.score_lead(lead, dates, history, _calendar(), horizon_days=20)
    assert r["entry_date"] == "2026-07-02"
    assert r["exit_date"] == "2026-07-02"
    assert r["ret"] == 0.0
    assert r["truncated"] is True


def test_score_lead_data_exhausted_before_horizon_is_censored():
    # Two more snapshots follow entry, but the 20-trading-day "weeks"
    # horizon is never reached before the price history runs out -> a
    # censored, still-open position, not a resolved outcome.
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    history = {d: {"AAA": (p, p - 1)} for d, p in
               zip(dates, (100.0, 105.0, 110.0, 115.0))}
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "weeks",
            "as_of_date": "2026-07-01"}
    r = evaluate.score_lead(lead, dates, history, _calendar(), horizon_days=20)
    assert r["entry_date"] == "2026-07-02"
    assert r["exit_date"] == "2026-07-06"
    assert r["truncated"] is True


def test_score_lead_delisting_truncates_path():
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    history = {"2026-07-01": {"AAA": (100.0, 99.0)},
               "2026-07-02": {"AAA": (105.0, 104.0)},
               "2026-07-03": {"AAA": (95.0, 94.0)},
               "2026-07-06": {}}                       # AAA gone: delisted
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "months",
            "as_of_date": "2026-07-01"}
    r = evaluate.score_lead(lead, dates, history, _calendar(), horizon_days=60)
    assert r["exit_date"] == "2026-07-03"              # truncated at last sighting
    assert r["truncated"]
    assert r["ret"] == pytest.approx((95.0 - 105.0) / 105.0)


def test_score_lead_stop_breach_exits_at_stop():
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    history = {d: {"AAA": pv} for d, pv in zip(dates, (
        (100.0, 99.0), (100.0, 99.0), (98.0, 89.0), (120.0, 119.0)))}
    lead = {"instrument": "AAA", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "months",
            "as_of_date": "2026-07-01"}
    r = evaluate.score_lead(lead, dates, history, _calendar(),
                            horizon_days=60, stop=90.0)
    assert r["exit_date"] == "2026-07-03"              # low 89 <= stop 90
    assert r["ret"] == pytest.approx((90.0 - 100.0) / 100.0)  # exit AT the stop


def test_score_lead_unscoreable_returns_none():
    lead = {"instrument": "ZZZ", "instrument_kind": "stock",
            "direction": "long", "horizon_band": "weeks",
            "as_of_date": "2026-07-05"}                # no snapshot after
    dates = ["2026-07-01"]
    history = {"2026-07-01": {"ZZZ": (10.0, 9.0)}}
    assert evaluate.score_lead(lead, dates, history, _calendar(),
                               horizon_days=20) is None


def test_evaluate_cohort_planted_edge_and_gap_report():
    # 5 snapshot dates with a weekend gap; two stock leads with a planted edge
    caps = ["2026-07-01T20:00:00+00:00", "2026-07-02T20:00:00+00:00",
            "2026-07-03T20:00:00+00:00", "2026-07-06T20:00:00+00:00",
            "2026-07-07T20:00:00+00:00"]
    quotes = [{"WIN": (100.0, 99.0), "LOSE": (100.0, 99.0)},
              {"WIN": (101.0, 100.0), "LOSE": (99.0, 98.0)},
              {"WIN": (102.0, 101.0), "LOSE": (98.0, 97.0)},
              {"WIN": (103.0, 102.0), "LOSE": (97.0, 96.0)},
              {"WIN": (104.0, 103.0), "LOSE": (96.0, 95.0)}]
    stocks = _price_db(list(zip(caps, quotes)))
    leads_conn = _leads([
        ("WIN", "stock", "long", "weeks", "2026-07-01"),
        ("LOSE", "stock", "short", "weeks", "2026-07-01"),
        ("GONE", "stock", "long", "weeks", "2026-07-01"),   # never in snapshots
    ])
    out = evaluate.evaluate_cohort(
        leads_conn, evaluate.load_price_history(stocks), None, _calendar())
    assert out["scored"] == 2 and out["skipped"] == 1
    assert all(r > 0 for r in out["returns"])              # planted edge
    assert out["window_start"] == out["window_end"] == "2026-07-01"
    assert out["max_gap_days"] == 3                        # 07-03 -> 07-06
    # "weeks" = 20 trading days, but the fixture only spans 5 snapshots ->
    # neither WIN nor LOSE reaches its horizon: both are censored.
    assert out["truncated"] == 2


def test_evaluate_cohort_missing_price_db_skips_that_kind():
    leads_conn = _leads([("GLD", "etf", "long", "weeks", "2026-07-01")])
    out = evaluate.evaluate_cohort(leads_conn, None, None, _calendar())
    assert out["scored"] == 0 and out["skipped"] == 1
