"""One-shot historical backfill of the permanent price ledger's benchmark
proxies (plan 005). Manual, never scheduled — the nightly scorer run keeps the
ledger current; this only gives its 18 crosswalk proxies deep history so the
backtest combiner can grade asset-class signals against a real spine.

The ledger's forward feeder (scorer.fetch.harvest_prices) stores the settled
close for a session. This module writes the same quantity from stockanalysis's
history API, and rows are reconciled by insert_prices' INSERT OR IGNORE:
existing forward rows always win. Verified 2026-07-09 that the two agree on
every overlapping (symbol, date) — 54/54 across the 18 proxies.
"""

import argparse
import json
import time
import urllib.request
from datetime import UTC, datetime

from sources.combiners.scorer import catalog, db
from sources.common.clock import phx_date

HISTORY_URL = "https://stockanalysis.com/api/symbol/s/{symbol}/history?range=Max"
_UA = {"User-Agent": "Mozilla/5.0"}
_SLEEP_SECONDS = 0.7  # unofficial endpoint; be a polite client


def _default_get(symbol: str) -> dict:
    req = urllib.request.Request(HISTORY_URL.format(symbol=symbol), headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _bars(payload) -> list:
    """The bar list, tolerating both observed shapes.

    With `?range=Max`, `payload["data"]` IS the list. The bare URL (no query
    string) instead returns `{"data": {"data": [...], "news": ..., "other": ...}}`
    for some symbols and HTTP 404 for others. The shape is demonstrably not
    stable, so accept either and raise on anything else rather than silently
    yielding no rows (CLAUDE.md: live-verify source schemas)."""
    bars = payload["data"]
    if isinstance(bars, dict):
        bars = bars["data"]
    if not isinstance(bars, list):
        raise ValueError(f"unexpected history payload: {type(bars).__name__}")
    return bars


def parse_history(payload, before_date: str) -> list[tuple[str, float]]:
    """Pure. (price_date, close) ascending, for bars STRICTLY BEFORE before_date.

    Uses `c`, the split-adjusted close — NOT `a`, which is also dividend-
    adjusted and would diverge from the forward feeder on every payer (XOM
    2015-01-02: c=92.83, a=57.09).

    before_date is the run's Phoenix date. The newest bar is the current
    session, whose `c` is a LIVE price when the market is open; the forward
    feeder applies the same settled-only rule. Dropping a settled same-day bar
    costs one day and self-heals on the next nightly harvest.

    An empty series is valid (a delisted symbol) and returns []. Rows with a
    null close are dropped, never defaulted."""
    out = []
    for bar in _bars(payload):
        date, close = bar.get("t"), bar.get("c")
        if not isinstance(date, str) or len(date) != 10 or date[4] != "-" or date[7] != "-":
            raise ValueError(f"unexpected bar date: {date!r}")
        if close is None or date >= before_date:
            continue
        out.append((date, float(close)))
    out.sort()
    return out


def fetch_history(symbol: str, before_date: str, get=_default_get) -> list[tuple[str, float]]:
    """Network. `get` is the injectable seam: symbol -> decoded JSON payload."""
    return parse_history(get(symbol), before_date)


def run(
    db_path,
    symbols=None,
    *,
    now_iso=None,
    dry_run=False,
    fetch_history=fetch_history,
    sleep=time.sleep,
) -> tuple[int, int, list[str]]:
    """Returns (symbols_ok, rows_inserted, failed_symbols)."""
    symbols = list(symbols if symbols is not None else catalog.BACKFILL_SYMBOLS)
    before_date = phx_date(now_iso or datetime.now(UTC).isoformat())
    conn = db.connect(db_path)
    ok = inserted = 0
    failed: list[str] = []
    try:
        db.ensure_schema(conn)
        for i, symbol in enumerate(symbols):
            if i:
                sleep(_SLEEP_SECONDS)
            try:
                rows = fetch_history(symbol, before_date)
                if not rows:
                    raise ValueError("no bars before " + before_date)
                if dry_run:
                    print(f"{symbol}: {len(rows)} bars {rows[0][0]}..{rows[-1][0]} (dry-run)")
                else:
                    n = db.insert_prices(conn, [(symbol, d, c) for d, c in rows])
                    conn.commit()
                    inserted += n
                    print(f"{symbol}: {len(rows)} bars, {n} new")
                ok += 1
            except Exception as e:
                # Secret hygiene: an HTTPError carries the request URL.
                conn.rollback()
                print(f"FAILED {symbol}: {type(e).__name__}")
                failed.append(symbol)
    finally:
        conn.close()
    return ok, inserted, failed


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="pricehistory",
        description="ONE-SHOT backfill of the price ledger's benchmark proxies"
        " from stockanalysis history. Never schedule this.",
    )
    p.add_argument("--db", default="scorer.db")
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--exclude", nargs="*", default=None)
    p.add_argument("--dry-run", action="store_true", help="fetch and report; write nothing")
    a = p.parse_args(argv)

    known = set(catalog.BACKFILL_SYMBOLS)
    chosen = list(a.only) if a.only else list(catalog.BACKFILL_SYMBOLS)
    unknown = sorted(set(chosen) - known)
    if unknown:
        raise SystemExit(f"unknown symbols: {', '.join(unknown)}")
    if a.exclude:
        chosen = [s for s in chosen if s not in set(a.exclude)]

    ok, inserted, failed = run(a.db, chosen, dry_run=a.dry_run)
    print(f"pricehistory: {ok} symbols, {inserted} rows inserted, {len(failed)} failed")
    if failed:
        print("failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
