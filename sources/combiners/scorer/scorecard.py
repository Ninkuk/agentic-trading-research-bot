"""Trader decision-quality scorecard: a periodic, read-only report that
grades the human's discretion, not the model. It reads the four decision-
journal views in scorer.db (v_human_filter, v_decision_outcomes, v_freelance)
and prints a text report — does acting on flagged opinions beat passing, what
execution costs, do acted trades agree with the opinion the human saw, and
how deliberate freelance trades performed.

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
from datetime import UTC, datetime

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
        dict(decision_id=r[0], symbol=r[1], side=r[2], realized_return=r[3], placed_agent=r[4])
        for r in conn.execute(
            "SELECT decision_id, symbol, side, realized_return, placed_agent"
            f" FROM v_freelance WHERE placed_agent IS NULL"
            f" OR placed_agent NOT IN ({placeholders})"
            " ORDER BY decision_id",
            tuple(AUTOMATIC_AGENTS),
        )
    ]


def equity_curve(conn) -> list[dict]:
    """v_equity_curve rows in date order — TWR legs plus same-date SPY close."""
    return [
        dict(
            obs_date=r[0],
            equity=r[1],
            flow=r[2],
            prev_equity=r[3],
            port_return=r[4],
            spy_close=r[5],
        )
        for r in conn.execute(
            "SELECT obs_date, equity, flow, prev_equity, port_return, spy_close"
            " FROM v_equity_curve ORDER BY obs_date"
        )
    ]


def orphan_transfer_dates(conn) -> list[str]:
    """Transfers dated where no equity observation exists. Each one poisons
    chaining across it — the single case where a bad/missing point does NOT
    self-cancel — so the section refuses rather than guesses (the same
    refuse-to-grade stance as the crosswalk rule in db.py)."""
    return [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT t.obs_date FROM transfers t"
            " LEFT JOIN equity_ledger e ON e.obs_date = t.obs_date"
            " WHERE e.obs_date IS NULL ORDER BY t.obs_date"
        )
    ]


def _chain(rows) -> float | None:
    """Geometric linking of per-leg returns (None until a second observation
    creates the first leg)."""
    legs = [r["port_return"] for r in rows if r["port_return"] is not None]
    if not legs:
        return None
    total = 1.0
    for leg in legs:
        total *= 1.0 + leg
    return total - 1.0


def _spy_endpoint_return(rows) -> float | None:
    """SPY over the same window, from endpoint closes — per-day alignment is
    unnecessary for a cumulative comparison and weekend ledger rows have no
    SPY close to align with."""
    closes = [r["spy_close"] for r in rows if r["spy_close"] is not None]
    if len(closes) < 2:
        return None
    return closes[-1] / closes[0] - 1.0


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


def _freelance_section(conn) -> str:
    rows = deliberate_freelance(conn)
    if not rows:
        return "  no deliberate freelance trades"
    lines = ["  decision_id | symbol | side | realized_return"]
    realized = [r["realized_return"] for r in rows if r["realized_return"] is not None]
    for r in rows:
        lines.append(
            f"  {r['decision_id']:>11} | {r['symbol']:<6} | {r['side'] or '?':<4}"
            f" | {_frac(r['realized_return'])}"
        )
    n = len(rows)
    avg = sum(realized) / len(realized) if realized else None
    # realized_return is fills-only; unrealized freelance positions are counted
    # and listed but excluded from the average (spec §3.4).
    avg_txt = _avg_or_suppressed(n, _frac(avg)) if avg is not None else f"insufficient data (n={n})"
    trade_word = "trade" if n == 1 else "trades"
    lines.append(f"  {n} {trade_word}, average realized return {avg_txt}")
    return "\n".join(lines)


def _portfolio_section(conn) -> str:
    orphans = orphan_transfer_dates(conn)
    if orphans:
        return (
            "  cannot chain: transfer(s) on "
            + ", ".join(orphans)
            + " have no equity observation — backfill the ledger for those"
            " dates or correct the transfer date"
        )
    rows = equity_curve(conn)
    if len(rows) < 2:
        return f"  insufficient data (n={len(rows)} ledger dates)"
    trading = [r for r in rows if r["spy_close"] is not None]
    lines = ["  window     | portfolio TWR | SPY      | excess"]

    def _window(label, window_rows):
        twr = _chain(window_rows)
        spy = _spy_endpoint_return(window_rows)
        if twr is None:
            lines.append(f"  {label:<10} | insufficient data")
            return
        excess = _pct(twr - spy) if spy is not None else "n/a"
        lines.append(f"  {label:<10} | {_pct(twr):>13} | {_pct(spy):>8} | {excess}")

    _window("inception", rows)
    for n in (21, 63):
        if len(trading) >= n + 1:
            start = trading[-(n + 1)]["obs_date"]
            _window(f"{n}d", [r for r in rows if r["obs_date"] >= start])
        else:
            lines.append(f"  {n:>2}d        | insufficient data (n={len(trading)} trading days)")
    gaps = conn.execute(
        "SELECT COUNT(*) FROM prices p WHERE p.symbol='SPY'"
        " AND p.price_date > ? AND p.price_date < ?"
        " AND p.price_date NOT IN (SELECT obs_date FROM equity_ledger)",
        (rows[0]["obs_date"], rows[-1]["obs_date"]),
    ).fetchone()[0]
    lines.append(
        f"  coverage: {len(rows)} ledger dates {rows[0]['obs_date']}..{rows[-1]['obs_date']},"
        f" {gaps} trading days missing"
    )
    return "\n".join(lines)


def build_report(conn, now_iso: str) -> str:
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
        "Freelance trades (deliberate only)",
        _freelance_section(conn),
        "",
        "Portfolio vs SPY (time-weighted)",
        _portfolio_section(conn),
    ]
    return "\n".join(parts)


def run(db_path: str, now_iso: str | None = None) -> str:
    now_iso = now_iso or datetime.now(UTC).isoformat()
    conn = db.connect(db_path)
    try:
        db.ensure_schema(conn)  # guarantees the views exist; never writes data
        return build_report(conn, now_iso)
    finally:
        conn.close()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="scorecard",
        description="Print the trader decision-quality scorecard (reads"
        " scorer.db read-only; grades human discretion, changes nothing)",
    )
    p.add_argument("--db", default="scorer.db")
    a = p.parse_args(argv)
    print(run(a.db))


if __name__ == "__main__":
    main()
