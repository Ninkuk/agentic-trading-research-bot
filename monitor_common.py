"""Shared store for event-date monitors — the forward-calendar analogue of
screener_common. Monitors (econ_calendar, fomc_calendar, market_calendar, ...)
reuse this for the events schema, write semantics, shared views, and prune.

Views are parameterised on 'today' via the single-row calendar_now table (a
SQLite view body cannot bind :today); callers set it from the injected now_iso
with set_today() — never date('now'), so tests are deterministic."""
from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "set_today", "upsert_events",
           "replace_forward_window", "write_snapshot", "prune"]

_EVENT_COLS = ("event_type", "event_date", "event_time", "subtype", "title",
               "status", "source", "payload")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,               -- YYYY-MM-DD
    event_time TEXT,                        -- 'HH:MM' ET if known else NULL
    subtype    TEXT NOT NULL DEFAULT '',    -- part of the natural key; '' not NULL
    title      TEXT,
    status     TEXT,                        -- tentative|scheduled|confirmed|released
    source     TEXT NOT NULL,
    payload    TEXT,                         -- optional JSON extras
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (event_type, event_date, subtype)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT,
    event_count INTEGER,
    source      TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type);

-- Single-row params table so real named views can filter on an injected 'today'.
CREATE TABLE IF NOT EXISTS calendar_now (
    id           INTEGER PRIMARY KEY CHECK (id = 0),
    today        TEXT NOT NULL DEFAULT '',
    horizon_days INTEGER NOT NULL DEFAULT 7
);
INSERT OR IGNORE INTO calendar_now (id, today, horizon_days) VALUES (0, '', 7);

-- Forward calendar: everything from today onward.
CREATE VIEW IF NOT EXISTS v_upcoming AS
SELECT e.* FROM events e, calendar_now p
WHERE e.event_date >= p.today
ORDER BY e.event_date, e.event_time;

-- Near-term watch list: today .. today + horizon_days.
CREATE VIEW IF NOT EXISTS v_imminent AS
SELECT e.* FROM events e, calendar_now p
WHERE e.event_date BETWEEN p.today
      AND date(p.today, '+' || p.horizon_days || ' days')
ORDER BY e.event_date, e.event_time;
"""


def ensure_schema(conn) -> None:
    """Create the events/snapshots/calendar_now schema + shared views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def set_today(conn, now_iso: str, horizon_days: int = 7) -> str:
    """Set the calendar_now singleton from the injected now_iso. Returns today
    as YYYY-MM-DD. Every view's :today derives from here — never date('now')."""
    today = datetime.fromisoformat(now_iso).date().isoformat()
    conn.execute("UPDATE calendar_now SET today=?, horizon_days=? WHERE id=0",
                 (today, horizon_days))
    conn.commit()
    return today
