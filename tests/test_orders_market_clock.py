from datetime import UTC, date, datetime

from sources.screeners.orders import market_clock


def test_open_is_1330_utc_in_summer():
    # 2026-07-27 is EDT: 9:30 ET == 13:30 UTC == 6:30 Phoenix.
    assert market_clock.market_open_utc(date(2026, 7, 27)) == datetime(
        2026, 7, 27, 13, 30, tzinfo=UTC
    )


def test_open_is_1430_utc_in_winter():
    # 2026-01-05 is EST: 9:30 ET == 14:30 UTC == 7:30 Phoenix.
    assert market_clock.market_open_utc(date(2026, 1, 5)) == datetime(
        2026, 1, 5, 14, 30, tzinfo=UTC
    )


def test_dst_boundary_days_2026():
    # DST starts second Sunday of March (2026-03-08), ends first Sunday of
    # November (2026-11-01). The Fridays/Mondays around them flip offsets.
    assert market_clock.market_open_utc(date(2026, 3, 6)).hour == 14  # EST Friday
    assert market_clock.market_open_utc(date(2026, 3, 9)).hour == 13  # EDT Monday
    assert market_clock.market_open_utc(date(2026, 10, 30)).hour == 13  # EDT Friday
    assert market_clock.market_open_utc(date(2026, 11, 2)).hour == 14  # EST Monday


def test_window_state_boundaries():
    # Window is [open+2min, open+45min]. Summer open 13:30 UTC.
    day = "2026-07-27"
    cases = [
        (f"{day}T13:31:00+00:00", "before"),  # open+1
        (f"{day}T13:32:00+00:00", "open"),  # open+2 inclusive
        (f"{day}T14:14:00+00:00", "open"),  # open+44
        (f"{day}T14:16:00+00:00", "after"),  # open+46
        (f"{day}T23:00:00+00:00", "after"),  # evening
    ]
    for now_iso, expected in cases:
        assert market_clock.window_state(now_iso, is_trading_day=True) == expected, now_iso


def test_window_state_closed_day_wins():
    assert (
        market_clock.window_state("2026-07-27T13:35:00+00:00", is_trading_day=False) == "closed_day"
    )


def test_window_uses_phoenix_date_not_utc_slice():
    # 04:12 UTC on the 28th is the EVENING of the 27th in Phoenix; the
    # relevant session is the 27th's (long over -> 'after'), not the 28th's
    # (not started -> 'before'). A [:10] slice gets this wrong.
    assert market_clock.window_state("2026-07-28T04:12:00+00:00", is_trading_day=True) == "after"
