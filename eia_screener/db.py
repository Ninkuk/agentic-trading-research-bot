from datetime import datetime, timedelta

from screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_series", "write_observations",
           "write_snapshot", "prune"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,
    series_count      INTEGER NOT NULL,
    observation_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS series (
    series_id  TEXT PRIMARY KEY,
    route      TEXT,
    label      TEXT,
    category   TEXT,
    unit       TEXT,
    frequency  TEXT,
    first_seen TEXT,
    last_seen  TEXT
);
CREATE TABLE IF NOT EXISTS eia_obs (
    series_id TEXT NOT NULL REFERENCES series(series_id),
    period    TEXT NOT NULL,
    value     REAL,
    PRIMARY KEY (series_id, period)
);
CREATE INDEX IF NOT EXISTS ix_eia_obs_period ON eia_obs(period);
"""


def ensure_schema(conn) -> None:
    """Create tables + indexes (+ views from Task 4). Idempotent."""
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def upsert_series(conn, metas, captured_at) -> None:
    """Upsert the series dimension: refresh route/label/category/unit/frequency +
    last_seen, preserve first_seen (FRED upsert_series shape)."""
    params = [{"series_id": m["series_id"], "route": m.get("route"),
               "label": m.get("label"), "category": m.get("category"),
               "unit": m.get("unit"), "frequency": m.get("frequency", "weekly"),
               "seen": captured_at} for m in metas]
    conn.executemany(
        """INSERT INTO series (series_id, route, label, category, unit,
                               frequency, first_seen, last_seen)
           VALUES (:series_id, :route, :label, :category, :unit, :frequency,
                   :seen, :seen)
           ON CONFLICT(series_id) DO UPDATE SET
             route=excluded.route, label=excluded.label,
             category=excluded.category, unit=excluded.unit,
             frequency=excluded.frequency, last_seen=excluded.last_seen""",
        params)
    conn.commit()


def write_observations(conn, series_id, rows) -> int:
    """Upsert observations by (series_id, period): revised values overwrite in
    place, periods never duplicate. Dedupe within batch (last wins)."""
    by_period = {r["period"]: r["value"] for r in rows}
    conn.executemany(
        """INSERT INTO eia_obs (series_id, period, value) VALUES (?, ?, ?)
           ON CONFLICT(series_id, period) DO UPDATE SET value=excluded.value""",
        [(series_id, p, v) for p, v in by_period.items()])
    conn.commit()
    return len(by_period)


def write_snapshot(conn, captured_at, series_count, observation_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) "
        "VALUES (?, ?, ?)", (captured_at, series_count, observation_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. eia_obs is the accumulated
    history and is NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})",
                 ids)
    conn.commit()
    return len(ids)


_VIEWS = ""   # filled in Task 4
