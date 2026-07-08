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

DATA_DIR = "data"
OUTPUT_PATH = "reports/dashboard.html"

# --- pure formatting helpers (no I/O; unit-tested without a DB) -------------


def _esc(x) -> str:
    return _html.escape("" if x is None else str(x))


def _num(x, dp=2) -> str:
    return "—" if x is None else f"{x:.{dp}f}"


def _pct(x, dp=1) -> str:
    return "—" if x is None else f"{x * 100:.{dp}f}%"


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{_esc(text)}</span>'


def _regime_badge(regime) -> str:
    cls = {"risk_on": "risk-on", "risk_off": "risk-off"}.get(regime or "", "mixed")
    return _badge(regime or "unknown", cls)


def _rec_badge(rec) -> str:
    cls = {
        "keep": "rec-keep",
        "watch": "rec-watch",
        "anti-signal": "rec-anti",
        "insufficient evidence": "rec-insufficient",
    }.get(rec or "", "rec-insufficient")
    return _badge(rec or "?", cls)


def _reliable_badge(reliable) -> str:
    return _badge("reliable", "ok") if reliable else _badge("thin", "dim")


def _table(headers: list[str], body_rows: list[str], empty: str = "no rows yet") -> str:
    if not body_rows:
        return f'<p class="empty">{_esc(empty)}</p>'
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _cells(*values, numeric_from: int = 0) -> str:
    """Row of <td>s; cells at index >= numeric_from get the tabular-nums class."""
    out = []
    for i, v in enumerate(values):
        cls = ' class="num"' if i >= numeric_from else ""
        out.append(f"<td{cls}>{v if isinstance(v, str) and v.startswith('<') else _esc(v)}</td>")
    return "<tr>" + "".join(out) + "</tr>"


def _stat_tiles(pairs: list[tuple[str, str]]) -> str:
    tiles = "".join(
        f'<div class="tile"><div class="tile-v">{v}</div><div class="tile-k">{_esc(k)}</div></div>'
        for k, v in pairs
    )
    return f'<div class="tiles">{tiles}</div>'


def _sparkline_svg(series: list[tuple], w: int = 480, h: int = 60) -> str:
    """Inline SVG VIX trend, one colored dot per point (by that point's
    regime). `series` is [(regime, vix), ...] oldest-first is not required —
    callers pass newest-first and we reverse. Degrades to a 'no data' note
    for < 2 usable points. Pure: coordinates computed here, zero JS/assets."""
    pts = [(r, v) for r, v in reversed(series) if v is not None]
    if len(pts) < 2:
        return '<p class="empty">no data</p>'
    vixes = [v for _, v in pts]
    lo, hi = min(vixes), max(vixes)
    span = (hi - lo) or 1.0  # flat series: avoid divide-by-zero
    n = len(pts)
    coords = []
    dots = []
    for i, (regime, v) in enumerate(pts):
        x = round(i / (n - 1) * (w - 8) + 4, 1)
        y = round(h - 4 - (v - lo) / span * (h - 8), 1)
        coords.append(f"{x},{y}")
        fill = {"risk_on": "var(--green)", "risk_off": "var(--red)"}.get(regime, "var(--amber)")
        dots.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{fill}"/>')
    return (
        f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'<polyline points="{" ".join(coords)}" fill="none"'
        f' stroke="var(--line)" stroke-width="1.5"/>{"".join(dots)}</svg>'
        f'<p class="cap">VIX, trailing {n} snapshots (dot color = regime)</p>'
    )


# --- section renderers (each takes an open ro conn; may raise -> caught) ----


def _regime(conn, now_iso) -> str:
    r = conn.execute(
        "SELECT regime, vix, inputs_present, inputs_expected FROM v_latest_regime"
    ).fetchone()
    if not r:
        return '<p class="empty">no regime yet</p>'
    return _stat_tiles(
        [
            ("regime", _regime_badge(r["regime"])),
            ("VIX", _num(r["vix"], 1)),
            ("inputs", f"{r['inputs_present']}/{r['inputs_expected']}"),
        ]
    )


def _regime_timeline(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT s.captured_at, m.regime, m.vix FROM market_regime m"
        " JOIN snapshots s ON s.id = m.snapshot_id"
        " ORDER BY s.captured_at DESC LIMIT 30"
    ).fetchall()
    return _sparkline_svg([(r["regime"], r["vix"]) for r in rows])


def _scorecard(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT symbol, score_sum, total, coverage, in_portfolio"
        " FROM v_latest_scorecard ORDER BY ABS(score_sum) DESC LIMIT 15"
    ).fetchall()
    flagged = {r["symbol"] for r in conn.execute("SELECT symbol FROM v_flagged")}
    body = [
        _cells(
            r["symbol"],
            f"{r['score_sum']:+d}",
            str(r["total"]),
            _pct(r["coverage"]),
            "✓" if r["in_portfolio"] else "",
            numeric_from=1,
        ).replace("<tr>", '<tr class="flagged">' if r["symbol"] in flagged else "<tr>")
        for r in rows
    ]
    return _table(["symbol", "score", "total", "coverage", "held"], body)


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
    )


def _signal_recommendation(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT signal_id, via_crosswalk, horizon, n_bench,"
        " avg_directional_excess, hit_ci_lo, hit_ci_hi, recommendation"
        " FROM v_signal_recommendation"
        " ORDER BY horizon, via_crosswalk, signal_id"
    ).fetchall()
    body = [
        _cells(
            r["signal_id"],
            "xw" if r["via_crosswalk"] else "direct",
            str(r["horizon"]),
            str(r["n_bench"]),
            _pct(r["avg_directional_excess"]),
            f"[{_pct(r['hit_ci_lo'])}, {_pct(r['hit_ci_hi'])}]",
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
        ["signal", "via", "horizon", "n_bench", "dir excess", "hit-rate 95% CI", "verdict"],
        body,
        empty="insufficient evidence for every signal (young scorer) — expected",
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
    return _stat_tiles(
        [
            ("positions", str(r["positions"] or 0)),
            ("book heat", _pct(r["heat_pct"], 2)),
            ("coverage", _num(r["heat_coverage"], 2)),
            ("equity", f"${_num(r['equity'], 0)}"),
            ("sources failed", _badge(str(failed), "red" if failed else "dim")),
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
    return _table(["bet", "members", "symbols", "heat $", "heat %"], body)


def _disagreements(conn, now_iso) -> str:
    rows = conn.execute(
        "SELECT symbol, score_sum, group_name, strong FROM v_disagreements"
    ).fetchall()
    body = [
        _cells(
            r["symbol"],
            f"{r['score_sum']:+d}",
            r["group_name"] or "",
            _badge("STRONG", "red") if r["strong"] else _badge("weak", "dim"),
            numeric_from=1,
        )
        for r in rows
    ]
    return _table(["symbol", "score", "group", ""], body, empty="no disagreements")


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
    )


SECTIONS = [
    ("regime", "Regime", "composite.db", _regime),
    ("regime-timeline", "Regime timeline", "composite.db", _regime_timeline),
    ("scorecard", "Ticker scorecard", "composite.db", _scorecard),
    ("signal-efficacy", "Signal efficacy", "scorer.db", _signal_efficacy),
    ("bucket-performance", "Bucket performance", "scorer.db", _bucket_performance),
    ("human-filter", "Human-filter tally", "scorer.db", _human_filter),
    ("book-heat", "Advisor book heat", "advisor.db", _book_heat),
    ("group-heat", "Advisor group heat", "advisor.db", _group_heat),
    ("disagreements", "Disagreements", "advisor.db", _disagreements),
    ("size-caps", "Size caps", "advisor.db", _size_caps),
    ("plan-001-report", "Signal recommendations", "scorer.db", _signal_recommendation),
    ("plan-004-scorecard", "Trader scorecard", "scorer.db", _trader_scorecard),
]
SECTION_IDS = [s[0] for s in SECTIONS]

_STYLE = """
:root {
  --bg:#12151b; --panel:#1a1f29; --fg:#e6e9ef; --muted:#8b93a7;
  --line:#5aa0ff; --green:#3fb950; --red:#f85149; --amber:#d29922;
  --border:#2a3140;
}
* { box-sizing:border-box; }
body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:14px; line-height:1.5; }
h1 { font-size:20px; margin:0 0 4px; }
.sub { color:var(--muted); margin:0 0 24px; font-size:12px; }
section { background:var(--panel); border:1px solid var(--border);
  border-radius:8px; padding:16px 18px; margin-bottom:16px; }
h2 { font-size:15px; margin:0 0 12px; }
table { border-collapse:collapse; width:100%; font-size:13px; }
th,td { text-align:left; padding:5px 10px; border-bottom:1px solid var(--border); }
th { color:var(--muted); font-weight:600; }
td.num,th.num { text-align:right; font-variant-numeric:tabular-nums;
  font-family:ui-monospace,"SF Mono",Menlo,monospace; }
tr.flagged td { background:rgba(210,153,34,0.14); }
.empty,.cap { color:var(--muted); font-size:12px; font-style:italic; }
.cap { margin:8px 0 0; }
.tiles { display:flex; flex-wrap:wrap; gap:12px; }
.tile { background:var(--bg); border:1px solid var(--border); border-radius:6px;
  padding:10px 14px; min-width:96px; }
.tile-v { font-size:18px; font-variant-numeric:tabular-nums; }
.tile-k { color:var(--muted); font-size:11px; text-transform:uppercase;
  letter-spacing:.04em; }
.badge { display:inline-block; padding:1px 8px; border-radius:10px;
  font-size:12px; font-weight:600; }
.risk-on { background:rgba(63,185,80,.2); color:var(--green); }
.risk-off { background:rgba(248,81,73,.2); color:var(--red); }
.mixed { background:rgba(210,153,34,.2); color:var(--amber); }
.ok { background:rgba(63,185,80,.2); color:var(--green); }
.dim { background:rgba(139,147,167,.18); color:var(--muted); }
.red { background:rgba(248,81,73,.2); color:var(--red); }
.rec-keep { background:rgba(63,185,80,.2); color:var(--green); }
.rec-watch { background:rgba(210,153,34,.2); color:var(--amber); }
.rec-anti { background:rgba(248,81,73,.2); color:var(--red); }
.rec-insufficient { background:rgba(139,147,167,.18); color:var(--muted); }
.spark { display:block; }
pre { background:var(--bg); border:1px solid var(--border); border-radius:6px;
  padding:12px; overflow-x:auto; font-size:12px;
  font-family:ui-monospace,"SF Mono",Menlo,monospace; }
""".strip()


def _ro(data_dir: str, db_name: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{os.path.join(data_dir, db_name)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _render_section(sid, title, db_name, fn, data_dir, now_iso) -> str:
    try:
        conn = _ro(data_dir, db_name)
        try:
            body = fn(conn, now_iso)
        finally:
            conn.close()
    except Exception as e:  # missing DB, dropped view — degrade, never crash
        print(f"{db_name}: unreadable ({type(e).__name__})", file=sys.stderr)
        body = f'<p class="unavailable">{_esc(db_name)}: unreadable ({type(e).__name__})</p>'
    return f'<section id="{sid}"><h2>{_esc(title)}</h2>{body}</section>'


def build_page(data_dir: str, now_iso: str) -> str:
    sections = "\n".join(
        _render_section(sid, title, db_name, fn, data_dir, now_iso)
        for sid, title, db_name, fn in SECTIONS
    )
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Trading Bot Dashboard</title>"
        f"<style>{_STYLE}</style></head><body>"
        "<h1>Trading Bot Dashboard</h1>"
        f'<p class="sub">generated {_esc(now_iso)} · snapshot of last night\'s runs'
        " · re-weighting is a human decision</p>"
        f"{sections}"
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
