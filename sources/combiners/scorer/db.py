"""scorer.db: the permanent efficacy dataset. prices is a rolling ledger;
outcome tables are never pruned — they ARE the experiment."""

import sqlite3

PRICE_KEEP_DAYS = 90  # must stay > 21 trading days (~31 calendar) + margin

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    harvested   INTEGER NOT NULL DEFAULT 0,
    registered  INTEGER NOT NULL DEFAULT 0,
    matured     INTEGER NOT NULL DEFAULT 0,
    skipped     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prices (
    symbol     TEXT NOT NULL,
    price_date TEXT NOT NULL,
    close      REAL NOT NULL,
    PRIMARY KEY (symbol, price_date)
);

-- Registration marker: a composite snapshot is registered atomically with
-- all its outcome rows, or not at all.
CREATE TABLE IF NOT EXISTS registered_snapshots (
    composite_snapshot_id INTEGER PRIMARY KEY,
    composite_date        TEXT NOT NULL,
    entry_date            TEXT,     -- benchmark entry; NULL if bench absent
    registered_at         TEXT NOT NULL,
    ticker_rows           INTEGER NOT NULL,
    signal_rows           INTEGER NOT NULL,
    skipped               INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    symbol                TEXT NOT NULL,
    score_sum             INTEGER NOT NULL,
    total                 INTEGER NOT NULL,
    bullish               INTEGER NOT NULL,
    bearish               INTEGER NOT NULL,
    in_portfolio          INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, symbol, horizon)
);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    entity                TEXT NOT NULL,
    score                 INTEGER NOT NULL,
    via_crosswalk         INTEGER NOT NULL DEFAULT 0,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    entry_close           REAL NOT NULL,
    bench_entry_close     REAL,
    exit_date             TEXT,
    exit_close            REAL,
    fwd_return            REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, signal_id, entity, horizon)
);

CREATE TABLE IF NOT EXISTS regime_outcomes (
    composite_snapshot_id INTEGER NOT NULL,
    composite_date        TEXT NOT NULL,
    regime                TEXT,
    horizon               INTEGER NOT NULL,
    entry_date            TEXT NOT NULL,
    bench_entry_close     REAL NOT NULL,
    exit_date             TEXT,
    bench_exit_close      REAL,
    bench_fwd_return      REAL,
    matured_at            TEXT,
    PRIMARY KEY (composite_snapshot_id, horizon)
);
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()
