"""Glossary parser tests: fixture-driven plus a live check against the real
docs/GLOSSARY.md so a formatting drift in the doc breaks loudly here."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "deploy" / "launchd"))
from dashboard_lib.glossary import load_glossary  # noqa: E402

FIXTURE = """# Glossary

Intro prose that must be ignored.

**Screener** — a small program that visits one
official data source.

**Fails-to-deliver (FTD)** — trades where the seller didn't
hand over the shares on time.

**Z-score** — how unusual is today's number?
"""


def test_parses_terms_and_joins_lines(tmp_path):
    p = tmp_path / "GLOSSARY.md"
    p.write_text(FIXTURE, encoding="utf-8")
    g = load_glossary(p)
    assert g["Screener"] == "a small program that visits one official data source."
    assert g["Z-score"] == "how unusual is today's number?"


def test_parenthetical_alternate_gets_own_key(tmp_path):
    p = tmp_path / "GLOSSARY.md"
    p.write_text(FIXTURE, encoding="utf-8")
    g = load_glossary(p)
    assert g["FTD"] == g["Fails-to-deliver"]
    assert "shares on time" in g["FTD"]


def test_missing_file_returns_empty(tmp_path):
    assert load_glossary(tmp_path / "nope.md") == {}


def test_real_glossary_parses_nonempty():
    g = load_glossary(REPO / "docs" / "GLOSSARY.md")
    assert len(g) >= 10
    assert all(v.strip() for v in g.values()), "no empty definitions"


def test_real_glossary_covers_dashboard_terms():
    g = load_glossary(REPO / "docs" / "GLOSSARY.md")
    assert {"ATR", "Coverage", "Hit rate", "CI"} <= set(g)
