"""Render-layer tests: masking is asserted, never eyeballed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config_ui  # noqa: E402

PLANTED = "supersecretvalue99"


def _page(values=None, errors=None, saved=False):
    return config_ui.render_page(values or {}, errors or {}, "tok123", saved=saved)


def test_mask_rules():
    assert config_ui.mask("supersecretvalue99") == "••••ue99"
    assert config_ui.mask("short") == "••••"


def test_full_secret_never_in_html():
    html = _page(values={"FRED_API_KEY": PLANTED})
    assert PLANTED not in html
    assert "••••ue99" in html


def test_sentinel_renders_as_not_set():
    html = _page(values={"EIA_API_KEY": "ZZ_EIA_API_KEY_ZZ"})
    assert "ZZ_EIA_API_KEY_ZZ" not in html
    assert "not set" in html.lower()


def test_csrf_token_and_sections_present():
    html = _page()
    assert 'name="csrf" value="tok123"' in html
    assert "Tunables" in html and "API keys" in html


def test_nonsecret_value_and_enum_render():
    html = _page(values={"RESEARCH_NIGHTLY_MAX": "2", "RESEARCH_NIGHTLY_MODEL": "sonnet"})
    assert 'name="RESEARCH_NIGHTLY_MAX" value="2"' in html
    assert '<option value="sonnet" selected>' in html


def test_error_and_saved_banner():
    assert "must be between" in _page(errors={"RESEARCH_NIGHTLY_MAX": "must be between 0 and 10"})
    assert "Saved." in _page(saved=True)
    assert "Saved." not in _page()


def test_help_and_signup_links_survive():
    html = _page()
    assert "https://fred.stlouisfed.org" in html
    assert "0 disables the run" in html
