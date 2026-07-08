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
    lines = ["  horizon | aligned=1 | aligned=0 | aligned=NULL"]
    for r in rows:
        lines.append(f"  {r['horizon']:>7} | {r['yes']:>9} | {r['no']:>9} | {r['null']:>12}")
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
    lines.append(f"  n={n}, avg_realized_return={avg_txt}")
    return "\n".join(lines)


def build_report(conn, now_iso: str) -> str:
    """Assemble the text scorecard. Read-only over scorer.db's journal views;
    every section renders its header + an explicit body even when empty, so a
    thin period is visibly thin rather than silently missing."""
    label = now_iso[:7]  # YYYY-MM — the period the report is generated for
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
