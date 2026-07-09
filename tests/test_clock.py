"""The house clock. Every case here straddles the 17:00-Phoenix / 00:00-UTC
rollover, because that boundary is the only place a UTC/Phoenix mixup is
observable — and it is exactly where the nightly combiner slots run."""

from datetime import UTC, datetime, timedelta, timezone

from sources.common.clock import PHOENIX_UTC_OFFSET, phx_date

IST = timezone(timedelta(hours=5, minutes=30))


def test_before_rollover_utc_and_phoenix_dates_agree():
    # 16:40 Phoenix (the fred slot) = 23:40 UTC, same calendar day.
    assert phx_date("2026-07-08T23:40:00+00:00") == "2026-07-08"


def test_after_rollover_phoenix_is_the_previous_utc_day():
    # 21:12 Phoenix (the advisor slot) = 04:12 UTC the NEXT day.
    assert phx_date("2026-07-09T04:12:00+00:00") == "2026-07-08"


def test_exact_rollover_instant():
    # 00:00 UTC is 17:00 Phoenix on the prior day — the first instant that skews.
    assert phx_date("2026-07-09T00:00:00+00:00") == "2026-07-08"
    assert phx_date("2026-07-08T23:59:59+00:00") == "2026-07-08"


def test_accepts_datetime_and_normalises_other_zones():
    aware = datetime(2026, 7, 9, 4, 12, tzinfo=UTC)
    assert phx_date(aware) == "2026-07-08"
    # A non-UTC aware input is converted, not truncated.
    assert phx_date(datetime(2026, 7, 9, 9, 42, tzinfo=IST)) == "2026-07-08"


def test_naive_input_is_read_as_utc():
    assert phx_date(datetime(2026, 7, 9, 4, 12)) == "2026-07-08"
    assert phx_date("2026-07-09T04:12:00") == "2026-07-08"


def test_offset_is_dst_free():
    # America/Phoenix does not observe DST: the same wall-clock slot maps to the
    # same Phoenix date in January and July, which is why a bare timedelta works.
    assert timedelta(hours=7) == PHOENIX_UTC_OFFSET
    assert phx_date("2026-01-09T04:12:00+00:00") == "2026-01-08"
    assert phx_date("2026-07-09T04:12:00+00:00") == "2026-07-08"
