"""Nightly grade of composite opinions: harvest -> register -> mature.
Every step idempotent; missed nights self-heal. Sources attached read-only
one at a time. The scorer never writes anything back into the composite."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.scorer import catalog, db, fetch


def run(db_path, db_dir, now_iso=None, keep_days=None, rebuild_prices=False):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        if rebuild_prices:
            # One-shot repair, never scheduled. Must precede the harvest: the
            # ledger is INSERT OR IGNORE, so stale rows win until deleted.
            dropped, outcomes, regs = db.rebuild_prices(conn)
            print(f"rebuild: {dropped} prices, {outcomes} outcomes, {regs} registrations dropped")
        sid = db.write_snapshot(conn, now_iso)
        harvested = registered = matured = skipped = 0
        # 1) harvest
        for src_db in catalog.PRICE_DBS:
            path = os.path.join(db_dir, src_db)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                print(f"skip {src_db}: {type(e).__name__}")
                continue
            try:
                harvested += db.insert_prices(conn, fetch.harvest_prices(conn))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"skip {src_db}: {type(e).__name__}")
            finally:
                fetch.detach(conn)
        # 2) register
        path = os.path.join(db_dir, catalog.COMPOSITE_DB)
        try:
            fetch.attach_ro(conn, path)
        except Exception as e:
            print(f"skip {catalog.COMPOSITE_DB}: {type(e).__name__}")
        else:
            try:
                done = db.registered_ids(conn)
                for csid, cdate in fetch.read_snapshots(conn):
                    if csid in done:
                        continue
                    reg, skip = db.register_snapshot(
                        conn,
                        csid,
                        cdate,
                        fetch.read_ticker_scores(conn, csid),
                        fetch.read_signal_rows(conn, csid),
                        fetch.read_regime(conn, csid),
                        catalog.HORIZONS,
                        catalog.BENCHMARK,
                        catalog.ENTRY_MAX_AGE_DAYS,
                        now_iso,
                        crosswalk_benchmark=catalog.CROSSWALK_BENCHMARK,
                    )
                    registered += reg
                    skipped += skip
            except Exception as e:
                conn.rollback()
                print(f"skip registration: {type(e).__name__}")
            finally:
                fetch.detach(conn)
        # 3) mature (local only)
        matured = db.mature(conn, now_iso, catalog.BENCHMARK)
        db.finish_snapshot(conn, sid, harvested, registered, matured, skipped)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, harvested, registered, matured, skipped


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="scorer",
        description="Grade composite opinions against forward returns"
        " (reads composite/stocks/etfs read-only)",
    )
    p.add_argument("--db", default="scorer.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    p.add_argument(
        "--rebuild-prices",
        action="store_true",
        help="ONE-SHOT REPAIR, never schedule: delete the price ledger and every"
        " unmatured outcome, then re-harvest. Refuses if any outcome has matured.",
    )
    a = p.parse_args(argv)
    sid, harvested, registered, matured, skipped = run(
        a.db, a.db_dir, keep_days=a.keep_days, rebuild_prices=a.rebuild_prices
    )
    print(
        f"scorer snapshot {sid}: {harvested} prices, {registered}"
        f" registered, {matured} matured, {skipped} skipped, into {a.db}"
    )


if __name__ == "__main__":
    main()
