from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = [
    "connect",
    "ensure_schema",
    "write_observations",
    "write_wasde",
    "write_snapshot",
    "prune",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at       TEXT NOT NULL,
    series_count      INTEGER NOT NULL,
    observation_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usda_obs (
    commodity TEXT NOT NULL,
    metric    TEXT NOT NULL,
    period    TEXT NOT NULL,
    value     REAL,
    unit      TEXT,
    PRIMARY KEY (commodity, metric, period)
);
CREATE INDEX IF NOT EXISTS ix_usda_obs_period ON usda_obs(period);

-- Latest period per (commodity, metric): current balance-sheet lines.
CREATE VIEW IF NOT EXISTS v_latest_balance AS
WITH ranked AS (
    SELECT commodity, metric, period, value, unit,
           ROW_NUMBER() OVER (PARTITION BY commodity, metric
                              ORDER BY period DESC) AS rn
    FROM usda_obs WHERE value IS NOT NULL
)
SELECT commodity, metric, period, value, unit FROM ranked WHERE rn = 1;

-- The key gauge: ending_stocks / total_use per commodity per period.
CREATE VIEW IF NOT EXISTS v_stocks_to_use AS
SELECT es.commodity, es.period, es.value AS ending_stocks,
       tu.value AS total_use,
       CASE WHEN tu.value IS NOT NULL AND tu.value <> 0
            THEN es.value / tu.value END AS stocks_to_use
FROM usda_obs es
LEFT JOIN usda_obs tu ON tu.commodity = es.commodity
     AND tu.period = es.period AND tu.metric = 'TOTAL_USE'
WHERE es.metric = 'ENDING_STOCKS';

-- Full history per (commodity, metric).
CREATE VIEW IF NOT EXISTS v_series_history AS
SELECT commodity, metric, period, value, unit FROM usda_obs
ORDER BY commodity, metric, period;
"""


# WASDE balance sheet (1e) — a sibling to usda_obs, kept separate so the Quick
# Stats path is untouched. unit is in the PK because a grain's U.S. line appears
# in two tables (U.S.-domestic bushels + world-table metric tons) under the same
# (commodity, region, metric, market_year).
_WASDE_SCHEMA = """
CREATE TABLE IF NOT EXISTS wasde_obs (
    commodity   TEXT NOT NULL,
    region      TEXT NOT NULL,
    metric      TEXT NOT NULL,
    market_year TEXT NOT NULL,
    unit        TEXT NOT NULL,
    value       REAL,
    report_date TEXT,
    PRIMARY KEY (commodity, region, metric, market_year, unit)
);
CREATE INDEX IF NOT EXISTS ix_wasde_commodity ON wasde_obs(commodity, region);

-- The WASDE-native gauge: ending_stocks / total_use per commodity+region+year,
-- on a single unit basis. total_use falls back to domestic_use + exports for
-- commodities (e.g. soybeans) that carry no single "Use, Total" line.
CREATE VIEW IF NOT EXISTS v_wasde_stocks_to_use AS
WITH use AS (
    SELECT commodity, region, market_year, unit,
        MAX(CASE WHEN metric='total_use'    THEN value END) AS total_use,
        MAX(CASE WHEN metric='domestic_use' THEN value END) AS domestic_use,
        MAX(CASE WHEN metric='exports'      THEN value END) AS exports
    FROM wasde_obs GROUP BY commodity, region, market_year, unit
)
SELECT es.commodity, es.region, es.market_year, es.unit,
       es.value AS ending_stocks,
       COALESCE(u.total_use, u.domestic_use + u.exports) AS total_use,
       CASE WHEN COALESCE(u.total_use, u.domestic_use + u.exports) > 0
            THEN es.value / COALESCE(u.total_use, u.domestic_use + u.exports)
            END AS stocks_to_use
FROM wasde_obs es
LEFT JOIN use u ON u.commodity=es.commodity AND u.region=es.region
     AND u.market_year=es.market_year AND u.unit=es.unit
WHERE es.metric='ending_stocks';
"""


def ensure_schema(conn) -> None:
    """Create the Quick Stats fact table + views and the WASDE sibling. Idempotent."""
    conn.executescript(_SCHEMA + _WASDE_SCHEMA)
    conn.commit()


def write_observations(conn, commodity, metric, rows) -> int:
    """Upsert obs by (commodity, metric, period): revisions overwrite in place,
    periods never duplicate. Dedupe within batch (last wins)."""
    by_period = {r["period"]: r for r in rows}
    conn.executemany(
        """INSERT INTO usda_obs (commodity, metric, period, value, unit)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(commodity, metric, period) DO UPDATE SET
             value=excluded.value, unit=excluded.unit""",
        [(commodity, metric, p, r["value"], r.get("unit")) for p, r in by_period.items()],
    )
    conn.commit()
    return len(by_period)


def write_wasde(conn, rows) -> int:
    """Upsert WASDE balance rows by (commodity, region, metric, market_year,
    unit): a later release's revised value overwrites in place. unit is
    coalesced to '' so the PK never sees NULL. Dedupe within batch (last wins)."""
    by_key = {
        (r["commodity"], r["region"], r["metric"], r["market_year"], r.get("unit") or ""): r
        for r in rows
    }
    conn.executemany(
        """INSERT INTO wasde_obs
           (commodity, region, metric, market_year, unit, value, report_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(commodity, region, metric, market_year, unit)
           DO UPDATE SET value=excluded.value, report_date=excluded.report_date""",
        [
            (k[0], k[1], k[2], k[3], k[4], r["value"], r.get("report_date"))
            for k, r in by_key.items()
        ],
    )
    conn.commit()
    return len(by_key)


def write_snapshot(conn, captured_at, series_count, observation_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, series_count, observation_count) VALUES (?, ?, ?)",
        (captured_at, series_count, observation_count),
    )
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshots ONLY. usda_obs is the accumulated
    history and is NEVER cascade-pruned (FRED prune shape)."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,)
        ).fetchall()
    ]
    if not ids:
        return 0
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({','.join('?' * len(ids))})", ids)
    conn.commit()
    return len(ids)
