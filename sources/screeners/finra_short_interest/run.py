# finra_short_interest/run.py
import argparse
import sys
from datetime import UTC, datetime, timedelta
from datetime import date as date_cls

from sources.screeners.finra_short_interest import db, fetch

# On incremental re-runs, re-fetch this many trailing already-stored settlements
# so a FINRA repost/revision is re-absorbed by replace_settlement. --full
# re-ingests every settlement in range.
_REFETCH_SETTLEMENTS = 2
_DEFAULT_LOOKBACK_DAYS = 365  # ~12 months (~24 settlements)


def _last_day_of_month(year: int, month: int) -> date_cls:
    if month == 12:
        return date_cls(year, 12, 31)
    return date_cls(year, month + 1, 1) - timedelta(days=1)


def _roll_back_to_weekday(d: date_cls) -> date_cls:
    """FINRA settlement dates fall on business days; a nominal 15th / month-end
    landing on a weekend rolls back to the prior Friday. Holiday shifts are not
    modeled — a wrong guess simply 404s and is skipped (and, being unstored, is
    retried on every later run until it publishes)."""
    wd = d.weekday()  # Mon=0 .. Sun=6
    if wd == 5:  # Saturday -> Friday
        return d - timedelta(days=1)
    if wd == 6:  # Sunday -> Friday
        return d - timedelta(days=2)
    return d


def settlement_dates(start: str, end: str) -> list[str]:
    """The FINRA bi-monthly settlement schedule in [start, end] inclusive: the
    mid-month (15th) and month-end of every month, each rolled back to the prior
    weekday. Returns 'YYYY-MM-DD' strings, ascending and de-duplicated."""
    s = date_cls.fromisoformat(start)
    e = date_cls.fromisoformat(end)
    out: list[str] = []
    year, month = s.year, s.month
    while date_cls(year, month, 1) <= e:
        mid = _roll_back_to_weekday(date_cls(year, month, 15))
        eom = _roll_back_to_weekday(_last_day_of_month(year, month))
        for d in (mid, eom):
            if s <= d <= e:
                out.append(d.isoformat())
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return sorted(set(out))


def _default_start(now_dt, days: int = _DEFAULT_LOOKBACK_DAYS) -> str:
    """'YYYY-MM-DD' for `days` before now_dt's date."""
    return (now_dt.date() - timedelta(days=days)).isoformat()


def run(
    db_path,
    start=None,
    keep_days=None,
    full=False,
    fetch_settlement=fetch.fetch_settlement,
    now_iso=None,
) -> tuple[int, int, int]:
    """Ingest FINRA bi-monthly short-interest files into SQLite. Enumerate
    settlement dates from `start` (default: ~12 months back) through today;
    ingest new settlements and re-fetch the trailing _REFETCH_SETTLEMENTS
    already-stored ones (all of them when full=True). A 403/404 (absent /
    not-yet-published settlement) is skipped. Any per-settlement failure rolls
    back and continues. Returns (snapshot_id, settlement_count, row_count)."""
    now_iso = now_iso or datetime.now(UTC).isoformat()
    now_dt = datetime.fromisoformat(now_iso)
    start = start or _default_start(now_dt)
    end_date = now_dt.date().isoformat()
    all_settlements = settlement_dates(start, end_date)

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        stored = db.stored_settlements(conn)
        stored_set = set(stored)
        refetch = set(stored[-_REFETCH_SETTLEMENTS:])  # newest stored settlements

        settlement_count = 0
        total_rows = 0
        for s in all_settlements:
            if not full and s in stored_set and s not in refetch:
                continue
            try:
                rows = fetch_settlement(s)
                if rows is None:  # 403/404 -> absent/unpublished
                    continue
                db.upsert_securities(conn, rows)
                written = db.replace_settlement(conn, s, rows)
                db.record_settlement(conn, s, now_iso, written)
                total_rows += written
                settlement_count += 1
            except Exception as e:  # skip-and-continue on any per-settlement failure
                # Roll back this settlement's uncommitted writes, then log ONLY
                # the exception class — never str(e)/e.url.
                conn.rollback()
                print(f"warning: skipping {s}: {type(e).__name__}", file=sys.stderr)
                continue

        snapshot_id = db.write_snapshot(conn, now_iso, settlement_count, total_rows)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, settlement_count, total_rows


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="short_interest", description="Pull FINRA bi-monthly equity short interest into SQLite"
    )
    p.add_argument("--db", default="short_interest.db")
    p.add_argument(
        "--start",
        default=None,
        help="earliest settlement date YYYY-MM-DD "
        "(default: ~12 months back; listed coverage starts "
        "2021-06, earlier is OTC-only)",
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="re-ingest every settlement in range, ignoring the incremental skip",
    )
    p.add_argument(
        "--keep-days",
        type=int,
        default=None,
        help="prune snapshot provenance older than N days (never touches short-interest history)",
    )
    a = p.parse_args(argv)
    _, sc, rc = run(a.db, start=a.start, keep_days=a.keep_days, full=a.full)
    print(f"stored {rc} short-interest rows across {sc} settlements into {a.db}")


if __name__ == "__main__":
    main()
