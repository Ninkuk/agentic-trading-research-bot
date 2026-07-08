"""Tests for the advisor digest block in the nightly ntfy summary.

Exercises the pure `format_advisor_lines` with hand-built dict rows (no DB,
no network) plus one reader-resilience test.
"""

import os
import sqlite3  # noqa: F401
import sys
import time
from pathlib import Path

import pytest

# daily_summary.py lives in deploy/launchd and inserts the repo root on
# sys.path itself at import; we only need its own dir on the path to import it.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


@pytest.fixture
def phoenix_tz():
    """Pin the process TZ to America/Phoenix so staleness-date assertions are
    deterministic on any host. The advisor slot runs on a Phoenix Mac mini, so
    this mirrors production; the digest converts UTC timestamps to local dates."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "America/Phoenix"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


def _book(positions=2, heat_pct=0.0021, heat_coverage=1.0, equity=200.12):
    return {
        "positions": positions,
        "heat_pct": heat_pct,
        "heat_coverage": heat_coverage,
        "equity": equity,
    }


def _header(
    portfolio_captured_at="2026-07-08T04:12:02+00:00",
    captured_at="2026-07-08T04:12:02+00:00",
    sources_failed=0,
):
    return {
        "portfolio_captured_at": portfolio_captured_at,
        "captured_at": captured_at,
        "sources_failed": sources_failed,
    }


def test_no_snapshot_returns_single_line():
    assert daily_summary.format_advisor_lines(None, [], [], None) == ["advisor: no snapshot"]


def test_book_line_nominal():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert lines[0] == "book: 0.21% risk · 2 positions · cov 1.0 · equity $200"


def test_book_line_percent_precision():
    assert daily_summary.format_advisor_lines(_book(heat_pct=0.00008), [], [], _header())[
        0
    ].startswith("book: 0.01% risk")
    assert daily_summary.format_advisor_lines(_book(heat_pct=0.0), [], [], _header())[0].startswith(
        "book: 0.00% risk"
    )


def test_book_line_singular_position():
    assert (
        "1 position ·"
        in daily_summary.format_advisor_lines(_book(positions=1), [], [], _header())[0]
    )


def test_book_line_null_fields():
    line = daily_summary.format_advisor_lines(
        _book(heat_coverage=None, equity=None), [], [], _header()
    )[0]
    assert "cov n/a" in line
    assert "equity ?" in line


def test_book_line_empty_book():
    # 0 positions → v_book_heat's SUM(heat_pct)/heat_coverage are NULL
    line = daily_summary.format_advisor_lines(
        _book(positions=0, heat_pct=None, heat_coverage=None), [], [], _header()
    )[0]
    assert line == "book: n/a risk · 0 positions · cov n/a · equity $200"


def test_sources_failed_note():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header(sources_failed=2))
    assert "advisor: 2 sources failed" in lines
