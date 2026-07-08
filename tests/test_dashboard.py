"""Tests for the zero-dependency nightly HTML dashboard generator.

Offline, like the rest of the suite: resilience is exercised by pointing the
generator at an empty data dir (every section degrades to 'unavailable' rather
than crashing), and self-containment is asserted on the emitted HTML string.
The per-section SQL is validated separately against live DB copies.
"""

import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import dashboard  # noqa: E402

NOW = "2026-07-08T21:13:00+00:00"


def test_sparkline_needs_two_points():
    assert "no data" in dashboard._sparkline_svg([])
    assert "no data" in dashboard._sparkline_svg([("risk_on", 16.0)])


def test_sparkline_emits_inline_polyline_no_external_refs():
    svg = dashboard._sparkline_svg([("risk_on", 16.0), ("mixed", 18.0), ("risk_off", 25.0)])
    assert "<polyline" in svg and "points=" in svg
    # inline only — no external asset references of any kind
    assert "http" not in svg and "xlink" not in svg


def test_sparkline_flat_series_does_not_divide_by_zero():
    # identical VIX across points -> zero range; must not raise
    svg = dashboard._sparkline_svg([("risk_on", 16.0), ("risk_on", 16.0)])
    assert "<polyline" in svg


def test_regime_badge_colors():
    assert "risk-on" in dashboard._regime_badge("risk_on")
    assert "risk-off" in dashboard._regime_badge("risk_off")
    assert "mixed" in dashboard._regime_badge("mixed")


def test_recommendation_badge_all_states():
    for state in ("keep", "watch", "anti-signal", "insufficient evidence"):
        assert dashboard._rec_badge(state)  # non-empty span, never raises


def test_build_page_degrades_when_all_dbs_missing(tmp_path):
    # empty data dir: every section's mode=ro connect fails -> unavailable,
    # never a crash; the whole page still assembles.
    html = dashboard.build_page(str(tmp_path), NOW)
    assert html.startswith("<!doctype html>") or "<html" in html
    assert html.count('class="unavailable"') >= 8  # most sections degrade
    # all 12 catalogued sections are present by id even when empty
    for sid in dashboard.SECTION_IDS:
        assert f'id="{sid}"' in html


def test_build_page_is_self_contained(tmp_path):
    html = dashboard.build_page(str(tmp_path), NOW)
    # hard constraint: no external assets — no CDN, no link/script src, no font
    for forbidden in ("http://", "https://", "cdn", "<link", "<script", "@font-face", "googleapis"):
        assert forbidden not in html.lower()
    assert "<style>" in html  # CSS is inlined in-head


def test_write_dashboard_is_atomic_replace(tmp_path):
    out = tmp_path / "sub" / "dashboard.html"
    dashboard.write_dashboard("<!doctype html><p>hi</p>", str(out))
    assert out.read_text(encoding="utf-8") == "<!doctype html><p>hi</p>"
    # no leftover temp file beside the target
    leftovers = [p.name for p in out.parent.iterdir() if p.name != "dashboard.html"]
    assert leftovers == []


def test_main_writes_page_and_returns_zero(tmp_path, monkeypatch):
    out = tmp_path / "dashboard.html"
    monkeypatch.setattr(dashboard, "DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(dashboard, "OUTPUT_PATH", str(out))
    rc = dashboard.main()
    assert rc == 0
    assert out.exists() and "Trading Bot Dashboard" in out.read_text(encoding="utf-8")
