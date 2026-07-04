import argparse
import sys
from datetime import date, datetime, timedelta, timezone

from finra_ats import db, fetch

_PUBLICATION_LAG_DAYS = 14      # newest fetchable week floored ~2 weeks back
_DEFAULT_LOOKBACK_DAYS = 182    # ~6 months
_REFETCH_WEEKS = 2              # re-absorb FINRA re-posts of the trailing weeks


def weeks_in_range(start: str, end: str) -> list:
    """Monday-anchored week-start dates from the Monday on/before start through
    end, inclusive."""
    s = date.fromisoformat(start)
    s -= timedelta(days=s.weekday())            # back to Monday
    e = date.fromisoformat(end)
    out = []
    while s <= e:
        out.append(s.isoformat())
        s += timedelta(days=7)
    return out


def _default_start(today: date) -> str:
    return (today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)).isoformat()


def run(db_path, start=None, keep_days=None, full=False,
        fetch_week=fetch.fetch_week, now_iso=None):
    """Enumerate delay-aware weeks, fetch new (and the trailing few) with
    replace-week writes, snapshot, optionally prune. Returns
    (snapshot_id, week_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = date.fromisoformat(now_iso[:10])
    end = (today - timedelta(days=_PUBLICATION_LAG_DAYS)).isoformat()
    start = start or _default_start(today)
    weeks = weeks_in_range(start, end)

    conn = db.connect(db_path)
    week_count, row_count = 0, 0
    try:
        db.ensure_schema(conn)
        stored = set(db.stored_weeks(conn))
        refetch = set() if full else set(sorted(stored)[-_REFETCH_WEEKS:])
        for w in weeks:
            if not full and w in stored and w not in refetch:
                continue
            try:
                rows = fetch_week(w)
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {w}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            if rows is None:                     # not published / absent
                continue
            db.upsert_venues(conn, rows)
            n = db.replace_week(conn, w, rows)
            db.record_week(conn, w, now_iso, n)
            week_count += 1
            row_count += n
        snapshot_id = db.write_snapshot(conn, now_iso, week_count, row_count)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, week_count, row_count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="ats",
        description="Pull FINRA weekly OTC/ATS (dark-pool) volume into SQLite")
    p.add_argument("--db", default="finra_ats.db")
    p.add_argument("--start", default=None,
                   help="earliest week to ingest (YYYY-MM-DD; default ~6mo back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every week in range")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, wc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} rows across {wc} weeks into {a.db}")


if __name__ == "__main__":
    main()
