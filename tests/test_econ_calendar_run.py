import sqlite3

from sources.monitors.econ_calendar import run as runmod

NOW = "2026-08-01T00:00:00+00:00"


def _raw(release_id, dates):
    return [{"release_id": release_id, "release_name": "X", "date": d} for d in dates]


def test_run_happy_path_counts_and_writes(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-08-12"])

    sid, count = runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW)
    assert count == 1
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_skips_release_that_raises_without_leaking_secret(tmp_path, capsys):
    def fetch_one(release_id, api_key, today):
        if release_id == 10:
            raise RuntimeError("http://api?api_key=SECRET boom")
        return _raw(release_id, ["2026-08-12"])

    sid, count = runmod.run(
        str(tmp_path / "e.db"), only=["10", "46"], api_key="K", fetch_one=fetch_one, now_iso=NOW
    )
    assert count == 1  # 10 skipped, 46 written
    err = capsys.readouterr().err
    assert "skipping 10" in err
    assert "SECRET" not in err  # secret hygiene: only the type name


def test_run_only_and_exclude_select_ids(tmp_path):
    seen = []

    def fetch_one(release_id, api_key, today):
        seen.append(release_id)
        return _raw(release_id, ["2026-08-12"])

    runmod.run(
        str(tmp_path / "e.db"),
        only=["10", "46"],
        exclude=["46"],
        api_key="K",
        fetch_one=fetch_one,
        now_iso=NOW,
    )
    assert seen == [10]


def test_run_second_run_firms_up_not_duplicated(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-08-12"])

    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW)
    runmod.run(db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW)
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_run_keep_days_prunes_snapshots_not_future_events(tmp_path):
    db_path = str(tmp_path / "e.db")

    def fetch_one(release_id, api_key, today):
        return _raw(release_id, ["2026-12-31"])  # far-future event

    runmod.run(
        db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso="2026-01-01T00:00:00+00:00"
    )  # old snapshot
    runmod.run(
        db_path, only=["10"], api_key="K", fetch_one=fetch_one, now_iso=NOW, keep_days=30
    )  # prunes old
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
