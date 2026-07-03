import argparse
import os
import sys
from datetime import datetime, timezone

from fred_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        api_key=None, fetch_series=fetch.fetch_series,
        fetch_obs=fetch.fetch_observations, now_iso=None):
    """Fetch selected FRED series into SQLite, upserting observation history.
    Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("FRED_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    themes = {s.series_id: s.theme for s in catalog.CATALOG}
    all_ids = [s.series_id for s in catalog.CATALOG]
    ids = catalog.select_ids(all_ids, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_obs = 0
        for series_id in ids:
            try:
                meta = fetch_series(series_id, api_key)
                obs = fetch_obs(series_id, api_key, start=start)
            except Exception as e:  # skip-and-continue on any per-series failure
                print(f"warning: skipping {series_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            meta = {**meta, "theme": themes.get(series_id, "custom")}
            db.upsert_series(conn, [meta], now_iso)
            total_obs += db.write_observations(conn, series_id, obs)
            successes += 1

        if successes == 0:
            print("warning: no FRED series fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_obs)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_obs


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fred",
        description="Pull curated FRED macro series into SQLite")
    p.add_argument("--db", default="fred.db")
    p.add_argument("--only", default=None,
                   help="comma-separated series ids to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated series ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra series id not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="observation_start YYYY-MM-DD (default: full history)")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, sc, oc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} series into {a.db}")


if __name__ == "__main__":
    main()
