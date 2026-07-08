from sources.combiners.scorer import db, scorecard

NOW = "2026-07-20T21:10:00+00:00"


def _fresh(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _owner(conn, n_ticker_rows):
    conn.execute(
        "INSERT INTO registered_snapshots (composite_snapshot_id, composite_date,"
        " entry_date, registered_at, ticker_rows, signal_rows, skipped)"
        " VALUES (1, '2026-07-03', '2026-07-06', ?, ?, 0, 0)",
        (NOW, n_ticker_rows),
    )


def _flagged_ticker(conn, symbol, horizon=5, fwd=0.04, bench=0.01):
    """One matured, flagged (bull) ticker outcome owned by snapshot 1."""
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
        " entry_close, bench_entry_close, exit_date, exit_close, fwd_return,"
        " bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-03', ?, 5, 4, 4, 0, ?, '2026-07-06',"
        " 100.0, 500.0, '2026-07-13', 104.0, ?, ?, ?)",
        (symbol, horizon, fwd, bench, NOW),
    )


def _acted_buy(conn, symbol, ref, fill_price=101.0):
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, composite_snapshot_id,"
        " composite_date, opinion_score_sum, opinion_total, fill_date,"
        " fill_price, order_ref, recorded_at)"
        " VALUES (?, 'acted', 'buy', 1, '2026-07-03', 5, 4, '2026-07-06',"
        " ?, ?, ?)",
        (symbol, fill_price, ref, NOW),
    )


def test_empty_db_renders_all_sections_without_crash(tmp_path):
    conn = _fresh(tmp_path)
    report = scorecard.build_report(conn, NOW)
    assert "Trader Decision-Quality Scorecard" in report
    assert "Filter edge" in report
    assert "Execution cost" in report
    assert "Alignment" in report
    assert "Freelance" in report
    # nothing matured -> explicit, not silently missing
    assert "no matured" in report.lower()


def test_small_n_is_suppressed_not_averaged(tmp_path):
    conn = _fresh(tmp_path)
    _owner(conn, 1)
    _flagged_ticker(conn, "XLE", horizon=5)
    _acted_buy(conn, "XLE", "o1")
    conn.commit()
    report = scorecard.build_report(conn, NOW)
    # exactly one acted decision at horizon 5 -> below the n<5 floor
    assert "insufficient data (n=1)" in report
    # the bare average (0.03 dir_excess) must NOT be surfaced as a verdict
    assert "0.03" not in report


def test_sufficient_n_shows_average(tmp_path):
    conn = _fresh(tmp_path)
    _owner(conn, scorecard.N_MIN)
    for i in range(scorecard.N_MIN):
        _flagged_ticker(conn, f"T{i}", horizon=5)
        _acted_buy(conn, f"T{i}", f"o{i}")
    conn.commit()
    report = scorecard.build_report(conn, NOW)
    # n=5 acted at horizon 5 clears the floor: an average is shown, unsuppressed
    assert "insufficient data (n=5)" not in report
    # avg_dir_excess for a bull flag = 0.04 - 0.01 = 0.03, now surfaced
    assert "0.03" in report


def test_per_horizon_never_pools(tmp_path):
    conn = _fresh(tmp_path)
    _owner(conn, 1)
    # one decision matured against TWO horizons -> two v_decision_outcomes rows
    _flagged_ticker(conn, "XLE", horizon=5)
    _flagged_ticker(conn, "XLE", horizon=10)
    _acted_buy(conn, "XLE", "o1")
    conn.commit()
    # v_decision_outcomes has 2 rows for 1 decision; the report must count
    # per horizon (n=1 each), never a pooled n=2
    rows = scorecard.execution_cost(conn)
    counts = {r["horizon"]: r["n"] for r in rows}
    assert counts == {5: 1, 10: 1}


def test_freelance_excludes_automatic_fills(tmp_path):
    conn = _fresh(tmp_path)
    # deliberate freelance (placed_agent NULL) + an automatic drip
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " order_ref, placed_agent, recorded_at)"
        " VALUES ('NVDA', 'acted', 'buy', '2026-07-06', 800.0, 'f1', NULL, ?)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " order_ref, placed_agent, recorded_at)"
        " VALUES ('KO', 'acted', 'buy', '2026-07-06', 60.0, 'f2', 'drip', ?)",
        (NOW,),
    )
    conn.commit()
    rows = scorecard.deliberate_freelance(conn)
    symbols = {r["symbol"] for r in rows}
    assert symbols == {"NVDA"}  # drip excluded by design
    report = scorecard.build_report(conn, NOW)
    assert "NVDA" in report and "KO" not in report
