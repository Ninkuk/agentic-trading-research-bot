"""earnings_calendar store: the shared monitor schema plus four earnings views.
The events/snapshots/calendar_now DDL lives in monitor_common; this only adds
views. Scope is by ingest (--only watchlist), so the views need no watchlist
table — they filter event_type='earnings' against the injected :today."""

from sources.common.monitor_common import connect
from sources.common.monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema"]

_EARNINGS_VIEWS = """
-- All upcoming earnings, biggest names first within a day.
CREATE VIEW IF NOT EXISTS v_upcoming_earnings AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status,
       e.source, json_extract(e.payload, '$.mktcap') AS mktcap,
       json_extract(e.payload, '$.eps_est') AS eps_est
FROM events e, calendar_now p
WHERE e.event_type = 'earnings' AND e.event_date >= p.today
ORDER BY e.event_date, json_extract(e.payload, '$.mktcap') DESC;

-- Reporting within the horizon window (drives sizing / IV-crush decisions).
CREATE VIEW IF NOT EXISTS v_imminent_earnings AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status
FROM events e, calendar_now p
WHERE e.event_type = 'earnings'
  AND e.event_date BETWEEN p.today
      AND date(p.today, '+' || p.horizon_days || ' days')
ORDER BY e.event_date;

-- Current Mon-Fri week ("who prints this week").
CREATE VIEW IF NOT EXISTS v_this_week_earnings AS
WITH wk AS (
    SELECT date(today, '-' ||
               ((CAST(strftime('%w', today) AS INTEGER) + 6) % 7) || ' days')
           AS mon
    FROM calendar_now
)
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status
FROM events e, wk
WHERE e.event_type = 'earnings'
  AND e.event_date >= wk.mon AND e.event_date <= date(wk.mon, '+4 days')
ORDER BY e.event_date;

-- EDGAR-verified subset: a firm print vs an aggregator estimate.
CREATE VIEW IF NOT EXISTS v_earnings_confirmed AS
SELECT e.event_date, e.event_time, e.subtype AS ticker, e.title, e.status,
       e.source
FROM events e
WHERE e.event_type = 'earnings'
  AND e.status IN ('confirmed', 'released') AND e.source = 'edgar'
ORDER BY e.event_date;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + earnings views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_EARNINGS_VIEWS)
    conn.commit()
