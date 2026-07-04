import sqlite3

from sources.monitors.fomc_calendar import fetch
from sources.monitors.fomc_calendar import run as runmod

NOW = "2026-01-01T00:00:00+00:00"
MEETING = {"start_date": "2026-03-17", "end_date": "2026-03-18",
           "status": "tentative", "has_press_conference": True}


def test_run_end_to_end_counts_and_snapshots(tmp_path):
    db_path = str(tmp_path / "fomc.db")
    sid, count = runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)
    assert count == 5                          # meeting+sep+minutes+2 blackout
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_parse_error_aborts_loudly(tmp_path):
    def boom():
        raise fetch.FomcCalendarParseError("page structure changed")

    try:
        runmod.run(str(tmp_path / "fomc.db"), fetch_calendar=boom, now_iso=NOW)
        assert False, "expected FomcCalendarParseError to propagate"
    except fetch.FomcCalendarParseError:
        pass


def test_run_transient_fetch_failure_preserves_calendar_and_hides_secret(
        tmp_path, capsys):
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING], now_iso=NOW)  # seed

    def boom():
        raise RuntimeError("https://fed?token=SECRET boom")

    runmod.run(db_path, fetch_calendar=boom, now_iso=NOW)
    err = capsys.readouterr().err
    assert "SECRET" not in err and "RuntimeError" in err
    conn = sqlite3.connect(db_path)                # calendar preserved
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 5


def test_run_keep_days_prunes_snapshots_not_events(tmp_path):
    db_path = str(tmp_path / "fomc.db")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, fetch_calendar=lambda: [MEETING],
               now_iso="2026-06-01T00:00:00+00:00", keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] >= 1
