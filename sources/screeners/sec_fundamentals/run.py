import argparse
import sys
from datetime import date, datetime, timezone

from sources.screeners.sec_fundamentals import catalog, db, fetch


def _default_period(now_iso: str) -> str:
    """Most recent COMPLETED calendar quarter as 'CYyyyyQq' (no I suffix)."""
    d = date.fromisoformat(now_iso[:10])
    q = (d.month - 1) // 3 + 1 - 1        # previous quarter
    y = d.year
    if q == 0:
        q, y = 4, y - 1
    return f"CY{y}Q{q}"


def _period_for(concept, period: str) -> str:
    """Instant concepts take the trailing 'I'; durations do not."""
    return period + "I" if concept.kind == "instant" else period


def _current_quarter(now_iso: str) -> tuple[int, int]:
    """(year, quarter) that now_iso falls in — the bulk enumeration's upper
    bound (its ZIP is unpublished until the quarter closes, so it 404-skips)."""
    d = date.fromisoformat(now_iso[:10])
    return d.year, (d.month - 1) // 3 + 1


def _parse_quarter(s: str) -> tuple[int, int]:
    """'2023q4' | '2023Q4' | 'CY2023Q4' -> (2023, 4)."""
    y, q = s.upper().removeprefix("CY").split("Q")
    return int(y), int(q)


def _quarters(start: tuple[int, int], end: tuple[int, int]):
    """Inclusive (year, quarter) walk from start to end."""
    y, q = start
    while (y, q) <= end:
        yield y, q
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)


def _ingest_bulk(conn, fetch_bulk, tag_set, ticker_map, ciks_touched, now_iso,
                 bulk_start) -> int:
    """Backfill from the DERA quarterly ZIPs: enumerate {YYYY}q{Q} from
    bulk_start (default: the most recent completed quarter) through the current
    quarter, parse each into facts, and upsert them grouped by CIK. Unpublished
    quarters (404 -> None) and empty placeholders (parse_bulk -> []) are skipped.
    Company labels (name/sic) come from the ZIP's sub.tsv; ticker from the map.
    Returns the number of fact rows written. Skip-and-continue per quarter."""
    start = (_parse_quarter(bulk_start) if bulk_start
             else _parse_quarter(_default_period(now_iso)))
    fact_total = 0
    for year, quarter in _quarters(start, _current_quarter(now_iso)):
        try:
            blob = fetch_bulk(year, quarter)
        except Exception as e:
            conn.rollback()
            print(f"warning: skipping bulk {year}q{quarter}: "
                  f"{type(e).__name__}", file=sys.stderr)
            continue
        if blob is None:                       # unpublished (future) quarter
            continue
        rows = fetch.parse_bulk(blob, tag_set)
        by_cik: dict[int, list] = {}
        for r in rows:
            by_cik.setdefault(r["cik"], []).append(r)
        for cik, crows in by_cik.items():
            label = ticker_map.get(cik, {})
            first = crows[0]
            db.upsert_companies(conn, [{"cik": cik, "ticker": label.get("ticker"),
                "name": first.get("name") or label.get("title"),
                "sic": first.get("sic")}], now_iso)
            fact_total += db.write_facts(conn, cik, crows)
            ciks_touched.add(cik)
    return fact_total


def run(db_path, only=None, exclude=None, add=None, tickers=None, periods=None,
        bulk=False, bulk_start=None, keep_days=None,
        fetch_frame=fetch.fetch_frame, fetch_facts=fetch.fetch_company_facts,
        fetch_map=fetch.fetch_ticker_map, fetch_bulk=fetch.fetch_bulk,
        now_iso=None):
    """Pull curated XBRL concepts (frames cross-section + optional companyfacts
    watchlist depth) into the facts panel. Skip-and-continue; returns
    (snapshot_id, company_count, fact_count)."""
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    tags = catalog.select_ids([c.tag for c in catalog.CATALOG], only, exclude,
                              add=add)
    tag_set = set(tags)
    by_tag = {c.tag: c for c in catalog.CATALOG}
    concepts = [by_tag[t] for t in tags if t in by_tag]
    periods = periods or [_default_period(now_iso)]

    ticker_map = {}
    try:
        ticker_map = fetch_map()
    except Exception as e:  # non-fatal: unmapped CIKs get ticker=NULL
        print(f"warning: ticker map unavailable: {type(e).__name__}",
              file=sys.stderr)
    cik_by_ticker = {v["ticker"]: k for k, v in ticker_map.items()}

    conn = db.connect(db_path)
    ciks_touched, fact_total = set(), 0
    try:
        db.ensure_schema(conn)

        if bulk:
            # --- quarterly-ZIP backfill (alternate primary path) ---
            fact_total += _ingest_bulk(
                conn, fetch_bulk, tag_set, ticker_map, ciks_touched, now_iso,
                bulk_start)
        else:
            # --- frames cross-section (primary) ---
            for concept in concepts:
                for period in periods:
                    try:
                        rows = fetch_frame(concept.tag, concept.unit,
                                           _period_for(concept, period),
                                           concept.taxonomy)
                    except Exception as e:
                        conn.rollback()
                        print(f"warning: skipping frame {concept.tag}@{period}: "
                              f"{type(e).__name__}", file=sys.stderr)
                        continue
                    for r in rows:
                        cik = r.get("cik")
                        if cik is None:
                            continue
                        label = ticker_map.get(cik, {})
                        db.upsert_companies(conn, [{"cik": cik,
                            "ticker": label.get("ticker"),
                            "name": label.get("title"), "sic": None}], now_iso)
                        r = {**r, "tag": r.get("tag") or concept.tag,
                             "uom": r.get("uom") or concept.unit,
                             "form": r.get("form") or "FRAME"}
                        fact_total += db.write_facts(conn, cik, [r])
                        ciks_touched.add(cik)

            # --- companyfacts watchlist depth (optional) ---
            for sym in (tickers or []):
                cik = cik_by_ticker.get(sym)
                if cik is None:
                    print(f"warning: unmapped ticker {sym}", file=sys.stderr)
                    continue
                try:
                    payload = fetch_facts(cik)
                    rows = fetch.parse_company_facts(payload, tag_set)
                except Exception as e:
                    conn.rollback()
                    print(f"warning: skipping companyfacts {sym}: "
                          f"{type(e).__name__}", file=sys.stderr)
                    continue
                label = ticker_map.get(cik, {})
                name = payload.get("entityName") or label.get("title")
                db.upsert_companies(conn, [{"cik": cik, "ticker": sym,
                    "name": name, "sic": None}], now_iso)
                fact_total += db.write_facts(conn, cik, rows)
                ciks_touched.add(cik)

        company_count = len(ciks_touched)
        if company_count == 0 and fact_total == 0:
            print("warning: no fundamentals fetched (0 companies, 0 facts)",
                  file=sys.stderr)
        snapshot_id = db.write_snapshot(conn, now_iso, company_count, fact_total)
        if keep_days is not None:
            db.prune(conn, keep_days, now_iso)
    finally:
        conn.close()
    return snapshot_id, company_count, fact_total


def _split(v):
    return [s for s in (v.split(",") if v else []) if s.strip()] or None


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="fundamentals",
        description="Pull SEC XBRL company fundamentals into a SQLite panel")
    p.add_argument("--db", default="fundamentals.db")
    p.add_argument("--only", default=None, help="comma-separated concept tags")
    p.add_argument("--exclude", default=None, help="comma-separated tags to skip")
    p.add_argument("--add", action="append", default=None,
                   help="extra tag not in the catalog (repeatable)")
    p.add_argument("--tickers", default=None,
                   help="watchlist for companyfacts depth (comma-separated)")
    p.add_argument("--period", action="append", default=None,
                   help="calendar period(s) e.g. CY2024Q3 (repeatable)")
    p.add_argument("--bulk", action="store_true",
                   help="backfill from the quarterly ZIP instead of the APIs")
    p.add_argument("--start", default=None,
                   help="--bulk start quarter e.g. 2015q1 (default: latest "
                        "completed quarter)")
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, ncomp, nfact = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                          add=a.add, tickers=_split(a.tickers), periods=a.period,
                          bulk=a.bulk, bulk_start=a.start, keep_days=a.keep_days)
    print(f"stored {nfact} facts across {ncomp} companies into {a.db}")


if __name__ == "__main__":
    main()
