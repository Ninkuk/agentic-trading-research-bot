# tests/test_finra_short_interest_run.py
from datetime import datetime, timezone

from sources.screeners.finra_short_interest import db, run as run_mod

NOW = "2024-08-15T00:00:00+00:00"


def _rows(s):
    """One liquid row whose settlement_date == s."""
    return [{"symbol": "AAL", "issue_name": "AMERICAN AIRLINES",
             "settlement_date": s, "current_short_qty": 1500000,
             "previous_short_qty": 1200000, "avg_daily_volume": 500000,
             "days_to_cover": 3.0, "change_pct": 25.0,
             "revision_flag": None, "market_class": "NNM"}]


def test_settlement_dates_rolls_weekend_back_to_friday():
    # 2024-06-15 is Saturday -> 06-14; 2024-06-30 is Sunday -> 06-28;
    # 2024-07-15 Mon, 2024-07-31 Wed -> unchanged.
    assert run_mod.settlement_dates("2024-06-01", "2024-07-31") == [
        "2024-06-14", "2024-06-28", "2024-07-15", "2024-07-31"]


def test_settlement_dates_bounds_are_inclusive_and_clipped():
    # start after the 15th drops that month's mid-month settlement.
    assert run_mod.settlement_dates("2024-06-20", "2024-07-16") == [
        "2024-06-28", "2024-07-15"]


def test_default_start_is_about_twelve_months_back():
    now = datetime(2026, 7, 3, tzinfo=timezone.utc)
    assert run_mod._default_start(now, days=365) == "2025-07-03"


def test_run_ingests_published_and_skips_unpublished(tmp_path):
    published = {"2024-06-14"}

    def fetch_settlement(s):
        return _rows(s) if s in published else None

    dbp = str(tmp_path / "si.db")
    _, sc, rc = run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                            fetch_settlement=fetch_settlement)
    assert (sc, rc) == (1, 1)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT COUNT(*) FROM short_interest").fetchone()[0] == 1


def test_run_incremental_skips_stored_refetches_last_two(tmp_path):
    # range 2024-06-01..2024-08-15 -> settlements:
    #   06-14, 06-28, 07-15, 07-31, 08-15  (five)
    def make_fs(sink):
        def fetch_settlement(s):
            sink.append(s)
            return _rows(s)
        return fetch_settlement

    dbp = str(tmp_path / "si.db")
    first = []
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                fetch_settlement=make_fs(first))
    assert len(first) == 5

    second = []
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW,
                fetch_settlement=make_fs(second))
    assert second == ["2024-07-31", "2024-08-15"]   # only trailing two refetched


def test_run_full_refetches_every_settlement(tmp_path):
    def make_fs(sink):
        def fetch_settlement(s):
            sink.append(s)
            return _rows(s)
        return fetch_settlement

    dbp = str(tmp_path / "si.db")
    run_mod.run(dbp, start="2024-06-01", now_iso=NOW, fetch_settlement=make_fs([]))
    second = []
    run_mod.run(dbp, start="2024-06-01", full=True, now_iso=NOW,
                fetch_settlement=make_fs(second))
    assert len(second) == 5


def test_run_skips_failing_settlement_and_logs_class_only(tmp_path, capsys):
    def fetch_settlement(s):
        if s == "2024-06-14":
            raise RuntimeError("boom-secret")
        if s == "2024-06-28":
            return _rows(s)
        return None

    dbp = str(tmp_path / "si.db")
    _, sc, _ = run_mod.run(dbp, start="2024-06-01",
                           now_iso="2024-07-01T00:00:00+00:00",
                           fetch_settlement=fetch_settlement)
    assert sc == 1
    err = capsys.readouterr().err
    assert "2024-06-14" in err
    assert "RuntimeError" in err
    assert "boom-secret" not in err          # secret-hygiene: no str(e)


def test_run_all_unpublished_writes_zero_snapshot(tmp_path):
    dbp = str(tmp_path / "si.db")
    _, sc, rc = run_mod.run(dbp, start="2024-06-01",
                            now_iso="2024-06-20T00:00:00+00:00",
                            fetch_settlement=lambda s: None)
    assert (sc, rc) == (0, 0)
    conn = db.connect(dbp)
    assert tuple(conn.execute(
        "SELECT settlement_count, row_count FROM snapshots").fetchone()) == (0, 0)


def test_run_keep_days_prunes_old_snapshots(tmp_path):
    dbp = str(tmp_path / "si.db")
    run_mod.run(dbp, start="2024-06-01",
                now_iso="2024-06-20T00:00:00+00:00",
                fetch_settlement=lambda s: None)
    conn = db.connect(dbp)
    db.write_snapshot(conn, "2000-01-01T00:00:00+00:00", 0, 0)
    conn.close()
    run_mod.run(dbp, start="2024-06-01",
                now_iso="2024-06-20T00:00:00+00:00", keep_days=30,
                fetch_settlement=lambda s: None)
    conn = db.connect(dbp)
    assert conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE captured_at < '2020-01-01'"
    ).fetchone()[0] == 0
