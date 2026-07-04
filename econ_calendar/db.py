from sources.common.monitor_common import connect
from sources.common.monitor_common import ensure_schema as _mc_ensure_schema

from econ_calendar.catalog import CATALOG

__all__ = ["connect", "ensure_schema"]

# release_catalog materializes the Python catalog so the views can JOIN impact /
# label / category in SQL. v_this_week runs today .. the coming Sunday
# (weekday 0), for a weekly planning glance.
_ECON_SCHEMA = """
CREATE TABLE IF NOT EXISTS release_catalog (
    event_type   TEXT PRIMARY KEY,
    release_id   INTEGER NOT NULL,
    label        TEXT NOT NULL,
    impact       TEXT NOT NULL,
    category     TEXT NOT NULL,
    release_time TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_upcoming_releases AS
SELECT u.event_type, u.event_date, u.event_time, u.subtype, u.title, u.status,
       c.label, c.impact, c.category
FROM v_upcoming u
JOIN release_catalog c ON c.event_type = u.event_type
ORDER BY u.event_date, u.event_time;

CREATE VIEW IF NOT EXISTS v_imminent_high_impact AS
SELECT i.event_type, i.event_date, i.event_time, i.subtype, i.title, i.status,
       c.label, c.impact, c.category
FROM v_imminent i
JOIN release_catalog c ON c.event_type = i.event_type
WHERE c.impact = 'high'
ORDER BY i.event_date, i.event_time;

CREATE VIEW IF NOT EXISTS v_this_week AS
SELECT u.event_type, u.event_date, u.event_time, u.subtype, u.title, u.status,
       c.label, c.impact, c.category
FROM v_upcoming u
JOIN release_catalog c ON c.event_type = u.event_type,
     calendar_now p
WHERE u.event_date <= date(p.today, 'weekday 0')
ORDER BY u.event_date, u.event_time;
"""


def ensure_schema(conn) -> None:
    """Create the shared monitor schema + econ-specific catalog table and views,
    then sync release_catalog from CATALOG. Idempotent."""
    _mc_ensure_schema(conn)
    conn.executescript(_ECON_SCHEMA)
    conn.executemany(
        """INSERT INTO release_catalog
           (event_type, release_id, label, impact, category, release_time)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(event_type) DO UPDATE SET
             release_id=excluded.release_id, label=excluded.label,
             impact=excluded.impact, category=excluded.category,
             release_time=excluded.release_time""",
        [(r.event_type, r.release_id, r.label, r.impact, r.category,
          r.release_time) for r in CATALOG],
    )
    conn.commit()
