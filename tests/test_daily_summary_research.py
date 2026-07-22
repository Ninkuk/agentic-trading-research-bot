"""Fresh-research digest block: pure formatter + a total reader."""

import datetime as dt
import sys
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "launchd"
sys.path.insert(0, str(DEPLOY))
import daily_summary  # noqa: E402

# 9:15pm Phoenix on 2026-07-22 == 04:15 UTC on the 23rd (rollover fixture).
NOW_UTC = dt.datetime.fromisoformat("2026-07-23T04:15:00+00:00")


def test_format_lines():
    lines = daily_summary.format_research_lines(
        [("EOSE", "2026-07-22")], ["2026-07-22 EOSE SOUND conditions=3 refuted=0 unknown=1"]
    )
    assert any("EOSE-2026-07-22" in ln for ln in lines)
    assert any("SOUND" in ln for ln in lines)


def test_digest_picks_only_fresh_theses(tmp_path):
    (tmp_path / "EOSE-2026-07-22.md").write_text("x" * 3000)
    (tmp_path / "OLD-2026-07-10.md").write_text("x" * 3000)
    (tmp_path / "README.md").write_text("no")
    got = daily_summary.research_digest(NOW_UTC, research_dir=tmp_path)
    assert any("EOSE" in ln for ln in got)
    assert not any("OLD" in ln for ln in got)


def test_digest_reads_fresh_verdicts_skips_comments(tmp_path):
    (tmp_path / "verdicts.log").write_text(
        "# header comment\n"
        "2026-07-10 OLD FLAWED conditions=2 refuted=1 unknown=0\n"
        "2026-07-22 EOSE SOUND conditions=3 refuted=0 unknown=1\n"
    )
    got = daily_summary.research_digest(NOW_UTC, research_dir=tmp_path)
    assert any("EOSE" in ln and "SOUND" in ln for ln in got)
    assert not any("FLAWED" in ln for ln in got)


def test_digest_total_on_missing_dir(tmp_path):
    assert daily_summary.research_digest(NOW_UTC, research_dir=tmp_path / "nope") == []


def test_slow_jobs_covers_research_nightly():
    assert "research-nightly" in daily_summary._SLOW_JOBS
