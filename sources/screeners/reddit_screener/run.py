import argparse
import sys
from datetime import datetime, timezone

from sources.screeners.reddit_screener import db, fetch

DEFAULT_FILTERS = ["all-stocks", "4chan"]


def run(db_path, filters=None, keep_days=None,
        fetch_filter=fetch.fetch_filter, now_iso=None):
    """Fetch each filter and append a snapshot. Returns [(snapshot_id, count)]."""
    filters = filters or DEFAULT_FILTERS
    captured_at = now_iso or datetime.now(timezone.utc).isoformat()
    conn = db.connect(db_path)
    results = []
    try:
        db.ensure_schema(conn)
        for filter_ in filters:
            rows = fetch_filter(filter_)
            if not rows:
                print(f"warning: filter '{filter_}' returned 0 tickers",
                      file=sys.stderr)
            snapshot_id, count = db.write_snapshot(conn, captured_at, filter_, rows)
            db.upsert_tickers(conn, rows, captured_at)
            results.append((snapshot_id, count))
        if keep_days is not None:
            db.prune(conn, keep_days, captured_at)
    finally:
        conn.close()
    return results


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="reddit", description="Pull ApeWisdom Reddit sentiment into SQLite")
    p.add_argument("--db", default="reddit.db")
    p.add_argument("--filters", default="all-stocks,4chan",
                   help="comma-separated ApeWisdom filters")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    filters = [f.strip() for f in a.filters.split(",") if f.strip()]
    results = run(a.db, filters, a.keep_days)
    total = sum(n for _, n in results)
    print(f"stored {total} rows across {len(results)} filter(s) into {a.db}")


if __name__ == "__main__":
    main()
