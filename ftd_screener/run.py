import argparse
import sys
from datetime import datetime, timezone

from ftd_screener import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored periods so
# SEC reposts (which occasionally revise a published half-month) are re-absorbed
# by the per-period replace. --full re-ingests every period in range.
_REFETCH_PERIODS = 2
_DEFAULT_LOOKBACK_MONTHS = 24


def periods_in_range(start_month: str, end_month: str) -> list:
    """Period ids from start_month..end_month inclusive (both 'YYYY-MM'),
    each month yielding its 'a' then 'b' half."""
    y, m = int(start_month[:4]), int(start_month[5:7])
    ey, em = int(end_month[:4]), int(end_month[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}a")
        out.append(f"{y:04d}{m:02d}b")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _default_start(now_dt, months: int = _DEFAULT_LOOKBACK_MONTHS) -> str:
    """'YYYY-MM' for `months` before now_dt."""
    y, m = now_dt.year, now_dt.month - months
    while m <= 0:
        m, y = m + 12, y - 1
    return f"{y:04d}-{m:02d}"


def run(db_path, start=None, keep_days=None, full=False,
        fetch_period=fetch.fetch_period, now_iso=None):
    """Ingest FTD periods into SQLite. Enumerate half-month periods from `start`
    (default: 24 months back) through the current month; ingest new periods and
    re-fetch the trailing _REFETCH_PERIODS already-stored ones (all of them when
    full=True). A 404 (period not yet published) is skipped. Any per-period
    failure rolls back and continues. Returns (snapshot_id, period_count,
    row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_month = f"{now_dt.year:04d}-{now_dt.month:02d}"
    all_periods = periods_in_range(start, end_month)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_periods(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_PERIODS:])  # newest already-stored periods

        period_count = 0
        total_rows = 0
        for period in all_periods:
            if (not full and period in stored_set and period not in refetch):
                continue
            try:
                result = fetch_period(period)
                if result is None:          # 404 -> not yet published
                    continue
                rows, trailer_count = result
                if trailer_count is not None and trailer_count != len(rows):
                    print(f"warning: {period} trailer count {trailer_count} != "
                          f"parsed {len(rows)}", file=sys.stderr)
                db.upsert_securities(conn, rows)
                written = db.replace_period(conn, period, rows)
                db.record_period(conn, period, fetch.settlement_bounds(period),
                                 now_iso, written, trailer_count)
                total_rows += written
                period_count += 1
            except Exception as e:  # skip-and-continue on any per-period failure
                # Roll back the failed period's uncommitted writes, then log only
                # the exception class — never str(e)/e.url, which may echo the URL.
                conn.rollback()
                print(f"warning: skipping {period}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, period_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, period_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="ftd",
        description="Pull SEC fails-to-deliver data into SQLite")
    p.add_argument("--db", default="ftd.db")
    p.add_argument("--start", default=None,
                   help="earliest publication month YYYY-MM "
                        "(default: 24 months back)")
    p.add_argument("--full", action="store_true",
                   help="re-ingest every period in range, ignoring the "
                        "incremental skip")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches fail history)")
    a = p.parse_args(argv)
    _, pc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} fail rows across {pc} periods into {a.db}")


if __name__ == "__main__":
    main()
