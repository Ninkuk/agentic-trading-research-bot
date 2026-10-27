import argparse
import sys
from datetime import UTC, datetime

from sources.common.screener_common import max_date, since_floor, split_csv
from sources.screeners.treasury_screener import catalog, db, fetch

# On incremental re-runs, re-fetch this many days before the latest stored
# record_date so the record_date upsert re-absorbs restatements to recent days
# (fiscal agencies revise a few days back). --full ignores it and re-pulls from
# --start (or full history). See [[incremental-since-misses-revisions]].
_LOOKBACK_DAYS = 7


# dataset_id -> (parser, writer, table). yield_curve is handled separately (XML).
_HANDLERS = {
    "dts_cash": (fetch.parse_dts_cash, db.write_dts_cash, "dts_cash"),
    "debt_penny": (fetch.parse_debt_penny, db.write_debt_penny, "debt_penny"),
    "avg_rates": (fetch.parse_avg_rates, db.write_avg_rates, "avg_rates"),
    "upcoming_auctions": (
        fetch.parse_upcoming_auctions,
        db.write_upcoming_auctions,
        "upcoming_auctions",
    ),
    "auction_results": (fetch.parse_auction_results, db.write_auction_results, "auction_results"),
}


def run(
    db_path,
    only=None,
    exclude=None,
    add=None,
    start=None,
    keep_days=None,
    full=False,
    fetch_dataset=fetch.fetch_dataset,
    fetch_yield_curve=fetch.fetch_yield_curve,
    now_iso=None,
):
    """Fetch the selected Treasury datasets, upsert each into its table,
    snapshot the run, optionally prune. Skip-and-continue per dataset. Returns
    (snapshot_id, dataset_count, row_count)."""
    now_iso = now_iso or datetime.now(UTC).isoformat()
    year = int(now_iso[:4])
    ids = catalog.select_ids([d.dataset_id for d in catalog.CATALOG], only, exclude, add=add)
    by_id = {d.dataset_id: d for d in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        db.set_today(conn, now_iso)
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
                        since = since_floor(
                            max_date(conn, table, "record_date"),
                            start,
                            full,
                            lookback_days=_LOOKBACK_DAYS,
                        )
                    raw = fetch_dataset(ds.endpoint if ds else dataset_id, since=since)
                    n = writer(conn, parser(raw))
                else:
                    print(f"warning: unknown dataset {dataset_id}", file=sys.stderr)
                    continue
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {dataset_id}: {type(e).__name__}", file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no Treasury datasets fetched (0 datasets, 0 rows)", file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="treasury", description="Pull U.S. Treasury Fiscal Data datasets into SQLite"
    )
    p.add_argument("--db", default="treasury.db")
    p.add_argument("--only", default=None, help="comma-separated dataset ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument(
        "--add",
        action="append",
        default=None,
        help="extra dataset id not in the catalog (repeatable)",
    )
    p.add_argument(
        "--start", default=None, help="record_date floor for the first fetch (YYYY-MM-DD)"
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="re-pull from --start (or full history), ignoring the incremental revision-lookback",
    )
    p.add_argument(
        "--keep-days", type=int, default=None, help="prune snapshot provenance older than N days"
    )
    a = p.parse_args(argv)
    _, nds, nrows = run(
        a.db,
        only=split_csv(a.only),
        exclude=split_csv(a.exclude),
        add=a.add,
        start=a.start,
        full=a.full,
        keep_days=a.keep_days,
    )
    print(f"stored {nrows} rows across {nds} datasets into {a.db}")


if __name__ == "__main__":
    main()
