"""narrative.py is pure: every function is (values in) -> (dicts out).
No sqlite, no clock, no file I/O — asserted by the import test."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import narrative  # noqa: E402


def test_bands():
    assert narrative.qualitative_band("vix", 14.2) == "calm"
    assert narrative.qualitative_band("vix", 20.0) == "nervous"
    assert narrative.qualitative_band("vix", 31.0) == "stressed"
    assert narrative.qualitative_band("book_heat_pct", 0.9) == "comfortable"
    assert narrative.qualitative_band("book_heat_pct", 3.0) == "elevated"
    assert narrative.qualitative_band("t10y2y", -0.4) == "inverted"
    assert narrative.qualitative_band("hy_spread", 4.5) == "wide"
    assert narrative.qualitative_band("unknown_metric", 1.0) is None


def test_regime_verdict_tones():
    assert narrative.regime_verdict("risk_on", 4) == {"text": "Risk-on, 4th night", "tone": "on"}
    assert narrative.regime_verdict("risk_off", 1) == {"text": "Risk-off, 1st night", "tone": "off"}
    assert narrative.regime_verdict("mixed", 2)["tone"] == "mid"
    assert narrative.regime_verdict(None, 0) is None


def test_book_verdict_uses_band():
    v = narrative.book_verdict(0.9)
    assert v["tone"] == "on" and "comfortable" in v["text"]
    assert narrative.book_verdict(None) is None


def test_efficacy_verdict_counts():
    v = narrative.efficacy_verdict(keep=3, watch=5, anti=1)
    assert "3" in v["text"] and v["tone"] == "on"
    assert narrative.efficacy_verdict(0, 0, 0) is None


def test_hero_bullets_shapes_and_degradation():
    bullets = narrative.hero_bullets(
        regime={"regime": "risk_on", "streak_nights": 3, "vix": 14.2},
        book={"heat_pct": 1.1, "positions": 6},
        disagreements=["XOM"],
        flagged=["DECK", "CROX"],
    )
    assert 1 <= len(bullets) <= 3
    assert all(set(b) == {"text", "tone"} for b in bullets)
    # every input missing -> still valid, possibly empty
    assert narrative.hero_bullets(None, None, [], []) == []


def test_book_verdict_takes_percent_not_fraction():
    # v_book_heat.heat_pct is a FRACTION (0.0196 = 1.96%); feeding the raw
    # fraction would read "comfortable" forever, at any real heat level.
    assert "moderate" in narrative.book_verdict(0.0196 * 100)["text"]


def test_caveats_cover_every_track_record_section():
    for sid in (
        "signal-efficacy",
        "bucket-performance",
        "human-filter",
        "regime-performance",
        "pending",
        "signal-recommendations",
        "trader-scorecard",
        "candidate-efficacy",
    ):
        assert narrative.CAVEATS[sid].strip()
