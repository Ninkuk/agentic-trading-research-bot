"""The rotation null holds the SPINE fixed and circularly shifts every
cell's observation rows by k for every k in 1..M-1 (M = returns in the
spine), so each draw keeps the returns' autocorrelation and volatility
clustering AND moves a clustered flag whole — a 53-day episode is graded as
one episode, not 53 draws. Exhaustive, so no seed. Same fixtures and real
views as test_backtest_mcpt; nothing mocks the statistic."""

import datetime as dt
import math

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
    c.execute(
        "INSERT INTO market_obs (signal_id, obs_date, val1, val2)"
        " VALUES ('cboe_vix_backwardation', ?, ?, ?)",
        (_date(i), close, vix3m),
    )


def _rows(conn):
    return {(r[0], r[1], r[2]): r for r in mcpt.rotation_null(conn)}


def test_n_shifts_is_spine_returns_minus_one(conn):
    """40 closes -> 39 returns -> 38 non-trivial rotations (k = 0 is the
    real alignment and is counted once, inclusively, in the numerator)."""
    spine(conn, [100 + (i % 7) for i in range(40)])
    vix(conn, 2, 10.0)
    rows = _rows(conn)
    assert rows[("cboe_vix", "bullish", 5)][3] == 38


def test_all_positive_returns_tie_at_p_one(conn):
    """Strictly rising spine: every rotation reproduces hit_rate 1.0, every
    shift ties the real statistic, p = (1 + 38) / 39 = 1.0 exactly."""
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    for key, r in _rows(conn).items():
        assert r[4] == 1.0, key


def test_right_signal_scores_lower_p_than_wrong_signal(conn):
    closes = [100.0 * (1.02**i) for i in range(12)]
    closes += [closes[-1] * (0.995 ** (i + 1)) for i in range(28)]
    spine(conn, closes)
    vix(conn, 1, 10.0)  # bullish into the rise
    backwardation(conn, 1, 20.0, 18.0)  # bearish into the rise: wrong
    rows = _rows(conn)
    p_bull = rows[("cboe_vix", "bullish", 5)][4]
    p_bear = rows[("cboe_vix_backwardation", "bearish", 5)][4]
    assert p_bull < p_bear
    assert p_bull <= 0.5
    assert p_bear >= 0.5


def test_p_matches_exhaustive_circular_enumeration(conn):
    """Independent oracle on a spine small enough to enumerate by hand:
    8 closes, 7 circular returns, one bullish obs at rn 1, h = 5. For each
    k the window is returns (1+k .. 1+k+4) mod 7; p counts shifts whose
    window return is >= the real one, plus the real alignment itself."""
    closes = [100.0, 103.0, 101.0, 104.0, 102.0, 99.0, 105.0, 103.0]
    spine(conn, closes)
    vix(conn, 0, 10.0)  # rn 1: entry rn 2, exit rn 7 -> matured at h = 5 only
    r = [math.log(closes[i + 1] / closes[i]) for i in range(7)]
    m = len(r)

    def window(start):
        return sum(r[(start + j) % m] for j in range(5))

    real_hit = window(1) > 0
    ties = sum(1 for k in range(1, m) if (window(1 + k) > 0) >= real_hit)
    expected = (1 + ties) / m
    rows = _rows(conn)
    assert rows[("cboe_vix", "bullish", 5)] == ("cboe_vix", "bullish", 5, m - 1, expected)
    assert set(rows) == {("cboe_vix", "bullish", 5), mcpt.FAMILY_KEY}


def test_cluster_is_moved_whole(conn):
    """Three consecutive bullish obs at the start of a 12-day rise. Under
    rotation the trio moves as a block, so its p equals that of the block's
    own circular enumeration — NOT three independent draws. Enumerated
    independently here over the 39 circular return windows."""
    closes = [100.0 * (1.02**i) for i in range(12)]
    closes += [closes[-1] * (0.995 ** (i + 1)) for i in range(28)]
    spine(conn, closes)
    for i in (0, 1, 2):
        vix(conn, i, 10.0)  # rns 1, 2, 3
    r = [math.log(closes[i + 1] / closes[i]) for i in range(39)]
    m = len(r)

    def up(start, h):
        return sum(r[(start + j) % m] for j in range(h)) > 0

    def hits(k, h):
        return sum(up(a + k, h) for a in (1, 2, 3)) / 3

    rows = _rows(conn)
    for h in (5, 10, 21):
        real = hits(0, h)
        ties = sum(1 for k in range(1, m) if hits(k, h) >= real)
        assert rows[("cboe_vix", "bullish", h)][4] == (1 + ties) / m, h


def test_family_row_prices_the_whole_scoreboard(conn):
    closes = [100.0 * (1.02**i) for i in range(12)]
    closes += [closes[-1] * (0.995 ** (i + 1)) for i in range(28)]
    spine(conn, closes)
    vix(conn, 1, 10.0)
    fam = _rows(conn)[mcpt.FAMILY_KEY]
    assert 0 < fam[4] <= 1.0
    assert fam[3] == 38


def test_neutral_only_flags_produce_no_rows(conn):
    spine(conn, [100 + i for i in range(40)])
    vix(conn, 2, 20.0)
    assert mcpt.rotation_null(conn) == []


def test_rot_n_matches_view_n_bench(conn):
    """Same population guard as the permutation pass: grade exactly the
    view's cells, or raise rather than publish a p for another statistic."""
    spine(conn, [100 + (i % 7) for i in range(40)])
    vix(conn, 2, 10.0)
    vix(conn, 9, 10.0)
    vix(conn, 20, 10.0)  # h=21 window unmatured for this one
    rows = _rows(conn)
    view = {
        (r[0], r[1], r[2])
        for r in conn.execute(
            "SELECT signal_id, direction, horizon FROM v_replay_efficacy"
            " WHERE direction != 'neutral' AND n_bench > 0"
        )
    }
    assert set(rows) == view | {mcpt.FAMILY_KEY}


# ---- storage + view join ---------------------------------------------

NOW = "2026-09-27T20:00:00+00:00"


def test_write_rotation_null_replaces_and_view_joins_rot_p(conn):
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    db.write_rotation_null(conn, mcpt.rotation_null(conn), NOW)
    conn.commit()
    row = conn.execute(
        "SELECT rot_p, rot_n, perm_p FROM v_replay_efficacy"
        " WHERE signal_id = 'cboe_vix' AND direction = 'bullish' AND horizon = 5"
    ).fetchone()
    assert row == (1.0, 38, None)  # rotation written, shuffle pass not run
    assert conn.execute(
        "SELECT COUNT(*), captured_at FROM replay_rotation_null WHERE signal_id = '*'"
    ).fetchone() == (1, NOW)
    assert (
        conn.execute("SELECT COUNT(*) FROM v_replay_efficacy WHERE signal_id = '*'").fetchone()[0]
        == 0
    )
    db.write_rotation_null(conn, [("stale", "bullish", 5, 3, 0.5)], NOW)
    conn.commit()
    assert conn.execute("SELECT signal_id FROM replay_rotation_null").fetchall() == [("stale",)]


def test_view_rot_p_null_before_any_pass(conn):
    spine(conn, [100.0 * (1.01**i) for i in range(40)])
    vix(conn, 2, 10.0)
    row = conn.execute(
        "SELECT rot_p, rot_n FROM v_replay_efficacy WHERE signal_id = 'cboe_vix' AND horizon = 5"
    ).fetchone()
    assert row == (None, None)
