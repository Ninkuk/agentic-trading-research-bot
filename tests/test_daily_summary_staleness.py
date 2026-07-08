"""Tests for the count-based "silent-empty fetch" freshness check (plan 002).

`stale_dbs` judges freshness on `captured_at` alone, so a fresh snapshot with
zero rows (DNS blip, endpoint schema drift, expired token) reads as healthy.
These tests exercise the added count-column check independently of the
freshness/age logic already covered by test_daily_summary_resilience.py.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

# daily_summary.py lives in deploy/launchd and inserts the repo root on
# sys.path itself at import; we only need its own dir on the path to import it.
DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402


def _make_snapshots_db(path, captured_at, count_col=None, count_value=None):
    with sqlite3.connect(path) as conn:
        cols = "id INTEGER PRIMARY KEY, captured_at TEXT"
        if count_col:
            cols += f", {count_col} INTEGER"
        conn.execute(f"CREATE TABLE snapshots ({cols})")
        if count_col:
            conn.execute(
                f"INSERT INTO snapshots (captured_at, {count_col}) VALUES (?, ?)",
                (captured_at, count_value),
            )
        else:
            conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (captured_at,))
        conn.commit()


@pytest.fixture
def now():
    return daily_summary.dt.datetime.now(daily_summary.dt.UTC)


def test_fresh_and_zero_rows_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", set())

    result = daily_summary.stale_dbs(now)

    assert any("0 rows" in line for line in result)


def test_fresh_and_nonzero_rows_not_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 5)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", set())

    result = daily_summary.stale_dbs(now)

    assert not any("0 rows" in line for line in result)


def test_fresh_and_zero_rows_but_allowlisted_not_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", {"fake.db"})

    result = daily_summary.stale_dbs(now)

    assert not any("0 rows" in line for line in result)


def test_unmapped_db_skips_count_check(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", set())

    result = daily_summary.stale_dbs(now)

    assert not any("0 rows" in line for line in result)


def test_stale_and_empty_both_notes(tmp_path, monkeypatch, now):
    old = (now - daily_summary.dt.timedelta(days=30)).isoformat()
    _make_snapshots_db(tmp_path / "fake.db", old, "row_count", 0)
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", set())

    result = daily_summary.stale_dbs(now)

    assert any("0 rows" in line for line in result)


def test_missing_count_column_does_not_crash(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat())  # no count column at all
    monkeypatch.setattr(daily_summary, "DATA", tmp_path)
    monkeypatch.setattr(daily_summary, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(daily_summary, "EMPTY_OK", set())

    result = daily_summary.stale_dbs(now)

    assert not any("0 rows" in line for line in result)
