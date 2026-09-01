"""Track-record sections that were only reachable through SQL: the
research-verdict grade, the per-flag detail behind the human filter, the
overlap-aware effective-n check, the candidate drill-downs, option P&L, and
the point-in-time backtest replay.

All SELECT-only over scorer.db / backtest.db. Drill-down views are capped
(`_DRILL_LIMIT` newest rows) with `total` carrying the full count — the
frontend shows "showing N of total".
"""

from __future__ import annotations

import sqlite3
from typing import Any

from dashboard_lib.common import (
    attach_history,
    col,
    fetch,
    histories,
    scalar,
    spark_col,
    tile,
    verdict,
)

_DRILL_LIMIT = 150
_DATE_HISTORY_LIMIT = 60


def _pct(v: Any) -> str:
    return "—" if v is None else f"{round(float(v) * 100)}%"


def _rate_tone(v: Any) -> str | None:
    if v is None:
        return None
    return "on" if v >= 0.55 else "off" if v <= 0.45 else "mid"


# --- research-ticker verdicts ---------------------------------------------

_RESEARCH_FILTER_COLUMNS = [
    col("verdict", "Research call", numeric=False),
    col("horizon", "Horizon"),
    col("n", "N", direction="up-good"),
    col("hit_rate", "Hit rate", direction="up-good"),
    col("avg_excess", "Excess vs SPY"),
    col("avg_fwd_return", "Fwd return", term="Forward return"),
]


def research_filter(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT verdict, horizon, n, hit_rate, avg_excess, avg_fwd_return"
        " FROM v_research_filter ORDER BY verdict, horizon",
    )
    # One tile per call at its longest matured horizon — the headline a
    # reader wants without scanning the grid.
    tiles = []
    for v in sorted({r["verdict"] for r in rows}):
        best = max((r for r in rows if r["verdict"] == v), key=lambda r: r["horizon"])
        tiles.append(
            tile(
                f"{v} calls right",
                _pct(best["hit_rate"]),
                f"n={best['n']} · {best['horizon']}d",
                _rate_tone(best["hit_rate"]),
            )
        )
    return {
        "tiles": tiles,
        "columns": _RESEARCH_FILTER_COLUMNS,
        "rows": rows,
        "caveat": "Hit rate is the safe headline; the excess column reads inversely"
        " on pass calls (a pass is right when the name lags), so compare it"
        " only within one call type.",
        "empty": "no matured research verdicts yet; appears once a call's forward window closes",
    }


_VERDICT_OUTCOME_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("verdict", "Call", numeric=False),
    col("verdict_date", "Call date", numeric=False),
    col("horizon", "Horizon"),
    col("fwd_return", "Fwd return", term="Forward return"),
    col("bench_fwd_return", "SPY return"),
    col("excess", "Excess vs SPY"),
    col("verdict_correct", "Right?", numeric=False),
]


def research_verdict_outcomes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_research_verdict_outcomes")
    rows = fetch(
        conn,
        "SELECT symbol, verdict, verdict_date, horizon, fwd_return, bench_fwd_return,"
        " excess, verdict_correct FROM v_research_verdict_outcomes"
        " ORDER BY verdict_date DESC, symbol, horizon LIMIT ?",
        (_DRILL_LIMIT,),
    )
    for r in rows:
        r["verdict_correct"] = None if r["verdict_correct"] is None else bool(r["verdict_correct"])
    return {
        "columns": _VERDICT_OUTCOME_COLUMNS,
        "rows": rows,
        "total": total,
        "empty": "no graded research calls yet",
    }


# --- per-flag human response ---------------------------------------------

_FLAG_RESPONSE_COLUMNS = [
    col("composite_date", "Flag date", numeric=False),
    col("symbol", "Symbol", numeric=False),
    col("score_sum", "Score"),
    col("total", "Signals"),
    col("response", "You did", numeric=False),
    col("horizon", "Horizon"),
    col("dir_excess", "Directional excess"),
]


def flag_response(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_flag_response")
    rows = fetch(
        conn,
        "SELECT composite_date, symbol, score_sum, total, response, horizon, dir_excess"
        " FROM v_flag_response ORDER BY composite_date DESC, symbol, horizon LIMIT ?",
        (_DRILL_LIMIT,),
    )
    return {
        "columns": _FLAG_RESPONSE_COLUMNS,
        "rows": rows,
        "total": total,
        "empty": "no matured flags yet; appears once a flagged name reaches its grading horizon",
    }


# --- effective n ----------------------------------------------------------

_EFFECTIVE_N_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("via_crosswalk", "Via crosswalk"),
    col("horizon", "Horizon"),
    col("n_matured", "Rows graded"),
    col("n_dates", "Distinct dates", direction="up-good"),
    col("n_blocks", "Independent episodes", direction="up-good"),
    col("hit_rate", "Pooled hit rate"),
    spark_col("history", "Hit rate by date"),
    col("latest_block", "Latest episode", numeric=False),
]


def signal_effective_n(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """v_signal_efficacy's n columns beside v_signal_efficacy_by_date's
    per-date hit rate and v_signal_blocks' episode spans: the pooled n is
    a row count, the honest n is distinct dates or independent episodes."""
    rows = fetch(
        conn,
        "SELECT signal_id, via_crosswalk, horizon, n_matured, n_dates, n_blocks, hit_rate"
        " FROM v_signal_efficacy ORDER BY horizon, via_crosswalk, signal_id",
    )
    hist = histories(
        conn,
        "SELECT signal_id || '|' || via_crosswalk || '|' || horizon, date_hit_rate * 100"
        " FROM v_signal_efficacy_by_date ORDER BY composite_date",
        limit=_DATE_HISTORY_LIMIT,
    )
    latest: dict[str, str] = {}
    for b in fetch(
        conn,
        "SELECT signal_id, via_crosswalk, horizon, composite_date, exit_date"
        " FROM v_signal_blocks ORDER BY composite_date",
    ):
        k = f"{b['signal_id']}|{b['via_crosswalk']}|{b['horizon']}"
        latest[k] = f"{b['composite_date']} → {b['exit_date']}"
    for r in rows:
        r["_k"] = f"{r['signal_id']}|{r['via_crosswalk']}|{r['horizon']}"
        r["latest_block"] = latest.get(r["_k"])
    attach_history(rows, hist, "_k")
    for r in rows:
        del r["_k"]
    thin = sum(1 for r in rows if (r["n_blocks"] or 0) < 3)
    return {
        "verdict": verdict(
            f"{thin} of {len(rows)} signals rest on fewer than 3 independent episodes",
            "off" if thin and thin >= len(rows) / 2 else "mid" if thin else "on",
        )
        if rows
        else None,
        "columns": _EFFECTIVE_N_COLUMNS,
        "rows": rows,
        "caveat": "A signal that fired on ten overlapping days is one observation, not ten."
        " Trust the episode count over the row count.",
        "empty": "no matured signal outcomes yet",
    }


# --- candidates screen drill-downs ----------------------------------------

_CANDIDATE_OUTCOME_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("screen_date", "Entered list", numeric=False),
    col("growth_door", "Growth door", numeric=False),
    col("branch", "Door", numeric=False),
    col("screen_version", "Screen", numeric=False),
    col("horizon", "Horizon"),
    col("entry_close", "Entry price"),
    col("fwd_return", "Fwd return", term="Forward return"),
    col("bench_fwd_return", "SPY return"),
    col("excess", "Excess vs SPY"),
    col("beat_benchmark", "Beat SPY?", numeric=False),
]


def candidate_outcomes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_candidate_outcomes")
    rows = fetch(
        conn,
        "SELECT symbol, screen_date, growth_door, branch, screen_version, horizon,"
        " entry_close, fwd_return, bench_fwd_return, excess, beat_benchmark"
        " FROM v_candidate_outcomes"
        " ORDER BY screen_date DESC, symbol, horizon LIMIT ?",
        (_DRILL_LIMIT,),
    )
    for r in rows:
        r["beat_benchmark"] = None if r["beat_benchmark"] is None else bool(r["beat_benchmark"])
    return {
        "columns": _CANDIDATE_OUTCOME_COLUMNS,
        "rows": rows,
        "total": total,
        "empty": "no matured list entries yet; appears 21 trading days after"
        " a name first enters the candidates list",
    }


_QUALITY_TREND_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("days_on_list", "Days on list"),
    col("n_sightings", "Sightings"),
    col("fscore_entry", "F-score at entry"),
    col("fscore_now", "F-score now", direction="up-good"),
    col("roic_entry", "ROIC at entry"),
    col("roic_now", "ROIC now", direction="up-good"),
    col("fcf_yield_entry", "FCF yield at entry"),
    col("fcf_yield_now", "FCF yield now"),
    col("accruals_now", "Accruals now"),
    col("falling_knife", "Falling knife?", numeric=False),
]


def _falling_knife(r: dict[str, Any]) -> bool | None:
    """FCF yield rising while F-score or ROIC falls: the price is dropping
    faster than the business is deteriorating — a cheapening that the level
    gates cannot see. None when either side lacks a before/after pair."""
    fy0, fy1 = r["fcf_yield_entry"], r["fcf_yield_now"]
    if fy0 is None or fy1 is None:
        return None
    pairs = [(r["fscore_entry"], r["fscore_now"]), (r["roic_entry"], r["roic_now"])]
    known = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not known:
        return None
    return fy1 > fy0 and any(b < a for a, b in known)


def candidate_quality_trend(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT symbol, days_on_list, n_sightings, fscore_entry, fscore_now, roic_entry,"
        " roic_now, fcf_yield_entry, fcf_yield_now, accruals_now"
        " FROM v_candidate_quality_trend",
    )
    for r in rows:
        r["falling_knife"] = _falling_knife(r)
    rows.sort(key=lambda r: (not r["falling_knife"], -(r["days_on_list"] or 0), r["symbol"]))
    knives = sum(1 for r in rows if r["falling_knife"])
    return {
        "verdict": verdict(
            f"{knives} falling {'knives' if knives != 1 else 'knife'} on the list"
            if knives
            else "no falling knives on the list",
            "off" if knives else "on",
        )
        if rows
        else None,
        "columns": _QUALITY_TREND_COLUMNS,
        "rows": rows,
        "empty": "no candidate has been on the list for two sightings yet",
    }


# --- options ---------------------------------------------------------------

_OPTION_PNL_COLUMNS = [
    col("symbol", "Underlying", numeric=False),
    col("direction", "Direction", numeric=False),
    col("expiration", "Expiry", numeric=False),
    col("fill_date", "Opened", numeric=False),
    col("contracts_opened", "Opened"),
    col("contracts_closed", "Closed"),
    col("contracts_outstanding", "Open"),
    col("pnl_dollars", "P&L $"),
    col("premium_return", "Premium return"),
]


def option_pnl(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """v_option_pnl (one row per opening fill) beside v_option_actor's
    per-direction grade as tiles. Contract identity (`contract_ref`) stays
    out — the underlying, direction and expiry are the public shape."""
    rows = fetch(
        conn,
        "SELECT symbol, direction, expiration, fill_date, contracts_opened,"
        " contracts_closed, contracts_outstanding, pnl_dollars, premium_return"
        " FROM v_option_pnl ORDER BY fill_date DESC, symbol",
    )
    tiles = [
        tile(
            f"{a['direction']} closed",
            a["n_closed"],
            f"hit {_pct(a['hit_rate'])} · P&L ${round(a['total_pnl'] or 0):,}",
            _rate_tone(a["hit_rate"]),
        )
        for a in fetch(conn, "SELECT * FROM v_option_actor ORDER BY direction")
    ]
    return {
        "tiles": tiles,
        "columns": _OPTION_PNL_COLUMNS,
        "rows": rows,
        "empty": "no option fills journaled yet; appears with the first"
        " single-leg option fill synced into the journal",
    }


# --- backtest replay (backtest.db) ----------------------------------------

_REPLAY_EFFICACY_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("direction", "Flag", numeric=False),
    col("horizon", "Horizon"),
    col("n_days", "Flag days"),
    col("hit_rate", "Hit rate"),
    col("hit_ci_lo", "CI low", term="CI"),
    col("hit_ci_hi", "CI high", term="CI"),
    col("baseline", "Drift baseline"),
    col("excess", "Excess vs drift", direction="up-good"),
    col("perm_p", "Permutation p", direction="down-good"),
    col("beats_baseline", "Beats drift?", numeric=False),
    col("anti_signal", "Anti-signal?", numeric=False),
]


def replay_efficacy(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT signal_id, direction, horizon, n_days, hit_rate, hit_ci_lo, hit_ci_hi,"
        " baseline, excess, perm_p, beats_baseline, anti_signal FROM v_replay_efficacy"
        " ORDER BY beats_baseline DESC, anti_signal, signal_id, direction, horizon",
    )
    for r in rows:
        for k in ("beats_baseline", "anti_signal"):
            r[k] = None if r[k] is None else bool(r[k])
    beats = sum(1 for r in rows if r["beats_baseline"])
    anti = sum(1 for r in rows if r["anti_signal"])
    return {
        "verdict": verdict(
            f"{beats} beat the drift · {anti} anti-signal · {len(rows) - beats - anti} noise",
            "on" if beats and not anti else "off" if anti > beats else "mid",
        )
        if rows
        else None,
        "columns": _REPLAY_EFFICACY_COLUMNS,
        "rows": rows,
        "caveat": "Nominal and uncorrected across ~48 comparisons; a lone 'beats drift'"
        " at p≈0.04 is what chance produces. Read excess against the baseline,"
        " never hit rate alone — the benchmarks drift up, so a bullish flag"
        " 'wins' by doing nothing.",
        "empty": "no replay yet; runs Saturdays after the ALFRED vintage pull",
    }


_BASELINE_COLUMNS = [
    col("benchmark", "Benchmark", numeric=False),
    col("horizon", "Horizon"),
    col("n_windows", "Windows"),
    col("p_up", "P(up)"),
    col("p_down", "P(down)"),
]


def replay_baseline(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT benchmark, horizon, n_windows, p_up, p_down FROM v_benchmark_baseline"
        " ORDER BY benchmark, horizon",
    )
    return {
        "columns": _BASELINE_COLUMNS,
        "rows": rows,
        "empty": "no benchmark history loaded yet",
    }


_REPLAY_FLAG_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("benchmark", "Benchmark", numeric=False),
    col("asof_date", "As of", numeric=False),
    col("value", "Value"),
    col("score", "Score"),
    spark_col("history", "Score, last 90 flag days"),
]


def replay_flags(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """The newest flag per (signal, benchmark) with its score history —
    what the replay believes right now, from the same point-in-time inputs
    it grades. One ordered scan of the view: a correlated MAX() subquery
    re-evaluates the (expensive) view per row."""
    latest: dict[str, dict[str, Any]] = {}
    hist: dict[str, list[float]] = {}
    for r in conn.execute(
        "SELECT signal_id, benchmark, asof_date, value, score FROM v_replay_flags"
        " ORDER BY asof_date"
    ):
        k = f"{r['signal_id']}|{r['benchmark']}"
        latest[k] = dict(r)
        if r["score"] is not None:
            hist.setdefault(k, []).append(float(r["score"]))
    rows = [latest[k] for k in sorted(latest)]
    for r in rows:
        r["history"] = (hist.get(f"{r['signal_id']}|{r['benchmark']}") or [])[-90:] or None
        if r["history"] is not None and len(r["history"]) < 3:
            r["history"] = None
    return {
        "columns": _REPLAY_FLAG_COLUMNS,
        "rows": rows,
        "empty": "no replay flags yet",
    }


SECTIONS: list[Any] = [
    (
        "research-filter",
        "Research call grade",
        "scorer.db",
        research_filter,
        "Track record",
        "When the research skill said buy or pass, how often was it right against SPY?",
        [
            (
                "How it is measured",
                "Every research-ticker verdict starts a stopwatch. A buy is"
                " right when the name beats SPY over the horizon; a pass is"
                " right when it lags. Hit rate is the share of calls that"
                " were right.",
            ),
            (
                "Why it matters",
                "This is the grade for the whole funnel's last step — the"
                " decision a human actually makes. Below 50% at n>30 means the"
                " research is adding noise, not signal.",
            ),
        ],
    ),
    (
        "research-verdict-outcomes",
        "Research calls, one by one",
        "scorer.db",
        research_verdict_outcomes,
        "Track record",
        "Every graded research call with what the stock and SPY did afterward.",
        [
            (
                "How to read it",
                "One row per call and horizon. Excess is the stock's return"
                " minus SPY's; 'Right?' applies the call's own direction (a"
                " pass is right when excess is negative).",
            ),
            (
                "Why it matters",
                "The grade above is an average; this is where you find the"
                " one call that dragged it, and whether the miss was a stock"
                " story or a market move.",
            ),
        ],
    ),
    (
        "flag-response",
        "What you did with each flag",
        "scorer.db",
        flag_response,
        "Track record",
        "Each composite flag, whether you acted or passed, and how the name moved afterward.",
        [
            (
                "How to read it",
                "'acted' means a fill landed on the flagged name, 'passed'"
                " means you logged a deliberate no, 'inferred' means no"
                " record either way. Directional excess is the return in the"
                " flag's direction, minus SPY.",
            ),
            (
                "Why it matters",
                "This is the row-level detail behind the 'Filter edge' tally:"
                " if the passes outperform the acted rows, your filter is"
                " subtracting value.",
            ),
        ],
    ),
    (
        "signal-effective-n",
        "How much evidence, really",
        "scorer.db",
        signal_effective_n,
        "Track record",
        "The signal report cards count rows; this counts independent episodes, which is the honest sample size.",
        [
            (
                "The problem",
                "A signal that fires on ten consecutive days produces ten"
                " overlapping forward windows. They mostly share the same"
                " market weeks, so ten rows is closer to one observation.",
            ),
            (
                "How to read it",
                "'Distinct dates' collapses same-day rows; 'independent"
                " episodes' also merges runs of consecutive dates whose"
                " windows overlap. The sparkline is the hit rate on each"
                " flag date — a grade earned on one hot week shows as a"
                " single spike.",
            ),
        ],
    ),
    (
        "candidate-outcomes",
        "Candidates list, entry by entry",
        "scorer.db",
        candidate_outcomes,
        "Track record",
        "What each name did against SPY after it first appeared on the candidates list.",
        [
            (
                "How to read it",
                "One row per list entry and horizon. 'Door' is which"
                " dislocation test let the name onto the list — an oversold"
                " RSI, a drawdown from the high, or both.",
            ),
            (
                "Why it matters",
                "The screen's edge is an average over these rows. A single"
                " large winner can carry it, so scan the distribution before"
                " trusting the summary.",
            ),
        ],
    ),
    (
        "candidate-quality-trend",
        "Falling-knife check",
        "scorer.db",
        candidate_quality_trend,
        "Track record",
        "For every name still on the candidates list, whether the business has weakened since it first appeared.",
        [
            (
                "What a falling knife is",
                "A stock that looks cheaper every week because its price is"
                " falling faster than its earnings — the cash-flow yield rises"
                " while the F-score or return on capital drops. The level"
                " gates keep passing it; only the trend shows the problem.",
            ),
            (
                "How to read it",
                "Each row compares the quality gates on the first sighting"
                " with the newest one. Flagged rows sort to the top; they"
                " are the names to re-research before buying more.",
            ),
        ],
    ),
    (
        "option-pnl",
        "Option premium P&L",
        "scorer.db",
        option_pnl,
        "Track record",
        "Dollar profit on single-leg option trades, kept separate from the stock grades.",
        [
            (
                "How it is measured",
                "Every option fill is a signed cash event in the premium"
                " ledger; a position's P&L is those events summed once it"
                " closes or expires. Premium return is P&L over the premium"
                " at risk.",
            ),
            (
                "Why it is separate",
                "Options are graded on dollars, stocks on return versus SPY —"
                " the two never mix, so a lucky expiry cannot flatter the"
                " stock-picking grade.",
            ),
        ],
    ),
    (
        "replay-efficacy",
        "Backtest replay",
        "backtest.db",
        replay_efficacy,
        "Track record",
        "Would the macro signals have worked in the past, using only the data that existed at the time?",
        [
            (
                "How it is measured",
                "Each FRED series is replayed from its ALFRED vintages —"
                " the numbers as first published, before revisions — and"
                " each flag is graded on what SPY (or a sector ETF) did next."
                " A report enters the replay only after its release date.",
            ),
            (
                "How to read it",
                "Drift baseline is how often the benchmark simply rose over"
                " that horizon; excess is the flag's hit rate minus that."
                " 'Beats drift' means the whole confidence interval sits"
                " above the baseline; 'anti-signal' means it sits entirely"
                " below — a signal reliably wrong is not a signal to flip.",
            ),
        ],
    ),
    (
        "replay-baseline",
        "Benchmark drift",
        "backtest.db",
        replay_baseline,
        "Track record",
        "How often each benchmark simply went up over each horizon — the bar every replayed flag has to clear.",
        [
            (
                "Why it exists",
                "Stocks drift upward, so a bullish flag that does nothing"
                " still 'wins' most windows. Every replay grade is measured"
                " against this null, never against 50%.",
            ),
        ],
    ),
    (
        "replay-flags",
        "Replay flags today",
        "backtest.db",
        replay_flags,
        "Track record",
        "What each replayed signal is saying right now, with its score over the last 90 flag days.",
        [
            (
                "How to read it",
                "Score is the flag's vote: positive bullish, negative"
                " bearish, zero quiet. The sparkline shows how long it has"
                " held that view.",
            ),
            (
                "Why it matters",
                "This is the live edge of the backtest — the same signal"
                " definitions the replay graded, applied to the newest"
                " vintage.",
            ),
        ],
    ),
]
