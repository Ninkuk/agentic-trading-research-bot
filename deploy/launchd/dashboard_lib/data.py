"""Generate the dashboard's data.json: the same accumulated pipeline state as
the legacy HTML generator (dashboard_lib/sections.py), exported as plain data
for a React frontend instead of server-rendered markup.

Mirrors dashboard_lib/sections.py's resilience contract: reads each source DB
with `sqlite3.connect("file:data/<db>?mode=ro", uri=True)`, strictly
read-only, and wraps every section in its own try/except so a missing DB, a
dropped view, or zero rows degrades to an `"error"` key on that section's
export rather than crashing the whole document. Nothing derived from the
exception ever leaves this module beyond `type(e).__name__` — never
`str(e)`/`repr(e)`, which can embed a DB path or (for a urllib error
upstream) a URL. A section registered here whose exporter fn doesn't exist
yet is simply absent from `SECTION_EXPORTERS` until its task lands; the
document as a whole always exports successfully — a total failure is the
caller's job to catch (mirrors dashboard.py's "generation failed" page: an
absent data.json would be worse than an honest error banner).
"""

import json
import re
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from dashboard_lib import narrative  # noqa: E402
from dashboard_lib.glossary import load_glossary  # noqa: E402
from sources.combiners.composite import candidates as candidates_mod  # noqa: E402
from sources.combiners.scorer import scorecard as scorer_scorecard  # noqa: E402
from sources.common.clock import phx_date  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _streak_nights(conn: sqlite3.Connection) -> int:
    """Leading run of consecutive nightly snapshots (newest-first) whose
    regime equals the latest snapshot's regime. Snapshot-grain (one
    market_regime row per snapshot by construction) — a regime change resets
    the run, and a `mixed` streak counts like any other regime. NEW SQL: no
    section in sections.py computes a streak (review-verified)."""
    rows = conn.execute(
        "SELECT m.regime FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at DESC"
    ).fetchall()
    if not rows:
        return 0
    latest = rows[0]["regime"]
    streak = 0
    for row in rows:
        if row["regime"] != latest:
            break
        streak += 1
    return streak


# _classify_regime (sources/combiners/composite/db.py) decides the regime
# from exactly three inputs — VIX level, VIX term-structure backwardation,
# and the high-yield spread (matching this section's own `note` prose
# below); the other eight tracked inputs never move the label. These
# thresholds mirror that function's own numbers so a driver row's "lean"
# reads consistently with the regime it explains; they are duplicated
# (not imported) because `_classify_regime`'s constants are module-private.
_VIX_RISK_ON_MAX = 20.0
_VIX_RISK_OFF_MIN = 25.0
_HY_SPREAD_WIDE = 4.0


def _lean_vix(vix: float | None) -> str:
    if vix is None:
        return "mid"
    if vix >= _VIX_RISK_OFF_MIN:
        return "off"
    if vix < _VIX_RISK_ON_MAX:
        return "on"
    return "mid"


def _lean_backwardation(back: int | None) -> str:
    if back is None:
        return "mid"
    return "off" if back else "on"


def _lean_hy_spread(hy: float | None) -> str:
    if hy is None:
        return "mid"
    return "on" if hy < _HY_SPREAD_WIDE else "off"


_REGIME_DRIVER_COLUMNS: list[dict[str, Any]] = [
    {"key": "input", "label": "Input", "numeric": False, "direction": None, "term": None},
    {"key": "value", "label": "Value", "numeric": True, "direction": None, "term": None},
    {"key": "lean", "label": "Lean", "numeric": False, "direction": None, "term": None},
]


def _regime(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    r = conn.execute(
        "SELECT regime, vix, inputs_present, inputs_expected,"
        " t10y2y, curve_inverted, hy_spread, vix_backwardation,"
        " equity_pcr_pctile, in_fomc_blackout, imminent_high_impact,"
        " days_to_opex, rrp_change, tga_change FROM v_latest_regime"
    ).fetchone()
    if r is None:
        return {
            "verdict": None,
            "tiles": [],
            "columns": _REGIME_DRIVER_COLUMNS,
            "rows": [],
            "empty": "no composite snapshot yet — fills after the first nightly run",
        }
    verdict = narrative.regime_verdict(r["regime"], _streak_nights(conn))
    tone = verdict["tone"] if verdict is not None else "mid"
    vix_band = None if r["vix"] is None else narrative.qualitative_band("vix", r["vix"])
    tiles = [
        {"label": "regime", "value": r["regime"], "band": None, "tone": tone},
        {"label": "VIX", "value": r["vix"], "band": vix_band, "tone": None},
        {
            "label": "inputs",
            "value": f"{r['inputs_present']}/{r['inputs_expected']}",
            "band": None,
            "tone": None,
        },
    ]
    rows = [
        {"input": "VIX level", "value": r["vix"], "lean": _lean_vix(r["vix"])},
        {"input": "10y–2y spread", "value": r["t10y2y"], "lean": "mid"},
        {"input": "yield curve inverted", "value": r["curve_inverted"], "lean": "mid"},
        {
            "input": "high-yield spread",
            "value": r["hy_spread"],
            "lean": _lean_hy_spread(r["hy_spread"]),
        },
        {
            "input": "VIX backwardation",
            "value": r["vix_backwardation"],
            "lean": _lean_backwardation(r["vix_backwardation"]),
        },
        {"input": "put / call percentile", "value": r["equity_pcr_pctile"], "lean": "mid"},
        {"input": "FOMC blackout", "value": r["in_fomc_blackout"], "lean": "mid"},
        {
            "input": "imminent high-impact event",
            "value": r["imminent_high_impact"],
            "lean": "mid",
        },
        {"input": "days to options expiry", "value": r["days_to_opex"], "lean": "mid"},
        {"input": "Fed RRP change", "value": r["rrp_change"], "lean": "mid"},
        {"input": "Treasury TGA change", "value": r["tga_change"], "lean": "mid"},
    ]
    return {"verdict": verdict, "tiles": tiles, "columns": _REGIME_DRIVER_COLUMNS, "rows": rows}


def _regime_timeline(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT s.captured_at, m.regime, m.vix FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at ASC"
    ).fetchall()
    if not rows:
        return {
            "rows": [],
            "empty": "no composite snapshots yet — fills after the first nightly run",
        }
    return {
        "rows": [
            {"date": phx_date(r["captured_at"]), "regime": r["regime"], "vix": r["vix"]}
            for r in rows
        ]
    }


# (series_id, tile label, qualitative_band metric) — the regime's three
# deciding inputs, same trio as _regime's `note` prose.
_FRED_DRIVER_SERIES = [
    ("T10Y2Y", "10y–2y spread", "t10y2y"),
    ("BAMLH0A0HYM2", "high-yield spread", "hy_spread"),
    ("VIXCLS", "VIX", "vix"),
]


def _macro_drivers(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    tiles: list[dict[str, Any]] = []
    for sid, label, metric in _FRED_DRIVER_SERIES:
        rows = conn.execute(
            "SELECT date, value FROM observations WHERE series_id = ?"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 90",
            (sid,),
        ).fetchall()
        values = list(reversed(rows))  # oldest-first
        if not values:
            tiles.append(
                {
                    "label": label,
                    "series_id": sid,
                    "value": None,
                    "delta": None,
                    "band": None,
                    "history": [],
                }
            )
            continue
        latest = values[-1]["value"]
        delta = latest - values[-2]["value"] if len(values) > 1 else None
        tiles.append(
            {
                "label": label,
                "series_id": sid,
                "value": latest,
                "delta": delta,
                "band": narrative.qualitative_band(metric, latest),
                "history": [{"date": row["date"], "value": row["value"]} for row in values],
            }
        )
    return {"tiles": tiles}


_SCORECARD_COLUMNS: list[dict[str, Any]] = [
    {"key": "symbol", "label": "Symbol", "numeric": False, "direction": None, "term": None},
    # Diverging: a large negative score_sum is just as strong a signal as a
    # large positive one, so there is no "higher is better" arrow to show.
    {"key": "score_sum", "label": "Score", "numeric": True, "direction": None, "term": None},
    {"key": "bullish", "label": "Bullish", "numeric": True, "direction": None, "term": None},
    {"key": "bearish", "label": "Bearish", "numeric": True, "direction": None, "term": None},
    {"key": "total", "label": "Signals", "numeric": True, "direction": None, "term": None},
    {
        "key": "coverage",
        "label": "Coverage",
        "numeric": True,
        "direction": "up-good",
        "term": "Coverage",
    },
    {
        "key": "worst_staleness_days",
        "label": "Data age (days)",
        "numeric": True,
        "direction": "down-good",
        "term": None,
    },
    {"key": "in_portfolio", "label": "Held", "numeric": False, "direction": None, "term": None},
]

# Bare rows (no history) run ~150-200KB for the full ~1,017-row scorecard;
# adding a 30-point history array to every one of those rows (v_score_history
# is ~30,760 rows tonight, growing toward 365-day retention) would put the
# export at 12-15MB at full retention. Trend history is exported only for
# the headline set below.
_SCORECARD_HISTORY_LIMIT = 30


def headline_symbols(conn: sqlite3.Connection) -> set[str]:
    """The scorecard's headline set: top-15-by-|score_sum| plus every
    flagged symbol (a flagged row can rank below 15 on score_sum alone,
    since flagging also gates on `total` — mirrors the union guard at
    sections.py:404-410). This is the only set that gets sparkline history
    in the scorecard export; Task 8 reuses it to bound the ticker
    drill-down (`tickers` in the top-level document) to the same size."""
    top = {
        r["symbol"]
        for r in conn.execute(
            "SELECT symbol FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC, symbol LIMIT 15"
        )
    }
    flagged = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_flagged")}
    return top | flagged


def flagged_tickers(data_dir: str) -> list[str]:
    """Tonight's flagged symbols, strongest-agreement first — for Task 8's
    hero clause. Degrades to an empty list on any failure (missing DB,
    dropped view), mirroring every other data_dir-driven helper here."""
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            return [
                r["symbol"]
                for r in conn.execute(
                    "SELECT symbol FROM v_flagged ORDER BY ABS(score_sum) DESC, symbol"
                )
            ]
        finally:
            conn.close()
    except Exception:
        return []


def _scorecard(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    flagged = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_flagged")}
    headline = headline_symbols(conn)

    all_rows = conn.execute(
        "SELECT symbol, score_sum, total, coverage, in_portfolio, bullish,"
        " bearish, worst_staleness_days FROM v_latest_scorecard"
        " ORDER BY ABS(score_sum) DESC, symbol"
    ).fetchall()

    # One grouped query covers every headline symbol's trend — never one
    # query per row. Every headline symbol defaults to [] so a symbol with
    # no/thin history still gets an (empty) list rather than being skipped.
    history: dict[str, list[int]] = {s: [] for s in headline}
    if headline:
        marks = ",".join("?" * len(headline))
        for r in conn.execute(
            f"SELECT symbol, score_sum FROM v_score_history WHERE symbol IN ({marks})"
            " ORDER BY captured_at ASC",
            tuple(headline),
        ):
            history[r["symbol"]].append(r["score_sum"])
    history = {s: v[-_SCORECARD_HISTORY_LIMIT:] for s, v in history.items()}

    rows = [
        {
            "symbol": r["symbol"],
            "score_sum": r["score_sum"],
            "bullish": r["bullish"],
            "bearish": r["bearish"],
            "total": r["total"],
            "coverage": r["coverage"],
            "worst_staleness_days": r["worst_staleness_days"],
            "in_portfolio": bool(r["in_portfolio"]),
            "flagged": r["symbol"] in flagged,
            "history": history[r["symbol"]] if r["symbol"] in headline else None,
        }
        for r in all_rows
    ]
    return {
        # No single tone/text summarizes ~1,000 independent per-ticker
        # tallies (unlike regime's one market-wide verdict) — always None,
        # per the generic section schema's "verdict | None" contract.
        "verdict": None,
        "columns": _SCORECARD_COLUMNS,
        "rows": rows,
        "total": len(all_rows),
    }


_CANDIDATES_COLUMNS: list[dict[str, Any]] = [
    {"key": "symbol", "label": "Symbol", "numeric": False, "direction": None, "term": None},
    {"key": "sector", "label": "Sector", "numeric": False, "direction": None, "term": None},
    {"key": "marketCap", "label": "Market cap", "numeric": True, "direction": None, "term": None},
    {"key": "roic", "label": "ROIC %", "numeric": True, "direction": "up-good", "term": None},
    {
        "key": "fcfYield",
        "label": "FCF yield %",
        "numeric": True,
        "direction": "up-good",
        "term": None,
    },
    {
        "key": "fScore",
        "label": "F-score",
        "numeric": True,
        "direction": "up-good",
        "term": "Piotroski score",
    },
    {"key": "rsi", "label": "RSI", "numeric": True, "direction": None, "term": None},
    {"key": "ch6m", "label": "6m change %", "numeric": True, "direction": None, "term": None},
]


def _candidates(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Quality-first research candidates from stocks.db. Reads the screen
    through `candidates.screen()` (never restates its gates) so this export
    and the CLI (`main.py candidates`) can never disagree about what
    qualifies."""
    rows = candidates_mod.screen(conn)
    return {
        "columns": _CANDIDATES_COLUMNS,
        "rows": [
            {
                "symbol": r["symbol"],
                "sector": r["sector"],
                "marketCap": r["marketCap"],
                "roic": r["roic"],
                "fcfYield": r["fcfYield"],
                "fScore": r["fScore"],
                "rsi": r["rsi"],
                "ch6m": r["ch6m"],
            }
            for r in rows
        ],
        "snapshot_date": candidates_mod.snapshot_date(conn),
    }


# Mirrors daily_summary._REOPEN_DATED_RE / sections.py's own regex — both
# read the same verdicts.log lines.
_REOPEN_FIELD_RE = re.compile(r"\breopen=(\d{4}-\d{2}-\d{2}|event):(\S+)")
_REOPEN_TICKER_RE = re.compile(r"^[A-Z0-9.\-]+$")
_REOPEN_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REOPEN_VERDICTS = {"SOUND", "FLAWED", "UNPROVEN"}

# research_verdicts.doc is recorded by the research-ticker skill as a bare
# filename "<TICKER>-<YYYY-MM-DD>.md" (see .claude/skills/research-ticker's
# journal-ingest doc), never a full path or URL — this guard mirrors
# _thesis_path's "don't trust a free-text column" posture before joining it
# under research/.
_VERDICT_DOC_RE = re.compile(r"^[A-Z0-9.\-]+-\d{4}-\d{2}-\d{2}\.md$")


def _verdict_thesis_path(doc: str | None) -> str | None:
    if doc is None or not _VERDICT_DOC_RE.match(doc):
        return None
    return f"research/{doc}"


_RESEARCH_REOPENS_COLUMNS: list[dict[str, Any]] = [
    {"key": "ticker", "label": "Ticker", "numeric": False, "direction": None, "term": None},
    {"key": "verdict", "label": "Verdict", "numeric": False, "direction": None, "term": None},
    {"key": "due", "label": "Due", "numeric": False, "direction": None, "term": None},
    {"key": "trigger", "label": "Trigger", "numeric": False, "direction": None, "term": None},
    {
        "key": "thesis_date",
        "label": "Thesis date",
        "numeric": False,
        "direction": None,
        "term": None,
    },
]


def _thesis_path(ticker: str, thesis_date: str) -> str | None:
    """Repo-relative path to the committed thesis doc, or None when the
    ticker/date don't look like a real filename (mirrors sections.py's
    `_thesis_link` fallback-to-plain-text guard). The CLIENT builds the
    GitHub blob URL from this — no absolute URL is ever exported."""
    if not _REOPEN_TICKER_RE.match(ticker) or not _REOPEN_DATE_RE.match(thesis_date):
        return None
    return f"research/{ticker}-{thesis_date}.md"


def _research_reopens(data_dir: str, now_iso: str) -> dict[str, Any]:
    """Open revisit triggers from research/verdicts.log, a sibling of the
    data dir (mirrors sections.py's `_research_reopens`, which resolves the
    same path from `data_dir`). Only the newest verdict line per ticker
    counts — a re-researched name retires its old trigger whether or not
    the new verdict sets its own."""
    vlog = Path(data_dir).parent / "research" / "verdicts.log"
    newest: dict[str, tuple[str, str]] = {}
    for raw in vlog.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2 or raw.lstrip().startswith("#"):
            continue
        if parts[1] not in newest or parts[0] >= newest[parts[1]][0]:
            newest[parts[1]] = (parts[0], raw)

    dated: list[tuple[str, str, str, str, str | None]] = []
    events: list[tuple[str, str, str, str | None]] = []
    for ticker, (thesis_date, line) in sorted(newest.items()):
        m = _REOPEN_FIELD_RE.search(line)
        if m is None:
            continue
        # Verdict-token extraction (field 2) is new logic, not a port of the
        # legacy parser (which reads only fields 0-1 and the reopen= regex):
        # validate against the allowed set, None for anything unrecognized.
        fields = line.split()
        verdict = fields[2] if len(fields) > 2 and fields[2] in _REOPEN_VERDICTS else None
        if m.group(1) == "event":
            events.append((ticker, m.group(2), thesis_date, verdict))
        else:
            dated.append((m.group(1), ticker, m.group(2), thesis_date, verdict))
    dated.sort(key=lambda t: (t[0], t[1]))

    rows = [
        {
            "ticker": ticker,
            "verdict": verdict,
            "due": when,
            "trigger": slug,
            "thesis_date": thesis_date,
            "thesis_path": _thesis_path(ticker, thesis_date),
        }
        for when, ticker, slug, thesis_date, verdict in dated
    ] + [
        {
            "ticker": ticker,
            "verdict": verdict,
            "due": None,
            "trigger": slug,
            "thesis_date": thesis_date,
            "thesis_path": _thesis_path(ticker, thesis_date),
        }
        for ticker, slug, thesis_date, verdict in events
    ]
    return {
        "columns": _RESEARCH_REOPENS_COLUMNS,
        "rows": rows,
        "dated": len(dated),
        "events": len(events),
    }


# --- Track-record strand (Task 6) ------------------------------------------
# Column-arrow convention, brief-specified and literal: only these exact
# view column names get an arrow. Everything else (ids, dates, CI bounds,
# `reliable`/`edge`/`n_blocks`/`n_matured`, via_crosswalk, recommendation)
# stays undirected rather than guessed.
_UP_GOOD = {
    "hit_rate",
    "avg_directional_excess",
    "n_bench",
    "n_dates",
    "avg_excess",
    "avg_fwd_return",
    "n",
}
# heat_dollars/heat_pct/weight_pct (Task 7, your-book strand): less dollars/
# percent of the book at risk on a one-ATR adverse day is always the better
# state, same "lower is safer" logic as null_rate.
_DOWN_GOOD = {"null_rate", "heat_dollars", "heat_pct", "weight_pct"}


def _direction(key: str) -> str | None:
    if key in _UP_GOOD:
        return "up-good"
    if key in _DOWN_GOOD:
        return "down-good"
    return None


def _track_col(
    key: str, label: str, numeric: bool = True, term: str | None = None
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "numeric": numeric,
        "direction": _direction(key),
        "term": term,
    }


_SIGNAL_EFFICACY_COLUMNS: list[dict[str, Any]] = [
    _track_col("signal_id", "Signal", numeric=False),
    _track_col("via_crosswalk", "Via crosswalk"),
    _track_col("horizon", "Horizon"),
    _track_col("n_bench", "N benchmarked"),
    _track_col("n_dates", "N dates"),
    _track_col("hit_rate", "Hit rate"),
    _track_col("hit_ci_lo", "Hit-rate CI low"),
    _track_col("hit_ci_hi", "Hit-rate CI high"),
    _track_col("null_rate", "Base rate"),
    _track_col("avg_directional_excess", "Directional excess"),
    _track_col("recommendation", "Recommendation", numeric=False),
]


def _signal_efficacy(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Every signal's raw report card. Rows come from **v_signal_recommendation**
    (scorer/db.py), NOT v_signal_efficacy / the legacy `_EFFICACY_COLS` — the
    recommendation view carries the CI bounds this section's dot-plot needs
    and the `recommendation` label the unfiltered efficacy view lacks.
    `via_crosswalk` stays in every row because the view is keyed on
    `(signal_id, via_crosswalk, horizon)`; dropping it would collapse
    distinct rows into indistinguishable duplicates."""
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_bench, n_dates, hit_rate,"
        " hit_ci_lo, hit_ci_hi, null_rate, avg_directional_excess, recommendation"
        " FROM v_signal_recommendation ORDER BY horizon, via_crosswalk, signal_id"
    ).fetchall()
    return {
        "columns": _SIGNAL_EFFICACY_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("signal-efficacy"),
        "empty": "no matured signal outcomes yet — appears once a signal's"
        " flagged calls reach their grading horizon",
    }


_BUCKET_PERFORMANCE_COLUMNS: list[dict[str, Any]] = [
    _track_col("bucket", "Bucket", numeric=False),
    _track_col("horizon", "Horizon"),
    _track_col("n_bench", "N"),
    _track_col("avg_fwd_return", "Fwd return"),
    _track_col("avg_excess", "Excess"),
    _track_col("hit_rate", "Hit rate"),
    _track_col("null_rate", "Base rate"),
    _track_col("edge", "Edge"),
    _track_col("reliable", "Reliable"),
]


def _bucket_performance(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT bucket, horizon, n_bench, avg_fwd_return, avg_excess,"
        " hit_rate, null_rate, edge, reliable FROM v_bucket_performance"
        " ORDER BY horizon, bucket"
    ).fetchall()
    return {
        "columns": _BUCKET_PERFORMANCE_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("bucket-performance"),
        "empty": "no matured buckets yet — appears once conviction-bucketed"
        " opinions reach their grading horizon",
    }


_HUMAN_FILTER_COLUMNS: list[dict[str, Any]] = [
    _track_col("response", "Response", numeric=False),
    _track_col("horizon", "Horizon"),
    _track_col("n", "N"),
    _track_col("avg_dir_excess", "Directional excess"),
    _track_col("avg_fwd_return", "Fwd return"),
]


def _human_filter(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT response, horizon, n, avg_dir_excess, avg_fwd_return"
        " FROM v_human_filter ORDER BY horizon, response"
    ).fetchall()
    return {
        "columns": _HUMAN_FILTER_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("human-filter"),
        "empty": "no matured flagged opinions yet — appears once an acted-on"
        " or passed-on flag reaches its grading horizon",
    }


_REGIME_PERFORMANCE_COLUMNS: list[dict[str, Any]] = [
    _track_col("regime", "Regime", numeric=False),
    _track_col("horizon", "Horizon"),
    _track_col("n_matured", "N"),
    _track_col("avg_bench_return", "Avg return"),
    _track_col("min_bench_return", "Min return"),
    _track_col("max_bench_return", "Max return"),
]


def _regime_performance(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT regime, horizon, n_matured, avg_bench_return, min_bench_return,"
        " max_bench_return FROM v_regime_performance ORDER BY horizon, regime"
    ).fetchall()
    return {
        "columns": _REGIME_PERFORMANCE_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("regime-performance"),
        "empty": "no matured regime outcomes yet — appears once a market-mood"
        " window reaches its grading horizon",
    }


_PENDING_COLUMNS: list[dict[str, Any]] = [
    _track_col("kind", "Kind", numeric=False),
    _track_col("composite_date", "Composite date", numeric=False),
    _track_col("symbol", "Entity", numeric=False),
    _track_col("horizon", "Horizon"),
    _track_col("entry_date", "Entry date", numeric=False),
]


def _pending(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """`total` is COUNT(*) over the full view — `rows` is the LIMIT 100 port
    (live v_pending is ~47K rows). Never drop `total`: it is the "showing
    100 of N" disclosure the legacy `.cap` note made. `entity` (the view's
    column) is exported as `symbol` for row-shape consistency with every
    other section here — it is a ticker for `kind='ticker'` rows and a
    compound/label for `signal`/`regime` rows."""
    total = conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0]
    rows = conn.execute(
        "SELECT kind, composite_date, entity AS symbol, horizon, entry_date"
        " FROM v_pending ORDER BY composite_date DESC LIMIT 100"
    ).fetchall()
    return {
        "columns": _PENDING_COLUMNS,
        "rows": [dict(r) for r in rows],
        "total": total,
        "caveat": narrative.CAVEATS.get("pending"),
        "empty": "nothing pending — everything registered so far has matured"
        " — fills once tonight's opinions are registered",
    }


_BASIS_BREAKS_COLUMNS: list[dict[str, Any]] = [
    _track_col("symbol", "Symbol", numeric=False),
    _track_col("prev_date", "Prev date", numeric=False),
    _track_col("prev_close", "Prev close"),
    _track_col("price_date", "Price date", numeric=False),
    _track_col("close", "Close"),
    _track_col("ratio", "Ratio"),
]


def _basis_breaks(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT symbol, prev_date, prev_close, price_date, close, ratio"
        " FROM v_basis_breaks ORDER BY price_date DESC"
    ).fetchall()
    return {
        "columns": _BASIS_BREAKS_COLUMNS,
        "rows": [dict(r) for r in rows],
        # No caveat: an integrity check, not a grade — a trust caveat here
        # would be noise (deliberate; narrative.CAVEATS has no entry for
        # "basis-breaks", see Task 2's deviations note).
        "caveat": narrative.CAVEATS.get("basis-breaks"),
        "empty": "no basis breaks detected — an empty table is the good"
        " outcome; fills only when a price move looks like a split or a bad tick",
    }


_SIGNAL_RECOMMENDATION_COLUMNS: list[dict[str, Any]] = [
    _track_col("signal_id", "Signal", numeric=False),
    _track_col("via_crosswalk", "Via crosswalk"),
    _track_col("horizon", "Horizon"),
    _track_col("n_blocks", "Independent windows"),
    _track_col("avg_directional_excess", "Directional excess"),
    _track_col("hit_rate", "Hit rate"),
    _track_col("hit_ci_lo", "Hit-rate CI low"),
    _track_col("hit_ci_hi", "Hit-rate CI high"),
    _track_col("recommendation", "Recommendation", numeric=False),
]


def _signal_recommendation(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """The verdict on each signal, graded against its own base rate. `verdict`
    wires narrative.efficacy_verdict (Task 2) against a tally of this
    section's own `recommendation` values — the helper would otherwise be
    dead code. Rows with recommendation == "insufficient evidence" count
    toward none of keep/watch/anti."""
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_blocks,"
        " avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, recommendation"
        " FROM v_signal_recommendation ORDER BY horizon, via_crosswalk, signal_id"
    ).fetchall()
    keep = sum(1 for r in rows if r["recommendation"] == "keep")
    watch = sum(1 for r in rows if r["recommendation"] == "watch")
    anti = sum(1 for r in rows if r["recommendation"] == "anti-signal")
    return {
        "verdict": narrative.efficacy_verdict(keep, watch, anti),
        "columns": _SIGNAL_RECOMMENDATION_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("plan-001-report"),
        "empty": "insufficient evidence for every signal (young scorer) —"
        " expected; fills in once a signal's evidence crosses the reliability floor",
    }


def _trader_scorecard(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Reuses the plan-004 report verbatim (single source of truth,
    scorer/scorecard.py's own `build_report`) — a plain-text report, not a
    table, so the export is `text_lines` only: no `columns`/`rows`, no
    `empty` (the report always renders a full structure, even a thin one,
    so there is no legacy empty-state prose to port)."""
    report = scorer_scorecard.build_report(conn, now_iso)
    return {
        "text_lines": report.split("\n"),
        "caveat": narrative.CAVEATS.get("plan-004-scorecard"),
    }


_CANDIDATE_EFFICACY_COLUMNS: list[dict[str, Any]] = [
    _track_col("screen_version", "Screen version", numeric=False),
    _track_col("branch", "Dislocation door", numeric=False),
    _track_col("horizon", "Horizon"),
    _track_col("n", "N"),
    _track_col("hit_rate", "Hit rate"),
    _track_col("avg_excess", "Excess"),
    _track_col("avg_fwd_return", "Fwd return"),
]


def _candidate_efficacy(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """NEW section — no sections.py counterpart to port (added 2026-07-29
    when the scorer began grading the candidates screen's list-entry timing,
    commit 3e4741b). Reads scorer.db's v_candidate_efficacy: a matured entry
    episode's 21/63-trading-day return vs SPY, split by which dislocation
    door admitted the name (oversold RSI / drawdown / both)."""
    rows = conn.execute(
        "SELECT screen_version, branch, horizon, n, hit_rate, avg_excess,"
        " avg_fwd_return FROM v_candidate_efficacy"
        " ORDER BY screen_version, horizon, branch"
    ).fetchall()
    return {
        "columns": _CANDIDATE_EFFICACY_COLUMNS,
        "rows": [dict(r) for r in rows],
        "caveat": narrative.CAVEATS.get("candidate-efficacy"),
        "empty": "no matured episodes yet — first grades appear ~21 trading"
        " days after the first screen night",
    }


# --- Your-book strand (Task 7) ----------------------------------------------
# Review-caught unit trap: advisor.db's v_book_heat/v_group_heat/v_latest_heat
# store heat_pct and weight_pct as FRACTIONS (heat_dollars / equity or market
# value), but sections.py's HTML always ran them through `_pct()` before
# display, and narrative.book_verdict/qualitative_band("book_heat_pct", ...)
# are calibrated in PERCENT (band cutoffs 1.5/3.0). Every one of these four
# exporters multiplies by 100 at the boundary — the one deliberate deviation
# from "export raw numbers" in this module, because the raw fraction would
# silently neuter the book verdict's bands (a live 0.0196 reads as
# "comfortable" under a percent-scale threshold table).


def _book_heat(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Book-wide risk-at-risk tiles — ported from sections.py:658-674
    (_book_heat). `heat_pct` is v_book_heat's FRACTION; converted to percent
    before it reaches narrative.book_verdict/qualitative_band (see the
    strand-level unit-trap note above)."""
    r = conn.execute(
        "SELECT positions, heat_pct, heat_coverage, equity, sources_failed FROM v_book_heat"
    ).fetchone()
    if r is None:
        return {
            "verdict": None,
            "tiles": [],
            "empty": "no advisor snapshot yet",
        }
    heat_pct_percent = None if r["heat_pct"] is None else r["heat_pct"] * 100
    heat_band = (
        None
        if heat_pct_percent is None
        else narrative.qualitative_band("book_heat_pct", heat_pct_percent)
    )
    tiles = [
        {"label": "positions", "value": r["positions"] or 0, "band": None, "tone": None},
        {"label": "book heat %", "value": heat_pct_percent, "band": heat_band, "tone": None},
        {"label": "coverage", "value": r["heat_coverage"], "band": None, "tone": None},
        {"label": "equity", "value": r["equity"], "band": None, "tone": None},
        {
            "label": "sources failed",
            "value": r["sources_failed"] or 0,
            "band": None,
            "tone": None,
        },
    ]
    return {"verdict": narrative.book_verdict(heat_pct_percent), "tiles": tiles}


_GROUP_HEAT_COLUMNS: list[dict[str, Any]] = [
    _track_col("bet", "Bet", numeric=False),
    _track_col("members", "Members"),
    _track_col("symbols", "Symbols", numeric=False),
    _track_col("heat_dollars", "Heat $"),
    _track_col("heat_pct", "Heat %"),
]


def _group_heat(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Correlated positions collapsed into single bets — ported from
    sections.py:677-692 (_group_heat). `heat_pct` is percent-converted, same
    unit trap as `_book_heat` above."""
    rows = conn.execute(
        "SELECT bet, members, symbols, heat_dollars, heat_pct FROM v_group_heat"
    ).fetchall()
    return {
        "columns": _GROUP_HEAT_COLUMNS,
        "rows": [
            {
                "bet": r["bet"],
                "members": r["members"],
                "symbols": r["symbols"] or "",
                "heat_dollars": r["heat_dollars"],
                "heat_pct": None if r["heat_pct"] is None else r["heat_pct"] * 100,
            }
            for r in rows
        ],
        "empty": "no group heat yet — appears once the advisor computes tonight's book",
    }


_POSITION_HEAT_COLUMNS: list[dict[str, Any]] = [
    _track_col("symbol", "Symbol", numeric=False),
    _track_col("group_name", "Group", numeric=False),
    _track_col("quantity", "Qty"),
    _track_col("market_value", "Market value"),
    _track_col("price", "Price"),
    _track_col("heat_dollars", "Heat $"),
    _track_col("heat_pct", "Heat %"),
    _track_col("weight_pct", "Weight %"),
    _track_col("score_sum", "Score"),
    _track_col("atr_stale", "Stale?", numeric=False),
]


def _position_heat(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Per-position risk contribution — ported from sections.py:695-735
    (_position_heat). The view's join-key column (snapshot_id) is internal
    bookkeeping and must never reach the page — explicit column list, never
    SELECT *. heat_pct/weight_pct are percent-converted, same unit trap as
    `_book_heat` above."""
    rows = conn.execute(
        "SELECT symbol, group_name, quantity, market_value, price, heat_dollars,"
        " heat_pct, weight_pct, score_sum, atr_stale FROM v_latest_heat"
        " ORDER BY heat_dollars DESC"
    ).fetchall()
    return {
        "columns": _POSITION_HEAT_COLUMNS,
        "rows": [
            {
                "symbol": r["symbol"],
                "group_name": r["group_name"],
                "quantity": r["quantity"],
                "market_value": r["market_value"],
                "price": r["price"],
                "heat_dollars": r["heat_dollars"],
                "heat_pct": None if r["heat_pct"] is None else r["heat_pct"] * 100,
                "weight_pct": None if r["weight_pct"] is None else r["weight_pct"] * 100,
                "score_sum": r["score_sum"],
                "atr_stale": bool(r["atr_stale"]),
            }
            for r in rows
        ],
        "empty": "no positions with heat yet",
    }


_DISAGREEMENTS_COLUMNS: list[dict[str, Any]] = [
    _track_col("symbol", "Symbol", numeric=False),
    _track_col("score_sum", "Score"),
    _track_col("group_name", "Group", numeric=False),
    _track_col("strong", "Strong", numeric=False),
]


def _disagreements(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Held positions where tonight's score points the opposite way — ported
    from sections.py:738-752 (_disagreements). `strong` mirrors composite's
    v_flagged thresholds (STRONG_MIN_ABS_SCORE/STRONG_MIN_TOTAL)."""
    rows = conn.execute(
        "SELECT symbol, score_sum, group_name, strong FROM v_disagreements"
    ).fetchall()
    return {
        "columns": _DISAGREEMENTS_COLUMNS,
        "rows": [
            {
                "symbol": r["symbol"],
                "score_sum": r["score_sum"],
                "group_name": r["group_name"],
                "strong": bool(r["strong"]),
            }
            for r in rows
        ],
        "empty": "no disagreements",
    }


_SIZE_CAPS_COLUMNS: list[dict[str, Any]] = [
    _track_col("symbol", "Symbol", numeric=False),
    _track_col("direction", "Direction", numeric=False),
    _track_col("score_sum", "Score"),
    _track_col("cap_shares", "Cap shares"),
    _track_col("cap_dollars", "Cap $"),
    _track_col("group_name", "Group", numeric=False),
    _track_col("exceeds_buying_power", "Exceeds buying power?", numeric=False),
]


def _size_caps(conn: sqlite3.Connection, now_iso: str) -> dict[str, Any]:
    """Volatility-scaled position-size ceiling per flagged candidate —
    ported from sections.py:755-778 (_size_caps). Decision support only,
    never an order (see this section's registry `note` below)."""
    rows = conn.execute(
        "SELECT symbol, direction, score_sum, cap_shares, cap_dollars,"
        " group_name, exceeds_buying_power FROM v_latest_caps"
    ).fetchall()
    return {
        "columns": _SIZE_CAPS_COLUMNS,
        "rows": [
            {
                "symbol": r["symbol"],
                "direction": r["direction"],
                "score_sum": r["score_sum"],
                "cap_shares": r["cap_shares"],
                "cap_dollars": r["cap_dollars"],
                "group_name": r["group_name"],
                "exceeds_buying_power": bool(r["exceeds_buying_power"]),
            }
            for r in rows
        ],
        "empty": "no caps tonight",
    }


# (sid, title, db_name, fn, kicker, note) — same ids/titles/kickers/notes as
# sections.py's SECTIONS; prose copied verbatim from sections.py:907-1116.
# candidate-efficacy has no sections.py counterpart (new 2026-07-29).
# Grows through Task 7-8 as the remaining (advisor/hero) sections register.
SECTION_EXPORTERS: list[tuple[str, str, str, Callable[..., dict[str, Any]], str, str]] = [
    (
        "regime",
        "Regime",
        "composite.db",
        _regime,
        "Macro",
        "The market's mood. The label is decided by three inputs — the VIX, its term structure, and high-yield spreads; the other seven are tracked and shown but do not move it. “Risk-on” means"
        " money is flowing toward risk; the VIX is a fear gauge — lower is"
        " calmer. Open the drivers to see which inputs argued which way.",
    ),
    (
        "regime-timeline",
        "Regime timeline",
        "composite.db",
        _regime_timeline,
        "Macro",
        "How the market mood and the VIX fear gauge have moved across"
        " recent nightly snapshots. Each dot is one snapshot; higher = more"
        " fear; dot color = that night's regime verdict (green risk-on, red"
        " risk-off, amber mixed).",
    ),
    (
        "macro-drivers",
        "Macro drivers",
        "fred.db",
        _macro_drivers,
        "Macro",
        "The regime's three deciding inputs with their recent history: the"
        " 10y–2y Treasury spread, the high-yield credit spread, and the VIX."
        " Each tile is today's value, the one-day change, and the last 90"
        " observations' trend.",
    ),
    (
        "candidates",
        "Research candidates",
        "stocks.db",
        _candidates,
        "Signals",
        "Businesses worth reading about, screened quality-first: durable returns"
        " on capital, real free cash flow, a rising Piotroski score, and a share"
        " price currently well off its highs. The scorecard below finds stocks"
        " doing something odd right now; this finds good companies that happen"
        " to be marked down. List entries are graded for calibration only"
        " (scorer.db v_candidate_efficacy) — it is a reading queue, not an"
        " opinion.",
    ),
    (
        "research-reopens",
        "Research reopens",
        "research/verdicts.log",
        _research_reopens,
        "Research",
        "Names already researched in depth and set aside, each with the stated"
        " evidence that would reopen the question. A dated trigger is usually"
        " an earnings report — “due” means that evidence now exists and the"
        " name deserves a fresh look. An event trigger waits on a filing or a"
        " price, with no date attached. A row retires when the name is"
        " re-researched; the ticker links to the full thesis.",
    ),
    (
        "scorecard",
        "Ticker scorecard",
        "composite.db",
        _scorecard,
        "Signals",
        "Every stock's net vote. Independent signals each lean bullish or"
        " bearish; the number is the summed score (the bar shows it, left of"
        " center for bearish). Split is the raw bullish/bearish count. A"
        " ★ marks strong agreement. A tally — not a buy or sell list.",
    ),
    (
        "signal-efficacy",
        "Signal efficacy",
        "scorer.db",
        _signal_efficacy,
        "Track record",
        "Every signal's raw report card: how often it has been right so far,"
        " and by how much it beat simply holding SPY. This is the unfiltered"
        " table — the verdict on whether each one is trustworthy yet lives"
        " in Signal recommendations below.",
    ),
    (
        "bucket-performance",
        "Bucket performance",
        "scorer.db",
        _bucket_performance,
        "Track record",
        "Grouping every past opinion by conviction bucket (strong-bull down"
        " to strong-bear): did stronger scores actually produce better"
        " forward returns than SPY?",
    ),
    (
        "human-filter",
        "Human-filter tally",
        "scorer.db",
        _human_filter,
        "Track record",
        "Of the opinions this page flagged, you either acted or passed. This"
        " compares how the acted-on ones did versus the passed ones — did"
        " your judgment add edge?",
    ),
    (
        "regime-performance",
        "Regime edge",
        "scorer.db",
        _regime_performance,
        "Track record",
        "Does the market-mood call itself have forward edge — do risk-on"
        " nights actually precede better returns than risk-off nights? Each"
        " row is one mood at one horizon.",
    ),
    (
        "pending",
        "In-flight opinions",
        "scorer.db",
        _pending,
        "Track record",
        "Opinions already recorded whose outcome has not matured yet — what"
        " is still being measured, and therefore not yet in any grade above.",
    ),
    (
        "basis-breaks",
        "Data-integrity checks",
        "scorer.db",
        _basis_breaks,
        "Track record",
        "Days where a price moved so far that it looks like a split or a bad"
        " tick rather than a real move. Surfaced so a silent data problem"
        " cannot quietly skew every grade above. An empty table is the good"
        " outcome.",
    ),
    (
        "book-heat",
        "Advisor book heat",
        "advisor.db",
        _book_heat,
        "Your book",
        "How much of your account is genuinely at risk right now, adding up"
        " the dollars at risk on a one-ATR adverse day across every open"
        " position. That is NOT the stop-out loss — the stop sits further"
        " out, so being stopped costs more. Coverage says how much of the"
        " book that number actually accounts for.",
    ),
    (
        "group-heat",
        "Advisor group heat",
        "advisor.db",
        _group_heat,
        "Your book",
        "Correlated positions collapsed into single bets (e.g. two energy"
        " names become one energy bet), because risk adds up within a group.",
    ),
    (
        "position-heat",
        "Per-position heat",
        "advisor.db",
        _position_heat,
        "Your book",
        "Risk contribution of each individual holding — the detail behind"
        " the book and group heat totals above. “Heat” is quantity ×"
        " ATR: the dollars at risk on a one-ATR adverse day, not the loss"
        " if the stop triggers.",
    ),
    (
        "disagreements",
        "Disagreements",
        "advisor.db",
        _disagreements,
        "Your book",
        "Tickers where tonight's score points the opposite way from a"
        " position you already hold. ‘Strong’ means the score is far"
        " enough from neutral to be worth a look.",
    ),
    (
        "size-caps",
        "Size caps",
        "advisor.db",
        _size_caps,
        "Your book",
        "A volatility-scaled ceiling on how large each candidate position"
        " could be — decision support, never an order. The warning marker"
        " means the cap exceeds buying power.",
    ),
    (
        "plan-001-report",
        "Signal recommendations",
        "scorer.db",
        _signal_recommendation,
        "Track record",
        "The verdict on each signal, graded against the BASE RATE rather than"
        " a coin flip: a randomly chosen scored ticker beat its benchmark only"
        " ~40% of the time over these windows, so a 61% hit-rate can still be"
        " worth nothing. ‘Keep’ means the whole confidence range sits above"
        " that baseline, ‘anti-signal’ entirely below it, ‘watch’"
        " straddling. Several signals are graded at once, so a few clear the"
        " bar by luck — hold every verdict loosely. Re-weighting the catalog"
        " is always a human decision; nothing here feeds back.",
    ),
    (
        "plan-004-scorecard",
        "Trader scorecard",
        "scorer.db",
        _trader_scorecard,
        "Track record",
        "A plain-text report grading past decision quality: did filtering"
        " help, what did execution cost, how did unrecommended (freelance)"
        " trades do.",
    ),
    (
        "candidate-efficacy",
        "Candidates screen edge",
        "scorer.db",
        _candidate_efficacy,
        "Track record",
        "A name's first ENTRY onto the candidates reading list starts a"
        " stopwatch: its 21- and 63-trading-day return is measured against"
        " SPY, split by which dislocation door let it in — oversold RSI, a"
        " price drawdown, or both at once. This grades TIMING only, never"
        " the multi-year quality thesis behind the pick, and none of it"
        " feeds back into the screen's own gates.",
    ),
]


# --- Hero bullets (Task 8) --------------------------------------------------
# Ports sections.py:1184-1343's `_hero_*_clause` SQL into plain dicts for
# narrative.hero_bullets. Each fetch is its own try/except (mirrors
# sections.py's `_hero_clause` wrapper) so a missing/unreadable advisor.db
# drops only the book/disagreement bullets, never the whole hero.


def _hero_regime_input(data_dir: str) -> dict[str, Any] | None:
    """{"regime", "streak_nights", "vix"} from composite.db, or None on any
    failure (missing DB, no snapshot yet) — ports `_hero_regime_clause`."""
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            r = conn.execute("SELECT regime, vix FROM v_latest_regime").fetchone()
            if r is None:
                return None
            return {
                "regime": r["regime"],
                "streak_nights": _streak_nights(conn),
                "vix": r["vix"],
            }
        finally:
            conn.close()
    except Exception:
        return None


def _hero_book_input(data_dir: str) -> dict[str, Any] | None:
    """{"heat_pct", "positions"} from advisor.db — ports `_hero_book_clause`.
    `heat_pct` is percent-scale (the view's fraction × 100), matching
    narrative.hero_bullets' documented contract, same unit trap as the
    your-book strand's section exporters above."""
    try:
        conn = _ro(data_dir, "advisor.db")
        try:
            r = conn.execute("SELECT heat_pct, positions FROM v_book_heat").fetchone()
            if r is None:
                return None
            heat_pct = None if r["heat_pct"] is None else r["heat_pct"] * 100
            return {"heat_pct": heat_pct, "positions": r["positions"] or 0}
        finally:
            conn.close()
    except Exception:
        return None


def _hero_disagreements_input(data_dir: str) -> list[str] | None:
    """Strong-only disagreement symbols from advisor.db — ports
    `_hero_disagreement_clause`. The strength judgment itself already lives
    in v_disagreements.strong (STRONG_MIN_ABS_SCORE/STRONG_MIN_TOTAL,
    computed in SQL by advisor/db.py); this just filters on it. None on any
    failure — narrative.hero_bullets treats None the same as an empty list
    (falls through to the flagged-tickers bullet)."""
    try:
        conn = _ro(data_dir, "advisor.db")
        try:
            rows = conn.execute(
                "SELECT symbol FROM v_disagreements WHERE strong ORDER BY symbol"
            ).fetchall()
            return [r["symbol"] for r in rows]
        finally:
            conn.close()
    except Exception:
        return None


def _hero(data_dir: str) -> dict[str, Any]:
    return {
        "bullets": narrative.hero_bullets(
            regime=_hero_regime_input(data_dir),
            book=_hero_book_input(data_dir),
            disagreements=_hero_disagreements_input(data_dir),
            flagged=flagged_tickers(data_dir),
        )
    }


# --- Ticker drill-down (Task 8) ---------------------------------------------
# Bounded to headline_symbols(composite) ∪ held (advisor v_latest_heat) ∪
# journal (scorer decisions symbols) — NOT the full ~1,017-row scorecard
# (same size-blocker review note as `headline_symbols`'s docstring). Each of
# the three source DBs is its own try/except: a missing scorer.db degrades
# `verdicts`/`fills` to `[]` for every ticker rather than blanking the whole
# `tickers` dict, and a missing composite/advisor.db behaves the same way
# for the fields only it can supply.

_TICKER_SCORE_HISTORY_LIMIT = 90


def _ticker_universe(data_dir: str) -> set[str]:
    headline: set[str] = set()
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            headline = headline_symbols(conn)
        finally:
            conn.close()
    except Exception:
        pass

    held: set[str] = set()
    try:
        conn = _ro(data_dir, "advisor.db")
        try:
            held = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_latest_heat")}
        finally:
            conn.close()
    except Exception:
        pass

    journal: set[str] = set()
    try:
        conn = _ro(data_dir, "scorer.db")
        try:
            journal = {r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM decisions")}
        finally:
            conn.close()
    except Exception:
        pass

    return headline | held | journal


def _empty_ticker_detail() -> dict[str, Any]:
    return {"score_history": [], "signals": [], "verdicts": [], "fills": [], "position": None}


def _fill_composite_ticker_fields(
    data_dir: str, symbols: set[str], tickers: dict[str, dict[str, Any]]
) -> None:
    """score_history (last 90, {"date", "score_sum"}) and signals
    ({"signal", "score", "raw_value"}) — one grouped query per field, never
    one query per symbol (same pattern as `_scorecard`'s history fetch)."""
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            marks = ",".join("?" * len(symbols))
            syms = tuple(symbols)

            history: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
            for r in conn.execute(
                f"SELECT symbol, captured_at, score_sum FROM v_score_history"
                f" WHERE symbol IN ({marks}) ORDER BY captured_at ASC",
                syms,
            ):
                history[r["symbol"]].append(
                    {"date": phx_date(r["captured_at"]), "score_sum": r["score_sum"]}
                )

            signals: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
            for r in conn.execute(
                f"SELECT entity AS symbol, signal_id, score, raw_value FROM v_signal_detail"
                f" WHERE entity IN ({marks})",
                syms,
            ):
                signals[r["symbol"]].append(
                    {"signal": r["signal_id"], "score": r["score"], "raw_value": r["raw_value"]}
                )
        finally:
            conn.close()
    except Exception:
        return
    for sym in symbols:
        tickers[sym]["score_history"] = history[sym][-_TICKER_SCORE_HISTORY_LIMIT:]
        tickers[sym]["signals"] = signals[sym]


def _fill_advisor_ticker_fields(
    data_dir: str, symbols: set[str], tickers: dict[str, dict[str, Any]]
) -> None:
    """position ({"quantity", "market_value", "heat_dollars", "heat_pct"} |
    None) from advisor.db's v_latest_heat. heat_pct is percent-scale (the
    view's fraction × 100), same unit trap as the your-book strand above."""
    try:
        conn = _ro(data_dir, "advisor.db")
        try:
            marks = ",".join("?" * len(symbols))
            rows = {
                r["symbol"]: r
                for r in conn.execute(
                    "SELECT symbol, quantity, market_value, heat_dollars, heat_pct"
                    f" FROM v_latest_heat WHERE symbol IN ({marks})",
                    tuple(symbols),
                )
            }
        finally:
            conn.close()
    except Exception:
        return
    for sym in symbols:
        r = rows.get(sym)
        if r is None:
            continue
        tickers[sym]["position"] = {
            "quantity": r["quantity"],
            "market_value": r["market_value"],
            "heat_dollars": r["heat_dollars"],
            "heat_pct": None if r["heat_pct"] is None else r["heat_pct"] * 100,
        }


def _fill_scorer_ticker_fields(
    data_dir: str, symbols: set[str], tickers: dict[str, dict[str, Any]]
) -> None:
    """verdicts ({"date", "verdict", "thesis_path"}) from research_verdicts
    and fills ({"action", "side", "fill_date", "fill_price", "quantity",
    "exit_fill_date", "exit_fill_price", "opinion_score_sum"}) from
    decisions — an explicit column list, NEVER `SELECT *`: `decisions` also
    carries note/order_ref/exit_order_ref/placed_agent, which Task 7's
    privacy walk test bans from this subtree. research_verdicts' own `note`
    column is left out the same way."""
    try:
        conn = _ro(data_dir, "scorer.db")
        try:
            marks = ",".join("?" * len(symbols))
            syms = tuple(symbols)

            verdicts: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
            for r in conn.execute(
                "SELECT symbol, verdict, verdict_date, doc FROM research_verdicts"
                f" WHERE symbol IN ({marks}) ORDER BY verdict_date DESC",
                syms,
            ):
                verdicts[r["symbol"]].append(
                    {
                        "date": r["verdict_date"],
                        "verdict": r["verdict"],
                        "thesis_path": _verdict_thesis_path(r["doc"]),
                    }
                )

            fills: dict[str, list[dict[str, Any]]] = {s: [] for s in symbols}
            for r in conn.execute(
                "SELECT symbol, action, side, fill_date, fill_price, quantity,"
                " exit_fill_date, exit_fill_price, opinion_score_sum FROM decisions"
                f" WHERE symbol IN ({marks}) ORDER BY fill_date",
                syms,
            ):
                fills[r["symbol"]].append(
                    {
                        "action": r["action"],
                        "side": r["side"],
                        "fill_date": r["fill_date"],
                        "fill_price": r["fill_price"],
                        "quantity": r["quantity"],
                        "exit_fill_date": r["exit_fill_date"],
                        "exit_fill_price": r["exit_fill_price"],
                        "opinion_score_sum": r["opinion_score_sum"],
                    }
                )
        finally:
            conn.close()
    except Exception:
        return
    for sym in symbols:
        tickers[sym]["verdicts"] = verdicts[sym]
        tickers[sym]["fills"] = fills[sym]


def _tickers(data_dir: str) -> dict[str, dict[str, Any]]:
    symbols = _ticker_universe(data_dir)
    tickers: dict[str, dict[str, Any]] = {s: _empty_ticker_detail() for s in symbols}
    if not symbols:
        return tickers
    _fill_composite_ticker_fields(data_dir, symbols, tickers)
    _fill_advisor_ticker_fields(data_dir, symbols, tickers)
    _fill_scorer_ticker_fields(data_dir, symbols, tickers)
    return tickers


def _ro(data_dir: str, db_name: str) -> sqlite3.Connection:
    """Read-only connection to `<data_dir>/<db_name>` — never write access."""
    conn = sqlite3.connect(f"file:{Path(data_dir) / db_name}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot_number(data_dir: str) -> int | None:
    """The composite.db snapshot id for the masthead. Guarded on its own: a
    missing DB, no rows, or a NULL MAX(id) all mean "omit the snapshot
    number" — never fabricate or coerce a placeholder value."""
    try:
        conn = _ro(data_dir, "composite.db")
        try:
            row = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()
        finally:
            conn.close()
    except Exception:
        return None
    if row is None or row[0] is None:
        return None
    return int(row[0])


def _edition_date(now_iso: str) -> str:
    """'July 8, 2026' — the Phoenix calendar date, not the UTC one (the
    9:13pm render slot is already tomorrow in UTC). Unlike the legacy
    `_edition_date` in sections.py (hair-space HTML entities meant for the
    masthead's styling), this is plain text bound for JSON — an explicit
    MONTHS table, no locale-dependent `%B`, no platform-dependent `%-d`. An
    unparseable now_iso degrades to the raw input rather than raising — the
    export must always produce something."""
    try:
        y, m, d = phx_date(now_iso).split("-")
        return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:
        return now_iso


def export_data(data_dir: str, now_iso: str, repo_root: str | None = None) -> dict[str, Any]:
    """The full data.json document. `repo_root` (default: this repo's real
    root) is where docs/GLOSSARY.md is resolved from — kept as an explicit
    parameter, not a hardcoded relative path, so tests can point it at a
    tmp_path sandbox instead of the live repo. File-backed sections (e.g.
    research/verdicts.log) resolve their own path from `data_dir`'s sibling
    directly, not from `repo_root` — see the branch below."""
    root = Path(repo_root) if repo_root is not None else _REPO_ROOT

    sections: dict[str, Any] = {}
    for sid, title, db_name, fn, kicker, note in SECTION_EXPORTERS:
        header = {"title": title, "kicker": kicker, "note": note}
        try:
            if db_name.endswith(".db"):
                conn = _ro(data_dir, db_name)
                try:
                    body = fn(conn, now_iso)
                finally:
                    conn.close()
            else:
                # File-backed section (e.g. research/verdicts.log): fn
                # resolves its own path from data_dir's sibling, mirroring
                # sections.py's `_render_section` (`fn(data_dir, now_iso)`)
                # and the populated_data_dir fixture's tmp_path/data +
                # tmp_path/research layout — NOT repo_root, which only
                # governs the glossary read below.
                body = fn(data_dir, now_iso)
        except Exception as e:  # missing DB, dropped view — degrade, never crash
            body = {"error": f"unavailable ({db_name}: {type(e).__name__})"}
        sections[sid] = {**header, **body}

    return {
        "schema_version": 1,
        "generated_at": now_iso,
        "edition_date": _edition_date(now_iso),
        "snapshot_number": _snapshot_number(data_dir),
        "hero": _hero(data_dir),
        "sections": sections,
        "tickers": _tickers(data_dir),
        "glossary": load_glossary(root / "docs" / "GLOSSARY.md"),
    }


def export_json(data_dir: str, now_iso: str, repo_root: str | None = None) -> str:
    """Compact-serialized `export_data(...)` — Task 9's entrypoint consumes
    this exact name/signature so the CLI and tests never diverge on
    serialization (separators, key order via dict insertion order)."""
    return json.dumps(export_data(data_dir, now_iso, repo_root), separators=(",", ":"))
