import argparse
import sys
from datetime import date, datetime, timezone

from sec_fundamentals import catalog, db, fetch


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


def run(db_path, only=None, exclude=None, add=None, tickers=None, periods=None,
        bulk=False, keep_days=None, fetch_frame=fetch.fetch_frame,
        fetch_facts=fetch.fetch_company_facts, fetch_map=fetch.fetch_ticker_map,
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
                        "ticker": label.get("ticker"), "name": label.get("title"),
                        "sic": None}], now_iso)
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
            db.upsert_companies(conn, [{"cik": cik, "ticker": sym, "name": name,
                                        "sic": None}], now_iso)
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
    p.add_argument("--keep-days", type=int, default=None,
                   help="prune snapshot provenance older than N days")
    a = p.parse_args(argv)
    _, ncomp, nfact = run(a.db, only=_split(a.only), exclude=_split(a.exclude),
                          add=a.add, tickers=_split(a.tickers), periods=a.period,
                          bulk=a.bulk, keep_days=a.keep_days)
    print(f"stored {nfact} facts across {ncomp} companies into {a.db}")


if __name__ == "__main__":
    main()
