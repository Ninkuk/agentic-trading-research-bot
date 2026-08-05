from tools.research import worklist


def test_index_theses_newest_date_wins():
    assert worklist.index_theses(
        [
            "AAPL-2026-06-01.md",
            "AAPL-2026-07-10.md",
            "BRK.B-2026-07-01.md",
            "README.md",
            "verdicts.log",
        ]
    ) == {"AAPL": "2026-07-10", "BRK.B": "2026-07-01"}


def test_list_theses_reads_a_directory(tmp_path):
    (tmp_path / "AAPL-2026-06-01.md").write_text("x")
    (tmp_path / "AAPL-2026-07-10.md").write_text("x")
    (tmp_path / "README.md").write_text("not a thesis")
    assert worklist.list_theses(tmp_path) == {"AAPL": "2026-07-10"}


def test_list_theses_missing_dir_is_empty(tmp_path):
    assert worklist.list_theses(tmp_path / "nope") == {}


def test_newest_verdict_lines_skips_comments_and_short_lines():
    lines = [
        "# a comment line with plenty of fields in it",
        "  # indented comment",
        "garbage",
        "2026-07-01 STNE UNPROVEN conditions=6",
    ]
    assert worklist.newest_verdict_lines(lines) == {
        "STNE": ("2026-07-01", "2026-07-01 STNE UNPROVEN conditions=6")
    }


def test_newest_verdict_lines_later_line_wins_a_date_tie():
    lines = [
        "2026-07-01 PEGA FLAWED first",
        "2026-07-01 PEGA FLAWED second",
    ]
    assert worklist.newest_verdict_lines(lines)["PEGA"][1].endswith("second")


def test_newest_verdict_lines_newest_date_wins_regardless_of_order():
    lines = [
        "2026-08-03 CHKP FLAWED newer",
        "2026-07-26 CHKP FLAWED older",
    ]
    assert worklist.newest_verdict_lines(lines)["CHKP"] == (
        "2026-08-03",
        "2026-08-03 CHKP FLAWED newer",
    )


def test_due_reopens_includes_today_and_overdue_excludes_future():
    newest = {
        "NICE": ("2026-07-27", "2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print"),
        "OLD": ("2026-06-20", "2026-06-20 OLD UNPROVEN reopen=2026-07-01:print"),
        "INTU": ("2026-07-30", "2026-07-30 INTU UNPROVEN reopen=2026-08-20:fy27-guide"),
    }
    assert worklist.due_reopens(newest, "2026-08-05") == [
        ("OLD", "2026-07-01", "print", "2026-06-20"),
        ("NICE", "2026-08-05", "q2-print", "2026-07-27"),
    ]


def test_due_reopens_excludes_event_triggers():
    newest = {"GFI": ("2026-07-01", "2026-07-01 GFI UNPROVEN reopen=event:tarkwa-renewal")}
    assert worklist.due_reopens(newest, "2026-08-05") == []


def test_due_reopens_ignores_lines_with_no_trigger():
    newest = {"CSU": ("2026-07-10", "2026-07-10 CSU UNPROVEN conditions=6 refuted=0")}
    assert worklist.due_reopens(newest, "2026-08-05") == []


def test_due_reopens_sorted_by_date_then_ticker():
    newest = {
        "PAYC": ("2026-07-30", "2026-07-30 PAYC UNPROVEN reopen=2026-08-05:b"),
        "NICE": ("2026-07-27", "2026-07-27 NICE UNPROVEN reopen=2026-08-05:a"),
        "PRIM": ("2026-07-30", "2026-07-30 PRIM UNPROVEN reopen=2026-08-04:c"),
    }
    assert [r[0] for r in worklist.due_reopens(newest, "2026-08-05")] == [
        "PRIM",
        "NICE",
        "PAYC",
    ]


def test_unresearched_preserves_screen_order():
    theses = {"ADBE": "2026-07-26", "GDDY": "2026-08-03"}
    assert worklist.unresearched(["GDDY", "LDOS", "ADBE", "CI"], theses) == ["LDOS", "CI"]


def test_worklists_are_disjoint_by_construction():
    """A reopen ticker HAS a thesis, so it can never be un-researched. The
    spec's overlap rule is a property of the data model, not a code path."""
    theses = {"NICE": "2026-07-27"}
    newest = {"NICE": ("2026-07-27", "2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print")}
    new = worklist.unresearched(["NICE", "LDOS"], theses)
    reopens = {r[0] for r in worklist.due_reopens(newest, "2026-08-05")}
    assert set(new).isdisjoint(reopens)


def test_reopen_field_re_matches_event_and_dated():
    assert worklist.REOPEN_FIELD_RE.search("x reopen=event:slug").group(1) == "event"
    assert worklist.REOPEN_FIELD_RE.search("x reopen=2026-08-05:slug").group(1) == "2026-08-05"
    assert worklist.REOPEN_DATED_RE.search("x reopen=event:slug") is None
