import argparse
import sys
from datetime import datetime, timedelta, timezone

from edgar_screener import db, fetch

_MAX_BACK = 5


def run(db_path, index_date=None, keep_days=None,
        fetch_index=fetch.fetch_daily_index, fetch_map=fetch.fetch_ticker_map,
        now_iso=None):
    """Fetch one EDGAR daily index, join tickers, append a snapshot.
    Returns (snapshot_id, filing_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    if index_date is None:
        day = datetime.fromisoformat(now_iso).date()
        rows = None
        for _ in range(_MAX_BACK + 1):
            index_date = day.isoformat()
            rows = fetch_index(index_date)
            if rows is not None:
                break
            day -= timedelta(days=1)
        if rows is None:
            raise RuntimeError(
                f"no EDGAR daily index in the {_MAX_BACK} days before {now_iso}")
    else:
        rows = fetch_index(index_date)
        if rows is None:
            raise RuntimeError(f"no EDGAR index for {index_date}")

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)

        # Ticker map is core to the join; a failure here must abort before
        # any snapshot is written (the schema itself is idempotent DDL, not
        # a data write, so creating it first is safe).
        tmap = fetch_map()

        for r in rows:
            info = tmap.get(r["cik"])
            r["ticker"] = info["ticker"] if info else None

        if not rows:
            print(f"warning: EDGAR index for {index_date} has 0 filings",
                  file=sys.stderr)

        snapshot_id, count = db.write_snapshot(conn, now_iso, index_date, rows)
        db.upsert_issuers(conn, rows, now_iso)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="edgar",
        description="Pull the SEC EDGAR daily filing index into SQLite")
    p.add_argument("--db", default="edgar.db")
    p.add_argument("--date", default=None,
                   help="YYYY-MM-DD filing day (default: latest available)")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    _, count = run(a.db, index_date=a.date, keep_days=a.keep_days)
    print(f"stored {count} filings into {a.db}")


if __name__ == "__main__":
    main()
