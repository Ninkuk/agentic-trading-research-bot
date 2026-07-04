from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "upsert_securities", "replace_period",
           "record_period", "write_snapshot", "stored_periods", "prune"]

_FAIL_COLS = ["cusip", "settlement_date", "period", "symbol", "quantity",
              "price", "dollar_value"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    cusip       TEXT PRIMARY KEY,
    symbol      TEXT,
    description TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE TABLE IF NOT EXISTS fails (
    cusip           TEXT NOT NULL REFERENCES securities(cusip),
    settlement_date TEXT NOT NULL,
    period          TEXT NOT NULL,
    symbol          TEXT,
    quantity        INTEGER NOT NULL,
    price           REAL,
    dollar_value    REAL,
    PRIMARY KEY (cusip, settlement_date)
);
CREATE INDEX IF NOT EXISTS ix_fails_date   ON fails(settlement_date);
CREATE INDEX IF NOT EXISTS ix_fails_period ON fails(period);
CREATE INDEX IF NOT EXISTS ix_fails_symbol ON fails(symbol);
CREATE TABLE IF NOT EXISTS periods (
    period        TEXT PRIMARY KEY,
    settle_start  TEXT NOT NULL,
    settle_end    TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    row_count     INTEGER NOT NULL,
    trailer_count INTEGER
);
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at  TEXT NOT NULL,
    period_count INTEGER NOT NULL,
    row_count    INTEGER NOT NULL
);
"""

_VIEWS = """
-- every fail joined to its security (convenience / per-security history)
CREATE VIEW IF NOT EXISTS v_security_history AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip;

-- (1) latest-settlement-date leaderboard; order by quantity OR dollar_value
CREATE VIEW IF NOT EXISTS v_latest_fails AS
SELECT f.cusip, f.symbol, s.description, f.settlement_date,
       f.quantity, f.price, f.dollar_value
FROM fails f JOIN securities s ON s.cusip = f.cusip
WHERE f.settlement_date = (SELECT MAX(settlement_date) FROM fails);

-- global dense rank of distinct settlement dates (settlement days are not
-- contiguous calendar days; this ordinal defines "consecutive")
CREATE VIEW IF NOT EXISTS v_date_rank AS
SELECT settlement_date,
       DENSE_RANK() OVER (ORDER BY settlement_date) AS drank
FROM (SELECT DISTINCT settlement_date FROM fails);

-- gaps-and-islands: one row per (cusip, unbroken run of >=10k-share days)
CREATE VIEW IF NOT EXISTS v_fail_streaks AS
WITH q AS (
  SELECT f.cusip, f.settlement_date, f.quantity, dr.drank,
         dr.drank - ROW_NUMBER() OVER (PARTITION BY f.cusip
                                       ORDER BY f.settlement_date) AS grp
  FROM fails f JOIN v_date_rank dr USING (settlement_date)
  WHERE f.quantity >= 10000)
SELECT cusip, COUNT(*) AS streak_days,
       MIN(settlement_date) AS streak_start,
       MAX(settlement_date) AS streak_end,
       MAX(quantity) AS peak_quantity
FROM q GROUP BY cusip, grp;

-- (2) Reg SHO threshold PROXY: >=5 consecutive settlement days at >=10k shares.
-- (Missing the "0.5% of shares outstanding" half by design.) active=1 when the
-- streak reaches the newest settlement date.
CREATE VIEW IF NOT EXISTS v_persistent AS
SELECT k.cusip, s.symbol, s.description, k.streak_days,
       k.streak_start, k.streak_end, k.peak_quantity,
       (k.streak_end = (SELECT MAX(settlement_date) FROM fails)) AS active
FROM v_fail_streaks k JOIN securities s ON s.cusip = k.cusip
WHERE k.streak_days >= 5;

-- (3) spikes: latest fails vs the security's own trailing 20-day average
-- (excludes the current day). spike_ratio >= 3 => notable jump.
CREATE VIEW IF NOT EXISTS v_spikes AS
WITH w AS (
  SELECT cusip, settlement_date, quantity,
         AVG(quantity) OVER (PARTITION BY cusip ORDER BY settlement_date
                             ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) AS base
  FROM fails)
SELECT w.cusip, s.symbol, s.description, w.settlement_date,
       w.quantity, w.base,
       CASE WHEN w.base > 0 THEN w.quantity / w.base END AS spike_ratio
FROM w JOIN securities s ON s.cusip = w.cusip
WHERE w.settlement_date = (SELECT MAX(settlement_date) FROM fails)
  AND w.base > 0;
"""


def ensure_schema(conn) -> None:
    """Create tables, indexes, and screener views. Idempotent."""
    conn.executescript(_SCHEMA)
    conn.executescript(_VIEWS)
    conn.commit()


def upsert_securities(conn, rows: list[dict]) -> None:
    """Upsert the CUSIP dimension: extend first_seen/last_seen to the min/max
    settlement_date ever seen, and refresh symbol/description from the row whose
    date is at or after the stored last_seen (so the label reflects the newest
    appearance regardless of insert order)."""
    params = [{"cusip": r["cusip"], "symbol": r.get("symbol"),
               "description": r.get("description"), "d": r["settlement_date"]}
              for r in rows]
    conn.executemany(
        """INSERT INTO securities (cusip, symbol, description, first_seen, last_seen)
           VALUES (:cusip, :symbol, :description, :d, :d)
           ON CONFLICT(cusip) DO UPDATE SET
             first_seen = MIN(securities.first_seen, excluded.first_seen),
             last_seen  = MAX(securities.last_seen,  excluded.last_seen),
             symbol      = CASE WHEN excluded.last_seen >= securities.last_seen
                                THEN excluded.symbol ELSE securities.symbol END,
             description = CASE WHEN excluded.last_seen >= securities.last_seen
                                THEN excluded.description
                                ELSE securities.description END""",
        params,
    )
    conn.commit()


def replace_period(conn, period: str, rows: list[dict]) -> int:
    """Delete all fails for this period, then bulk-insert the given rows.
    Period-replace (not upsert) so a repost that drops a row leaves no orphan.
    Dedupes within the batch by (cusip, settlement_date); each settlement_date
    belongs to exactly one period (a=1..15, b=16..end), so no cross-period
    collision is possible. Returns rows written."""
    by_key = {(r["cusip"], r["settlement_date"]): r for r in rows}
    conn.execute("DELETE FROM fails WHERE period = ?", (period,))
    placeholders = ", ".join(":" + c for c in _FAIL_COLS)
    params = []
    for r in by_key.values():
        p = {c: r.get(c) for c in _FAIL_COLS}
        p["period"] = period
        params.append(p)
    conn.executemany(
        f"INSERT INTO fails ({', '.join(_FAIL_COLS)}) VALUES ({placeholders})",
        params,
    )
    conn.commit()
    return len(by_key)


def record_period(conn, period: str, bounds: tuple, fetched_at: str,
                  row_count: int, trailer_count) -> None:
    """Upsert one period's provenance row."""
    start, end = bounds
    conn.execute(
        """INSERT INTO periods (period, settle_start, settle_end, fetched_at,
                                row_count, trailer_count)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(period) DO UPDATE SET
             fetched_at=excluded.fetched_at, row_count=excluded.row_count,
             trailer_count=excluded.trailer_count""",
        (period, start, end, fetched_at, row_count, trailer_count))
    conn.commit()


def write_snapshot(conn, captured_at: str, period_count: int,
                   row_count: int) -> int:
    """Insert one fetch-run header. Returns the snapshot id."""
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, period_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, period_count, row_count))
    conn.commit()
    return cur.lastrowid


def stored_periods(conn) -> list:
    """All ingested period ids, sorted ascending (lexical == chronological
    because months are zero-padded and 'a' < 'b')."""
    return [r[0] for r in conn.execute(
        "SELECT period FROM periods ORDER BY period")]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Delete run-provenance snapshots older than keep_days before now_iso.
    Fail history is NOT snapshot-scoped, so this is a single-table delete of
    snapshot headers only — do NOT cascade into fails."""
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
