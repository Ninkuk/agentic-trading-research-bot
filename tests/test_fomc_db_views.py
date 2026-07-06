import json

import sources.common.monitor_common as monitor_common
from sources.monitors.fomc_calendar import db


def _fresh(now):
    conn = db.connect(":memory:")
    db.ensure_schema(conn)
    monitor_common.set_today(conn, now)
    return conn


def _evt(event_type, event_date, subtype="", event_time="14:00", status="confirmed", payload=None):
    return {
        "event_type": event_type,
        "event_date": event_date,
        "event_time": event_time,
        "subtype": subtype,
        "title": "T",
        "status": status,
        "source": "federalreserve",
        "payload": json.dumps(payload or {}),
    }


def test_v_next_fomc_picks_next_meeting_with_days_until_and_has_sep():
    conn = _fresh("2026-03-01T00:00:00+00:00")
    monitor_common.upsert_events(
        conn,
        [
            _evt("fomc_meeting", "2026-01-28", payload={"has_sep": False}),  # past
            _evt("fomc_meeting", "2026-03-18", payload={"has_sep": True}),  # next
        ],
        "t",
    )
    row = conn.execute("SELECT event_date, days_until, has_sep FROM v_next_fomc").fetchone()
    assert row[0] == "2026-03-18"
    assert row[1] == 17  # 2026-03-18 minus 2026-03-01
    assert row[2] in (1, True)  # json true -> 1


def test_v_in_blackout_true_inside_window_false_outside():
    conn = _fresh("2026-03-14T00:00:00+00:00")
    monitor_common.upsert_events(
        conn,
        [
            _evt(
                "fomc_blackout_start",
                "2026-03-07",
                subtype="2026-03-18",
                event_time=None,
                payload={"window_end": "2026-03-19"},
            ),
        ],
        "t",
    )
    assert conn.execute("SELECT in_blackout FROM v_in_blackout").fetchone()[0] == 1
    monitor_common.set_today(conn, "2026-03-25T00:00:00+00:00")  # after window
    assert conn.execute("SELECT in_blackout FROM v_in_blackout").fetchone()[0] == 0


def test_v_upcoming_fomc_events_orders_and_labels():
    conn = _fresh("2026-03-01T00:00:00+00:00")
    monitor_common.upsert_events(
        conn,
        [
            _evt("fomc_minutes", "2026-04-08", subtype="2026-03-18"),
            _evt("fomc_meeting", "2026-03-18"),
        ],
        "t",
    )
    rows = conn.execute("SELECT event_type, label FROM v_upcoming_fomc_events").fetchall()
    assert rows[0][0] == "fomc_meeting"  # earliest first
    assert "Decision" in rows[0][1] or "Meeting" in rows[0][1]
