import argparse
from datetime import datetime, timezone

import sources.common.monitor_common as monitor_common
from sources.monitors.market_calendar import catalog, compute, db, fetch

_NYSE_URL = "https://www.nyse.com/trade/hours-calendars"
_SIFMA_URL = "https://www.sifma.org/resources/guides-playbooks/holiday-schedule"


def _rows(mapping, event_type, source, event_time=None):
    """Build events rows from a {date: label-or-time} seed mapping."""
    return [{"event_type": event_type, "event_date": d,
             "event_time": event_time, "subtype": "", "title": _title(label),
             "status": "scheduled", "source": source, "payload": None}
            for d, label in mapping.items()]


def _title(label):
    return label if isinstance(label, str) and not label[:1].isdigit() else None


def run(db_path, years=2, horizon_days=7, keep_days=None, refresh=False,
        pages=None, now_iso=None):
    """Seed holidays/early closes + compute OPEX/quad-witching into the events
    calendar; write each event_type via replace_forward_window so stale future
    rows disappear. Deterministic and network-free unless refresh/pages given.
    Returns (snapshot_id, event_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    today = datetime.fromisoformat(now_iso).date().isoformat()
    start_year = int(today[:4])

    eq_hol = dict(catalog.EQUITY_HOLIDAYS)
    eq_early = dict(catalog.EQUITY_EARLY_CLOSES)
    bond_hol = dict(catalog.BOND_HOLIDAYS)
    bond_early = dict(catalog.BOND_EARLY_CLOSES)

    if refresh or pages is not None:
        pages = pages or {"nyse": fetch.fetch_page(_NYSE_URL),
                          "sifma": fetch.fetch_page(_SIFMA_URL)}
        if pages.get("nyse"):
            eq_hol.update(fetch.parse_nyse_calendar(pages["nyse"]))  # raises on drift
        if pages.get("sifma"):
            bond_hol.update(fetch.parse_sifma_calendar(pages["sifma"]))

    holiday_set = set(eq_hol) | set(bond_hol)
    opex = []
    for year in range(start_year, start_year + years):
        for iso, kind in compute.opex_dates(year, holiday_set):
            opex.append({"event_type": kind, "event_date": iso,
                         "event_time": "16:00", "subtype": "",
                         "title": _opex_title(iso, kind), "status": "scheduled",
                         "source": "computed", "payload": None})

    by_type = {
        "market_holiday": _rows(eq_hol, "market_holiday", "nyse"),
        "early_close": _rows(eq_early, "early_close", "nyse", "13:00"),
        "bond_holiday": _rows(bond_hol, "bond_holiday", "sifma"),
        "bond_early_close": _rows(bond_early, "bond_early_close", "sifma", "14:00"),
        "opex": [r for r in opex if r["event_type"] == "opex"],
        "quad_witching": [r for r in opex if r["event_type"] == "quad_witching"],
    }

    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)
        monitor_common.set_today(conn, now_iso, horizon_days)
        for event_type, rows in by_type.items():
            monitor_common.replace_forward_window(conn, event_type, today, rows,
                                                  now_iso)
        count = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_date >= ?", (today,)
        ).fetchone()[0]
        snapshot_id = monitor_common.write_snapshot(conn, now_iso, count,
                                                    "market_calendar")
        if keep_days is not None:
            monitor_common.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, count


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _opex_title(iso, kind):
    month = _MONTHS[int(iso[5:7]) - 1]
    return (f"{month} Quad Witching" if kind == "quad_witching"
            else f"{month} Monthly OPEX")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="market_calendar",
        description="Seed U.S. market holidays/early closes + compute OPEX into SQLite")
    p.add_argument("--db", default="market_calendar.db")
    p.add_argument("--years", type=int, default=2,
                   help="years of OPEX/quad-witching to compute forward")
    p.add_argument("--horizon-days", type=int, default=7,
                   help="imminence window for v_imminent")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune run-provenance snapshots older than N days")
    p.add_argument("--refresh", action="store_true",
                   help="opt-in: refresh the seed from the live NYSE/SIFMA pages")
    a = p.parse_args(argv)
    _, count = run(a.db, years=a.years, horizon_days=a.horizon_days,
                   keep_days=a.keep_days, refresh=a.refresh)
    print(f"stored {count} forward market-calendar events into {a.db}")


if __name__ == "__main__":
    main()
