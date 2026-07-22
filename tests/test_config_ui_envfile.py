"""Round-trip tests for config_ui's .env layer: pure text in/out, no I/O."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config_ui  # noqa: E402

SAMPLE = """# Free API keys — signup URLs inside.
FRED_API_KEY=abc123secret       # St. Louis Fed
EIA_API_KEY=ZZ_EIA_API_KEY_ZZ   # sentinel, still unset
# NTFY_SERVER=https://ntfy.sh       # optional; self-hosted
#RESEARCH_NIGHTLY_MAX=3
UNKNOWN_FUTURE_KEY=keepme
"""


def test_parse_strips_trailing_comment_and_keeps_unknown():
    got = config_ui.parse_env(SAMPLE)
    assert got["FRED_API_KEY"] == "abc123secret"
    assert got["UNKNOWN_FUTURE_KEY"] == "keepme"
    assert "NTFY_SERVER" not in got  # commented-out line is not an assignment
    assert "RESEARCH_NIGHTLY_MAX" not in got


def test_parse_last_assignment_wins():
    assert config_ui.parse_env("A=1\nA=2\n")["A"] == "2"


def test_apply_noop_is_byte_identical():
    assert config_ui.apply_updates(SAMPLE, {}) == SAMPLE


def test_apply_uncomments_default_line_in_place():
    out = config_ui.apply_updates(SAMPLE, {"RESEARCH_NIGHTLY_MAX": "2"})
    lines = out.splitlines()
    assert "RESEARCH_NIGHTLY_MAX=2" in lines
    assert "#RESEARCH_NIGHTLY_MAX=3" not in out
    # position preserved: still directly after the NTFY_SERVER comment line
    assert lines.index("RESEARCH_NIGHTLY_MAX=2") == 4


def test_apply_updates_active_line_preserving_trailing_comment():
    out = config_ui.apply_updates(SAMPLE, {"FRED_API_KEY": "newkey9999"})
    assert "FRED_API_KEY=newkey9999  # St. Louis Fed" in out
    assert "abc123secret" not in out


def test_apply_appends_new_key_at_end():
    out = config_ui.apply_updates(SAMPLE, {"BRAND_NEW": "x"})
    assert out.endswith("BRAND_NEW=x\n")
    assert out.startswith(SAMPLE)


def test_apply_none_removes_assignment_keeps_everything_else():
    out = config_ui.apply_updates(SAMPLE, {"FRED_API_KEY": None})
    assert "FRED_API_KEY" not in config_ui.parse_env(out)
    assert "# Free API keys" in out and "UNKNOWN_FUTURE_KEY=keepme" in out


def test_apply_none_for_absent_key_is_noop():
    assert config_ui.apply_updates(SAMPLE, {"NOT_THERE": None}) == SAMPLE
