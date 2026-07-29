"""Due-reopen digest block: dated reopen= fields from verdicts.log."""

import datetime as dt
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

# 9:15pm Phoenix on 2026-07-29 == 04:15 UTC on the 30th (rollover fixture).
NOW_UTC = dt.datetime.fromisoformat("2026-07-30T04:15:00+00:00")

HEADER = "# Format: ... [reopen=<YYYY-MM-DD|event>:<slug>]\n"


def _write_vlog(tmp_path, *lines):
    (tmp_path / "verdicts.log").write_text(HEADER + "".join(f"{ln}\n" for ln in lines))
    return tmp_path


def test_format_lines():
    got = daily_summary.format_reopen_lines([("TIMB", "2026-07-29", "q2-print", "2026-07-27")])
    assert got == ["TIMB due 2026-07-29: q2-print (thesis 2026-07-27)"]


def test_due_today_surfaces(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-27 TIMB UNPROVEN conditions=7 refuted=0 unknown=4 reopen=2026-07-29:q2-print",
    )
    got = daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path)
    assert any("TIMB" in ln and "q2-print" in ln for ln in got)


def test_not_due_on_utc_tomorrow(tmp_path):
    # It is 07-30 in UTC but still 07-29 in Phoenix: a 07-30 reopen is NOT due.
    _write_vlog(
        tmp_path,
        "2026-07-27 CHKP FLAWED conditions=6 refuted=3 unknown=3 reopen=2026-07-30:q2-print-guidance",
    )
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path) == []


def test_stale_reopen_past_window_absent(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-10 OLD UNPROVEN conditions=1 refuted=0 unknown=1 reopen=2026-07-15:q2-print",
    )
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path) == []


def test_newer_verdict_answers_reopen(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-27 TIMB UNPROVEN conditions=7 refuted=0 unknown=4 reopen=2026-07-29:q2-print",
        "2026-07-29 TIMB SOUND conditions=5 refuted=0 unknown=0",
    )
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path) == []


def test_event_reopen_never_surfaces(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-27 GFI UNPROVEN conditions=4 refuted=0 unknown=2 reopen=event:tarkwa-renewal-gold-ge-3800",
    )
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path) == []


def test_total_on_missing_dir(tmp_path):
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path / "nope") == []


def test_sorted_by_due_date_then_ticker(tmp_path):
    _write_vlog(
        tmp_path,
        "2026-07-27 SFM UNPROVEN conditions=5 refuted=0 unknown=3 reopen=2026-07-29:q2-print",
        "2026-07-26 CAPR FLAWED conditions=5 refuted=2 unknown=3 reopen=2026-07-28:adcom-vote",
    )
    got = daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path)
    assert [ln.split()[0] for ln in got] == ["CAPR", "SFM"]


def test_early_reresearch_retires_trigger(tmp_path):
    # Re-researched BEFORE the due date and the new thesis set no reopen:
    # the superseded line's trigger must not fire when its date arrives.
    _write_vlog(
        tmp_path,
        "2026-07-20 TIMB UNPROVEN conditions=7 refuted=0 unknown=4 reopen=2026-07-29:q2-print",
        "2026-07-25 TIMB SOUND conditions=5 refuted=0 unknown=0",
    )
    assert daily_summary.reopen_digest(NOW_UTC, research_dir=tmp_path) == []
