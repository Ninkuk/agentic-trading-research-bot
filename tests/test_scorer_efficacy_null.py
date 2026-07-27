"""v_signal_efficacy must be graded against the universe's base rate, not 0.5.

Equities do not coin-flip against a benchmark, and this universe least of all:
measured 2026-07-27, a randomly chosen scored ticker BEAT SPY only 40.3% of the
time at 10 days (55.3%/44.6% at 5 days) — every composite name is a microcap and
the index rallied through the whole graded window.

Read against 0.5 the view was wrong in BOTH directions at once:
  si_spike        10d  hit 61.1%  null 59.6%  -> +1.5pp, but labelled `keep`
  si_days_to_cover 5d  hit 45.7%  null 44.6%  -> +1.1pp, but labelled `anti-signal`
It condemned a signal beating its baseline and endorsed one that barely moved.

The null population is ticker_outcomes (one row per snapshot x symbol), NOT
signal_outcomes: the latter carries one row per signal, so a signal firing on
2,599 of 7,351 rows would supply a third of its own baseline.
"""

import datetime as dt

from sources.combiners.scorer import db

NOW = "2026-07-27T04:10:00+00:00"


def _fresh(tmp_path):
    conn = db.connect(str(tmp_path / "scorer.db"))
    db.ensure_schema(conn)
    return conn


def _universe(conn, horizon, n_over, n_under):
    """n_over tickers beat the benchmark, n_under lost to it."""
    for i in range(n_over + n_under):
        beat = i < n_over
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at) VALUES (1, '2026-07-06', ?, 0, 0, 0, 0, ?, '2026-07-07',"
            " 100.0, 500.0, '2026-07-14', 100.0, ?, 0.0, ?)",
            (f"U{i}", horizon, 0.05 if beat else -0.05, NOW),
        )


def _signal(conn, signal_id, horizon, score, n_hit, n_miss, tag=""):
    """n_hit rows where the signal's DIRECTION was right, n_miss where wrong.
    One composite_date per row: reliable needs distinct dates, not just
    row count, so a same-day pile must not clear the bar."""
    for i in range(n_hit + n_miss):
        right = i < n_hit
        # bullish hit = outperformed; bearish hit = underperformed
        fwd = (0.05 if right else -0.05) if score > 0 else (-0.05 if right else 0.05)
        date = (dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat()
        conn.execute(
            "INSERT INTO signal_outcomes (composite_snapshot_id, composite_date, signal_id,"
            " entity, score, via_crosswalk, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at, benchmark) VALUES (?, ?, ?, ?, ?, 0, ?, '2026-07-07',"
            " 100.0, 500.0, '2026-07-14', 100.0, ?, 0.0, ?, 'SPY')",
            (i + 1, date, signal_id, f"S{tag}{i}", score, horizon, fwd, NOW),
        )


def _row(conn, signal_id, horizon):
    return conn.execute(
        "SELECT hit_rate, null_rate, edge FROM v_signal_efficacy WHERE signal_id=? AND horizon=?",
        (signal_id, horizon),
    ).fetchone()


def test_null_for_a_bullish_signal_is_the_universe_outperform_rate(tmp_path):
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=40, n_under=60)  # 40% of names beat the benchmark
    _signal(conn, "bull_sig", 10, score=1, n_hit=50, n_miss=50)
    hit, null, edge = _row(conn, "bull_sig", 10)
    assert abs(hit - 0.50) < 1e-9
    assert abs(null - 0.40) < 1e-9
    assert abs(edge - 0.10) < 1e-9


def test_null_for_a_bearish_signal_is_the_universe_underperform_rate(tmp_path):
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=40, n_under=60)  # 60% of names LOST to the benchmark
    _signal(conn, "bear_sig", 10, score=-1, n_hit=60, n_miss=40)
    hit, null, edge = _row(conn, "bear_sig", 10)
    assert abs(hit - 0.60) < 1e-9
    assert abs(null - 0.60) < 1e-9
    assert abs(edge) < 1e-9, "a bearish signal matching the base rate has NO edge"


def test_a_bidirectional_signal_gets_a_blended_null(tmp_path):
    """stocks_rsi votes both ways; one null per signal would be wrong for it,
    so the baseline is resolved per ROW from that row's own direction."""
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=40, n_under=60)
    _signal(conn, "mixed", 10, score=1, n_hit=10, n_miss=10, tag="a")
    _signal(conn, "mixed", 10, score=-1, n_hit=10, n_miss=10, tag="b")
    _, null, _ = _row(conn, "mixed", 10)
    assert abs(null - 0.50) < 1e-9, "half bullish (0.40) + half bearish (0.60)"


def test_ties_are_not_counted_as_outperformance(tmp_path):
    """p_over must be measured, never derived as 1 - p_under: the live table
    carries exact ties (8 at 5d, 3 at 10d)."""
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=50, n_under=50)
    conn.execute(
        "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
        " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
        " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
        " matured_at) VALUES (1, '2026-07-06', 'TIE', 0, 0, 0, 0, 10, '2026-07-07',"
        " 100.0, 500.0, '2026-07-14', 100.0, 0.0, 0.0, ?)",
        (NOW,),
    )
    _signal(conn, "bull_sig", 10, score=1, n_hit=1, n_miss=0)
    _, null, _ = _row(conn, "bull_sig", 10)
    assert abs(null - 50 / 101) < 1e-9, "the tie is in the denominator, not the numerator"


def test_recommendation_grades_against_the_null_not_a_coin_flip(tmp_path):
    """The bug in one test: 50% looks like a coin flip and is BAD against a
    60% base rate.

    n=1000, not 100: at n=100 the Wilson interval spans ~19pp, so a 10pp
    shortfall is genuinely indistinguishable from the null and `watch` is the
    right answer. The view being conservative there is a feature — this test
    supplies enough evidence for the CI to actually clear the baseline."""
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=40, n_under=60)
    _signal(conn, "looks_good", 10, score=-1, n_hit=500, n_miss=500)
    rec = conn.execute(
        "SELECT recommendation FROM v_signal_recommendation WHERE signal_id='looks_good'"
    ).fetchone()[0]
    assert rec == "anti-signal", f"50% against a 60% null is not a keep, got {rec}"


def test_recommendation_does_not_condemn_a_signal_that_beats_its_null(tmp_path):
    """si_days_to_cover's real shape: 45.7% hit looks sub-coin-flip, but the
    bullish null is 44.6% — it was being labelled anti-signal for winning."""
    conn = _fresh(tmp_path)
    _universe(conn, 10, n_over=30, n_under=70)
    _signal(conn, "beats_null", 10, score=1, n_hit=450, n_miss=550)
    rec = conn.execute(
        "SELECT recommendation FROM v_signal_recommendation WHERE signal_id='beats_null'"
    ).fetchone()[0]
    assert rec == "keep", f"45% against a 30% null clearly beats it, got {rec}"


def test_no_universe_rows_leaves_the_null_null_rather_than_guessing(tmp_path):
    """An empty ticker_outcomes must not silently reinstate 0.5."""
    conn = _fresh(tmp_path)
    _signal(conn, "orphan", 10, score=1, n_hit=5, n_miss=5)
    hit, null, edge = _row(conn, "orphan", 10)
    assert hit is not None
    assert null is None and edge is None


# --- the same null, shared by both graded views --------------------------


def test_baseline_is_one_shared_view_not_two_copies(tmp_path):
    """v_signal_efficacy and v_bucket_performance must not each carry their own
    copy of the base-rate SQL, or they drift the way prose and code did."""
    conn = _fresh(tmp_path)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert "v_universe_baseline" in names
    src = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name IN ('v_signal_efficacy','v_bucket_performance')"
    ).fetchall()
    for (text,) in src:
        assert "v_universe_baseline" in text, "view must join the shared baseline"


def test_bucket_performance_carries_the_null_and_edge(tmp_path):
    """Same defect the efficacy table had: hit_rate with a green `reliable`
    badge and nothing to compare it against. The `thin` bucket reads 50.7%
    'reliable' on the live page while its excess is -1.8%."""
    conn = _fresh(tmp_path)
    # Directional score_sum: a row scoring 0 has no direction, so hit and
    # null_rate are both correctly NULL for it — the view is right to decline.
    for i in range(100):
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at) VALUES (?, '2026-07-06', ?, 4, 3, 0, 0, 10, '2026-07-07',"
            " 100.0, 500.0, '2026-07-14', 100.0, ?, 0.0, ?)",
            (i + 1, f"T{i}", 0.05 if i < 40 else -0.05, NOW),
        )
    row = conn.execute(
        "SELECT hit_rate, null_rate, edge FROM v_bucket_performance"
        " WHERE horizon=10 AND bucket='strong_bull'"
    ).fetchone()
    assert row is not None
    assert row[1] is not None, "null_rate must be populated"
    assert abs(row[2] - (row[0] - row[1])) < 1e-9, "edge = hit - null"


def test_bucket_null_follows_the_bucket_direction(tmp_path):
    """A bull bucket is graded on outperformance, a bear bucket on
    underperformance — so they cannot share one baseline number."""
    conn = _fresh(tmp_path)
    # 40 beat / 60 lost, and give each row a directional score_sum.
    for i in range(100):
        beat = i < 40
        conn.execute(
            "INSERT INTO ticker_outcomes (composite_snapshot_id, composite_date, symbol,"
            " score_sum, total, bullish, bearish, horizon, entry_date, entry_close,"
            " bench_entry_close, exit_date, exit_close, fwd_return, bench_fwd_return,"
            " matured_at) VALUES (?, '2026-07-06', ?, ?, 3, 0, 0, 10, '2026-07-07',"
            " 100.0, 500.0, '2026-07-14', 100.0, ?, 0.0, ?)",
            (i + 1, f"T{i}", 4 if i % 2 else -4, 0.05 if beat else -0.05, NOW),
        )
    got = dict(
        (b, n)
        for b, n in conn.execute(
            "SELECT bucket, null_rate FROM v_bucket_performance WHERE horizon=10"
        )
    )
    assert abs(got["strong_bull"] - 0.40) < 1e-9, "bullish bucket -> outperform base rate"
    assert abs(got["strong_bear"] - 0.60) < 1e-9, "bearish bucket -> underperform base rate"
