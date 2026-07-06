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


# Signals that inform but do not vote (score is structurally 0 and the
# signal is excluded from bullish/bearish/total and coverage).
INFORMATIONAL_SIGNALS = frozenset({"portfolio_holding"})


def write_snapshot(conn, now_iso: str, signals_expected: int) -> int:
    cur = conn.execute(
        "INSERT INTO snapshots (captured_at, signals_expected) VALUES (?, ?)",
        (now_iso, signals_expected))
    conn.commit()  # survive later per-signal rollbacks
    return cur.lastrowid


def finish_snapshot(conn, sid: int, ok: int, failed: int) -> None:
    conn.execute("UPDATE snapshots SET signals_ok=?, signals_failed=?"
                 " WHERE id=?", (ok, failed, sid))


def write_signal_values(conn, sid: int, rows) -> int:
    n = 0
    for r in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO signal_values (snapshot_id, signal_id,"
            " grain, entity, raw_value, score, obs_date, staleness_days,"
            " via_crosswalk) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, r["signal_id"], r["grain"], r["entity"], r["raw_value"],
             r["score"], r["obs_date"], r["staleness_days"],
             r.get("via_crosswalk", 0)))
        n += cur.rowcount
    return n


def apply_crosswalk(conn, sid: int, crosswalk: dict) -> int:
    """Fan each asset-class row out to its mapped tickers (via_crosswalk=1)."""
    n = 0
    for asset_class, tickers in crosswalk.items():
        rows = conn.execute(
            "SELECT signal_id, raw_value, score, obs_date, staleness_days"
            " FROM signal_values WHERE snapshot_id=? AND grain='asset_class'"
            " AND entity=? AND via_crosswalk=0",
            (sid, asset_class)).fetchall()
        for signal_id, raw, score, obs, stale in rows:
            for t in tickers:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO signal_values (snapshot_id,"
                    " signal_id, grain, entity, raw_value, score, obs_date,"
                    " staleness_days, via_crosswalk)"
                    " VALUES (?, ?, 'ticker', ?, ?, ?, ?, ?, 1)",
                    (sid, signal_id, t, raw, score, obs, stale))
                n += cur.rowcount
    return n


# Hand-set regime thresholds — documented judgment, not fitted. Tune here.
_REGIME_RISK_OFF_VIX = 25.0
_REGIME_RISK_ON_VIX = 20.0
_REGIME_HY_WIDE = 4.0


def _classify_regime(vals: dict) -> str:
    vix, hy = vals.get("vix"), vals.get("hy_spread")
    back = (vals.get("vix_backwardation") or 0) > 0
    if vix is None or hy is None:
        return "mixed"
    if vix >= _REGIME_RISK_OFF_VIX or (back and hy >= _REGIME_HY_WIDE):
        return "risk_off"
    if vix < _REGIME_RISK_ON_VIX and not back and hy < _REGIME_HY_WIDE:
        return "risk_on"
    return "mixed"


def write_market_regime(conn, sid: int, regime_fields: dict) -> None:
    """regime_fields: signal_id -> market_regime column; values come from
    that signal's market-grain raw_value in this snapshot."""
    vals, present = {}, 0
    for signal_id, col in regime_fields.items():
        row = conn.execute(
            "SELECT raw_value FROM signal_values WHERE snapshot_id=?"
            " AND signal_id=? AND entity='*'", (sid, signal_id)).fetchone()
        vals[col] = row[0] if row else None
        present += 1 if row else 0
    t10y2y = vals.get("t10y2y")
    back = vals.get("vix_backwardation")
    conn.execute(
        "INSERT INTO market_regime (snapshot_id, t10y2y, curve_inverted,"
        " hy_spread, vix, vix_backwardation, equity_pcr_pctile,"
        " in_fomc_blackout, imminent_high_impact, days_to_opex, rrp_change,"
        " tga_change, regime, inputs_expected, inputs_present)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, t10y2y,
         None if t10y2y is None else int(t10y2y < 0),
         vals.get("hy_spread"), vals.get("vix"),
         None if back is None else int(back > 0),
         vals.get("equity_pcr_pctile"),
         None if vals.get("in_fomc_blackout") is None
         else int(vals["in_fomc_blackout"]),
         None if vals.get("imminent_high_impact") is None
         else int(vals["imminent_high_impact"]),
         None if vals.get("days_to_opex") is None
         else int(vals["days_to_opex"]),
         vals.get("rrp_change"), vals.get("tga_change"),
         _classify_regime(vals), len(regime_fields), present))


def write_ticker_scores(conn, sid: int) -> int:
    """Counting, not weighting: bullish/bearish/total votes + score sum.
    Informational signals never vote; coverage = total / distinct voting
    ticker-grain signals present in this snapshot."""
    info = ",".join("?" * len(INFORMATIONAL_SIGNALS))
    args = (sid, *INFORMATIONAL_SIGNALS)
    applicable = conn.execute(
        f"SELECT COUNT(DISTINCT signal_id) FROM signal_values"
        f" WHERE snapshot_id=? AND grain='ticker'"
        f" AND signal_id NOT IN ({info})", args).fetchone()[0]
    conn.execute(
        f"INSERT INTO ticker_scores (snapshot_id, symbol, bullish, bearish,"
        f" total, score_sum, coverage, worst_staleness_days)"
        f" SELECT snapshot_id, entity,"
        f"  SUM(score > 0), SUM(score < 0), COUNT(*), SUM(score),"
        f"  CASE WHEN ? > 0 THEN CAST(COUNT(*) AS REAL) / ? END,"
        f"  MAX(staleness_days)"
        f" FROM signal_values WHERE snapshot_id=? AND grain='ticker'"
        f" AND signal_id NOT IN ({info}) GROUP BY entity",
        (applicable, applicable, *args))
    # Held tickers always appear, even with zero signals; then flag them.
    conn.execute(
        "INSERT OR IGNORE INTO ticker_scores (snapshot_id, symbol, coverage)"
        " SELECT snapshot_id, entity, 0.0 FROM signal_values"
        " WHERE snapshot_id=? AND signal_id='portfolio_holding'", (sid,))
    conn.execute(
        "UPDATE ticker_scores SET in_portfolio=1 WHERE snapshot_id=?"
        " AND symbol IN (SELECT entity FROM signal_values WHERE snapshot_id=?"
        " AND signal_id='portfolio_holding')", (sid, sid))
    return conn.execute("SELECT COUNT(*) FROM ticker_scores"
                        " WHERE snapshot_id=?", (sid,)).fetchone()[0]


def prune(conn, keep_days: int, now_iso: str) -> int:
    """Snapshot cascade over ALL child tables. Same fixed-width-timestamp
    caveat as screener_common.prune (which handles a single child table —
    calling it once per child would orphan the later ones, so the cascade
    is reimplemented here over the three children)."""
    cutoff = (datetime.fromisoformat(now_iso)
              - timedelta(days=keep_days)).isoformat()
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM snapshots WHERE captured_at < ?", (cutoff,))]
    if not ids:
        return 0
    qmarks = ",".join("?" * len(ids))
    for table in ("signal_values", "market_regime", "ticker_scores"):
        conn.execute(f"DELETE FROM {table} WHERE snapshot_id IN ({qmarks})",
                     ids)
    conn.execute(f"DELETE FROM snapshots WHERE id IN ({qmarks})", ids)
    conn.commit()
    return len(ids)
