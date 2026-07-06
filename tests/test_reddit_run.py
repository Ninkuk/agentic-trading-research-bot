import pytest

from sources.screeners.reddit_screener.db import connect
from sources.screeners.reddit_screener.run import run


def _mkrows(ticker, mentions):
    return [
        {
            "ticker": ticker,
            "name": ticker,
            "rank": 1,
            "mentions": mentions,
            "upvotes": mentions * 2,
            "rank_24h_ago": 1,
            "mentions_24h_ago": mentions,
        }
    ]


def test_run_writes_one_snapshot_per_filter_sharing_capture(tmp_path):
    db_path = str(tmp_path / "r.db")

    def fake_fetch(filter_):
        return _mkrows("MU" if filter_ == "all-stocks" else "AAA", 5)

    results = run(
        db_path,
        filters=["all-stocks", "4chan"],
        fetch_filter=fake_fetch,
        now_iso="2026-07-02T00:00:00+00:00",
    )
    assert len(results) == 2
    conn = connect(db_path)
    rows = conn.execute("SELECT filter, captured_at FROM snapshots ORDER BY id").fetchall()
    assert rows == [
        ("all-stocks", "2026-07-02T00:00:00+00:00"),
        ("4chan", "2026-07-02T00:00:00+00:00"),
    ]


def test_run_warns_on_empty_filter_but_still_writes_snapshot(tmp_path, capsys):
    db_path = str(tmp_path / "r.db")

    def fake_fetch(filter_):
        return []

    run(
        db_path,
        filters=["all-stocks"],
        fetch_filter=fake_fetch,
        now_iso="2026-07-02T00:00:00+00:00",
    )
    assert "warning" in capsys.readouterr().err.lower()
    conn = connect(db_path)
    assert conn.execute("SELECT ticker_count FROM snapshots").fetchone()[0] == 0


def test_run_second_run_appends_history(tmp_path):
    db_path = str(tmp_path / "r.db")

    run(
        db_path,
        filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 10),
        now_iso="2026-07-01T00:00:00+00:00",
    )
    run(
        db_path,
        filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 20),
        now_iso="2026-07-02T00:00:00+00:00",
    )

    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
    latest = conn.execute("SELECT mentions FROM v_latest WHERE ticker='MU'").fetchone()[0]
    assert latest == 20


def test_run_keep_days_prunes_through_run(tmp_path):
    db_path = str(tmp_path / "r.db")
    run(
        db_path,
        filters=["all-stocks"],
        fetch_filter=lambda f: _mkrows("MU", 10),
        now_iso="2026-06-01T00:00:00+00:00",
    )
    run(
        db_path,
        filters=["all-stocks"],
        keep_days=7,
        fetch_filter=lambda f: _mkrows("MU", 20),
        now_iso="2026-07-02T00:00:00+00:00",
    )
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 1


def test_run_first_filter_failure_writes_no_snapshot(tmp_path):
    db_path = str(tmp_path / "r.db")

    def failing_fetch(filter_):
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        run(
            db_path,
            filters=["all-stocks"],
            fetch_filter=failing_fetch,
            now_iso="2026-07-02T00:00:00+00:00",
        )
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_run_partial_failure_keeps_earlier_filter(tmp_path):
    db_path = str(tmp_path / "r.db")

    def fetch(filter_):
        if filter_ == "4chan":
            raise RuntimeError("boom")
        return _mkrows("MU", 5)

    with pytest.raises(RuntimeError):
        run(
            db_path,
            filters=["all-stocks", "4chan"],
            fetch_filter=fetch,
            now_iso="2026-07-02T00:00:00+00:00",
        )
    conn = connect(db_path)
    filters = [r[0] for r in conn.execute("SELECT filter FROM snapshots").fetchall()]
    assert filters == ["all-stocks"]
