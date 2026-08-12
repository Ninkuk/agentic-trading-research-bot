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


def test_open_event_triggers_lists_events_sorted_by_ticker():
    newest = {
        "TSLA": ("2026-07-27", "2026-07-27 TSLA FLAWED reopen=event:robotaxi-miles"),
        "GFI": ("2026-07-27", "2026-07-27 GFI UNPROVEN reopen=event:tarkwa-renewal"),
        "NICE": ("2026-07-27", "2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print"),
        "CSU": ("2026-07-10", "2026-07-10 CSU UNPROVEN conditions=6 refuted=0"),
    }
    assert worklist.open_event_triggers(newest) == [
        ("GFI", "tarkwa-renewal", "2026-07-27"),
        ("TSLA", "robotaxi-miles", "2026-07-27"),
    ]


def test_open_event_triggers_only_newest_line_counts():
    """A re-research retires the old event trigger via newest_verdict_lines;
    what reaches open_event_triggers is already one line per ticker."""
    lines = [
        "2026-07-01 GFI UNPROVEN reopen=event:tarkwa-renewal",
        "2026-08-01 GFI SOUND conditions=4 refuted=0",
    ]
    assert worklist.open_event_triggers(worklist.newest_verdict_lines(lines)) == []


def test_unresearched_preserves_screen_order():
    theses = {"ADBE": "2026-07-26", "GDDY": "2026-08-03"}
    assert worklist.unresearched(["GDDY", "LDOS", "ADBE", "CI"], theses) == ["LDOS", "CI"]


def test_worklists_are_disjoint_when_the_thesis_is_named_correctly(tmp_path):
    """A reopen ticker has a thesis, so it is not un-researched -- but that
    holds only through the FILENAME, which is why this drives list_theses over
    a real directory instead of a hand-built index. A misnamed file (`-v2`,
    lowercase) breaks the property, and build() then dedupes: see
    test_build_counts_a_ticker_in_both_lists_once_under_max."""
    (tmp_path / "NICE-2026-07-27.md").write_text("x")
    (tmp_path / "NICE-2026-07-27-v2.md").write_text("misnamed sibling, unindexed")
    newest = {"NICE": ("2026-07-27", "2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print")}
    new = worklist.unresearched(["NICE", "LDOS"], worklist.list_theses(tmp_path))
    reopens = {r[0] for r in worklist.due_reopens(newest, "2026-08-05")}
    assert reopens == {"NICE"}
    assert new == ["LDOS"]
    assert set(new).isdisjoint(reopens)


def test_build_events_outside_the_max_cap(tmp_path):
    """--max caps dispatchable names only; the event verification list must
    never lose a row to it."""
    (tmp_path / "GFI-2026-07-27.md").write_text("x")
    (tmp_path / "NICE-2026-07-27.md").write_text("x")
    (tmp_path / "verdicts.log").write_text(
        "2026-07-27 GFI UNPROVEN reopen=event:tarkwa-renewal\n"
        "2026-07-27 NICE UNPROVEN reopen=2026-08-05:q2-print\n"
    )
    doc = worklist.build("unused.db", tmp_path, "2026-08-10", "reopen", max_n=1)
    assert doc["reopens"][0][0] == "NICE"
    assert doc["events"] == [("GFI", "tarkwa-renewal", "2026-07-27")]
    assert doc["dropped"] == []


def test_format_worklist_events_open_but_nothing_due(tmp_path):
    (tmp_path / "GFI-2026-07-27.md").write_text("x")
    (tmp_path / "verdicts.log").write_text("2026-07-27 GFI UNPROVEN reopen=event:tarkwa-renewal\n")
    doc = worklist.build("unused.db", tmp_path, "2026-08-10", "reopen", max_n=None)
    out = "\n".join(worklist.format_worklist(doc))
    assert "GFI  event:tarkwa-renewal  (thesis 2026-07-27)" in out
    assert "nothing auto-due" in out
    assert "VERIFIED" in out


def test_reopen_field_re_matches_event_and_dated():
    assert worklist.REOPEN_FIELD_RE.search("x reopen=event:slug").group(1) == "event"
    assert worklist.REOPEN_FIELD_RE.search("x reopen=2026-08-05:slug").group(1) == "2026-08-05"
    assert worklist.REOPEN_DATED_RE.search("x reopen=event:slug") is None
