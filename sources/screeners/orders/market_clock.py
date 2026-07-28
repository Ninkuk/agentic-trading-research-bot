"""Pure NYSE-open arithmetic (no DB, no clock). ET observes DST; Phoenix does
not — so 9:30 ET is 6:30 Phx under EDT and 7:30 under EST, and the launchd
schedule covers both slots while this module decides which one is live. DST
boundaries (second Sunday of March, first Sunday of November) are Sundays, so
no trading day is ever ambiguous. Exception to the four-file rule, like
market_calendar/compute.py."""

from datetime import UTC, date, datetime, time, timedelta

from sources.common.clock import phx_date
from sources.screeners.orders.catalog import WINDOW_END_MIN, WINDOW_START_MIN

__all__ = ["market_open_utc", "window_state"]


def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))


def _et_utc_offset(d: date) -> timedelta:
    """ET's UTC offset on date d: -4h under EDT, -5h under EST."""
    edt = _nth_sunday(d.year, 3, 2) <= d < _nth_sunday(d.year, 11, 1)
    return timedelta(hours=-4 if edt else -5)


def market_open_utc(d: date) -> datetime:
    """9:30am ET on d, as an aware-UTC datetime."""
    naive_et = datetime.combine(d, time(9, 30))
    return (naive_et - _et_utc_offset(d)).replace(tzinfo=UTC)


def window_state(now_iso: str, is_trading_day: bool) -> str:
    """'open' iff now is inside [open+WINDOW_START_MIN, open+WINDOW_END_MIN]
    of *today's Phoenix-date* session. The Phoenix date (not a UTC slice)
    picks the session: 04:12 UTC is the previous Phoenix evening."""
    if not is_trading_day:
        return "closed_day"
    now = datetime.fromisoformat(now_iso)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    opened = market_open_utc(date.fromisoformat(phx_date(now_iso)))
    if now < opened + timedelta(minutes=WINDOW_START_MIN):
        return "before"
    if now > opened + timedelta(minutes=WINDOW_END_MIN):
        return "after"
    return "open"
