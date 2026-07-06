"""composite.db schema: snapshot-scoped signal values, one market-regime
row per run, and a per-ticker scorecard. The composite's value is its
replayable history — everything is snapshot-scoped and pruned by cascade."""
import sqlite3
from datetime import datetime, timedelta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at      TEXT NOT NULL,
    signals_expected INTEGER NOT NULL,
    signals_ok       INTEGER NOT NULL DEFAULT 0,
    signals_failed   INTEGER NOT NULL DEFAULT 0
);

-- Audit trail: every composite number is reconstructible from here.
CREATE TABLE IF NOT EXISTS signal_values (
    snapshot_id    INTEGER NOT NULL REFERENCES snapshots(id),
    signal_id      TEXT NOT NULL,
    grain          TEXT NOT NULL
                   CHECK (grain IN ('market', 'asset_class', 'ticker')),
    entity         TEXT NOT NULL,          -- '*' | asset class | ticker
    raw_value      REAL,
    score          INTEGER NOT NULL DEFAULT 0
                   CHECK (score BETWEEN -2 AND 2),
    obs_date       TEXT,
    staleness_days REAL,
    via_crosswalk  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, signal_id, entity)
);

CREATE TABLE IF NOT EXISTS market_regime (
    snapshot_id          INTEGER PRIMARY KEY REFERENCES snapshots(id),
    t10y2y               REAL,
    curve_inverted       INTEGER,
    hy_spread            REAL,
    vix                  REAL,
    vix_backwardation    INTEGER,
    equity_pcr_pctile    REAL,
    in_fomc_blackout     INTEGER,
    imminent_high_impact INTEGER,
    days_to_opex         INTEGER,
    rrp_change           REAL,
    tga_change           REAL,
    regime               TEXT,             -- risk_on | risk_off | mixed
    inputs_expected      INTEGER NOT NULL,
    inputs_present       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_scores (
    snapshot_id          INTEGER NOT NULL REFERENCES snapshots(id),
    symbol               TEXT NOT NULL,
    bullish              INTEGER NOT NULL DEFAULT 0,
    bearish              INTEGER NOT NULL DEFAULT 0,
    total                INTEGER NOT NULL DEFAULT 0,
    score_sum            INTEGER NOT NULL DEFAULT 0,
    coverage             REAL,
    worst_staleness_days REAL,
    in_portfolio         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, symbol)
);
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine);
    # without it the read-only attach fails outright.
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
