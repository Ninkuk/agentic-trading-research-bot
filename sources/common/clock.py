"""The house clock: every calendar date the system reasons about is a Phoenix date.

Timestamps are stored as UTC isoformat() instants, but a *date* is not
derivable from one by slicing. UTC midnight falls at 17:00 Phoenix, and the
launchd schedule runs eight jobs after that (cboe_stats 18:00 through
daily-summary 21:15), so `now_iso[:10]` yields *tomorrow* for every one of
them. Composite stamps opinions with the Phoenix date and the journal matches
fills on it; anything comparing against those must agree, or ages come out one
day high and a fill can appear to precede an opinion formed after it.

America/Phoenix does not observe DST, so the offset is a fixed UTC-7 and needs
no tzdata lookup — which is also why a bare timedelta is safe here and would
not be for an ET-anchored clock.
"""

from datetime import UTC, datetime, timedelta

__all__ = ["PHOENIX_UTC_OFFSET", "phx_date"]

PHOENIX_UTC_OFFSET = timedelta(hours=7)


def phx_date(when: str | datetime) -> str:
    """Phoenix-local date (YYYY-MM-DD) of a UTC isoformat string or a datetime.
    A naive input is read as UTC, matching how the rest of the repo stores time."""
    dt = datetime.fromisoformat(when) if isinstance(when, str) else when
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (dt.astimezone(UTC) - PHOENIX_UTC_OFFSET).date().isoformat()
