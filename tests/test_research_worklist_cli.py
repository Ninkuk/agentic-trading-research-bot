import json
import sqlite3

import pytest

from tools.research import worklist

VLOG = (
    "# Format: <YYYY-MM-DD> <TICKER> <VERDICT> ... [reopen=...]\n"
    "2026-07-27 NICE UNPROVEN conditions=4 reopen=2026-08-05:q2-print\n"
    "2026-07-30 INTU UNPROVEN conditions=5 reopen=2026-08-20:fy27-guide\n"
    "2026-07-01 GFI UNPROVEN conditions=4 reopen=event:tarkwa-renewal\n"
)


@pytest.fixture
def research_dir(tmp_path):
    d = tmp_path / "research"
    d.mkdir()
    (d / "verdicts.log").write_text(VLOG)
    (d / "NICE-2026-07-27.md").write_text("x")
    (d / "INTU-2026-07-30.md").write_text("x")
    return d


def test_read_verdicts_missing_file_names_the_error(tmp_path):
    newest, err = worklist.read_verdicts(tmp_path / "nope")
    assert newest == {}
    assert err == "FileNotFoundError"


def test_read_candidates_missing_db_names_the_error(tmp_path):
    symbols, err = worklist.read_candidates(str(tmp_path / "nope.db"))
    assert symbols == []
    assert err is not None
    # Secret hygiene: the exception CLASS only, never a path or a message.
    assert str(tmp_path) not in err


def test_build_splits_new_and_due(research_dir, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["NICE", "LDOS", "CI"], None))
    doc = worklist.build("ignored.db", research_dir, "2026-08-05", "both", None)
    assert doc["new"] == ["LDOS", "CI"]
    assert [r[0] for r in doc["reopens"]] == ["NICE"]


def test_build_kind_filters(research_dir, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS"], None))
    assert worklist.build("x", research_dir, "2026-08-05", "new", None)["reopens"] == []
    assert worklist.build("x", research_dir, "2026-08-05", "reopen", None)["new"] == []


def test_build_max_reports_what_it_dropped(research_dir, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS", "CI", "BWA"], None))
    doc = worklist.build("x", research_dir, "2026-08-05", "both", 2)
    # Reopens lead, then new names -- so NICE and LDOS survive a cap of 2.
    assert [r[0] for r in doc["reopens"]] + doc["new"] == ["NICE", "LDOS"]
    assert doc["dropped"] == ["CI", "BWA"]


def test_build_no_max_drops_nothing(research_dir, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS", "CI"], None))
    assert worklist.build("x", research_dir, "2026-08-05", "both", None)["dropped"] == []


def test_format_worklist_says_so_when_empty():
    doc = {"today": "2026-08-05", "new": [], "reopens": [], "dropped": [], "errors": []}
    out = "\n".join(worklist.format_worklist(doc))
    assert "nothing to research" in out.lower()


def test_format_worklist_lists_dropped_names(research_dir):
    doc = {
        "today": "2026-08-05",
        "new": ["LDOS"],
        "reopens": [],
        "dropped": ["CI", "BWA"],
        "errors": [],
    }
    out = "\n".join(worklist.format_worklist(doc))
    assert "CI" in out and "BWA" in out


def test_format_worklist_warns_above_the_large_threshold():
    doc = {
        "today": "2026-08-05",
        "new": [f"T{i}" for i in range(worklist.SWEEP_LARGE + 1)],
        "reopens": [],
        "dropped": [],
        "errors": [],
    }
    assert "LARGE SWEEP" in "\n".join(worklist.format_worklist(doc))


def test_format_worklist_silent_at_the_threshold():
    """Boundary: exactly SWEEP_LARGE is not 'large' — the warning fires above."""
    doc = {
        "today": "2026-08-05",
        "new": [f"T{i}" for i in range(worklist.SWEEP_LARGE)],
        "reopens": [],
        "dropped": [],
        "errors": [],
    }
    assert "LARGE SWEEP" not in "\n".join(worklist.format_worklist(doc))


def test_main_json_is_parseable(research_dir, monkeypatch, capsys):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS"], None))
    rc = worklist.main(
        ["--json", "--research-dir", str(research_dir), "--db", "x.db"],
        now_iso="2026-08-05T04:12:00+00:00",
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["new"] == ["LDOS"]
    assert doc["today"] == "2026-08-04"


def test_main_uses_phoenix_date_not_utc_slice(research_dir, monkeypatch, capsys):
    """04:12Z on the 5th is still the 4th in Phoenix. A now_iso[:10] slice
    would read 2026-08-05 and pull NICE's reopen a day early."""
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: ([], None))
    worklist.main(
        ["--json", "--research-dir", str(research_dir), "--db", "x.db"],
        now_iso="2026-08-05T04:12:00+00:00",
    )
    doc = json.loads(capsys.readouterr().out)
    assert doc["today"] == "2026-08-04"
    assert doc["reopens"] == []


def test_read_candidates_reads_the_screen(tmp_path, monkeypatch):
    """read_candidates delegates to candidates.screen() rather than
    restating its SQL -- the sweep and `main.py candidates` can never
    disagree about what qualifies."""
    from sources.combiners.composite import candidates

    monkeypatch.setattr(candidates, "connect_ro", lambda _p: sqlite3.connect(":memory:"))
    monkeypatch.setattr(candidates, "screen", lambda _c: [{"symbol": "LDOS"}, {"symbol": "CI"}])
    assert worklist.read_candidates("x.db") == (["LDOS", "CI"], None)
