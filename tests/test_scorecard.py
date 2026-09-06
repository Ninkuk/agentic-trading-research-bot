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


def _fill(conn, symbol, fill_date, qty, price, exit_date=None, exit_price=None, side="buy"):
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price, quantity,"
        " exit_fill_date, exit_fill_price, order_ref, recorded_at)"
        " VALUES (?, 'acted', ?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, side, fill_date, price, qty, exit_date, exit_price, f"{symbol}-{fill_date}", NOW),
    )


def _prices(conn, symbol, rows):
    conn.executemany(
        "INSERT INTO prices (symbol, price_date, close) VALUES (?, ?, ?)",
        [(symbol, d, c) for d, c in rows],
    )


def _seed_curve(conn):
    """AAA bought 07-31, BBB added 08-04; SPY 630 → 636.3 → 640 (+1.59%).
    Book legs: 08-04 (24+55)/(22+50) = +9.72%, 08-05 (25+56)/79 = +2.53%
    → 81/72 = +12.50% chained."""
    _fill(conn, "AAA", "2026-07-31", 2.0, 10.0)
    _fill(conn, "BBB", "2026-08-04", 1.0, 50.0)
    _prices(conn, "AAA", [("2026-07-31", 11.0), ("2026-08-04", 12.0), ("2026-08-05", 12.5)])
    _prices(conn, "BBB", [("2026-08-04", 55.0), ("2026-08-05", 56.0)])
    _prices(conn, "SPY", [("2026-07-31", 630.0), ("2026-08-04", 636.3), ("2026-08-05", 640.0)])
    conn.commit()


def test_portfolio_section_chains_the_stock_book(tmp_path):
    conn = _fresh(tmp_path)
    _seed_curve(conn)
    text = scorecard._portfolio_section(conn)
    inception = next(ln for ln in text.splitlines() if ln.strip().startswith("inception"))
    cells = [c.strip() for c in inception.split("|")]
    assert cells[1] == "12.50%" and cells[2] == "1.59%"


def test_portfolio_section_skips_empty_book_legs_on_both_sides(tmp_path):
    conn = _fresh(tmp_path)
    # Sold out 08-04, empty through 08-06, back in 08-07. SPY's +11% on 08-05
    # happened while nothing was held, so neither side may count it.
    _fill(conn, "AAA", "2026-07-31", 2.0, 10.0, "2026-08-04", 11.0)
    _fill(conn, "BBB", "2026-08-07", 1.0, 100.0)
    _prices(conn, "AAA", [("2026-07-31", 11.0), ("2026-08-04", 11.0)])
    _prices(conn, "BBB", [("2026-08-07", 100.0), ("2026-08-10", 100.0)])
    _prices(
        conn,
        "SPY",
        [
            (d, c)
            for d, c in (
                ("2026-07-31", 630.0),
                ("2026-08-04", 630.0),
                ("2026-08-05", 700.0),
                ("2026-08-06", 700.0),
                ("2026-08-07", 700.0),
                ("2026-08-10", 700.0),
            )
        ],
    )
    conn.commit()
    text = scorecard._portfolio_section(conn)
    inception = next(ln for ln in text.splitlines() if ln.strip().startswith("inception"))
    cells = [c.strip() for c in inception.split("|")]
    assert cells[1:4] == ["0.00%", "0.00%", "0.00%"]


def test_portfolio_section_thin_book(tmp_path):
    conn = _fresh(tmp_path)
    text = scorecard._portfolio_section(conn)
    assert "insufficient data" in text


def test_portfolio_section_names_excluded_symbols(tmp_path):
    conn = _fresh(tmp_path)
    _seed_curve(conn)
    _fill(conn, "PRE", "2026-08-04", 0.5, 100.0, side="sell")
    _prices(conn, "PRE", [("2026-08-04", 100.0)])
    _fill(conn, "NOPX", "2026-08-04", 1.0, 40.0)
    conn.commit()
    text = scorecard._portfolio_section(conn)
    assert "excluded: NOPX (no_price_history), PRE (sold_before_journal)" in text
    inception = next(ln for ln in text.splitlines() if ln.strip().startswith("inception"))
    assert inception.split("|")[1].strip() == "12.50%"


def test_portfolio_section_coverage_counts_positions_and_days(tmp_path):
    conn = _fresh(tmp_path)
    _seed_curve(conn)
    text = scorecard._portfolio_section(conn)
    assert "book: 2 positions, 3 trading days 2026-07-31..2026-08-05" in text


def _seed_lockstep(conn, n_days=25, daily=0.01):
    """One share of BOOK bought at the first close, priced in EXACT lockstep
    with SPY over n_days consecutive trading days — so true excess is zero in
    every window."""
    price, spy = 100.0, 500.0
    _fill(conn, "BOOK", "2026-06-01", 1.0, price)
    for i in range(1, n_days + 1):
        obs_date = f"2026-06-{i:02d}"
        conn.execute(
            "INSERT INTO prices (symbol, price_date, close) VALUES ('BOOK', ?, ?)",
            (obs_date, price),
        )
        conn.execute(
            "INSERT INTO prices (symbol, price_date, close) VALUES ('SPY', ?, ?)",
            (obs_date, spy),
        )
        price *= 1.0 + daily
        spy *= 1.0 + daily
    conn.commit()


def test_portfolio_section_window_excess_is_zero_in_lockstep(tmp_path):
    conn = _fresh(tmp_path)
    _seed_lockstep(conn)
    text = scorecard._portfolio_section(conn)
    line = next(ln for ln in text.splitlines() if ln.strip().startswith("21d"))
    # The 21d window must measure the SAME 21 legs on both sides. The anchor
    # row's own port_return is the leg INTO the window from the day before it
    # — chaining it gives the book 22 legs against SPY's 21 and invents excess
    # (+1.23% here) for a book that tracked SPY exactly.
    assert line.split("|")[1].strip() == line.split("|")[2].strip()
    assert line.split("|")[3].strip() == "0.00%"


# --- Cash (DFF) benchmark leg -----------------------------------------------


def _dff(rate=3.6, month="06", start=1, end=25):
    """Daily DFF observations at a flat annualized percent. 3.6%/360 = exactly
    1bp of daily accrual, so expected products are powers of 1.0001."""
    return [(f"2026-{month}-{d:02d}", rate) for d in range(start, end + 1)]


def test_cash_endpoint_return_compounds_daily():
    # 5 accrual days at 3.6/36000 = 1e-4 each: (1.0001)^5 - 1.
    r = scorecard.cash_endpoint_return(_dff(), "2026-06-01", "2026-06-06")
    assert abs(r - (1.0001**5 - 1.0)) < 1e-12


def test_cash_endpoint_return_carries_forward_gaps():
    # No observations on 06-02/03/05/06: each day accrues at the most recent
    # observation on/before it (publication lag and history gaps).
    dff = [("2026-06-01", 3.6), ("2026-06-04", 7.2)]
    r = scorecard.cash_endpoint_return(dff, "2026-06-01", "2026-06-06")
    assert abs(r - (1.0001**3 * 1.0002**2 - 1.0)) < 1e-12


def test_cash_endpoint_return_refuses_without_coverage():
    # No observation on/before the window start: refuse (None), never 0%.
    assert scorecard.cash_endpoint_return([("2026-06-10", 3.6)], "2026-06-01", "2026-06-06") is None
    assert scorecard.cash_endpoint_return([], "2026-06-01", "2026-06-06") is None
    assert scorecard.cash_endpoint_return(_dff(), "2026-06-06", "2026-06-06") is None


def test_portfolio_section_prints_cash_column(tmp_path):
    conn = _fresh(tmp_path)
    _seed_lockstep(conn)  # 25 rows, 2026-06-01..2026-06-25
    text = scorecard._portfolio_section(conn, dff=_dff())
    assert "cash (DFF)" in text.splitlines()[0]
    inception = next(ln for ln in text.splitlines() if ln.strip().startswith("inception"))
    # 24 calendar days of accrual at 1bp/day: (1.0001)^24 - 1 = 0.24%.
    assert inception.split("|")[4].strip() == "0.24%"
    d21 = next(ln for ln in text.splitlines() if ln.strip().startswith("21d"))
    assert d21.split("|")[4].strip() == "0.21%"


def test_portfolio_section_cash_na_without_dff(tmp_path):
    conn = _fresh(tmp_path)
    _seed_lockstep(conn)
    text = scorecard._portfolio_section(conn)
    inception = next(ln for ln in text.splitlines() if ln.strip().startswith("inception"))
    assert inception.split("|")[4].strip() == "n/a"


def test_run_reads_fred_db_for_cash(tmp_path):
    conn = _fresh(tmp_path)
    _seed_curve(conn)
    conn.close()

    from sources.screeners.fred_screener import db as fred_db

    fconn = fred_db.connect(str(tmp_path / "fred.db"))
    fred_db.ensure_schema(fconn)
    fred_db.write_observations(
        fconn, "DFF", [{"date": d, "value": v} for d, v in _dff(month="07", start=28, end=31)]
    )
    fconn.commit()
    fconn.close()

    report = scorecard.run(str(tmp_path / "scorer.db"), NOW, fred_db_path=str(tmp_path / "fred.db"))
    inception = next(ln for ln in report.splitlines() if ln.strip().startswith("inception"))
    # Window 07-31..08-05 = 5 accrual days, carried forward from the 07-31
    # observation: (1.0001)^5 - 1 = 0.05%.
    assert inception.split("|")[4].strip() == "0.05%"


def test_run_missing_fred_db_degrades_to_na(tmp_path):
    conn = _fresh(tmp_path)
    _seed_curve(conn)
    conn.close()
    report = scorecard.run(str(tmp_path / "scorer.db"), NOW, fred_db_path=str(tmp_path / "nope.db"))
    inception = next(ln for ln in report.splitlines() if ln.strip().startswith("inception"))
    assert inception.split("|")[4].strip() == "n/a"


def test_research_backed_section_lists_recommended_buys(tmp_path):
    conn = _fresh(tmp_path)
    conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, recorded_at)"
        " VALUES ('NVDA', 'buy', '2026-07-05', ?)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " exit_fill_date, exit_fill_price, order_ref, placed_agent, recorded_at)"
        " VALUES ('NVDA', 'acted', 'buy', '2026-07-06', 800.0, '2026-07-20', 880.0,"
        " 'f1', 'agentic', ?)",
        (NOW,),
    )
    conn.execute(
        "INSERT INTO decisions (symbol, action, side, fill_date, fill_price,"
        " order_ref, placed_agent, recorded_at)"
        " VALUES ('XOM', 'acted', 'buy', '2026-07-06', 100.0, 'f2', NULL, ?)",
        (NOW,),
    )
    conn.commit()
    assert [r["symbol"] for r in scorecard.research_backed(conn)] == ["NVDA"]
    assert [r["symbol"] for r in scorecard.deliberate_freelance(conn)] == ["XOM"]
    report = scorecard.build_report(conn, NOW)
    backed, free = report.split("Freelance trades")
    assert "NVDA" in backed and "2026-07-05" in backed and "NVDA" not in free
    assert "XOM" in free
