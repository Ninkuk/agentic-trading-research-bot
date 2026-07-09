import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta

import sources.common.monitor_common as monitor_common
from sources.common.clock import phx_date
from sources.monitors.earnings_calendar import db, fetch


def build_events(rows, now_iso) -> list:
    """Map normalized forward rows to earnings events (subtype=ticker)."""
    out = []
    for r in rows:
        out.append(
            {
                "event_type": "earnings",
                "event_date": r["date"],
                "event_time": fetch.timing_to_time(r.get("timing")),
                "subtype": r["ticker"],
                "title": r.get("name"),
                "status": "scheduled",
                "source": "stockanalysis",
                "payload": json.dumps(
                    {
                        "eps_est": r.get("eps_est"),
                        "rev_est": r.get("rev_est"),
                        "mktcap": r.get("mktcap"),
                        "timing": r.get("timing"),
                    }
                ),
            }
        )
    return out


def build_estimate_events(estimates) -> list:
    """Map {ticker: ISO date} cadence estimates to scheduled earnings events
    tagged source='edgar-estimate', so consumers can rank them below an
    aggregator forward date and a real EDGAR confirmation."""
    return [
        {
            "event_type": "earnings",
            "event_date": when,
            "event_time": None,
            "subtype": ticker,
            "title": None,
            "status": "scheduled",
            "source": "edgar-estimate",
            "payload": json.dumps({"method": "item202-median-gap"}),
        }
        for ticker, when in estimates.items()
    ]


def run(
    db_path,
    horizon_days=None,
    keep_days=None,
    only=None,
    fetch_forward=fetch.fetch_forward,
    confirm=fetch.confirm_via_edgar,
    history=fetch.item_202_history,
    now_iso=None,
):
    """Decode the forward earnings feed, replace the forward window, optionally
    confirm watched tickers via EDGAR, snapshot, and optionally prune. Returns
    (snapshot_id, event_count). Feed drift aborts loudly; a transient feed
    failure preserves the last-good calendar."""
    now_iso = now_iso or datetime.now(UTC).isoformat()
    today = phx_date(now_iso)
    watch = {t.strip().upper() for t in only} if only else None

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days or 7)

        try:
            rows = fetch_forward()
        except fetch.EarningsFeedError:
            raise  # abort loudly on schema drift
        except Exception as e:  # transient: keep last-good
            print(f"warning: earnings feed failed: {type(e).__name__}", file=sys.stderr)
            rows = None

        if rows is not None:
            if watch is not None:
                rows = [r for r in rows if r["ticker"].upper() in watch]
            cutoff = None
            if horizon_days is not None:
                cutoff = (date.fromisoformat(today) + timedelta(days=horizon_days)).isoformat()
                rows = [r for r in rows if r["date"] <= cutoff]
            events = build_events(rows, now_iso)

            # job b: for watched names the forward feed omits, estimate the next
            # report date from their 8-K Item 2.02 cadence (edgar-estimate).
            if watch is not None:
                covered = {r["ticker"].upper() for r in rows}
                missing = sorted(watch - covered)
                if missing:
                    try:
                        hist = history(missing)
                    except Exception as e:
                        print(
                            f"warning: earnings estimate failed: {type(e).__name__}",
                            file=sys.stderr,
                        )
                        hist = {}
                    estimates = {}
                    for ticker, dates in hist.items():
                        est = fetch.estimate_next_report(dates, today)
                        if est is None or (cutoff is not None and est > cutoff):
                            continue
                        estimates[ticker] = est
                    events = events + build_estimate_events(estimates)

            monitor_common.replace_forward_window(conn, "earnings", today, events, now_iso)

            if watch is not None and rows:
                scheduled_by_ticker: dict[str, list] = {}
                for r in rows:
                    scheduled_by_ticker.setdefault(r["ticker"], []).append(r["date"])
                try:
                    confirmed = confirm(list(scheduled_by_ticker), scheduled_by_ticker)
                except Exception as e:
                    print(f"warning: earnings confirm failed: {type(e).__name__}", file=sys.stderr)
                    confirmed = set()
                for ticker, when in confirmed:
                    conn.execute(
                        "UPDATE events SET status='confirmed', source='edgar' "
                        "WHERE event_type='earnings' AND subtype=? "
                        "AND event_date=?",
                        (ticker, when),
                    )
                conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='earnings' AND event_date >= ?", (today,)
        ).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count, "stockanalysis")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="earnings",
        description="Pull the forward earnings calendar (stockanalysis + EDGAR confirm)",
    )
    p.add_argument("--db", default="earnings.db")
    p.add_argument("--horizon-days", type=int, default=None, help="cap how far forward to store")
    p.add_argument(
        "--keep-days",
        type=int,
        default=None,
        help="prune run-provenance snapshots older than N days",
    )
    p.add_argument(
        "--only", nargs="+", default=None, help="restrict to these tickers (default: the watchlist)"
    )
    a = p.parse_args(argv)
    _, count = run(a.db, horizon_days=a.horizon_days, keep_days=a.keep_days, only=a.only)
    print(f"stored {count} forward earnings events into {a.db}")


if __name__ == "__main__":
    main()
