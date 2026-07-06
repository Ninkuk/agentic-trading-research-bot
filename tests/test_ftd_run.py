# tests/test_ftd_run.py
from datetime import UTC, datetime

from sources.screeners.ftd_screener import db
from sources.screeners.ftd_screener import run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _one_row(period):
    """One fail row whose settlement_date falls inside `period` (a=05th,
    b=20th) — keeps (cusip, date) unique across periods."""
    day = "05" if period[6] == "a" else "20"
    d = f"{period[:4]}-{period[4:6]}-{day}"
    return [
        {
            "cusip": "A",
            "settlement_date": d,
            "symbol": "A",
            "quantity": 10,
            "price": 1.0,
            "description": "A",
            "dollar_value": 10.0,
        }
    ]


def test_periods_in_range_inclusive_both_halves():
    assert run_mod.periods_in_range("2025-11", "2026-01") == [
        "202511a",
        "202511b",
        "202512a",
        "202512b",
        "202601a",
        "202601b",
    ]


def test_default_start_is_24_months_back():
    now = datetime(2026, 7, 3, tzinfo=UTC)
    assert run_mod._default_start(now) == "2024-07"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"202606b"}

    def fetch_period(period):
        return (_one_row(period), 1) if period in published else None

    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(dbp, start="2026-06", now_iso=NOW, fetch_period=fetch_period)
    assert (pc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM fails").fetchone()[0] == 1


def test_run_incremental_skips_old_stored_refetches_last_two(tmp_path):
    def make_fp(sink):
        def fetch_period(period):
            sink.append(period)
            return (_one_row(period), 1)

        return fetch_period

    dbp = str(tmp_path / "ftd.db")
    now = "2026-03-31T00:00:00+00:00"  # range 2026-01..2026-03 -> 6 periods
    first = []
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp(first))
    assert len(first) == 6  # first run fetches all published

    second = []
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp(second))
    assert second == ["202603a", "202603b"]  # only the trailing two refetched


def test_run_full_refetches_every_period(tmp_path):
    def make_fp(sink):
        def fetch_period(period):
            sink.append(period)
            return (_one_row(period), 1)

        return fetch_period

    dbp = str(tmp_path / "ftd.db")
    now = "2026-03-31T00:00:00+00:00"
    run_mod.run(dbp, start="2026-01", now_iso=now, fetch_period=make_fp([]))
    second = []
    run_mod.run(dbp, start="2026-01", full=True, now_iso=now, fetch_period=make_fp(second))
    assert len(second) == 6


def test_run_skips_failing_period_and_continues(tmp_path, capsys):
    def fetch_period(period):
        if period == "202606a":
            raise RuntimeError("boom")
        if period == "202606b":
            return (_one_row(period), 1)
        return None

    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(
        dbp, start="2026-06", now_iso="2026-06-30T00:00:00+00:00", fetch_period=fetch_period
    )
    assert pc == 1
    assert "202606a" in capsys.readouterr().err


def test_run_warns_on_trailer_mismatch(tmp_path, capsys):
    def fetch_period(period):
        return (_one_row(period), 999) if period == "202606b" else None

    run_mod.run(
        str(tmp_path / "ftd.db"),
        start="2026-06",
        now_iso="2026-06-30T00:00:00+00:00",
        fetch_period=fetch_period,
    )
    assert "trailer" in capsys.readouterr().err.lower()


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "ftd.db")
    sid, pc, rc = run_mod.run(dbp, start="2026-06", now_iso=NOW, fetch_period=lambda period: None)
    assert (pc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute("SELECT period_count, row_count FROM snapshots").fetchone()) == (0, 0)
