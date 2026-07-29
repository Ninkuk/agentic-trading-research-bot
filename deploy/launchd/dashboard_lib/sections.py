"""Generate the zero-dependency nightly HTML dashboard.

A single self-contained static HTML file summarizing the pipeline's accumulated
state — regime, ticker scorecard, signal efficacy/recommendations, bucket
performance, the human-filter tally, and the advisor book — for a human to
review before the weekly reweighting decision. Opens locally (double-click,
file://); no server, no auth, no JS framework, no CDN, no external asset of any
kind (CLAUDE.md's stdlib-only constraint, extended to the emitted HTML).

Mirrors deploy/launchd/daily_summary.py: reads each source DB with
`sqlite3.connect("file:data/<db>?mode=ro", uri=True)`, strictly read-only, and
wraps every section in its own try/except so a missing DB, a dropped view, or
zero rows degrades to a visible "unavailable"/"no rows yet" note rather than a
crash. A total failure still writes an explicit "generation failed" page — a
stale dashboard with no error banner would be worse than an honest one.

Wired as its own launchd slot at 9:13pm (after advisor 9:12, before the
daily-summary ntfy at 9:15) so it reflects tonight's rows; being a separate
process, a bug here can never delay or suppress that health alert.
"""

import os
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from dashboard_lib.js import SCRIPT
from dashboard_lib.style import _STYLE
from dashboard_lib.svg import (
    _esc,
    _num,
    _pct,
    _signed_num,
    _sparkline_svg,
    _yn,
    dot_ci_svg,
    regime_strip,
    score_spark,
    tile_spark,
)
from sources.combiners.advisor.catalog import STOP_ATR_MULTIPLE  # noqa: E402
from sources.combiners.composite import candidates  # noqa: E402
from sources.combiners.scorer import scorecard  # noqa: E402
from sources.combiners.scorer.db import (  # noqa: E402
    FLAG_MIN_ABS_SCORE,
    FLAG_MIN_TOTAL,
    RELIABLE_MIN_BLOCKS,
)
from sources.common.clock import phx_date  # noqa: E402

DATA_DIR = "data"
OUTPUT_PATH = "reports/dashboard.html"

# Denominator for the diverging score bar. Pinned at 5, not derived at runtime:
#   * it reproduces the mockup exactly (+5 -> width:50%, +3 -> width:30%);
#   * it sits just above the |score_sum| >= 4 flag threshold (composite/db.py:79),
#     so a nearly-full bar reads as "this one crossed the flag line";
#   * measured 2026-07-08 over all 6,215 rows of composite.db ticker_scores, the
#     observed max |score_sum| is 3 and max total is 4, so nothing saturates today.
# The theoretical bound is 2 * total (each signal votes -2..+2, catalog.py:2), i.e.
# 8 at total=4. Scores past 5 therefore CAN saturate the bar in principle; that is
# acceptable because the exact signed number is always rendered as visible text and
# repeated in the tooltip. A fixed cap (rather than per-row 2*total) is what makes
# bars comparable down the column.
_SCORE_BAR_MAX = 5

_REPO_URL = "https://github.com/Ninkuk/agentic-trading-research-bot"

_INTRO = (
    '<details class="intro"><summary>First time here? What this page is</summary>'
    "<p>Every day, small programs collect numbers from official public sources"
    " — the Federal Reserve, the SEC, the Treasury, and more — and every"
    " evening they write this page: the market's overall mood, a scorecard of"
    " stocks whose numbers stand out, and a running record of how past"
    " opinions worked out. Nothing here places a trade; a human makes every"
    " decision. The code and data pipeline are developed in the open: read"
    f' <a href="{_REPO_URL}">how it works</a> or the plain-English'
    f' <a href="{_REPO_URL}/blob/main/docs/GLOSSARY.md">glossary</a>.</p>'
    "</details>"
)


# --- pure formatting helpers (no I/O; unit-tested without a DB) -------------


def _badge(text: str, cls: str) -> str:
    """A verdict pill (`.pill.{cls}` — see _STYLE's ins/weak/watch/keep/anti rules)."""
    return f'<span class="pill {cls}">{_esc(text)}</span>'


def _regime_badge(regime) -> str:
    label = {"risk_on": "risk-on", "risk_off": "risk-off", "mixed": "mixed"}.get(
        regime or "", "unknown"
    )
    cls = {"risk_on": "tag-on", "risk_off": "tag-off"}.get(regime or "", "tag-dim")
    return f'<span class="{cls}">{_esc(label)}</span>'


def _rec_badge(rec) -> str:
    cls = {
        "keep": "keep",
        "watch": "watch",
        "anti-signal": "anti",
        "insufficient evidence": "ins",
    }.get(rec or "", "ins")
    return _badge(rec or "insufficient evidence", cls)


def _reliable_badge(reliable) -> str:
    return (
        '<span class="tag-on">reliable</span>' if reliable else '<span class="tag-dim">thin</span>'
    )


def _table(
    headers: list[str],
    body_rows: list[str],
    empty: str = "no rows yet",
    numeric_from: int = 0,
    sortable: set[int] | None = None,
) -> str:
    """`sortable` restricts which numeric_from-and-later columns get the JS
    sort hook (`data-num`) — pass the set of column indices that actually
    sort as numbers. None (default) keeps every numeric_from column
    sortable, the prior behavior. A column excluded from `sortable` still
    gets `class="num"` (right-aligned to match its `.num` cells) — it just
    isn't wired for the header-click sort, because its values aren't scalar
    (e.g. the scorecard's trend sparkline, split count, held checkmark)."""
    if not body_rows:
        return f'<p class="empty">{_esc(empty)}</p>'

    def _head_cell(i: int, h: str) -> str:
        if i < numeric_from:
            return f"<th>{_esc(h)}</th>"
        attr = ' data-num="1"' if sortable is None or i in sortable else ""
        return f'<th class="num"{attr}>{_esc(h)}</th>'

    head = "".join(_head_cell(i, h) for i, h in enumerate(headers))
    table = f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    return f'<div class="twrap">{table}</div>'


# Cell values built by our own helpers (never user/DB-controlled markup) may
# pass through _cells unescaped; anything else is treated as plain text and
# _esc'd. Explicit allowlist rather than "any string starting with '<'".
_SAFE_HTML_PREFIXES = ("<span", "<div", "<svg", "<circle", "<polyline", "<p")


def _cells(*values, numeric_from: int = 0) -> str:
    """Row of <td>s; cells at index >= numeric_from get the tabular-nums class."""
    out = []
    for i, v in enumerate(values):
        cls = ' class="num"' if i >= numeric_from else ""
        if isinstance(v, str) and v.startswith(_SAFE_HTML_PREFIXES):
            content = v
        else:
            content = _esc(v)
        out.append(f"<td{cls}>{content}</td>")
    return "<tr>" + "".join(out) + "</tr>"


def _stat_tiles(pairs: list[tuple[str, str]]) -> str:
    tiles = "".join(
        f'<div class="tile"><div class="v">{v}</div><div class="k">{_esc(k)}</div></div>'
        for k, v in pairs
    )
    return f'<div class="tiles">{tiles}</div>'


def _drivers_table(rows: list[tuple[str, str]]) -> str:
    """The regime section's <details> breakdown: a plain label/value table,
    no header row (mirrors the mockup's `table.drivers`)."""
    body = "".join(f'<tr><td>{_esc(k)}</td><td class="num">{v}</td></tr>' for k, v in rows)
    return f'<div class="twrap"><table class="drivers"><tbody>{body}</tbody></table></div>'


def _score_cell(score_sum: int, bullish: int, bearish: int, flagged: bool) -> str:
    """The scorecard's signed-number + diverging-bar cell. Bar width is
    clamped to _SCORE_BAR_MAX so no row's bar can exceed the track — the
    exact signed number is always shown as visible text too."""
    sign_cls = "up" if score_sum >= 0 else "down"
    bar_cls = "p" if score_sum >= 0 else "n"
    width = min(abs(score_sum) / _SCORE_BAR_MAX, 1) * 50
    total_votes = bullish + bearish
    vote_word = "vote" if total_votes == 1 else "votes"
    flag_suffix = " · flagged" if flagged else ""
    title = f"summed score {score_sum:+d} · {bullish} bullish, {bearish} bearish {vote_word}{flag_suffix}"
    return (
        f'<div class="scorecell"><span class="sval {sign_cls}">{score_sum:+d}</span>'
        f'<div class="sbar" title="{_esc(title)}">'
        f'<i class="{bar_cls}" style="width:{width:.0f}%"></i></div></div>'
    )


def _reliability_meter(n_bench: int | None, threshold: int, unit: str = "benchmarked calls") -> str:
    """The evidence meter: how far the sample (default n_bench — NOT
    n_matured, see scorer/db.py's reliable-gates-on-n_bench note) has
    filled toward the reliability floor. The recommendation table passes
    n_blocks/"independent windows": blocks are the binding gate, and a
    meter on rows would read 100% off one rolling episode."""
    n = n_bench or 0
    pct = min(n / threshold, 1) * 100 if threshold else 0.0
    low_cls = " low" if n < threshold else ""
    status = "not enough yet" if n < threshold else "enough to grade"
    title = f"{n} {unit}, threshold {threshold} — {status}"
    return (
        f'<div class="meter" title="{_esc(title)}"><div class="trk">'
        f'<div class="fil{low_cls}" style="width:{pct:.0f}%"></div></div>'
        f'<div class="lab">{n} / {threshold}</div></div>'
    )


def _ci_bar(hit_rate, ci_lo, ci_hi) -> str:
    """The hit-rate confidence-interval bar: a dot-and-whisker SVG plot.
    NULLs (no bench sample yet) degrade to a plain dash — no crash."""
    return dot_ci_svg(hit_rate, ci_lo, ci_hi)


def _view_table(
    conn,
    sql: str,
    empty: str,
    fmt: dict[str, Callable[[object], str]] | None = None,
) -> str:
    """Render every column a query returns, headers taken from
    `cursor.description` — avoids hardcoding column names, so this works
    against any view without coupling the page to its exact shape.

    Alignment is decided per column FROM THE DATA, not by position: a column
    is numeric (right-aligned, `class="num"`) only if its non-NULL values are
    all int/float (bools excluded, and an all-NULL column counts as
    non-numeric). A positional `numeric_from` can't express "columns 2, 4, 5",
    which is exactly what a view like v_basis_breaks (text, date, num, date,
    num, num) needs. `fmt` optionally maps a column name to a formatter (e.g.
    `_pct`) applied before escaping; a formatted column is treated as numeric
    for alignment. Every value is `_esc`'d — nothing from a view is trusted."""
    fmt = fmt or {}
    cur = conn.execute(sql)
    headers = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        return f'<p class="empty">{_esc(empty)}</p>'
    numeric = []
    for j, h in enumerate(headers):
        if h in fmt:
            numeric.append(True)
            continue
        vals = [row[j] for row in rows if row[j] is not None]
        numeric.append(
            bool(vals) and all(isinstance(v, int | float) and not isinstance(v, bool) for v in vals)
        )
    head = "".join(
        f'<th class="num" data-num="1">{_esc(h)}</th>' if numeric[j] else f"<th>{_esc(h)}</th>"
        for j, h in enumerate(headers)
    )
    body_rows = []
    for row in rows:
        tds = []
        for j, h in enumerate(headers):
            raw = fmt[h](row[j]) if h in fmt else row[j]
            cls = ' class="num"' if numeric[j] else ""
            tds.append(f"<td{cls}>{_esc(raw)}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")
    table = f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    return f'<div class="twrap">{table}</div>'


def _regime(conn, now_iso) -> str:
    r = conn.execute(
        "SELECT regime, vix, inputs_present, inputs_expected,"
        " t10y2y, curve_inverted, hy_spread, vix_backwardation,"
        " equity_pcr_pctile, in_fomc_blackout, imminent_high_impact,"
        " days_to_opex, rrp_change, tga_change FROM v_latest_regime"
    ).fetchone()
    if not r:
        return '<p class="empty">no regime yet</p>'
    tiles = _stat_tiles(
        [
            ("regime", _regime_badge(r["regime"])),
            ("VIX", _num(r["vix"], 1)),
            ("inputs", f"{r['inputs_present']}/{r['inputs_expected']}"),
        ]
    )
    drivers = _drivers_table(
        [
            ("VIX level", _num(r["vix"], 1)),
            ("10y–2y spread", _signed_num(r["t10y2y"], 2)),
            ("yield curve inverted", _yn(r["curve_inverted"])),
            ("high-yield spread", _num(r["hy_spread"], 2)),
            ("VIX backwardation", _yn(r["vix_backwardation"])),
            (
                "put / call percentile",
                # equity_pcr_pctile is already stored 0-100 (composite/catalog.py's
                # cboe_equity_pcr is `100.0 * COUNT/COUNT`) — _pct expects a 0-1
                # fraction and would multiply by 100 a second time, so format
                # in-line rather than reuse it.
                "—" if r["equity_pcr_pctile"] is None else f"{r['equity_pcr_pctile']:.1f}%",
            ),
            ("FOMC blackout", _yn(r["in_fomc_blackout"])),
            ("imminent high-impact event", _yn(r["imminent_high_impact"])),
            (
                "days to options expiry",
                "—" if r["days_to_opex"] is None else str(r["days_to_opex"]),
            ),
            ("Fed RRP change", _signed_num(r["rrp_change"])),
            ("Treasury TGA change", _signed_num(r["tga_change"])),
        ]
    )
    return tiles + f"<details><summary>All regime inputs</summary>{drivers}</details>"


def _regime_timeline(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT s.captured_at, m.regime, m.vix FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at DESC LIMIT 60"
    ).fetchall()
    days = [(phx_date(r["captured_at"]), r["regime"]) for r in reversed(rows)]
    strip = regime_strip(days)
    spark = _sparkline_svg([(r["regime"], r["vix"]) for r in rows[:30]])
    return f'<div class="stripwrap">{strip}</div>{spark}'


_FRED_DRIVER_SERIES = [
    ("T10Y2Y", "10y–2y spread", 2),
    ("BAMLH0A0HYM2", "high-yield spread", 2),
    ("VIXCLS", "VIX", 1),
]


def _macro_drivers(conn, now_iso) -> str:
    tiles = []
    for sid, label, dp in _FRED_DRIVER_SERIES:
        rows = conn.execute(
            "SELECT date, value FROM observations WHERE series_id = ?"
            " AND value IS NOT NULL ORDER BY date DESC LIMIT 90",
            (sid,),
        ).fetchall()
        values = [r["value"] for r in reversed(rows)]
        if not values:
            tiles.append(
                f'<div class="tile"><div class="v">—</div><div class="k">{_esc(label)}</div></div>'
            )
            continue
        latest = values[-1]
        delta = latest - values[-2] if len(values) > 1 else None
        delta_txt = "" if delta is None else f' <span class="d">{_signed_num(delta, dp)}</span>'
        tiles.append(
            f'<div class="tile"><div class="v">{_num(latest, dp)}{delta_txt}</div>'
            f'{tile_spark(values)}<div class="k">{_esc(label)}</div></div>'
        )
    return f'<div class="tiles">{"".join(tiles)}</div>'


_SCORECARD_HEADERS = [
    "symbol",
    "score",
    "trend",
    "split (bull/bear)",
    "coverage",
    "data age",
    "held",
]
_SCORECARD_COLS = (
    "symbol, score_sum, total, coverage, in_portfolio, bullish, bearish, worst_staleness_days"
)


# _scorecard's numeric_from=1 columns are score(1), trend(2), split(3),
# coverage(4), data age(5), held(6). Only score/coverage/data age are
# actual scalars fit for the JS header-click sort; trend is an SVG
# sparkline, split is a "b / b" string, and held is a checkmark-or-blank —
# all three sort as nonsense text if wired up, so they keep the `.num`
# right-alignment (via numeric_from) without the `data-num` sort hook.
_SCORECARD_SORTABLE = {1, 4, 5}


def _scorecard_row(r, flagged: set, history: dict[str, list[int]] | None) -> str:
    trend = score_spark(history.get(r["symbol"], [])) if history is not None else "—"
    cell = _cells(
        f'<span class="sym">{_esc(r["symbol"])}</span>',
        _score_cell(r["score_sum"], r["bullish"], r["bearish"], r["symbol"] in flagged),
        trend,
        f"{r['bullish']} / {r['bearish']}",
        _pct(r["coverage"]),
        "—" if r["worst_staleness_days"] is None else f"{r['worst_staleness_days']:.1f}d",
        "✓" if r["in_portfolio"] else "",
        numeric_from=1,
    )
    return cell.replace("<tr>", '<tr class="flag">') if r["symbol"] in flagged else cell


def _scorecard(conn, now_iso) -> str:
    headline_rows = conn.execute(
        f"SELECT {_SCORECARD_COLS} FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC LIMIT 15"
    ).fetchall()
    flagged = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_flagged")}

    # v_flagged (|score_sum| >= 3 AND total >= 2) is not implied by the
    # headline's ORDER BY ABS(score_sum) DESC LIMIT 15 — total is a second,
    # independent gate, so a high-|score_sum|-but-low-total unflagged row can
    # outrank a flagged one and push it past rank 15. Union in any flagged
    # symbol the headline query missed, rather than raising the limit.
    headline_symbols = {r["symbol"] for r in headline_rows}
    missing_flagged = flagged - headline_symbols
    appended_rows: list = []
    if missing_flagged:
        placeholders = ",".join("?" for _ in missing_flagged)
        appended_rows = conn.execute(
            f"SELECT {_SCORECARD_COLS} FROM v_latest_scorecard"
            f" WHERE symbol IN ({placeholders}) ORDER BY ABS(score_sum) DESC",
            tuple(missing_flagged),
        ).fetchall()

    # Trend sparklines are headline + appended-flagged only (never the
    # potentially-hundreds-of-rows expander below — one SVG per expander row
    # would add ~1MB to a page published nightly). One grouped query covers
    # every sparklined row, never one query per row. Every shown symbol
    # defaults to [] so a symbol with no/thin history still gets a row —
    # score_spark itself degrades <2 points to "no data".
    shown = [r["symbol"] for r in (*headline_rows, *appended_rows)]
    history: dict[str, list[int]] = {s: [] for s in shown}
    if shown:
        marks = ",".join("?" * len(shown))
        for r in conn.execute(
            f"SELECT symbol, score_sum FROM v_score_history"
            f" WHERE symbol IN ({marks}) ORDER BY captured_at ASC",
            shown,
        ):
            history[r["symbol"]].append(r["score_sum"])
    history = {s: v[-30:] for s, v in history.items()}  # score_spark degrades past ~56 points

    body = [_scorecard_row(r, flagged, history) for r in (*headline_rows, *appended_rows)]
    filter_box = (
        '<input id="tickfilter" type="search" placeholder="filter tickers"'
        ' aria-label="filter tickers">'
    )
    headline = filter_box + _table(
        _SCORECARD_HEADERS, body, numeric_from=1, sortable=_SCORECARD_SORTABLE
    )

    all_rows = conn.execute(
        f"SELECT {_SCORECARD_COLS} FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC"
    ).fetchall()
    all_body = [_scorecard_row(r, flagged, history=None) for r in all_rows]
    expander = (
        f"<details><summary>Show all {len(all_rows)} scored tickers</summary>"
        f"{_table(_SCORECARD_HEADERS, all_body, numeric_from=1, sortable=_SCORECARD_SORTABLE)}"
        "</details>"
    )
    return headline + expander


# `hit rate` alone is what made si_spike read as the strongest signal in the
# system: 61.1% looks decisive until you see that a randomly chosen scored
# ticker beat SPY only 40.3% of the time over the same window. `null` is that
# base rate, resolved per row from the signal's own direction; `edge` is the
# difference, and it is the only column here worth acting on.
_EFFICACY_HEADERS = [
    "signal",
    "via",
    "horizon",
    "n",
    "blocks",
    "dir excess",
    "hit rate",
    "null",
    "edge",
    "",
]
_EFFICACY_COLS = (
    "signal_id, via_crosswalk, horizon, n_bench, n_blocks,"
    " avg_directional_excess, hit_rate, null_rate, edge, reliable"
)


def _signed_pct(x, dp: int = 1) -> str:
    """Percentage carrying an explicit sign — an edge of -7.9% must never be
    mistaken for a magnitude."""
    return "—" if x is None else f"{x * 100:+.{dp}f}%"


def _efficacy_row(r) -> str:
    return _cells(
        r["signal_id"],
        "xw" if r["via_crosswalk"] else "direct",
        str(r["horizon"]),
        str(r["n_bench"]),
        str(r["n_blocks"]),
        _pct(r["avg_directional_excess"]),
        _pct(r["hit_rate"]),
        _pct(r["null_rate"]),
        _signed_pct(r["edge"]),
        _reliable_badge(r["reliable"]),
        numeric_from=2,
    )


def _signal_efficacy(conn, now_iso) -> str:
    rows = conn.execute(
        f"SELECT {_EFFICACY_COLS} FROM v_signal_efficacy"
        " ORDER BY reliable DESC, n_matured DESC LIMIT 40"
    ).fetchall()
    headline = _table(
        _EFFICACY_HEADERS,
        [_efficacy_row(r) for r in rows],
        empty="no matured signal outcomes yet",
        numeric_from=2,
    )
    all_rows = conn.execute(
        f"SELECT {_EFFICACY_COLS} FROM v_signal_efficacy ORDER BY reliable DESC, n_bench DESC"
    ).fetchall()
    expander = (
        f"<details><summary>Show all {len(all_rows)} signals</summary>"
        f"{_table(_EFFICACY_HEADERS, [_efficacy_row(r) for r in all_rows], numeric_from=2)}"
        "</details>"
    )
    return headline + expander


def _bucket_performance(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT bucket, horizon, n_bench, avg_fwd_return, avg_excess,"
        " hit_rate, null_rate, edge, reliable FROM v_bucket_performance"
        " ORDER BY horizon, bucket"
    ).fetchall()
    body = [
        _cells(
            r["bucket"],
            str(r["horizon"]),
            str(r["n_bench"]),
            _pct(r["avg_fwd_return"]),
            _pct(r["avg_excess"]),
            _pct(r["hit_rate"]),
            _pct(r["null_rate"]),
            _signed_pct(r["edge"]),
            _reliable_badge(r["reliable"]),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(
        ["bucket", "horizon", "n", "fwd return", "excess", "hit rate", "null", "edge", ""],
        body,
        empty="no matured buckets yet",
        numeric_from=1,
    )


def _human_filter(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT response, horizon, n, avg_dir_excess, avg_fwd_return"
        " FROM v_human_filter ORDER BY horizon, response"
    ).fetchall()
    body = [
        _cells(
            r["response"],
            str(r["horizon"]),
            str(r["n"]),
            _pct(r["avg_dir_excess"]),
            _pct(r["avg_fwd_return"]),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(
        ["response", "horizon", "n", "dir excess", "fwd return"],
        body,
        empty="no matured flagged opinions yet",
        numeric_from=1,
    )


def _regime_performance(conn, now_iso) -> str:
    return _view_table(
        conn,
        "SELECT regime, horizon, n_matured, avg_bench_return, min_bench_return,"
        " max_bench_return FROM v_regime_performance ORDER BY horizon, regime",
        empty="no matured regime outcomes yet",
        # Returns are raw fractions in the view; render as % to match every
        # other return/rate on the page (_signal_efficacy, _bucket_performance,
        # _human_filter, _position_heat). horizon/n_matured stay bare counts.
        fmt={
            "avg_bench_return": _pct,
            "min_bench_return": _pct,
            "max_bench_return": _pct,
        },
    )


def _pending(conn, now_iso) -> str:
    total = conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0]
    table = _view_table(
        conn,
        "SELECT kind, composite_date, entity, horizon, entry_date FROM v_pending"
        " ORDER BY composite_date DESC LIMIT 100",
        empty="nothing pending — everything registered so far has matured",
    )
    if total > 100:
        cap = f'<p class="cap">Showing 100 of {total} pending — capped for readability.</p>'
        return cap + table
    return table


def _basis_breaks(conn, now_iso) -> str:
    return _view_table(
        conn,
        "SELECT symbol, prev_date, prev_close, price_date, close, ratio"
        " FROM v_basis_breaks ORDER BY price_date DESC",
        empty="no basis breaks detected — an empty table is the good outcome",
    )


def _signal_recommendation(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_blocks,"
        " avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, recommendation"
        " FROM v_signal_recommendation"
        " ORDER BY horizon, via_crosswalk, signal_id"
    ).fetchall()
    body = [
        _cells(
            r["signal_id"],
            "xw" if r["via_crosswalk"] else "direct",
            str(r["horizon"]),
            _reliability_meter(r["n_blocks"], RELIABLE_MIN_BLOCKS, "independent windows"),
            _pct(r["avg_directional_excess"]),
            _ci_bar(r["hit_rate"], r["hit_ci_lo"], r["hit_ci_hi"]),
            _rec_badge(r["recommendation"]),
            numeric_from=2,
        )
        for r in rows
    ]
    caveat = (
        '<p class="cap">Lead with n and the CI, not the excess. Several rows'
        " are graded at once — a few cross a 95% threshold by chance alone;"
        " hold every verdict loosely. Re-weighting stays a human decision.</p>"
    )
    return caveat + _table(
        ["signal", "via", "horizon", "evidence", "excess vs bench", "hit-rate (0–100%)", "verdict"],
        body,
        empty="insufficient evidence for every signal (young scorer) — expected",
        numeric_from=2,
    )


def _trader_scorecard(conn, now_iso) -> str:
    # Reuse the plan-004 report verbatim (single source of truth) in a <pre>.
    return f"<pre>{_esc(scorecard.build_report(conn, now_iso))}</pre>"


def _book_heat(conn, now_iso) -> str:
    r = conn.execute(
        "SELECT positions, heat_pct, heat_coverage, equity, sources_failed FROM v_book_heat"
    ).fetchone()
    if not r:
        return '<p class="empty">no advisor snapshot yet</p>'
    failed = r["sources_failed"] or 0
    failed_cls = "tag-off" if failed else "tag-dim"
    return _stat_tiles(
        [
            ("positions", str(r["positions"] or 0)),
            ("book heat", _pct(r["heat_pct"], 2)),
            ("coverage", _num(r["heat_coverage"], 2)),
            ("equity", f"${_num(r['equity'], 0)}"),
            ("sources failed", f'<span class="{failed_cls}">{failed}</span>'),
        ]
    )


def _group_heat(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT bet, group_name, members, symbols, heat_dollars, heat_pct FROM v_group_heat"
    ).fetchall()
    body = [
        _cells(
            r["bet"],
            str(r["members"]),
            r["symbols"] or "",
            f"${_num(r['heat_dollars'])}",
            _pct(r["heat_pct"], 2),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(["bet", "members", "symbols", "heat $", "heat %"], body, numeric_from=1)


def _position_heat(conn, now_iso) -> str:
    # The view's join-key column is internal bookkeeping and must never
    # reach the page — explicit column list, never SELECT *.
    rows = conn.execute(
        "SELECT symbol, group_name, quantity, market_value, price, heat_dollars,"
        " heat_pct, weight_pct, score_sum, atr_stale FROM v_latest_heat"
        " ORDER BY heat_dollars DESC"
    ).fetchall()
    body = [
        _cells(
            r["symbol"],
            r["group_name"] or "",
            _num(r["quantity"]),
            f"${_num(r['market_value'])}",
            f"${_num(r['price'])}",
            f"${_num(r['heat_dollars'])}",
            _pct(r["heat_pct"], 2),
            _pct(r["weight_pct"], 2),
            "—" if r["score_sum"] is None else f"{r['score_sum']:+d}",
            "⚠" if r["atr_stale"] else "",
            numeric_from=2,
        )
        for r in rows
    ]
    return _table(
        [
            "symbol",
            "group",
            "qty",
            "market value",
            "price",
            "heat $",
            "heat %",
            "weight %",
            "score",
            "stale?",
        ],
        body,
        empty="no positions with heat yet",
        numeric_from=2,
    )


def _disagreements(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT symbol, score_sum, group_name, strong FROM v_disagreements"
    ).fetchall()
    body = [
        _cells(
            r["symbol"],
            f"{r['score_sum']:+d}",
            r["group_name"] or "",
            _badge("STRONG", "anti") if r["strong"] else _badge("weak", "weak"),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(["symbol", "score", "group", ""], body, empty="no disagreements", numeric_from=1)


def _size_caps(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT symbol, direction, score_sum, cap_shares, cap_dollars,"
        " group_name, exceeds_buying_power FROM v_latest_caps"
    ).fetchall()
    body = [
        _cells(
            r["symbol"],
            r["direction"] or "",
            f"{r['score_sum']:+d}",
            _num(r["cap_shares"]),
            f"${_num(r['cap_dollars'])}",
            r["group_name"] or "",
            "⚠" if r["exceeds_buying_power"] else "",
            numeric_from=2,
        )
        for r in rows
    ]
    return _table(
        ["symbol", "dir", "score", "cap shares", "cap $", "group", "bp?"],
        body,
        empty="no caps tonight",
        numeric_from=2,
    )


_CANDIDATES_HEADERS = ["symbol", "sector", "cap $B", "roic %", "fcf yld %", "F", "rsi", "6m %"]
# The page is a report, not a push, but the whole screen is still long enough
# to bury everything under it; the CLI (`main.py candidates`) prints all of it.
_CANDIDATES_MAX = 15


def _candidates(conn, now_iso) -> str:
    """Quality-first research candidates from stocks.db.

    Reads the screen through `candidates.screen()` rather than restating its
    gates, so this page and the CLI can never disagree about what qualifies."""
    rows = candidates.screen(conn)
    data_date = candidates.snapshot_date(conn)
    body = [
        _cells(
            r["symbol"],
            (r["sector"] or "—"),
            _num(r["marketCap"] / 1e9, 1),
            _num(r["roic"], 1),
            _num(r["fcfYield"], 1),
            _num(r["fScore"], 0),
            _num(r["rsi"], 1),
            _num(r["ch6m"], 1),
            numeric_from=2,
        )
        for r in rows[:_CANDIDATES_MAX]
    ]
    table = _table(
        _CANDIDATES_HEADERS,
        body,
        empty="no names pass the screen tonight",
        numeric_from=2,
    )
    # Two facts a reader needs before the table means anything: how old the
    # data is (stocks.db does not refresh at weekends, so a Sunday edition is
    # showing Friday's RSI), and that nothing grades this list.
    stamp = f"stocks.db snapshot {candidates.data_age_label(data_date, now_iso)}"
    shown = min(len(rows), _CANDIDATES_MAX)
    # `.cap`, not `.read`: this is metadata ABOUT the table, not reading
    # matter. `.read` is the page's 22px serif prose style and made a row count
    # out-shout both the section heading and the data. Same convention _pending
    # uses for "Showing 100 of N". The disclaimer stays factual rather than
    # bold — the margin note beside this section already carries "Nothing
    # scores this list — it is a reading queue, not an opinion."
    caption = (
        f'<p class="cap">{len(rows)} name(s) pass'
        f"{f' · top {shown} shown' if len(rows) > shown else ''}"
        f" · {_esc(stamp)} · ungraded — row order is free-cash-flow yield,"
        " not conviction</p>"
    )
    return caption + table


SECTIONS = [
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
        "The colored strip is the regime verdict itself, one cell per day —"
        " green risk-on, red risk-off, gray mixed. How the market mood and"
        " the VIX fear gauge have moved across recent nightly snapshots."
        " Each dot is one snapshot; higher = more fear; color = that"
        " night's regime.",
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
        " to be marked down. Nothing scores this list — it is a reading queue,"
        " not an opinion.",
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
]
SECTION_IDS = [s[0] for s in SECTIONS]


def _ro(data_dir: str, db_name: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{os.path.join(data_dir, db_name)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _render_section(sid, title, db_name, fn, kicker, note, data_dir, now_iso) -> str:
    try:
        conn = _ro(data_dir, db_name)
        try:
            body = fn(conn, now_iso)
        finally:
            conn.close()
    except Exception as e:  # missing DB, dropped view — degrade, never crash
        print(f"{db_name}: unreadable ({type(e).__name__})", file=sys.stderr)
        body = f'<p class="unavailable">{_esc(db_name)}: unreadable ({type(e).__name__})</p>'
    # A degraded section still gets its margin note — what it *would* show
    # is useful precisely when it has no data.
    return (
        f'<section id="{sid}" class="ledger" aria-labelledby="s-{sid}">'
        f'<aside class="note"><p class="kicker">{_esc(kicker)}</p>'
        f'<h2 id="s-{sid}">{_esc(title)}</h2><p>{_esc(note)}</p></aside>'
        f'<div class="data">{body}</div></section>'
    )


def _edition_date(now_iso: str) -> str:
    """'2026 · 07 · 08' (hair-space separated, mockup style). The Phoenix date,
    not the UTC one — the 9:13pm render slot is already tomorrow in UTC. Total:
    any unparseable now_iso degrades to its bare date-ish prefix rather than
    raising — the masthead must always render something."""
    try:
        y, m, d = phx_date(now_iso).split("-")
    except Exception:
        return _esc(now_iso[:10])
    sep = "&#8202;·&#8202;"
    return f"{y}{sep}{m}{sep}{d}"


def _snapshot_number(data_dir: str) -> str | None:
    """The composite.db snapshot id for the masthead. Guarded on its own:
    a missing DB, no rows, or a NULL MAX(id) all mean "omit the snapshot
    line" — never fabricate or print a placeholder number."""
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
    return str(row[0])


_HERO_FALLBACK = '<p class="read">Tonight\'s summary is unavailable — see the sections below.</p>'


def _hero_regime_clause(data_dir: str) -> str:
    """Regime + VIX + input coverage. May raise (missing DB/view) — each
    clause is guarded independently by _hero_clause, so a raise here drops
    only this sentence, not the whole read. NULLs inside an existing row
    degrade to honest in-sentence text instead."""
    conn = _ro(data_dir, "composite.db")
    try:
        r = conn.execute(
            "SELECT regime, vix, inputs_present, inputs_expected FROM v_latest_regime"
        ).fetchone()
    finally:
        conn.close()
    if not r:
        return "Regime not yet computed for tonight."
    regime = r["regime"]
    cls = {"risk_on": "on", "risk_off": "off"}.get(regime or "", "mid")
    label = {"risk_on": "risk-on", "risk_off": "risk-off"}.get(regime or "", "mixed")
    mood = {
        "risk_on": "leaning into risky assets",
        "risk_off": "pulling back from risk",
    }.get(regime or "", "sending mixed signals")
    vix = r["vix"]
    if vix is None:
        vix_txt = "not available"
    else:
        temper = "calm" if vix < 20 else "elevated"
        vix_txt = f'{temper} at <span class="n">{_num(vix, 1)}</span>'
    present, expected = r["inputs_present"], r["inputs_expected"]
    if expected:
        if present == expected:
            info = (
                f' All <span class="n">{present} / {expected}</span> inputs reported'
                " in, so this read is on full information."
            )
        else:
            info = (
                f' Only <span class="n">{present} / {expected}</span> inputs reported'
                " in, so this read is on partial information."
            )
    else:
        info = ""
    return (
        f'The market is <b class="{cls}">{label}</b> — {mood} — with the VIX fear'
        f" gauge {vix_txt}.{info}"
    )


def _hero_book_clause(data_dir: str) -> str:
    """Book exposure + feed health from the advisor snapshot. Guarded per
    clause by _hero_clause — a failed advisor run drops this sentence but
    leaves the regime/flag lines intact."""
    conn = _ro(data_dir, "advisor.db")
    try:
        r = conn.execute(
            "SELECT positions, heat_pct, equity, sources_failed FROM v_book_heat"
        ).fetchone()
    finally:
        conn.close()
    if not r:
        return "Your book hasn't been captured yet tonight."
    positions = r["positions"] or 0
    pos_word = "position" if positions == 1 else "positions"
    equity = r["equity"]
    equity_txt = (
        "equity unknown" if equity is None else f'<span class="n">${_num(equity, 0)}</span> equity'
    )
    if r["heat_pct"] is None:
        risk_txt = ""
    else:
        risk_txt = f' — <span class="n">{_pct(r["heat_pct"], 2)}</span> of {equity_txt} at risk'
    failed = r["sources_failed"] or 0
    if failed == 0:
        failed_txt = "no feeds failed"
    else:
        feed_word = "feed" if failed == 1 else "feeds"
        failed_txt = f'<span class="n">{failed}</span> {feed_word} failed'
    return f'Your book holds <span class="n">{positions}</span> {pos_word}{risk_txt}, {failed_txt}.'


def _hero_disagreement_clause(data_dir: str) -> str | None:
    """The one holding (if exactly one) whose signal has turned against it,
    or an honest count otherwise. Guarded per clause by _hero_clause.

    Zero `v_disagreements` rows is ambiguous — it happens both when a book
    was captured with no disagreements AND when no book was captured at all.
    So we first confirm an advisor snapshot exists; with none we return None
    (this sentence is dropped) rather than claiming "nothing you own is being
    second-guessed", which would be false when we have no positions data."""
    conn = _ro(data_dir, "advisor.db")
    try:
        has_snapshot = conn.execute("SELECT 1 FROM v_latest_snapshot").fetchone() is not None
        rows = conn.execute(
            "SELECT symbol, strong FROM v_disagreements ORDER BY strong DESC, symbol"
        ).fetchall()
    finally:
        conn.close()
    if not has_snapshot:
        return None
    if not rows:
        return "No holdings to eye tonight — nothing you own is being second-guessed."
    if len(rows) == 1:
        strength = "strong" if rows[0]["strong"] else "weak"
        return (
            f'<b class="mid">One</b> holding to eye — <span class="n">{_esc(rows[0]["symbol"])}</span>'
            f" — now leans against your position ({strength})."
        )
    return f'<span class="n">{len(rows)}</span> holdings to eye tonight — see Disagreements below.'


def _hero_flag_clause(data_dir: str) -> str:
    """The single strongest-agreement flagged ticker tonight, if any.
    Guarded per clause by _hero_clause."""
    conn = _ro(data_dir, "composite.db")
    try:
        r = conn.execute(
            "SELECT symbol, score_sum FROM v_flagged ORDER BY ABS(score_sum) DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if not r:
        return "No flagged tickers tonight — no signal cluster crossed the agreement bar."
    return (
        f'Strongest agreement: <span class="n">{_esc(r["symbol"])}</span>, flagged at'
        f' <span class="n">{r["score_sum"]:+d}</span>.'
    )


def _hero_clause(fn, data_dir: str) -> str | None:
    """Run one clause helper, swallowing any failure to None so a single
    unreadable DB/view drops only that sentence — mirrors _render_section's
    per-section degradation. A clause may also return None to opt out
    honestly (e.g. no advisor snapshot)."""
    try:
        return fn(data_dir)
    except Exception as e:  # log by type only (an exception may carry an api_key)
        print(f"hero {fn.__name__}: unreadable ({type(e).__name__})", file=sys.stderr)
        return None


def _hero_read(data_dir: str, now_iso: str) -> str:
    """Tonight's plain-English read, assembled from the same views the
    sections below read. Degrades per clause, not all-or-nothing: each of
    the four clauses is guarded independently, so a failed advisor run (say)
    still leaves the regime and flagged-ticker lines. Only when *every*
    clause fails or opts out does it fall back to a single honest line."""
    clauses = [
        _hero_clause(fn, data_dir)
        for fn in (
            _hero_regime_clause,
            _hero_book_clause,
            _hero_disagreement_clause,
            _hero_flag_clause,
        )
    ]
    prose = " ".join(c for c in clauses if c)
    if not prose:
        return _HERO_FALLBACK
    return f'<p class="read">{prose}</p>'


def _jump_nav() -> str:
    """One link per section group, derived from SECTIONS' kicker field so the
    nav can never drift from the page."""
    first_sid: dict[str, str] = {}
    for sid, _title, _db, _fn, kicker, _note in SECTIONS:
        first_sid.setdefault(kicker, sid)
    links = "".join(f'<a href="#{sid}">{_esc(k)}</a>' for k, sid in first_sid.items())
    return f'<nav class="jump" aria-label="Sections">{links}</nav>'


def _footer() -> str:
    return (
        '<footer class="colophon"><div class="rule-thin"></div>'
        f'<p>Generated nightly (~9:13pm Phoenix) by <a href="{_REPO_URL}">'
        "code developed in the open</a> from official public sources. Research notes,"
        " not investment advice — nothing here places a trade, and a human"
        " makes every decision.</p></footer>"
    )


def build_page(data_dir: str, now_iso: str) -> str:
    edition_lines = [f"Edition <b>{_edition_date(now_iso)}</b>"]
    snapshot_no = _snapshot_number(data_dir)
    if snapshot_no is not None:
        edition_lines.append(f"Snapshot <b>#{_esc(snapshot_no)}</b>")
    edition_lines.append("Nothing here places a trade")

    hero_body = _hero_read(data_dir, now_iso)

    sections = "\n".join(
        _render_section(sid, title, db_name, fn, kicker, note, data_dir, now_iso)
        for sid, title, db_name, fn, kicker, note in SECTIONS
    )

    gloss = f"""<details style="margin-top:26px">
    <summary>The whole vocabulary, in one place</summary>
    <dl class="gloss">
      <dt>regime</dt><dd>The market's risk mood — risk-on, risk-off, or mixed — read from ten macro inputs.</dd>
      <dt>VIX</dt><dd>An index of expected volatility. A fear gauge: higher means more fear priced in.</dd>
      <dt>score</dt><dd>Sum of each signal's bullish (positive) and bearish (negative) reading for one stock.</dd>
      <dt>split (bull/bear)</dt><dd>How many signals voted each way. Can differ from the score, which is weighted.</dd>
      <dt>coverage</dt><dd>Share of all applicable signals that actually had an opinion on this stock.</dd>
      <dt>data age</dt><dd>How old the freshest-to-stalest input behind this row is, in days.</dd>
      <dt>held</dt><dd>A check mark means you currently own this stock.</dd>
      <dt>flagged &#9733;</dt><dd>Strong agreement: absolute score of {FLAG_MIN_ABS_SCORE} or more, with at least {FLAG_MIN_TOTAL} signals voting.</dd>
      <dt>excess vs bench</dt><dd>Average return above the row’s benchmark — SPY for direct signals, an asset-class proxy (XLE, GLD, DBA, TLT) for crosswalked ones — in the direction the signal pointed.</dd>
      <dt>hit-rate &amp; 95% range</dt><dd>How often it beat the benchmark, and where the true rate likely sits. Wide range = still noisy.</dd>
      <dt>book at risk</dt><dd>Share of account equity at risk on a one-ATR adverse day across every open position. Not the stop-out loss — the stop sits {STOP_ATR_MULTIPLE:.0f} ATRs away, so that would be larger.</dd>
      <dt>10y&ndash;2y spread</dt><dd>The 10-year Treasury yield minus the 2-year yield. A negative number means the curve is inverted &mdash; a classic recession-risk signal.</dd>
      <dt>RRP</dt><dd>The Federal Reserve's overnight reverse repo facility, where cash is parked overnight. A falling balance means money is flowing back into the financial system.</dd>
      <dt>TGA</dt><dd>The U.S. Treasury's general account &mdash; its checking account at the Fed. A rising balance pulls cash out of the banking system; a falling one adds it back.</dd>
      <dt>put / call percentile</dt><dd>Where today's ratio of put options traded to call options traded ranks against its own recent history. A high percentile means unusually heavy hedging or bearish betting.</dd>
      <dt>pending / in-flight opinion</dt><dd>An opinion already recorded whose forward-return outcome has not been measured yet, because not enough time has passed.</dd>
      <dt>basis break</dt><dd>A price move so large between two consecutive trading days that it looks like an unadjusted stock split rather than a real move &mdash; flagged so it cannot silently distort a return calculation.</dd>
      <dt>heat</dt><dd>Dollars at risk on a one-ATR adverse day (quantity &times; ATR) &mdash; a measure of real risk, not simply how much money is invested. The stop sits {STOP_ATR_MULTIPLE:.0f} ATRs out, so a stop-out loses more than this.</dd>
      <dt>ATR</dt><dd>Average True Range &mdash; a stock's typical daily price swing in dollars, used to size a stop distance and, from it, this page's heat number.</dd>
    </dl>
  </details>"""

    body_html = (
        '<main class="page">\n'
        '<header class="mast">\n'
        "<div>\n"
        '<h1 class="name">The Nightly <em>Almanac</em></h1>\n'
        '<div class="tag">Signals, sizing &amp; reliability — read before the weekly reweighting</div>\n'
        "</div>\n"
        f'<div class="edition">{"<br>".join(edition_lines)}</div>\n'
        "</header>\n"
        '<div class="rule-thin"></div>\n'
        f"{_INTRO}\n"
        f"{_jump_nav()}\n"
        '<section aria-labelledby="read-h">\n'
        '<h2 id="read-h" class="eyebrow">Tonight\'s read</h2>\n'
        f"{hero_body}\n"
        "</section>\n"
        f"{sections}\n"
        f"{gloss}\n"
        f"{_footer()}\n"
        "</main>\n"
    )

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Agentic Trading Research Bot Dashboard</title>"
        f"<style>{_STYLE}</style></head><body>"
        f"{body_html}"
        f"<script>{SCRIPT}</script>"
        "</body></html>\n"
    )


def write_dashboard(html_text: str, output_path: str) -> None:
    """Write atomically: temp file in the same dir, then os.replace, so a
    reader who opens the file mid-write never sees a truncated page."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(html_text, encoding="utf-8")
    os.replace(tmp, out)
