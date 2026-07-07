"""Nightly sizing/risk advice: joins the composite scorecard against real
holdings (book heat, disagreements, size caps). Sources attached read-only
one at a time; the advisor writes only advisor.db — decision support,
never order generation."""

import argparse
import os
from datetime import UTC, datetime

from sources.combiners.advisor import catalog, db, fetch


def run(db_path, db_dir, now_iso=None, keep_days=None):
    now_iso = now_iso or datetime.now(UTC).isoformat()
    today = now_iso[:10]  # one-clock rule: all staleness is judged on this
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso)
        composite = None
        account = None
        scorecard: dict = {}
        flag_signals: dict = {}
        flagged: list = []
        positions: list = []
        metrics: dict = {}
        reliable: set = set()

        failures = 0

        def read_source(db_name, reader):
            """Attach one source read-only, run reader(), skip-and-continue
            printing only the exception type (secret hygiene). Failures are
            counted into the header so a partial night is visible."""
            nonlocal failures
            path = os.path.join(db_dir, db_name)
            try:
                fetch.attach_ro(conn, path)
            except Exception as e:
                failures += 1
                print(f"skip {db_name}: {type(e).__name__}")
                return
            try:
                reader()
            except Exception as e:
                failures += 1
                conn.rollback()
                print(f"skip {db_name}: {type(e).__name__}")
            finally:
                fetch.detach(conn)

        # Readers assign their nonlocals only after EVERY read in the source
        # succeeds — a failure mid-source must not apply half a source (real
        # equity + zero positions would masquerade as an empty book).
        def read_composite():
            nonlocal composite, scorecard, flagged, flag_signals
            header = fetch.read_composite_header(conn)
            cards = fetch.read_scorecard(conn)
            flags = fetch.read_flagged(conn)
            sigs = fetch.read_flag_signals(conn)
            composite, scorecard, flagged, flag_signals = header, cards, flags, sigs

        def read_portfolio():
            nonlocal account, positions
            acct = fetch.read_account(conn)
            pos = fetch.read_positions(conn)
            account, positions = acct, pos

        def read_prices():
            for sym, m in fetch.read_metrics(conn, symbols).items():
                metrics.setdefault(sym, m)  # first DB (stocks) wins

        def read_scorer():
            nonlocal reliable
            reliable = fetch.read_reliable_signals(conn)

        read_source(catalog.COMPOSITE_DB, read_composite)
        read_source(catalog.PORTFOLIO_DB, read_portfolio)
        symbols = {p["symbol"] for p in positions} | set(flagged)
        if symbols:
            for price_db in catalog.PRICE_DBS:
                read_source(price_db, read_prices)
        read_source(catalog.SCORER_DB, read_scorer)

        equity = account["equity"] if account else None
        buying_power = account["buying_power"] if account else None
        heat_rows = db.build_position_heat(
            positions,
            scorecard,
            metrics,
            equity,
            today,
            catalog.TICKER_GROUP,
            catalog.ATR_MAX_AGE_DAYS,
        )
        cap_rows = db.build_size_caps(
            flagged,
            scorecard,
            metrics,
            heat_rows,
            equity,
            buying_power,
            catalog.RISK_BUDGET,
            catalog.TICKER_GROUP,
            flag_signals,
            reliable,
        )
        db.write_position_heat(conn, sid, heat_rows)
        db.write_size_caps(conn, sid, cap_rows)
        db.finish_snapshot(conn, sid, account, composite, failures)
        conn.commit()
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, len(heat_rows), len(cap_rows)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="advisor",
        description="Sizing/risk advice: book heat, disagreements, size caps"
        " (reads composite/portfolio/stocks/etfs/scorer read-only)",
    )
    p.add_argument("--db", default="advisor.db")
    p.add_argument("--db-dir", default="data")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)
    sid, n_heat, n_caps = run(a.db, a.db_dir, keep_days=a.keep_days)
    print(f"advisor snapshot {sid}: {n_heat} positions, {n_caps} caps, into {a.db}")


if __name__ == "__main__":
    main()
