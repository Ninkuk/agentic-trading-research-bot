from datetime import datetime, timedelta

from sources.common.screener_common import connect

__all__ = ["connect", "ensure_schema", "write_dts_cash", "write_debt_penny",
           "write_avg_rates", "write_upcoming_auctions", "write_auction_results",
           "write_yield_curve", "write_snapshot", "prune", "set_today"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at   TEXT NOT NULL,
    dataset_count INTEGER NOT NULL,
    row_count     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dts_cash (
    record_date   TEXT NOT NULL,
    account_type  TEXT NOT NULL,
    open_balance  REAL,
    close_balance REAL,
    PRIMARY KEY (record_date, account_type)
);
CREATE TABLE IF NOT EXISTS debt_penny (
    record_date      TEXT PRIMARY KEY,
    tot_pub_debt_out REAL,
    debt_held_public REAL,
    intragov_hold    REAL
);
CREATE TABLE IF NOT EXISTS avg_rates (
    record_date        TEXT NOT NULL,
    security_type_desc TEXT NOT NULL,
    security_desc      TEXT NOT NULL,
    avg_interest_rate  REAL,
    PRIMARY KEY (record_date, security_type_desc, security_desc)
);
CREATE TABLE IF NOT EXISTS yield_curve (
    record_date TEXT PRIMARY KEY,
    mo1 REAL, mo2 REAL, mo3 REAL, mo4 REAL, mo6 REAL,
    yr1 REAL, yr2 REAL, yr3 REAL, yr5 REAL, yr7 REAL,
    yr10 REAL, yr20 REAL, yr30 REAL
);
CREATE TABLE IF NOT EXISTS upcoming_auctions (
    cusip             TEXT,
    security_type     TEXT NOT NULL,
    security_term     TEXT NOT NULL,
    announcement_date TEXT,
    auction_date      TEXT NOT NULL,
    issue_date        TEXT,
    PRIMARY KEY (auction_date, security_type, security_term)
);
CREATE TABLE IF NOT EXISTS auction_results (
    cusip              TEXT NOT NULL,
    auction_date       TEXT NOT NULL,
    security_type      TEXT,
    security_term      TEXT,
    high_yield         REAL,
    bid_to_cover_ratio REAL,
    offering_amt       REAL,
    total_accepted     REAL,
    PRIMARY KEY (cusip, auction_date)
);
CREATE TABLE IF NOT EXISTS calendar_now (
    id    INTEGER PRIMARY KEY CHECK (id = 0),
    today TEXT NOT NULL DEFAULT ''
);
INSERT OR IGNORE INTO calendar_now (id, today) VALUES (0, '');
"""


def ensure_schema(conn) -> None:
    """Create all Treasury tables (+ views from Task 4). Idempotent.
    Drops v_upcoming_auctions before recreating to migrate off date('now'),
    and v_tga_trend to migrate off the pre-2022 close_balance-only body."""
    conn.execute("DROP VIEW IF EXISTS v_upcoming_auctions")
    conn.execute("DROP VIEW IF EXISTS v_tga_trend")
    conn.executescript(_SCHEMA + _VIEWS)
    conn.commit()


def _upsert(conn, table, cols, key_cols, rows) -> int:
    """Generic upsert: dedupe by key (last wins), INSERT ... ON CONFLICT(key)
    DO UPDATE the non-key columns. Rows are dicts whose keys are `cols`."""
    by_key = {tuple(r[k] for k in key_cols): r for r in rows}
    placeholders = ", ".join(f":{c}" for c in cols)
    non_key = [c for c in cols if c not in key_cols]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in non_key) or \
        f"{key_cols[0]}={key_cols[0]}"
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({', '.join(key_cols)}) DO UPDATE SET {set_clause}",
        list(by_key.values()))
    conn.commit()
    return len(by_key)


def write_dts_cash(conn, rows) -> int:
    return _upsert(conn, "dts_cash",
                   ["record_date", "account_type", "open_balance", "close_balance"],
                   ["record_date", "account_type"], rows)


def write_debt_penny(conn, rows) -> int:
    return _upsert(conn, "debt_penny",
                   ["record_date", "tot_pub_debt_out", "debt_held_public",
                    "intragov_hold"], ["record_date"], rows)


def write_avg_rates(conn, rows) -> int:
    return _upsert(conn, "avg_rates",
                   ["record_date", "security_type_desc", "security_desc",
                    "avg_interest_rate"],
                   ["record_date", "security_type_desc", "security_desc"], rows)


def write_upcoming_auctions(conn, rows) -> int:
    return _upsert(conn, "upcoming_auctions",
                   ["cusip", "security_type", "security_term", "announcement_date",
                    "auction_date", "issue_date"],
                   ["auction_date", "security_type", "security_term"], rows)


def write_auction_results(conn, rows) -> int:
    return _upsert(conn, "auction_results",
                   ["cusip", "auction_date", "security_type", "security_term",
                    "high_yield", "bid_to_cover_ratio", "offering_amt",
                    "total_accepted"], ["cusip", "auction_date"], rows)


def write_yield_curve(conn, rows) -> int:
    cols = ["record_date", "mo1", "mo2", "mo3", "mo4", "mo6", "yr1", "yr2",
            "yr3", "yr5", "yr7", "yr10", "yr20", "yr30"]
    return _upsert(conn, "yield_curve", cols, ["record_date"], rows)


def write_snapshot(conn, captured_at, dataset_count, row_count) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, dataset_count, row_count) "
        "VALUES (?, ?, ?)", (captured_at, dataset_count, row_count))
    conn.commit()
    return cur.lastrowid


def prune(conn, keep_days, now_iso) -> int:
    """Single-table delete of old snapshot provenance ONLY. The fact tables are
    the historical store and are NEVER cascade-pruned (FRED prune shape)."""
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


def set_today(conn, now_iso: str) -> str:
    """Set the calendar_now singleton from the injected now_iso (monitor_common
    pattern). v_upcoming_auctions filters on this — never date('now')."""
    today = datetime.fromisoformat(now_iso).date().isoformat()
    conn.execute("UPDATE calendar_now SET today=? WHERE id=0", (today,))
    conn.commit()
    return today


_VIEWS = """
-- TGA closing balance per date with ~week-over-week (5 business-day) change.
-- Two DTS formats: since 2022-04-18 the closing balance is its own
-- account_type row whose value the API publishes in open_today_bal (its
-- close_today_bal is always the literal string "null"); before that, one row
-- per account carried a real close_today_bal. One continuous series.
CREATE VIEW IF NOT EXISTS v_tga_trend AS
WITH tga AS (
    SELECT record_date, open_balance AS close_balance FROM dts_cash
    WHERE account_type = 'Treasury General Account (TGA) Closing Balance'
    UNION ALL
    SELECT record_date, close_balance FROM dts_cash
    WHERE account_type IN ('Treasury General Account (TGA)',
                           'Federal Reserve Account')
)
SELECT record_date, close_balance,
       close_balance - LAG(close_balance, 5) OVER (ORDER BY record_date)
         AS wow_change
FROM tga ORDER BY record_date;

-- Total public debt per date with the delta vs the prior stored date.
CREATE VIEW IF NOT EXISTS v_debt_trend AS
SELECT record_date, tot_pub_debt_out,
       tot_pub_debt_out - LAG(tot_pub_debt_out) OVER (ORDER BY record_date)
         AS change_vs_prior
FROM debt_penny ORDER BY record_date;

-- Newest par curve with the 2s10s spread + inversion flag + 3m10y.
CREATE VIEW IF NOT EXISTS v_yield_curve_latest AS
WITH latest AS (SELECT * FROM yield_curve ORDER BY record_date DESC LIMIT 1)
SELECT record_date, yr2, yr10, mo3,
       yr10 - yr2 AS spread_2s10s,
       (yr10 - yr2 < 0) AS inverted,
       yr10 - mo3 AS spread_3m10y
FROM latest;

-- Forward auction calendar: announced auctions dated today or later.
CREATE VIEW IF NOT EXISTS v_upcoming_auctions AS
SELECT u.cusip, u.security_type, u.security_term, u.announcement_date,
       u.auction_date, u.issue_date
FROM upcoming_auctions u, calendar_now p
WHERE u.auction_date >= p.today
ORDER BY u.auction_date;

-- Latest bid-to-cover per term + the term's average across stored auctions.
CREATE VIEW IF NOT EXISTS v_auction_demand AS
WITH ranked AS (
    SELECT security_term, auction_date, bid_to_cover_ratio,
           ROW_NUMBER() OVER (PARTITION BY security_term
                              ORDER BY auction_date DESC) AS rn,
           AVG(bid_to_cover_ratio) OVER (PARTITION BY security_term) AS avg_btc
    FROM auction_results WHERE bid_to_cover_ratio IS NOT NULL
)
SELECT security_term, auction_date, bid_to_cover_ratio AS latest_btc, avg_btc
FROM ranked WHERE rn = 1;
"""
