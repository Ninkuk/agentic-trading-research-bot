"""Thin, OPTIONAL HTML refresh for the seeded calendar. Isolated and fails loudly.

A normal run never calls this — the seed in catalog.py is the source of truth.
`--refresh` uses it to re-derive the seed from the official pages. If the target
table is missing or zero dated rows parse, we RAISE: a silently-empty holiday set
would tell the bot the market is open every day, which is dangerous."""
import re

from http_client import http_get, make_opener

_UA = {"User-Agent": "agentic-trading-bot ninadk.dev@gmail.com"}
_RETRY = {403, 429, 503}

# Tolerant row matcher: a text label followed (within the same row) by a date we
# can normalize to ISO. The exact markup is confirmed live at refresh time; this
# contract — <label, date> pairs, raise on none — is what the monitor depends on.
_ROW = re.compile(
    r"<td[^>]*>\s*([A-Za-z][^<]*?)\s*</td>\s*<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>",
    re.IGNORECASE | re.DOTALL,
)


def _parse(html: str) -> dict:
    out = {}
    for label, iso in _ROW.findall(html or ""):
        out[iso] = label.strip()
    if not out:
        raise ValueError("no dated calendar rows parsed — refusing to blank the "
                         "calendar (source markup likely changed)")
    return out


def parse_nyse_calendar(html: str) -> dict:
    """Equity closures from the NYSE hours-and-calendars page. Raises on drift."""
    return _parse(html)


def parse_sifma_calendar(html: str) -> dict:
    """Bond closures from the SIFMA holiday-schedule page. Raises on drift."""
    return _parse(html)


def fetch_page(url: str, get=None) -> str:
    """Bounded-backoff GET for the opt-in refresh. `get` injectable for tests."""
    opener = get or make_opener(_UA)
    return http_get(url, opener, _RETRY)
