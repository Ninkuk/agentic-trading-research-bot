import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone

import monitor_common
from earnings_calendar import db, fetch


def build_events(rows, now_iso) -> list:
    """Map normalized forward rows to earnings events (subtype=ticker)."""
    out = []
    for r in rows:
        out.append({
            "event_type": "earnings", "event_date": r["date"],
            "event_time": fetch.timing_to_time(r.get("timing")),
            "subtype": r["ticker"], "title": r.get("name"),
            "status": "scheduled", "source": "stockanalysis",
            "payload": json.dumps({"eps_est": r.get("eps_est"),
                                   "rev_est": r.get("rev_est"),
                                   "mktcap": r.get("mktcap"),
                                   "timing": r.get("timing")}),
        })
    return out


def run(db_path, horizon_days=None, keep_days=None, only=None,
        fetch_forward=fetch.fetch_forward, confirm=fetch.confirm_via_edgar,
        now_iso=None):
    """Decode the forward earnings feed, replace the forward window, optionally
    confirm watched tickers via EDGAR, snapshot, and optionally prune. Returns
    (snapshot_id, event_count). Feed drift aborts loudly; a transient feed
    failure preserves the last-good calendar."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()
    watch = {t.strip().upper() for t in only} if only else None

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days or 7)

        try:
            rows = fetch_forward()
        except fetch.EarningsFeedError:
            raise                                   # abort loudly on schema drift
        except Exception as e:                      # transient: keep last-good
            print(f"warning: earnings feed failed: {type(e).__name__}",
                  file=sys.stderr)
            rows = None

        if rows is not None:
            if watch is not None:
                rows = [r for r in rows if r["ticker"].upper() in watch]
            if horizon_days is not None:
                cutoff = (date.fromisoformat(today)
                          + timedelta(days=horizon_days)).isoformat()
                rows = [r for r in rows if r["date"] <= cutoff]
            events = build_events(rows, now_iso)
            monitor_common.replace_forward_window(conn, "earnings", today,
                                                  events, now_iso)

            if watch is not None and rows:
                scheduled_by_ticker = {}
                for r in rows:
                    scheduled_by_ticker.setdefault(r["ticker"], []).append(
                        r["date"])
                try:
                    confirmed = confirm(list(scheduled_by_ticker),
                                        scheduled_by_ticker)
                except Exception as e:
                    print(f"warning: earnings confirm failed: "
                          f"{type(e).__name__}", file=sys.stderr)
                    confirmed = set()
                for ticker, when in confirmed:
                    conn.execute(
                        "UPDATE events SET status='confirmed', source='edgar' "
                        "WHERE event_type='earnings' AND subtype=? "
                        "AND event_date=?", (ticker, when))
                conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='earnings' "
            "AND event_date >= ?", (today,)).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "stockanalysis")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="earnings",
        description="Pull the forward earnings calendar (stockanalysis + EDGAR confirm)")
    p.add_argument("--db", default="earnings.db")
    p.add_argument("--horizon-days", type=int, default=None,
                   help="cap how far forward to store")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    p.add_argument("--only", nargs="+", default=None,
                   help="restrict to these tickers (default: the watchlist)")
    a = p.parse_args(argv)
    _, count = run(a.db, horizon_days=a.horizon_days, keep_days=a.keep_days,
                   only=a.only)
    print(f"stored {count} forward earnings events into {a.db}")


if __name__ == "__main__":
    main()
