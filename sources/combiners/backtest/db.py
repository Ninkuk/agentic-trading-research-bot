"""backtest.db: point-in-time replay of composite's FRED regime signals.

Data tables are upsert-keyed history copied out of fred.db (never
snapshot-scoped); prune deletes old snapshot headers ONLY. The product is
the views (Tasks 5-6 of the plan; see the design spec): what flag
composite WOULD have emitted on each historical date using only data
knowable that day, and how the benchmark moved afterward. Manual analysis
tool — deliberately unscheduled."""

import sqlite3
from datetime import datetime, timedelta

from sources.combiners.backtest import catalog
from sources.combiners.scorer.db import RELIABLE_MIN_N, _wilson

_TABLES = """
CREATE TABLE IF NOT EXISTS snapshots (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at    TEXT NOT NULL,
    vintage_rows   INTEGER NOT NULL DEFAULT 0,
    benchmark_rows INTEGER NOT NULL DEFAULT 0,
    market_rows    INTEGER NOT NULL DEFAULT 0,
    sources_failed INTEGER NOT NULL DEFAULT 0
);

-- ALFRED vintages for the replay series: one row per (observation date,
-- publication date). Copied verbatim from fred.db observation_vintages.
CREATE TABLE IF NOT EXISTS signal_vintages (
    series_id      TEXT NOT NULL,
    date           TEXT NOT NULL,
    realtime_start TEXT NOT NULL,
    value          REAL,
    PRIMARY KEY (series_id, date, realtime_start)
);

-- Non-vintage market-grain observations: unrevised same-day exchange series
-- copied from their source DB (val1/val2 are the raw score-input columns; the
-- replay aliases them to the names the composite CASE expects). No
-- realtime_start -- the as-of read is just the latest obs_date <= D.
CREATE TABLE IF NOT EXISTS market_obs (
    signal_id TEXT NOT NULL,
    obs_date  TEXT NOT NULL,
    val1      REAL,
    val2      REAL,
    PRIMARY KEY (signal_id, obs_date)
);

-- The grading spine: benchmark daily closes (SP500 via fred.db
-- observations; index closes are not revised).
CREATE TABLE IF NOT EXISTS benchmark_closes (
    date  TEXT PRIMARY KEY,
    close REAL NOT NULL
);
"""


def _horizons_union() -> str:
    return " UNION ALL ".join(f"SELECT {h} AS horizon" for h in catalog.HORIZONS)


def _flags_select(signal: dict) -> str:
    return (
        f"SELECT asof_date, '{signal['signal_id']}' AS signal_id, value,\n"
        f"       {signal['score_case']} AS score\n"
        f"FROM v_pit_signal\n"
        f"WHERE series_id = '{signal['series_id']}' AND value IS NOT NULL"
    )


def _market_flags_select(signal: dict) -> str:
    """Flag select for a non-vintage market signal: alias the stored val1/val2
    back to the column names its imported CASE expects, then apply raw_expr +
    score_case verbatim over the as-of row (v_pit_market)."""
    alias_cols = ", ".join(f"{src} AS {name}" for name, src in signal["aliases"].items())
    primary = next(iter(signal["aliases"]))  # first CASE column present => a real obs
    return (
        f"SELECT asof_date, '{signal['signal_id']}' AS signal_id,\n"
        f"       {signal['raw_expr']} AS value, {signal['score_case']} AS score\n"
        f"FROM (SELECT asof_date, {alias_cols} FROM v_pit_market\n"
        f"      WHERE signal_id = '{signal['signal_id']}')\n"
        f"WHERE {primary} IS NOT NULL"
    )


def _views() -> str:
    flags = "\nUNION ALL\n".join(
        [_flags_select(s) for s in catalog.REPLAY_SIGNALS]
        + [_market_flags_select(s) for s in catalog.MARKET_OBS_SIGNALS]
    )
    return f"""
-- For every (benchmark trading date D, replay series): the value as KNOWN
-- on D — the latest observation date having any vintage published on or
-- before D, valued at its newest such vintage. NULL when nothing was
-- published yet (LEFT-JOIN-shaped miss, not an error).
DROP VIEW IF EXISTS v_pit_signal;
CREATE VIEW v_pit_signal AS
SELECT d.date AS asof_date, s.series_id,
       (SELECT v.value FROM signal_vintages v
         WHERE v.series_id = s.series_id
           AND v.realtime_start <= d.date
           AND v.value IS NOT NULL
         ORDER BY v.date DESC, v.realtime_start DESC
         LIMIT 1) AS value
FROM benchmark_closes d
CROSS JOIN (SELECT DISTINCT series_id FROM signal_vintages) s;

-- As-of read for non-vintage market signals: for every benchmark date D and
-- market signal, the val1/val2 of the latest observation on or before D (both
-- pick the SAME latest row, so they stay consistent). NULL when nothing was
-- observed yet. No revision trail -- latest obs_date <= D is the whole story.
DROP VIEW IF EXISTS v_pit_market;
CREATE VIEW v_pit_market AS
SELECT d.date AS asof_date, o.signal_id,
       (SELECT m.val1 FROM market_obs m
         WHERE m.signal_id = o.signal_id AND m.obs_date <= d.date
         ORDER BY m.obs_date DESC LIMIT 1) AS val1,
       (SELECT m.val2 FROM market_obs m
         WHERE m.signal_id = o.signal_id AND m.obs_date <= d.date
         ORDER BY m.obs_date DESC LIMIT 1) AS val2
FROM benchmark_closes d
CROSS JOIN (SELECT DISTINCT signal_id FROM market_obs) o;

-- The flag composite WOULD have emitted on each date, via the identical
-- imported CASE expressions (see catalog.REPLAY_SIGNALS + MARKET_OBS_SIGNALS).
DROP VIEW IF EXISTS v_replay_flags;
CREATE VIEW v_replay_flags AS
{flags};

-- Benchmark spine with row numbers: horizons step in TRADING days.
DROP VIEW IF EXISTS v_spine;
CREATE VIEW v_spine AS
SELECT date, close, ROW_NUMBER() OVER (ORDER BY date) AS rn
FROM benchmark_closes;

-- Forward benchmark returns per decision date x horizon. Entry is the
-- first close STRICTLY after asof_date (same no-overnight-look-ahead rule
-- as scorer's entry_for); exit is `horizon` spine rows after entry.
-- Unmatured dates yield NULL via LEFT JOIN.
DROP VIEW IF EXISTS v_replay_returns;
CREATE VIEW v_replay_returns AS
SELECT d.date AS asof_date, h.horizon,
       e.date AS entry_date, e.close AS entry_close,
       x.date AS exit_date, x.close AS exit_close,
       CASE WHEN x.close IS NOT NULL AND e.close IS NOT NULL
            THEN x.close / e.close - 1 END AS fwd_return
FROM v_spine d
CROSS JOIN ({_horizons_union()}) h
LEFT JOIN v_spine e ON e.rn = d.rn + 1
LEFT JOIN v_spine x ON x.rn = d.rn + 1 + h.horizon;

-- Hit-rate scoreboard, same column shape as scorer v_signal_efficacy:
-- hit = sign agreement between flag and forward benchmark return.
-- Neutral (score 0) days form their own direction group with NULL hits —
-- reported as base rate, excluded from grading.
DROP VIEW IF EXISTS v_replay_efficacy;
CREATE VIEW v_replay_efficacy AS
SELECT signal_id, direction, horizon,
       COUNT(*) AS n_days,
       AVG(fwd_return) AS avg_fwd_return,
       AVG(hit) AS hit_rate,
       COUNT(hit) AS n_bench,
       {_wilson("-")} AS hit_ci_lo,
       {_wilson("+")} AS hit_ci_hi,
       (COUNT(hit) >= {RELIABLE_MIN_N}) AS reliable
FROM (
    SELECT f.signal_id,
           CASE WHEN f.score < 0 THEN 'bearish'
                WHEN f.score > 0 THEN 'bullish' ELSE 'neutral' END AS direction,
           r.horizon, r.fwd_return,
           CASE WHEN f.score = 0 OR r.fwd_return IS NULL THEN NULL
                WHEN f.score < 0 AND r.fwd_return < 0 THEN 1
                WHEN f.score > 0 AND r.fwd_return > 0 THEN 1
                ELSE 0 END AS hit
    FROM v_replay_flags f
    JOIN v_replay_returns r ON r.asof_date = f.asof_date
)
GROUP BY signal_id, direction, horizon;
"""


def connect(path: str) -> sqlite3.Connection:
    # uri=True so ATTACH 'file:...?mode=ro' works (plain paths still fine).
    conn = sqlite3.connect(path, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_schema(conn) -> None:
    """Tables (CREATE IF NOT EXISTS), then views (DROP+CREATE)."""
    conn.executescript(_TABLES)
    conn.executescript(_views())
    conn.commit()


def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (now_iso,))
    conn.commit()  # survive a later per-source rollback
    return cur.lastrowid


def finish_snapshot(
    conn,
    sid: int,
    vintage_rows: int,
    benchmark_rows: int,
    sources_failed: int,
    market_rows: int = 0,
) -> None:
    conn.execute(
        "UPDATE snapshots SET vintage_rows = ?, benchmark_rows = ?,"
        " market_rows = ?, sources_failed = ? WHERE id = ?",
        (vintage_rows, benchmark_rows, market_rows, sources_failed, sid),
    )


def insert_vintages(conn, rows) -> int:
    rows = list(rows)
    conn.executemany(
        "INSERT OR REPLACE INTO signal_vintages"
        " (series_id, date, realtime_start, value) VALUES (?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def insert_benchmark(conn, rows) -> int:
    rows = list(rows)
    conn.executemany("INSERT OR REPLACE INTO benchmark_closes (date, close) VALUES (?, ?)", rows)
    return len(rows)


def insert_market_obs(conn, signal_id: str, rows) -> int:
    """Copy a market signal's raw observations (obs_date, val1, val2) verbatim.
    INSERT OR REPLACE so a re-copy of a revised/reposted date overwrites (the
    accepted with-caveat behavior for these unrevised feeds)."""
    tagged = [(signal_id, obs_date, val1, val2) for obs_date, val1, val2 in rows]
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?, ?, ?, ?)",
        tagged,
    )
    return len(tagged)


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Snapshot headers only — signal_vintages/benchmark_closes are the
    replay dataset and are never pruned."""
    cutoff = (datetime.fromisoformat(now_iso) - timedelta(days=keep_days)).isoformat()
    cur = conn.execute("DELETE FROM snapshots WHERE captured_at < ?", (cutoff,))
    conn.commit()
    return cur.rowcount
