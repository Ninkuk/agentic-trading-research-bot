"""Ingest one combined account/positions JSON document into portfolio.db.

Invoked by the `account-positions` Claude command (see
.claude/skills/account-positions/), which fetches live state via the
Robinhood MCP and writes it to a file — whatever Claude learns enters the
system as data through this dispatcher, never as live calls. Secret hygiene:
errors print exception type names only (an MCP payload could embed account
identifiers in a message)."""
import argparse
import json
import sys
from datetime import datetime, timezone

from sources.screeners.portfolio_screener import db, fetch


def run(db_path: str, doc, now_iso=None, keep_days=None) -> tuple:
    """Parse + store one snapshot. Returns (snapshot_id, position_count,
    skipped_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    account, positions, skipped = fetch.parse_snapshot(doc)
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        sid = db.write_snapshot(conn, now_iso, account, positions)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return sid, len(positions), skipped


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="portfolio",
        description="Snapshot account positions/details into portfolio.db")
    p.add_argument("--db", default="portfolio.db")
    p.add_argument("--input", required=True,
                   help="path to the combined JSON document, or - for stdin")
    p.add_argument("--keep-days", type=int, default=None)
    a = p.parse_args(argv)

    try:
        if a.input == "-":
            doc = json.load(sys.stdin)
        else:
            with open(a.input, encoding="utf-8") as f:
                doc = json.load(f)
    except Exception as e:
        print(f"error: cannot read input: {type(e).__name__}",
              file=sys.stderr)
        raise SystemExit(1) from None

    try:
        sid, n_pos, skipped = run(a.db, doc, keep_days=a.keep_days)
    except ValueError as e:
        print(f"error: bad document: {type(e).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
    suffix = f" ({skipped} skipped)" if skipped else ""
    print(f"portfolio snapshot {sid}: {n_pos} positions{suffix} into {a.db}")


if __name__ == "__main__":
    main()
