from datetime import datetime, timedelta

from sources.common.screener_common import connect

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
    series_id                 TEXT PRIMARY KEY,
    theme                     TEXT,
    title                     TEXT,
    frequency                 TEXT,
    frequency_short           TEXT,
    units                     TEXT,
    units_short               TEXT,
    seasonal_adjustment_short TEXT,
    observation_start         TEXT,
    observation_end           TEXT,
    last_updated              TEXT,
    popularity                INTEGER,
    notes                     TEXT,
    first_seen                TEXT,
    last_seen                 TEXT
);
CREATE TABLE IF NOT EXISTS observations (
    series_id TEXT NOT NULL REFERENCES series(series_id),
    date      TEXT NOT NULL,
    value     REAL,
    PRIMARY KEY (series_id, date)
);
CREATE INDEX IF NOT EXISTS ix_observations_date ON observations(date);

-- Latest non-null observation per series, joined to metadata.
CREATE VIEW IF NOT EXISTS v_latest AS
WITH ranked AS (
    SELECT o.series_id, o.date, o.value,
           ROW_NUMBER() OVER (PARTITION BY o.series_id
                              ORDER BY o.date DESC) AS rn
    FROM observations o
    WHERE o.value IS NOT NULL
)
SELECT r.series_id, s.theme, s.title, s.units_short, s.frequency_short,
       r.date, r.value
FROM ranked r JOIN series s ON s.series_id = r.series_id
WHERE r.rn = 1;

-- Latest value vs. the nearest observation on/before ~1 year earlier.
CREATE VIEW IF NOT EXISTS v_yoy_change AS
SELECT l.series_id, l.theme, l.title, l.date AS latest_date, l.value AS latest,
       p.value AS year_ago,
       l.value - p.value AS change_abs,
       CASE WHEN p.value IS NOT NULL AND p.value <> 0
            THEN 100.0 * (l.value - p.value) / p.value END AS change_pct
FROM v_latest l
LEFT JOIN observations p ON p.series_id = l.series_id
     AND p.value IS NOT NULL
     AND p.date = (
        SELECT MAX(o2.date) FROM observations o2
        WHERE o2.series_id = l.series_id AND o2.value IS NOT NULL
          AND o2.date <= date(l.date, '-1 year'));

-- Latest value as a z-score over the series' full stored history.
CREATE VIEW IF NOT EXISTS v_zscore AS
WITH stats AS (
    SELECT series_id, AVG(value) AS mean,
           -- population stddev; SQLite has no STDDEV, compute from moments
           CASE WHEN COUNT(value) > 1
                THEN SQRT(AVG(value*value) - AVG(value)*AVG(value)) END AS sd
    FROM observations WHERE value IS NOT NULL GROUP BY series_id
)
SELECT l.series_id, l.theme, l.title, l.value AS latest, st.mean, st.sd,
       CASE WHEN st.sd IS NOT NULL AND st.sd <> 0
            THEN (l.value - st.mean) / st.sd END AS zscore
FROM v_latest l JOIN stats st ON st.series_id = l.series_id;

-- Curated macro regime flags from the latest values (LEFT JOINs so a
-- partial --only run yields NULLs instead of erroring on missing series).
CREATE VIEW IF NOT EXISTS v_regime_signals AS
SELECT
    curve.value        AS t10y2y,
    (curve.value < 0)  AS yield_curve_inverted,
    hy.value           AS hy_spread,
    ff.value           AS fed_funds,
    unrate.value       AS unemployment
FROM (SELECT 1) base
LEFT JOIN v_latest curve  ON curve.series_id  = 'T10Y2Y'
LEFT JOIN v_latest hy     ON hy.series_id     = 'BAMLH0A0HYM2'
LEFT JOIN v_latest ff     ON ff.series_id     = 'DFF'
LEFT JOIN v_latest unrate ON unrate.series_id = 'UNRATE';
"""

_SERIES_FIELDS = ("frequency", "frequency_short", "units", "units_short",
                  "seasonal_adjustment_short", "observation_start",
                  "observation_end", "last_updated", "popularity", "notes")


def ensure_schema(conn) -> None:
    """Create tables + ELT views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_series(conn, meta_rows: list[dict], captured_at: str) -> None:
    """Upsert the series dimension: refresh metadata + last_seen, preserve
    first_seen. Each meta_row is a FRED series dict plus a 'theme' key."""
    params = []
    for m in meta_rows:
        row = {"series_id": m["id"], "theme": m.get("theme"),
               "title": m.get("title"), "seen": captured_at}
        for f in _SERIES_FIELDS:
            row[f] = m.get(f)
        params.append(row)
    conn.executemany(
        f"""INSERT INTO series
            (series_id, theme, title, {", ".join(_SERIES_FIELDS)},
             first_seen, last_seen)
            VALUES (:series_id, :theme, :title,
                    {", ".join(":" + f for f in _SERIES_FIELDS)},
                    :seen, :seen)
            ON CONFLICT(series_id) DO UPDATE SET
              theme=excluded.theme, title=excluded.title,
              {", ".join(f"{f}=excluded.{f}" for f in _SERIES_FIELDS)},
              last_seen=excluded.last_seen""",
        params,
    )
    conn.commit()


def write_observations(conn, series_id: str, obs_rows: list[dict]) -> int:
    """Upsert observations by (series_id, date): revised values overwrite in
    place, dates are never duplicated. Dedupes within the batch (last wins)."""
    by_date = {r["date"]: r["value"] for r in obs_rows}
    conn.executemany(
        """INSERT INTO observations (series_id, date, value)
           VALUES (?, ?, ?)
           ON CONFLICT(series_id, date) DO UPDATE SET value=excluded.value""",
        [(series_id, d, v) for d, v in by_date.items()],
    )
    conn.commit()
    return len(by_date)


def write_snapshot(conn, captured_at: str, series_count: int,
                   observation_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) "
        "VALUES (?, ?, ?)",
        (captured_at, series_count, observation_count),
    )
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.

    NOTE: unlike the other screeners, observations are NOT snapshot-scoped
    (they are upserted by (series_id, date) and are the historical store), so
    this is a plain single-table delete of old snapshot headers, NOT the shared
    cascade prune in screener_common. Do not wire observations into a cascade."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)).fetchall()]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
