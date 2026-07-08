"""Point-in-time replay: copy vintage + benchmark rows out of fred.db, let
the views grade what composite's FRED regime signals would have said each
historical day. The 4th combiner — scheduled weekly (Sat, after
fred-vintages), not nightly, because its only inputs (ALFRED vintages +
SP500 closes) refresh weekly there (see docs/SCHEDULE.md)."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.backtest import catalog, db, fetch


def run(
    db_path,
    db_dir="data",
    now_iso=None,
    keep_days=None,
    harvest_vintages=fetch.harvest_vintages,
    harvest_benchmark=fetch.harvest_benchmark,
    harvest_market_obs=fetch.harvest_market_obs,
):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso)
        n_vint = n_bench = n_market = failures = 0
        path = os.path.join(db_dir, catalog.FRED_DB)
        try:
            fetch.attach_ro(conn, path)
        except Exception as e:
            failures += 1
            print(f"skip {catalog.FRED_DB}: {type(e).__name__}")
        else:
            try:
                series = [s["series_id"] for s in catalog.REPLAY_SIGNALS]
                n_vint = db.insert_vintages(conn, harvest_vintages(conn, series))
                n_bench = db.insert_benchmark(
                    conn, harvest_benchmark(conn, catalog.BENCHMARK_SERIES)
                )
            except Exception as e:
                failures += 1
                conn.rollback()
                n_vint = n_bench = (
                    0  # rollback discarded the copy; header must not claim stale counts
                )
                print(f"skip {catalog.FRED_DB}: {type(e).__name__}")
            finally:
                conn.commit()
                fetch.detach(conn)

        # Non-vintage market-grain signals, grouped by source DB so each is
        # attached once. Same skip-and-continue discipline as the FRED block:
        # a missing/failed source counts as a failure and rolls back only its
        # own copy, never the already-committed FRED data.
        by_db: dict[str, list] = {}
        for s in catalog.MARKET_OBS_SIGNALS:
            by_db.setdefault(s["db"], []).append(s)
        for db_name, sigs in by_db.items():
            try:
                fetch.attach_ro(conn, os.path.join(db_dir, db_name))
            except Exception as e:
                failures += 1
                print(f"skip {db_name}: {type(e).__name__}")
                continue
            try:
                got = 0
                for s in sigs:
                    got += db.insert_market_obs(
                        conn, s["signal_id"], harvest_market_obs(conn, s["harvest_sql"])
                    )
                conn.commit()
                n_market += got
            except Exception as e:
                failures += 1
                conn.rollback()  # discard this DB's partial copy; counts stay honest
                print(f"skip {db_name}: {type(e).__name__}")
            finally:
                fetch.detach(conn)

        db.finish_snapshot(conn, sid, n_vint, n_bench, failures, n_market)
        conn.commit()
        for row in conn.execute(
            "SELECT signal_id, direction, horizon, n_days, n_bench, hit_rate,"
            " hit_ci_lo, hit_ci_hi, reliable FROM v_replay_efficacy"
            " ORDER BY signal_id, direction, horizon"
        ):
            sig, direction, horizon, row_n_days, row_n_bench, hr, lo, hi, rel = row
            stats = (
                f"hit {hr:.2f} (CI {lo:.2f}-{hi:.2f}, n={row_n_bench})"
                if hr is not None
                else f"ungraded (n_days incl. neutral; n={row_n_days})"
            )
            tag = " reliable" if rel else ""
            print(f"{sig} {direction} {horizon}d: {stats}{tag}")
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, n_vint, n_bench


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="backtest",
        description="Point-in-time replay of composite's FRED regime signals"
        " (reads fred.db read-only; manual tool, not scheduled)",
    )
    p.add_argument("--db", default="backtest.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, n_vint, n_bench = run(a.db, a.db_dir, keep_days=a.keep_days)
    print(f"backtest snapshot {sid}: {n_vint} vintages, {n_bench} closes, into {a.db}")


__all__ = ["main", "run"]


if __name__ == "__main__":
    main()
