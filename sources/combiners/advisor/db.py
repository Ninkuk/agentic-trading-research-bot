"""advisor.db: snapshot-scoped sizing/risk advice — per-position ATR heat,
composite disagreements, and vol-scaled size caps. Everything cascades on
prune; the permanent record lives upstream (scorer.db), not here.

Heat/cap math is pure Python (build_* helpers) because it joins data already
fetched from four source DBs; views only scope and aggregate."""

import sqlite3
from datetime import date, datetime, timedelta

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


def write_snapshot(conn, now_iso: str) -> int:
    cur = conn.execute("INSERT INTO snapshots (captured_at) VALUES (?)", (now_iso,))
    conn.commit()  # survive later per-source rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid, account, composite, sources_failed=0) -> None:
    """Freeze account scalars + upstream provenance into the header (every
    derived number depends on them). Either upstream may be None.
    sources_failed distinguishes a genuinely empty book from a night where
    a source read failed and left the tables empty."""
    a, c = account or {}, composite or {}
    conn.execute(
        "UPDATE snapshots SET equity=?, cash=?, buying_power=?,"
        " portfolio_captured_at=?, composite_captured_at=?, regime=?,"
        " sources_failed=? WHERE id=?",
        (
            a.get("equity"),
            a.get("cash"),
            a.get("buying_power"),
            a.get("captured_at"),
            c.get("captured_at"),
            c.get("regime"),
            sources_failed,
            sid,
        ),
    )


def _age_days(today: str, obs_date: str) -> int:
    return (date.fromisoformat(today) - date.fromisoformat(obs_date)).days


def build_position_heat(
    positions, scorecard, metrics, equity, today, ticker_group, atr_max_age_days
) -> list:
    """One row per held position. heat = quantity x ATR (dollars lost on a
    one-ATR adverse day); NULL heat when the symbol has no metrics row —
    visible, never silently dropped (v_book_heat.heat_coverage counts it)."""
    rows = []
    for p in positions:
        sym = p["symbol"]
        m = metrics.get(sym, {})
        atr, close, pdate = m.get("atr"), m.get("close"), m.get("price_date")
        heat_dollars = p["quantity"] * atr if atr is not None else None
        heat_pct = heat_dollars / equity if heat_dollars is not None and equity else None
        weight_pct = (
            p["market_value"] / equity if p["market_value"] is not None and equity else None
        )
        sc = scorecard.get(sym, {})
        atr_stale = None
        if pdate is not None:
            atr_stale = 1 if _age_days(today, pdate) > atr_max_age_days else 0
        rows.append(
            {
                "symbol": sym,
                "group_name": ticker_group.get(sym),
                "quantity": p["quantity"],
                "market_value": p["market_value"],
                "atr": atr,
                "price": close,
                "price_date": pdate,
                "heat_dollars": heat_dollars,
                "heat_pct": heat_pct,
                "weight_pct": weight_pct,
                "score_sum": sc.get("score_sum"),
                "bullish": sc.get("bullish"),
                "bearish": sc.get("bearish"),
                "total": sc.get("total"),
                "atr_stale": atr_stale,
            }
        )
    return rows


def build_size_caps(
    flagged,
    scorecard,
    metrics,
    heat_rows,
    equity,
    buying_power,
    risk_budget,
    ticker_group,
    flag_signals,
    reliable_ids,
) -> list:
    """One row per flagged ticker. The cap inverts the risk budget and
    shrinks by heat already carried through the same crosswalk group (a
    group is one bet): allowed = max(0, budget*equity - group_heat), then
    cap_shares = allowed / ATR — FRACTIONAL, matching Robinhood fractional
    sizing (flooring to whole shares would zero every cap on a small
    account). Bearish flags carry NULL caps: the book is long-only, so the
    row itself (direction, score, group) is the advice, never a buy size.
    Same-group sibling caps each see the same remaining budget —
    alternatives, not a shopping list. exceeds_buying_power and the
    reliable-evidence counts are annotations, never gates (reliable = the
    scorer's n_bench >= 30 sample floor, not proof a signal works);
    flag_signals/reliable_ids intersect on (signal_id, via_crosswalk)
    pairs so crosswalk-only reliability never cites as direct evidence."""
    group_heat: dict = {}
    held = set()
    for r in heat_rows:
        held.add(r["symbol"])
        if r["heat_dollars"] is not None:
            bet = r["group_name"] or r["symbol"]
            group_heat[bet] = group_heat.get(bet, 0.0) + r["heat_dollars"]
    rows = []
    for sym in flagged:
        sc = scorecard.get(sym, {})
        m = metrics.get(sym, {})
        atr, close = m.get("atr"), m.get("close")
        existing = group_heat.get(ticker_group.get(sym) or sym, 0.0)
        score_sum = sc.get("score_sum")
        direction = "bullish" if (score_sum or 0) > 0 else "bearish"
        cap_shares = cap_dollars = None
        if direction == "bullish" and atr and equity:
            allowed = max(0.0, risk_budget * equity - existing)
            cap_shares = allowed / atr
            if close is not None:
                cap_dollars = cap_shares * close
        sigs = flag_signals.get(sym, set())
        rows.append(
            {
                "symbol": sym,
                "direction": direction,
                "score_sum": score_sum,
                "atr": atr,
                "price": close,
                "cap_shares": cap_shares,
                "cap_dollars": cap_dollars,
                "group_name": ticker_group.get(sym),
                "group_heat_pct": existing / equity if equity else None,
                "reliable_signals": len(sigs & reliable_ids),
                "total_signals": len(sigs),
                "exceeds_buying_power": 1
                if cap_dollars is not None
                and buying_power is not None
                and cap_dollars > buying_power
                else 0,
                "already_held": 1 if sym in held else 0,
            }
        )
    return rows


def write_position_heat(conn, sid, rows) -> int:
    conn.executemany(
        "INSERT INTO position_heat (snapshot_id, symbol, group_name, quantity,"
        " market_value, atr, price, price_date, heat_dollars, heat_pct,"
        " weight_pct, score_sum, bullish, bearish, total, atr_stale)"
        " VALUES (:sid, :symbol, :group_name, :quantity, :market_value, :atr,"
        " :price, :price_date, :heat_dollars, :heat_pct, :weight_pct,"
        " :score_sum, :bullish, :bearish, :total, :atr_stale)",
        [{**r, "sid": sid} for r in rows],
    )
    return len(rows)


def write_size_caps(conn, sid, rows) -> int:
    conn.executemany(
        "INSERT INTO size_caps (snapshot_id, symbol, direction, score_sum,"
        " atr, price, cap_shares, cap_dollars, group_name, group_heat_pct,"
        " reliable_signals, total_signals, exceeds_buying_power, already_held)"
        " VALUES (:sid, :symbol, :direction, :score_sum, :atr, :price,"
        " :cap_shares, :cap_dollars, :group_name, :group_heat_pct,"
        " :reliable_signals, :total_signals, :exceeds_buying_power,"
        " :already_held)",
        [{**r, "sid": sid} for r in rows],
    )
    return len(rows)
