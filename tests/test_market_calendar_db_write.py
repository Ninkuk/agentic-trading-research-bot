import sources.common.monitor_common as monitor_common
from market_calendar import db


def _fresh():
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    return conn


def _evt(event_type, date, event_time=None, title="T", source="nyse"):
    return {"event_type": event_type, "event_date": date,
            "event_time": event_time, "subtype": "", "title": title,
            "status": "scheduled", "source": source, "payload": None}


def test_is_trading_day_false_on_weekend_and_holiday():
    conn = _fresh()
    monitor_common.upsert_events(conn, [_evt("market_holiday", "2026-07-03")], "t")
    assert db.is_trading_day(conn, "2026-07-03") is False   # holiday
    assert db.is_trading_day(conn, "2026-07-04") is False   # Saturday
    assert db.is_trading_day(conn, "2026-07-06") is True    # Monday, open


def test_next_trading_day_skips_weekend_and_holiday():
    conn = _fresh()
    monitor_common.upsert_events(conn, [_evt("market_holiday", "2026-07-03")], "t")
    # Thu 2026-07-02 -> Fri is a holiday, Sat/Sun weekend -> Mon 2026-07-06
    assert db.next_trading_day(conn, "2026-07-02") == "2026-07-06"


def test_next_early_close_returns_next_on_or_after():
    conn = _fresh()
    monitor_common.upsert_events(
        conn, [_evt("early_close", "2026-11-27", "13:00")], "t")
    assert db.next_early_close(conn, "2026-01-01") == "2026-11-27"
    assert db.next_early_close(conn, "2026-12-01") is None


def test_v_upcoming_closures_lists_holidays_and_early_closes_from_today():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-06-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("market_holiday", "2026-05-25"),                  # past -> out
        _evt("market_holiday", "2026-07-03"),                  # future -> in
        _evt("early_close", "2026-11-27", "13:00"),            # future -> in
    ], "t")
    dates = [r[0] for r in conn.execute(
        "SELECT event_date FROM v_upcoming_closures ORDER BY event_date")]
    assert dates == ["2026-07-03", "2026-11-27"]


def test_v_next_opex_returns_soonest_expiration():
    conn = _fresh()
    monitor_common.set_today(conn, "2026-08-01T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("opex", "2026-08-21", "16:00", source="computed"),
        _evt("quad_witching", "2026-09-18", "16:00", source="computed"),
    ], "t")
    row = conn.execute(
        "SELECT event_date, event_type FROM v_next_opex").fetchone()
    assert row == ("2026-08-21", "opex")
