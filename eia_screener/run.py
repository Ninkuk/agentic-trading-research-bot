import argparse
import os
import sys
from datetime import datetime, timezone

from eia_screener import catalog, db, fetch


def run(db_path, only=None, exclude=None, add=None, start=None, keep_days=None,
        api_key=None, now_iso=None, fetch_series_obs=fetch.fetch_series_obs):
    """Fetch selected EIA series, upsert obs, snapshot, optionally prune.
    Skip-and-continue. Returns (snapshot_id, series_count, observation_count)."""
    api_key = fetch.require_api_key(api_key or os.environ.get("EIA_API_KEY"))
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()

    ad_hoc, add_ids = {}, []
    for token in (add or []):
        route, _, facet = token.partition(":")
        if not route or not facet:
            print(f"warning: bad --add token {token} (want route:facet)",
                  file=sys.stderr)
            continue
        ad_hoc[facet] = catalog.Series(facet, route, facet, facet, "custom")
        add_ids.append(facet)

    ids = catalog.select_ids([s.series_id for s in catalog.CATALOG], only,
                             exclude, add=add_ids)
    by_id = {**{s.series_id: s for s in catalog.CATALOG}, **ad_hoc}

    conn = db.connect(db_path)
    successes, total_obs = 0, 0
    try:
        db.ensure_schema(conn)
        for sid in ids:
            s = by_id.get(sid)
            if s is None:
                continue
            try:
                rows, unit = fetch_series_obs(s.route, s.facet, api_key,
                                              start=start)
                db.upsert_series(conn, [{"series_id": s.series_id,
                    "route": s.route, "label": s.label, "category": s.category,
                    "unit": unit, "frequency": "weekly"}], now_iso)
                n = db.write_observations(conn, s.series_id, rows)
            except Exception as e:  # key rides in the URL -> type name only
                conn.rollback()
                print(f"warning: skipping {sid}: {type(e).__name__}",
                      file=sys.stderr)
                continue
            successes += 1
            total_obs += n

        if successes == 0:
            print("warning: no EIA series fetched (0 series, 0 observations)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, successes, total_obs)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, successes, total_obs


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="eia",
        description="Pull weekly EIA energy-inventory series into SQLite")
    p.add_argument("--db", default="eia.db")
    p.add_argument("--only", default=None, help="comma-separated series ids")
    p.add_argument("--exclude", default=None, help="comma-separated ids to skip")
    p.add_argument("--add", action="append", default=None,
                   help="ad-hoc series as route:facet (repeatable)")
    p.add_argument("--start", default=None, help="period floor (YYYY-MM-DD)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, sc, oc = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                    add=a.add, start=a.start, keep_days=a.keep_days)
    print(f"stored {oc} observations across {sc} series into {a.db}")


if __name__ == "__main__":
    main()
