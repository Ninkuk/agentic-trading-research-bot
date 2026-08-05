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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "launchd"))
from dashboard_lib import health  # noqa: E402


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
    return health.dt.datetime.now(health.dt.UTC)


def test_fresh_and_zero_rows_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(health, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(health, "EMPTY_OK", set())

    result = health.stale_dbs(now, tmp_path)

    assert any(p["kind"] == "empty" for p in result)


def test_fresh_and_nonzero_rows_not_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 5)
    monkeypatch.setattr(health, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(health, "EMPTY_OK", set())

    result = health.stale_dbs(now, tmp_path)

    assert not any(p["kind"] == "empty" for p in result)


def test_fresh_and_zero_rows_but_allowlisted_not_flagged(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(health, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(health, "EMPTY_OK", {"fake.db"})

    result = health.stale_dbs(now, tmp_path)

    assert not any(p["kind"] == "empty" for p in result)


def test_unmapped_db_skips_count_check(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat(), "row_count", 0)
    monkeypatch.setattr(health, "ROW_COUNT_COL", {})
    monkeypatch.setattr(health, "EMPTY_OK", set())

    result = health.stale_dbs(now, tmp_path)

    assert not any(p["kind"] == "empty" for p in result)


def test_stale_and_empty_both_notes(tmp_path, monkeypatch, now):
    old = (now - health.dt.timedelta(days=30)).isoformat()
    _make_snapshots_db(tmp_path / "fake.db", old, "row_count", 0)
    monkeypatch.setattr(health, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(health, "EMPTY_OK", set())

    result = health.stale_dbs(now, tmp_path)

    assert any(p["kind"] == "empty" for p in result)
    assert any(p["kind"] == "stale" for p in result)


def test_missing_count_column_does_not_crash(tmp_path, monkeypatch, now):
    _make_snapshots_db(tmp_path / "fake.db", now.isoformat())  # no count column at all
    monkeypatch.setattr(health, "ROW_COUNT_COL", {"fake.db": "row_count"})
    monkeypatch.setattr(health, "EMPTY_OK", set())

    result = health.stale_dbs(now, tmp_path)

    assert not any(p["kind"] == "empty" for p in result)
