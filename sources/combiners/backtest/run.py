"""Point-in-time replay: copy vintage + benchmark rows out of fred.db, let
the views grade what composite's FRED regime signals would have said each
historical day. The 4th combiner — scheduled weekly (Sat, after
fred-vintages), not nightly, because its only inputs (ALFRED vintages +
SP500 closes) refresh weekly there (see docs/SCHEDULE.md)."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.backtest import catalog, db, fetch, mcpt


def run(
    db_path,
    db_dir="data",
    now_iso=None,
    keep_days=None,
    harvest_vintages=fetch.harvest_vintages,
    harvest_benchmark=fetch.harvest_benchmark,
    harvest_market_obs=fetch.harvest_market_obs,
    harvest_price_ledger=fetch.harvest_price_ledger,
    n_perms=1000,
    seed=0,
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
                # dict.fromkeys: the two DFF signals share one series
                series = list(dict.fromkeys(s["series_id"] for s in catalog.REPLAY_SIGNALS))
                n_vint = db.insert_vintages(conn, harvest_vintages(conn, series))
                n_bench = db.insert_benchmark(
                    conn,
                    catalog.BENCHMARK_SERIES,
                    harvest_benchmark(conn, catalog.BENCHMARK_SERIES),
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

        # Asset-class proxy benchmarks (e.g. XLE) from scorer.db's price
        # ledger, grouped by source DB. Same skip-and-continue discipline; a
        # missing/young ledger just means thin asset-class coverage, not a
        # crash. Counted into n_bench alongside SP500.
        by_bench_db: dict[str, list] = {}
        for b in catalog.CLASS_BENCHMARKS:
            by_bench_db.setdefault(b["db"], []).append(b)
        for db_name, benches in by_bench_db.items():
            try:
                fetch.attach_ro(conn, os.path.join(db_dir, db_name))
            except Exception as e:
                failures += 1
                print(f"skip {db_name}: {type(e).__name__}")
                continue
            try:
                got = 0
                for b in benches:
                    got += db.insert_benchmark(
                        conn, b["symbol"], harvest_price_ledger(conn, b["symbol"])
                    )
                conn.commit()
                n_bench += got
            except Exception as e:
                failures += 1
                conn.rollback()
                print(f"skip {db_name}: {type(e).__name__}")
            finally:
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
                        conn,
                        s["signal_id"],
                        harvest_market_obs(conn, s["harvest_sql"]),
                        s.get("publication_lag_days", 0),
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
        # Permutation null (mcpt.py): flags fixed, spine shuffled, seeded —
        # the p that prices the overlap the Wilson interval cannot, plus the
        # one family row that prices multiplicity. n_perms=0 skips (leaves
        # any prior pass in place, distinguishable via captured_at).
        # Skip-and-continue on failure like every other per-item block, and
        # CLEAR the table: a raise must never leave last week's p-values
        # silently joined to this week's fresh flags — that staleness is the
        # exact failure the population guard exists to prevent.
        if n_perms:
            try:
                null_rows = mcpt.permutation_null(conn, n_perms, seed)
                db.write_replay_null(conn, null_rows, now_iso)
                conn.commit()
            except Exception as e:
                # snapshot header is already final here; the print is the record
                conn.rollback()
                db.write_replay_null(conn, [], now_iso)
                conn.commit()
                print(f"skip permutation pass: {type(e).__name__}")
            else:
                family = next((r for r in null_rows if (r[0], r[1], r[2]) == mcpt.FAMILY_KEY), None)
                if family:
                    print(
                        f"-- permutation null: {len(null_rows) - 1} cells @ {n_perms} perms"
                        f" (seed {seed}); family max-statistic p = {family[4]:.3f} —"
                        " the multiplicity answer for the whole scoreboard, but"
                        " un-studentized: a large value means the MAX is unremarkable,"
                        " never 'no cell survives'. Per-cell perm_p is one-sided"
                        " (favorable tail): near 0 = hard to match by shuffling, near"
                        " 1 = no better than any shuffle (ties included — not itself"
                        " evidence of anti-prediction). Vol-keyed cells (cboe_vix*)"
                        " read an optimistic null (shuffling destroys vol clustering)."
                    )
        # Print `excess` beside `hit`: a bare hit rate is unreadable against a
        # benchmark that drifts up 61-68% of the time. `reliable` is a
        # sample-size floor, NOT evidence the signal works — `beats baseline`
        # is the honest (still weak) claim, and `anti_signal` its
        # significantly-wrong mirror; both count toward the noise budget.
        graded, flagged = conn.execute(
            "SELECT COUNT(*),"
            " COALESCE(SUM(beats_baseline), 0) + COALESCE(SUM(anti_signal), 0)"
            " FROM v_replay_efficacy WHERE direction != 'neutral' AND n_bench > 0"
        ).fetchone()
        expected_noise = graded * 0.05
        print(
            f"-- {graded} graded rows, {flagged} flagged. n counts OBSERVATIONS"
            " (reports), not forward-filled days. Flags are NOMINAL 95%,"
            f" uncorrected: ~{expected_noise:.0f} are expected by chance."
            " Overlapping forward windows from consecutive reports make even the"
            " observation count optimistic. Trust nothing on a lone flag."
        )
        for row in conn.execute(
            "SELECT signal_id, direction, horizon, n_obs, n_days, n_bench, hit_rate,"
            " hit_ci_lo, hit_ci_hi, reliable, baseline, excess, beats_baseline,"
            " anti_signal, perm_p"
            " FROM v_replay_efficacy ORDER BY signal_id, direction, horizon"
        ):
            (
                sig,
                direction,
                horizon,
                n_obs,
                row_n_days,
                row_n_bench,
                hr,
                lo,
                hi,
                rel,
                base,
                exc,
                beats,
                anti,
                perm_p,
            ) = row
            if hr is None:
                stats = f"ungraded (n_obs incl. neutral; n_obs={n_obs})"
            else:
                # n is OBSERVATIONS (reports), not forward-filled days.
                stats = (
                    f"hit {hr:.2f} vs base {base:.2f} -> excess {exc:+.3f}"
                    f" (CI {lo:.2f}-{hi:.2f}, n={row_n_bench} obs / {row_n_days} days)"
                )
            if perm_p is not None:
                stats += f" perm_p={perm_p:.3f}"
            tag = " reliable" if rel else ""
            if beats:
                tag += " beats baseline"
            if anti:
                tag += " ANTI-SIGNAL"
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
    p.add_argument(
        "--perms",
        type=int,
        default=1000,
        help="permutation-null resamples (0 skips the pass, keeping the prior one)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=0,
        help="RNG seed for the permutation pass (fixed default: determinism invariant)",
    )
    a = p.parse_args(argv)
    sid, n_vint, n_bench = run(a.db, a.db_dir, keep_days=a.keep_days, n_perms=a.perms, seed=a.seed)
    print(f"backtest snapshot {sid}: {n_vint} vintages, {n_bench} closes, into {a.db}")


__all__ = ["main", "run"]


if __name__ == "__main__":
    main()
