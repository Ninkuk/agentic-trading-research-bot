# tests/test_finra_shorts_run.py
from datetime import UTC, datetime

from sources.screeners.finra_short_volume import db
from sources.screeners.finra_short_volume import run as run_mod

NOW = "2026-07-03T00:00:00+00:00"


def _rows(day):
    """One liquid, elevated row whose date == day (keeps (symbol, date) unique)."""
    return [
        {
            "symbol": "AAL",
            "date": day,
            "short_volume": 120,
            "short_exempt_volume": 0,
            "total_volume": 200,
            "short_ratio": 0.6,
            "market": "Q",
        }
    ]


def test_days_in_range_inclusive():
    assert run_mod.days_in_range("2026-06-29", "2026-07-02") == [
        "2026-06-29",
        "2026-06-30",
        "2026-07-01",
        "2026-07-02",
    ]


def test_default_start_is_about_six_months_back():
    now = datetime(2026, 7, 3, tzinfo=UTC)
    assert run_mod._default_start(now, days=183) == "2026-01-01"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"2026-06-30"}

    def fetch_day(day):
        return _rows(day) if day in published else None

    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW, fetch_day=fetch_day)
    assert (dc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute("SELECT COUNT(*) FROM short_volume").fetchone()[0] == 1


def test_run_incremental_skips_old_stored_refetches_last_two(tmp_path):
    def make_fd(sink):
        def fetch_day(day):
            sink.append(day)
            return _rows(day)

        return fetch_day

    dbp = str(tmp_path / "sv.db")
    now = "2026-01-05T00:00:00+00:00"  # range 2026-01-01..2026-01-05
    first = []
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd(first))
    assert len(first) == 5  # all five days fetched

    second = []
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd(second))
    assert second == ["2026-01-04", "2026-01-05"]  # only trailing two refetched


def test_run_full_refetches_every_day(tmp_path):
    def make_fd(sink):
        def fetch_day(day):
            sink.append(day)
            return _rows(day)

        return fetch_day

    dbp = str(tmp_path / "sv.db")
    now = "2026-01-05T00:00:00+00:00"
    run_mod.run(dbp, start="2026-01-01", now_iso=now, fetch_day=make_fd([]))
    second = []
    run_mod.run(dbp, start="2026-01-01", full=True, now_iso=now, fetch_day=make_fd(second))
    assert len(second) == 5


def test_run_skips_failing_day_and_continues(tmp_path, capsys):
    def fetch_day(day):
        if day == "2026-06-30":
            raise RuntimeError("boom")
        if day == "2026-07-01":
            return _rows(day)
        return None

    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW, fetch_day=fetch_day)
    assert dc == 1
    err = capsys.readouterr().err
    assert "2026-06-30" in err
    assert "RuntimeError" in err
    assert "boom" not in err


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "sv.db")
    _, dc, rc = run_mod.run(dbp, start="2026-06-29", now_iso=NOW, fetch_day=lambda day: None)
    assert (dc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute("SELECT day_count, row_count FROM snapshots").fetchone()) == (0, 0)


def test_run_keep_days_prunes_old_snapshots(tmp_path):
    dbp = str(tmp_path / "sv.db")
    # Create schema and one recent snapshot
    run_mod.run(dbp, start="2026-06-29", now_iso=NOW, fetch_day=lambda day: None)
    # Directly insert an old snapshot
    conn = db.connect(dbp)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 0, 0)
    conn.close()
    # Verify old snapshot exists
    conn = db.connect(dbp)
    cnt_before = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert cnt_before == 2  # recent + old
    conn.close()
    # Run with keep_days=30 to prune
    run_mod.run(dbp, start="2026-06-29", now_iso=NOW, keep_days=30, fetch_day=lambda day: None)
    # Assert old snapshot is gone
    conn = db.connect(dbp)
    cnt_old = conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE captured_at < '2020-01-01'"
    ).fetchone()[0]
    assert cnt_old == 0
    conn.close()
