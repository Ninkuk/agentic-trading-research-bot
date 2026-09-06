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
                f"{str(v).capitalize()} calls right",
                _pct(best["hit_rate"]),
                f"{best['n']} calls · {best['horizon']} days out",
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
    col("fwd_return", "Return", term="Forward return"),
    col("bench_fwd_return", "SPY return", hidden=True),
    col("excess", "Vs SPY", term="Excess"),
    col("verdict_correct", "Right?", numeric=False),
]


def research_verdict_outcomes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_research_verdict_outcomes")
    # One tile per call type at its longest matured horizon, counted over
    # the whole view (the table below is a LIMITed drill-down).
    tiles = []
    seen: set[str] = set()
    for g in fetch(
        conn,
        "SELECT verdict, horizon, COUNT(*) AS n, SUM(verdict_correct) AS n_right"
        " FROM v_research_verdict_outcomes WHERE verdict_correct IS NOT NULL"
        " GROUP BY verdict, horizon ORDER BY verdict, horizon DESC",
    ):
        if g["verdict"] in seen:
            continue  # a longer horizon already made this call's tile
        seen.add(g["verdict"])
        tiles.append(
            tile(
                f"{str(g['verdict']).capitalize()} calls right",
                f"{int(g['n_right'] or 0)} of {g['n']}",
                f"at {g['horizon']}d",
            )
        )
    rows = fetch(
        conn,
        "SELECT symbol, verdict, verdict_date, horizon, fwd_return, bench_fwd_return,"
        " excess, verdict_correct FROM v_research_verdict_outcomes"
        " ORDER BY (fwd_return IS NULL), verdict_date DESC, symbol, horizon LIMIT ?",
        (_DRILL_LIMIT,),
    )
    for r in rows:
        r["verdict_correct"] = None if r["verdict_correct"] is None else bool(r["verdict_correct"])
    return {
        "tiles": tiles,
        "columns": _VERDICT_OUTCOME_COLUMNS,
        "rows": rows,
        "total": total,
        "empty": "no graded research calls yet",
    }


_CALIBRATION_BIN_COLUMNS = [
    col("horizon", "Horizon"),
    col("p_bin", "Said it would win", numeric=False),
    col("n", "Calls", direction="up-good"),
    col("n_dates", "Distinct dates", hidden=True),
    col("avg_p", "Average confidence"),
    col("beat_rate", "Actually won", direction="up-good"),
    col("brier", "Forecast error", direction="down-good"),
]

# A bin is its lower edge (0.6 = the 60–70% calls); the table shows the band.
_CALIBRATION_MATCH_TOLERANCE = 0.05


def _p_band(edge: Any) -> Any:
    if edge is None:
        return None
    lo = round(float(edge) * 100)
    return f"{lo}–{lo + 10}%"


def _calibration_chip(head: dict[str, Any]) -> dict[str, str] | None:
    """Said-vs-won at the stated horizon, once five calls have matured."""
    if head["n"] < 5 or head["avg_p"] is None or head["beat_rate"] is None:
        return None
    said, won = _pct(head["avg_p"]), _pct(head["beat_rate"])
    gap = head["avg_p"] - head["beat_rate"]
    if abs(gap) < _CALIBRATION_MATCH_TOLERANCE:
        return verdict(f"Confidence matched results: said {said}, won {won}", "mid")
    if gap > 0:
        return verdict(f"Overconfident: said {said}, won {won}", "off")
    return verdict(f"Underconfident: said {said}, won {won}", "on")


def research_calibration(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Stated-probability calibration. The headline horizon is the one the
    forecasts were STATED for (max n_stated), not the one with the most
    matured rows -- the fixed short horizons mature first and would
    otherwise grade a one-year call at five days."""
    summary = fetch(
        conn,
        "SELECT horizon, n, n_dates, n_stated, avg_p, beat_rate, brier,"
        " brier_base_rate, brier_kill, avg_disagreement"
        " FROM v_research_calibration ORDER BY horizon",
    )
    rows = fetch(
        conn,
        "SELECT horizon, p_bin, n, n_dates, avg_p, beat_rate, brier"
        " FROM v_research_calibration_bins ORDER BY horizon, p_bin",
    )
    for r in rows:
        r["p_bin"] = _p_band(r["p_bin"])
    tiles = []
    chip = None
    if summary:
        head = max(summary, key=lambda r: (r["n_stated"], r["horizon"]))
        h = head["horizon"]
        beats = head["brier"] < head["brier_base_rate"]
        calls = "call" if head["n"] == 1 else "calls"
        tiles.append(
            tile(
                "Forecast error",
                f"{head['brier']:.2f}",
                f"{h} days out · guessing the base rate scores"
                f" {head['brier_base_rate']:.2f} · {head['n']} {calls}",
                "on" if beats else "off",
            )
        )
        tiles.append(
            tile(
                "Said vs won",
                f"{_pct(head['avg_p'])} vs {_pct(head['beat_rate'])}",
                f"average confidence vs actual wins · {h} days out",
            )
        )
        if head["brier_kill"] is not None:
            tiles.append(
                tile(
                    "Kill-thesis forecast error",
                    f"{head['brier_kill']:.2f}",
                    f"disagrees with the thesis by {head['avg_disagreement']:.2f} on average",
                    "on" if head["brier_kill"] < head["brier"] else None,
                )
            )
        chip = _calibration_chip(head)
    return {
        "verdict": chip,
        "tiles": tiles,
        "columns": _CALIBRATION_BIN_COLUMNS,
        "rows": rows,
        "caveat": "Forecast error below the base-rate score means the stated"
        " confidence carries information; above it, always guessing the"
        " average would have done better. Bins stay tiny for months, so read"
        " Calls before the rates.",
        "empty": "no matured verdicts carry a stated probability yet",
    }


# --- per-flag human response ---------------------------------------------

_FLAG_RESPONSE_COLUMNS = [
    col("composite_date", "Flag date", numeric=False),
    col("symbol", "Symbol", numeric=False),
    col("score_sum", "Score"),
    col("total", "Signals"),
    col("response", "You did", numeric=False),
    col("horizon", "Horizon"),
    col("dir_excess", "Gain had you followed it", term="Directional excess"),
]

# The view's response codes, in the words the human-filter card uses.
_RESPONSE_WORDS = {
    "acted": "Acted",
    "acted_option": "Acted (options)",
    "passed": "Passed",
    "passed_inferred": "Skipped (no journal entry)",
}


def flag_response(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_flag_response")
    rows = fetch(
        conn,
        "SELECT composite_date, symbol, score_sum, total, response, horizon, dir_excess"
        " FROM v_flag_response ORDER BY composite_date DESC, symbol, horizon LIMIT ?",
        (_DRILL_LIMIT,),
    )
    for r in rows:
        r["response"] = _RESPONSE_WORDS.get(r["response"], r["response"])
    return {
        "columns": _FLAG_RESPONSE_COLUMNS,
        "rows": rows,
        "total": total,
        "empty": "no matured flags yet; appears once a flagged name reaches its grading horizon",
    }


# --- effective n ----------------------------------------------------------

_EFFECTIVE_N_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("via_crosswalk", "Via crosswalk", hidden=True),
    col("horizon", "Horizon"),
    col("n_matured", "Rows graded", hidden=True),
    col("n_dates", "Distinct dates", direction="up-good", hidden=True),
    col("n_blocks", "Independent episodes", direction="up-good"),
    col("hit_rate", "Hit rate (all rows)", term="Hit rate"),
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

# The screen's mechanics fold behind "more columns"; the outcome stays.
_CANDIDATE_OUTCOME_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("screen_date", "Entered list", numeric=False),
    col("growth_door", "Why it qualified", numeric=False, hidden=True),
    col("branch", "What flagged it", numeric=False, hidden=True),
    col("screen_version", "Screen version", numeric=False, hidden=True),
    col("horizon", "Horizon"),
    col("entry_close", "Price at entry", hidden=True),
    col("fwd_return", "Return", term="Forward return"),
    col("bench_fwd_return", "SPY return"),
    col("excess", "Vs SPY", term="Excess"),
    col("beat_benchmark", "Beat SPY?", numeric=False),
]


def candidate_outcomes(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    total = scalar(conn, "SELECT COUNT(*) FROM v_candidate_outcomes")
    rows = fetch(
        conn,
        "SELECT symbol, screen_date, growth_door, branch, screen_version, horizon,"
        " entry_close, fwd_return, bench_fwd_return, excess, beat_benchmark"
        " FROM v_candidate_outcomes"
        " ORDER BY (fwd_return IS NULL), screen_date DESC, symbol, horizon LIMIT ?",
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


# The words column leads; the entry/now pairs behind it fold behind
# "more columns".
_QUALITY_TREND_COLUMNS = [
    col("symbol", "Symbol", numeric=False),
    col("what_weakened", "What weakened", numeric=False),
    col("days_on_list", "Days on list"),
    col("n_sightings", "Sightings"),
    col("fscore_entry", "F-score at entry", hidden=True),
    col("fscore_now", "F-score now", direction="up-good", hidden=True),
    col("roic_entry", "ROIC at entry", hidden=True),
    col("roic_now", "ROIC now", direction="up-good", hidden=True),
    col("fcf_yield_entry", "FCF yield at entry", hidden=True),
    col("fcf_yield_now", "FCF yield now", hidden=True),
    col("accruals_now", "Accruals now", hidden=True),
    col("falling_knife", "Falling knife?", numeric=False),
]

_QUALITY_PAIRS = (("F-score", "fscore"), ("ROIC", "roic"))


def _what_weakened(r: dict[str, Any]) -> str:
    """The quality gates that fell between first sighting and now, as words;
    a pair missing either side is not counted."""
    fell = [
        name
        for name, k in _QUALITY_PAIRS
        if r[f"{k}_entry"] is not None
        and r[f"{k}_now"] is not None
        and r[f"{k}_now"] < r[f"{k}_entry"]
    ]
    return ", ".join(fell) or "nothing"


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
        r["what_weakened"] = _what_weakened(r)
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
    col("fill_date", "Opened on", numeric=False),
    col("contracts_opened", "Contracts opened"),
    col("contracts_closed", "Contracts closed"),
    col("contracts_outstanding", "Still open"),
    col("pnl_dollars", "Profit $"),
    col("premium_return", "Return on premium"),
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

# The statistics behind the verdict fold behind the table's "more columns"
# toggle; keys stay so the cell formatter still draws the CI mark and the
# excess bar.
_REPLAY_EFFICACY_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("direction", "Flag", numeric=False),
    col("horizon", "Horizon"),
    col("n_days", "Days flagged", hidden=True),
    col("hit_rate", "Hit rate"),
    col("hit_ci_lo", "CI low", term="CI", hidden=True),
    col("hit_ci_hi", "CI high", term="CI", hidden=True),
    col("baseline", "Drift alone", term="Base rate", hidden=True),
    col("excess", "Better than drift by", term="Excess", direction="up-good"),
    col("perm_p", "Chance of a fluke", direction="down-good", hidden=True),
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
    col("n_windows", "Days measured"),
    col("p_up", "Went up"),
    col("p_down", "Went down"),
]

# The chip reads the broad-market benchmark when it is present.
_HEADLINE_BENCHMARKS = ("SPY", "SP500")


def replay_baseline(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = fetch(
        conn,
        "SELECT benchmark, horizon, n_windows, p_up, p_down FROM v_benchmark_baseline"
        " ORDER BY benchmark, horizon",
    )
    chip = None
    if rows:
        names = {r["benchmark"] for r in rows}
        lead = next((b for b in _HEADLINE_BENCHMARKS if b in names), rows[0]["benchmark"])
        head = max((r for r in rows if r["benchmark"] == lead), key=lambda r: r["horizon"])
        chip = verdict(
            f"{lead} rose on {_pct(head['p_up'])} of {head['horizon']}-day windows", "mid"
        )
    return {
        "verdict": chip,
        "columns": _BASELINE_COLUMNS,
        "rows": rows,
        "empty": "no benchmark history loaded yet",
    }


# The score is a -1/0/+1 vote; the word is what a reader needs, so the
# number folds. The catalog carries no unit per series, so Value stays bare.
_REPLAY_FLAG_COLUMNS = [
    col("signal_id", "Signal", numeric=False),
    col("lean", "Lean", numeric=False),
    col("benchmark", "Benchmark", numeric=False),
    col("asof_date", "As of", numeric=False),
    col("value", "Value"),
    col("score", "Score", hidden=True),
    spark_col("history", "Score, last 90 flag days"),
]


def _lean(score: Any) -> str | None:
    if score is None:
        return None
    return "bullish" if score > 0 else "bearish" if score < 0 else "neutral"


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
        r["lean"] = _lean(r["score"])
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
        "Research",
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
        "Research",
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
        "research-calibration",
        "Research call calibration",
        "scorer.db",
        research_calibration,
        "Research",
        "When the research said 70% it would beat SPY, did it beat SPY 70% of the time?",
        [
            (
                "The chip and the tiles",
                "Every research call states how likely it is to beat SPY"
                " over a horizon. The chip compares the average confidence"
                " with the share of calls that actually won, once five have"
                " matured. Forecast error scores each call by how far its"
                " confidence sat from what happened: 0 is perfect, 0.25 is"
                " a coin flip, and lower is better. The tile also shows what"
                " always guessing the average win rate would have scored,"
                " which is the number to beat.",
            ),
            (
                "The table",
                "Calls are grouped by what they said, in ten-point bands."
                " A well-calibrated forecaster's 60–70% band wins about"
                " 65% of the time. Distinct dates, behind the columns"
                " toggle, is how many separate days those calls were made:"
                " ten calls on one day are closer to one observation.",
            ),
            (
                "Why it matters",
                "Hit rate cannot tell a calibrated forecaster from a lucky"
                " one. Sizing up on conviction is defensible only once the"
                " stated confidence is shown to track reality; nothing here"
                " feeds back into gates or sizing.",
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
        "Signals",
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
        "Research",
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
        "Research",
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
                "'What weakened' names the gates that fell since the first"
                " sighting; the before-and-after numbers sit behind 'more"
                " columns'. Flagged rows sort to the top; they are the names"
                " to re-research before buying more.",
            ),
            (
                "The gates",
                "F-score is a nine-point financial-health checklist; ROIC is"
                " the profit earned on the capital invested; FCF yield is"
                " spare cash as a share of the price; accruals are earnings"
                " that have not yet shown up as cash.",
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
        "Signals",
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
                "Drift alone is how often the benchmark simply rose over"
                " that horizon; better than drift by is the flag's hit rate"
                " minus that. 'Beats drift' means the whole confidence"
                " interval sits above the drift; 'anti-signal' means it sits"
                " entirely below — a signal reliably wrong is not a signal"
                " to flip.",
            ),
            (
                "The hidden columns",
                "Behind the columns toggle: how many days the flag was on,"
                " the confidence interval around the hit rate, the drift"
                " figure itself, and the chance of a fluke — how often"
                " shuffled data produced a hit rate this good, so 0.04"
                " means about one time in twenty-five.",
            ),
        ],
    ),
    (
        "replay-baseline",
        "Benchmark drift",
        "backtest.db",
        replay_baseline,
        "Signals",
        "How often each benchmark simply went up over each horizon — the bar every replayed flag has to clear.",
        [
            (
                "Why it exists",
                "Stocks drift upward, so a bullish flag that does nothing"
                " still 'wins' most windows. Every replay grade is measured"
                " against this drift, never against 50%.",
            ),
            (
                "The columns",
                "Days measured is how many start dates were tested. Went up"
                " and went down are the share of those windows where the"
                " benchmark finished higher or lower; they need not sum to"
                " 100% because some windows end flat.",
            ),
        ],
    ),
    (
        "replay-flags",
        "Replay flags today",
        "backtest.db",
        replay_flags,
        "Signals",
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
