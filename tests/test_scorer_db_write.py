from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _ledger(conn, symbol, dates, start=100.0, step=1.0):
    """Insert a run of closes: dates[i] -> start + i*step."""
    db.insert_prices(conn, [(symbol, d, start + i * step)
                            for i, d in enumerate(dates)])


# 8 trading days around the 2026-07-04 holiday weekend (Jul 3 closed).
DAYS = ["2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30",
        "2026-07-01", "2026-07-02", "2026-07-06", "2026-07-07"]


def test_insert_prices_dedupes(tmp_path):
    conn = _conn(tmp_path)
    assert db.insert_prices(conn, [("A", "2026-07-02", 1.0)] * 2) == 1


def test_entry_for_respects_guard(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    # weekend composite date -> Friday 07-02 close
    assert db.entry_for(conn, "AAPL", "2026-07-05", 7) == ("2026-07-02", 105.0)
    # stale: newest price 07-07, composite date 30 days later
    assert db.entry_for(conn, "AAPL", "2026-08-15", 7) is None
    assert db.entry_for(conn, "GHOST", "2026-07-05", 7) is None


def test_register_and_mature_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)                       # 100..107
    _ledger(conn, "SPY", DAYS, start=500.0)           # 500..507
    reg, skipped = db.register_snapshot(
        conn, csid=1, composite_date="2026-07-01",
        ticker_rows=[dict(symbol="AAPL", score_sum=3, total=3, bullish=3,
                          bearish=0, in_portfolio=0)],
        signal_rows=[dict(signal_id="si_days_to_cover", entity="AAPL",
                          score=2, via_crosswalk=0)],
        regime="risk_on", horizons=(2,), benchmark="SPY",
        max_age_days=7, now_iso=NOW)
    assert (reg, skipped) == (3, 0)   # 1 ticker + 1 signal + 1 regime
    # entry was 07-01 (close 104 / 504); +2 trading days = 07-06
    assert db.mature(conn, NOW) == 3
    t = conn.execute("SELECT entry_date, entry_close, exit_date, exit_close,"
                     " fwd_return, bench_fwd_return FROM ticker_outcomes"
                     ).fetchone()
    assert t[0] == "2026-07-01" and t[1] == 104.0
    assert t[2] == "2026-07-06" and t[3] == 106.0
    assert abs(t[4] - (106.0 / 104.0 - 1)) < 1e-9
    assert abs(t[5] - (506.0 / 504.0 - 1)) < 1e-9
    r = conn.execute("SELECT regime, bench_fwd_return FROM regime_outcomes"
                     ).fetchone()
    assert r[0] == "risk_on" and abs(r[1] - (506.0 / 504.0 - 1)) < 1e-9


def test_pending_without_data_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06",
                         [dict(symbol="AAPL", score_sum=2, total=2,
                               bullish=2, bearish=0, in_portfolio=0)],
                         [], "mixed", (5,), "SPY", 7, NOW)
    assert db.mature(conn, NOW) == 0   # only 1 day past entry exists
    assert conn.execute("SELECT exit_close FROM ticker_outcomes"
                        ).fetchone()[0] is None


def test_register_skips_stale_and_missing_symbols(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-06",
        [dict(symbol="GHOST", score_sum=2, total=2, bullish=2, bearish=0,
              in_portfolio=0)],
        [], "risk_on", (5,), "SPY", 7, NOW)
    assert skipped == 1                       # GHOST has no prices
    assert reg == 1                           # regime row still registered
    assert 1 in db.registered_ids(conn)


def test_register_is_atomic_and_once(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                         (5,), "SPY", 7, NOW)
    import sqlite3

    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                             (5,), "SPY", 7, NOW)


def test_bench_missing_registers_null_bench(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-01",
        [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0,
              in_portfolio=0)],
        [], "risk_on", (2,), "SPY", 7, NOW)
    assert conn.execute("SELECT bench_entry_close FROM ticker_outcomes"
                        ).fetchone()[0] is None
    # regime needs the benchmark; skipped, but ticker row registered
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes"
                        ).fetchone()[0] == 0
    db.mature(conn, NOW)                      # matures with NULL bench
    row = conn.execute("SELECT fwd_return, bench_fwd_return"
                       " FROM ticker_outcomes").fetchone()
    assert row[0] is not None and row[1] is None


def test_duplicate_entry_window_registers_marker_only(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    rows = [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0,
                 in_portfolio=0)]
    reg1, _ = db.register_snapshot(conn, 1, "2026-07-04", rows, [],
                                   "risk_on", (5,), "SPY", 7, NOW)
    # Sunday-run snapshot grades the same Friday close window
    reg2, _ = db.register_snapshot(conn, 2, "2026-07-05", rows, [],
                                   "risk_on", (5,), "SPY", 7, NOW)
    assert reg1 == 2 and reg2 == 0        # ticker + regime, then marker-only
    assert {1, 2} <= db.registered_ids(conn)
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes"
                        ).fetchone()[0] == 1


def test_gap_beyond_bound_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    db.insert_prices(conn, [("AAPL", "2026-07-01", 100.0),
                            ("SPY", "2026-07-01", 500.0)])
    # ledger gap: next prices only in November (sources were down > 30d)
    db.insert_prices(conn, [("AAPL", f"2026-11-{d:02d}", 200.0)
                            for d in range(2, 9)])
    db.register_snapshot(conn, 1, "2026-07-01",
                         [dict(symbol="AAPL", score_sum=2, total=2,
                               bullish=2, bearish=0, in_portfolio=0)],
                         [], "risk_on", (5,), "SPY", 7, NOW)
    # the 5th post-entry date exists (Nov 6) but violates the calendar
    # bound -> must stay pending rather than grade the wrong window
    assert db.mature(conn, NOW) == 0
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes"
                        " WHERE matured_at IS NULL").fetchone()[0] == 1


def test_prune_never_touches_outcomes(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", ["2026-01-02"])     # ancient ledger row
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on",
                         (5,), "SPY", 7, NOW)
    old_header = db.write_snapshot(conn, "2025-01-01T00:00:00+00:00")
    db.prune(conn, keep_days=90, now_iso=NOW)
    assert conn.execute("SELECT COUNT(*) FROM prices WHERE symbol='AAPL'"
                        ).fetchone()[0] == 0  # ancient price pruned
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes"
                        ).fetchone()[0] == 1  # outcomes untouched
    assert conn.execute("SELECT COUNT(*) FROM snapshots WHERE id=?",
                        (old_header,)).fetchone()[0] == 0


def test_registered_counts_actual_inserts(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    # Two identical ticker_rows for "AAPL"; the duplicate will be ignored
    ticker_rows = [
        dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0,
             in_portfolio=0),
        dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0,
             in_portfolio=0)
    ]
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-01", ticker_rows, [], "risk_on",
        horizons=(5,), benchmark="SPY", max_age_days=7, now_iso=NOW)
    # Expected: 1 ticker (duplicate ignored) + 1 regime = 2
    assert reg == 2
    assert skipped == 0
    # Verify only one ticker_outcomes row was actually inserted
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes"
                        ).fetchone()[0] == 1
