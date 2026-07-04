import argparse
import os
import sys
from datetime import datetime, timezone

import monitor_common
from econ_calendar import catalog, db, fetch


def run(db_path, only=None, exclude=None, horizon_days=7, keep_days=None,
        api_key=None, fetch_one=fetch.fetch_release_dates, now_iso=None):
    """Fetch upcoming release dates for the selected FRED releases, upsert them
    into the events calendar, snapshot the run, and optionally prune old
    snapshots. Returns (snapshot_id, event_count).

    Per-release fetch is skip-and-continue: one release failing never aborts the
    run, and only type(e).__name__ is logged (a FRED URL embeds the api_key)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("FRED_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()

    ids = catalog.select_ids(only, exclude)
    by_id = {r.release_id: r for r in catalog.CATALOG}

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days)
        rows = []
        for release_id in ids:
            try:
                raw = fetch_one(release_id, api_key, today)
                rows.extend(fetch.parse_release_dates(raw, {release_id:
                                                            by_id[release_id]}))
            except Exception as e:  # skip-and-continue; never echo str(e)/e.url
                conn.rollback()
                print(f"warning: skipping {release_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
        count = monitor_common.upsert_events(conn, rows, now_iso)
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count, "fred")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="econ_calendar",
        description="Pull the FRED forward economic-release calendar into SQLite")
    p.add_argument("--db", default="econ_calendar.db")
    p.add_argument("--only", default=None,
                   help="comma-separated release_ids to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated release_ids to skip")
    p.add_argument("--horizon-days", type=int, default=7,
                   help="imminence window for v_imminent_high_impact")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, count = run(a.db, only=only, exclude=exclude,
                   horizon_days=a.horizon_days, keep_days=a.keep_days)
    print(f"stored {count} scheduled releases into {a.db}")


if __name__ == "__main__":
    main()
