"""Candidate-screen grading: the scorer records each night's candidates
list (candidate_appearances, from stocks.db read-only) and creates graded
outcome rows ONLY for list-ENTRY episodes — a name sits on the list for
weeks, and grading every sighting would count one call N times (the
overlapping-sample trap v_signal_efficacy documents). Outcomes reuse the
verdict machinery: same ledger, same no-look-ahead entry, same maturation
SQL. This grades the screen's dislocation TIMING at 21/63 trading days vs
SPY — calibration only; nothing feeds back into the gates."""

import datetime as dt
import sqlite3

from sources.combiners.composite import candidates
from sources.combiners.scorer import catalog, db, fetch
from sources.screeners.stock_analysis_screener import db as stocks_db

NOW = "2026-07-07T04:12:00+00:00"  # 21:12 Phoenix on 2026-07-06


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _ledger(conn, symbol, dates, start=100.0, step=1.0):
    db.insert_prices(conn, [(symbol, d, start + i * step) for i, d in enumerate(dates)])


def _row(symbol="GOOD", rsi=38.0, high52ch=-20.0, fcf_yield=6.0, fscore=7.0, **quality):
    return {
        "symbol": symbol,
        "fcf_yield": fcf_yield,
        "rsi": rsi,
        "high52ch": high52ch,
        "fscore": fscore,
        **quality,
        "via_rsi": int(rsi is not None and 0 < rsi < candidates.RSI_MAX),
        "via_drawdown": int(high52ch is not None and high52ch <= candidates.HIGH52_DISLOCATION_MAX),
    }


def _appear(conn, symbol, screen_date, **metrics):
    return db.record_appearances(
        conn, [_row(symbol=symbol, **metrics)], screen_date, candidates.SCREEN_VERSION, NOW
    )


# ------------------------------------------------------------ catalog ----


def test_candidate_grading_constants_wellformed():
    """21/63 trading days grade the dislocation-timing claim; 5/10d would
    grade noise for a screen whose thesis is quarters, not days."""
    assert catalog.CANDIDATE_HORIZONS == (21, 63)
    assert catalog.CANDIDATE_ENTRY_GAP_DAYS == 7
    assert catalog.STOCKS_DB == "stocks.db"


def test_screen_version_is_pinned_in_candidates():
    """Appearance rows are stamped with the gate-set version so efficacy
    samples never mix gate regimes."""
    assert isinstance(candidates.SCREEN_VERSION, str) and candidates.SCREEN_VERSION


# ------------------------------------------------------------- schema ----


def test_schema_has_candidate_tables(tmp_path):
    conn = _conn(tmp_path)
    a_cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_appearances)")}
    assert {"symbol", "screen_date", "screen_version", "via_rsi", "via_drawdown"} <= a_cols
    o_cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_outcomes)")}
    v_cols = {r[1] for r in conn.execute("PRAGMA table_info(verdict_outcomes)")}
    # Mirrors verdict_outcomes (modulo the FK name) so the generic
    # _MATURE_SYMBOL template grades this table with zero forked SQL.
    assert o_cols - {"appearance_id"} == v_cols - {"verdict_id"}


# ------------------------------------------------------- appearances ----


def test_record_appearances_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    assert _appear(conn, "AAA", "2026-07-01") == 1
    assert _appear(conn, "AAA", "2026-07-01") == 0  # weekend re-sight is free
    assert conn.execute("SELECT COUNT(*) FROM candidate_appearances").fetchone()[0] == 1


def test_appearance_stores_metrics_and_branch_flags(tmp_path):
    conn = _conn(tmp_path)
    _appear(conn, "INTU", "2026-07-01", rsi=62.0, high52ch=-45.0)
    row = conn.execute(
        "SELECT via_rsi, via_drawdown, screen_version FROM candidate_appearances"
    ).fetchone()
    assert row == (0, 1, candidates.SCREEN_VERSION)


# ------------------------------------------- entry-episode registration ----


def test_first_appearance_registers_all_horizons(tmp_path):
    conn = _conn(tmp_path)
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    _ledger(conn, "AAA", dates, start=100.0)
    _ledger(conn, "SPY", dates, start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    n = db.register_candidates(conn, (2, 3), "SPY", 7, 7)
    assert n == 2
    row = conn.execute(
        "SELECT entry_date, entry_close, bench_entry_close FROM candidate_outcomes"
    ).fetchone()
    # STRICTLY AFTER the screen date — never the same-day close.
    assert row == ("2026-07-02", 101.0, 501.0)


def test_continuation_within_gap_never_grades(tmp_path):
    """The same episode re-sighted two days later must not become a second
    graded call."""
    conn = _conn(tmp_path)
    _ledger(conn, "AAA", ["2026-07-01", "2026-07-02", "2026-07-04"], start=100.0)
    _ledger(conn, "SPY", ["2026-07-02", "2026-07-04"], start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    _appear(conn, "AAA", "2026-07-03")
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 1
    entries = conn.execute("SELECT DISTINCT entry_date FROM candidate_outcomes").fetchall()
    assert entries == [("2026-07-02",)]  # only the 07-01 entry graded


def test_reentry_after_the_gap_is_a_new_episode(tmp_path):
    conn = _conn(tmp_path)
    days = [f"2026-07-{d:02d}" for d in range(1, 25)]
    _ledger(conn, "AAA", days, start=100.0)
    _ledger(conn, "SPY", days, start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    _appear(conn, "AAA", "2026-07-20")  # off the list >7 days, back on
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 2


def test_candidate_register_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAA", ["2026-07-02"], start=100.0)
    _ledger(conn, "SPY", ["2026-07-02"], start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    assert db.register_candidates(conn, (2, 5), "SPY", 7, 7) == 2
    assert db.register_candidates(conn, (2, 5), "SPY", 7, 7) == 0


def test_uncovered_candidate_defers_then_heals(tmp_path):
    conn = _conn(tmp_path)
    _appear(conn, "ZZZ", "2026-07-01")
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 0  # no ledger rows
    _ledger(conn, "ZZZ", ["2026-07-03"], start=50.0)
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 1


def test_late_coverage_beyond_guard_never_registers(tmp_path):
    conn = _conn(tmp_path)
    _appear(conn, "CSU", "2026-07-01")
    _ledger(conn, "CSU", ["2026-07-20"], start=100.0)  # first print 19 days later
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 0


# ---------------------------------------------------------- maturation ----


def test_candidate_register_and_mature_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    _ledger(conn, "AAA", dates, start=100.0)  # 100,101,102,103
    _ledger(conn, "SPY", dates, start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 1
    db.mature(conn, "2026-07-07T04:12:00+00:00", "SPY")
    row = conn.execute(
        "SELECT exit_date, exit_close, fwd_return, bench_fwd_return"
        " FROM candidate_outcomes WHERE matured_at IS NOT NULL"
    ).fetchone()
    assert row is not None
    assert row[0] == "2026-07-06" and row[1] == 103.0
    assert abs(row[2] - (103.0 / 101.0 - 1)) < 1e-12
    assert abs(row[3] - (503.0 / 501.0 - 1)) < 1e-12


def test_rebuild_prices_sweeps_unmatured_candidate_outcomes(tmp_path):
    """candidate_outcomes is derived and rebuildable; candidate_appearances
    is the screen's own ledger and must survive a price rebuild."""
    conn = _conn(tmp_path)
    _ledger(conn, "AAA", ["2026-07-02"], start=100.0)
    _ledger(conn, "SPY", ["2026-07-02"], start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 1
    db.rebuild_prices(conn)
    assert conn.execute("SELECT COUNT(*) FROM candidate_outcomes").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM candidate_appearances").fetchone()[0] == 1
    assert "candidate_outcomes" in db.matured_counts(conn)


# ---------------------------------------------------------------- views ----


def test_efficacy_splits_by_dislocation_branch(tmp_path):
    """The actionable readout: does the momentum branch or the price-level
    branch carry the timing edge? One matured winner via rsi, one matured
    loser via drawdown, graded at the same horizon."""
    conn = _conn(tmp_path)
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    _ledger(conn, "WIN", dates, start=100.0, step=5.0)  # beats SPY
    _ledger(conn, "LOSE", dates, start=100.0, step=-2.0)  # loses to SPY
    _ledger(conn, "SPY", dates, start=500.0, step=1.0)
    _appear(conn, "WIN", "2026-07-01", rsi=30.0, high52ch=-10.0)  # rsi branch
    _appear(conn, "LOSE", "2026-07-01", rsi=60.0, high52ch=-45.0)  # drawdown branch
    assert db.register_candidates(conn, (2,), "SPY", 7, 7) == 2
    db.mature(conn, "2026-07-07T04:12:00+00:00", "SPY")
    rows = {
        r[0]: (r[1], r[2])
        for r in conn.execute(
            "SELECT branch, n, hit_rate FROM v_candidate_efficacy WHERE horizon = 2"
        )
    }
    assert rows["rsi"] == (1, 1.0)
    assert rows["drawdown"] == (1, 0.0)


def test_unmatured_rows_are_visible_but_not_counted(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAA", ["2026-07-02"], start=100.0)
    _ledger(conn, "SPY", ["2026-07-02"], start=500.0)
    _appear(conn, "AAA", "2026-07-01")
    db.register_candidates(conn, (21,), "SPY", 7, 7)
    assert conn.execute("SELECT COUNT(*) FROM v_candidate_outcomes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM v_candidate_efficacy").fetchone()[0] == 0


# ------------------------------------------------- fetch from stocks.db ----

_SCREEN_COLS = {
    "sector": "TEXT",
    "marketCap": "REAL",
    "dollarVolume": "REAL",
    "roic": "REAL",
    "roic5y": "REAL",
    "fcfYield": "REAL",
    "revenueGrowth3Y": "REAL",
    "netDebtEbitda": "REAL",
    "sharesYoY": "REAL",
    "fScore": "REAL",
    "rsi": "REAL",
    "ch6m": "REAL",
    "high52ch": "REAL",
    "zScore": "REAL",
    "interestCoverage": "REAL",
    "priceDate": "TEXT",
    "isin": "TEXT",
    "isPrimaryListing": "TEXT",
}


def _mini_stocks(path, captured_at="2026-07-02T11:00:00+00:00"):
    """A stocks.db with one row that passes every screen gate, built through
    the screener's own ensure_schema (no hand-rolled DDL)."""
    conn = stocks_db.connect(str(path))
    stocks_db.ensure_schema(conn, _SCREEN_COLS)
    conn.execute(
        "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 1, 't')",
        (captured_at,),
    )
    conn.execute(
        'INSERT INTO metrics (snapshot_id, symbol, sector, "marketCap", "dollarVolume",'
        ' roic, roic5y, "fcfYield", "revenueGrowth3Y", "netDebtEbitda", "sharesYoY",'
        ' "fScore", rsi, ch6m, high52ch, "zScore", "interestCoverage", "priceDate",'
        " isin, \"isPrimaryListing\") VALUES (1, 'GOOD', 'Technology', 2e10, 5e7,"
        " 25.0, 20.0, 6.0, 9.0, 0.5, -1.0, 7.0, 38.0, -20.0, -20.0, 6.0, 12.0,"
        " '2026-07-01', 'US1111111111', '1')"
    )
    conn.commit()
    conn.close()


def test_read_candidate_rows_from_attached_stocks_db(tmp_path):
    conn = _conn(tmp_path)
    # The scorer's own run header shares the `snapshots` table name; the
    # screen date must come from src.snapshots, never main's.
    db.write_snapshot(conn, "2026-07-30T04:12:00+00:00")
    _mini_stocks(tmp_path / "stocks.db")
    fetch.attach_ro(conn, str(tmp_path / "stocks.db"))
    try:
        screen_date, version, rows = fetch.read_candidate_rows(conn)
    finally:
        fetch.detach(conn)
    assert screen_date == "2026-07-02"  # 11:00Z is 04:00 Phoenix, same day
    assert version == candidates.SCREEN_VERSION
    assert [r["symbol"] for r in rows] == ["GOOD"]
    assert rows[0]["via_rsi"] == 1 and rows[0]["via_drawdown"] == 0


def test_read_candidate_rows_screen_date_respects_phoenix_rollover(tmp_path):
    conn = _conn(tmp_path)
    _mini_stocks(tmp_path / "stocks.db", captured_at="2026-07-03T04:12:00+00:00")
    fetch.attach_ro(conn, str(tmp_path / "stocks.db"))
    try:
        screen_date, _, _ = fetch.read_candidate_rows(conn)
    finally:
        fetch.detach(conn)
    assert screen_date == "2026-07-02"  # 04:12Z is 21:12 the PREVIOUS Phoenix day


# ------------------------------------------------------------ run wiring ----


def test_run_records_and_registers_candidates(tmp_path):
    """End to end through run(): the nightly scorer records today's list and
    creates entry-episode outcome rows, alongside its existing steps."""
    from sources.combiners.scorer import run as run_mod

    price_cols = {"priceDate": "TEXT", "close": "REAL", "price": "REAL"}
    conn = stocks_db.connect(str(tmp_path / "etfs.db"))
    stocks_db.ensure_schema(conn, price_cols)
    for i, d in enumerate(["2026-07-01", "2026-07-02"]):
        captured = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()
        conn.execute(
            "INSERT INTO snapshots (captured_at, universe_count, source) VALUES (?, 1, 's')",
            (f"{captured}T11:00:00+00:00",),
        )
        sid = conn.execute("SELECT MAX(id) FROM snapshots").fetchone()[0]
        conn.execute(
            'INSERT INTO metrics (snapshot_id, symbol, "priceDate", "close", "price")'
            " VALUES (?, 'SPY', ?, ?, ?)",
            (sid, d, 499.0 + i, 500.0 + i),
        )
    conn.commit()
    conn.close()
    _mini_stocks(tmp_path / "stocks.db")  # GOOD passes; snapshot dated 2026-07-02

    out = str(tmp_path / "scorer.db")
    run_mod.run(out, str(tmp_path), now_iso="2026-07-03T04:12:00+00:00")
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT symbol, screen_date FROM candidate_appearances").fetchall() == [
        ("GOOD", "2026-07-02")
    ]
    # GOOD has no post-screen-date ledger coverage yet -> outcomes defer;
    # the appearance row is the durable fact this run must leave behind.
    assert conn.execute("SELECT COUNT(*) FROM candidate_outcomes").fetchone()[0] == 0


# ------------------------------------------------------ quality trend ----
# Every gate value is ledgered per sighting, not just the timing fields, so
# a name whose fcf yield rises BECAUSE roic/fScore are decaying (a falling
# knife) is distinguishable from oversold quality — the case the screen's
# LEVEL gates cannot see.

_QUALITY_COLS = {"roic", "roic5y", "rev_growth_3y", "net_debt_ebitda", "shares_yoy"}


def test_appearances_ledger_every_quality_gate(tmp_path):
    conn = _conn(tmp_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_appearances)")}
    assert cols >= _QUALITY_COLS


def test_ensure_schema_migrates_a_pre_quality_ledger(tmp_path):
    """A live scorer.db predates these columns; ensure_schema must ADD them
    rather than leave the nightly INSERT failing on an unknown column."""
    conn = db.connect(str(tmp_path / "old.db"))
    conn.execute(
        "CREATE TABLE candidate_appearances (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " symbol TEXT NOT NULL, screen_date TEXT NOT NULL, screen_version TEXT NOT NULL,"
        " fcf_yield REAL, rsi REAL, high52ch REAL, fscore REAL,"
        " via_rsi INTEGER NOT NULL DEFAULT 0, via_drawdown INTEGER NOT NULL DEFAULT 0,"
        " recorded_at TEXT NOT NULL, UNIQUE (symbol, screen_date))"
    )
    conn.commit()
    db.ensure_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_appearances)")}
    assert cols >= _QUALITY_COLS
    assert _appear(conn, "AAA", "2026-07-01", roic=30.0) == 1


def test_appearance_stores_quality_gates(tmp_path):
    conn = _conn(tmp_path)
    _appear(
        conn,
        "AAA",
        "2026-07-01",
        roic=30.0,
        roic5y=22.0,
        rev_growth_3y=8.0,
        net_debt_ebitda=None,
        shares_yoy=-1.5,
    )
    row = conn.execute(
        "SELECT roic, roic5y, rev_growth_3y, net_debt_ebitda, shares_yoy FROM candidate_appearances"
    ).fetchone()
    assert row == (30.0, 22.0, 8.0, None, -1.5)


def test_read_candidate_rows_carries_quality_gates(tmp_path):
    conn = _conn(tmp_path)
    _mini_stocks(tmp_path / "stocks.db")
    fetch.attach_ro(conn, str(tmp_path / "stocks.db"))
    try:
        _, _, rows = fetch.read_candidate_rows(conn)
    finally:
        fetch.detach(conn)
    r = rows[0]
    assert (r["roic"], r["roic5y"], r["rev_growth_3y"]) == (25.0, 20.0, 9.0)
    assert (r["net_debt_ebitda"], r["shares_yoy"]) == (0.5, -1.0)


def _trend(conn, symbol):
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM v_candidate_quality_trend WHERE symbol = ?", (symbol,)
    ).fetchone()
    return dict(row) if row else None


def test_quality_trend_compares_episode_entry_to_latest_sighting(tmp_path):
    conn = _conn(tmp_path)
    _appear(conn, "AAA", "2026-07-01", fscore=7.0, roic=25.0, fcf_yield=6.0)
    _appear(conn, "AAA", "2026-07-03", fscore=6.0, roic=22.0, fcf_yield=7.0)
    _appear(conn, "AAA", "2026-07-08", fscore=6.0, roic=20.0, fcf_yield=8.0)
    t = _trend(conn, "AAA")
    assert (t["entry_date"], t["latest_date"]) == ("2026-07-01", "2026-07-08")
    assert (t["days_on_list"], t["n_sightings"]) == (7, 3)
    assert (t["fscore_entry"], t["fscore_now"]) == (7.0, 6.0)
    assert (t["roic_entry"], t["roic_now"]) == (25.0, 20.0)
    assert (t["fcf_yield_entry"], t["fcf_yield_now"]) == (6.0, 8.0)


def test_quality_trend_is_the_current_episode_only(tmp_path):
    """A sighting more than the entry gap before the next one belongs to an
    older episode — the same split register_candidates uses — so its values
    never pose as this episode's entry."""
    conn = _conn(tmp_path)
    _appear(conn, "AAA", "2026-06-01", fscore=9.0)
    _appear(conn, "AAA", "2026-07-01", fscore=7.0)
    _appear(conn, "AAA", "2026-07-02", fscore=6.0)
    t = _trend(conn, "AAA")
    assert (t["entry_date"], t["n_sightings"], t["fscore_entry"]) == ("2026-07-01", 2, 7.0)


def test_quality_trend_single_sighting_has_zero_days(tmp_path):
    conn = _conn(tmp_path)
    _appear(conn, "AAA", "2026-07-01", fscore=7.0)
    t = _trend(conn, "AAA")
    assert (t["days_on_list"], t["n_sightings"], t["fscore_now"]) == (0, 1, 7.0)
