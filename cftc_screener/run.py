import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from cftc_screener import catalog, db, fetch

# On incremental re-runs, re-fetch this many recent weeks per market so the
# (code, report_date) upsert re-absorbs CFTC's revisions to already-stored
# weeks. --full ignores this and re-pulls from --start (or full history).
_LOOKBACK_WEEKS = 10


def _fetch_floor(conn, code, start, full):
    """Inclusive report-date floor to fetch from for one market. A full re-pull
    (or a first-ever pull with no stored data) uses the caller's ``start`` (None
    = full history). Otherwise re-fetch a recent lookback window ending at the
    latest stored week."""
    if full:
        return start
    last = db.max_report_date(conn, code)
    if last is None:
        return start
    return (datetime.fromisoformat(last)
            - timedelta(weeks=_LOOKBACK_WEEKS)).date().isoformat()


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        app_token=None, full=False, fetch_rows=fetch.fetch_market_rows,
        now_iso=None):
    """Fetch selected CFTC markets into SQLite, upserting weekly COT history.
    Incremental runs re-fetch the last _LOOKBACK_WEEKS weeks per market to catch
    revisions; full=True re-pulls from ``start`` (or full history).
    Returns (snapshot_id, market_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    app_token = app_token or os.environ.get("CFTC_APP_TOKEN")  # optional; may be None

    asset = {m.code: m.asset_class for m in catalog.CATALOG}
    all_codes = [m.code for m in catalog.CATALOG]
    codes = catalog.select_ids(all_codes, only, exclude, add=add)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        successes = 0
        total_rows = 0
        for code in codes:
            try:
                floor = _fetch_floor(conn, code, start, full)
                rows = fetch_rows(code, app_token=app_token, start=floor)
                if rows:
                    name = rows[-1].get("name")  # ordered ascending -> newest last
                    db.upsert_markets(conn, [{"code": code, "name": name,
                                              "asset_class": asset.get(code, "custom")}],
                                      now_iso)
                    total_rows += db.write_cot(conn, code, rows)
                successes += 1
            except Exception as e:  # skip-and-continue on any per-market failure
                # Roll back the failed market's uncommitted writes, then log only
                # the exception class — never str(e)/e.url, which may echo the
                # request URL or token.
                conn.rollback()
                print(f"warning: skipping {code}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        if successes == 0:
            print("warning: no CFTC markets fetched successfully; "
                  "wrote empty snapshot", file=sys.stderr)

        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="cftc",
        description="Pull curated CFTC COT positioning into SQLite")
    p.add_argument("--db", default="cftc.db")
    p.add_argument("--only", default=None,
                   help="comma-separated contract codes to pull (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated contract codes to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra contract code not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="earliest report date YYYY-MM-DD (default: full history)")
    p.add_argument("--full", action="store_true",
                   help="re-pull from --start (or full history), ignoring the "
                        "incremental lookback")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    exclude = a.exclude.split(",") if a.exclude else None
    _, mc, rc = run(a.db, only=only, exclude=exclude, add=a.add, start=a.start,
                    keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} weekly rows across {mc} markets into {a.db}")


if __name__ == "__main__":
    main()
