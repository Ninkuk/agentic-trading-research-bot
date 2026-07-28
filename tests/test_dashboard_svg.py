"""Pure-builder tests for dashboard_lib (svg + style). Offline, no DB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import style  # noqa: E402


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
