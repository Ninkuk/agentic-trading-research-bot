"""market_calendar store: the shared monitor schema plus calendar-specific views
and the trading-day helpers other modules import.

is_trading_day/next_trading_day/next_early_close are Python helpers (not views)
because 'is date D open?' needs a bound date argument, which a stored SQLite view
cannot carry. They read the events table written by run.py."""
from datetime import date, timedelta

from sources.common.monitor_common import connect
from sources.common.monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema", "is_trading_day", "next_trading_day",
           "next_early_close"]

_CAL_SCHEMA = """
-- What's closed or short from today onward (equity + bond).
CREATE VIEW IF NOT EXISTS v_upcoming_closures AS
SELECT e.event_type, e.event_date, e.event_time, e.title, e.source
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('market_holiday', 'early_close',
                       'bond_holiday', 'bond_early_close')
ORDER BY e.event_date, e.event_time;

-- The single soonest option expiration (monthly OPEX or quad-witching).
CREATE VIEW IF NOT EXISTS v_next_opex AS
SELECT e.event_type, e.event_date, e.event_time, e.title
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('opex', 'quad_witching')
ORDER BY e.event_date
LIMIT 1;

-- Upcoming half-days (equity + bond), with their close time.
CREATE VIEW IF NOT EXISTS v_early_closes AS
SELECT e.event_type, e.event_date, e.event_time, e.title, e.source
FROM events e, calendar_now p
WHERE e.event_date >= p.today
  AND e.event_type IN ('early_close', 'bond_early_close')
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + calendar views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_CAL_SCHEMA)
    conn.commit()


def is_trading_day(conn, d: str) -> bool:
    """True iff `d` (YYYY-MM-DD) is a weekday and not an equity market_holiday."""
    if date.fromisoformat(d).weekday() >= 5:            # Sat/Sun
        return False
    hit = conn.execute(
        "SELECT 1 FROM events WHERE event_type='market_holiday' "
        "AND event_date=? LIMIT 1", (d,)).fetchone()
    return hit is None


def next_trading_day(conn, d: str) -> str:
    """The next equity trading day strictly after `d`. Bounded scan (holidays
    never cluster more than a few days) so a bad DB can't loop forever."""
    cur = date.fromisoformat(d)
    for _ in range(30):
        cur += timedelta(days=1)
        if is_trading_day(conn, cur.isoformat()):
            return cur.isoformat()
    raise RuntimeError("no trading day found within 30 days")


def next_early_close(conn, d: str):
    """The next equity early_close on or after `d`, or None."""
    row = conn.execute(
        "SELECT event_date FROM events WHERE event_type='early_close' "
        "AND event_date >= ? ORDER BY event_date LIMIT 1", (d,)).fetchone()
    return row[0] if row else None
