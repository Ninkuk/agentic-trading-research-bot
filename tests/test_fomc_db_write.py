import json

from fomc_calendar import run as runmod

NOW = "2026-01-01T00:00:00+00:00"
MEETING = {"start_date": "2026-03-17", "end_date": "2026-03-18",
           "status": "tentative", "has_press_conference": True}
JAN = {"start_date": "2026-01-27", "end_date": "2026-01-28",
       "status": "confirmed", "has_press_conference": True}


def test_build_events_expands_all_types_with_subtype_convention():
    evs = runmod.build_events([MEETING], NOW)
    by_type = {e["event_type"]: e for e in evs}
    assert set(by_type) == {"fomc_meeting", "fomc_sep", "fomc_minutes",
                            "fomc_blackout_start", "fomc_blackout_end"}
    # meeting subtype is '' ; derived events pin to the decision date (end)
    assert by_type["fomc_meeting"]["subtype"] == ""
    assert by_type["fomc_minutes"]["subtype"] == "2026-03-18"
    # SEP only appears for a quarter-month meeting (March)
    assert json.loads(by_type["fomc_meeting"]["payload"])["has_sep"] is True
    assert by_type["fomc_minutes"]["event_date"] == "2026-04-08"     # +21d
    assert by_type["fomc_blackout_end"]["event_date"] == "2026-03-19"  # end+1


def test_build_events_no_sep_for_january_meeting():
    types = {e["event_type"] for e in runmod.build_events([JAN], NOW)}
    assert "fomc_sep" not in types


def test_run_upserts_then_firms_status_in_place(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)
    firmed = {**MEETING, "status": "confirmed"}
    runmod.run(db_path, fetch_calendar=lambda: [firmed], now_iso=NOW)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT status FROM events WHERE event_type='fomc_meeting'").fetchall()
    assert rows == [("confirmed",)]           # in place, no duplicate


def test_run_replace_forward_drops_cancelled_future_meeting(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [JAN, MEETING], now_iso=NOW)
    # next run no longer lists the March meeting -> its future rows disappear
    runmod.run(db_path, fetch_calendar=lambda: [JAN], now_iso=NOW)
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM events "
                     "WHERE event_date >= '2026-03-01'").fetchone()[0]
    assert n == 0
