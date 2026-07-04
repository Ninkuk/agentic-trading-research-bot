import argparse
import sys
from datetime import datetime, timedelta, timezone

from sources.screeners.treasury_screener import catalog, db, fetch

# On incremental re-runs, re-fetch this many days before the latest stored
# record_date so the record_date upsert re-absorbs restatements to recent days
# (fiscal agencies revise a few days back). --full ignores it and re-pulls from
# --start (or full history). See [[incremental-since-misses-revisions]].
_LOOKBACK_DAYS = 7


def _since_floor(last, start, full):
    """Inclusive record_date floor for a daily/monthly dataset. Explicit
    ``start`` wins; ``full`` (or a first-ever pull with no stored data) pulls
    full history / from start; otherwise floor at ``last`` - _LOOKBACK_DAYS."""
    if start is not None:
        return start
    if full or last is None:
        return start
    return (datetime.fromisoformat(last)
            - timedelta(days=_LOOKBACK_DAYS)).date().isoformat()

# dataset_id -> (parser, writer, table). yield_curve is handled separately (XML).
_HANDLERS = {
    "dts_cash": (fetch.parse_dts_cash, db.write_dts_cash, "dts_cash"),
    "debt_penny": (fetch.parse_debt_penny, db.write_debt_penny, "debt_penny"),
    "avg_rates": (fetch.parse_avg_rates, db.write_avg_rates, "avg_rates"),
    "upcoming_auctions": (fetch.parse_upcoming_auctions,
                          db.write_upcoming_auctions, "upcoming_auctions"),
    "auction_results": (fetch.parse_auction_results, db.write_auction_results,
                        "auction_results"),
}


def _max_date(conn, table, date_col="record_date"):
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    return row[0] if row and row[0] else None


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        full=False, fetch_dataset=fetch.fetch_dataset,
        fetch_yield_curve=fetch.fetch_yield_curve, now_iso=None):
    """Fetch the selected Treasury datasets, upsert each into its table,
    snapshot the run, optionally prune. Skip-and-continue per dataset. Returns
    (snapshot_id, dataset_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    year = int(now_iso[:4])
    ids = catalog.select_ids([d.dataset_id for d in catalog.CATALOG], only,
                             exclude, add=add)
    by_id = {d.dataset_id: d for d in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for dataset_id in ids:
            ds = by_id.get(dataset_id)
            try:
                if dataset_id == "yield_curve":
                    rows = fetch_yield_curve(year)
                    n = db.write_yield_curve(conn, rows)
                elif dataset_id in _HANDLERS:
                    parser, writer, table = _HANDLERS[dataset_id]
                    # event datasets have no record_date floor; daily/monthly do
                    if ds and ds.frequency == "event":
                        since = start
                    else:
                        since = _since_floor(_max_date(conn, table), start, full)
                    raw = fetch_dataset(ds.endpoint if ds else dataset_id,
                                        since=since)
                    n = writer(conn, parser(raw))
                else:
                    print(f"warning: unknown dataset {dataset_id}",
                          file=sys.stderr)
                    continue
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {dataset_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no Treasury datasets fetched (0 datasets, 0 rows)",
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
        prog="treasury",
        description="Pull U.S. Treasury Fiscal Data datasets into SQLite")
    p.add_argument("--db", default="treasury.db")
    p.add_argument("--only", default=None, help="comma-separated dataset ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra dataset id not in the catalog (repeatable)")
    p.add_argument("--start", default=None,
                   help="record_date floor for the first fetch (YYYY-MM-DD)")
    p.add_argument("--full", action="store_true",
                   help="re-pull from --start (or full history), ignoring the "
                        "incremental revision-lookback")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, nds, nrows = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                        add=a.add, start=a.start, full=a.full,
                        keep_days=a.keep_days)
    print(f"stored {nrows} rows across {nds} datasets into {a.db}")


if __name__ == "__main__":
    main()
