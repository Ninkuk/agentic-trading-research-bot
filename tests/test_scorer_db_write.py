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


def _register_signal(conn, entity, xw_bench, horizons=(2,)):
    """Register one bullish crosswalked signal opinion on DAYS[4] (2026-07-01)."""
    return db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [],
        [dict(signal_id="cftc_energy", entity=entity, score=2, via_crosswalk=1)],
        "risk_on",
        horizons,
        "SPY",
        7,
        NOW,
        crosswalk_benchmark=xw_bench,
    )


def test_crosswalk_row_matures_vs_own_benchmark(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XOM", DAYS, start=100.0, step=1.0)  # entry 105 -> exit 107
    _ledger(conn, "XLE", DAYS, start=50.0, step=5.0)  # entry 75 -> exit 85
    _ledger(conn, "SPY", DAYS, start=500.0, step=0.0)  # flat: SPY excess would be ~0
    _register_signal(conn, "XOM", {"XOM": "XLE"})
    db.mature(conn, NOW)
    row = conn.execute(
        "SELECT fwd_return, bench_fwd_return, matured_at FROM signal_outcomes"
    ).fetchone()
    assert row[2] is not None
    assert abs(row[0] - (107.0 / 105.0 - 1)) < 1e-9
    # graded against XLE's move, NOT SPY's flat 0.0
    assert abs(row[1] - (85.0 / 75.0 - 1)) < 1e-9


def test_unbenchmarked_row_matures_with_null_bench(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XLE", DAYS, start=50.0)
    _ledger(conn, "SPY", DAYS, start=500.0)
    _register_signal(conn, "XLE", {"XLE": None})
    db.mature(conn, NOW)
    row = conn.execute(
        "SELECT fwd_return, bench_fwd_return, matured_at FROM signal_outcomes"
    ).fetchone()
    assert row[2] is not None and row[0] is not None
    assert row[1] is None


def test_matched_benchmark_split_blocks_row(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "XOM", DAYS, start=100.0)
    # XLE 2:1 split between DAYS[2] and DAYS[3] -- inside the (2,) window
    closes = [100.0, 101.0, 99.5, 50.2, 50.0, 50.5, 49.8, 50.1]
    db.insert_prices(conn, list(zip(["XLE"] * 8, DAYS, closes, strict=True)))
    _ledger(conn, "SPY", DAYS, start=500.0)
    db.register_snapshot(
        conn,
        1,
        DAYS[0],
        [],
        [
            dict(signal_id="cftc_energy", entity="XOM", score=2, via_crosswalk=1),
            dict(signal_id="stocks_rsi", entity="XOM", score=1, via_crosswalk=0),
        ],
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
        crosswalk_benchmark={"XOM": "XLE"},
    )
    db.mature(conn, NOW)
    rows = dict(conn.execute("SELECT signal_id, matured_at IS NOT NULL FROM signal_outcomes"))
    # the XLE-benchmarked row is held pending by the benchmark-leg break;
    # the SPY-benchmarked row for the same entity matures fine
    assert rows == {"cftc_energy": 0, "stocks_rsi": 1}


# --- rebuild_prices: one-shot repair of the off-by-one-session ledger --------


def _outcome(conn, table, csid=1, matured=None):
    if table == "regime_outcomes":
        conn.execute(
            "INSERT INTO regime_outcomes (composite_snapshot_id, composite_date, regime,"
            " horizon, entry_date, bench_entry_close, matured_at) VALUES (?,?,?,?,?,?,?)",
            (csid, "2026-07-06", "mixed", 5, "2026-07-07", 100.0, matured),
        )
    elif table == "ticker_outcomes":
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " matured_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (csid, "2026-07-06", "AAPL", 4, 3, 3, 0, 5, "2026-07-07", 100.0, matured),
        )
    else:
        conn.execute(
            "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date, signal_id,"
            " entity, score, horizon, entry_date, entry_close, matured_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (csid, "2026-07-06", "stocks_rsi", "AAPL", 2, 5, "2026-07-07", 100.0, matured),
        )


def _registration(conn, csid=1, ticker_rows=1):
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date, entry_date,"
        " registered_at, ticker_rows, signal_rows, skipped) VALUES (?,?,?,?,?,?,0)",
        (csid, "2026-07-06", f"2026-07-0{6 + csid}", NOW, ticker_rows, 1),
    )


def test_rebuild_prices_clears_ledger_unmatured_outcomes_and_registrations(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    for t in ("signal_outcomes", "ticker_outcomes", "regime_outcomes"):
        _outcome(conn, t)
    _registration(conn)
    conn.commit()

    prices, outcomes, regs = db.rebuild_prices(conn)

    assert (prices, outcomes, regs) == (len(DAYS), 3, 1)
    for t in (
        "prices",
        "signal_outcomes",
        "ticker_outcomes",
        "regime_outcomes",
        "registered_snapshots",
    ):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0, t


def test_rebuild_prices_refuses_when_any_outcome_matured(tmp_path):
    """A matured row's forward return came from mislabeled closes; deleting the
    ledger under it would strand an unrepairable result."""
    conn = _conn(tmp_path)
    _ledger(conn, "AAPL", DAYS)
    _outcome(conn, "signal_outcomes", matured=NOW)
    _outcome(conn, "ticker_outcomes")  # unmatured; must survive the refusal
    conn.commit()

    try:
        db.rebuild_prices(conn)
    except RuntimeError as e:
        assert "signal_outcomes=1" in str(e)
        assert "ticker_outcomes" not in str(e)  # only non-zero tables named
    else:
        raise AssertionError("expected RuntimeError")

    assert conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == len(DAYS)
    assert conn.execute("SELECT COUNT(*) FROM signal_outcomes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM ticker_outcomes").fetchone()[0] == 1


def test_rebuild_prices_is_idempotent_on_an_empty_db(tmp_path):
    conn = _conn(tmp_path)
    assert db.rebuild_prices(conn) == (0, 0, 0)
    assert db.rebuild_prices(conn) == (0, 0, 0)


def test_matured_counts_reports_per_table(tmp_path):
    conn = _conn(tmp_path)
    _outcome(conn, "regime_outcomes", matured=NOW)
    conn.commit()
    assert db.matured_counts(conn) == {
        "signal_outcomes": 0,
        "ticker_outcomes": 0,
        "regime_outcomes": 1,
        "verdict_outcomes": 0,
    }


# --- research verdicts: registration + maturation ----------------------------


def _verdict(conn, symbol="AAA", vdate="2026-07-01", verdict="pass"):
    cur = conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date,"
        " recorded_at) VALUES (?, ?, ?, '2026-07-02T04:12:00+00:00')",
        (symbol, verdict, vdate),
    )
    conn.commit()
    return cur.lastrowid


def test_verdict_register_and_mature_roundtrip(tmp_path):
    conn = _conn(tmp_path)
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]
    _ledger(conn, "AAA", dates, start=100.0, step=1.0)  # 100,101,102,103
    _ledger(conn, "SPY", dates, start=500.0, step=1.0)  # 500,501,502,503
    _verdict(conn, "AAA", "2026-07-01")
    n = db.register_verdicts(conn, (2,), "SPY", 7)
    assert n == 1
    row = conn.execute(
        "SELECT entry_date, entry_close, bench_entry_close FROM verdict_outcomes"
    ).fetchone()
    # STRICTLY AFTER the verdict date — never the same-day close.
    assert row == ("2026-07-02", 101.0, 501.0)
    db.mature(conn, "2026-07-07T04:12:00+00:00", "SPY")
    row = conn.execute(
        "SELECT exit_date, exit_close, fwd_return, bench_fwd_return"
        " FROM verdict_outcomes WHERE matured_at IS NOT NULL"
    ).fetchone()
    assert row is not None
    assert row[0] == "2026-07-06" and row[1] == 103.0
    assert abs(row[2] - (103.0 / 101.0 - 1)) < 1e-12
    assert abs(row[3] - (503.0 / 501.0 - 1)) < 1e-12


def test_verdict_register_is_idempotent(tmp_path):
    conn = _conn(tmp_path)
    _ledger(conn, "AAA", ["2026-07-02"], start=100.0)
    _ledger(conn, "SPY", ["2026-07-02"], start=500.0)
    _verdict(conn, "AAA", "2026-07-01")
    assert db.register_verdicts(conn, (2, 5), "SPY", 7) == 2
    assert db.register_verdicts(conn, (2, 5), "SPY", 7) == 0


def test_uncovered_verdict_defers_then_heals(tmp_path):
    conn = _conn(tmp_path)
    _verdict(conn, "ZZZ", "2026-07-01")
    assert db.register_verdicts(conn, (2,), "SPY", 7) == 0  # no ledger rows
    _ledger(conn, "ZZZ", ["2026-07-03"], start=50.0)  # coverage arrives in-window
    assert db.register_verdicts(conn, (2,), "SPY", 7) == 1
    # Benchmark close missing on entry date -> NULL bench leg, still registers.
    row = conn.execute("SELECT entry_date, bench_entry_close FROM verdict_outcomes").fetchone()
    assert row == ("2026-07-03", None)


def test_late_coverage_beyond_guard_never_registers(tmp_path):
    conn = _conn(tmp_path)
    _verdict(conn, "CSU", "2026-07-01")
    _ledger(conn, "CSU", ["2026-07-20"], start=100.0)  # first print 19 days later
    assert db.register_verdicts(conn, (2,), "SPY", 7) == 0


def test_rebuild_prices_sweeps_unmatured_verdict_outcomes(tmp_path):
    """verdict_outcomes is one of the _OUTCOME_TABLES rebuild_prices clears, but
    research_verdicts (the skill's own ledger, not a derived outcome) is untouched
    — and register_verdicts can re-register from scratch once the ledger refills."""
    conn = _conn(tmp_path)
    dates = ["2026-07-01", "2026-07-02"]
    _ledger(conn, "AAA", dates, start=100.0, step=1.0)
    _ledger(conn, "SPY", dates, start=500.0, step=1.0)
    vid = _verdict(conn, "AAA", "2026-07-01")

    assert db.register_verdicts(conn, (2,), "SPY", 7) == 1
    assert conn.execute("SELECT COUNT(*) FROM verdict_outcomes").fetchone()[0] == 1

    prices, outcomes, regs = db.rebuild_prices(conn)
    assert (prices, outcomes, regs) == (4, 1, 0)  # 2 AAA + 2 SPY closes; no snapshot registrations

    assert conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM verdict_outcomes").fetchone()[0] == 0
    row = conn.execute("SELECT id FROM research_verdicts").fetchone()
    assert row == (vid,)  # survives: it's the ledger of what the skill decided

    _ledger(conn, "AAA", dates, start=100.0, step=1.0)
    _ledger(conn, "SPY", dates, start=500.0, step=1.0)
    assert db.register_verdicts(conn, (2,), "SPY", 7) == 1
