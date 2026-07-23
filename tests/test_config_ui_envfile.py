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


def test_set_prefers_active_line_over_earlier_commented_default():
    out = config_ui.apply_updates("#FOO=1\nFOO=2\n", {"FOO": "3"})
    assert config_ui.parse_env(out)["FOO"] == "3"
    assert out == "#FOO=1\nFOO=3\n"


def test_clear_with_commented_default_and_active_line_removes_active():
    out = config_ui.apply_updates("#FOO=1\nFOO=2\n", {"FOO": None})
    assert out == "#FOO=1\n"


def test_written_values_survive_bash_sourcing(tmp_path):
    """The one subprocess test in this suite — .env's real consumer is
    env.sh's `set -a; . ./.env`, and only bash itself proves source-safety
    (offline, hermetic, <100ms)."""
    import shutil
    import subprocess

    if not shutil.which("bash"):
        import pytest

        pytest.skip("bash unavailable")
    danger = "https://hc-ping.com/abc?ping=1&fail=2"
    new_text, errors = config_ui.handle_save("", {"secret_HEALTHCHECK_URL": danger})
    assert errors == {}
    env_file = tmp_path / "env"
    env_file.write_text(new_text)
    marker = tmp_path / "pwned"
    out = subprocess.run(
        [
            "bash",
            "-c",
            f'cd "{tmp_path}" && set -a && . ./env && set +a && printf %s "$HEALTHCHECK_URL"',
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert out.stdout == danger
    assert not marker.exists()


def test_command_substitution_payload_does_not_execute(tmp_path):
    """Sibling to the above: a `$(...)` payload must round-trip literally,
    never execute, when the written .env is bash-sourced."""
    import shutil
    import subprocess

    if not shutil.which("bash"):
        import pytest

        pytest.skip("bash unavailable")
    danger = "x$(>pwned)"
    new_text, errors = config_ui.handle_save("", {"secret_HEALTHCHECK_URL": danger})
    assert errors == {}
    env_file = tmp_path / "env"
    env_file.write_text(new_text)
    marker = tmp_path / "pwned"
    out = subprocess.run(
        [
            "bash",
            "-c",
            f'cd "{tmp_path}" && set -a && . ./env && set +a && printf %s "$HEALTHCHECK_URL"',
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert out.stdout == danger
    assert not marker.exists()
