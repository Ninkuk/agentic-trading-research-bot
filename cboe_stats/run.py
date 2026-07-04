import argparse
import sys
from datetime import datetime, timezone

from cboe_stats import catalog, db, fetch


def _filter_start(rows, start):
    return [r for r in rows if r["date"] >= start] if start else rows


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        now_iso=None, fetch_pcr=fetch.fetch_pcr, fetch_vix=fetch.fetch_vix):
    """Fetch selected CBOE feeds, upsert into pcr_daily/vix_daily, snapshot,
    optionally prune. Skip-and-continue. Returns
    (snapshot_id, feed_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    ids = catalog.select_ids([f.feed_id for f in catalog.CATALOG], only, exclude,
                             add)
    kind_by_id = {f.feed_id: f.kind for f in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for feed_id in ids:
            kind = kind_by_id.get(feed_id, "vix")  # --add unknown -> vix
            try:
                if kind == "pcr":
                    rows = fetch_pcr()
                    if rows is None:
                        continue                    # 403/404 skip
                    n = db.write_pcr(conn, _filter_start(rows, start))
                else:
                    rows = fetch_vix(feed_id)
                    if rows is None:
                        continue
                    n = db.write_vix(conn, feed_id, _filter_start(rows, start))
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {feed_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no CBOE feeds fetched (0 feeds, 0 rows)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cboe_stats",
        description="Pull CBOE market-wide put/call + VIX sentiment into SQLite")
    p.add_argument("--db", default="cboe_stats.db")
    p.add_argument("--only", default=None, help="comma-separated feed ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra vol-index feed id (repeatable)")
    p.add_argument("--start", default=None,
                   help="filter parsed rows to date >= this (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, fc, rc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {rc} rows across {fc} feeds into {a.db}")


if __name__ == "__main__":
    main()
