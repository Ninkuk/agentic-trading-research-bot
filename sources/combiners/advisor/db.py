"""advisor.db: snapshot-scoped sizing/risk advice — per-position ATR heat,
composite disagreements, and vol-scaled size caps. Everything cascades on
prune; the permanent record lives upstream (scorer.db), not here.

Heat/cap math is pure Python (build_* helpers) because it joins data already
fetched from four source DBs; views only scope and aggregate."""

import sqlite3
from datetime import datetime, timedelta

# Strong-disagreement thresholds, mirroring composite v_flagged
# (|score_sum| >= 4 AND total >= 3). A schema test pins these to
# composite.db's view text so the two drift together.
STRONG_MIN_ABS_SCORE = 4
STRONG_MIN_TOTAL = 3

_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at           TEXT NOT NULL,
    equity                REAL,
    cash                  REAL,
    buying_power          REAL,
    portfolio_captured_at TEXT,
    composite_captured_at TEXT,
    regime                TEXT,
    sources_failed        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS position_heat (
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots(id),
    symbol       TEXT NOT NULL,
    group_name   TEXT,
    quantity     REAL NOT NULL,
    market_value REAL,
    atr          REAL,
    price        REAL,
    price_date   TEXT,
    heat_dollars REAL,
    heat_pct     REAL,
    weight_pct   REAL,
    score_sum    INTEGER,
    bullish      INTEGER,
    bearish      INTEGER,
    total        INTEGER,
    atr_stale    INTEGER,
    PRIMARY KEY (snapshot_id, symbol)
);

CREATE TABLE IF NOT EXISTS size_caps (
    snapshot_id          INTEGER NOT NULL REFERENCES snapshots(id),
    symbol               TEXT NOT NULL,
    direction            TEXT CHECK (direction IN ('bullish', 'bearish')),
    score_sum            INTEGER,
    atr                  REAL,
    price                REAL,
    cap_shares           REAL,
    cap_dollars          REAL,
    group_name           TEXT,
    group_heat_pct       REAL,
    reliable_signals     INTEGER,
    total_signals        INTEGER,
    exceeds_buying_power INTEGER NOT NULL DEFAULT 0,
    already_held         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, symbol)
);
"""

# Views are DROP+CREATEd every run (scorer pattern) so edits deploy nightly.
_VIEWS = f"""
DROP VIEW IF EXISTS v_latest_snapshot;
CREATE VIEW v_latest_snapshot AS
SELECT id FROM snapshots ORDER BY captured_at DESC, id DESC LIMIT 1;

DROP VIEW IF EXISTS v_latest_heat;
CREATE VIEW v_latest_heat AS
SELECT p.* FROM position_heat p
JOIN v_latest_snapshot l ON p.snapshot_id = l.id;

-- One row of book totals. heat_coverage = share of book market value with
-- a usable ATR, so missing metrics can never silently understate heat.
-- LEFT JOIN so an empty book still yields a row (0 positions, NULL heat).
-- sources_failed rides along: 0 positions is only believable when 0 failed.
DROP VIEW IF EXISTS v_book_heat;
CREATE VIEW v_book_heat AS
SELECT s.id AS snapshot_id, s.captured_at, s.equity, s.sources_failed,
       COUNT(p.symbol) AS positions,
       SUM(p.heat_dollars) AS heat_dollars,
       SUM(p.heat_pct) AS heat_pct,
       CASE WHEN SUM(p.market_value) > 0 THEN
            SUM(CASE WHEN p.atr IS NOT NULL THEN p.market_value ELSE 0 END)
            * 1.0 / SUM(p.market_value) END AS heat_coverage
FROM snapshots s LEFT JOIN position_heat p ON p.snapshot_id = s.id
WHERE s.id IN (SELECT id FROM v_latest_snapshot)
GROUP BY s.id, s.captured_at, s.equity, s.sources_failed;

-- CROSSWALK groups collapsed to one bet; ungrouped symbols are their own
-- single-member bet (exposure adds within a group).
DROP VIEW IF EXISTS v_group_heat;
CREATE VIEW v_group_heat AS
SELECT snapshot_id,
       COALESCE(group_name, symbol) AS bet,
       group_name,
       COUNT(*) AS members,
       GROUP_CONCAT(symbol) AS symbols,
       SUM(heat_dollars) AS heat_dollars,
       SUM(heat_pct) AS heat_pct
FROM v_latest_heat
GROUP BY snapshot_id, COALESCE(group_name, symbol);

-- Holdings today's composite scores negative (long book: bearish evidence
-- against something held). strong mirrors composite v_flagged thresholds.
DROP VIEW IF EXISTS v_disagreements;
CREATE VIEW v_disagreements AS
SELECT *, (score_sum <= -{STRONG_MIN_ABS_SCORE} AND total >= {STRONG_MIN_TOTAL}) AS strong
FROM v_latest_heat
WHERE score_sum < 0;

DROP VIEW IF EXISTS v_latest_caps;
CREATE VIEW v_latest_caps AS
SELECT c.* FROM size_caps c
JOIN v_latest_snapshot l ON c.snapshot_id = l.id;
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Tables (CREATE IF NOT EXISTS), then views (DROP+CREATE)."""
    conn.executescript(_TABLES)
    conn.executescript(_VIEWS)
    conn.commit()


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Cascade position_heat + size_caps then snapshot headers (fully
    snapshot-scoped, same pattern as portfolio.db)."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute("SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,))]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for child in ("position_heat", "size_caps"):
        conn.execute(f"DELETE FROM {child} WHERE snapshot_id IN ({qmarks})", ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
