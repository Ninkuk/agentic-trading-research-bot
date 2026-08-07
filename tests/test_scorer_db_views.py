import datetime as dt

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


def _date(i):
    """Sequential ISO dates so a fixture can spread rows across composite
    dates (reliable requires distinct dates, not just row count)."""
    return (dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat()


def _signal_row(
    conn,
    sig,
    entity,
    score,
    fwd,
    bench_fwd,
    benchmark="SPY",
    xw=0,
    date="2026-07-01",
    entry_date="2026-07-02",
    exit_date="2026-07-10",
):
    """Insert one matured signal outcome directly (views read the table)."""
    conn.execute(
        "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date,"
        " signal_id, entity, score, via_crosswalk, horizon, entry_date,"
        " entry_close, benchmark, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, ?, ?, ?, ?, ?, 5, ?, 100.0, ?, ?, ?, 100.0, ?, ?, ?)",
        (
            date,
            sig,
            entity,
            score,
            xw,
            entry_date,
            benchmark,
            None if benchmark is None else 500.0,
            exit_date,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def _spread_signal_row(conn, sig, i, fwd=0.02, bench_fwd=0.01, score=1, entity=None):
    """One matured row whose forward window overlaps no other index's:
    7-day windows spaced 10 days apart, so row i and row i+1 are
    independent blocks (entry_{i+1} two days after exit_i)."""
    _signal_row(
        conn,
        sig,
        entity or f"T{i}",
        score,
        fwd,
        bench_fwd,
        date=_date(10 * i),
        entry_date=_date(10 * i + 1),
        exit_date=_date(10 * i + 8),
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
    # 3 hits out of 4 independent windows (bullish rows, hit = fwd > bench)
    for i, fwd in enumerate((0.02, 0.02, 0.02, 0.00)):
        _spread_signal_row(conn, "sig_a", i, fwd=fwd)
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
        _spread_signal_row(conn, "sig_a", i)  # 5/5 hits, independent windows
    _, nb, hr, lo, hi, _, _, _ = _efficacy(conn, "sig_a")
    assert (nb, hr) == (5, 1.0)
    # Wald would say 100% +/- 0; Wilson: lo = 1/(1+3.8416/5) ~ 0.565509
    assert abs(lo - 0.565509) < 1e-4
    # float rounding can land a hair above 1.0 (1.0000000000000002)
    assert abs(hi - 1.0) < 1e-9


def test_reliable_flag_boundary(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(db.RELIABLE_MIN_BLOCKS):
        _spread_signal_row(conn, "sig_30", i)
    for i in range(db.RELIABLE_MIN_BLOCKS - 1):
        _spread_signal_row(conn, "sig_29", i)
    assert _efficacy(conn, "sig_30")[5] == 1
    assert _efficacy(conn, "sig_29")[5] == 0


def test_efficacy_n_dates_counts_distinct_benchmarked_dates(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 3 benchmarked rows on 2 distinct dates + 1 unbenchmarked row on a 3rd
    # date: n_dates counts only dates with a gradable benchmark, matching
    # the population reliable is judged on.
    _signal_row(conn, "sig_d", "A", 1, 0.02, 0.01, date=_date(0))
    _signal_row(conn, "sig_d", "B", 1, 0.02, 0.01, date=_date(0))
    _signal_row(conn, "sig_d", "C", 1, 0.02, 0.01, date=_date(1))
    _signal_row(conn, "sig_d", "D", 1, 0.02, None, benchmark=None, date=_date(2))
    row = conn.execute(
        "SELECT n_matured, n_bench, n_dates FROM v_signal_efficacy WHERE signal_id = 'sig_d'"
    ).fetchone()
    assert row == (4, 3, 2)


def test_reliable_requires_distinct_dates(tmp_path):
    """The si_spike trap: 2,599 matured rows collapsed to 8 distinct
    composite dates (measured 2026-07-27) yet wore the reliable badge.
    Row count alone must not clear the bar — the same rows on one date
    are one episode, not RELIABLE_MIN_N observations."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(db.RELIABLE_MIN_N * 2):
        _signal_row(conn, "sig_one_day", f"T{i}", 1, 0.02, 0.01)
    assert _efficacy(conn, "sig_one_day")[5] == 0  # 60 rows, 1 date


def test_bucket_reliable_requires_distinct_dates(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(db.RELIABLE_MIN_N * 2):
        _ticker_row(conn, f"T{i}", 4, 0.02, 0.01)  # all one date
    n_bench, n_dates, reliable = conn.execute(
        "SELECT n_bench, n_dates, reliable FROM v_bucket_performance WHERE bucket = 'strong_bull'"
    ).fetchone()
    assert n_bench == db.RELIABLE_MIN_N * 2
    assert n_dates == 1
    assert reliable == 0


def test_ci_center_is_date_mean_not_row_pooled(tmp_path):
    """One heavy cross-section must not drag the CI's center: the graded
    hit_rate weights each DATE equally (cluster mean), matching the block
    count the interval's n uses. 3 hits on date 0 + 1 miss on date 10 is
    50% by date-mean (2 blocks), not 75% by row-pool — measured live,
    si_spike's heaviest date carried 26% of the rows and biased the pooled
    center +2pp."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for sym in ("A", "B", "C"):  # one date, three hit rows
        _signal_row(
            conn,
            "sig_c",
            sym,
            1,
            0.02,
            0.01,
            date=_date(0),
            entry_date=_date(1),
            exit_date=_date(8),
        )
    _signal_row(  # second date, one miss row
        conn,
        "sig_c",
        "D",
        1,
        0.00,
        0.01,
        date=_date(10),
        entry_date=_date(11),
        exit_date=_date(18),
    )
    row = conn.execute(
        "SELECT n_bench, n_blocks, hit_rate, hit_ci_lo, hit_ci_hi"
        " FROM v_signal_efficacy WHERE signal_id = 'sig_c'"
    ).fetchone()
    assert (row[0], row[1]) == (4, 2)
    assert abs(row[2] - 0.5) < 1e-9  # (1.0 + 0.0) / 2, not 3/4
    # Wilson 95% for p=0.5, n=2 blocks — same hand-computed pair as the
    # bucket guardrail test
    assert abs(row[3] - 0.094529) < 1e-4
    assert abs(row[4] - 0.905471) < 1e-4


def test_bucket_ci_center_is_date_mean_not_row_pooled(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for sym in ("A", "B", "C"):
        _ticker_row(
            conn,
            sym,
            4,
            0.02,
            0.01,
            date=_date(0),
            entry_date=_date(1),
            exit_date=_date(8),
        )
    _ticker_row(
        conn,
        "D",
        4,
        0.00,
        0.01,
        date=_date(10),
        entry_date=_date(11),
        exit_date=_date(18),
    )
    row = conn.execute(
        "SELECT n_bench, n_blocks, hit_rate FROM v_bucket_performance WHERE bucket = 'strong_bull'"
    ).fetchone()
    assert row[0] == 4 and row[1] == 2
    assert abs(row[2] - 0.5) < 1e-9


def test_degenerate_window_row_terminates_the_chain(tmp_path):
    """Corrupted data (exit before entry — mature() can never write it, but
    the chain must not trust that) terminates instead of recursing forever:
    a block anchor can never re-select its own date."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _signal_row(  # exit BEFORE entry: satisfies its own chain condition
        conn,
        "sig_bad",
        "A",
        1,
        0.02,
        0.01,
        date=_date(0),
        entry_date=_date(8),
        exit_date=_date(1),
    )
    _signal_row(
        conn,
        "sig_bad",
        "B",
        1,
        0.02,
        0.01,
        date=_date(10),
        entry_date=_date(11),
        exit_date=_date(18),
    )
    n_blocks = conn.execute(
        "SELECT n_blocks FROM v_signal_efficacy WHERE signal_id = 'sig_bad'"
    ).fetchone()[0]
    assert n_blocks == 2  # terminated, both dates chained


def test_by_date_view_collapses_rows_per_date(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # date 0: two benchmarked rows (1 hit, 1 miss); date 1: one unbenchmarked
    _signal_row(conn, "sig_bd", "A", 1, 0.02, 0.01, date=_date(0))
    _signal_row(conn, "sig_bd", "B", 1, 0.00, 0.01, date=_date(0))
    _signal_row(conn, "sig_bd", "C", 1, 0.02, None, benchmark=None, date=_date(1))
    rows = conn.execute(
        "SELECT composite_date, n_rows, n_bench, date_hit_rate"
        " FROM v_signal_efficacy_by_date WHERE signal_id = 'sig_bd'"
        " ORDER BY composite_date"
    ).fetchall()
    assert rows[0] == (_date(0), 2, 2, 0.5)
    assert rows[1][1:3] == (1, 0) and rows[1][3] is None


def test_blocks_overlapping_windows_are_one_block(tmp_path):
    """Three consecutive composite dates whose forward windows share days
    are ONE independent observation, not three."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(3):
        _signal_row(
            conn,
            "sig_ov",
            f"T{i}",
            1,
            0.02,
            0.01,
            date=_date(i),
            entry_date=_date(i + 1),
            exit_date=_date(i + 8),
        )
    n_blocks = conn.execute(
        "SELECT n_blocks FROM v_signal_efficacy WHERE signal_id = 'sig_ov'"
    ).fetchone()[0]
    assert n_blocks == 1


def test_blocks_touching_windows_are_independent(tmp_path):
    """A window whose entry_date equals the prior window's exit_date shares
    a close but no return interval — it starts a new block."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _signal_row(
        conn, "sig_tb", "A", 1, 0.02, 0.01, date=_date(0), entry_date=_date(1), exit_date=_date(8)
    )
    _signal_row(
        conn, "sig_tb", "B", 1, 0.02, 0.01, date=_date(7), entry_date=_date(8), exit_date=_date(15)
    )
    # one day earlier and it overlaps: same block
    _signal_row(
        conn, "sig_tb2", "A", 1, 0.02, 0.01, date=_date(0), entry_date=_date(1), exit_date=_date(8)
    )
    _signal_row(
        conn, "sig_tb2", "B", 1, 0.02, 0.01, date=_date(6), entry_date=_date(7), exit_date=_date(14)
    )
    blocks = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT signal_id, n_blocks FROM v_signal_efficacy"
            " WHERE signal_id IN ('sig_tb', 'sig_tb2')"
        )
    }
    assert blocks == {"sig_tb": 2, "sig_tb2": 1}


def test_signal_blocks_view_exposes_the_chain(tmp_path):
    """v_signal_blocks is the audit trail: one row per block anchor date."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(3):
        _spread_signal_row(conn, "sig_chain", i)
    anchors = [
        r[0]
        for r in conn.execute(
            "SELECT composite_date FROM v_signal_blocks"
            " WHERE signal_id = 'sig_chain' ORDER BY composite_date"
        )
    ]
    assert anchors == [_date(0), _date(10), _date(20)]


def test_wilson_n_is_blocks_not_rows(tmp_path):
    """8 rows on 4 non-overlapping dates: the CI must be Wilson(p=0.75,
    n=4 blocks) — the hand-computed 3-of-4 interval — never Wilson(n=8)."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(4):
        fwd = 0.02 if i < 3 else 0.00  # dates 0-2 hit twice, date 3 misses twice
        for sym in ("A", "B"):
            _signal_row(
                conn,
                "sig_blk",
                f"{sym}{i}",
                1,
                fwd,
                0.01,
                date=_date(10 * i),
                entry_date=_date(10 * i + 1),
                exit_date=_date(10 * i + 8),
            )
    row = conn.execute(
        "SELECT n_bench, n_blocks, hit_rate, hit_ci_lo, hit_ci_hi"
        " FROM v_signal_efficacy WHERE signal_id = 'sig_blk'"
    ).fetchone()
    n_bench, n_blocks, hr, lo, hi = row
    assert (n_bench, n_blocks) == (8, 4)
    assert abs(hr - 0.75) < 1e-9
    assert abs(lo - 0.300636) < 1e-4  # Wilson 3/4, NOT 6/8
    assert abs(hi - 0.954414) < 1e-4


def test_reliable_requires_nonoverlapping_blocks(tmp_path):
    """The consecutive-sessions trap the n_dates gate cannot catch: 30
    rolling one-day-apart dates with 7-day windows are ~5 independent
    windows, not 30 — six weeks of nightly runs must NOT re-arm verdicts."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(30):
        _signal_row(
            conn,
            "sig_roll",
            f"T{i}",
            1,
            0.02,
            0.01,
            date=_date(i),
            entry_date=_date(i + 1),
            exit_date=_date(i + 8),
        )
    row = conn.execute(
        "SELECT n_bench, n_dates, n_blocks, reliable FROM v_signal_efficacy"
        " WHERE signal_id = 'sig_roll'"
    ).fetchone()
    assert row[0] == 30 and row[1] == 30  # both old gates would pass
    assert row[2] == 5  # anchors at i = 0, 7, 14, 21, 28
    assert row[3] == 0


def test_recommendation_consecutive_sessions_stay_insufficient(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _coin_flip_universe(conn)
    for i in range(30):
        _signal_row(
            conn,
            "sig_roll",
            f"T{i}",
            1,
            0.02,
            0.01,
            date=_date(i),
            entry_date=_date(i + 1),
            exit_date=_date(i + 8),
        )
    row = conn.execute(
        "SELECT n_blocks, recommendation FROM v_signal_recommendation WHERE signal_id = 'sig_roll'"
    ).fetchone()
    assert row == (5, "insufficient evidence")


def test_bucket_blocks_and_reliable(tmp_path):
    """v_bucket_performance carries the same defect and the same fix."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    for i in range(3):  # overlapping windows -> one block
        _ticker_row(
            conn,
            f"T{i}",
            4,
            0.02,
            0.01,
            date=_date(i),
            entry_date=_date(i + 1),
            exit_date=_date(i + 8),
        )
    row = conn.execute(
        "SELECT n_bench, n_blocks, reliable FROM v_bucket_performance WHERE bucket = 'strong_bull'"
    ).fetchone()
    assert row == (3, 1, 0)


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


def _coin_flip_universe(conn, horizon=5, n=100):
    """A ticker_outcomes population that is exactly 50/50 against the
    benchmark, so v_signal_efficacy.null_rate resolves to 0.5 and these tests
    keep asserting what they always meant: CI above/below a COIN FLIP.

    Needed since the recommendation view stopped hardcoding 0.5 and started
    grading against the measured base rate — with no universe rows the null is
    NULL and every signal correctly falls through to 'watch'."""
    for i in range(n):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
            " symbol, score_sum, total, bullish, bearish, horizon, entry_date,"
            " entry_close, bench_entry_close, exit_date, exit_close, fwd_return,"
            " bench_fwd_return, matured_at) VALUES (1, '2026-07-01', ?, 0, 0, 0, 0,"
            " ?, '2026-07-02', 100.0, 500.0, '2026-07-10', 100.0, ?, 0.0,"
            " '2026-07-10T00:00:00+00:00')",
            (f"U{i}", horizon, 0.01 if i < n // 2 else -0.01),
        )


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
    _coin_flip_universe(conn)
    # 30 all-hit independent windows -> reliable, hit_ci_lo > 0.5 -> keep
    for i in range(db.RELIABLE_MIN_BLOCKS):
        _spread_signal_row(conn, "sig_keep", i)
    row = _recommendation(conn, "sig_keep")
    assert row[7] == 1 and row[5] > 0.5  # reliable, ci_lo above coin flip
    assert row[8] == "keep"


def test_recommendation_anti_signal_ci_below_half(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _coin_flip_universe(conn)
    # 30 all-miss bullish independent windows (fwd < bench) -> reliable,
    # hit_ci_hi < 0.5
    for i in range(db.RELIABLE_MIN_BLOCKS):
        _spread_signal_row(conn, "sig_anti", i, fwd=0.00)
    row = _recommendation(conn, "sig_anti")
    assert row[7] == 1 and row[6] < 0.5  # reliable, ci_hi below coin flip
    assert row[8] == "anti-signal"


def test_recommendation_watch_ci_straddles_half(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # 15 hits + 15 misses across 30 independent windows -> reliable, CI
    # straddles 0.5 -> watch
    for i in range(db.RELIABLE_MIN_BLOCKS // 2):
        _spread_signal_row(conn, "sig_watch", i, entity=f"H{i}")  # hit
    for i in range(db.RELIABLE_MIN_BLOCKS // 2):
        _spread_signal_row(conn, "sig_watch", 15 + i, fwd=0.00, entity=f"M{i}")
    row = _recommendation(conn, "sig_watch")
    assert row[7] == 1 and row[5] < 0.5 < row[6]  # reliable, CI straddles
    assert row[8] == "watch"


def test_recommendation_insufficient_evidence_when_dates_thin(tmp_path):
    """Enough rows but one composite date must read 'insufficient evidence',
    not 'keep' — the recommendation view re-derives its gate rather than
    trusting the reliable flag, so it needs the date floor independently."""
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    _coin_flip_universe(conn)
    for i in range(db.RELIABLE_MIN_N * 2):
        _signal_row(conn, "sig_episode", f"T{i}", 1, 0.02, 0.01)  # all one date
    row = _recommendation(conn, "sig_episode")
    assert row[7] == 0  # not reliable despite n_bench = 60
    assert row[8] == "insufficient evidence"


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


def _ticker_row(
    conn,
    symbol,
    score_sum,
    fwd,
    bench_fwd,
    total=3,
    date="2026-07-01",
    entry_date="2026-07-02",
    exit_date="2026-07-10",
):
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date,"
        " symbol, score_sum, total, bullish, bearish, in_portfolio, horizon,"
        " entry_date, entry_close, bench_entry_close, exit_date, exit_close,"
        " fwd_return, bench_fwd_return, matured_at)"
        " VALUES (1, ?, ?, ?, ?, 0, 0, 0, 5, ?, 100.0, ?, ?, 100.0, ?, ?, ?)",
        (
            date,
            symbol,
            score_sum,
            total,
            entry_date,
            None if bench_fwd is None else 500.0,
            exit_date,
            fwd,
            bench_fwd,
            NOW,
        ),
    )


def test_bucket_guardrail_columns(tmp_path):
    conn = db.connect(str(tmp_path / "s.db"))
    db.ensure_schema(conn)
    # strong_bull bucket: one hit + one miss on independent windows, plus
    # one benchmark-less row
    _ticker_row(
        conn, "A", 4, 0.02, 0.01, date=_date(0), entry_date=_date(1), exit_date=_date(8)
    )  # hit
    _ticker_row(
        conn, "B", 4, 0.00, 0.01, date=_date(10), entry_date=_date(11), exit_date=_date(18)
    )  # miss
    _ticker_row(conn, "C", 4, 0.02, None, date=_date(20), entry_date=_date(21), exit_date=_date(28))
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


def test_equity_curve_subtracts_flow_before_chaining(tmp_path):
    conn = _conn(tmp_path)  # module's existing schema-backed connection helper
    conn.executemany(
        "INSERT INTO equity_ledger (obs_date, equity, cash, captured_at)"
        " VALUES (?, ?, 0, '2026-08-06T04:00:00+00:00')",
        [("2026-07-31", 197.0), ("2026-08-04", 303.0), ("2026-08-05", 306.0)],
    )
    conn.execute(
        "INSERT INTO transfers (obs_date, amount, recorded_at)"
        " VALUES ('2026-08-04', 100.0, '2026-08-06T04:00:00+00:00')"
    )
    conn.executemany(
        "INSERT INTO prices (symbol, price_date, close) VALUES ('SPY', ?, ?)",
        [("2026-07-31", 630.0), ("2026-08-04", 636.3), ("2026-08-05", 640.0)],
    )
    conn.commit()
    rows = conn.execute(
        "SELECT obs_date, flow, prev_equity, port_return, spy_close"
        " FROM v_equity_curve ORDER BY obs_date"
    ).fetchall()
    assert rows[0] == ("2026-07-31", 0.0, None, None, 630.0)
    # deposit day: (303-100)/197 - 1 ≈ +3.05%, NOT +53.8%
    assert rows[1][0:3] == ("2026-08-04", 100.0, 197.0)
    assert abs(rows[1][3] - ((303.0 - 100.0) / 197.0 - 1.0)) < 1e-9
    assert abs(rows[2][3] - (306.0 / 303.0 - 1.0)) < 1e-9


def test_equity_curve_missing_spy_date_is_null_not_dropped(tmp_path):
    conn = _conn(tmp_path)
    conn.executemany(
        "INSERT INTO equity_ledger (obs_date, equity, cash, captured_at)"
        " VALUES (?, ?, 0, '2026-08-06T04:00:00+00:00')",
        [("2026-08-01", 200.0), ("2026-08-04", 202.0)],  # 08-01 is a Saturday
    )
    conn.commit()
    rows = conn.execute(
        "SELECT obs_date, spy_close FROM v_equity_curve ORDER BY obs_date"
    ).fetchall()
    assert rows == [("2026-08-01", None), ("2026-08-04", None)]
