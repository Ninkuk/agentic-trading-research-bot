import sqlite3

from sources.screeners.finra_ats import run as runmod

NOW = "2026-07-03T00:00:00+00:00"


def _row(week, symbol="A", mpid="M1"):
    return {"week_start": week, "symbol": symbol, "mpid": mpid,
            "ats_name": "ATS", "trade_count": 1, "share_quantity": 100,
            "tier": "T1"}


def test_weeks_in_range_monday_anchored():
    wks = runmod.weeks_in_range("2026-06-10", "2026-06-24")   # Wed .. Wed
    assert wks == ["2026-06-08", "2026-06-15", "2026-06-22"]  # Mondays


def test_run_delay_aware_end_and_counts(tmp_path):
    db_path = str(tmp_path / "a.db")
    fetched = []

    def fetch_week(week_start):
        fetched.append(week_start)
        return [_row(week_start)]

    sid, wc, rc = runmod.run(db_path, start="2026-06-01",
                             fetch_week=fetch_week, now_iso=NOW)
    # newest week must be floored ~2 weeks before 2026-07-03 -> no 2026-06-29+
    assert all(w <= "2026-06-22" for w in fetched)
    assert wc == len(fetched) and rc == wc


def test_run_incremental_skips_stored_but_refetches_trailing(tmp_path):
    db_path = str(tmp_path / "a.db")
    runmod.run(db_path, start="2026-06-01",
               fetch_week=lambda w: [_row(w)], now_iso=NOW)
    second = []

    def fetch_week(week_start):
        second.append(week_start)
        return [_row(week_start)]

    runmod.run(db_path, start="2026-06-01", fetch_week=fetch_week, now_iso=NOW)
    # only the trailing 2 stored weeks are re-fetched on the second run
    assert len(second) == 2


def test_run_none_week_skipped_and_failure_hides_secret(tmp_path, capsys):
    db_path = str(tmp_path / "a.db")

    def fetch_week(week_start):
        if week_start == "2026-06-08":
            return None                          # not published -> skip
        if week_start == "2026-06-15":
            raise RuntimeError("https://api.finra.org?x=SECRET boom")
        return [_row(week_start)]

    sid, wc, rc = runmod.run(db_path, start="2026-06-01",
                             fetch_week=fetch_week, now_iso=NOW)
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "SECRET" not in err
    conn = sqlite3.connect(db_path)
    stored = {r[0] for r in conn.execute("SELECT week_start FROM weeks")}
    assert "2026-06-08" not in stored and "2026-06-15" not in stored


def test_run_keep_days_prunes_snapshots_not_facts(tmp_path):
    db_path = str(tmp_path / "a.db")
    runmod.run(db_path, start="2026-06-01", fetch_week=lambda w: [_row(w)],
               now_iso="2026-01-01T00:00:00+00:00")
    runmod.run(db_path, start="2026-06-01", fetch_week=lambda w: [_row(w)],
               now_iso=NOW, keep_days=30)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM ats_volume").fetchone()[0] >= 1
