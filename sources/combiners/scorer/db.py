"""scorer.db: the permanent efficacy dataset. prices is a rolling ledger;
outcome tables are never pruned — they ARE the experiment."""

import sqlite3
from datetime import datetime, timedelta

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


def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)",
                       (now_iso,))
    conn.commit()  # survive later rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid, harvested, registered, matured, skipped):
    conn.execute("UPDATE snapshots SET harvested=?, registered=?,"
                 " matured=?, skipped=? WHERE id=?",
                 (harvested, registered, matured, skipped, sid))


def insert_prices(conn, rows) -> int:
    n = 0
    for symbol, price_date, close in rows:
        if symbol is None or price_date is None or close is None:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, price_date, close)"
            " VALUES (?, ?, ?)", (symbol, price_date, close))
        n += cur.rowcount
    return n


def entry_for(conn, symbol, composite_date, max_age_days):
    """Newest ledger close on/before composite_date, unless staler than the
    guard (halted/delisted symbols must not register garbage windows)."""
    row = conn.execute(
        "SELECT price_date, close FROM prices WHERE symbol=?"
        " AND price_date <= ? AND price_date >= date(?, ?)"
        " ORDER BY price_date DESC LIMIT 1",
        (symbol, composite_date, composite_date,
         f"-{int(max_age_days)} days")).fetchone()
    return (row[0], row[1]) if row else None


def _bench_close(conn, benchmark, price_date):
    row = conn.execute("SELECT close FROM prices WHERE symbol=?"
                       " AND price_date=?", (benchmark, price_date)).fetchone()
    return row[0] if row else None


def register_snapshot(conn, csid, composite_date, ticker_rows, signal_rows,
                      regime, horizons, benchmark, max_age_days,
                      now_iso) -> tuple:
    """All-or-nothing registration of one composite snapshot: the marker row
    and every outcome row commit together. Returns (registered, skipped).

    One grading per trading window (adversarial-review F3): weekend and
    same-day-rerun composite snapshots share a benchmark entry date; only
    the first snapshot for that entry date registers outcome rows — later
    ones write a marker-only row so the dedupe is durable and the loop
    never revisits them. Multi-counting duplicate windows would let
    v_bucket_performance treat copies of one window as independent samples.
    """
    registered = skipped = 0
    bench_entry = entry_for(conn, benchmark, composite_date, max_age_days)
    entry_date = bench_entry[0] if bench_entry else None
    with conn:  # transaction
        duplicate_window = entry_date is not None and conn.execute(
            "SELECT 1 FROM registered_snapshots WHERE entry_date = ?"
            " LIMIT 1", (entry_date,)).fetchone() is not None
        conn.execute(
            "INSERT INTO registered_snapshots (composite_snapshot_id,"
            " composite_date, entry_date, registered_at, ticker_rows,"
            " signal_rows, skipped) VALUES (?, ?, ?, ?, 0, 0, 0)",
            (csid, composite_date, entry_date, now_iso))
        if duplicate_window:
            return 0, 0
        for r in ticker_rows:
            entry = entry_for(conn, r["symbol"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO ticker_outcomes"
                    " (composite_snapshot_id, composite_date, symbol,"
                    "  score_sum, total, bullish, bearish, in_portfolio,"
                    "  horizon, entry_date, entry_close, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (csid, composite_date, r["symbol"], r["score_sum"],
                     r["total"], r["bullish"], r["bearish"],
                     r["in_portfolio"], h, entry[0], entry[1], bench))
                registered += 1
        for r in signal_rows:
            entry = entry_for(conn, r["entity"], composite_date, max_age_days)
            if entry is None:
                skipped += 1
                continue
            bench = _bench_close(conn, benchmark, entry[0])
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO signal_outcomes"
                    " (composite_snapshot_id, composite_date, signal_id,"
                    "  entity, score, via_crosswalk, horizon, entry_date,"
                    "  entry_close, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (csid, composite_date, r["signal_id"], r["entity"],
                     r["score"], r["via_crosswalk"], h, entry[0], entry[1],
                     bench))
                registered += 1
        if bench_entry is None:
            skipped += 1
        else:
            for h in horizons:
                conn.execute(
                    "INSERT OR IGNORE INTO regime_outcomes"
                    " (composite_snapshot_id, composite_date, regime,"
                    "  horizon, entry_date, bench_entry_close)"
                    " VALUES (?,?,?,?,?,?)",
                    (csid, composite_date, regime, h,
                     bench_entry[0], bench_entry[1]))
                registered += 1
        conn.execute(
            "UPDATE registered_snapshots SET ticker_rows=?, signal_rows=?,"
            " skipped=? WHERE composite_snapshot_id=?",
            (len(ticker_rows), len(signal_rows), skipped, csid))
    return registered, skipped


def registered_ids(conn):
    return {r[0] for r in conn.execute(
        "SELECT composite_snapshot_id FROM registered_snapshots")}


# Maturation: the Nth distinct ledger date after entry, per symbol.
# NOTE: SQLite rejects a correlated OFFSET ("LIMIT 1 OFFSET t.horizon - 1"
# fails with "no such column"), so the Nth date is selected via a
# COUNT-correlated WHERE instead (adversarial-review F1, verified).
# The julianday bound (F2) refuses to mature across a ledger gap wider
# than the horizon could plausibly span (~2 calendar days per trading day
# + a holiday week) — a gapped row stays pending and visible forever
# rather than silently grading the wrong window into the permanent record.
_MATURE_SYMBOL = """
UPDATE {table} SET
  exit_date = x.xdate,
  exit_close = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate),
  fwd_return = (SELECT close FROM prices
                WHERE symbol = {table}.{sym} AND price_date = x.xdate)
               / entry_close - 1,
  bench_fwd_return = CASE WHEN bench_entry_close IS NOT NULL THEN
      (SELECT close FROM prices
       WHERE symbol = :bench AND price_date = x.xdate)
      / bench_entry_close - 1 END,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = t.{sym} AND p.price_date > t.entry_date
                AND (SELECT COUNT(*) FROM prices q
                     WHERE q.symbol = t.{sym}
                       AND q.price_date > t.entry_date
                       AND q.price_date <= p.price_date) = t.horizon
              LIMIT 1) AS xdate
      FROM {table} t WHERE t.exit_date IS NULL) AS x
WHERE {table}.rowid = x.rid AND x.xdate IS NOT NULL
  AND julianday(x.xdate) - julianday({table}.entry_date)
      <= {table}.horizon * 2 + 7
"""

_MATURE_REGIME = """
UPDATE regime_outcomes SET
  exit_date = x.xdate,
  bench_exit_close = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate),
  bench_fwd_return = (SELECT close FROM prices
                      WHERE symbol = :bench AND price_date = x.xdate)
                     / bench_entry_close - 1,
  matured_at = :now
FROM (SELECT t.rowid AS rid,
             (SELECT p.price_date FROM prices p
              WHERE p.symbol = :bench AND p.price_date > t.entry_date
                AND (SELECT COUNT(*) FROM prices q
                     WHERE q.symbol = :bench
                       AND q.price_date > t.entry_date
                       AND q.price_date <= p.price_date) = t.horizon
              LIMIT 1) AS xdate
      FROM regime_outcomes t WHERE t.exit_date IS NULL) AS x
WHERE regime_outcomes.rowid = x.rid AND x.xdate IS NOT NULL
  AND julianday(x.xdate) - julianday(regime_outcomes.entry_date)
      <= regime_outcomes.horizon * 2 + 7
"""


def mature(conn, now_iso, benchmark="SPY") -> int:
    n = 0
    params = {"now": now_iso, "bench": benchmark}
    for table, sym in (("ticker_outcomes", "symbol"),
                       ("signal_outcomes", "entity")):
        cur = conn.execute(_MATURE_SYMBOL.format(table=table, sym=sym),
                           params)
        n += cur.rowcount
    n += conn.execute(_MATURE_REGIME, params).rowcount
    conn.commit()
    return n


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Run headers + old ledger rows only. Outcome tables are the permanent
    experiment record and are NEVER pruned."""
    header_cutoff = (datetime.fromisoformat(now_iso)
                     - timedelta(days=keep_days)).isoformat()
    price_cutoff = (datetime.fromisoformat(now_iso)
                    - timedelta(days=PRICE_KEEP_DAYS)).date().isoformat()
    n = conn.execute("DELETE FROM snapshots WHERE captured_at < ?",
                     (header_cutoff,)).rowcount
    conn.execute("DELETE FROM prices WHERE price_date < ?", (price_cutoff,))
    conn.commit()
    return n
