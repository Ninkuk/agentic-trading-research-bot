"""FOMC calendar fetch + the one fragile HTML parser, isolated here.

Only meeting dates are parsed; minutes/blackout/SEP are computed elsewhere. The
parser fails loudly (FomcCalendarParseError) rather than emit an empty calendar —
a silent 'no meetings coming' is the dangerous failure mode for a macro monitor."""
import re
from datetime import date, timedelta

from http_client import http_get, make_opener

CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY_STATUS = frozenset({403, 429, 503})

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

_YEAR = re.compile(r"(\d{4})\s+FOMC\s+Meetings([^<]*)", re.IGNORECASE)
# month (opt /second-month) ... date "d-d" (opt trailing '*') — confirm vs live markup.
_MEETING = re.compile(
    r"fomc-meeting__month[^>]*>\s*([A-Za-z]+)(?:\s*/\s*([A-Za-z]+))?\s*<"
    r"[\s\S]*?fomc-meeting__date[^>]*>\s*(\d+)\s*-\s*(\d+)\s*(\*?)",
    re.IGNORECASE)


class FomcCalendarParseError(Exception):
    """Raised when the FOMC page yields zero meetings from non-empty HTML."""


def _norm_date(year: int, month_name: str, day: str) -> str:
    mo = _MONTHS[month_name.strip().lower()[:3]]
    return date(int(year), mo, int(day)).isoformat()


def parse_calendar(html: str) -> list:
    """Extract meetings from the FOMC calendars page. Raises on drift."""
    if not html or not html.strip():
        raise FomcCalendarParseError("empty FOMC calendar HTML")
    meetings = []
    # split into per-year panels (chunk starts at each 'YYYY FOMC Meetings')
    for chunk in re.split(r"(?=\d{4}\s+FOMC\s+Meetings)", html):
        ym = _YEAR.search(chunk)
        if not ym:
            continue
        year, heading = int(ym.group(1)), ym.group(2)
        tentative = "tentative" in heading.lower()
        for m1, m2, d1, d2, star in _MEETING.findall(chunk):
            start = _norm_date(year, m1, d1)
            end = _norm_date(year, m2 or m1, d2)
            meetings.append({
                "start_date": start, "end_date": end,
                "status": "tentative" if tentative else "confirmed",
                "has_press_conference": bool(star),
            })
    if not meetings:
        raise FomcCalendarParseError(
            "no meetings parsed from non-empty HTML (page structure changed?)")
    return meetings


_urlopen = make_opener(_UA)


def _http_get(url: str) -> str:
    return http_get(url, _urlopen, _RETRY_STATUS)


def fetch_calendar(get=_http_get) -> list:
    """GET the FOMC calendars page and parse it."""
    return parse_calendar(get(CALENDAR_URL))


def minutes_date(end_date: str) -> str:
    """Minutes release = meeting end + 3 weeks (21 days)."""
    return (date.fromisoformat(end_date) + timedelta(days=21)).isoformat()


def blackout_window(start_date: str, end_date: str):
    """(blackout_start, blackout_end): the second Saturday preceding the meeting
    start, and the day after the meeting end. Saturday is weekday 5."""
    start = date.fromisoformat(start_date)
    days_back = (start.weekday() - 5) % 7 or 7    # strictly-preceding Saturday
    first_sat = start - timedelta(days=days_back)
    blackout_start = first_sat - timedelta(days=7)
    blackout_end = date.fromisoformat(end_date) + timedelta(days=1)
    return blackout_start.isoformat(), blackout_end.isoformat()


def is_sep_meeting(decision_date: str) -> bool:
    """SEP / dot-plot meetings are roughly quarterly: Mar/Jun/Sep/Dec."""
    return date.fromisoformat(decision_date).month in {3, 6, 9, 12}
