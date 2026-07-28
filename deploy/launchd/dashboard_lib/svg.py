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
