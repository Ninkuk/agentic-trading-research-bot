import argparse
import json
import sys
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.trials import catalog, db, evaluate, stats


def run_register(db_path, stage, description, params_json,
                 family=catalog.DEFAULT_FAMILY, now_iso=None, git_rev=None):
    """Register (or fetch) a trial. The workflow discipline: register BEFORE
    running the variant, so the DSR's N never undercounts."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    params = json.loads(params_json)   # invalid JSON raises ValueError
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        trial_id, created = db.register_trial(
            conn, stage, description, params, now_iso,
            family=family, git_rev=git_rev)
        db.write_snapshot(conn, now_iso)
    finally:
        conn.close()
    return trial_id, created


def _open_ro(connect_ro, path, label):
    try:
        return connect_ro(path)
    except Exception as e:
        print(f"warning: {label} unavailable: {type(e).__name__}",
              file=sys.stderr)
        return None


def run_evaluate(db_path, trial_id, leads_db, stocks_db, etfs_db, calendar_db,
                 entry_lag=catalog.DEFAULT_ENTRY_LAG,
                 connect_ro=pipeline_common.connect_ro, now_iso=None):
    """Walk-forward evaluate one trial. Returns the result dict written to
    trial_results, or None (unknown trial / no calendar)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    conn = db.connect(db_path)
    opened = []
    try:
        db.ensure_schema(conn)
        trial = db.trial_row(conn, trial_id)
        if trial is None:
            print(f"error: no such trial: {trial_id}", file=sys.stderr)
            return None
        cal = _open_ro(connect_ro, calendar_db, "calendar db")
        if cal is None:
            return None                 # trading days are non-negotiable
        opened.append(cal)
        leads_conn = _open_ro(connect_ro, leads_db, "leads db")
        if leads_conn is None:
            return None
        opened.append(leads_conn)

        histories = {}
        for kind, path, label in (("stock", stocks_db, "stocks db"),
                                  ("etf", etfs_db, "etfs db")):
            src = _open_ro(connect_ro, path, label)
            if src is None:
                histories[kind] = None
                continue
            opened.append(src)
            evaluate.check_required_columns(src, label)
            histories[kind] = evaluate.load_price_history(src)

        cohort = evaluate.evaluate_cohort(
            leads_conn, histories["stock"], histories["etf"], cal,
            entry_lag=entry_lag)
        rets = cohort["returns"]

        sr = stats.sharpe(rets) if rets else None
        skew = stats.skewness(rets) if rets else None
        kurt = stats.kurtosis_raw(rets) if rets else None
        family = trial["family"]
        n_family = db.family_size(conn, family)
        sd_sr = stats.sample_stdev(db.family_latest_sharpes(conn, family))
        dsr = stats.deflated_sharpe(sr, len(rets), skew, kurt,
                                    n_family, sd_sr)
        if dsr is None:
            print("dsr: not computable (family N < 2 or sd_SR = 0)",
                  file=sys.stderr)

        result = {
            "evaluated_at": now_iso,
            "window_start": cohort["window_start"],
            "window_end": cohort["window_end"],
            "n_obs": len(rets),
            "sharpe": sr, "skew": skew, "kurtosis": kurt,
            "hit_rate": (sum(1 for r in rets if r > 0) / len(rets)
                         if rets else None),
            "avg_return": stats.mean(rets) if rets else None,
            "max_drawdown": stats.max_drawdown(rets) if rets else None,
            "dsr_at_eval": dsr, "n_at_eval": n_family,
            "detail": json.dumps(
                {"max_gap_days": cohort["max_gap_days"],
                 "skipped": cohort["skipped"], "scored": cohort["scored"],
                 "truncated": cohort["truncated"],
                 "entry_lag": entry_lag,
                 "haircut": catalog.TRANSACTION_HAIRCUT},
                separators=(",", ":")),
        }
        db.write_result(conn, trial_id, result)
        db.write_snapshot(conn, now_iso)
        print(f"trial {trial_id}: n_obs={result['n_obs']} "
              f"sharpe={result['sharpe']} dsr={result['dsr_at_eval']} "
              f"(family {family}, N={n_family})")
        return result
    finally:
        for c in opened:
            c.close()
        conn.close()


def run_leaderboard(db_path, family=None) -> list:
    """Family leaderboard with LIVE DSR (vs the family's CURRENT N) appended
    in Python — stored dsr_at_eval values go stale as the family grows."""
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        where, params = ("WHERE family = ?", (family,)) if family else ("", ())
        rows = conn.execute(
            f"SELECT family, n_trials, best_sharpe, evaluated_trials "
            f"FROM v_family_leaderboard {where} ORDER BY family",
            params).fetchall()
        out = []
        for fam, n_trials, best_sr, evaluated in rows:
            sharpes = db.family_latest_sharpes(conn, fam)
            sd_sr = stats.sample_stdev(sharpes)
            best = conn.execute(
                """SELECT l.sharpe, l.n_obs, l.skew, l.kurtosis
                   FROM v_latest_results l JOIN trials t
                     ON t.trial_id = l.trial_id
                   WHERE t.family=? AND l.sharpe IS NOT NULL
                   ORDER BY l.sharpe DESC LIMIT 1""", (fam,)).fetchone()
            dsr_live = None
            if best is not None:
                dsr_live = stats.deflated_sharpe(
                    best[0], best[1] or 0, best[2], best[3], n_trials, sd_sr)
            out.append({"family": fam, "n_trials": n_trials,
                        "best_sharpe": best_sr,
                        "evaluated_trials": evaluated, "dsr_live": dsr_live})
        return out
    finally:
        conn.close()


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="trials",
        description="Trial registry + DSR + walk-forward evaluation")
    p.add_argument("--db", default="trials.db")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--register", action="store_true")
    mode.add_argument("--evaluate", type=int, metavar="TRIAL_ID")
    mode.add_argument("--leaderboard", action="store_true")
    p.add_argument("--stage", default=None)
    p.add_argument("--description", default=None)
    p.add_argument("--params", default=None, help="JSON of every knob")
    p.add_argument("--family", default=None)
    p.add_argument("--leads-db", default="leads.db")
    p.add_argument("--stocks-db", default="stocks.db")
    p.add_argument("--etfs-db", default="etfs.db")
    p.add_argument("--calendar-db", default="market_calendar.db")
    p.add_argument("--entry-lag", type=int, default=catalog.DEFAULT_ENTRY_LAG)
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)

    if a.register:
        if not (a.stage and a.description and a.params):
            p.error("--register needs --stage, --description, --params")
        trial_id, created = run_register(
            a.db, a.stage, a.description, a.params,
            family=a.family or catalog.DEFAULT_FAMILY)
        print(f"trial {trial_id} {'registered' if created else 'already registered'}")
    elif a.evaluate is not None:
        run_evaluate(a.db, a.evaluate, leads_db=a.leads_db,
                     stocks_db=a.stocks_db, etfs_db=a.etfs_db,
                     calendar_db=a.calendar_db, entry_lag=a.entry_lag)
    else:
        for row in run_leaderboard(a.db, family=a.family):
            print(json.dumps(row, separators=(",", ":")))

    if a.keep_days is not None:
        conn = db.connect(a.db)
        try:
            from datetime import datetime as _dt, timezone as _tz
            db.prune(conn, a.keep_days, _dt.now(_tz.utc).isoformat())
        finally:
            conn.close()


if __name__ == "__main__":
    main()
