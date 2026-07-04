"""Walk-forward scorer: stored leads vs later-observed snapshot prices.
Zero look-ahead by construction: entry is the first snapshot AFTER the lead's
as_of_date (t+1), exits at horizon/stop/truncation using only prices a later
snapshot actually recorded. A name absent from a snapshot is untradable that
day (tradability mask) — paths truncate, gaps shrink n_obs, nothing is
interpolated."""
from datetime import date, timedelta

from pipeline.common import pipeline_common
from pipeline.trials import catalog
from sources.monitors.market_calendar.db import is_trading_day


def check_required_columns(conn, db_label: str) -> None:
    """Fail up front with the full missing-id list — a clear error beats
    `OperationalError: no such column` mid-evaluation."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metrics)")}
    missing = [c for c in catalog.REQUIRED_DATA_POINTS if c not in cols]
    if missing:
        raise ValueError(
            f"{db_label} metrics table missing required data points: "
            f"{', '.join(missing)} (was it built with --only?)")


def load_price_history(conn):
    """(sorted snapshot dates, {date: {SYMBOL: (price, low)}}). Snapshot date
    = captured_at[:10]; when two snapshots share a date the later one wins.
    Symbols normalized for the cross-source join."""
    snaps = conn.execute("SELECT id, captured_at FROM snapshots "
                         "ORDER BY captured_at, id").fetchall()
    sid_by_date = {}
    for sid, cap in snaps:
        sid_by_date[cap[:10]] = sid
    history = {}
    for d, sid in sid_by_date.items():
        rows = conn.execute(
            'SELECT symbol, "price", "low" FROM metrics WHERE snapshot_id=?',
            (sid,)).fetchall()
        history[d] = {pipeline_common.normalize_ticker(sym): (price, low)
                      for sym, price, low in rows if sym}
    return sorted(history), history


def load_leads(conn) -> list:
    """Deduped cohort across snapshots: the same (instrument, signal-day)
    appearing in many funnel runs is ONE cohort entry."""
    rows = conn.execute(
        "SELECT DISTINCT instrument, instrument_kind, direction, "
        "horizon_band, as_of_date FROM leads "
        "ORDER BY as_of_date, instrument").fetchall()
    keys = ("instrument", "instrument_kind", "direction", "horizon_band",
            "as_of_date")
    return [dict(zip(keys, r)) for r in rows]


def trading_days_between(cal_conn, start: str, end: str) -> int:
    """Trading days in (start, end], from market_calendar — never plain
    date arithmetic."""
    n = 0
    cur = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    while cur < stop:
        cur += timedelta(days=1)
        if is_trading_day(cal_conn, cur.isoformat()):
            n += 1
    return n


def max_gap_days(dates: list) -> int:
    """Max calendar-day gap between consecutive snapshot dates — the honesty
    flag for results computed over gappy history."""
    if len(dates) < 2:
        return 0
    return max((date.fromisoformat(b) - date.fromisoformat(a)).days
               for a, b in zip(dates, dates[1:]))


def score_lead(lead: dict, dates: list, history: dict, cal_conn,
               horizon_days: int, entry_lag: int = catalog.DEFAULT_ENTRY_LAG,
               stop=None):
    """One lead -> {"ret", "entry_date", "exit_date", "truncated"} or None.

    Entry: the entry_lag-th snapshot date strictly after as_of_date where the
    symbol has a price (t+1 discipline). Exit: horizon breach, stop breach
    (LONG only — no high column exists for shorts), or truncation at the last
    snapshot where the symbol still exists. Stop-breach caveat: `low` is the
    snapshot day's low only; a breach inside a snapshot gap is undetected."""
    sym = lead["instrument"]
    later = [d for d in dates
             if d > lead["as_of_date"] and sym in history[d]
             and history[d][sym][0] is not None]
    if len(later) < entry_lag:
        return None
    entry_date = later[entry_lag - 1]
    entry_px = history[entry_date][sym][0]
    exit_date, exit_px = entry_date, entry_px
    truncated = False
    for d in dates:
        if d <= entry_date:
            continue
        if sym not in history[d] or history[d][sym][0] is None:
            truncated = True            # tradability mask: path ends here
            break
        px, low = history[d][sym]
        exit_date, exit_px = d, px
        if (stop is not None and lead["direction"] == "long"
                and low is not None and low <= stop):
            exit_px = stop              # exit AT the stop, not the close
            break
        if trading_days_between(cal_conn, entry_date, d) >= horizon_days:
            break
    if lead["direction"] == "long":
        ret = (exit_px - entry_px) / entry_px
    else:
        ret = (entry_px - exit_px) / entry_px
    return {"ret": ret, "entry_date": entry_date, "exit_date": exit_date,
            "truncated": truncated}


def evaluate_cohort(leads_conn, stock_history, etf_history, cal_conn,
                    entry_lag: int = catalog.DEFAULT_ENTRY_LAG) -> dict:
    """Score every deduped lead. stock_history/etf_history are
    (dates, history) tuples from load_price_history, or None when that price
    DB is unavailable (those leads are skipped, counted, never guessed)."""
    by_kind = {"stock": stock_history, "etf": etf_history}
    returns, scored, skipped = [], 0, 0
    window = []
    gaps = [max_gap_days(h[0]) for h in by_kind.values() if h is not None]
    for lead in load_leads(leads_conn):
        priced = by_kind.get(lead["instrument_kind"])
        horizon = catalog.HORIZON_TRADING_DAYS.get(lead["horizon_band"])
        if priced is None or horizon is None:
            skipped += 1
            continue
        result = score_lead(lead, priced[0], priced[1], cal_conn, horizon,
                            entry_lag=entry_lag)
        if result is None:
            skipped += 1
            continue
        returns.append(result["ret"])
        scored += 1
        window.append(lead["as_of_date"])
    return {"returns": returns,
            "window_start": min(window) if window else None,
            "window_end": max(window) if window else None,
            "scored": scored, "skipped": skipped,
            "max_gap_days": max(gaps) if gaps else 0}
