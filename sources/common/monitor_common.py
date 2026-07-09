"""Shared store for event-date monitors — the forward-calendar analogue of
screener_common. Monitors (econ_calendar, fomc_calendar, market_calendar, ...)
reuse this for the events schema, write semantics, shared views, and prune.

Views are parameterised on 'today' via the single-row calendar_now table (a
SQLite view body cannot bind :today); callers set it from the injected now_iso
with set_today() — never date('now'), so tests are deterministic."""

from datetime import datetime, timedelta

from sources.common.clock import phx_date
from sources.common.screener_common import connect

__all__ = [
    "connect",
    "ensure_schema",
    "set_today",
    "upsert_events",
    "replace_forward_window",
    "write_snapshot",
    "prune",
]

_EVENT_COLS = (
    "event_type",
    "event_date",
    "event_time",
    "subtype",
    "title",
    "status",
    "source",
    "payload",
)

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
    as YYYY-MM-DD. Every view's :today derives from here — never date('now').

    The date is Phoenix-local, not UTC: a run after 17:00 Phoenix is already the
    next UTC day, and a day-ahead `today` would make v_upcoming hide events
    happening today and stop replace_forward_window from re-deleting them."""
    today = phx_date(now_iso)
    conn.execute(
        "UPDATE calendar_now SET today=?, horizon_days=? WHERE id=0", (today, horizon_days)
    )
    conn.commit()
    return today


def upsert_events(conn, rows: list[dict], fetched_at: str) -> int:
    """Insert-or-firm-up events by (event_type, event_date, subtype). A date that
    firms up (tentative -> confirmed) or gains a time updates in place; no
    duplicate row. Dedupes within the batch (last wins). Returns distinct rows."""
    by_key = {(r["event_type"], r["event_date"], r.get("subtype") or ""): r for r in rows}
    params = [
        (
            r["event_type"],
            r["event_date"],
            r.get("event_time"),
            r.get("subtype") or "",
            r.get("title"),
            r.get("status"),
            r["source"],
            r.get("payload"),
            fetched_at,
        )
        for r in by_key.values()
    ]
    conn.executemany(
        f"""INSERT INTO events ({", ".join(_EVENT_COLS)}, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_type, event_date, subtype) DO UPDATE SET
              event_time=excluded.event_time, title=excluded.title,
              status=excluded.status, source=excluded.source,
              payload=excluded.payload, fetched_at=excluded.fetched_at""",
        params,
    )
    conn.commit()
    return len(params)


def replace_forward_window(
    conn, event_type: str, today: str, rows: list[dict], fetched_at: str
) -> int:
    """Cancellation-aware path for one event_type: delete future rows
    (event_date >= today) then insert the freshly-fetched set, so a source that
    stops listing a future event lets that row disappear. Past events
    (event_date < today) are NEVER touched. Returns rows inserted."""
    conn.execute("DELETE FROM events WHERE event_type=? AND event_date >= ?", (event_type, today))
    n = upsert_events(conn, rows, fetched_at)  # commits
    return n


def write_snapshot(conn, captured_at: str, event_count: int, source: str) -> int:
    """Insert one run-provenance header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, event_count, source) VALUES (?, ?, ?)",
        (captured_at, event_count, source),
    )
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.

    Single-table delete of snapshot headers only, exactly like
    fred_screener.db.prune. It must NEVER prune events: the whole point of a
    monitor is the forward calendar. Compares captured_at to a UTC isoformat
    cutoff as a plain string (fixed-width, so lexicographic '<' is correct)."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)
        ).fetchall()
    ]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
