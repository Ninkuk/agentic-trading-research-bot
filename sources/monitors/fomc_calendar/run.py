import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone

import sources.common.monitor_common as monitor_common
from sources.monitors.fomc_calendar import db, fetch

_EVENT_TYPES = ("fomc_meeting", "fomc_sep", "fomc_minutes",
                "fomc_blackout_start", "fomc_blackout_end")


def _evt(event_type, event_date, event_time, subtype, title, status, payload):
    return {"event_type": event_type, "event_date": event_date,
            "event_time": event_time, "subtype": subtype, "title": title,
            "status": status, "source": "federalreserve",
            "payload": json.dumps(payload)}


def build_events(meetings, now_iso) -> list:
    """Expand each parsed meeting into its events rows. The meeting uses
    subtype='' ; every derived event pins to the meeting's decision date."""
    out = []
    for m in meetings:
        decision = m["end_date"]                 # day 2 = decision day
        status = m["status"]
        has_sep = fetch.is_sep_meeting(decision)
        out.append(_evt("fomc_meeting", decision, "14:00", "", "FOMC Meeting",
                        status, {"start": m["start_date"], "end": m["end_date"],
                                 "has_press_conference": m["has_press_conference"],
                                 "has_sep": has_sep}))
        if has_sep:
            out.append(_evt("fomc_sep", decision, "14:00", decision,
                            "FOMC SEP (dot plot)", status, {}))
        out.append(_evt("fomc_minutes", fetch.minutes_date(m["end_date"]),
                        "14:00", decision, "FOMC Minutes", status, {}))
        bo_start, bo_end = fetch.blackout_window(m["start_date"], m["end_date"])
        out.append(_evt("fomc_blackout_start", bo_start, None, decision,
                        "FOMC Blackout Begins", status, {"window_end": bo_end}))
        out.append(_evt("fomc_blackout_end", bo_end, None, decision,
                        "FOMC Blackout Ends", status, {"window_start": bo_start}))
    return out


def run(db_path, horizon_days=None, keep_days=None,
        fetch_calendar=fetch.fetch_calendar, now_iso=None):
    """Parse the FOMC calendar, derive minutes/blackout/SEP, replace the forward
    window per event_type, snapshot, and optionally prune. Returns
    (snapshot_id, event_count). A whole-page parse error aborts loudly; a
    transient fetch failure preserves the last-good calendar."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days or 7)

        try:
            meetings = fetch_calendar()
        except fetch.FomcCalendarParseError:
            raise                                # abort loudly on structural drift
        except Exception as e:                   # transient: keep last-good calendar
            print(f"warning: FOMC fetch failed: {type(e).__name__}",
                  file=sys.stderr)
            meetings = []

        if meetings:
            events = build_events(meetings, now_iso)
            if horizon_days is not None:
                cutoff = (date.fromisoformat(today)
                          + timedelta(days=horizon_days)).isoformat()
                events = [e for e in events if e["event_date"] <= cutoff]
            by_type = {}
            for e in events:
                by_type.setdefault(e["event_type"], []).append(e)
            for et in _EVENT_TYPES:
                monitor_common.replace_forward_window(conn, et, today,
                                                      by_type.get(et, []), now_iso)

        count = conn.execute("SELECT COUNT(*) FROM events WHERE event_date >= ?",
                             (today,)).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "federalreserve")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fomc",
        description="Pull the FOMC forward calendar (meetings/minutes/blackout/SEP)")
    p.add_argument("--db", default="fomc.db")
    p.add_argument("--horizon-days", type=int, default=None,
                   help="cap how far forward to store (default: keep all parsed)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    a = p.parse_args(argv)
    _, count = run(a.db, horizon_days=a.horizon_days, keep_days=a.keep_days)
    print(f"stored {count} forward FOMC events into {a.db}")


if __name__ == "__main__":
    main()
