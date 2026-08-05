import json
import sqlite3
from pathlib import Path

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
    symbols, data_date, err = worklist.read_candidates(str(tmp_path / "nope.db"))
    assert symbols == []
    assert data_date is None
    # Secret hygiene: the exception CLASS only. connect_ro raises
    # FileNotFoundError(path), so anything wider than the bare class name
    # would carry tmp_path -- an equality check is the only assertion that
    # can actually catch that.
    assert err == "FileNotFoundError"


def test_build_splits_new_and_due(research_dir, monkeypatch):
    monkeypatch.setattr(
        worklist, "read_candidates", lambda _db: (["NICE", "LDOS", "CI"], "2026-07-08", None)
    )
    doc = worklist.build("ignored.db", research_dir, "2026-08-05", "both", None)
    assert doc["new"] == ["LDOS", "CI"]
    assert [r[0] for r in doc["reopens"]] == ["NICE"]


def test_build_kind_filters(research_dir, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS"], "2026-07-08", None))
    assert worklist.build("x", research_dir, "2026-08-05", "new", None)["reopens"] == []
    assert worklist.build("x", research_dir, "2026-08-05", "reopen", None)["new"] == []


def test_build_max_reports_what_it_dropped(research_dir, monkeypatch):
    monkeypatch.setattr(
        worklist, "read_candidates", lambda _db: (["LDOS", "CI", "BWA"], "2026-07-08", None)
    )
    doc = worklist.build("x", research_dir, "2026-08-05", "both", 2)
    # Reopens lead, then new names -- so NICE and LDOS survive a cap of 2.
    assert [r[0] for r in doc["reopens"]] + doc["new"] == ["NICE", "LDOS"]
    assert doc["dropped"] == ["CI", "BWA"]


def test_build_no_max_drops_nothing(research_dir, monkeypatch):
    monkeypatch.setattr(
        worklist, "read_candidates", lambda _db: (["LDOS", "CI"], "2026-07-08", None)
    )
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
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS"], "2026-07-08", None))
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
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: ([], "2026-07-08", None))
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
    monkeypatch.setattr(candidates, "snapshot_date", lambda _c: "2026-07-08")
    assert worklist.read_candidates("x.db") == (["LDOS", "CI"], "2026-07-08", None)


def test_read_candidates_against_a_real_stocks_db(populated_data_dir):
    """Unmocked, offline: a stocks.db built through the screener's own
    ensure_schema, read through candidates.screen()'s real SQL. The mocked
    test above cannot catch a row-shape change in screen() -- this one can,
    which is the whole point of delegating instead of restating the SQL."""
    symbols, data_date, err = worklist.read_candidates(f"{populated_data_dir}/stocks.db")
    assert err is None
    assert symbols == ["ADBE", "PEGA"]
    # The snapshot header, not the run date: stocks.db does not refresh at
    # weekends and a list without its data date reads as tonight's.
    assert data_date == "2026-07-08"


def test_build_records_an_unreadable_candidates_db(research_dir, tmp_path):
    """The screener failing overnight must land in errors, not vanish."""
    doc = worklist.build(str(tmp_path / "gone.db"), research_dir, "2026-08-05", "new", None)
    assert doc["new"] == []
    assert doc["errors"] == ["candidates unreadable (FileNotFoundError)"]


def test_build_records_an_unreadable_verdicts_log(tmp_path, monkeypatch):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: ([], "2026-07-08", None))
    doc = worklist.build("x", tmp_path / "nope", "2026-08-05", "reopen", None)
    assert doc["reopens"] == []
    assert doc["errors"] == ["verdicts.log unreadable (FileNotFoundError)"]


def test_format_worklist_never_calls_a_failed_read_empty():
    """An unreadable source is an INCOMPLETE worklist, never a clean backlog:
    SKILL.md §1 tells the agent to stop on an empty list, so 'nothing to
    research' printed over a failed read would send it home blind."""
    doc = {
        "today": "2026-08-05",
        "new": [],
        "reopens": [],
        "dropped": [],
        "errors": ["candidates unreadable (OperationalError)"],
    }
    out = "\n".join(worklist.format_worklist(doc))
    assert "nothing to research" not in out.lower()
    assert "INCOMPLETE" in out
    # Names what could not be read, both as a ! line and in the verdict.
    assert out.count("candidates unreadable (OperationalError)") == 2


def test_format_worklist_flags_incomplete_even_with_names_found():
    doc = {
        "today": "2026-08-05",
        "new": ["LDOS"],
        "reopens": [],
        "dropped": [],
        "errors": ["verdicts.log unreadable (FileNotFoundError)"],
    }
    out = "\n".join(worklist.format_worklist(doc))
    assert "INCOMPLETE" in out
    assert "1 name(s) found so far" in out


def test_format_worklist_prints_the_stocks_snapshot_date():
    doc = {
        "today": "2026-08-05",
        "data_date": "2026-07-31",
        "data_age": "2026-07-31 (5d old)",
        "new": ["LDOS"],
        "reopens": [],
        "dropped": [],
        "errors": [],
    }
    assert "[stocks.db snapshot 2026-07-31 (5d old)]" in "\n".join(worklist.format_worklist(doc))


def test_main_reports_the_data_date_and_its_age(populated_data_dir, capsys):
    """Run date and DATA date are different facts and diverge every weekend:
    04:12Z on the 11th is the 10th in Phoenix, over a Wednesday snapshot."""
    sibling_research = Path(populated_data_dir).parent / "research"
    rc = worklist.main(
        ["--research-dir", str(sibling_research), "--db", f"{populated_data_dir}/stocks.db"],
        now_iso="2026-07-11T04:12:00+00:00",
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "=== Research Sweep worklist — 2026-07-10 ===" in out
    assert "[stocks.db snapshot 2026-07-08 (2d old)]" in out


def test_main_json_carries_the_data_date(populated_data_dir, capsys):
    sibling_research = Path(populated_data_dir).parent / "research"
    worklist.main(
        [
            "--json",
            "--research-dir",
            str(sibling_research),
            "--db",
            f"{populated_data_dir}/stocks.db",
        ],
        now_iso="2026-07-11T04:12:00+00:00",
    )
    doc = json.loads(capsys.readouterr().out)
    assert doc["data_date"] == "2026-07-08"
    assert doc["data_age"] == "2026-07-08 (2d old)"
    assert doc["new"] == ["ADBE", "PEGA"]


def test_build_counts_a_ticker_in_both_lists_once_under_max(tmp_path, monkeypatch):
    """A MISNAMED thesis (-v2 suffix) puts one name in both lists: the index
    reads it as un-researched while its verdict line is still due. Before the
    positional dedupe, `--max 1` returned NICE twice (two survivors against a
    cap of 1) and buried the genuinely-dropped LDOS in a DROPPED line that
    also named NICE."""
    d = tmp_path / "research"
    d.mkdir()
    (d / "verdicts.log").write_text("2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print\n")
    (d / "NICE-2026-07-27-v2.md").write_text("x")  # does not match THESIS_RE
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["NICE", "LDOS"], None, None))

    doc = worklist.build("x", d, "2026-08-05", "both", 1)
    assert [r[0] for r in doc["reopens"]] == ["NICE"]
    assert doc["new"] == []
    assert doc["dropped"] == ["LDOS"]


def test_build_keeps_a_both_lists_ticker_in_reopens_without_max(tmp_path, monkeypatch):
    """Same duplicate without a cap: still one name, and the reopen wins --
    it carries the prior thesis's context, so it is the more informative run."""
    d = tmp_path / "research"
    d.mkdir()
    (d / "verdicts.log").write_text("2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print\n")
    (d / "nice-2026-07-27.md").write_text("x")  # lowercase: also unindexed
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["NICE", "LDOS"], None, None))

    doc = worklist.build("x", d, "2026-08-05", "both", None)
    assert [r[0] for r in doc["reopens"]] == ["NICE"]
    assert doc["new"] == ["LDOS"]


@pytest.mark.parametrize("bad", ["0", "-1"])
def test_main_rejects_a_max_below_one(bad, research_dir, capsys):
    """`--max 0` used to print a full DROPPED line and then 'nothing to
    research'; `--max -1` silently trimmed the tail."""
    with pytest.raises(SystemExit) as exc:
        worklist.main(["--max", bad, "--research-dir", str(research_dir), "--db", "x.db"])
    assert exc.value.code == 2
    assert "must be at least 1" in capsys.readouterr().err


def test_main_accepts_a_max_of_one(research_dir, monkeypatch, capsys):
    monkeypatch.setattr(worklist, "read_candidates", lambda _db: (["LDOS"], "2026-07-08", None))
    rc = worklist.main(
        ["--json", "--max", "1", "--research-dir", str(research_dir), "--db", "x.db"],
        now_iso="2026-08-05T18:00:00+00:00",
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert [r[0] for r in doc["reopens"]] == ["NICE"]
    assert doc["dropped"] == ["LDOS"]
