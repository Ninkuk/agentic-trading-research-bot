"""Thin, OPTIONAL HTML refresh for the seeded calendar. Isolated and fails loudly.

A normal run never calls this — the seed in catalog.py is the source of truth.
`--refresh` uses it to re-derive the seed from the official pages. If zero dated
rows parse, we RAISE: a silently-empty holiday set would tell the bot the market
is open every day, which is dangerous.

Live-verified 2026-07-06 against both pages:
  * NYSE serves ONE <table>: header <th>Holiday</th><th>2026</th><th>2027</th>...
    sets the year per column; each body row is <th>name</th> plus one year-less
    date cell per year ("Thursday, January 1", possibly with footnote stars or
    an "(observed)" note; an em-dash cell = not observed that year).
  * SIFMA serves <h3>name</h3><span>Weekday, Month D, YYYY</span> groups under
    per-country sections — only "U.S. Holiday Recommendations" counts; the
    U.K./Japan sections that follow must not leak into the bond calendar.
"""
import html as html_text
import re

from sources.common.http_client import http_get, make_opener

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY = {403, 429, 503}

_MONTHS = {m: i for i, m in enumerate(
    ("january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"), start=1)}
_MONTH_PAT = "|".join(_MONTHS)
_MONTH_DAY = re.compile(rf"({_MONTH_PAT})\s+(\d{{1,2}})", re.IGNORECASE)

_NYSE_YEARS = re.compile(
    r"<th[^>]*>\s*Holiday\s*</th>((?:\s*<th[^>]*>\s*\d{4}\s*</th>)+)",
    re.IGNORECASE)
_NYSE_ROW = re.compile(
    r"<tr[^>]*>\s*<th[^>]*>([^<]+)</th>((?:\s*<td[^>]*>.*?</td>)+)\s*</tr>",
    re.IGNORECASE | re.DOTALL)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
_YEAR = re.compile(r"\d{4}")

_SIFMA_US = re.compile(r"U\.S\.\s+Holiday\s+Recommendations", re.IGNORECASE)
_SIFMA_NEXT = re.compile(r"(?:U\.K\.|Japan)\s+Holiday\s+Recommendations",
                         re.IGNORECASE)
_SIFMA_ENTRY = re.compile(
    rf"<h3[^>]*>([^<]+)</h3>\s*<span[^>]*>[^<]*?"
    rf"({_MONTH_PAT})\s+(\d{{1,2}}),\s*(\d{{4}})", re.IGNORECASE)

_DRIFT = ("no dated calendar rows parsed — refusing to blank the "
          "calendar (source markup likely changed)")


def _iso(month_name, day, year):
    return f"{int(year):04d}-{_MONTHS[month_name.lower()]:02d}-{int(day):02d}"


def parse_nyse_calendar(html: str) -> dict:
    """Equity closures from the NYSE hours-and-calendars page. Raises on drift."""
    out = {}
    header = _NYSE_YEARS.search(html or "")
    if header:
        years = _YEAR.findall(header.group(1))
        for name, cells in _NYSE_ROW.findall(html):
            label = html_text.unescape(name).strip()
            for year, cell in zip(years, _CELL.findall(cells)):
                d = _MONTH_DAY.search(cell)
                if d:  # dash placeholder cells ("—*") carry no date
                    out[_iso(d.group(1), d.group(2), year)] = label
    if not out:
        raise ValueError(_DRIFT)
    return out


def parse_sifma_calendar(html: str) -> dict:
    """Bond closures from the SIFMA holiday-schedule page (U.S. section only).
    Raises on drift."""
    us = _SIFMA_US.search(html or "")
    if not us:
        raise ValueError(_DRIFT)
    section = html[us.end():]
    cut = _SIFMA_NEXT.search(section)
    if cut:
        section = section[:cut.start()]
    out = {_iso(mon, day, year): html_text.unescape(name).strip()
           for name, mon, day, year in _SIFMA_ENTRY.findall(section)}
    if not out:
        raise ValueError(_DRIFT)
    return out


def fetch_page(url: str, get=None) -> str:
    """Bounded-backoff GET for the opt-in refresh. `get` injectable for tests."""
    opener = get or make_opener(_UA)
    return http_get(url, opener, _RETRY)
