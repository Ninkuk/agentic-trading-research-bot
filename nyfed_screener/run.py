import argparse
import sys
from datetime import datetime, timezone

from nyfed_screener import catalog, db, fetch

_DATE_COL = {"reference_rates": "effective_date", "repo_ops": "operation_date",
             "soma_holdings": "as_of_date", "primary_dealer_stats": "as_of_date"}
_WRITER = {"reference_rates": db.write_reference_rates, "rrp": db.write_repo_ops,
           "repo": db.write_repo_ops, "soma": db.write_soma_holdings,
           "primary_dealer": db.write_primary_dealer}


def _parse(domain_id, records):
    if domain_id == "reference_rates":
        return fetch.parse_reference_rates(records)
    if domain_id == "rrp":
        return fetch.parse_repo_ops(records, "reverse_repo")
    if domain_id == "repo":
        return fetch.parse_repo_ops(records, "repo")
    if domain_id == "soma":
        return fetch.parse_soma_holdings(records)
    if domain_id == "primary_dealer":
        return fetch.parse_primary_dealer(records)
    return []


def _max_date(conn, table, date_col):
    row = conn.execute(f"SELECT MAX({date_col}) FROM {table}").fetchone()
    return row[0] if row and row[0] else None


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        fetch_domain=fetch.fetch_domain, now_iso=None):
    """Fetch selected NY Fed domains, upsert into per-domain tables, snapshot,
    optionally prune. Skip-and-continue. Returns
    (snapshot_id, domain_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    ids = catalog.select_ids(catalog.enabled_ids(), only, exclude, add=add)
    by_id = {d.domain_id: d for d in catalog.CATALOG}

    conn = db.connect(db_path)
    successes, total_rows = 0, 0
    try:
        db.ensure_schema(conn)
        for domain_id in ids:
            ds = by_id.get(domain_id)
            if ds is None:
                print(f"warning: unknown domain {domain_id}", file=sys.stderr)
                continue
            try:
                since = start if start is not None else _max_date(
                    conn, ds.table, _DATE_COL[ds.table])
                records = fetch_domain(ds.endpoint, start=since)
                n = _WRITER[domain_id](conn, _parse(domain_id, records))
            except Exception as e:
                conn.rollback()
                print(f"warning: skipping {domain_id}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_rows += n

        if successes == 0:
            print("warning: no NY Fed domains fetched (0 domains, 0 rows)",
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
        prog="nyfed",
        description="Pull NY Fed Markets data (rates/repo/SOMA) into SQLite")
    p.add_argument("--db", default="nyfed.db")
    p.add_argument("--only", default=None, help="comma-separated domain ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra domain id e.g. primary_dealer (repeatable)")
    p.add_argument("--start", default=None,
                   help="date floor for the first fetch (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, nd, nr = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {nr} rows across {nd} domains into {a.db}")


if __name__ == "__main__":
    main()
