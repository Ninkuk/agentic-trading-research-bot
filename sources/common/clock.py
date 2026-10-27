"""The house clock: every calendar date the system reasons about is a Phoenix date.

Timestamps are stored as UTC isoformat() instants, but a *date* is not
derivable from one by slicing. UTC midnight falls at 17:00 Phoenix, and the
launchd schedule runs twelve jobs after that (cboe_stats 18:00 through
research-nightly 22:00), so `now_iso[:10]` yields *tomorrow* for every one of
them. Composite stamps opinions with the Phoenix date and the journal matches
fills on it; anything comparing against those must agree, or ages come out one
day high and a fill can appear to precede an opinion formed after it.

America/Phoenix does not observe DST, so the offset is a fixed UTC-7 and needs
no tzdata lookup — which is also why a bare timedelta is safe here and would
not be for an ET-anchored clock.
"""

from datetime import UTC, datetime, timedelta

__all__ = ["PHOENIX_UTC_OFFSET", "PHX_DATE_SQL", "phx_date"]

PHOENIX_UTC_OFFSET = timedelta(hours=7)

# The same conversion in SQL: format with the timestamp column, e.g.
# PHX_DATE_SQL.format(ts="s.captured_at"). Every view that derives a calendar
# date from a stored UTC instant must use this one expression so the journal's
# fill-vs-opinion join and composite's obs_date stay on one clock.
PHX_DATE_SQL = "substr(datetime({ts}, '-7 hours'), 1, 10)"


def phx_date(when: str | datetime) -> str:
    """Phoenix-local date (YYYY-MM-DD) of a UTC isoformat string or a datetime.
    A naive input is read as UTC, matching how the rest of the repo stores time."""
    dt = datetime.fromisoformat(when) if isinstance(when, str) else when
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (dt.astimezone(UTC) - PHOENIX_UTC_OFFSET).date().isoformat()
