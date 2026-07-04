# finra_short_volume/run.py
import argparse
import sys
from datetime import date as date_cls, datetime, timedelta, timezone

from sources.screeners.finra_short_volume import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored days so a
# FINRA file repost is re-absorbed by the per-day replace. --full re-ingests
# every day in range.
_REFETCH_DAYS = 2
_DEFAULT_LOOKBACK_DAYS = 183       # ~6 months


def days_in_range(start_date: str, end_date: str) -> list[str]:
    """All calendar dates start_date..end_date inclusive, each 'YYYY-MM-DD'."""
    d = date_cls.fromisoformat(start_date)
    end = date_cls.fromisoformat(end_date)
    out = []
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _default_start(now_dt, days: int = _DEFAULT_LOOKBACK_DAYS) -> str:
    """'YYYY-MM-DD' for `days` before now_dt's date."""
    return (now_dt.date() - timedelta(days=days)).isoformat()


def run(db_path, start=None, keep_days=None, full=False,
        fetch_day=fetch.fetch_day, now_iso=None) -> tuple[int, int, int]:
    """Ingest FINRA daily short-volume files into SQLite. Enumerate calendar days
    from `start` (default: ~6 months back) through today; ingest new days and
    re-fetch the trailing _REFETCH_DAYS already-stored ones (all of them when
    full=True). A 404 (weekend/holiday/unpublished) is skipped. Any per-day
    failure rolls back and continues. Returns (snapshot_id, day_count,
    row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_date = now_dt.date().isoformat()
    all_days = days_in_range(start, end_date)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_days(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_DAYS:])   # newest already-stored days

        day_count = 0
        total_rows = 0
        for day in all_days:
            if not full and day in stored_set and day not in refetch:
                continue
            try:
                rows = fetch_day(day)
                if rows is None:                  # 404 -> weekend/holiday/unpub
                    continue
                db.upsert_securities(conn, rows)
                written = db.replace_day(conn, day, rows)
                db.record_day(conn, day, now_iso, written)
                total_rows += written
                day_count += 1
            except Exception as e:  # skip-and-continue on any per-day failure
                # Roll back the failed day's uncommitted writes, then log only the
                # exception class — never str(e)/e.url.
                conn.rollback()
                print(f"warning: skipping {day}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, day_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, day_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="short_volume",
        description="Pull FINRA daily short sale volume into SQLite")
    p.add_argument("--db", default="short_volume.db")
    p.add_argument("--start", default=None,
                   help="earliest trading date YYYY-MM-DD "
                        "(default: ~6 months back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every day in range, ignoring the "
                        "incremental skip")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches short-volume history)")
    a = p.parse_args(argv)
    _, dc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} short-volume rows across {dc} days into {a.db}")


if __name__ == "__main__":
    main()
