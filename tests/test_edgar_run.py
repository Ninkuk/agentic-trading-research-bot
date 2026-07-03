import pytest

from edgar_screener.db import connect
from edgar_screener.run import run

TMAP = {1000623: {"ticker": "MATV", "title": "Mativ"}}


def _rows(form="4"):
    return [{"accession": "a1", "cik": 1000623, "company": "Mativ", "form": form,
             "bucket": "insider", "filed_date": "2025-06-02",
             "path": "edgar/data/1000623/a1.txt"},
            {"accession": "a2", "cik": 555, "company": "Private", "form": "D",
             "bucket": "other", "filed_date": "2025-06-02",
             "path": "edgar/data/555/a2.txt"}]


def test_run_joins_tickers_and_writes(tmp_path):
    db_path = str(tmp_path / "e.db")
    sid, n = run(db_path, index_date="2025-06-02",
                 fetch_index=lambda d: _rows(), fetch_map=lambda: TMAP,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 2
    conn = connect(db_path)
    got = dict(conn.execute("SELECT cik, ticker FROM filings").fetchall())
    assert got == {1000623: "MATV", 555: None}   # untickered stays NULL


def test_run_default_date_walks_back_to_latest(tmp_path):
    db_path = str(tmp_path / "e.db")
    calls = []

    def fake_index(d):
        calls.append(d)
        return _rows() if d == "2026-06-30" else None  # only this day exists

    run(db_path, fetch_index=fake_index, fetch_map=lambda: TMAP,
        now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT index_date FROM snapshots").fetchone()[0] == "2026-06-30"
    assert calls[:3] == ["2026-07-02", "2026-07-01", "2026-06-30"]


def test_run_default_date_walks_past_empty_index(tmp_path):
    # An index that exists but is empty ([], not None) must not stop the
    # walk-back: keep looking for a day that actually has filings rather than
    # storing a 0-filing snapshot for today.
    db_path = str(tmp_path / "e.db")
    calls = []

    def fake_index(d):
        calls.append(d)
        return _rows() if d == "2026-06-30" else []  # earlier days present-but-empty

    run(db_path, fetch_index=fake_index, fetch_map=lambda: TMAP,
        now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT index_date FROM snapshots").fetchone()[0] == "2026-06-30"
    assert calls[:3] == ["2026-07-02", "2026-07-01", "2026-06-30"]


def test_run_explicit_missing_date_raises(tmp_path):
    db_path = str(tmp_path / "e.db")
    with pytest.raises(RuntimeError, match="no EDGAR index for 2025-06-01"):
        run(db_path, index_date="2025-06-01",
            fetch_index=lambda d: None, fetch_map=lambda: TMAP,
            now_iso="2026-07-02T00:00:00+00:00")


def test_run_empty_index_warns_and_writes_zero(tmp_path, capsys):
    db_path = str(tmp_path / "e.db")
    sid, n = run(db_path, index_date="2025-06-02",
                 fetch_index=lambda d: [], fetch_map=lambda: TMAP,
                 now_iso="2026-07-02T00:00:00+00:00")
    assert n == 0
    assert "0 filings" in capsys.readouterr().err
    conn = connect(db_path)
    assert conn.execute("SELECT filing_count FROM snapshots").fetchone()[0] == 0


def test_run_ticker_map_failure_writes_nothing(tmp_path):
    db_path = str(tmp_path / "e.db")

    def boom():
        raise RuntimeError("map down")

    with pytest.raises(RuntimeError, match="map down"):
        run(db_path, index_date="2025-06-02",
            fetch_index=lambda d: _rows(), fetch_map=boom,
            now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0


def test_run_second_run_appends_history(tmp_path):
    db_path = str(tmp_path / "e.db")
    run(db_path, index_date="2025-06-02", fetch_index=lambda d: _rows(),
        fetch_map=lambda: TMAP, now_iso="2026-07-01T00:00:00+00:00")
    run(db_path, index_date="2025-06-03", fetch_index=lambda d: _rows(),
        fetch_map=lambda: TMAP, now_iso="2026-07-02T00:00:00+00:00")
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 2
