"""Trader decision-quality scorecard: a periodic, read-only report that
grades the human's discretion, not the model. It reads the decision-journal
views in scorer.db (v_human_filter, v_decision_outcomes, v_research_backed,
v_freelance) and prints a text report — does acting on flagged opinions beat passing, what
execution costs, do acted trades agree with the opinion the human saw, and
how research-backed and deliberate freelance trades performed.

Decision-support/reflection only: it computes nothing new, re-weights nothing,
generates no orders, and never writes to scorer.db (SELECT-only; ensure_schema
just guarantees the views exist, exactly as the journal dispatcher does).

Two correctness rules the report must never break (both from
sources/combiners/scorer/db.py):
  * ONE ROW PER HORIZON — a matured decision has up to len(HORIZONS) rows in
    v_decision_outcomes, so every aggregate GROUPs BY / filters on horizon.
  * SMALL-n — no bare average below N_MIN; a thin cell reads "insufficient
    data (n=k)", so one trade's outcome is never mistaken for a trend."""

import argparse
import sqlite3
from bisect import bisect_right
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sources.combiners.scorer import db
from sources.combiners.scorer.journal import AUTOMATIC_AGENTS
from sources.common.clock import phx_date

# Suppression floor: a (response|horizon) or (aligned|horizon) cell with fewer
# matured rows than this shows "insufficient data (n=k)" instead of an average.
# A floor, not a statistical test — it exists to stop a single trade reading as
# a trend, matching the views' own "plain averages + n day one" stance.
N_MIN = 5


def filter_edge(conn) -> list[dict]:
    """v_human_filter: acted vs passed vs passed_inferred, per horizon."""
    return [
        dict(response=r[0], horizon=r[1], n=r[2], avg_dir_excess=r[3], avg_fwd_return=r[4])
        for r in conn.execute(
            "SELECT response, horizon, n, avg_dir_excess, avg_fwd_return"
            " FROM v_human_filter ORDER BY horizon, response"
        )
    ]


def execution_cost(conn) -> list[dict]:
    """v_decision_outcomes grouped by horizon — slippage and fill lag on acted
    decisions. horizon IS NOT NULL drops still-ungraded decisions; GROUP BY
    horizon is the one-row-per-horizon guard."""
    return [
        dict(horizon=r[0], n=r[1], avg_entry_slippage=r[2], avg_fill_lag_days=r[3])
        for r in conn.execute(
            "SELECT horizon, COUNT(*) AS n, AVG(entry_slippage), AVG(fill_lag_days)"
            " FROM v_decision_outcomes WHERE horizon IS NOT NULL"
            " GROUP BY horizon ORDER BY horizon"
        )
    ]


def alignment(conn) -> list[dict]:
    """Per horizon, how many acted decisions agreed with the opinion the human
    saw (aligned=1), disagreed (0), or matched no registered opinion (NULL)."""
    counts: dict[int, dict[str, int]] = {}
    for horizon, aligned, n in conn.execute(
        "SELECT horizon, aligned, COUNT(*) FROM v_decision_outcomes"
        " WHERE horizon IS NOT NULL GROUP BY horizon, aligned"
    ):
        cell = counts.setdefault(horizon, {"yes": 0, "no": 0, "null": 0})
        key = "yes" if aligned == 1 else "no" if aligned == 0 else "null"
        cell[key] += n
    return [dict(horizon=h, **counts[h]) for h in sorted(counts)]


def deliberate_freelance(conn) -> list[dict]:
    """v_freelance minus automatic (drip/recurring) fills — trades nothing
    recommended, that a human deliberately placed."""
    placeholders = ", ".join("?" for _ in AUTOMATIC_AGENTS)
    return [
        dict(
            decision_id=r[0],
            symbol=r[1],
            side=r[2],
            realized_return=r[3],
            placed_agent=r[4],
            fill_date=r[5],
        )
        for r in conn.execute(
            "SELECT decision_id, symbol, side, realized_return, placed_agent, fill_date"
            f" FROM v_freelance WHERE placed_agent IS NULL"
            f" OR placed_agent NOT IN ({placeholders})"
            " ORDER BY decision_id",
            tuple(AUTOMATIC_AGENTS),
        )
    ]


def research_backed(conn) -> list[dict]:
    """v_research_backed rows — buys the research skill recommended."""
    return [
        dict(
            decision_id=r[0],
            symbol=r[1],
            side=r[2],
            realized_return=r[3],
            placed_agent=r[4],
            verdict_date=r[5],
            fill_date=r[6],
        )
        for r in conn.execute(
            "SELECT decision_id, symbol, side, realized_return, placed_agent, verdict_date,"
            " fill_date FROM v_research_backed ORDER BY decision_id"
        )
    ]


def book_curve(conn) -> list[dict]:
    """v_book_curve rows in date order — the stock book's TWR legs with SPY's
    matching leg."""
    return [
        dict(
            obs_date=r[0],
            equity=r[1],
            buys=r[2],
            sells=r[3],
            port_return=r[4],
            spy_close=r[5],
            spy_return=r[6],
        )
        for r in conn.execute(
            "SELECT obs_date, equity, buys, sells, port_return, spy_close, spy_return"
            " FROM v_book_curve ORDER BY obs_date"
        )
    ]


def book_excluded(conn) -> list[tuple[str, str]]:
    """(symbol, reason) the book refuses to price — printed, never silently
    dropped."""
    return [
        (r[0], r[1])
        for r in conn.execute("SELECT symbol, reason FROM v_book_excluded ORDER BY symbol")
    ]


def measured_legs(rows) -> list[dict]:
    """Rows whose leg the book can measure. A row with no prior value and no
    buy (the anchor, or an all-cash day) has no book leg, and SPY's leg for
    that day is dropped with it — the two sides always chain the same days."""
    return [r for r in rows if r["port_return"] is not None]


def _chain(rows, key="port_return") -> float | None:
    """Geometric linking of per-leg returns (None until a second observation
    creates the first leg)."""
    legs = [r[key] for r in rows if r[key] is not None]
    if not legs:
        return None
    total = 1.0
    for leg in legs:
        total *= 1.0 + leg
    return total - 1.0


def dff_series(fred_conn) -> list[tuple[str, float]]:
    """(date, annualized percent) DFF observations, oldest first — the cash
    benchmark's raw input. fred.db is opened as its own read-only connection
    (never attached to the scorer's write connection)."""
    return [
        (r[0], r[1])
        for r in fred_conn.execute(
            "SELECT date, value FROM observations"
            " WHERE series_id = 'DFF' AND value IS NOT NULL ORDER BY date"
        )
    ]


def cash_endpoint_return(dff, start_date: str, end_date: str) -> float | None:
    """Chained overnight cash over [start_date, end_date): each calendar day
    accrues DFF/360 (fed funds is annualized actual/360), carrying the most
    recent observation forward across gaps and publication lag. None when no
    observation exists on/before start_date — refuse, never assume 0%."""
    rows = sorted((d, v) for d, v in dff if v is not None)
    if start_date >= end_date or not rows:
        return None
    dates = [d for d, _ in rows]
    i = bisect_right(dates, start_date) - 1
    if i < 0:
        return None
    total = 1.0
    day = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    while day < end:
        iso = day.isoformat()
        while i + 1 < len(dates) and dates[i + 1] <= iso:
            i += 1
        total *= 1.0 + rows[i][1] / 36000.0
        day += timedelta(days=1)
    return total - 1.0


def _frac(x) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:.2f}%"


def _mean(x) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def _avg_or_suppressed(n, formatted: str) -> str:
    return formatted if n >= N_MIN else f"insufficient data (n={n})"


def _filter_edge_section(conn) -> str:
    rows = filter_edge(conn)
    if not rows:
        return "  no matured flagged opinions yet"
    lines = ["  horizon | response         | n  | avg_dir_excess | avg_fwd_return"]
    for r in rows:
        excess = _avg_or_suppressed(r["n"], _frac(r["avg_dir_excess"]))
        fwd = _avg_or_suppressed(r["n"], _frac(r["avg_fwd_return"]))
        lines.append(
            f"  {r['horizon']:>7} | {r['response']:<16} | {r['n']:>2} | {excess:<14} | {fwd}"
        )
    return "\n".join(lines)


def _execution_cost_section(conn) -> str:
    rows = execution_cost(conn)
    if not rows:
        return "  no matured acted decisions yet"
    lines = ["  horizon | n  | avg_entry_slippage | avg_fill_lag_days"]
    for r in rows:
        slip = _avg_or_suppressed(r["n"], _pct(r["avg_entry_slippage"]))
        lag = _avg_or_suppressed(r["n"], _mean(r["avg_fill_lag_days"]))
        lines.append(f"  {r['horizon']:>7} | {r['n']:>2} | {slip:<18} | {lag}")
    return "\n".join(lines)


def _alignment_section(conn) -> str:
    rows = alignment(conn)
    if not rows:
        return "  no matured acted decisions yet"
    # Human column names, not the view's aligned=1/0/NULL coding: the report
    # is a reading surface (CLI and dashboard both render it verbatim).
    lines = ["  horizon | agreed | contrarian | no opinion"]
    for r in rows:
        lines.append(f"  {r['horizon']:>7} | {r['yes']:>6} | {r['no']:>10} | {r['null']:>10}")
    return "\n".join(lines)


def _trade_list(rows, empty: str, extra=None) -> str:
    if not rows:
        return f"  {empty}"
    header = "  decision_id | symbol | side | realized_return"
    lines = [header + (f" | {extra}" if extra else "")]
    realized = [r["realized_return"] for r in rows if r["realized_return"] is not None]
    for r in rows:
        line = (
            f"  {r['decision_id']:>11} | {r['symbol']:<6} | {r['side'] or '?':<4}"
            f" | {_frac(r['realized_return'])}"
        )
        if extra:
            line += f" | {r[extra]}"
        lines.append(line)
    n = len(rows)
    avg = sum(realized) / len(realized) if realized else None
    # realized_return is fills-only; open positions are counted and listed
    # but excluded from the average.
    avg_txt = _avg_or_suppressed(n, _frac(avg)) if avg is not None else f"insufficient data (n={n})"
    trade_word = "trade" if n == 1 else "trades"
    lines.append(f"  {n} {trade_word}, average realized return {avg_txt}")
    return "\n".join(lines)


def _freelance_section(conn) -> str:
    return _trade_list(deliberate_freelance(conn), "no deliberate freelance trades")


def _research_backed_section(conn) -> str:
    return _trade_list(research_backed(conn), "no research-backed trades", extra="verdict_date")


def _portfolio_section(conn, dff=()) -> str:
    rows = book_curve(conn)
    if len(rows) < 2:
        return f"  insufficient data (n={len(rows)} trading days with a book)"
    lines = ["  window     | portfolio TWR | SPY      | excess   | cash (DFF)"]

    def _window(label, window_rows):
        # The first row is the window's ANCHOR: both sides measure forward
        # from its close, so its own leg (the one INTO the anchor) is dropped
        # from both — chaining it would give the book one more leg than SPY.
        legs = measured_legs(window_rows[1:])
        twr = _chain(legs)
        spy = _chain(legs, "spy_return")
        if twr is None or spy is None:
            lines.append(f"  {label:<10} | insufficient data")
            return
        # Cash is a reference column, not a second excess: it spans the same
        # endpoints as the window, so all three columns measure one window.
        cash = cash_endpoint_return(dff, window_rows[0]["obs_date"], window_rows[-1]["obs_date"])
        lines.append(
            f"  {label:<10} | {_pct(twr):>13} | {_pct(spy):>8} | {_pct(twr - spy):>8} | {_pct(cash)}"
        )

    _window("inception", rows)
    for n in (21, 63):
        if len(rows) >= n + 1:
            _window(f"{n}d", rows[-(n + 1) :])
        else:
            lines.append(f"  {n:>2}d        | insufficient data (n={len(rows)} trading days)")
    positions = conn.execute(
        "SELECT COUNT(*) FROM v_book_fills WHERE symbol NOT IN"
        " (SELECT symbol FROM v_book_excluded) GROUP BY symbol HAVING SUM(qty) > 1e-9"
    ).fetchall()
    lines.append(
        f"  book: {len(positions)} positions, {len(rows)} trading days"
        f" {rows[0]['obs_date']}..{rows[-1]['obs_date']}"
    )
    excluded = book_excluded(conn)
    if excluded:
        lines.append("  excluded: " + ", ".join(f"{s} ({why})" for s, why in excluded))
    return "\n".join(lines)


def build_report(conn, now_iso: str, dff=()) -> str:
    """Assemble the text scorecard. Read-only over scorer.db's journal views;
    every section renders its header + an explicit body even when empty, so a
    thin period is visibly thin rather than silently missing."""
    label = phx_date(now_iso)[:7]  # YYYY-MM — the period the report is generated for
    parts = [
        f"=== Trader Decision-Quality Scorecard — {label} ===",
        "",
        "Filter edge (acted vs passed, by horizon)",
        _filter_edge_section(conn),
        "",
        "Execution cost (acted decisions, by horizon)",
        _execution_cost_section(conn),
        "",
        "Alignment (acted decisions, by horizon)",
        _alignment_section(conn),
        "",
        "Research-backed trades (research-ticker buy verdict before the fill)",
        _research_backed_section(conn),
        "",
        "Freelance trades (deliberate only)",
        _freelance_section(conn),
        "",
        "Portfolio vs SPY and cash (time-weighted, stock book only)",
        _portfolio_section(conn, dff),
    ]
    return "\n".join(parts)


def run(db_path: str, now_iso: str | None = None, fred_db_path: str | None = None) -> str:
    now_iso = now_iso or datetime.now(UTC).isoformat()
    # A missing fred.db degrades the cash column to n/a rather than erroring:
    # cash is a reference benchmark, never a gate on the report itself.
    dff: list[tuple[str, float]] = []
    if fred_db_path and Path(fred_db_path).exists():
        fconn = sqlite3.connect(f"file:{fred_db_path}?mode=ro", uri=True)
        try:
            dff = dff_series(fconn)
        finally:
            fconn.close()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)  # guarantees the views exist; never writes data
        return build_report(conn, now_iso, dff)
    finally:
        conn.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="scorecard",
        description="Print the trader decision-quality scorecard (reads"
        " scorer.db and fred.db read-only; grades human discretion, changes"
        " nothing)",
    )
    p.add_argument("--db", default="scorer.db")
    p.add_argument("--fred-db", default="fred.db", help="fred.db for the cash (DFF) benchmark")
    a = p.parse_args(argv)
    print(run(a.db, fred_db_path=a.fred_db))


if __name__ == "__main__":
    main()
