from sources.combiners.scorer import db

NOW = "2026-07-06T21:10:00+00:00"
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


def _seed(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # WIN rises faster than SPY; LOSE falls; SPY drifts up
    db.insert_prices(conn, [("WIN", d, 100 + 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("LOSE", d, 100 - 5 * i) for i, d in enumerate(DAYS)])
    db.insert_prices(conn, [("SPY", d, 500 + i) for i, d in enumerate(DAYS)])
    db.register_snapshot(
        conn,
        1,
        "2026-07-01",
        [
            dict(
                symbol="WIN",
                score_sum=4,
                total=3,
                bullish=3,
                bearish=0,
                in_portfolio=0,
            ),
            dict(
                symbol="LOSE",
                score_sum=-4,
                total=3,
                bullish=0,
                bearish=3,
                in_portfolio=0,
            ),
            dict(
                symbol="SPY",
                score_sum=1,
                total=1,
                bullish=1,
                bearish=0,
                in_portfolio=0,
            ),
        ],
        [
            dict(
                signal_id="si_days_to_cover",
                entity="WIN",
                score=2,
                via_crosswalk=0,
            ),
            dict(
                signal_id="sv_ratio_spike",
                entity="LOSE",
                score=-2,
                via_crosswalk=0,
            ),
        ],
        "risk_on",
        (2,),
        "SPY",
        7,
        NOW,
    )
    db.mature(conn, NOW)
    return conn


def test_bucket_performance(tmp_path):
    conn = _seed(tmp_path)
    rows = {
        r[0]: r
        for r in conn.execute(
            "SELECT bucket, horizon, n_matured, avg_excess, hit_rate FROM v_bucket_performance"
        )
    }
    assert rows["strong_bull"][2] == 1 and rows["strong_bull"][3] > 0
    assert rows["strong_bull"][4] == 1.0  # WIN beat SPY
    assert rows["strong_bear"][2] == 1
    assert rows["strong_bear"][4] == 1.0  # LOSE lagged SPY = bear hit
    assert rows["thin"][2] == 1  # single-signal SPY row


def test_signal_efficacy_direction_adjusted(tmp_path):
    conn = _seed(tmp_path)
    rows = {
        r[0]: r
        for r in conn.execute(
            "SELECT signal_id, n_matured, avg_directional_excess, hit_rate FROM v_signal_efficacy"
        )
    }
    # both signals called their direction correctly -> positive adj excess
    assert rows["si_days_to_cover"][2] > 0
    assert rows["sv_ratio_spike"][2] > 0
    assert rows["sv_ratio_spike"][3] == 1.0


def test_regime_and_pending(tmp_path):
    conn = _seed(tmp_path)
    r = conn.execute(
        "SELECT regime, n_matured, avg_bench_return FROM v_regime_performance"
    ).fetchone()
    assert r[0] == "risk_on" and r[1] == 1 and r[2] > 0
    # register something unmaturable -> shows in v_pending
    db.register_snapshot(conn, 2, "2026-07-06", [], [], "mixed", (21,), "SPY", 7, NOW)
    assert conn.execute("SELECT COUNT(*) FROM v_pending").fetchone()[0] == 1


def test_v_basis_breaks_flags_split_only(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # ACME splits 2:1 between DAYS[2] and DAYS[3]; SPY is normal noise.
    closes = [100.0, 101.0, 99.0, 49.6, 50.0, 50.4, 49.9, 50.2]
    db.insert_prices(conn, list(zip(["ACME"] * 8, DAYS, closes, strict=True)))
    db.insert_prices(conn, [("SPY", d, 500 + i) for i, d in enumerate(DAYS)])
    rows = conn.execute(
        "SELECT symbol, prev_date, price_date, ratio FROM v_basis_breaks"
    ).fetchall()
    assert len(rows) == 1
    sym, prev_date, price_date, ratio = rows[0]
    assert (sym, prev_date, price_date) == ("ACME", DAYS[2], DAYS[3])
    assert abs(ratio - 49.6 / 99.0) < 1e-9


def _signal_row(conn, sig, entity, score, fwd, bench_fwd, benchmark="SPY", xw=0):
    """Insert one matured signal outcome directly (views read the table)."""
    conn.execute(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, ?, 5, '2026-07-02', 100.0, ?, ?,"
        " '2026-07-10', 100.0, ?, ?, ?)",
        (
            sig,
            entity,
            score,
            xw,
            benchmark,
            None if benchmark is None else 500.0,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def _efficacy(conn, sig):
    return conn.execute(
        "SELECT n_matured, n_bench, hit_rate, hit_ci_lo, hit_ci_hi,"
        " reliable, avg_directional_return, benchmarks"
        " FROM v_signal_efficacy WHERE signal_id = ?",
        (sig,),
    ).fetchone()


def test_wilson_interval_hand_computed(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 3 hits out of 4 (bullish rows, hit = fwd > bench_fwd)
    for i, fwd in enumerate((0.02, 0.02, 0.02, 0.00)):
        _signal_row(conn, "sig_a", f"T{i}", 1, fwd, 0.01)
    n, nb, hr, lo, hi, rel, _, _ = _efficacy(conn, "sig_a")
    assert (n, nb) == (4, 4)
    assert abs(hr - 0.75) < 1e-9
    # Wilson 95% for 3/4, hand-computed: z=1.96, z^2=3.8416
    # center=0.75+3.8416/8, margin=1.96*sqrt(0.75*0.25/4+3.8416/64),
    # denom=1+3.8416/4 -> (0.300636, 0.954414)
    assert abs(lo - 0.300636) < 1e-4
    assert abs(hi - 0.954414) < 1e-4
    assert rel == 0


def test_wilson_all_hits_not_degenerate(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(5):
        _signal_row(conn, "sig_a", f"T{i}", 1, 0.02, 0.01)  # 5/5 hits
    _, nb, hr, lo, hi, _, _, _ = _efficacy(conn, "sig_a")
    assert (nb, hr) == (5, 1.0)
    # Wald would say 100% +/- 0; Wilson: lo = 1/(1+3.8416/5) ~ 0.565509
    assert abs(lo - 0.565509) < 1e-4
    # float rounding can land a hair above 1.0 (1.0000000000000002)
    assert abs(hi - 1.0) < 1e-9


def test_reliable_flag_boundary(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(db.RELIABLE_MIN_N):
        _signal_row(conn, "sig_30", f"T{i}", 1, 0.02, 0.01)
    for i in range(db.RELIABLE_MIN_N - 1):
        _signal_row(conn, "sig_29", f"T{i}", 1, 0.02, 0.01)
    assert _efficacy(conn, "sig_30")[5] == 1
    assert _efficacy(conn, "sig_29")[5] == 0


def test_unbenchmarked_rows_labeled_not_hidden(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 2 unbenchmarked (class-proxy) rows + 1 benchmarked, all bullish wins
    _signal_row(conn, "cftc_energy", "XLE", 2, 0.05, None, benchmark=None, xw=1)
    _signal_row(conn, "cftc_energy", "DBA", 2, 0.03, None, benchmark=None, xw=1)
    _signal_row(conn, "cftc_energy", "XOM", 2, 0.04, 0.01, benchmark="XLE", xw=1)
    n, nb, hr, lo, hi, rel, avg_ret, benchmarks = _efficacy(conn, "cftc_energy")
    assert (n, nb) == (3, 1)  # n_matured - n_bench = 2 unbenchmarked
    assert hr == 1.0  # over the 1 benchmarked row only
    assert benchmarks == "XLE"  # states what it was measured against
    # raw directional return covers ALL rows, benchmarked or not
    assert abs(avg_ret - (0.05 + 0.03 + 0.04) / 3) < 1e-9


def test_zero_bench_rows_null_ci(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _signal_row(conn, "cftc_ags", "DBA", 2, 0.03, None, benchmark=None, xw=1)
    n, nb, hr, lo, hi, rel, _, benchmarks = _efficacy(conn, "cftc_ags")
    assert (n, nb) == (1, 0)
    assert hr is None and lo is None and hi is None
    assert rel == 0
    assert benchmarks is None


def _recommendation(conn, sig):
    return conn.execute(
        "SELECT via_crosswalk, horizon, n_bench, avg_directional_excess,"
        " hit_rate, hit_ci_lo, hit_ci_hi, reliable, recommendation"
        " FROM v_signal_recommendation WHERE signal_id = ?",
        (sig,),
    ).fetchone()


def test_recommendation_insufficient_evidence_below_min_n(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 4 benchmarked rows (< RELIABLE_MIN_N) -> not reliable, no verdict
    for i, fwd in enumerate((0.02, 0.02, 0.02, 0.00)):
        _signal_row(conn, "sig_thin", f"T{i}", 1, fwd, 0.01)
    row = _recommendation(conn, "sig_thin")
    assert row[2] == 4 and row[7] == 0  # n_bench=4, reliable=0
    assert row[8] == "insufficient evidence"


def test_recommendation_keep_ci_above_half(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 30 all-hit rows -> reliable, hit_ci_lo > 0.5 -> keep
    for i in range(db.RELIABLE_MIN_N):
        _signal_row(conn, "sig_keep", f"T{i}", 1, 0.02, 0.01)
    row = _recommendation(conn, "sig_keep")
    assert row[7] == 1 and row[5] > 0.5  # reliable, ci_lo above coin flip
    assert row[8] == "keep"


def test_recommendation_anti_signal_ci_below_half(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 30 all-miss bullish rows (fwd < bench) -> reliable, hit_ci_hi < 0.5
    for i in range(db.RELIABLE_MIN_N):
        _signal_row(conn, "sig_anti", f"T{i}", 1, 0.00, 0.01)
    row = _recommendation(conn, "sig_anti")
    assert row[7] == 1 and row[6] < 0.5  # reliable, ci_hi below coin flip
    assert row[8] == "anti-signal"


def test_recommendation_watch_ci_straddles_half(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 15 hits + 15 misses of 30 -> reliable, CI straddles 0.5 -> watch
    for i in range(db.RELIABLE_MIN_N // 2):
        _signal_row(conn, "sig_watch", f"H{i}", 1, 0.02, 0.01)  # hit
    for i in range(db.RELIABLE_MIN_N // 2):
        _signal_row(conn, "sig_watch", f"M{i}", 1, 0.00, 0.01)  # miss
    row = _recommendation(conn, "sig_watch")
    assert row[7] == 1 and row[5] < 0.5 < row[6]  # reliable, CI straddles
    assert row[8] == "watch"


def test_recommendation_crosswalk_split_kept_separate(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # same signal_id, direct vs crosswalk -> two rows, never merged
    _signal_row(conn, "sig_split", "DIR", 1, 0.02, 0.01, xw=0)
    _signal_row(conn, "sig_split", "XW", 1, 0.02, 0.01, benchmark="XLE", xw=1)
    rows = conn.execute(
        "SELECT via_crosswalk FROM v_signal_recommendation"
        " WHERE signal_id = 'sig_split' ORDER BY via_crosswalk"
    ).fetchall()
    assert [r[0] for r in rows] == [0, 1]


def _ticker_row(conn, symbol, score_sum, fwd, bench_fwd, total=3):
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, in_portfolio, horizon,"
        " entry_date, entry_close, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, '2026-07-01', ?, ?, ?, 0, 0, 0, 5, '2026-07-02', 100.0,"
        " ?, '2026-07-10', 100.0, ?, ?, ?)",
        (
            symbol,
            score_sum,
            total,
            None if bench_fwd is None else 500.0,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def test_bucket_guardrail_columns(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # strong_bull bucket: one hit, one miss, one benchmark-less row
    _ticker_row(conn, "A", 4, 0.02, 0.01)  # hit
    _ticker_row(conn, "B", 4, 0.00, 0.01)  # miss
    _ticker_row(conn, "C", 4, 0.02, None)  # unbenchmarked
    row = conn.execute(
        "SELECT n_matured, n_bench, hit_rate, hit_ci_lo, hit_ci_hi, reliable"
        " FROM v_bucket_performance WHERE bucket = 'strong_bull'"
    ).fetchone()
    assert (row[0], row[1]) == (3, 2)
    assert abs(row[2] - 0.5) < 1e-9
    # Wilson 95% for 1/2: hand-computed (0.094529, 0.905471)
    assert abs(row[3] - 0.094529) < 1e-4
    assert abs(row[4] - 0.905471) < 1e-4
    assert row[5] == 0


def _conn(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    return conn


def _graded_verdict(conn, symbol, verdict, fwd, bench, matured="2026-07-20T04:12:00+00:00"):
    cur = conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, recorded_at)"
        " VALUES (?, ?, '2026-07-01', '2026-07-01T20:00:00+00:00')",
        (symbol, verdict),
    )
    conn.execute(
        "INSERT INTO verdict_outcomes (verdict_id, symbol, horizon, entry_date,"
        " entry_close, fwd_return, bench_fwd_return, matured_at)"
        " VALUES (?, ?, 5, '2026-07-02', 100.0, ?, ?, ?)",
        (cur.lastrowid, symbol, fwd, bench, matured),
    )
    return cur.lastrowid


def test_verdict_correct_both_directions(tmp_path):
    conn = _conn(tmp_path)
    _graded_verdict(conn, "AAA", "pass", fwd=0.01, bench=0.05)  # lagged: pass right
    _graded_verdict(conn, "BBB", "pass", fwd=0.10, bench=0.02)  # beat: pass wrong
    _graded_verdict(conn, "CCC", "buy", fwd=0.10, bench=0.02)  # beat: buy right
    _graded_verdict(conn, "DDD", "buy", fwd=0.01, bench=0.05)  # lagged: buy wrong
    rows = dict(
        conn.execute("SELECT symbol, verdict_correct FROM v_research_verdict_outcomes").fetchall()
    )
    assert rows == {"AAA": 1, "BBB": 0, "CCC": 1, "DDD": 0}


def test_unmatured_and_unregistered_verdicts_show_null(tmp_path):
    conn = _conn(tmp_path)
    conn.execute(
        "INSERT INTO research_verdicts (symbol, verdict, verdict_date, recorded_at)"
        " VALUES ('CSU', 'pass', '2026-07-10', '2026-07-10T20:00:00+00:00')"
    )  # no outcome rows at all (uncovered ticker)
    _graded_verdict(conn, "EEE", "pass", fwd=0.01, bench=0.05, matured=None)
    rows = conn.execute(
        "SELECT symbol, verdict_correct FROM v_research_verdict_outcomes ORDER BY symbol"
    ).fetchall()
    assert rows == [("CSU", None), ("EEE", None)]


def test_research_filter_aggregates_matured_only(tmp_path):
    conn = _conn(tmp_path)
    _graded_verdict(conn, "AAA", "pass", fwd=0.01, bench=0.05)
    _graded_verdict(conn, "BBB", "pass", fwd=0.10, bench=0.02)
    _graded_verdict(conn, "EEE", "pass", fwd=0.99, bench=0.0, matured=None)
    row = conn.execute(
        "SELECT n, hit_rate, avg_excess FROM v_research_filter"
        " WHERE verdict = 'pass' AND horizon = 5"
    ).fetchone()
    assert row[0] == 2
    assert abs(row[1] - 0.5) < 1e-12
    assert abs(row[2] - ((0.01 - 0.05) + (0.10 - 0.02)) / 2) < 1e-12


def test_verdict_correct_tie_boundary(tmp_path):
    """fwd_return == bench_fwd_return: pass uses <= (ties count as correct,
    the tracked name didn't beat the benchmark), buy uses > (ties are not a
    beat). Pins the operator pair against a future flip."""
    conn = _conn(tmp_path)
    _graded_verdict(conn, "AAA", "pass", fwd=0.03, bench=0.03)
    _graded_verdict(conn, "BBB", "buy", fwd=0.03, bench=0.03)
    rows = dict(
        conn.execute("SELECT symbol, verdict_correct FROM v_research_verdict_outcomes").fetchall()
    )
    assert rows == {"AAA": 1, "BBB": 0}
