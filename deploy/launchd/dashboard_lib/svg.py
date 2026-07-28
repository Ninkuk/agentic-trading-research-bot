"""Pure SVG/format helpers for the dashboard: rows in, strings out, no I/O."""

import html as _html


def _esc(x) -> str:
    return _html.escape("" if x is None else str(x))


def _num(x, dp=2) -> str:
    return "—" if x is None else f"{x:.{dp}f}"


def _pct(x, dp=1) -> str:
    return "—" if x is None else f"{x * 100:.{dp}f}%"


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


def regime_strip(days: list[tuple[str, str | None]], cell: int = 14) -> str:
    """One rounded cell per Phoenix day, oldest→newest left→right. Diverging
    status: risk_on/risk_off poles, neutral-gray midpoint for mixed/unknown
    (never a hue at the midpoint — dataviz diverging rule). 2px surface gaps
    are the secondary encoding that licenses the poles' CVD warn band."""
    if not days:
        return '<p class="empty">no data</p>'
    gap, h = 2, 18
    fills = {"risk_on": "var(--mark-up)", "risk_off": "var(--mark-down)"}
    rects = []
    for i, (d, regime) in enumerate(days):
        x = i * (cell + gap)
        fill = fills.get(regime or "", "var(--mark-mid)")
        label = f"{d} · {regime or 'unknown'}"
        rects.append(
            f'<rect x="{x}" y="0" width="{cell}" height="{h}" rx="3" fill="{fill}"'
            f' data-d="{_esc(d)}" data-r="{_esc(regime or "unknown")}">'
            f"<title>{_esc(label)}</title></rect>"
        )
    w = len(days) * (cell + gap) - gap
    aria = f"regime by day, {days[0][0]} to {days[-1][0]}"
    return (
        f'<svg class="strip" role="img" viewBox="0 0 {w} {h}" width="100%" height="{h}"'
        f' preserveAspectRatio="none" aria-label="{_esc(aria)}">{"".join(rects)}</svg>'
    )


def score_spark(points: list[int], w: int = 110, h: int = 28, cap: int = 5) -> str:
    """Diverging mini-bars for score_sum history, oldest-first. |v| clamps to
    cap (same fixed denominator idea as _SCORE_BAR_MAX: bars stay comparable
    across rows). Sign is double-encoded: side of baseline + color."""
    if len(points) < 2:
        return '<p class="empty">no data</p>'
    n = len(points)
    mid = h / 2
    slot = w / n
    bw = max(2.0, slot - 2)  # 2px gap between bars
    rects = []
    for i, v in enumerate(points):
        frac = min(abs(v), cap) / cap
        bh = round(frac * (mid - 1), 1)
        x = round(i * slot, 1)
        if v > 0:
            y, fill = round(mid - bh, 1), "var(--mark-up)"
        elif v < 0:
            y, fill = mid, "var(--mark-down)"
        else:
            y, bh, fill = mid - 0.5, 1.0, "var(--mark-mid)"
        rects.append(
            f'<rect x="{x}" y="{y}" width="{bw:.1f}" height="{max(bh, 1.0)}" rx="1"'
            f' fill="{fill}"><title>{_esc(f"{v:+d}")}</title></rect>'
        )
    return (
        f'<svg class="sspark" role="img" viewBox="0 0 {w} {h}" width="{w}" height="{h}"'
        f' aria-label="{_esc(f"score history, {n} snapshots")}">'
        f'<line x1="0" y1="{mid}" x2="{w}" y2="{mid}" stroke="var(--edge)" stroke-width="1"/>'
        f"{''.join(rects)}</svg>"
    )


def tile_spark(values: list[float], w: int = 120, h: int = 30) -> str:
    """Single-series context sparkline for a KPI tile. One 2px line in the
    neutral line hue (not up/down — a level trend has no polarity); end dot
    marks 'now'. No legend: the tile's own label names the series."""
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return '<p class="empty">no data</p>'
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    n = len(pts)
    coords = [
        (round(i / (n - 1) * (w - 6) + 3, 1), round(h - 3 - (v - lo) / span * (h - 6), 1))
        for i, v in enumerate(pts)
    ]
    poly = " ".join(f"{x},{y}" for x, y in coords)
    ex, ey = coords[-1]
    slot = max(8.0, w / n)  # >=8px hover target per point (spec mark rule)
    hits = "".join(
        f'<rect x="{round(x - slot / 2, 1)}" y="0" width="{slot:.1f}" height="{h}"'
        f' fill="transparent"><title>{_esc(_num(v, 2))}</title></rect>'
        for (x, _y), v in zip(coords, pts, strict=True)
    )
    return (
        f'<svg class="tspark" role="img" viewBox="0 0 {w} {h}" width="{w}" height="{h}"'
        f' aria-label="{_esc(f"trend, {n} points")}">'
        f'<polyline points="{poly}" fill="none" stroke="var(--mark-line)" stroke-width="2"/>'
        f'<circle cx="{ex}" cy="{ey}" r="2.5" fill="var(--mark-line)"/>{hits}</svg>'
    )


def dot_ci_svg(hit_rate, ci_lo, ci_hi, w: int = 160, h: int = 18) -> str:
    """Hit-rate estimate + 95% CI as dot-and-whisker on a 0–100 track, with a
    hairline reference tick at 50% (coin flip). Same NULL contract as _ci_bar."""
    if hit_rate is None or ci_lo is None or ci_hi is None:
        return '<div class="ci">—</div>'

    def px(frac: float) -> float:
        return round(max(0.0, min(frac, 1.0)) * (w - 8) + 4, 1)

    lo, hi, est = px(ci_lo), px(ci_hi), px(hit_rate)
    mid = h / 2
    pct = round(hit_rate * 100)
    title = f"best estimate {pct}%, 95% range {round(ci_lo * 100)}–{round(ci_hi * 100)}%"
    return (
        f'<div class="ci"><div class="num"><b>{pct}%</b></div>'
        f'<svg role="img" viewBox="0 0 {w} {h}" width="{w}" height="{h}"'
        f' aria-label="{_esc(title)}"><title>{_esc(title)}</title>'
        f'<line x1="4" y1="{mid}" x2="{w - 4}" y2="{mid}" stroke="var(--edge)" stroke-width="1"/>'
        f'<line x1="{px(0.5)}" y1="2" x2="{px(0.5)}" y2="{h - 2}" stroke="var(--edge)" stroke-width="1"/>'
        f'<line x1="{lo}" y1="{mid}" x2="{hi}" y2="{mid}" stroke="var(--mark-line)" stroke-width="2"/>'
        f'<circle cx="{est}" cy="{mid}" r="4" fill="var(--mark-line)" stroke="var(--ink)" stroke-width="1"/>'
        "</svg></div>"
    )
