"""The permutation null holds the FLAGS fixed and shuffles the spine's
daily log returns, so every permutation carries the same overlap structure
and the same n as the real data — the two defects the Wilson interval
cannot price (overlapping windows, ~90 uncorrected cells) land in the null
instead of in the analyst's head.

Fixtures drive real catalog signals (cboe_vix scores bullish below 15,
bearish at 25+; cboe_vix_backwardation bearish when close > vix3m) through
the real views — nothing here mocks the statistic."""

import datetime as dt

import pytest

from sources.combiners.backtest import db, mcpt


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.ensure_schema(c)
    yield c
    c.close()


def _date(i):
    return (dt.date(2025, 1, 1) + dt.timedelta(days=i)).isoformat()


def spine(c, closes, benchmark="SP500"):
    c.executemany(
        "INSERT INTO benchmark_closes (benchmark, date, close) VALUES (?, ?, ?)",
        [(benchmark, _date(i), close) for i, close in enumerate(closes)],
    )


def vix(c, i, val):
    """cboe_vix obs: val < 15 -> bullish +1, val >= 25 -> bearish, else 0."""
    c.execute(
        "INSERT INTO market_obs (signal_id, obs_date, val1) VALUES ('cboe_vix', ?, ?)",
        (_date(i), val),
    )


def backwardation(c, i, close, vix3m):
    """cboe_vix_backwardation obs: close > vix3m -> bearish -2, else 0."""
    c.execute(
        "INSERT INTO market_obs (signal_id, obs_date, val1, val2)"
        " VALUES ('cboe_vix_backwardation', ?, ?, ?)",
        (_date(i), close, vix3m),
    )


def _null_rows(conn, n_perms=20, seed=1):
    return {(r[0], r[1], r[2]): r for r in mcpt.permutation_null(conn, n_perms, seed)}


def test_harvest_dedupes_forward_filled_days_to_one_observation(conn):
    """One obs forward-fills across every later as-of date; the cell must
    carry ONE observation at its first as-of, exactly like the view."""
    spine(conn, [100 + i for i in range(40)])
    vix(conn, 2, 10.0)  # bullish, serves dates 2..39
    _, groups, _ = mcpt.harvest(conn)
    ((signal, benchmark, direction, rns),) = groups
    assert (signal, benchmark, direction) == ("cboe_vix", "SP500", "bullish")
    assert rns == [3]  # rn of _date(2); 37 served days, one observation


def test_all_positive_returns_tie_at_p_one_inclusive_convention(conn):
    """Strictly rising spine: every permutation of all-positive returns
    reproduces hit_rate 1.0, so every permutation ties the real statistic
    and p = (1 + n_perms) / (1 + n_perms) = 1.0 exactly — the inclusive
    convention counts the real sample as its own permutation, which is
    also why p can never be 0."""
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    rows = _null_rows(conn, n_perms=25, seed=3)
    for key, r in rows.items():
        assert r[4] == 1.0, key


def test_same_seed_same_p_values(conn):
    closes = [100, 102, 99, 103, 101, 106, 104, 108, 103, 110] * 4
    spine(conn, closes)
    vix(conn, 1, 10.0)
    vix(conn, 8, 10.0)
    a = mcpt.permutation_null(conn, 50, 7)
    b = mcpt.permutation_null(conn, 50, 7)
    assert a == b


def test_right_signal_scores_lower_p_than_wrong_signal(conn):
    """Spine rises hard for 12 days then decays. A bullish flag at the
    start of the rise should look hard to beat by shuffling; a bearish
    flag on the same dates should look like what it is — wrong — with p
    in the unfavorable tail (the anti_signal mirror)."""
    closes = [100.0 * (1.02**i) for i in range(12)]
    closes += [closes[-1] * (0.995 ** (i + 1)) for i in range(28)]
    spine(conn, closes)
    vix(conn, 1, 10.0)  # bullish into the rise
    backwardation(conn, 1, 20.0, 18.0)  # bearish into the rise: wrong
    rows = _null_rows(conn, n_perms=99, seed=5)
    p_bull = rows[("cboe_vix", "bullish", 5)][4]
    p_bear = rows[("cboe_vix_backwardation", "bearish", 5)][4]
    assert p_bull < p_bear
    assert p_bull <= 0.5
    assert p_bear >= 0.5


def test_family_row_prices_the_whole_scoreboard(conn):
    closes = [100.0 * (1.02**i) for i in range(12)]
    closes += [closes[-1] * (0.995 ** (i + 1)) for i in range(28)]
    spine(conn, closes)
    vix(conn, 1, 10.0)
    rows = _null_rows(conn, n_perms=30, seed=2)
    fam = rows[mcpt.FAMILY_KEY]
    assert 0 < fam[4] <= 1.0
    assert fam[3] == 30  # n_perms recorded


def test_everyday_signal_has_no_selection_skill(conn):
    """A signal that flags EVERY day is pure market exposure — zero window
    SELECTION. Its per-cell p must not reward it for the real market's
    ordering (clustered crashes make the real path's up-rate beat any
    shuffled path's): the statistic is EXCESS over each permutation's OWN
    baseline, so an everyday flag ties at excess 0 in every permutation
    and reads p = 1.0. Comparing raw hit rates instead lit broad-coverage
    cells up at p = 0.001 on +0.3pp excess (measured live 2026-07-28) —
    arrangement, not skill."""
    closes, c = [], 100.0
    for i in range(40):
        c *= 0.85 if i in (30, 31) else 1.01  # two ADJACENT crashes
        closes.append(c)
    spine(conn, closes)
    for i in range(40):
        vix(conn, i, 10.0)  # bullish flag every single day
    rows = _null_rows(conn, n_perms=60, seed=4)
    for key, r in rows.items():
        if key == mcpt.FAMILY_KEY:
            continue
        assert r[4] == 1.0, key


def test_neutral_only_flags_produce_no_rows(conn):
    spine(conn, [100 + i for i in range(40)])
    vix(conn, 2, 20.0)  # 15 <= 20 < 25 -> score 0, neutral
    assert mcpt.permutation_null(conn, 10, 1) == []


def test_unmatured_observation_grades_nothing(conn):
    """An observation too near the spine's end has no matured window at any
    horizon — no graded cell, no rows (matches the view's n_bench = 0)."""
    spine(conn, [100 + i for i in range(40)])
    vix(conn, 38, 10.0)  # rn 39: even h=5 needs rn <= 34
    assert mcpt.permutation_null(conn, 10, 1) == []


def test_perm_n_matches_view_n_bench(conn):
    """The permutation must grade exactly the view's population: if the
    replication drifts from v_replay_efficacy's dedupe or maturity, fail
    loudly rather than publish a p for a different statistic."""
    spine(conn, [100 + (i % 7) for i in range(40)])
    vix(conn, 2, 10.0)
    vix(conn, 9, 10.0)
    vix(conn, 20, 10.0)  # h=21 window unmatured for this one
    rows = _null_rows(conn, n_perms=10, seed=1)
    view = {
        (r[0], r[1], r[2]): r[3]
        for r in conn.execute(
            "SELECT signal_id, direction, horizon, n_bench FROM v_replay_efficacy"
            " WHERE direction != 'neutral' AND n_bench > 0"
        )
    }
    assert set(rows) == set(view) | {mcpt.FAMILY_KEY}


def test_nonpositive_n_perms_rejected(conn):
    """-1 divided by zero and -2 wrote p = -1.0 rows before the guard; 0
    would write p = 1.0 everywhere without permuting anything."""
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    for bad in (0, -1, -2):
        with pytest.raises(ValueError):
            mcpt.permutation_null(conn, bad, 1)


# ---- storage + view join ---------------------------------------------

NOW = "2026-07-28T20:00:00+00:00"


def test_write_replay_null_replaces_and_view_joins_perm_p(conn):
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    db.write_replay_null(conn, mcpt.permutation_null(conn, 10, 1), NOW)
    conn.commit()
    row = conn.execute(
        "SELECT perm_p, perm_n FROM v_replay_efficacy"
        " WHERE signal_id = 'cboe_vix' AND direction = 'bullish' AND horizon = 5"
    ).fetchone()
    assert row == (1.0, 10)  # all-positive spine ties at p = 1.0
    # family row is stored but never joins a cell
    assert conn.execute("SELECT COUNT(*) FROM replay_null WHERE signal_id = '*'").fetchone() == (1,)
    assert (
        conn.execute("SELECT COUNT(*) FROM v_replay_efficacy WHERE signal_id = '*'").fetchone()[0]
        == 0
    )
    # a second pass REPLACES the table, never appends
    db.write_replay_null(conn, mcpt.permutation_null(conn, 20, 2), NOW)
    conn.commit()
    assert conn.execute("SELECT DISTINCT n_perms FROM replay_null").fetchall() == [(20,)]


def test_replay_null_records_when_it_was_computed(conn):
    """--perms 0 deliberately keeps a prior pass; captured_at is what makes
    a kept pass distinguishable from a fresh one."""
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    db.write_replay_null(conn, mcpt.permutation_null(conn, 10, 1), NOW)
    conn.commit()
    assert conn.execute("SELECT DISTINCT captured_at FROM replay_null").fetchall() == [(NOW,)]


def test_view_perm_p_null_before_any_pass(conn):
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    row = conn.execute(
        "SELECT perm_p FROM v_replay_efficacy WHERE signal_id = 'cboe_vix' AND horizon = 5"
    ).fetchone()
    assert row == (None,)
