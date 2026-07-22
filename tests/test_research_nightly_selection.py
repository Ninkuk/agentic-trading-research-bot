"""Selection logic for the nightly research loop: pure functions over plain
data — no network, no subprocess, fake DBs only."""

import sqlite3
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import research_nightly  # noqa: E402

TODAY = "2026-07-22"  # phx date of a 2026-07-23T05:12:00+00:00 run (10:12pm Phoenix)


def _mkdb(path, script):
    conn = sqlite3.connect(path)
    conn.executescript(script)
    conn.commit()
    conn.close()


def test_list_theses_newest_date_wins(tmp_path):
    (tmp_path / "AAPL-2026-06-01.md").write_text("x")
    (tmp_path / "AAPL-2026-07-10.md").write_text("x")
    (tmp_path / "BRK.B-2026-07-01.md").write_text("x")
    (tmp_path / "README.md").write_text("not a thesis")
    (tmp_path / "verdicts.log").write_text("not a thesis")
    assert research_nightly.list_theses(tmp_path) == {
        "AAPL": "2026-07-10",
        "BRK.B": "2026-07-01",
    }


def test_list_theses_missing_dir_is_empty(tmp_path):
    assert research_nightly.list_theses(tmp_path / "nope") == {}


def test_read_flagged_reads_view(tmp_path):
    db = tmp_path / "composite.db"
    _mkdb(
        db,
        """CREATE TABLE scorecard (symbol TEXT, score_sum INT);
           INSERT INTO scorecard VALUES ('EOSE', 4), ('CRML', -3);
           CREATE VIEW v_flagged AS SELECT * FROM scorecard;""",
    )
    assert sorted(research_nightly.read_flagged(str(db))) == ["CRML", "EOSE"]


def test_read_flagged_missing_db_is_empty(tmp_path):
    assert research_nightly.read_flagged(str(tmp_path / "absent.db")) == []


def test_read_held_missing_view_is_empty(tmp_path):
    db = tmp_path / "portfolio.db"
    _mkdb(db, "CREATE TABLE t (x);")
    assert research_nightly.read_held(str(db)) == []


def test_priority_new_flags_then_stale_flags_then_stale_held():
    theses = {"OLD": "2026-06-01", "HELD1": "2026-05-01", "FRESH": "2026-07-20"}
    got = research_nightly.select_candidates(
        flagged=["NEW", "OLD", "FRESH"],
        held=["HELD1", "FRESH"],
        theses=theses,
        today=TODAY,
        max_n=10,
        stale_days=30,
    )
    # NEW: flagged, never researched. OLD: flagged, stale. HELD1: held, stale.
    # FRESH excluded everywhere (thesis 2 days old).
    assert got == ["NEW", "OLD", "HELD1"]


def test_cap_and_dedupe():
    got = research_nightly.select_candidates(
        flagged=["B", "A"],
        held=["A", "B"],
        theses={},
        today=TODAY,
        max_n=2,
        stale_days=30,
    )
    # Both are never-researched flags (bucket 1, sorted); held bucket must not
    # re-add them; cap applies after ordering.
    assert got == ["A", "B"]


def test_held_never_researched_counts_as_stale():
    got = research_nightly.select_candidates(
        flagged=[], held=["ZZZ"], theses={}, today=TODAY, max_n=5, stale_days=30
    )
    assert got == ["ZZZ"]


def test_staleness_boundary_is_phoenix_date_math():
    # stale_days=30 from 2026-07-22 → cutoff 2026-06-22. A thesis dated
    # exactly on the cutoff is NOT stale (age == window, not older).
    theses = {"EDGE": "2026-06-22", "STALE": "2026-06-21"}
    got = research_nightly.select_candidates(
        flagged=["EDGE", "STALE"],
        held=[],
        theses=theses,
        today=TODAY,
        max_n=5,
        stale_days=30,
    )
    assert got == ["STALE"]
