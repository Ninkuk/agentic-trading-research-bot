import json

import sources.common.monitor_common as monitor_common
from sources.monitors.earnings_calendar import db


def _fresh(now, horizon=7):
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    monitor_common.set_today(conn, now, horizon)
    return conn


def _evt(ticker, event_date, status="scheduled", source="stockanalysis",
         mktcap=1e9, timing="amc"):
    return {"event_type": "earnings", "event_date": event_date,
            "event_time": "after close", "subtype": ticker, "title": ticker,
            "status": status, "source": source,
            "payload": json.dumps({"mktcap": mktcap, "timing": timing})}


def test_v_upcoming_earnings_filters_future_orders_by_date_then_mktcap():
    conn = _fresh("2026-07-06T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("OLD", "2026-06-01"),                       # past -> out
        _evt("SM", "2026-07-08", mktcap=1e9),
        _evt("BIG", "2026-07-08", mktcap=9e11),          # same day, bigger first
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_upcoming_earnings")]
    assert rows == ["BIG", "SM"]


def test_v_imminent_earnings_respects_horizon():
    conn = _fresh("2026-07-06T00:00:00+00:00", horizon=7)
    monitor_common.upsert_events(conn, [
        _evt("A", "2026-07-09"),      # in
        _evt("B", "2026-07-20"),      # out (14 days)
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_imminent_earnings")]
    assert rows == ["A"]


def test_v_this_week_earnings_mon_to_fri():
    conn = _fresh("2026-07-06T00:00:00+00:00")   # Monday
    monitor_common.upsert_events(conn, [
        _evt("MON", "2026-07-06"), _evt("FRI", "2026-07-10"),
        _evt("NEXTMON", "2026-07-13"),          # next week -> out
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_this_week_earnings")]
    assert rows == ["MON", "FRI"]


def test_v_earnings_confirmed_only_edgar_verified():
    conn = _fresh("2026-07-06T00:00:00+00:00")
    monitor_common.upsert_events(conn, [
        _evt("A", "2026-07-08", status="scheduled", source="stockanalysis"),
        _evt("B", "2026-07-09", status="confirmed", source="edgar"),
    ], "t")
    rows = [r[0] for r in conn.execute(
        "SELECT ticker FROM v_earnings_confirmed")]
    assert rows == ["B"]
