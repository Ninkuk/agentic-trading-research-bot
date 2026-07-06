"""Combine per-source signals into data/composite.db.

Two-phase: (1) per-source sequential read-only ATTACH -> extract ->
DETACH (SQLite caps attached DBs at 10, so never all-at-once); (2) build
market_regime + ticker_scores inside composite.db with nothing attached.
Time enters only as now_iso; extraction binds the run's own :today (the
one-clock rule) and never reads calendar_now-dependent source views.
Skip-and-continue per signal; failures print exception type names only."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.composite import catalog, db, fetch


def run(
    db_path, db_dir, now_iso=None, only=None, exclude=None, add=None, keep_days=None, signals=None
):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    today = now_iso[:10]
    if signals is None:
        signals = catalog.select_ids(only, exclude, add)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso, len(signals))
        ok = failed = 0
        by_db: dict[str, list] = {}
        for s in signals:
            by_db.setdefault(s["db"], []).append(s)
        for db_file, sigs in by_db.items():
            path = os.path.join(db_dir, db_file)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                print(f"skip {db_file}: {type(e).__name__}")
                failed += len(sigs)
                continue
            try:
                for sig in sigs:
                    try:
                        rows = fetch.extract(conn, sig, today)
                        db.write_signal_values(conn, sid, rows)
                        conn.commit()
                        ok += 1
                    except Exception as e:
                        conn.rollback()
                        print(f"skip {sig['signal_id']}: {type(e).__name__}")
                        failed += 1
            finally:
                fetch.detach(conn)
        try:
            db.apply_crosswalk(conn, sid, catalog.CROSSWALK)
            db.write_market_regime(conn, sid, catalog.REGIME_FIELDS)
            db.write_ticker_scores(conn, sid)
        except Exception as e:
            # Loud failure, honest header: record the real phase-1 counts,
            # drop partial combine writes, and re-raise for the operator.
            conn.rollback()
            db.finish_snapshot(conn, sid, ok, failed)
            conn.commit()
            print(f"combine failed: {type(e).__name__}")
            raise
        db.finish_snapshot(conn, sid, ok, failed)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, ok, failed


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="composite",
        description="Combine per-source signals into a market-regime row"
        " + per-ticker scorecard (reads other data/ DBs"
        " read-only)",
    )
    p.add_argument("--db", default="composite.db")
    p.add_argument("--db-dir", default="data", help="directory holding the source DBs")
    p.add_argument("--only", action="append")
    p.add_argument("--exclude", action="append")
    p.add_argument("--add", action="append")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, ok, failed = run(
        a.db, a.db_dir, only=a.only, exclude=a.exclude, add=a.add, keep_days=a.keep_days
    )
    print(f"composite snapshot {sid}: {ok} signals ok, {failed} failed, into {a.db}")


if __name__ == "__main__":
    main()
