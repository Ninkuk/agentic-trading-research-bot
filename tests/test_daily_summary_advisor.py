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


def _dis(symbol="XOM", score_sum=-1, group_name="energy", strong=0):
    return {"symbol": symbol, "score_sum": score_sum, "group_name": group_name, "strong": strong}


def _cap(symbol="NVDA", cap_shares=3.2):
    return {"symbol": symbol, "cap_shares": cap_shares}


def test_disagree_weak_with_group():
    lines = daily_summary.format_advisor_lines(_book(), [_dis()], [], _header())
    assert "disagree: XOM -1 weak (energy)" in lines


def test_disagree_strong_uppercase():
    lines = daily_summary.format_advisor_lines(
        _book(), [_dis(score_sum=-5, strong=1)], [], _header()
    )
    assert "disagree: XOM -5 STRONG (energy)" in lines


def test_disagree_null_group_no_parens():
    lines = daily_summary.format_advisor_lines(_book(), [_dis(group_name=None)], [], _header())
    assert "disagree: XOM -1 weak" in lines
    assert "(" not in [line for line in lines if line.startswith("disagree")][0]


def test_disagree_multiple_stable_order():
    rows = [_dis(symbol="CVX", score_sum=-1), _dis(symbol="XOM", score_sum=-3)]
    lines = [
        line
        for line in daily_summary.format_advisor_lines(_book(), rows, [], _header())
        if line.startswith("disagree")
    ]
    # ordered by score_sum asc, then symbol: XOM(-3) before CVX(-1)
    assert lines == ["disagree: XOM -3 weak (energy)", "disagree: CVX -1 weak (energy)"]


def test_disagree_none():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert "disagree: none" in lines


def test_caps_present():
    lines = daily_summary.format_advisor_lines(
        _book(),
        [],
        [_cap(symbol="AMD", cap_shares=1.5), _cap(symbol="NVDA", cap_shares=3.2)],
        _header(),
    )
    assert "cap: AMD ≤ 1.50sh" in lines
    assert "cap: NVDA ≤ 3.20sh" in lines


def test_caps_none():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert "caps: none tonight" in lines


def test_caps_null_cap_shares_renders_na():
    # Bearish/ATR-less flags write cap_shares=NULL by design (long-only book).
    lines = daily_summary.format_advisor_lines(
        _book(), [], [_cap(symbol="XOM", cap_shares=None)], _header()
    )
    assert "cap: XOM ≤ n/a" in lines


def test_caps_mixed_null_and_normal():
    lines = daily_summary.format_advisor_lines(
        _book(),
        [],
        [_cap(symbol="XOM", cap_shares=None), _cap(symbol="NVDA", cap_shares=3.2)],
        _header(),
    )
    assert "cap: XOM ≤ n/a" in lines
    assert "cap: NVDA ≤ 3.20sh" in lines


def test_staleness_same_day_no_note():
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header())
    assert not any(line.startswith("(sized vs portfolio") for line in lines)


def test_staleness_stale_note(phoenix_tz):
    # portfolio Jul 06 10:30 Phoenix, run Jul 07 21:12 Phoenix → 1 day old.
    hdr = _header(
        portfolio_captured_at="2026-07-06T17:30:00+00:00", captured_at="2026-07-08T04:12:00+00:00"
    )
    lines = daily_summary.format_advisor_lines(_book(), [], [], hdr)
    assert "(sized vs portfolio from Jul 06 — 1d old)" in lines


def test_full_nominal_block(phoenix_tz):
    hdr = _header(
        portfolio_captured_at="2026-07-06T17:30:00+00:00", captured_at="2026-07-08T04:12:00+00:00"
    )
    lines = daily_summary.format_advisor_lines(_book(), [_dis()], [], hdr)
    assert lines == [
        "book: 0.21% risk · 2 positions · cov 1.0 · equity $200",
        "disagree: XOM -1 weak (energy)",
        "caps: none tonight",
        "(sized vs portfolio from Jul 06 — 1d old)",
    ]


def test_null_portfolio_captured_at_no_staleness_note():
    """When portfolio_captured_at is None (advisor ran before first portfolio
    sync), emit no staleness note and do not raise."""
    lines = daily_summary.format_advisor_lines(_book(), [], [], _header(portfolio_captured_at=None))
    assert not any(line.startswith("(sized vs portfolio") for line in lines)


def test_reader_unreadable_returns_note(monkeypatch):
    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("no such table: snapshots")

    monkeypatch.setattr(daily_summary.sqlite3, "connect", boom)
    assert daily_summary.advisor_digest() == ["advisor: unreadable (OperationalError)"]
