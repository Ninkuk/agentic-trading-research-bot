from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _ledger(conn, symbol, dates, start=100.0, step=1.0):
    """Insert a run of closes: dates[i] -> start + i*step."""
    db.insert_prices(conn, [(symbol, d, start + i * step) for i, d in enumerate(dates)])


# 8 trading days around the 2026-07-04 holiday weekend (Jul 3 closed).
DAYS = [
    "2026-06-25",
    "2026-06-26",
    "2026-06-29",
    "2026-06-30",
    "2026-07-01",
    "2026-07-02",
    "2026-07-06",
    "2026-07-07",
]


def test_insert_prices_dedupes(tmp_path):
    conn = _conn(tmp_path)
    assert db.insert_prices(conn, [("A", "2026-07-02", 1.0)] * 2) == 1


def test_entry_for_respects_guard(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    # first close strictly after the opinion date; holiday weekend spanned
    assert db.entry_for(conn, "AAPL", "2026-07-02", 7) == ("2026-07-06", 106.0)
    # nothing after the last ledger date
    assert db.entry_for(conn, "AAPL", "2026-07-07", 7) is None
    # forward guard: next print lands more than 7 days after the opinion
    assert db.entry_for(conn, "AAPL", "2026-06-10", 7) is None
    assert db.entry_for(conn, "GHOST", "2026-07-02", 7) is None


def test_register_and_mature_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)  # 100..107
    _ledger(conn, "SPY", DAYS, start=500.0)  # 500..507
    reg, skipped = db.register_snapshot(
        conn,
        csid=1,
        composite_date="2026-07-01",
        ticker_rows=[
            dict(symbol="AAPL", score_sum=3, total=3, bullish=3, bearish=0, in_portfolio=0)
        ],
        signal_rows=[dict(signal_id="si_days_to_cover", entity="AAPL", score=2, via_crosswalk=0)],
        regime="risk_on",
        horizons=(2,),
        benchmark="SPY",
        max_age_days=7,
        now_iso=NOW,
    )
    assert (reg, skipped) == (3, 0)  # 1 ticker + 1 signal + 1 regime
    # entry is the first close AFTER 07-01 -> 07-02 (105 / 505), no
    # look-ahead; +2 trading days = 07-07
    assert db.mature(conn, NOW) == 3
    t = conn.execute(
        "SELECT entry_date, entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return FROM ticker_outcomes"
    ).fetchone()
    assert t[0] == "2026-07-02" and t[1] == 105.0
    assert t[2] == "2026-07-07" and t[3] == 107.0
    assert abs(t[4] - (107.0 / 105.0 - 1)) < 1e-9
    assert abs(t[5] - (507.0 / 505.0 - 1)) < 1e-9
    r = conn.execute("SELECT regime, bench_fwd_return FROM regime_outcomes").fetchone()
    assert r[0] == "risk_on" and abs(r[1] - (507.0 / 505.0 - 1)) < 1e-9


def test_pending_without_data_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(
        conn,
        1,
        "2026-07-06",
        [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)],
        [],
        "mixed",
        (5,),
        "SPY",
        7,
        NOW,
    )
    assert db.mature(conn, NOW) == 0  # entry 07-07 is the last ledger date
    assert conn.execute("SELECT exit_close FROM ticker_outcomes").fetchone()[0] is None


def test_register_skips_stale_and_missing_symbols(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    reg, skipped = db.register_snapshot(
        conn,
        1,
        "2026-07-06",
        [dict(symbol="GHOST", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)],
        [],
        "risk_on",
        (5,),
        "SPY",
        7,
        NOW,
    )
    assert skipped == 1  # GHOST has no prices
    assert reg == 1  # regime row still registered
    assert 1 in db.registered_ids(conn)


def test_register_is_atomic_and_once(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on", (5,), "SPY", 7, NOW)
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on", (5,), "SPY", 7, NOW)


def test_bench_missing_registers_null_bench(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    reg, skipped = db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)],
        [],
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
    )
    assert conn.execute("SELECT bench_entry_close FROM ticker_outcomes").fetchone()[0] is None
    # regime needs the benchmark; skipped, but ticker row registered
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes").fetchone()[0] == 0
    db.mature(conn, NOW)  # matures with NULL bench
    row = conn.execute("SELECT fwd_return, bench_fwd_return FROM ticker_outcomes").fetchone()
    assert row[0] is not None and row[1] is None


def test_duplicate_entry_window_registers_marker_only(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    rows = [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)]
    reg1, _ = db.register_snapshot(conn, 1, "2026-07-04", rows, [], "risk_on", (5,), "SPY", 7, NOW)
    # Sunday-run snapshot shares the same Monday entry close -> marker-only
    reg2, _ = db.register_snapshot(conn, 2, "2026-07-05", rows, [], "risk_on", (5,), "SPY", 7, NOW)
    assert reg1 == 2 and reg2 == 0  # ticker + regime, then marker-only
    assert {1, 2} <= db.registered_ids(conn)
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes").fetchone()[0] == 1


def test_bench_gap_does_not_discard_gradeable_night(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "SPY", DAYS[:6], start=500.0)  # SPY ledger stops at 2026-07-02
    _ledger(conn, "AAPL", DAYS)  # AAPL ledger runs through 2026-07-07
    rows = [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)]

    # etfs-only harvest failure: SPY has no close after 07-02 but AAPL does,
    # so the anchor is AAPL's 07-06 and the night still registers — the
    # ticker row with NULL bench, the regime row skipped (its graded leg IS
    # the benchmark) — rather than being discarded or deferred forever.
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-02", rows, [], "risk_on", (5,), "SPY", 7, NOW
    )
    assert 1 in db.registered_ids(conn)
    assert (reg, skipped) == (1, 1)  # ticker registered; regime skipped
    assert (
        conn.execute(
            "SELECT entry_date FROM registered_snapshots WHERE composite_snapshot_id = 1"
        ).fetchone()[0]
        == "2026-07-06"
    )
    ticker_row = conn.execute(
        "SELECT entry_date, bench_entry_close FROM ticker_outcomes"
    ).fetchone()
    assert ticker_row == ("2026-07-06", None)
    assert conn.execute("SELECT COUNT(*) FROM regime_outcomes").fetchone()[0] == 0


def test_same_night_registration_defers(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS[:6])
    _ledger(conn, "SPY", DAYS[:6], start=500.0)
    rows = [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)]
    # opinion formed on the ledger's newest date: its entry close doesn't
    # exist yet, so registration must defer -- no marker, retried later.
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-02", rows, [], "risk_on", (5,), "SPY", 7, NOW
    )
    assert (reg, skipped) == (0, 0)
    assert db.registered_ids(conn) == set()
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes").fetchone()[0] == 0
    # next night the 07-06 closes land -> the same snapshot registers
    db.insert_prices(conn, [("AAPL", "2026-07-06", 106.0), ("SPY", "2026-07-06", 506.0)])
    reg, skipped = db.register_snapshot(
        conn, 1, "2026-07-02", rows, [], "risk_on", (5,), "SPY", 7, NOW
    )
    assert (reg, skipped) == (2, 0)  # ticker + regime
    assert 1 in db.registered_ids(conn)


def test_gap_beyond_bound_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    db.insert_prices(conn, [("AAPL", "2026-07-01", 100.0), ("AAPL", "2026-07-02", 100.0)])
    db.insert_prices(conn, [("SPY", "2026-07-01", 500.0), ("SPY", "2026-07-02", 500.0)])
    # ledger gap: next prices only in November (sources were down > 30d);
    # 150 keeps the day-over-day ratio inside the basis-break bounds so the
    # calendar bound is what's under test here
    db.insert_prices(conn, [("AAPL", f"2026-11-{d:02d}", 150.0) for d in range(2, 9)])
    db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0)],
        [],
        "risk_on",
        (5,),
        "SPY",
        7,
        NOW,
    )
    # the 5th post-entry date exists (Nov 6) but violates the calendar
    # bound -> must stay pending rather than grade the wrong window
    assert db.mature(conn, NOW) == 0
    assert (
        conn.execute("SELECT COUNT(*) FROM ticker_outcomes WHERE matured_at IS NULL").fetchone()[0]
        == 1
    )


def test_prune_only_removes_run_headers(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", ["2026-01-02"])  # ancient ledger row
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(conn, 1, "2026-07-06", [], [], "risk_on", (5,), "SPY", 7, NOW)
    old_header = db.write_snapshot(conn, "2025-01-01T00:00:00+00:00")
    db.prune(conn, keep_days=90, now_iso=NOW)
    assert (
        conn.execute("SELECT COUNT(*) FROM prices WHERE symbol='AAPL'").fetchone()[0] == 1
    )  # the ledger is permanent: ancient prices survive
    assert (
        conn.execute("SELECT COUNT(*) FROM regime_outcomes").fetchone()[0] == 1
    )  # outcomes untouched
    assert (
        conn.execute("SELECT COUNT(*) FROM snapshots WHERE id=?", (old_header,)).fetchone()[0] == 0
    )


def test_registered_counts_actual_inserts(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _ledger(conn, "SPY", DAYS, start=500.0)
    # Two identical ticker_rows for "AAPL"; the duplicate will be ignored
    ticker_rows = [
        dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0),
        dict(symbol="AAPL", score_sum=2, total=2, bullish=2, bearish=0, in_portfolio=0),
    ]
    reg, skipped = db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        ticker_rows,
        [],
        "risk_on",
        horizons=(5,),
        benchmark="SPY",
        max_age_days=7,
        now_iso=NOW,
    )
    # Expected: 1 ticker (duplicate ignored) + 1 regime = 2
    assert reg == 2
    assert skipped == 0
    # Verify only one ticker_outcomes row was actually inserted
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes").fetchone()[0] == 1


def _register_one(conn, symbol, horizons):
    """Register a single bullish DAYS[0] opinion (enters at DAYS[1]'s close)."""
    return db.register_snapshot(
        conn,
        1,
        DAYS[0],
        [dict(symbol=symbol, score_sum=4, total=3, bullish=3, bearish=0, in_portfolio=0)],
        [],
        "risk_on",
        horizons,
        "SPY",
        7,
        NOW,
    )


def test_split_in_window_stays_pending(tmp_path):
    conn = _conn(tmp_path)
    # 2:1 split between DAYS[2] and DAYS[3]: basis halves, price is flat.
    closes = [100.0, 101.0, 99.5, 50.2, 50.0, 50.5, 49.8, 50.1]
    db.insert_prices(conn, list(zip(["ACME"] * 8, DAYS, closes, strict=True)))
    _ledger(conn, "SPY", DAYS, start=500.0)
    _register_one(conn, "ACME", (5,))
    db.mature(conn, NOW)  # regime row may mature; ACME must not
    t = conn.execute("SELECT exit_date, fwd_return, matured_at FROM ticker_outcomes").fetchone()
    assert t == (None, None, None)


def test_gradual_crash_still_matures(tmp_path):
    conn = _conn(tmp_path)
    # -47% over the window but every day-over-day ratio ~0.88 (no break).
    closes = [100.0, 88.0, 77.0, 68.0, 60.0, 53.0, 47.0, 41.0]
    db.insert_prices(conn, list(zip(["CRSH"] * 8, DAYS, closes, strict=True)))
    _ledger(conn, "SPY", DAYS, start=500.0)
    _register_one(conn, "CRSH", (5,))
    db.mature(conn, NOW)
    t = conn.execute("SELECT exit_date, fwd_return FROM ticker_outcomes").fetchone()
    assert t[0] == DAYS[6]  # entry DAYS[1] + 5 trading days
    assert abs(t[1] - (47.0 / 88.0 - 1)) < 1e-9


def test_split_after_exit_does_not_block(tmp_path):
    conn = _conn(tmp_path)
    # Clean through DAYS[5]; split lands between DAYS[5] and DAYS[6].
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 52.0, 52.5]
    db.insert_prices(conn, list(zip(["ACME"] * 8, DAYS, closes, strict=True)))
    _ledger(conn, "SPY", DAYS, start=500.0)
    _register_one(conn, "ACME", (4, 5))
    db.mature(conn, NOW)
    rows = dict(
        conn.execute("SELECT horizon, matured_at IS NOT NULL FROM ticker_outcomes").fetchall()
    )
    assert rows[4] == 1  # entry DAYS[1] + 4 days ends at DAYS[5], before the break
    assert rows[5] == 0  # window spans the break -> quarantined


def test_benchmark_break_blocks_symbol_rows(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    # SPY itself breaks basis inside the window.
    closes = [500.0, 505.0, 510.0, 250.0, 252.0, 254.0, 256.0, 258.0]
    db.insert_prices(conn, list(zip(["SPY"] * 8, DAYS, closes, strict=True)))
    _register_one(conn, "AAPL", (5,))
    assert db.mature(conn, NOW) == 0
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM ticker_outcomes WHERE matured_at IS NOT NULL"
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM regime_outcomes WHERE matured_at IS NOT NULL"
        ).fetchone()[0]
        == 0
    )


XW_BENCH = {"XOM": "XLE", "XLE": None}


def test_signal_benchmark_resolution(tmp_path):
    conn = _conn(tmp_path)
    for sym, start in (
        ("XOM", 100.0),
        ("XLE", 50.0),
        ("NEWX", 20.0),
        ("AAPL", 200.0),
        ("SPY", 500.0),
    ):
        _ledger(conn, sym, DAYS, start=start)
    signal_rows = [
        # crosswalked, mapped -> matched benchmark XLE
        dict(signal_id="cftc_energy", entity="XOM", score=2, via_crosswalk=1),
        # crosswalked class proxy -> explicitly unbenchmarked
        dict(signal_id="cftc_energy", entity="XLE", score=2, via_crosswalk=1),
        # crosswalked but unknown to the map -> fail safe to unbenchmarked
        dict(signal_id="cftc_energy", entity="NEWX", score=2, via_crosswalk=1),
        # direct ticker evidence -> global benchmark
        dict(signal_id="stocks_rsi", entity="AAPL", score=1, via_crosswalk=0),
    ]
    db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [],
        signal_rows,
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
        crosswalk_benchmark=XW_BENCH,
    )
    bench = dict(conn.execute("SELECT entity, benchmark FROM signal_outcomes"))
    assert bench == {"XOM": "XLE", "XLE": None, "NEWX": None, "AAPL": "SPY"}
    # bench_entry_close is the row's OWN benchmark's close at the entry
    # date (2026-07-02 = DAYS[5], close = start + 5)
    entry = dict(conn.execute("SELECT entity, bench_entry_close FROM signal_outcomes"))
    assert entry["XOM"] == 55.0  # XLE, not SPY
    assert entry["XLE"] is None
    assert entry["NEWX"] is None
    assert entry["AAPL"] == 505.0  # SPY
