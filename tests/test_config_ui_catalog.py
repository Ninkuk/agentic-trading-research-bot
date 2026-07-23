"""KNOBS catalog, validation, and the pure save pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config_ui  # noqa: E402

ENV = """FRED_API_KEY=oldsecret123
#RESEARCH_NIGHTLY_MAX=3
NTFY_TOPIC=ZZ_NTFY_TOPIC_ZZ
"""


def _knob(key):
    return next(k for k in config_ui.KNOBS if k.key == key)


def test_catalog_matches_spec():
    kinds = {k.key: k.kind for k in config_ui.KNOBS}
    assert kinds["RESEARCH_NIGHTLY_MAX"] == "int"
    assert kinds["RESEARCH_NIGHTLY_MODEL"] == "enum"
    assert kinds["NTFY_SERVER"] == "str"
    for secret in (
        "FRED_API_KEY",
        "CFTC_APP_TOKEN",
        "EIA_API_KEY",
        "NASS_API_KEY",
        "NTFY_TOKEN",
        "NTFY_TOPIC",
        "HEALTHCHECK_URL",
    ):
        assert kinds[secret] == "secret"
    assert len(config_ui.KNOBS) == 11


def test_sentinel_and_empty_are_unset():
    assert not config_ui.is_set("ZZ_FRED_API_KEY_ZZ")
    assert not config_ui.is_set("")
    assert not config_ui.is_set(None)
    assert config_ui.is_set("realvalue")


def test_validate_int_bounds_and_enum():
    m = _knob("RESEARCH_NIGHTLY_MAX")
    assert config_ui.validate(m, "0") is None
    assert config_ui.validate(m, "11") is not None
    assert config_ui.validate(m, "abc") is not None
    e = _knob("RESEARCH_NIGHTLY_MODEL")
    assert config_ui.validate(e, "sonnet") is None
    assert config_ui.validate(e, "gpt") is not None


def test_validate_int_rejects_unicode_digits_without_crashing():
    m = _knob("RESEARCH_NIGHTLY_MAX")
    for bad in ("²", "٣", "-1", "1.5"):
        assert config_ui.validate(m, bad) is not None


def test_validate_rejects_env_breaking_characters():
    s = _knob("NTFY_SERVER")
    assert config_ui.validate(s, "https://ntfy.example.com") is None
    for bad in ("has space", 'quo"te', "hash#tag", "back\\slash"):
        assert config_ui.validate(s, bad) is not None


def test_handle_save_sets_clears_and_ignores_unchanged():
    form = {
        "RESEARCH_NIGHTLY_MAX": "2",  # set (uncomment)
        "NTFY_SERVER": "",  # clear (absent -> noop)
        "secret_FRED_API_KEY": "",  # blank secret = unchanged
        "secret_EIA_API_KEY": "newkey42",  # set secret
        "clear_NTFY_TOPIC": "on",  # clear secret (sentinel present)
    }
    new_text, errors = config_ui.handle_save(ENV, form)
    assert errors == {}
    parsed = config_ui.parse_env(new_text)
    assert parsed["RESEARCH_NIGHTLY_MAX"] == "2"
    assert parsed["FRED_API_KEY"] == "oldsecret123"  # untouched
    assert parsed["EIA_API_KEY"] == "newkey42"
    assert "NTFY_TOPIC" not in parsed


def test_handle_save_all_or_nothing_on_error():
    form = {"RESEARCH_NIGHTLY_MAX": "99", "secret_EIA_API_KEY": "fine"}
    new_text, errors = config_ui.handle_save(ENV, form)
    assert new_text is None
    assert "RESEARCH_NIGHTLY_MAX" in errors
    # error text never echoes a secret value
    assert "fine" not in " ".join(errors.values())


def test_clear_checkbox_beats_typed_value():
    form = {"secret_FRED_API_KEY": "typedanyway", "clear_FRED_API_KEY": "on"}
    new_text, errors = config_ui.handle_save(ENV, form)
    assert errors == {}
    assert "FRED_API_KEY" not in config_ui.parse_env(new_text)


def test_metachar_values_are_single_quoted_and_roundtrip():
    form = {"secret_HEALTHCHECK_URL": "https://hc-ping.com/abc?ping=1&fail=2"}
    new_text, errors = config_ui.handle_save("", form)
    assert errors == {}
    assert "HEALTHCHECK_URL='https://hc-ping.com/abc?ping=1&fail=2'" in new_text
    assert (
        config_ui.parse_env(new_text)["HEALTHCHECK_URL"] == "https://hc-ping.com/abc?ping=1&fail=2"
    )


def test_simple_values_stay_bare():
    form = {"RESEARCH_NIGHTLY_MAX": "2"}
    new_text, errors = config_ui.handle_save("", form)
    assert "RESEARCH_NIGHTLY_MAX=2\n" in new_text and "'" not in new_text
