"""fomc_calendar store: the shared monitor schema plus three FOMC views. The
events/snapshots/calendar_now DDL lives in monitor_common; this only adds views."""
from sources.common.monitor_common import connect
from sources.common.monitor_common import ensure_schema as _mc_ensure_schema

__all__ = ["connect", "ensure_schema"]

_FOMC_VIEWS = """
-- The single next rate decision, with days_until and the dot-plot flag.
CREATE VIEW IF NOT EXISTS v_next_fomc AS
SELECT e.event_date, e.event_time, e.status,
       CAST(julianday(e.event_date) - julianday(p.today) AS INTEGER) AS days_until,
       json_extract(e.payload, '$.has_sep') AS has_sep
FROM events e, calendar_now p
WHERE e.event_type = 'fomc_meeting' AND e.event_date >= p.today
ORDER BY e.event_date
LIMIT 1;

-- Boolean helper other modules query: is today inside a blackout window?
CREATE VIEW IF NOT EXISTS v_in_blackout AS
SELECT EXISTS(
    SELECT 1 FROM events e, calendar_now p
    WHERE e.event_type = 'fomc_blackout_start'
      AND e.event_date <= p.today
      AND json_extract(e.payload, '$.window_end') >= p.today
) AS in_blackout;

-- The full forward FOMC agenda with a human label per event type.
CREATE VIEW IF NOT EXISTS v_upcoming_fomc_events AS
SELECT e.event_type, e.event_date, e.event_time, e.status, e.title,
       CASE e.event_type
         WHEN 'fomc_meeting'         THEN 'FOMC Rate Decision'
         WHEN 'fomc_sep'             THEN 'Summary of Economic Projections'
         WHEN 'fomc_minutes'         THEN 'FOMC Minutes'
         WHEN 'fomc_blackout_start'  THEN 'Communication Blackout Begins'
         WHEN 'fomc_blackout_end'    THEN 'Communication Blackout Ends'
         ELSE e.event_type END AS label
FROM events e, calendar_now p
WHERE e.event_type LIKE 'fomc\\_%' ESCAPE '\\' AND e.event_date >= p.today
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Shared monitor schema + FOMC views. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_FOMC_VIEWS)
    conn.commit()
