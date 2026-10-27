import argparse
import sys
from datetime import UTC, datetime

from sources.common.screener_common import select_ids, split_csv
from sources.screeners.stock_analysis_screener import catalog, db, fetch
from sources.screeners.stock_analysis_screener.typing import column_type

SOURCE = "stockanalysis.com"

_RESERVED_COLUMNS = {"snapshot_id", "symbol"}


def run(
    db_path,
    keep_days=None,
    only=None,
    exclude=None,
    type_="s",
    fetch_catalog=catalog.fetch_catalog,
    fetch_data=fetch.fetch_data_points,
    now_iso=None,
):
    data_points, universe_count = fetch_catalog(type_)
    all_ids = [d.id for d in data_points]
    ids = select_ids(all_ids, only, exclude)
    # Defensive guard: never let a catalog id collide with a base metrics column.
    ids = [i for i in ids if i not in _RESERVED_COLUMNS]
    data = fetch_data(ids, type_)
    if len(data) < universe_count:
        print(
            f"warning: stored {len(data)} stocks but catalog reported {universe_count}",
            file=sys.stderr,
        )

    # Build the column set, skipping any data-point that is null for every
    # symbol this run (e.g. a pro-only field on a free plan). Creating a column
    # for each such id would grow the metrics table unboundedly across runs.
    columns = {}
    stored_ids = []
    for cid in ids:
        values = [row.get(cid) for row in data.values()]
        if all(v is None for v in values):
            continue
        columns[cid] = column_type(cid, values)
        stored_ids.append(cid)
    skipped = len(ids) - len(stored_ids)
    if skipped:
        print(
            f"warning: skipped {skipped} data-point column(s) with no values this run",
            file=sys.stderr,
        )

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn, columns)
        db.upsert_data_points(conn, data_points)
        captured_at = now_iso or datetime.now(UTC).isoformat()
        snapshot_id = db.write_snapshot(conn, captured_at, SOURCE, data, stored_ids)
        if keep_days is not None:
            db.prune(conn, keep_days, captured_at)
    finally:
        conn.close()
    return snapshot_id, len(data)


def main(argv=None):
    p = argparse.ArgumentParser(description="Pull stockanalysis.com screener into SQLite")
    p.add_argument("--db", default="stocks.db")
    p.add_argument("--keep-days", type=int, default=None)
    p.add_argument("--only", default=None, help="comma-separated data-point ids")
    p.add_argument("--exclude", default=None, help="comma-separated data-point ids")
    p.add_argument("--type", dest="type_", default="s", choices=sorted(catalog.TYPE_ROUTES))
    a = p.parse_args(argv)
    only = split_csv(a.only)
    exclude = split_csv(a.exclude)
    snapshot_id, n = run(a.db, a.keep_days, only, exclude, a.type_)
    print(f"snapshot {snapshot_id}: stored {n} stocks into {a.db}")


if __name__ == "__main__":
    main()
