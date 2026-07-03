import argparse
import sys
from datetime import datetime, timezone

from cboe_options import catalog, db, fetch


def _split(arg):
    """'A,B , C' -> ['A','B','C']; None/'' -> None."""
    if not arg:
        return None
    return [t.strip() for t in arg.split(",") if t.strip()]


def run(db_path, symbols=None, keep_days=None, now_iso=None,
        fetch_chain=fetch.fetch_chain) -> tuple[int, int, int]:
    """Snapshot each symbol's CBOE option chain into SQLite. For each symbol:
    fetch the chain (None -> skip), parse contracts + daily rollup, and
    replace-write them under the payload's session date. Any per-symbol failure
    rolls back and continues (logging only the exception class). Always writes a
    run-header snapshot. Returns (snapshot_id, symbol_count, row_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    if symbols is None:
        symbols = [u.symbol for u in catalog.CATALOG]

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        ok_count = 0
        total_rows = 0
        for symbol in symbols:
            try:
                is_index = catalog.index_flag(symbol)
                payload = fetch_chain(symbol, is_index)
                if payload is None:               # no chain for this ticker
                    continue
                daily, contracts = fetch.parse_chain(payload, symbol)
                snapshot_date = fetch.session_date(payload) or now_iso[:10]
                db.upsert_underlying(conn, symbol, is_index, snapshot_date)
                written = db.replace_day(conn, snapshot_date, symbol,
                                         contracts, now_iso)
                db.upsert_underlying_daily(conn, snapshot_date, daily)
                db.record_day(conn, snapshot_date, symbol, now_iso, written)
                total_rows += written
                ok_count += 1
            except Exception as e:  # skip-and-continue on any per-symbol failure
                conn.rollback()
                print(f"warning: skipping {symbol}: {type(e).__name__}",
                      file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, ok_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, ok_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="options",
        description="Pull CBOE delayed-quote option chains into SQLite")
    p.add_argument("--db", default="cboe_options.db")
    p.add_argument("--only", default=None,
                   help="comma-separated symbols to fetch (default: catalog)")
    p.add_argument("--exclude", default=None,
                   help="comma-separated symbols to skip")
    p.add_argument("--add", default=None,
                   help="comma-separated extra symbols to append")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days "
                        "(never touches option history)")
    a = p.parse_args(argv)
    all_syms = [u.symbol for u in catalog.CATALOG]
    symbols = catalog.select_symbols(all_syms, _split(a.only), _split(a.exclude),
                                     _split(a.add))
    _, sc, rc = run(a.db, symbols=symbols, keep_days=a.keep_days)
    print(f"stored {rc} option rows across {sc} symbols into {a.db}")


if __name__ == "__main__":
    main()
