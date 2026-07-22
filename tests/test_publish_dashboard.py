from datetime import UTC, datetime

from deploy.launchd.publish_dashboard import (
    NOINDEX_META,
    inject_noindex,
    is_fresh,
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
