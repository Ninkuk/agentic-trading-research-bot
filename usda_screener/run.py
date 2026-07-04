import argparse
import os
import sys
from datetime import datetime, timezone

from usda_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, keep_days=None, api_key=None,
        now_iso=None, fetch_target=fetch.fetch_target):
    """Fetch selected USDA targets, upsert obs, snapshot, optionally prune.
    Skip-and-continue. Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("NASS_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    by_id = {s.id: s for s in catalog.CATALOG}
    ids = catalog.select_ids([s.id for s in catalog.CATALOG], only, exclude,
                             add=add)

    conn = db.connect(db_path)
    successes, total_obs = 0, 0
    try:
        db.ensure_schema(conn)
        for cid in ids:
            s = by_id.get(cid)
            if s is None:
                print(f"warning: unknown target {cid}", file=sys.stderr)
                continue
            try:
                rows = fetch_target(s.query, api_key)
                n = db.write_observations(conn, s.commodity, s.metric, rows)
            except Exception as e:  # key rides in the URL -> type name only
                conn.rollback()
                print(f"warning: skipping {cid}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_obs += n

        if successes == 0:
            print("warning: no USDA targets fetched (0 series, 0 observations)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_obs)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_obs


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="usda",
        description="Pull USDA crop supply/demand balance-sheet data into SQLite")
    p.add_argument("--db", default="usda.db")
    p.add_argument("--only", default=None, help="comma-separated COMMODITY:METRIC")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra catalog-known COMMODITY:METRIC (repeatable)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, sc, oc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} targets into {a.db}")


if __name__ == "__main__":
    main()
