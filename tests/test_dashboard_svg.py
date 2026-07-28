"""Pure-builder tests for dashboard_lib (svg + style). Offline, no DB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import (
    style,  # noqa: E402
    svg,  # noqa: E402
)


def test_mark_palette_is_the_validated_set():
    # Validated 2026-07-28 (dataviz validate_palette.js, dark, surface #151a1e):
    # green/red pass CVD with diverging secondary encoding; midpoint is neutral
    # gray by rule; single-series lines take categorical slot-1 blue. See
    # docs/superpowers/specs/2026-07-28-dashboard-charts-design.md. Changing
    # any hex requires re-running the validator, not just this test.
    assert style.MARK_UP == "#199e70"
    assert style.MARK_DOWN == "#e66767"
    assert style.MARK_MID == "#3a434b"
    assert style.MARK_LINE == "#3987e5"


def test_style_uses_mark_tokens():
    assert f"--mark-up:{style.MARK_UP}" in style._STYLE
    assert f"--mark-down:{style.MARK_DOWN}" in style._STYLE
    # brass may still appear as accent ink, but never as a mark token
    assert "--mark-up:#5bbf8a" not in style._STYLE


def test_regime_strip_one_rect_per_day_with_gaps_and_titles():
    out = svg.regime_strip(
        [("2026-07-01", "risk_on"), ("2026-07-02", None), ("2026-07-03", "risk_off")]
    )
    assert out.count("<rect") == 3
    assert out.count("<title>") == 3
    assert "var(--mark-up)" in out and "var(--mark-down)" in out and "var(--mark-mid)" in out
    assert 'data-d="2026-07-02"' in out


def test_regime_strip_empty_degrades():
    assert "no data" in svg.regime_strip([])


def test_score_spark_diverges_and_clamps():
    out = svg.score_spark([2, -3, 0, 9], cap=5)
    assert out.count("<rect") == 4  # zero still draws a 1px tick at baseline
    assert "var(--mark-up)" in out and "var(--mark-down)" in out
    # a value beyond cap must not draw outside the viewBox
    import re

    for m in re.finditer(r'y="(-?[\d.]+)".*?height="([\d.]+)"', out):
        y, hgt = float(m.group(1)), float(m.group(2))
        assert y >= 0 and y + hgt <= 28


def test_score_spark_needs_two_points():
    assert "no data" in svg.score_spark([3])


def test_tile_spark_single_line_no_legend():
    out = svg.tile_spark([1.0, 2.0, 1.5])
    assert out.count("<polyline") == 1 and "<text" not in out
    assert 'stroke="var(--mark-line)"' in out and 'stroke-width="2"' in out
    # spec: >=8px invisible hover targets, one titled hit rect per point
    assert out.count('fill="transparent"') == 3 and out.count("<title>") == 3


def test_tile_spark_flat_series_no_zero_division():
    assert "<svg" in svg.tile_spark([2.0, 2.0, 2.0])


def test_dot_ci_svg_nulls_degrade_and_values_clamp():
    assert svg.dot_ci_svg(None, None, None) == '<div class="ci">—</div>'
    out = svg.dot_ci_svg(0.62, 0.40, 1.20)  # hi past 100% must clamp
    assert "<svg" in out and "62%" in out
