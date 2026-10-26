"""Intraday stock book vs SPY, both rebased to $100 at the prior close.

Pure core under a thin file-reading shell: no network, no DB, no clock. The
broker exposes no intraday portfolio history, so the book is rebuilt as
today's quantities marked at each 5-minute bar's close — the same stock-book
convention as the dashboard's Portfolio-vs-SPY curve (cash excluded).

Inputs are the raw JSON the Robinhood MCP returns (`get_equity_positions`,
`get_equity_historicals`); the `book-vs-spy-intraday` skill fetches them.
Interpolated bars (`interpolated: true`) are gap-fill, not prints: they are
dropped and the last real print carries forward.

    uv run python -m tools.book.intraday_curve --date 2026-10-22 \
        --positions positions.json --out curve.json --html page.html \
        bars-a.json bars-b.json bars-c.json daily.json
    # exit 0 built · 2 refused (a symbol with no bars or no prior close)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path

from sources.common.clock import PHOENIX_UTC_OFFSET

SESSION_BARS = 78  # 09:30–16:00 ET in 5-minute bars; a half day is 42
BAR_MINUTES = 5
OPEN_UTC = "T13:30:00"  # 09:30 ET while New York is on daylight time
BENCHMARK = "SPY"
TEMPLATE = Path(__file__).with_name("intraday_curve_page.html")


def load_positions(doc: Mapping[str, object]) -> dict[str, float]:
    """`get_equity_positions` JSON → {symbol: quantity}, long legs only."""
    data = doc.get("data", doc)
    assert isinstance(data, Mapping)
    out: dict[str, float] = {}
    for p in data.get("positions", []):
        if p.get("type", "long") == "long":
            out[p["symbol"]] = float(p["quantity"])
    return out


def load_historicals(
    docs: Iterable[Mapping[str, object]],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Split `get_equity_historicals` results into (intraday, daily) close maps.

    intraday: {symbol: {begins_at: close}} with interpolated bars dropped.
    daily:    {symbol: {date: close}}.
    """
    intraday: dict[str, dict[str, float]] = {}
    daily: dict[str, dict[str, float]] = {}
    for doc in docs:
        data = doc.get("data", doc)
        assert isinstance(data, Mapping)
        for r in data.get("results", []):
            target = daily if r.get("interval") == "day" else intraday
            closes = target.setdefault(r["symbol"], {})
            for b in r.get("bars", []):
                if b.get("interpolated"):
                    continue
                key = b["begins_at"][:10] if target is daily else b["begins_at"]
                closes[key] = float(b["close_price"])
    return intraday, daily


def prior_closes(daily: Mapping[str, Mapping[str, float]], date: str) -> dict[str, float]:
    """Each symbol's last daily close strictly before `date`."""
    out: dict[str, float] = {}
    for sym, closes in daily.items():
        before = [d for d in closes if d < date]
        if before:
            out[sym] = closes[max(before)]
    return out


def session_times(date: str, session_bars: int = SESSION_BARS) -> list[str]:
    start = datetime.fromisoformat(date + OPEN_UTC + "+00:00")
    return [
        (start + timedelta(minutes=BAR_MINUTES * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(session_bars)
    ]


def _phoenix_label(begins_at: str, plus_minutes: int = BAR_MINUTES) -> tuple[str, str]:
    """Bar END (begins_at + 5 min) in Phoenix time: ('HH:MM', 'h:MM AM')."""
    end = datetime.fromisoformat(begins_at.replace("Z", "+00:00")) + timedelta(minutes=plus_minutes)
    local = end.replace(tzinfo=None) - PHOENIX_UTC_OFFSET
    return local.strftime("%H:%M"), local.strftime("%-I:%M %p")


def build_curve(
    date: str,
    positions: Mapping[str, float],
    intraday: Mapping[str, Mapping[str, float]],
    prev: Mapping[str, float],
    session_bars: int = SESSION_BARS,
) -> dict[str, object]:
    """Rebase the book and the benchmark to 100 at the prior close, bar by bar.

    A holding with no bar yet at a given time stays at its last real print
    (or the prior close before its first print). Raises ValueError when a
    symbol is missing bars or a prior close — a silent NULL here would mark
    part of the book at zero.
    """
    needed = [*positions, BENCHMARK]
    no_prev = [s for s in needed if s not in prev]
    no_bars = [s for s in needed if s not in intraday]
    if no_prev or no_bars:
        raise ValueError(f"missing prior close: {no_prev}; missing bars: {no_bars}")
    times = [t for t in session_times(date, session_bars) if t in intraday[BENCHMARK]]
    if not times:
        raise ValueError(f"no {BENCHMARK} bars on {date}")
    base_book = sum(positions[s] * prev[s] for s in positions)
    last = dict(prev)
    counts = dict.fromkeys(positions, 0)
    open_hm, _ = _phoenix_label(session_times(date, 1)[0], plus_minutes=0)
    points: list[dict[str, object]] = [
        {"t": open_hm, "label": "Prev close", "book": 100.0, "spy": 100.0}
    ]
    for t in times:
        for s in positions:
            if t in intraday[s]:
                last[s] = intraday[s][t]
                counts[s] += 1
        book = sum(positions[s] * last[s] for s in positions)
        hm, label = _phoenix_label(t)
        points.append(
            {
                "t": hm,
                "label": label,
                "book": round(100 * book / base_book, 4),
                "spy": round(100 * intraday[BENCHMARK][t] / prev[BENCHMARK], 4),
            }
        )
    rows = []
    for s in positions:
        weight = positions[s] * prev[s] / base_book
        ret = last[s] / prev[s] - 1
        rows.append((s, round(weight, 4), round(ret, 4), round(weight * ret, 5), counts[s]))
    rows.sort(key=lambda r: -r[3])
    holdings = [
        {
            "symbol": s,
            "weight": w,
            "ret": r,
            "contrib": c,
            "bars": b,
            "prev": prev[s],
            "last": last[s],
        }
        for s, w, r, c, b in rows
    ]
    # Thin = missed more than a tenth of the session's bars so far (at least one):
    # the line is a staircase of real prints, which the page should say.
    thin = [s for s, _, _, _, b in rows if b < len(times) - max(1, len(times) // 10)]
    return {
        "date": date,
        "session_bars": session_bars,
        "bars_done": len(times),
        "partial": len(times) < session_bars,
        "last_label": points[-1]["label"],
        "base_book": round(base_book, 2),
        "close_book": round(sum(positions[s] * last[s] for s in positions), 2),
        "spy_prev": prev[BENCHMARK],
        "spy_last": intraday[BENCHMARK][times[-1]],
        "thin": thin,
        "points": points,
        "holdings": holdings,
    }


def render_page(curve: Mapping[str, object], template: str | None = None) -> str:
    """Inline the curve into the page template (dashboard-styled, self-contained)."""
    html = template if template is not None else TEMPLATE.read_text()
    payload = json.dumps(curve).replace("</", "<\\/")
    return html.replace("__DATA__", payload)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--date", required=True, help="session date, YYYY-MM-DD (UTC bar date)")
    ap.add_argument("--positions", required=True, help="get_equity_positions JSON")
    ap.add_argument("--out", required=True, help="curve JSON to write")
    ap.add_argument("--html", help="also render the page here")
    ap.add_argument(
        "--session-bars",
        type=int,
        default=SESSION_BARS,
        help="bars in a full session: 78 (default), 42 on a half day; never bars-so-far",
    )
    ap.add_argument("historicals", nargs="+", help="get_equity_historicals JSON (5minute and day)")
    ns = ap.parse_args(argv)
    with open(ns.positions) as f:
        positions = load_positions(json.load(f))
    docs = []
    for path in ns.historicals:
        with open(path) as f:
            docs.append(json.load(f))
    intraday, daily = load_historicals(docs)
    try:
        curve = build_curve(
            ns.date, positions, intraday, prior_closes(daily, ns.date), ns.session_bars
        )
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    with open(ns.out, "w") as f:
        json.dump(curve, f)
    if ns.html:
        Path(ns.html).write_text(render_page(curve))
    pts = curve["points"]
    assert isinstance(pts, list)
    print(
        f"{curve['date']}: {curve['bars_done']}/{curve['session_bars']} bars"
        f"{' (partial)' if curve['partial'] else ''}; book {pts[-1]['book']:.2f}"
        f" spy {pts[-1]['spy']:.2f}; thin {curve['thin']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
