import argparse
import dataclasses
import os
import sys
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.promote import catalog, db, extract, gates


def _resolve_equity(equity):
    """--equity flag, else PIPELINE_EQUITY env (the Stage 5 scheduler's path).
    Missing both is a hard error BEFORE any DB write."""
    if equity is not None:
        return float(equity)
    env = os.environ.get("PIPELINE_EQUITY")
    if env:
        return float(env)
    raise ValueError("no equity: pass --equity or set PIPELINE_EQUITY")


def _load_liquidity(connect_ro, path, required, label):
    try:
        src = connect_ro(path)
    except Exception as e:
        print(f"warning: {label} unavailable: {type(e).__name__}",
              file=sys.stderr)
        return {}
    try:
        extract.check_required_columns(src, required, label)
        return extract.load_liquidity(src, required)
    finally:
        src.close()


def run(db_path, leads_db="leads.db", stocks_db="stocks.db",
        etfs_db="etfs.db", equity=None, allow_short=False, keep_days=None,
        config=catalog.DEFAULT_CONFIG,
        connect_ro=pipeline_common.connect_ro, now_iso=None):
    """Promote the latest leads through G1..G6 + sizing into candidates.db.
    Returns (snapshot_id, candidate_count, rejection_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    equity = _resolve_equity(equity)
    cfg = dataclasses.replace(config, allow_short=allow_short) \
        if allow_short != config.allow_short else config

    try:
        leads_conn = connect_ro(leads_db)
    except Exception as e:
        print(f"warning: leads db unavailable: {type(e).__name__}",
              file=sys.stderr)
        raise ValueError("leads db unavailable") from None
    try:
        cohort = extract.load_latest_leads(leads_conn)
    finally:
        leads_conn.close()

    liquidity = {
        "stock": _load_liquidity(connect_ro, stocks_db,
                                 catalog.REQUIRED_STOCK_POINTS, "stocks db"),
        "etf": _load_liquidity(connect_ro, etfs_db,
                               catalog.REQUIRED_ETF_POINTS, "etfs db"),
    }

    rejections = []
    groups, rej = gates.group_leads(cohort["leads"])          # G1
    rejections += rej
    groups, rej = gates.gate_direction(groups, cfg.allow_short)  # G2
    rejections += rej
    groups, rej = gates.gate_liquidity(groups, liquidity, cfg)   # G3
    rejections += rej
    groups, rej = gates.gate_confluence(groups, cfg)             # G4
    rejections += rej
    groups, rej = gates.gate_sector_cap(groups, cfg)             # G5
    rejections += rej
    groups, rej = gates.gate_max_positions(groups, cfg)          # G6
    rejections += rej

    candidates = []
    for g in groups:
        cand, rej_row = gates.size_candidate(
            g, equity, cohort["regime_scalar"], cfg)
        if cand is None:
            rejections.append(rej_row)
        else:
            candidates.append(cand)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso, equity,
                                cohort["regime_scalar"],
                                cohort["leads_snapshot_id"],
                                catalog.config_hash(cfg))
        db.write_candidates(conn, sid, candidates)
        db.write_rejections(conn, sid, rejections)
        cc, rc = db.finalize_snapshot(conn, sid)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    print(f"promoted {cc} candidates ({rc} rejections) into {db_path}")
    return sid, cc, rc


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="promote",
        description="Deterministic promotion gates: leads -> candidates")
    p.add_argument("--db", default="candidates.db")
    p.add_argument("--leads-db", default="leads.db")
    p.add_argument("--stocks-db", default="stocks.db")
    p.add_argument("--etfs-db", default="etfs.db")
    p.add_argument("--equity", type=float, default=None,
                   help="account equity (default: PIPELINE_EQUITY env)")
    p.add_argument("--allow-short", action="store_true")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    run(a.db, leads_db=a.leads_db, stocks_db=a.stocks_db, etfs_db=a.etfs_db,
        equity=a.equity, allow_short=a.allow_short, keep_days=a.keep_days)


if __name__ == "__main__":
    main()
