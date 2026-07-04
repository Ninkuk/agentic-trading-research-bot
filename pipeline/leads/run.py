import argparse
import sys
from datetime import datetime, timezone

from pipeline.common import pipeline_common
from pipeline.leads import db, extract

LEGS = ("cot", "quality", "regime")


def _run_leg(conn, snapshot_id, leg_name, sources, connect_ro, work):
    """Open the leg's source DBs read-only, record their provenance, run
    work(*source_conns). Skip-and-continue: on any failure roll back and
    print ONLY the exception class (never str(e) — secret hygiene)."""
    opened = []
    try:
        for source, path in sources:
            opened.append((source, path, connect_ro(path)))
        db.write_source_state(conn, snapshot_id, [
            extract.read_source_state(src, source, path)
            for source, path, src in opened])
        work(*[src for _s, _p, src in opened])
    except Exception as e:
        conn.rollback()
        print(f"warning: skipping {leg_name} leg: {type(e).__name__}",
              file=sys.stderr)
    finally:
        for _s, _p, src in opened:
            src.close()


def run(db_path, cftc_db="cftc.db", fred_db="fred.db",
        fundamentals_db="sec_fundamentals.db", stocks_db="stocks.db",
        only=None, keep_days=None, connect_ro=pipeline_common.connect_ro,
        now_iso=None):
    """Funnel per-source signals into leads.db (read-only on every source).
    Returns (snapshot_id, lead_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    legs = [leg for leg in LEGS if only is None or leg in only]

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        snapshot_id = db.write_snapshot(conn, now_iso)

        if "cot" in legs:
            def cot_work(cftc_conn):
                n = db.write_leads(conn, snapshot_id,
                                   extract.extract_cot_extremes(cftc_conn))
                print(f"cot: {n} leads")
            _run_leg(conn, snapshot_id, "cot", [("cftc", cftc_db)],
                     connect_ro, cot_work)

        if "quality" in legs:
            def quality_work(fund_conn, stocks_conn):
                leads, dropped = extract.extract_quality(fund_conn, stocks_conn)
                n = db.write_leads(conn, snapshot_id, leads)
                print(f"quality: {n} leads "
                      f"({dropped} names dropped with <2 dimensions)")
            _run_leg(conn, snapshot_id, "quality",
                     [("fundamentals", fundamentals_db), ("stocks", stocks_db)],
                     connect_ro, quality_work)

        if "regime" in legs:
            def regime_work(fred_conn):
                db.write_regime(conn, snapshot_id,
                                extract.extract_regime(fred_conn))
            _run_leg(conn, snapshot_id, "regime", [("fred", fred_db)],
                     connect_ro, regime_work)

        lead_count = db.finalize_snapshot(conn, snapshot_id)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, lead_count


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="leads",
        description="Funnel per-source signals into ranked, tagged leads")
    p.add_argument("--db", default="leads.db")
    p.add_argument("--cftc-db", default="cftc.db")
    p.add_argument("--fred-db", default="fred.db")
    p.add_argument("--fundamentals-db", default="sec_fundamentals.db")
    p.add_argument("--stocks-db", default="stocks.db")
    p.add_argument("--only", default=None,
                   help=f"comma-separated legs to run "
                        f"(default: {','.join(LEGS)})")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    only = a.only.split(",") if a.only else None
    snapshot_id, lead_count = run(
        a.db, cftc_db=a.cftc_db, fred_db=a.fred_db,
        fundamentals_db=a.fundamentals_db, stocks_db=a.stocks_db,
        only=only, keep_days=a.keep_days)
    print(f"wrote {lead_count} leads into {a.db} (snapshot {snapshot_id})")


if __name__ == "__main__":
    main()
