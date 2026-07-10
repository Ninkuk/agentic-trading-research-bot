import pytest

from sources.combiners.backtest import db


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def spine(c, rows, benchmark="SP500"):
    c.executemany(
        "INSERT INTO benchmark_closes (benchmark, date, close) VALUES (?, ?, ?)",
        [(benchmark, d, close) for d, close in rows],
    )


def bench(c, benchmark, rows):
    spine(c, rows, benchmark=benchmark)


def vintage(c, series, date, realtime_start, value):
    c.execute(
        "INSERT INTO signal_vintages VALUES (?, ?, ?, ?)",
        (series, date, realtime_start, value),
    )


def pit(c, asof, series):
    return c.execute(
        "SELECT value FROM v_pit_signal WHERE asof_date = ? AND series_id = ?",
        (asof, series),
    ).fetchone()


# ---- v_pit_signal ----------------------------------------------------


def test_pit_no_lookahead_ignores_later_revision(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)  # future revision
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


def test_pit_reflects_revision_once_published(conn):
    spine(conn, [("2025-01-10", 100.0), ("2025-02-02", 101.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-02-01", -0.7)
    assert pit(conn, "2025-02-02", "T10Y2Y") == (-0.7,)


def test_pit_hides_observation_published_after_asof(conn):
    # obs date is in the past but its FIRST vintage lands later: invisible.
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-15", 0.9)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (None,)


def test_pit_prefers_latest_observation_date(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-08", "2025-01-08", 0.3)
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", 0.5)
    assert pit(conn, "2025-01-10", "T10Y2Y") == (0.5,)


# ---- v_replay_flags --------------------------------------------------


def test_flags_apply_composite_cases(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-09", -0.1)  # inverted -> -1
    vintage(conn, "BAMLH0A0HYM2", "2025-01-09", "2025-01-09", 5.5)  # >=5.0 -> -2
    rows = dict(
        conn.execute("SELECT signal_id, score FROM v_replay_flags WHERE asof_date = '2025-01-10'")
    )
    assert rows == {"fred_curve": -1, "fred_hy_spread": -2}


def test_flags_exclude_dates_with_no_published_value(conn):
    spine(conn, [("2025-01-10", 100.0)])
    vintage(conn, "T10Y2Y", "2025-01-09", "2025-01-15", 0.5)  # not yet published
    rows = conn.execute("SELECT * FROM v_replay_flags").fetchall()
    assert rows == []


# ---- market_obs (non-vintage market-grain signals) -------------------


def market_obs(c, signal_id, obs_date, val1, val2=None):
    c.execute(
        "INSERT INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?, ?, ?, ?)",
        (signal_id, obs_date, val1, val2),
    )


def test_market_pit_picks_latest_observation_on_or_before_asof(conn):
    spine(conn, [("2025-01-10", 100.0)])
    market_obs(conn, "cboe_vix", "2025-01-08", 22.0)
    market_obs(conn, "cboe_vix", "2025-01-09", 26.0)  # newest <= asof
    market_obs(conn, "cboe_vix", "2025-01-11", 40.0)  # future: invisible
    row = conn.execute(
        "SELECT val1 FROM v_pit_market WHERE asof_date = '2025-01-10' AND signal_id = 'cboe_vix'"
    ).fetchone()
    assert row == (26.0,)


def test_market_flags_reuse_composite_vix_case(conn):
    # 26 -> -1 (>=25), 12 -> +1 (<15), 20 -> 0
    spine(conn, [("2025-01-10", 100.0), ("2025-01-11", 100.0), ("2025-01-12", 100.0)])
    market_obs(conn, "cboe_vix", "2025-01-10", 26.0)
    market_obs(conn, "cboe_vix", "2025-01-11", 12.0)
    market_obs(conn, "cboe_vix", "2025-01-12", 20.0)
    rows = dict(
        conn.execute("SELECT asof_date, score FROM v_replay_flags WHERE signal_id = 'cboe_vix'")
    )
    assert rows == {"2025-01-10": -1, "2025-01-11": 1, "2025-01-12": 0}


def test_market_backwardation_uses_both_columns(conn):
    # close > vix3m -> -2 (backwardation); else 0
    spine(conn, [("2025-01-10", 100.0), ("2025-01-11", 100.0)])
    market_obs(conn, "cboe_vix_backwardation", "2025-01-10", 20.0, 18.0)  # 20>18 -> -2
    market_obs(conn, "cboe_vix_backwardation", "2025-01-11", 15.0, 18.0)  # 15<18 -> 0
    rows = dict(
        conn.execute(
            "SELECT asof_date, score FROM v_replay_flags WHERE signal_id = 'cboe_vix_backwardation'"
        )
    )
    assert rows == {"2025-01-10": -2, "2025-01-11": 0}


def test_market_liquidity_signals_reuse_composite_cases(conn):
    # nyfed_rrp: falling RRP (change<0) -> +1 bullish; rising -> -1.
    # tsy_tga: falling TGA (wow_change<0) -> +1 bullish; rising -> -1.
    spine(conn, [("2025-01-10", 100.0), ("2025-01-11", 100.0)])
    market_obs(conn, "nyfed_rrp", "2025-01-10", -5.0)  # falling -> +1
    market_obs(conn, "nyfed_rrp", "2025-01-11", 5.0)  # rising -> -1
    market_obs(conn, "tsy_tga", "2025-01-10", -3.0)  # falling -> +1
    market_obs(conn, "tsy_tga", "2025-01-11", 3.0)  # rising -> -1
    rows = {
        (r[0], r[1]): r[2]
        for r in conn.execute(
            "SELECT signal_id, asof_date, score FROM v_replay_flags"
            " WHERE signal_id IN ('nyfed_rrp', 'tsy_tga')"
        )
    }
    assert rows[("nyfed_rrp", "2025-01-10")] == 1
    assert rows[("nyfed_rrp", "2025-01-11")] == -1
    assert rows[("tsy_tga", "2025-01-10")] == 1
    assert rows[("tsy_tga", "2025-01-11")] == -1


def test_market_pctile_high_when_latest_is_window_max(conn):
    # ascending equity_pcr -> latest (highest date) is the window max ->
    # pctile 100 -> score +2 (contrarian: panicky put buying = bullish)
    spine(conn, [("2025-02-01", 100.0)])
    for i in range(1, 11):
        market_obs(conn, "cboe_equity_pcr", f"2025-01-{i:02d}", float(i))
    row = conn.execute(
        "SELECT value, score FROM v_replay_flags"
        " WHERE signal_id = 'cboe_equity_pcr' AND asof_date = '2025-02-01'"
    ).fetchone()
    assert row[0] == pytest.approx(100.0) and row[1] == 2


def test_market_pctile_low_when_latest_is_window_min(conn):
    # descending equity_pcr -> latest is the window min -> pctile 10 -> -2
    spine(conn, [("2025-02-01", 100.0)])
    for i in range(1, 11):
        market_obs(conn, "cboe_equity_pcr", f"2025-01-{i:02d}", float(11 - i))
    row = conn.execute(
        "SELECT value, score FROM v_replay_flags"
        " WHERE signal_id = 'cboe_equity_pcr' AND asof_date = '2025-02-01'"
    ).fetchone()
    assert row[0] == pytest.approx(10.0) and row[1] == -2


def test_market_pctile_window_excludes_future_observations(conn):
    # an obs published after D must never enter the as-of window
    spine(conn, [("2025-01-05", 100.0)])
    for i in range(1, 6):
        market_obs(conn, "cboe_equity_pcr", f"2025-01-{i:02d}", float(i))
    market_obs(conn, "cboe_equity_pcr", "2025-01-20", 999.0)  # future, invisible
    row = conn.execute(
        "SELECT value, score FROM v_replay_flags"
        " WHERE signal_id = 'cboe_equity_pcr' AND asof_date = '2025-01-05'"
    ).fetchone()
    # latest <= D is Jan-05 (value 5, the max of the visible 1..5) -> pctile 100
    assert row[0] == pytest.approx(100.0) and row[1] == 2


def test_returns_use_per_benchmark_spine(conn):
    # SP500 flat, XLE rising: an XLE-graded row must reflect XLE's own return,
    # never SP500's. Proves the spine is partitioned by benchmark.
    bench(conn, "SP500", [(f"2025-01-{d:02d}", 100.0) for d in range(1, 11)])
    bench(conn, "XLE", [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 11)])
    row = conn.execute(
        "SELECT entry_close, exit_close, fwd_return FROM v_replay_returns"
        " WHERE benchmark = 'XLE' AND asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row[0] == 102.0  # XLE next close after D (day 2)
    assert row[1] == 107.0  # 5 XLE rows later (day 7)
    assert row[2] == pytest.approx(107.0 / 102.0 - 1)


def test_eia_energy_signal_graded_against_xle_not_sp500(conn):
    # rising XLE + crude DRAW (change_pct <= -2 -> +1 bullish energy). Even
    # with a FALLING SP500 present, the energy hit is judged on XLE.
    bench(conn, "SP500", [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    bench(conn, "XLE", [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    for d in range(1, 31):
        market_obs(conn, "eia_crude_stocks", f"2025-01-{d:02d}", -3.0)  # draw -> +1
    row = conn.execute(
        "SELECT n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'eia_crude_stocks' AND direction = 'bullish' AND horizon = 5"
    ).fetchone()
    assert row[0] == 24  # graded on XLE's spine (same maturation window)
    assert row[1] == pytest.approx(1.0)  # draw called XLE's rise correctly


def test_market_signal_graded_against_sp500_spine(conn):
    # falling benchmark + high VIX (bearish score) from day one -> bearish hits
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    for d in range(1, 31):
        market_obs(conn, "cboe_vix", f"2025-01-{d:02d}", 26.0)  # -1 bearish every day
    row = conn.execute(
        "SELECT n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'cboe_vix' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    assert row[0] == 24  # same maturation window as the fred_curve test
    assert row[1] == pytest.approx(1.0)  # VIX-high called the fall correctly


# ---- v_replay_returns ------------------------------------------------


def test_returns_entry_strictly_after_and_horizon_offsets(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    row = conn.execute(
        "SELECT entry_date, exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row[0] == "2025-01-02"  # first close STRICTLY after D
    assert row[1] == "2025-01-07"  # 5 trading rows after entry
    assert row[2] == pytest.approx(107.0 / 102.0 - 1)


def test_returns_unmatured_dates_yield_null(conn):
    spine(conn, [("2025-01-01", 100.0), ("2025-01-02", 101.0)])
    row = conn.execute(
        "SELECT exit_date, fwd_return FROM v_replay_returns"
        " WHERE asof_date = '2025-01-01' AND horizon = 5"
    ).fetchone()
    assert row == (None, None)


# ---- v_replay_efficacy -----------------------------------------------


def test_efficacy_grades_bearish_flag_against_falling_benchmark(conn):
    # 30 falling closes; curve inverted from day one -> every matured
    # bearish day is a hit at every horizon.
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    row = conn.execute(
        "SELECT n_bench, hit_rate, reliable FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    # ONE vintage observation, forward-filled across 24 matured as-of days.
    # That is one measurement, not 24 (see v_replay_efficacy's report grain).
    assert row[0] == 1
    assert row[1] == pytest.approx(1.0)
    assert row[2] == 0  # 24 < RELIABLE_MIN_N (30)


def test_efficacy_wilson_ci_brackets_hit_rate(conn):
    spine(conn, [(f"2025-01-{d:02d}", 200.0 - d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", -0.5)
    lo, hi = conn.execute(
        "SELECT hit_ci_lo, hit_ci_hi FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'bearish' AND horizon = 5"
    ).fetchone()
    assert 0.0 < lo < 1.0  # Wilson never collapses to zero width on all-hit
    assert hi >= 1.0 or hi == pytest.approx(1.0, abs=1e-9)


def test_efficacy_neutral_rows_reported_but_ungraded(conn):
    spine(conn, [(f"2025-01-{d:02d}", 100.0 + d) for d in range(1, 31)])
    vintage(conn, "T10Y2Y", "2025-01-01", "2025-01-01", 0.5)  # not inverted -> 0
    row = conn.execute(
        "SELECT n_days, n_bench, hit_rate FROM v_replay_efficacy"
        " WHERE signal_id = 'fred_curve' AND direction = 'neutral' AND horizon = 5"
    ).fetchone()
    assert row[0] > 0  # reported
    assert row[1] == 0 and row[2] is None  # excluded from grading


# --- baseline: hit_rate is meaningless without the benchmark's own drift -----


def _spine(conn, benchmark, closes, start="2026-01-01"):
    """closes[i] is the close on trading day i (dates need only be ordered)."""
    import datetime as dt

    d0 = dt.date.fromisoformat(start)
    conn.executemany(
        "INSERT OR REPLACE INTO benchmark_closes (benchmark, date, close) VALUES (?,?,?)",
        [(benchmark, (d0 + dt.timedelta(days=i)).isoformat(), c) for i, c in enumerate(closes)],
    )
    conn.commit()


def test_baseline_measures_unconditional_drift(tmp_path):
    """A monotonically rising spine must report p_up = 1.0 — the null a bullish
    flag has to beat."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "UP", [100.0 + i for i in range(40)])
    rows = dict(conn.execute("SELECT horizon, p_up FROM v_benchmark_baseline WHERE benchmark='UP'"))
    assert rows[5] == 1.0 and rows[10] == 1.0
    downs = dict(
        conn.execute("SELECT horizon, p_down FROM v_benchmark_baseline WHERE benchmark='UP'")
    )
    assert downs[5] == 0.0


def test_baseline_is_per_benchmark(tmp_path):
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "UP", [100.0 + i for i in range(40)])
    _spine(conn, "DOWN", [100.0 - i for i in range(40)])
    got = dict(conn.execute("SELECT benchmark, p_up FROM v_benchmark_baseline WHERE horizon = 5"))
    assert got == {"UP": 1.0, "DOWN": 0.0}


def test_excess_subtracts_the_directional_baseline(tmp_path):
    """A bullish flag on an always-rising spine has hit_rate 1.0 and excess 0.0:
    it did exactly as well as doing nothing. That is the whole point."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])
    # cboe_vix score is bullish when close < 15
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?,?,?,NULL)",
        [
            ("cboe_vix", d, 10.0)
            for (d,) in conn.execute("SELECT date FROM benchmark_closes WHERE benchmark='SP500'")
        ],
    )
    conn.commit()
    row = conn.execute(
        "SELECT hit_rate, baseline, excess, beats_baseline FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bullish' AND horizon=5"
    ).fetchone()
    assert row is not None
    hit, base, excess, beats = row
    assert hit == 1.0 and base == 1.0
    assert excess == 0.0, "a flag that matches pure drift has zero edge"
    assert beats == 0, "and must not be reported as beating the baseline"


def test_reliable_stays_a_sample_size_floor_not_a_verdict(tmp_path):
    """The advisor reads `reliable` as n_bench >= 30 and nothing more
    (advisor/fetch.read_reliable_signals). Adding a baseline must not silently
    redefine it."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='v_replay_efficacy'").fetchone()[0]
    assert "n_bench >= 30) AS reliable" in sql.replace("g.", "")


def _vix_flags(conn, level):
    """Stamp every spine date with one VIX level. CBOE_VIX_SCORE: >=30 -> -2,
    >=25 -> -1, <15 -> +1, else 0."""
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?,?,?,NULL)",
        [
            ("cboe_vix", d, level)
            for (d,) in conn.execute("SELECT date FROM benchmark_closes WHERE benchmark='SP500'")
        ],
    )
    conn.commit()


def test_excess_uses_p_down_for_a_bearish_flag(tmp_path):
    """The bearish arm must subtract p_down, not p_up. On an always-rising spine
    a bearish flag hits 0.0 and p_down is 0.0, so excess is 0.0 — it did exactly
    as badly as the drift implies. Using p_up would give -1.0."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])
    _vix_flags(conn, 31.0)  # bearish
    hit, base, excess, beats = conn.execute(
        "SELECT hit_rate, baseline, excess, beats_baseline FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bearish' AND horizon=5"
    ).fetchone()
    assert (hit, base) == (0.0, 0.0)
    assert excess == 0.0, "bearish excess must be hit - p_down"
    assert beats == 0


def test_beats_baseline_bearish_arm_compares_against_p_down(tmp_path):
    """A bearish flag on a spine that ALWAYS falls hits 1.0, and p_down is 1.0 —
    indistinguishable from drift. Comparing the CI against p_up (0.0) would
    wrongly report it as beating the baseline."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [200.0 - i for i in range(40)])
    _vix_flags(conn, 31.0)
    hit, base, beats = conn.execute(
        "SELECT hit_rate, baseline, beats_baseline FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bearish' AND horizon=5"
    ).fetchone()
    assert (hit, base) == (1.0, 1.0)
    assert beats == 0, "a bearish flag matching pure downward drift has no edge"


def test_beats_baseline_is_null_for_neutral_and_ungraded_rows(tmp_path):
    """score 0 carries no direction, so there is nothing to beat. A NULL here is
    the honest answer; 0 would read as 'tested and failed'."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])
    _vix_flags(conn, 20.0)  # neutral: 15 <= 20 < 25
    row = conn.execute(
        "SELECT direction, n_bench, hit_rate, baseline, excess, beats_baseline"
        " FROM v_replay_efficacy WHERE signal_id='cboe_vix' AND horizon=5"
    ).fetchone()
    direction, n_bench, hit, base, excess, beats = row
    assert direction == "neutral" and n_bench == 0 and hit is None
    assert beats is None, "neutral rows must not claim a verdict"


# --- report grain: n counts observations, not forward-filled days ------------


def test_efficacy_counts_observations_not_forward_filled_days(tmp_path):
    """A weekly report is served on ~5 consecutive as-of dates by v_pit_market's
    forward-fill. Those five days are ONE measurement. Counting them as five
    inflated n ~5x and shrank every Wilson interval to match — that is how
    `eia_crude bearish 10d` came to read n=339 when only 67 reports existed."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])

    # Two observations, 10 calendar days apart -> each forward-fills across many
    # as-of dates. cboe_vix < 15 is bullish.
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?,?,?,NULL)",
        [("cboe_vix", "2026-01-01", 10.0), ("cboe_vix", "2026-01-11", 10.0)],
    )
    conn.commit()

    n_obs, n_days, n_bench = conn.execute(
        "SELECT n_obs, n_days, n_bench FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bullish' AND horizon=5"
    ).fetchone()

    assert n_obs == 2, f"two observations, got n_obs={n_obs}"
    assert n_days > n_obs, "n_days still reports the forward-filled span"
    assert n_bench <= n_obs, "graded count can never exceed the observation count"


def test_wilson_interval_is_computed_on_the_observation_count(tmp_path):
    """The CI must widen when the honest n is small. Same data as above: with
    n_obs=2 the interval must be very wide, not the narrow one 20 forward-filled
    days would produce."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?,?,?,NULL)",
        [("cboe_vix", "2026-01-01", 10.0), ("cboe_vix", "2026-01-11", 10.0)],
    )
    conn.commit()
    n_bench, lo, hi = conn.execute(
        "SELECT n_bench, hit_ci_lo, hit_ci_hi FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bullish' AND horizon=5"
    ).fetchone()
    assert n_bench <= 2
    assert hi - lo > 0.4, f"CI width {hi - lo:.3f} — computed on days, not observations?"


def test_reliable_floor_now_counts_observations(tmp_path):
    """`reliable` is still only a sample-size floor, but the sample it counts is
    now observations. 40 forward-filled days behind 2 reports is not 40 samples."""
    conn = db.connect(str(tmp_path / "backtest.db"))
    db.ensure_schema(conn)
    _spine(conn, "SP500", [100.0 + i for i in range(40)])
    conn.executemany(
        "INSERT OR REPLACE INTO market_obs (signal_id, obs_date, val1, val2) VALUES (?,?,?,NULL)",
        [("cboe_vix", "2026-01-01", 10.0), ("cboe_vix", "2026-01-11", 10.0)],
    )
    conn.commit()
    n_days, reliable = conn.execute(
        "SELECT n_days, reliable FROM v_replay_efficacy"
        " WHERE signal_id='cboe_vix' AND direction='bullish' AND horizon=5"
    ).fetchone()
    assert n_days >= 30, "the inflated day count would have cleared the floor"
    assert reliable == 0, "2 observations must not be called reliable"
