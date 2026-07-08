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

import html as _html
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.combiners.scorer import scorecard  # noqa: E402
from sources.combiners.scorer.db import RELIABLE_MIN_N  # noqa: E402

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

# --- pure formatting helpers (no I/O; unit-tested without a DB) -------------


def _esc(x) -> str:
    return _html.escape("" if x is None else str(x))


def _num(x, dp=2) -> str:
    return "—" if x is None else f"{x:.{dp}f}"


def _pct(x, dp=1) -> str:
    return "—" if x is None else f"{x * 100:.{dp}f}%"


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
) -> str:
    if not body_rows:
        return f'<p class="empty">{_esc(empty)}</p>'
    head = "".join(
        f'<th class="num">{_esc(h)}</th>' if i >= numeric_from else f"<th>{_esc(h)}</th>"
        for i, h in enumerate(headers)
    )
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


def _sparkline_svg(series: list[tuple], w: int = 640, h: int = 64) -> str:
    """Inline SVG VIX trend: gradient area fill + polyline + one titled dot
    per point (colored by that point's regime, last dot emphasized).
    `series` is [(regime, vix), ...] oldest-first is not required — callers
    pass newest-first and we reverse. Degrades to a 'no data' note for < 2
    usable points. Pure: coordinates computed here, zero JS/assets."""
    pts = [(r, v) for r, v in reversed(series) if v is not None]
    if len(pts) < 2:
        return '<p class="empty">no data</p>'
    vixes = [v for _, v in pts]
    lo, hi = min(vixes), max(vixes)
    span = (hi - lo) or 1.0  # flat series: avoid divide-by-zero
    n = len(pts)
    coords: list[tuple[float, float]] = []
    circles = []
    for i, (regime, v) in enumerate(pts):
        x = round(i / (n - 1) * (w - 8) + 4, 1)
        y = round(h - 4 - (v - lo) / span * (h - 8), 1)
        coords.append((x, y))
        is_last = i == n - 1
        fill = {"risk_on": "var(--up)", "risk_off": "var(--down)"}.get(regime, "var(--hold)")
        radius = 4 if is_last else 3
        stroke = ' stroke="var(--ink)" stroke-width="2"' if is_last else ""
        label = f"point {i + 1} of {n} · VIX {_num(v, 1)} · {regime or 'regime unknown'}"
        circles.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}"{stroke}>'
            f"<title>{_esc(label)}</title></circle>"
        )
    poly = " ".join(f"{x},{y}" for x, y in coords)
    area = (
        f"M{coords[0][0]},{h} L"
        + " L".join(f"{x},{y}" for x, y in coords)
        + f" L{coords[-1][0]},{h} Z"
    )
    aria = f"VIX over the trailing {n} snapshots, from {_num(vixes[0], 1)} to {_num(vixes[-1], 1)}"
    return (
        f'<svg class="spark" role="img" viewBox="0 0 {w} {h}" preserveAspectRatio="none"'
        f' aria-label="{_esc(aria)}">'
        '<defs><linearGradient id="dashfade" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#e0bd76" stop-opacity=".26"/>'
        '<stop offset="1" stop-color="#e0bd76" stop-opacity="0"/></linearGradient></defs>'
        f'<path d="{area}" fill="url(#dashfade)"/>'
        f'<polyline points="{poly}" fill="none" stroke="#e0bd76" stroke-width="2"/>'
        f"{''.join(circles)}</svg>"
        '<p class="cap">VIX · trailing'
        f" {n} snapshots · higher = more fear · dot color = that night's regime</p>"
    )


def _yn(x) -> str:
    if x is None:
        return "—"
    return "yes" if x else "no"


def _signed_num(x, dp: int = 1) -> str:
    return "—" if x is None else f"{x:+.{dp}f}"


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


def _reliability_meter(n_bench: int | None, threshold: int) -> str:
    """The evidence meter: how far n_bench (benchmarked calls — NOT
    n_matured, see scorer/db.py's reliable-gates-on-n_bench note) has
    filled toward the reliability floor."""
    n = n_bench or 0
    pct = min(n / threshold, 1) * 100 if threshold else 0.0
    low_cls = " low" if n < threshold else ""
    status = "not enough yet" if n < threshold else "enough to grade"
    title = f"{n} benchmarked calls, threshold {threshold} — {status}"
    return (
        f'<div class="meter" title="{_esc(title)}"><div class="trk">'
        f'<div class="fil{low_cls}" style="width:{pct:.0f}%"></div></div>'
        f'<div class="lab">{n} / {threshold}</div></div>'
    )


def _ci_bar(hit_rate, ci_lo, ci_hi) -> str:
    """The hit-rate confidence-interval bar: visible numbers, a range bar
    clamped to the 0-100 track, and an estimate marker. NULLs (no bench
    sample yet) degrade to a plain dash — no crash, no marker at 0."""
    if hit_rate is None or ci_lo is None or ci_hi is None:
        return '<div class="ci">—</div>'
    hr = round(hit_rate * 100)
    lo = max(0, min(round(ci_lo * 100), 100))
    hi = max(0, min(round(ci_hi * 100), 100))
    width = max(0, hi - lo)
    est = max(0, min(hr, 100))
    title = f"best estimate {hr}%, 95% range {lo}–{hi}%"
    return (
        f'<div class="ci" title="{_esc(title)}">'
        f'<div class="num"><b>{hr}%</b> <span>· {lo}–{hi}%</span></div>'
        f'<div class="trk"><div class="rng" style="left:{lo}%;width:{width}%"></div>'
        f'<div class="est" style="left:{est}%"></div></div>'
        '<div class="sc"><span>0</span><span>50</span><span>100</span></div></div>'
    )


# --- section renderers (each takes an open ro conn; may raise -> caught) ----


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
            ("yield curve inverted", _yn(r["curve_inverted"])),
            ("high-yield spread", _num(r["hy_spread"], 2)),
            ("VIX backwardation", _yn(r["vix_backwardation"])),
            ("put / call percentile", _pct(r["equity_pcr_pctile"])),
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
    return tiles + f"<details><summary>All 10 regime inputs</summary>{drivers}</details>"


def _regime_timeline(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT s.captured_at, m.regime, m.vix FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at DESC LIMIT 30"
    ).fetchall()
    return _sparkline_svg([(r["regime"], r["vix"]) for r in rows])


def _scorecard(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT symbol, score_sum, total, coverage, in_portfolio,"
        " bullish, bearish, worst_staleness_days"
        " FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC LIMIT 15"
    ).fetchall()
    flagged = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_flagged")}
    body = [
        _cells(
            r["symbol"],
            _score_cell(r["score_sum"], r["bullish"], r["bearish"], r["symbol"] in flagged),
            f"{r['bullish']} / {r['bearish']}",
            _pct(r["coverage"]),
            "—" if r["worst_staleness_days"] is None else f"{r['worst_staleness_days']:.1f}d",
            "✓" if r["in_portfolio"] else "",
            numeric_from=1,
        ).replace("<tr>", '<tr class="flag">' if r["symbol"] in flagged else "<tr>")
        for r in rows
    ]
    return _table(
        ["symbol", "score", "split (bull/bear)", "coverage", "data age", "held"],
        body,
        numeric_from=1,
    )


def _signal_efficacy(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_matured,"
        " avg_directional_excess, hit_rate, reliable FROM v_signal_efficacy"
        " ORDER BY reliable DESC, n_matured DESC LIMIT 40"
    ).fetchall()
    body = [
        _cells(
            r["signal_id"],
            "xw" if r["via_crosswalk"] else "direct",
            str(r["horizon"]),
            str(r["n_matured"]),
            _pct(r["avg_directional_excess"]),
            _pct(r["hit_rate"]),
            _reliable_badge(r["reliable"]),
            numeric_from=2,
        )
        for r in rows
    ]
    return _table(
        ["signal", "via", "horizon", "n", "dir excess", "hit rate", ""],
        body,
        empty="no matured signal outcomes yet",
        numeric_from=2,
    )


def _bucket_performance(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT bucket, horizon, n_matured, avg_fwd_return, avg_excess,"
        " hit_rate, reliable FROM v_bucket_performance ORDER BY horizon, bucket"
    ).fetchall()
    body = [
        _cells(
            r["bucket"],
            str(r["horizon"]),
            str(r["n_matured"]),
            _pct(r["avg_fwd_return"]),
            _pct(r["avg_excess"]),
            _pct(r["hit_rate"]),
            _reliable_badge(r["reliable"]),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(
        ["bucket", "horizon", "n", "fwd return", "excess", "hit rate", ""],
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


def _signal_recommendation(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_bench,"
        " avg_directional_excess, hit_rate, hit_ci_lo, hit_ci_hi, recommendation"
        " FROM v_signal_recommendation"
        " ORDER BY horizon, via_crosswalk, signal_id"
    ).fetchall()
    body = [
        _cells(
            r["signal_id"],
            "xw" if r["via_crosswalk"] else "direct",
            str(r["horizon"]),
            _reliability_meter(r["n_bench"], RELIABLE_MIN_N),
            _pct(r["avg_directional_excess"]),
            _ci_bar(r["hit_rate"], r["hit_ci_lo"], r["hit_ci_hi"]),
            _rec_badge(r["recommendation"]),
            numeric_from=2,
        )
        for r in rows
    ]
    caveat = (
        '<p class="cap">Lead with n and the CI, not the excess. ~144 rows'
        " are graded at once — a few cross a 95% threshold by chance alone;"
        " hold every verdict loosely. Re-weighting stays a human decision.</p>"
    )
    return caveat + _table(
        ["signal", "via", "horizon", "evidence", "excess vs SPY", "hit-rate (0–100%)", "verdict"],
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


SECTIONS = [
    (
        "regime",
        "Regime",
        "composite.db",
        _regime,
        "Macro",
        "The market's mood, distilled from ten macro inputs. “Risk-on” means"
        " money is flowing toward risk; the VIX is a fear gauge — lower is"
        " calmer. Open the drivers to see which inputs argued which way.",
    ),
    (
        "regime-timeline",
        "Regime timeline",
        "composite.db",
        _regime_timeline,
        "Macro",
        "How the market mood and the VIX fear gauge have moved across recent"
        " nightly snapshots. Each dot is one snapshot; higher = more fear;"
        " color = that night's regime.",
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
        "book-heat",
        "Advisor book heat",
        "advisor.db",
        _book_heat,
        "Your book",
        "How much of your account is genuinely at risk right now, adding up"
        " what you would lose if every open position hit its stop. Coverage"
        " says how much of the book that number actually accounts for.",
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
        "The verdict on each signal, based on where its 95% confidence range"
        " for hit-rate sits relative to a coin flip. ‘Keep’ means the"
        " whole range beats 50%; ‘anti-signal’ means the whole range"
        " loses; ‘watch’ means we cannot yet tell. Roughly 144 signals"
        " are graded at once, so a few clear the bar by luck — hold every"
        " verdict loosely.",
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

_STYLE = """
:root{
  --ink:#0d1013; --paper:#151a1e; --gutter:#10161a; --edge:#232c33;
  --fg:#e8e6df; --muted:#9aa1ab; --faint:#7b828c;
  --brass:#e0bd76; --brass-dim:#b39758;
  --up:#5bbf8a; --down:#e0736b; --hold:#e0bd76;
  --serif:ui-serif,Georgia,"Iowan Old Style","Palatino Linotype","Times New Roman",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box;}
body{margin:0;background:
    radial-gradient(1200px 500px at 80% -10%, rgba(224,189,118,.06), transparent 70%),
    var(--ink);
  color:var(--fg);font-family:var(--sans);font-size:14px;line-height:1.55;padding:32px 20px 64px;}
.page{max-width:940px;margin:0 auto;}

/* masthead */
.mast{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:2px solid var(--edge);padding-bottom:14px;margin-bottom:6px;}
.mast .name{font-family:var(--serif);font-size:30px;font-weight:600;letter-spacing:.01em;line-height:1;margin:0;}
.mast .name em{color:var(--brass);font-style:italic;}
.mast .tag{color:var(--muted);font-size:12px;margin-top:6px;letter-spacing:.02em;}
.mast .edition{text-align:right;font-family:var(--mono);font-size:11px;color:var(--muted);
  letter-spacing:.06em;text-transform:uppercase;line-height:1.7;}
.mast .edition b{color:var(--fg);font-weight:600;}
.rule-thin{height:1px;background:var(--edge);margin:0 0 26px;}
.lab-banner{background:rgba(224,189,118,.09);border:1px solid var(--brass-dim);color:var(--brass);
  border-radius:8px;padding:7px 13px;font-size:12px;margin:14px 0 26px;font-family:var(--mono);}

/* thesis hero */
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;
  color:var(--brass);margin:0 0 10px;}
.read{font-family:var(--serif);font-size:22px;line-height:1.5;margin:0 0 18px;color:var(--fg);}
.read .n{font-family:var(--mono);font-weight:600;font-size:.9em;background:rgba(255,255,255,.05);
  padding:0 5px;border-radius:4px;}
.read b{font-style:normal;}
.read b.on{color:var(--up);}.read b.off{color:var(--down);}.read b.mid{color:var(--hold);}
.conditions{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 10px;}
.cond{display:flex;align-items:baseline;gap:8px;background:var(--paper);border:1px solid var(--edge);
  border-radius:999px;padding:6px 14px;}
.cond .cv{font-family:var(--mono);font-size:15px;font-weight:600;}
.cond .cl{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em;}
.legend{color:var(--muted);font-size:11.5px;margin:16px 0 30px;font-family:var(--mono);}
.legend .sw{display:inline-block;width:9px;height:9px;border-radius:2px;margin:0 3px 0 12px;vertical-align:middle;}

/* ledger sections: margin-note gutter + data (signature) */
.ledger{display:grid;grid-template-columns:210px 1fr;gap:0;border-top:1px solid var(--edge);margin-bottom:2px;}
.note{padding:20px 22px 20px 0;border-right:1px solid var(--edge);}
.note .kicker{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--brass-dim);margin:0 0 8px;}
.note h2{font-family:var(--serif);font-size:18px;font-weight:600;margin:0 0 10px;line-height:1.15;}
.note p{color:var(--muted);font-size:12.5px;line-height:1.55;margin:0;font-style:italic;}
.data{padding:20px 0 24px 26px;min-width:0;}

/* readouts */
.tiles{display:flex;flex-wrap:wrap;gap:22px;margin-bottom:4px;}
.tile .v{font-family:var(--mono);font-size:26px;font-weight:600;line-height:1;letter-spacing:-.01em;}
.tile .k{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-top:6px;}
.tag-on{color:var(--up);}.tag-off{color:var(--down);}.tag-dim{color:var(--muted);}

/* tables */
.twrap{overflow-x:auto;}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:440px;}
th{color:var(--muted);font-weight:600;text-align:left;padding:0 10px 8px;font-size:11px;
  text-transform:uppercase;letter-spacing:.04em;}
td{padding:8px 10px;border-top:1px solid rgba(255,255,255,.06);vertical-align:middle;}
td.num,th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;}
tbody tr{transition:background .12s ease;}
tbody tr:hover td{background:rgba(255,255,255,.035);}
[title]{cursor:help;}
.sym{font-family:var(--mono);font-weight:600;}
.drivers td:first-child{color:var(--muted);}
tr.flag td{background:rgba(224,189,118,.08);}
tr.flag td:first-child{box-shadow:inset 2px 0 0 var(--brass);}
tr.flag .sym::after{content:"★";color:var(--brass);margin-left:6px;font-size:11px;}

/* score cell: signed number (visible) + diverging bar */
.scorecell{display:flex;align-items:center;gap:10px;justify-content:flex-end;}
.sval{font-family:var(--mono);font-weight:600;min-width:26px;text-align:right;}
.sval.up{color:var(--up);}.sval.down{color:var(--down);}
.sbar{position:relative;width:88px;height:9px;background:var(--gutter);border-radius:5px;overflow:hidden;flex:none;}
.sbar::before{content:"";position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--edge);}
.sbar i{position:absolute;top:0;height:100%;}
.sbar i.p{left:50%;background:var(--up);}
.sbar i.n{right:50%;background:var(--down);}

/* reliability meter */
.meter{width:104px;margin-left:auto;}
.meter .trk{height:6px;background:var(--gutter);border-radius:3px;overflow:hidden;}
.meter .fil{height:100%;border-radius:3px;background:var(--up);}
.meter .fil.low{background:var(--hold);}
.meter .lab{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:3px;text-align:right;}

/* CI: visible numbers + scaled range bar with 0/50/100 axis */
.ci{width:168px;margin-left:auto;}
.ci .num{font-family:var(--mono);font-size:11px;margin-bottom:3px;text-align:right;}
.ci .num b{color:var(--fg);}.ci .num span{color:var(--muted);}
.ci .trk{position:relative;height:9px;background:var(--gutter);border-radius:5px;}
.ci .trk::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--faint);}
.ci .rng{position:absolute;top:1px;height:7px;background:var(--brass);opacity:.55;border-radius:4px;}
.ci .est{position:absolute;top:-2px;width:3px;height:13px;background:var(--fg);border-radius:1px;}
.ci .sc{display:flex;justify-content:space-between;font-family:var(--mono);font-size:9px;
  color:var(--faint);margin-top:2px;}

/* verdict pills */
.pill{display:inline-block;font-family:var(--mono);font-size:11px;font-weight:600;
  padding:2px 9px;border-radius:999px;letter-spacing:.02em;}
.pill.ins,.pill.weak{background:rgba(154,161,171,.16);color:var(--muted);}
.pill.watch{background:rgba(224,189,118,.16);color:var(--brass);}
.pill.keep{background:rgba(91,191,138,.16);color:var(--up);}
.pill.anti{background:rgba(224,115,107,.16);color:var(--down);}

/* sparkline */
.spark{display:block;width:100%;height:64px;}
.cap{color:var(--muted);font-size:11px;font-family:var(--mono);margin:6px 0 0;}

/* disclosure */
details{margin-top:16px;}
summary{cursor:pointer;color:var(--brass);font-family:var(--mono);font-size:11.5px;letter-spacing:.04em;list-style:none;}
summary::before{content:"+ ";}details[open] summary::before{content:"– ";}
summary:focus-visible{outline:2px solid var(--brass);outline-offset:3px;border-radius:3px;}
.gloss{border-top:1px solid var(--edge);margin-top:8px;padding-top:12px;}
.gloss dt{font-family:var(--mono);color:var(--fg);font-size:12px;font-weight:600;margin-top:10px;}
.gloss dd{color:var(--muted);margin:2px 0 0;font-size:12.5px;}

@media (max-width:660px){
  .ledger{grid-template-columns:1fr;}
  .note{border-right:none;border-bottom:1px solid var(--edge);padding:18px 0;}
  .data{padding:18px 0;}
  .mast{flex-direction:column;align-items:flex-start;gap:10px;}
  .mast .edition{text-align:left;}
}
""".strip()


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
    """'2026 · 07 · 08' (hair-space separated, mockup style). Total: any
    unparseable now_iso degrades to its bare date-ish prefix rather than
    raising — the masthead must always render something."""
    try:
        dt = datetime.fromisoformat(now_iso)
    except Exception:
        return _esc(now_iso[:10])
    sep = "&#8202;·&#8202;"
    return f"{dt.year:04d}{sep}{dt.month:02d}{sep}{dt.day:02d}"


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

    gloss = """<details style="margin-top:26px">
    <summary>The whole vocabulary, in one place</summary>
    <dl class="gloss">
      <dt>regime</dt><dd>The market's risk mood — risk-on, risk-off, or mixed — read from ten macro inputs.</dd>
      <dt>VIX</dt><dd>An index of expected volatility. A fear gauge: higher means more fear priced in.</dd>
      <dt>score</dt><dd>Sum of each signal's bullish (positive) and bearish (negative) reading for one stock.</dd>
      <dt>split (bull/bear)</dt><dd>How many signals voted each way. Can differ from the score, which is weighted.</dd>
      <dt>coverage</dt><dd>Share of all applicable signals that actually had an opinion on this stock.</dd>
      <dt>data age</dt><dd>How old the freshest-to-stalest input behind this row is, in days.</dd>
      <dt>held</dt><dd>A check mark means you currently own this stock.</dd>
      <dt>flagged &#9733;</dt><dd>Strong agreement: absolute score of 4 or more, with at least 3 signals voting.</dd>
      <dt>excess vs SPY</dt><dd>Average return above the S&amp;P 500 benchmark, in the direction the signal pointed.</dd>
      <dt>hit-rate &amp; 95% range</dt><dd>How often it beat the benchmark, and where the true rate likely sits. Wide range = still noisy.</dd>
      <dt>book at risk</dt><dd>Share of account equity you'd lose if every stop triggered at once.</dd>
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
        '<section aria-labelledby="read-h">\n'
        '<h2 id="read-h" class="eyebrow">Tonight\'s read</h2>\n'
        f"{hero_body}\n"
        "</section>\n"
        f"{sections}\n"
        f"{gloss}\n"
        "</main>\n"
    )

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Trading Bot Dashboard</title>"
        f"<style>{_STYLE}</style></head><body>"
        f"{body_html}"
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


def main() -> int:
    now_iso = datetime.now(UTC).isoformat()
    try:
        page = build_page(DATA_DIR, now_iso)
    except Exception as e:  # never leave a stale file with no error banner
        page = (
            "<!doctype html>\n<html><head><meta charset='utf-8'>"
            "<title>Trading Bot Dashboard</title></head><body>"
            f"<h1>Trading Bot Dashboard</h1><p>generation failed"
            f" ({_esc(type(e).__name__)})</p></body></html>\n"
        )
    write_dashboard(page, OUTPUT_PATH)
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
