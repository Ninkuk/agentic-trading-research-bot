import argparse
import os
import sys
from datetime import datetime, timezone

from usda_screener import catalog, db, fetch, wasde

# How many months to walk back looking for the newest published WASDE release
# (the current month's report may not be out yet).
_WASDE_LOOKBACK = 6


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


def _months_back(now_iso, n):
    """Yield (year, month) from now_iso's month back n-1 further months."""
    d = datetime.fromisoformat(now_iso)
    y, m = d.year, d.month
    for _ in range(n):
        yield y, m
        m -= 1
        if m == 0:
            y, m = y - 1, 12


def run_wasde(db_path, year=None, month=None, keep_days=None, now_iso=None,
              fetch=wasde.fetch_wasde):
    """Ingest the WASDE balance sheet into the wasde_obs sibling. With an
    explicit (year, month) fetch that release; otherwise walk back from the
    current month to the newest published release (a 404 -> not yet out). No API
    key needed. Returns (snapshot_id, commodity_count, observation_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    targets = ([(year, month)] if year and month
               else list(_months_back(now_iso, _WASDE_LOOKBACK)))

    conn = db.connect(db_path)
    obs_count, commodities = 0, set()
    try:
        db.ensure_schema(conn)
        rows = None
        for y, m in targets:
            try:
                rows = fetch(y, m)
            except Exception as e:  # a bad release -> try the previous month
                print(f"warning: WASDE {y}-{m:02d}: {type(e).__name__}",
                      file=sys.stderr)
                rows = None
            if rows is not None:
                break
        if rows:
            obs_count = db.write_wasde(conn, rows)
            commodities = {r["commodity"] for r in rows}
        else:
            print("warning: no WASDE release found (0 commodities, 0 rows)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, len(commodities), obs_count)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, len(commodities), obs_count


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
    p.add_argument("--wasde", action="store_true",
                   help="ingest the WASDE balance sheet (OCE CSV) instead of "
                        "Quick Stats — no API key needed")
    p.add_argument("--wasde-month", default=None,
                   help="pin a WASDE release YYYY-MM (default: latest published)")
    a = p.parse_args(argv)
    if a.wasde:
        y = m = None
        if a.wasde_month:
            y, m = (int(x) for x in a.wasde_month.split("-"))
        _, cc, oc = run_wasde(a.db, year=y, month=m, keep_days=a.keep_days)
        print(f"stored {oc} WASDE observations across {cc} commodities "
              f"into {a.db}")
        return
    _, sc, oc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} targets into {a.db}")


if __name__ == "__main__":
    main()
