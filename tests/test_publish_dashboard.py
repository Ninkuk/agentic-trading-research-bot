from datetime import UTC, datetime

from deploy.launchd.publish_dashboard import (
    NOINDEX_META,
    ROBOTS_TXT,
    inject_noindex,
    is_fresh,
    stage,
)


def _epoch(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=UTC).timestamp()


def test_is_fresh_same_phoenix_day():
    # 2026-07-21 14:00 UTC == 07:00 Phoenix, same Phoenix day as the now below
    assert is_fresh(_epoch(2026, 7, 21, 14, 0), "2026-07-21T14:30:00+00:00")


def test_is_fresh_rejects_yesterday():
    assert not is_fresh(_epoch(2026, 7, 20, 14, 0), "2026-07-21T14:30:00+00:00")


def test_is_fresh_survives_utc_rollover():
    """The job runs 9:20pm Phoenix = 04:20 UTC the NEXT day.

    The dashboard was written at 9:13pm Phoenix (04:13 UTC on the 22nd). Both are
    Phoenix 2026-07-21, so this must be fresh. A `now_iso[:10]` implementation
    compares "2026-07-22" against the file's Phoenix date "2026-07-21", calls it
    stale, and refuses to publish every single night. That is what this test catches.
    """
    assert is_fresh(_epoch(2026, 7, 22, 4, 13), "2026-07-22T04:20:00+00:00")


def test_inject_noindex_after_head():
    out = inject_noindex("<html><head><title>x</title></head><body>b</body></html>")
    assert NOINDEX_META in out
    assert out.index(NOINDEX_META) < out.index("<title>")


def test_inject_noindex_without_head_tag():
    out = inject_noindex("<p>no head here</p>")
    assert NOINDEX_META in out
    assert "<p>no head here</p>" in out


def test_inject_noindex_is_idempotent():
    once = inject_noindex("<html><head></head></html>")
    assert inject_noindex(once) == once


def test_stage_writes_three_files(tmp_path):
    stage("<html><head></head><body>hi</body></html>", tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / ".nojekyll").exists()
    assert (tmp_path / "robots.txt").exists()


def test_stage_index_has_noindex_and_content(tmp_path):
    stage("<html><head></head><body>hi</body></html>", tmp_path)
    out = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert NOINDEX_META in out
    assert "hi" in out


def test_stage_robots_disallows_all(tmp_path):
    stage("<html></html>", tmp_path)
    assert (tmp_path / "robots.txt").read_text(encoding="utf-8") == ROBOTS_TXT
    assert "Disallow: /" in ROBOTS_TXT


def test_stage_nojekyll_is_empty(tmp_path):
    stage("<html></html>", tmp_path)
    assert (tmp_path / ".nojekyll").read_text(encoding="utf-8") == ""
